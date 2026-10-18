"""Cosmic Web registry, structure state, classification, API, and Stellarium tests."""

from __future__ import annotations

import json
import unittest
import urllib.error
import urllib.request

from app import cosmic_web
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


class TestCosmicWebRegistry(unittest.TestCase):
    def setUp(self):
        cosmic_web.reload_registry()

    def test_list_and_classifications(self):
        payload = cosmic_web.list_payload()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["id"], "cosmic_web")
        self.assertFalse(payload["audio_autoplay"])
        self.assertGreaterEqual(len(payload["objects"]), 4)
        classes = {o.get("media_classification") for o in payload["objects"]}
        self.assertTrue({"observation", "reconstruction", "simulation"} & classes)
        self.assertIn("illustration", payload["classification_legend"])

    def test_structure_is_illustrative(self):
        state = cosmic_web.structure_state(progress=1.0)
        self.assertTrue(state["ok"])
        self.assertEqual(state["kind"], "illustrative")
        self.assertEqual(state["classification"], "illustration")
        self.assertFalse(state["measured_reconstruction"])
        self.assertIn("ILLUSTRATIVE", (state.get("label") or "").upper())

    def test_layer_overrides(self):
        state = cosmic_web.structure_state(
            step_id="t4",
            layers={"galaxies": True, "filaments": False, "nodes": True, "voids": False},
        )
        self.assertTrue(state["ok"])
        self.assertTrue(state["layers"]["galaxies"])
        self.assertFalse(state["layers"]["filaments"])
        self.assertTrue(state["layers"]["nodes"])
        self.assertFalse(state["layers"]["voids"])

    def test_object_media_classification_required(self):
        obj = cosmic_web.object_payload("sim_structure")
        self.assertTrue(obj["ok"])
        self.assertEqual(obj["object"]["media"]["classification"], "simulation")

    def test_narration_segments(self):
        for key in (
            "intro",
            "fluctuations",
            "gravity",
            "filaments",
            "voids",
            "surveys",
            "night_sky",
            "closing",
        ):
            payload = cosmic_web.narration_segment(key)
            self.assertTrue(payload["ok"], key)
            self.assertFalse(payload["audio_autoplay"])

    def test_focus_without_client(self):
        result = cosmic_web.apply_focus(None, "coma_cluster")
        self.assertTrue(result["ok"])
        self.assertFalse(result["focused"])


class TestCosmicWebApi(unittest.TestCase):
    def setUp(self):
        cosmic_web.reload_registry()
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

    def test_routes(self):
        status, body = _get(f"{self.base}/api/cosmic-web")
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        status, body = _get(f"{self.base}/api/cosmic-web/structure?progress=0.75&layer_voids=0")
        self.assertEqual(status, 200)
        self.assertEqual(body["classification"], "illustration")
        self.assertFalse(body["layers"]["voids"])
        status, body = _get(f"{self.base}/api/cosmic-web/object/coma_cluster")
        self.assertEqual(status, 200)
        status, body = _get(f"{self.base}/api/cosmic-web/narration?segment=gravity")
        self.assertEqual(status, 200)
        self.assertIn("dark matter", body["text"].lower())

    def test_exhibit_registered(self):
        status, body = _get(f"{self.base}/api/exhibits")
        self.assertEqual(status, 200)
        ids = {ex["id"] for ex in body.get("exhibits") or []}
        self.assertIn("cosmic_web", ids)
        self.assertIn("light_echoes", ids)
        status, body = _get(f"{self.base}/api/exhibit/cosmic_web")
        self.assertTrue(body["ok"])
        types = [s["step_type"] for s in body["exhibit"]["steps"]]
        self.assertEqual(types[0], "intro")
        self.assertEqual(types[-1], "outro")
        self.assertIn("cosmic_web", types)

    def test_focus_coma(self):
        self.fake.focus_catalog["coma cluster"] = {
            "name": "Coma Cluster",
            "localized-name": "Coma Cluster",
            "type": "galaxy cluster",
            "ra": "12h59m48s",
            "dec": "+27d58m50s",
        }
        status, body = _post(f"{self.base}/api/cosmic-web/focus", {"object_id": "coma_cluster"})
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertTrue(body.get("focus_posted") or body.get("focused") or "message" in body)


if __name__ == "__main__":
    unittest.main()
