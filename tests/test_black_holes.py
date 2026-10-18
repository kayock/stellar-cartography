"""Black Holes registry, labs, objects, API, and Stellarium tests."""

from __future__ import annotations

import json
import unittest
import urllib.request

from app import black_holes as bh
from app import exhibit
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


class TestBlackHolesRegistry(unittest.TestCase):
    def setUp(self):
        bh.reload_registry()

    def test_list_and_classifications(self):
        payload = bh.list_payload()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["id"], "black_holes")
        self.assertFalse(payload["audio_autoplay"])
        ids = {o["id"] for o in payload["objects"]}
        self.assertIn("sgr_a", ids)
        self.assertIn("m87", ids)
        self.assertIn("cygnus_x1", ids)
        self.assertIn("reconstruction", payload["classification_legend"])
        self.assertIn("theoretical_model", payload["classification_legend"])

    def test_scale_schwarzschild(self):
        ten = bh.scale_state(example_id="stellar_10")
        self.assertTrue(ten["ok"])
        self.assertEqual(ten["assumption"], "non_rotating_schwarzschild")
        self.assertAlmostEqual(ten["schwarzschild_radius_km"], 29.532, places=2)
        self.assertIn("SCHWARZSCHILD", ten.get("label") or "")
        huge = bh.scale_state(example_id="m87_mass")
        self.assertGreater(huge["schwarzschild_radius_km"], ten["schwarzschild_radius_km"])

    def test_approach_and_lensing(self):
        approach = bh.approach_state(region_id="photon")
        self.assertTrue(approach["ok"])
        self.assertEqual(approach["region"]["id"], "photon")
        self.assertIn("not a solid", (approach["region"]["caption"] + approach["disclaimer"]).lower())
        lens = bh.lensing_state(strength=0.8)
        self.assertTrue(lens["ok"])
        self.assertTrue(lens["exaggerated"])
        self.assertIn("ILLUSTRATIVE", lens["label"])
        self.assertGreater(len(lens["stars"]), 10)

    def test_tidal_smbh_weaker(self):
        stellar = bh.tidal_state("stellar")
        smbh = bh.tidal_state("smbh")
        self.assertTrue(stellar["ok"] and smbh["ok"])
        self.assertGreater(stellar["relative_horizon_tide_vs_stellar"], smbh["relative_horizon_tide_vs_stellar"])

    def test_eht_media_classification(self):
        for oid in ("sgr_a", "m87"):
            obj = bh.object_by_id(oid)
            self.assertEqual(obj["media"]["classification"], "reconstruction")
        cyg = bh.object_by_id("cygnus_x1")
        self.assertEqual(cyg["media"]["classification"], "observation")

    def test_sgr_a_host_sky_not_fake(self):
        meta = bh.focus_request("sgr_a")
        self.assertEqual(meta["stellarium_match_mode"], "host_sky")
        self.assertEqual(meta["stellarium_search"], "NGC 6522")
        note = (meta.get("stellarium_note") or "").lower()
        self.assertIn("not", note)
        result = bh.apply_focus(None, "sgr_a")
        self.assertTrue(result["ok"])
        self.assertFalse(result["focused"])

    def test_narration(self):
        for key in ("what_is", "horizon", "sgr_a", "m87", "closing"):
            payload = bh.narration_segment(key)
            self.assertTrue(payload["ok"], key)
            self.assertFalse(payload["audio_autoplay"])


class TestBlackHolesApi(unittest.TestCase):
    def setUp(self):
        bh.reload_registry()
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
        status, body = _get(f"{self.base}/api/black-holes")
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        status, body = _get(f"{self.base}/api/black-holes/scale?example_id=stellar_10")
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        status, body = _get(f"{self.base}/api/black-holes/lensing?strength=0.5")
        self.assertIn("ILLUSTRATIVE", body["label"])
        status, body = _get(f"{self.base}/api/exhibits")
        ids = {ex["id"] for ex in body["exhibits"]}
        self.assertIn("black_holes", ids)
        self.assertIn("gravitational_waves", ids)
        self.assertIn("light_echoes", ids)
        self.assertIn("cosmic_web", ids)
        status, body = _get(f"{self.base}/api/exhibit/black_holes")
        self.assertTrue(body["ok"])
        types = [s["step_type"] for s in body["exhibit"]["steps"]]
        self.assertIn("black_holes", types)
        self.assertGreaterEqual(len(body["exhibit"]["steps"]), 12)

    def test_focus_m87_and_cygnus(self):
        status, body = _post(f"{self.base}/api/black-holes/focus", {"object_id": "m87"})
        self.assertEqual(status, 200)
        self.assertEqual(body.get("stellarium_match_mode"), "exact")
        self.assertTrue(body.get("focused") or body.get("focus_posted"))
        status, body = _post(f"{self.base}/api/black-holes/focus", {"object_id": "cygnus_x1"})
        self.assertEqual(status, 200)
        self.assertEqual(body.get("stellarium_search"), "HD 226868")

    def test_focus_sgr_host_sky(self):
        status, body = _post(f"{self.base}/api/black-holes/focus", {"object_id": "sgr_a"})
        self.assertEqual(status, 200)
        self.assertEqual(body.get("stellarium_match_mode"), "host_sky")
        self.assertEqual(body.get("stellarium_search"), "NGC 6522")
