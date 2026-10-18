"""Cosmic Dawn registry, labs, objects, API, and Stellarium tests."""

from __future__ import annotations

import json
import unittest
import urllib.request

from app import cosmic_dawn as cd
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


class TestCosmicDawnRegistry(unittest.TestCase):
    def setUp(self):
        cd.reload_registry()

    def test_list_and_classifications(self):
        payload = cd.list_payload()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["id"], "cosmic_dawn")
        self.assertFalse(payload["audio_autoplay"])
        ids = {o["id"] for o in payload["objects"]}
        self.assertTrue({"planck_cmb", "hubble_udf", "jwst_pandora", "first_stars_sim"} <= ids)
        self.assertIn("reconstruction", payload["classification_legend"])
        self.assertIn("theoretical_model", payload["classification_legend"])

    def test_timeline_epochs(self):
        early = cd.timeline_state(progress=0.1)
        late = cd.timeline_state(progress=0.9)
        self.assertTrue(early["ok"] and late["ok"])
        self.assertTrue(early["approximate"])
        self.assertIn("ILLUSTRATIVE", early["label"])
        self.assertNotEqual(early["epoch"]["id"], late["epoch"]["id"])

    def test_redshift_not_doppler_only(self):
        rz = cd.redshift_state(z=8)
        self.assertTrue(rz["ok"])
        self.assertTrue(rz["not_ordinary_doppler_only"])
        self.assertLess(rz["scale_factor_teaching"], 1.0)

    def test_reionization_and_structure(self):
        reion = cd.reionization_state(progress=0.8)
        self.assertTrue(reion["ok"])
        self.assertTrue(reion["active_research"])
        self.assertIn("ILLUSTRATIVE", reion["label"])
        struct = cd.structure_state(progress=0.7)
        self.assertEqual(struct["related_special"], "cosmic_web")

    def test_21cm_conservative(self):
        block = cd.twenty_one_cm_payload()
        self.assertTrue(block["conservative"])
        self.assertFalse(block["detection_overstated"])
        blob = (block.get("disclaimer") or "").lower()
        self.assertIn("foreground", blob)

    def test_media_classifications(self):
        self.assertEqual(cd.object_by_id("planck_cmb")["media"]["classification"], "reconstruction")
        self.assertEqual(cd.object_by_id("hubble_udf")["media"]["classification"], "observation")
        self.assertEqual(cd.object_by_id("jwst_pandora")["media"]["classification"], "observation")
        self.assertEqual(cd.object_by_id("first_stars_sim")["media"]["classification"], "simulation")

    def test_cmb_stellarium_unavailable(self):
        meta = cd.focus_request("planck_cmb")
        self.assertEqual(meta["stellarium_match_mode"], "unavailable")
        self.assertFalse(meta["stellarium_shows_early_universe"])
        result = cd.apply_focus(None, "planck_cmb")
        self.assertTrue(result["ok"])
        self.assertFalse(result["focused"])

    def test_first_stars_uncertainty_language(self):
        science = cd.list_payload()["science"]["first_stars"].lower()
        self.assertIn("uncertain", science)

    def test_narration(self):
        for key in ("lookback", "cmb", "dark_ages", "jwst", "twenty_one_cm", "closing"):
            payload = cd.narration_segment(key)
            self.assertTrue(payload["ok"], key)
            self.assertFalse(payload["audio_autoplay"])


class TestCosmicDawnApi(unittest.TestCase):
    def setUp(self):
        cd.reload_registry()
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
        status, body = _get(f"{self.base}/api/cosmic-dawn")
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        status, body = _get(f"{self.base}/api/cosmic-dawn/timeline?progress=0.5")
        self.assertIn("ILLUSTRATIVE", body["label"])
        status, body = _get(f"{self.base}/api/exhibits")
        ids = {ex["id"] for ex in body["exhibits"]}
        for needed in (
            "cosmic_dawn",
            "galactic_encounters",
            "black_holes",
            "gravitational_waves",
            "cosmic_web",
            "light_echoes",
        ):
            self.assertIn(needed, ids)
        status, body = _get(f"{self.base}/api/exhibit/cosmic_dawn")
        self.assertTrue(body["ok"])
        self.assertGreaterEqual(len(body["exhibit"]["steps"]), 12)

    def test_focus_cmb_unavailable_and_others(self):
        status, body = _post(f"{self.base}/api/cosmic-dawn/focus", {"object_id": "planck_cmb"})
        self.assertEqual(status, 200)
        self.assertEqual(body.get("stellarium_match_mode"), "unavailable")
        self.assertFalse(body.get("focused"))
        for oid in ("hubble_udf", "jwst_pandora", "first_stars_sim"):
            status, body = _post(f"{self.base}/api/cosmic-dawn/focus", {"object_id": oid})
            self.assertEqual(status, 200, oid)
            self.assertIn(body.get("stellarium_match_mode"), ("exact", "host_sky"))
