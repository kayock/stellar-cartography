"""Light Echoes registry, geometry state, API, and Stellarium-graceful tests."""

from __future__ import annotations

import json
import unittest
import urllib.error
import urllib.request

from app import light_echoes
from app.server import run_server
from tests.fixtures.fake_stellarium_server import FakeStellariumServer


def _get(url: str):
    with urllib.request.urlopen(url, timeout=3) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def _get_error(url: str):
    try:
        return _get(url)
    except urllib.error.HTTPError as exc:
        body = json.loads(exc.read().decode("utf-8"))
        return exc.code, body


def _post(url: str, payload: dict):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=3) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


class TestLightEchoesRegistry(unittest.TestCase):
    def setUp(self):
        light_echoes.reload_registry()

    def test_registry_loads_and_lists_objects(self):
        payload = light_echoes.list_payload()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["id"], "light_echoes")
        self.assertFalse(payload["audio_autoplay"])
        self.assertGreaterEqual(len(payload["objects"]), 3)
        ids = {o["id"] for o in payload["objects"]}
        self.assertIn("v838_mon", ids)
        self.assertIn("cas_a_echoes", ids)
        self.assertIn("sn_1987a", ids)

    def test_science_fields_present(self):
        sci = light_echoes.list_payload()["science"]
        for key in (
            "what_is",
            "not_matter_expansion",
            "geometry",
            "apparent_superluminal",
            "takeaway",
        ):
            self.assertTrue(sci.get(key))

    def test_geometry_is_illustrative(self):
        geo = light_echoes.geometry_state(progress=0.5)
        self.assertTrue(geo["ok"])
        self.assertEqual(geo["kind"], "illustrative")
        self.assertFalse(geo["measured_reconstruction"])
        self.assertIn("ILLUSTRATIVE", (geo.get("label") or "").upper())

    def test_geometry_step_id(self):
        geo = light_echoes.geometry_state(step_id="t3")
        self.assertTrue(geo["ok"])
        self.assertEqual(geo["step"]["id"], "t3")
        self.assertIn("far", geo["step"]["illuminated"])

    def test_object_provenance_hosts(self):
        obj = light_echoes.object_payload("v838_mon")
        self.assertTrue(obj["ok"])
        media = obj["object"]["media"]
        self.assertTrue(media["source_page_url"].startswith("https://"))
        self.assertTrue(media["image_url"].startswith("https://"))
        self.assertTrue(media.get("credit"))
        self.assertTrue(obj["object"]["sources"])

    def test_unknown_object(self):
        self.assertFalse(light_echoes.object_payload("not_real")["ok"])

    def test_narration_segments(self):
        for key in ("intro", "geometry", "apparent_expansion", "examples", "closing"):
            payload = light_echoes.narration_segment(key)
            self.assertTrue(payload["ok"], key)
            self.assertFalse(payload["audio_autoplay"])
            self.assertTrue(payload["listen_available"])
            self.assertTrue(payload["text"])

    def test_focus_without_client(self):
        result = light_echoes.apply_focus(None, "v838_mon")
        self.assertTrue(result["ok"])
        self.assertFalse(result["focused"])
        self.assertIn("unavailable", (result.get("message") or "").lower())


class TestLightEchoesApi(unittest.TestCase):
    def setUp(self):
        light_echoes.reload_registry()
        from app import exhibit

        exhibit.reload_registry()
        exhibit.reset_session()
        self.fake = FakeStellariumServer()
        self.fake.start()
        self.httpd = run_server(host="127.0.0.1", port=0, stellarium_base_url=self.fake.base_url)
        self.port = self.httpd.server_address[1]
        self.base = f"http://127.0.0.1:{self.port}"
        import threading

        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=2)
        self.fake.stop()
        from app import exhibit

        exhibit.reset_session()

    def test_list_route(self):
        status, body = _get(f"{self.base}/api/light-echoes")
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertGreaterEqual(len(body["objects"]), 3)

    def test_object_route(self):
        status, body = _get(f"{self.base}/api/light-echoes/object/v838_mon")
        self.assertEqual(status, 200)
        self.assertEqual(body["object"]["stellarium_search"], "Monoceros")
        self.assertEqual(body["object"].get("stellarium_match_mode"), "host_sky")

    def test_geometry_route(self):
        status, body = _get(f"{self.base}/api/light-echoes/geometry?progress=1")
        self.assertEqual(status, 200)
        self.assertEqual(body["kind"], "illustrative")

    def test_narration_route(self):
        status, body = _get(f"{self.base}/api/light-echoes/narration?segment=intro")
        self.assertEqual(status, 200)
        self.assertTrue(body["listen_available"])
        self.assertFalse(body["audio_autoplay"])

    def test_focus_route_with_fake_stellarium(self):
        self.fake.focus_catalog["cassiopeia a"] = {
            "name": "Cassiopeia A",
            "localized-name": "Cassiopeia A",
            "type": "supernova remnant",
            "ra": "23h23m26s",
            "dec": "+58d48m54s",
        }
        status, body = _post(f"{self.base}/api/light-echoes/focus", {"object_id": "cas_a_echoes"})
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertTrue(body.get("focus_posted") or body.get("focused") or "message" in body)

    def test_focus_graceful_without_match(self):
        status, body = _post(f"{self.base}/api/light-echoes/focus", {"object_id": "v838_mon"})
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertIn("message", body)

    def test_exhibit_lists_light_echoes(self):
        status, body = _get(f"{self.base}/api/exhibits")
        self.assertEqual(status, 200)
        ids = {ex["id"] for ex in body.get("exhibits") or []}
        self.assertIn("light_echoes", ids)

    def test_exhibit_payload(self):
        status, body = _get(f"{self.base}/api/exhibit/light_echoes")
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        types = [s["step_type"] for s in body["exhibit"]["steps"]]
        self.assertEqual(types[0], "intro")
        self.assertEqual(types[-1], "outro")
        self.assertIn("light_echo", types)


if __name__ == "__main__":
    unittest.main()
