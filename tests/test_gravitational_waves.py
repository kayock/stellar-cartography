"""Gravitational Waves registry, labs, events, API, and Stellarium tests."""

from __future__ import annotations

import json
import unittest
import urllib.request

from app import exhibit
from app import gravitational_waves as gw
from app.server import run_server
from tests.fixtures.fake_stellarium_server import FakeStellariumServer


def _get(url: str):
    with urllib.request.urlopen(url, timeout=3) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def _post(url: str, payload: dict):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=3) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


class TestGravitationalWavesRegistry(unittest.TestCase):
    def setUp(self):
        gw.reload_registry()

    def test_list_events_and_classifications(self):
        payload = gw.list_payload()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["id"], "gravitational_waves")
        self.assertFalse(payload["audio_autoplay"])
        ids = {e["id"] for e in payload["events"]}
        self.assertIn("gw150914", ids)
        self.assertIn("gw170817", ids)
        self.assertEqual(payload["chirp_lab"]["classification"], "sonification")
        self.assertIn("NOT original detector-band", payload["chirp_lab"]["audio_label"])

    def test_wave_plus_cross(self):
        plus = gw.wave_state(polarization="plus", phase=0.5, amplitude=0.3)
        cross = gw.wave_state(polarization="cross", phase=0.5, amplitude=0.3)
        self.assertTrue(plus["ok"])
        self.assertTrue(cross["ok"])
        self.assertTrue(plus["exaggerated"])
        self.assertEqual(plus["classification"], "illustration")
        self.assertNotEqual(plus["points"][0], cross["points"][0])

    def test_interferometer_and_chirp(self):
        ifo = gw.interferometer_state(progress=1.0)
        self.assertTrue(ifo["ok"])
        self.assertEqual(ifo["classification"], "illustration")
        chirp = gw.chirp_state(progress=0.85)
        self.assertTrue(chirp["ok"])
        self.assertFalse(chirp["is_detector_band_audio"])
        self.assertFalse(chirp["is_space_sound"])
        self.assertTrue(chirp["is_frequency_shifted_representation"])

    def test_network(self):
        net = gw.network_payload()
        self.assertGreaterEqual(len(net["detectors"]), 3)

    def test_gw150914_no_fake_host(self):
        meta = gw.focus_request("gw150914")
        self.assertEqual(meta["stellarium_match_mode"], "unavailable")
        result = gw.apply_focus(None, "gw150914")
        self.assertTrue(result["ok"])
        self.assertFalse(result["focused"])

    def test_narration(self):
        for key in ("spacetime", "chirp", "gw150914", "gw170817", "closing"):
            payload = gw.narration_segment(key)
            self.assertTrue(payload["ok"], key)
            self.assertFalse(payload["audio_autoplay"])


class TestGravitationalWavesApi(unittest.TestCase):
    def setUp(self):
        gw.reload_registry()
        exhibit.reload_registry()
        exhibit.reset_session()
        self.fake = FakeStellariumServer()
        self.fake.start()
        self.httpd = run_server(host="127.0.0.1", port=0, stellarium_base_url=self.fake.base_url)
        self.base = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        import threading

        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=2)
        self.fake.stop()
        exhibit.reset_session()

    def test_routes_and_exhibit(self):
        status, body = _get(f"{self.base}/api/gravitational-waves")
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        status, body = _get(f"{self.base}/api/gravitational-waves/wave?polarization=cross&phase=1")
        self.assertEqual(status, 200)
        status, body = _get(f"{self.base}/api/gravitational-waves/chirp?progress=0.5")
        self.assertEqual(body["classification"], "sonification")
        status, body = _get(f"{self.base}/api/exhibits")
        ids = {ex["id"] for ex in body["exhibits"]}
        self.assertIn("gravitational_waves", ids)
        self.assertIn("light_echoes", ids)
        self.assertIn("cosmic_web", ids)
        status, body = _get(f"{self.base}/api/exhibit/gravitational_waves")
        self.assertTrue(body["ok"])
        types = [s["step_type"] for s in body["exhibit"]["steps"]]
        self.assertIn("gravitational_waves", types)

    def test_focus_gw170817_coordinate_host(self):
        # Fake returns whatever is in objects_info; set catalog + body
        self.fake.focus_catalog["ngc 4993"] = {
            "name": "",
            "localized-name": "",
            "type": "galaxy",
            "object-type": "galaxy",
            "ra": "13h09m47s",
            "dec": "-23d23m02s",
        }
        # Also need get_selection to parse dec — stellarium client extracts from fake body
        from tests.fixtures.fake_stellarium_server import canned_json

        self.fake.objects_info_body = canned_json(
            {
                "name": "",
                "type": "galaxy",
                "ra": 196.0,
                "dec": -23.4,
            }
        )
        status, body = _post(
            f"{self.base}/api/gravitational-waves/focus",
            {"event_id": "gw170817"},
        )
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        # focused may be true via coordinate hint if client exposes dec_deg
        self.assertIn("message", body)

    def test_focus_gw150914_unavailable(self):
        status, body = _post(
            f"{self.base}/api/gravitational-waves/focus",
            {"event_id": "gw150914"},
        )
        self.assertEqual(status, 200)
        self.assertFalse(body.get("focused"))
        blob = ((body.get("message") or "") + " " + (body.get("stellarium_note") or "")).lower()
        self.assertTrue("host" in blob or "localization" in blob or "precise" in blob or "unique" in blob)



if __name__ == "__main__":
    unittest.main()
