"""Galactic Encounters registry, labs, objects, API, and Stellarium tests."""

from __future__ import annotations

import json
import unittest
import urllib.request

from app import exhibit
from app import galactic_encounters as ge
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


class TestGalacticEncountersRegistry(unittest.TestCase):
    def setUp(self):
        ge.reload_registry()

    def test_list_and_classifications(self):
        payload = ge.list_payload()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["id"], "galactic_encounters")
        self.assertFalse(payload["audio_autoplay"])
        ids = {o["id"] for o in payload["objects"]}
        self.assertTrue({"antennae", "whirlpool", "mice", "mw_andromeda"} <= ids)
        self.assertIn("future_prediction", payload["classification_legend"])
        self.assertEqual(payload["future_mw_m31"]["classification"], "future_prediction")

    def test_encounter_stages(self):
        early = ge.encounter_state(progress=0.1)
        late = ge.encounter_state(progress=0.95)
        self.assertTrue(early["ok"] and late["ok"])
        self.assertIn("ILLUSTRATIVE", early["label"])
        self.assertLess(early["layout"]["tail_length"], late["layout"]["tail_length"])
        pro = ge.encounter_state(progress=0.6, orientation_id="prograde")
        ret = ge.encounter_state(progress=0.6, orientation_id="retrograde")
        self.assertGreaterEqual(pro["layout"]["stretch"], ret["layout"]["stretch"])

    def test_tidal_and_stars_gas(self):
        tidal = ge.tidal_state(strength=0.8)
        self.assertTrue(tidal["ok"])
        self.assertGreater(tidal["near_side_pull"], tidal["far_side_pull"])
        self.assertIn("not black-hole", (tidal.get("scale_note") or "").lower())
        stars = ge.stars_gas_state("stars")
        gas = ge.stars_gas_state("gas")
        self.assertFalse(stars["star_collision_likely"])
        self.assertTrue(gas["gas_interaction_strong"])

    def test_major_minor(self):
        major = ge.merger_state("major")
        minor = ge.merger_state("minor")
        self.assertIn("comparable", major["mode"]["caption"].lower())
        self.assertIn("smaller", minor["mode"]["caption"].lower())

    def test_mw_m31_future_label(self):
        fut = ge.future_payload()
        self.assertEqual(fut["classification"], "future_prediction")
        blob = (fut.get("disclaimer") or "").lower() + json.dumps(fut.get("points")).lower()
        self.assertIn("model", blob)
        obj = ge.object_by_id("mw_andromeda")
        self.assertEqual(obj["media"]["classification"], "future_prediction")

    def test_observations_classified(self):
        for oid in ("antennae", "whirlpool", "mice"):
            self.assertEqual(ge.object_by_id(oid)["media"]["classification"], "observation")

    def test_unavailable_stellarium(self):
        result = ge.apply_focus(None, "antennae")
        self.assertTrue(result["ok"])
        self.assertFalse(result["focused"])

    def test_narration(self):
        for key in ("motion", "tides", "antennae", "mw_m31", "closing"):
            payload = ge.narration_segment(key)
            self.assertTrue(payload["ok"], key)
            self.assertFalse(payload["audio_autoplay"])


class TestGalacticEncountersApi(unittest.TestCase):
    def setUp(self):
        ge.reload_registry()
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
        status, body = _get(f"{self.base}/api/galactic-encounters")
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        status, body = _get(f"{self.base}/api/galactic-encounters/encounter?progress=0.5")
        self.assertIn("ILLUSTRATIVE", body["label"])
        status, body = _get(f"{self.base}/api/exhibits")
        ids = {ex["id"] for ex in body["exhibits"]}
        self.assertIn("galactic_encounters", ids)
        self.assertIn("black_holes", ids)
        self.assertIn("gravitational_waves", ids)
        status, body = _get(f"{self.base}/api/exhibit/galactic_encounters")
        self.assertTrue(body["ok"])
        self.assertGreaterEqual(len(body["exhibit"]["steps"]), 12)
        types = [s["step_type"] for s in body["exhibit"]["steps"]]
        self.assertIn("galactic_encounters", types)

    def test_focus_routes(self):
        for oid in ("antennae", "whirlpool", "mice", "mw_andromeda"):
            status, body = _post(f"{self.base}/api/galactic-encounters/focus", {"object_id": oid})
            self.assertEqual(status, 200, oid)
            self.assertEqual(body.get("stellarium_match_mode"), "exact")
            self.assertTrue(body.get("focus_posted") or body.get("focused") is False)
