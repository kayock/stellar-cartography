"""Constellation Story Deck tests."""

from __future__ import annotations

import json
import threading
import unittest

from app import constellation_story
from app import cosmic_signal_registry
from app import experience
from app.server import run_server
from app.stellarium_client import StellariumClient
from tests.fixtures.fake_stellarium_server import FakeStellariumServer, canned_json


def _selection(name="Betelgeuse", constellation="Ori", alt="Betelgeuse", designations=None):
    return {
        "ok": True,
        "connected": True,
        "name": name,
        "alt_name": alt,
        "constellation": constellation,
        "catalogue_designations": designations,
        "object_type": "star",
        "ra_deg": 88.79,
        "dec_deg": 7.4,
        "ra_sexagesimal": "05h55m10s",
        "dec_sexagesimal": "+07d24m25s",
    }


def _info(name, localized, iau, **extra):
    payload = {
        "name": name,
        "localized-name": localized,
        "type": extra.get("type", "Star"),
        "object-type": extra.get("object_type", "star"),
        "raJ2000": extra.get("ra", 88.79),
        "decJ2000": extra.get("dec", 7.4),
        "iauConstellation": iau,
    }
    if extra.get("designations"):
        payload["designations"] = extra["designations"]
    return payload


def _get(url):
    import urllib.request

    with urllib.request.urlopen(url, timeout=3) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def _get_status(url):
    import urllib.error
    import urllib.request

    try:
        with urllib.request.urlopen(url, timeout=3) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        exc.close()
        return exc.code, json.loads(body) if body else {}


def _post(url, payload):
    import urllib.request

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=3) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def _post_expect_status(url, payload):
    import urllib.error
    import urllib.request

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        return exc.code, json.loads(body) if body else {}


class TestConstellationModel(unittest.TestCase):
    def test_registry_keeps_original_modern_stories(self):
        listing = constellation_story.list_constellations("modern")
        ids = [c["id"] for c in listing["constellations"]]
        for expected in ("orion", "ursa_major", "cassiopeia", "scorpius", "sagittarius"):
            self.assertIn(expected, ids)
        self.assertGreaterEqual(len(ids), 17)

    def test_story_order_is_deterministic(self):
        story = constellation_story.get_story("orion")
        self.assertEqual(
            story["story_order"],
            ["orion", "betelgeuse", "rigel", "alnilam", "orion_nebula"],
        )
        steps = constellation_story.story_steps(story)
        self.assertEqual([s["object_id"] for s in steps], story["story_order"])

    def test_detects_orion_from_iau_abbreviation(self):
        detected = constellation_story.detect_constellation(_selection())
        self.assertTrue(detected["control_visible"])
        self.assertEqual(detected["story_id"], "orion")
        self.assertEqual(detected["iau_abbreviation"], "Ori")

    def test_detects_orion_from_constellation_name(self):
        detected = constellation_story.detect_constellation(
            {"name": "Orion", "object_type": "constellation"}
        )
        self.assertEqual(detected["story_id"], "orion")

    def test_missing_constellation_hides_control(self):
        detected = constellation_story.detect_constellation({"name": "Mars", "ok": True})
        self.assertFalse(detected["control_visible"])
        self.assertIn("no constellation context", detected["empty_reason"].lower())

    def test_andromeda_now_has_a_modern_story(self):
        detected = constellation_story.detect_constellation(_selection("M 31", "And", "Andromeda Galaxy"))
        self.assertTrue(detected["detected"])
        self.assertEqual(detected["story_id"], "andromeda")

    def test_unknown_iau_constellation_disables_story(self):
        detected = constellation_story.detect_constellation(_selection("Nu Horologii", "Hor", "Nu Horologii"))
        self.assertTrue(detected["detected"])
        self.assertFalse(detected["story_available"])
        self.assertFalse(detected["control_visible"])

    def test_malformed_constellation_id(self):
        result = constellation_story.story_payload("../etc/passwd")
        self.assertFalse(result["ok"])
        self.assertIn("Malformed", result["error"])

    def test_unknown_constellation_id(self):
        result = constellation_story.story_payload("not_a_real_story")
        self.assertFalse(result["ok"])
        self.assertIn("Unknown", result["error"])


class TestSignalAndMediaMatching(unittest.TestCase):
    def test_does_not_create_second_signal_registry(self):
        self.assertEqual(len(cosmic_signal_registry.enabled_entries()), 21)
        cass = constellation_story.match_signals_for_constellation(
            constellation_story.get_story("cassiopeia")
        )
        self.assertEqual(cass["registry"], "cosmic_signal_registry")
        self.assertTrue(any(e["id"] == "cassiopeia_a_chandra_sonification" for e in cass["exact"]))
        self.assertFalse(cass["audio_autoplay"])

    def test_exact_related_general_labels(self):
        story = constellation_story.get_story("cassiopeia")
        overview = constellation_story.match_signals_for_constellation(story)
        exact_ids = {e["id"] for e in overview["exact"]}
        self.assertIn("cassiopeia_a_chandra_sonification", exact_ids)
        related = constellation_story.match_signals_for_constellation(
            story, {"name": "Schedar", "alt_name": "Schedar"}
        )
        self.assertTrue(related["related"])
        self.assertEqual(related["related"][0]["relation_label"], "Related")
        self.assertNotIn("cassiopeia_a_chandra_sonification", {e["id"] for e in related["exact"]})
        self.assertNotIn(
            "galactic_center_chandra_sonification",
            {e["id"] for e in related["related"] + related["exact"] + related["general"]},
        )

    def test_orion_has_no_overclaimed_exact_signal(self):
        signals = constellation_story.match_signals_for_constellation(
            constellation_story.get_story("orion")
        )
        self.assertEqual(signals["exact"], [])

    def test_cassiopeia_spectra_reuse_gallery(self):
        spectra = constellation_story.match_spectra_for_constellation(
            constellation_story.get_story("cassiopeia")
        )
        self.assertEqual(spectra["registry"], "spectrum_gallery_registry")
        self.assertTrue(spectra["exact"])
        self.assertTrue(any("casa" in e["id"] for e in spectra["exact"]))

    def test_constellation_media_empty_is_graceful(self):
        media = constellation_story.match_media_for_constellation(constellation_story.get_story("orion"))
        self.assertTrue(media["empty"])
        self.assertEqual(media["registry"], "solar_system_media_registry")


class TestTourStateMachine(unittest.TestCase):
    def setUp(self):
        constellation_story.reset_tour()

    def tearDown(self):
        constellation_story.reset_tour()

    def test_start_next_previous_stop_and_restore(self):
        original = _selection()
        started = constellation_story.start_tour("orion", original)
        self.assertTrue(started["ok"])
        self.assertEqual(started["step_index"], 0)
        self.assertEqual(started["step"]["search_name"], "Orion")
        self.assertFalse(started["audio_autoplay"])
        nxt = constellation_story.step_tour("next")
        self.assertEqual(nxt["step"]["object_id"], "betelgeuse")
        nxt2 = constellation_story.step_tour("next")
        self.assertEqual(nxt2["step"]["object_id"], "rigel")
        prev = constellation_story.step_tour("prev")
        self.assertEqual(prev["step"]["object_id"], "betelgeuse")
        stopped = constellation_story.stop_tour()
        self.assertFalse(stopped["active"])
        self.assertEqual(stopped["restore_search_name"], "Betelgeuse")
        self.assertFalse(constellation_story.tour_status()["active"])

    def test_story_order_bounds(self):
        constellation_story.start_tour("orion", _selection())
        first = constellation_story.step_tour("prev")
        self.assertEqual(first["step_index"], 0)
        self.assertTrue(first.get("bounded"))
        story = constellation_story.get_story("orion")
        for _ in story["story_order"]:
            constellation_story.step_tour("next")
        last = constellation_story.step_tour("next")
        self.assertEqual(last["step_index"], len(story["story_order"]) - 1)

    def test_no_autoplay_flag_on_every_step(self):
        constellation_story.start_tour("orion", _selection())
        for _ in range(3):
            result = constellation_story.step_tour("next")
            self.assertFalse(result["audio_autoplay"])


class TestSkyCultureAndNarration(unittest.TestCase):
    def test_sky_culture_fallback_when_live_differs(self):
        payload = constellation_story.story_payload("orion", sky_culture_live="navajo")
        self.assertTrue(payload["ok"])
        self.assertFalse(payload["sky_culture_synchronized"])
        self.assertEqual(payload["sky_culture"], "modern")
        self.assertEqual(payload["sky_culture_live"], "navajo")

    def test_sky_culture_sync_when_live_matches(self):
        payload = constellation_story.story_payload("orion", sky_culture_live="modern")
        self.assertTrue(payload["sky_culture_synchronized"])

    def test_narration_kinds(self):
        story = constellation_story.get_story("orion")
        overview = experience.narration_payload(_selection(), {}, kind="constellation_overview", constellation=story)
        self.assertEqual(overview["kind"], "constellation_overview")
        self.assertIn("Orion", overview["title"])
        self.assertTrue(overview["listen_available"])
        tour = constellation_story.start_tour("orion", _selection())
        step = experience.narration_payload(
            _selection(),
            {},
            kind="tour_step",
            constellation=story,
            tour=tour,
        )
        self.assertEqual(step["kind"], "tour_step")
        self.assertIsNotNone(step["step_index"])
        transition = experience.narration_payload(
            _selection("Rigel", "Ori", "Rigel"),
            {},
            kind="object_transition",
            constellation=story,
            tour=constellation_story.step_tour("next"),
        )
        self.assertEqual(transition["kind"], "object_transition")
        constellation_story.reset_tour()

    def test_supported_and_unsupported_controls(self):
        payload = constellation_story.constellation_controls_payload(
            {
                "ConstellationMgr.linesDisplayed": {"value": True},
                "ConstellationMgr.namesDisplayed": {"value": False},
                "StelSkyCultureMgr.currentSkyCultureID": {"value": "modern"},
            }
        )
        self.assertTrue(payload["controls"]["lines"]["supported"])
        self.assertTrue(payload["controls"]["lines"]["value"])
        self.assertFalse(payload["controls"]["labels"]["value"])
        self.assertTrue(any(u["id"] == "select_constellation_by_object_type" for u in payload["unsupported"]))
        parsed = constellation_story.parse_control_request({"artwork": True, "isolate": False})
        self.assertTrue(parsed["ok"])
        self.assertEqual(len(parsed["updates"]), 2)


class TestStellariumClientFocus(unittest.TestCase):
    def test_focus_and_controls_use_remote_control(self):
        fake = FakeStellariumServer(objects_info_body=canned_json(_info("HIP 27989", "Betelgeuse", "Ori")))
        fake.focus_catalog = {
            "rigel": _info("HIP 24436", "Rigel", "Ori", ra=78.6, dec=-8.2),
        }
        fake.start()
        try:
            client = StellariumClient(base_url=fake.base_url)
            self.assertTrue(client.focus_object("Rigel"))
            self.assertEqual(fake.posted_focus["target"], "Rigel")
            result = client.get_selection()
            self.assertEqual(result.alt_name, "Rigel")
            self.assertTrue(client.set_fov(12))
            self.assertEqual(fake.posted_fov["fov"], "12.0000")
            self.assertEqual(client.get_sky_culture_id(), "modern")
            self.assertTrue(client.set_stel_property("ConstellationMgr.linesDisplayed", False))
            self.assertFalse(client.get_stel_properties()["ConstellationMgr.linesDisplayed"]["value"])
        finally:
            fake.stop()


class TestConstellationApi(unittest.TestCase):
    def setUp(self):
        constellation_story.reset_tour()
        fake = FakeStellariumServer(objects_info_body=canned_json(_info("HIP 27989", "Betelgeuse", "Ori")))
        fake.focus_catalog = {
            "orion": _info("Orion", "Orion", "Ori", type="Constellation", object_type="constellation", ra=86.0, dec=0.0),
            "betelgeuse": _info("HIP 27989", "Betelgeuse", "Ori"),
            "rigel": _info("HIP 24436", "Rigel", "Ori", ra=78.6, dec=-8.2),
            "alnilam": _info("HIP 26311", "Alnilam", "Ori", ra=84.0, dec=-1.2),
        }
        fake.start()
        self.fake = fake
        self.httpd = run_server(host="127.0.0.1", port=0, stellarium_base_url=fake.base_url)
        self.port = self.httpd.server_address[1]
        self.base = f"http://127.0.0.1:{self.port}"
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=2)
        self.fake.stop()
        constellation_story.reset_tour()

    def test_list_and_get_story(self):
        status, data = _get(f"{self.base}/api/constellations")
        self.assertEqual(status, 200)
        self.assertGreaterEqual(len(data["constellations"]), 17)
        modern = [c for c in data["constellations"] if c.get("culture_id") == "modern"]
        self.assertGreaterEqual(len(modern), 17)
        status, story = _get(f"{self.base}/api/constellation/orion")
        self.assertEqual(status, 200)
        self.assertEqual(story["canonical_name"], "Orion")
        self.assertFalse(story["audio_autoplay"])

    def test_context_from_live_selection(self):
        status, data = _get(f"{self.base}/api/constellation-context")
        self.assertTrue(data["context"]["story_available"])
        self.assertEqual(data["context"]["story_id"], "orion")

    def test_malformed_id_is_404(self):
        status, data = _get_status(f"{self.base}/api/constellation/..orion")
        self.assertEqual(status, 404)
        self.assertFalse(data.get("ok", True))
        self.assertIn("Malformed", data.get("error", ""))

    def test_unknown_id_is_404(self):
        status, data = _get_status(f"{self.base}/api/constellation/not-a-real-constellation")
        self.assertEqual(status, 404)
        self.assertFalse(data.get("ok", True))

    def test_tour_moves_stellarium_and_restores(self):
        status, started = _post(f"{self.base}/api/constellation-tour/start", {"id": "orion"})
        self.assertTrue(started["ok"])
        self.assertEqual(self.fake.posted_focus["target"], "Orion")
        self.assertFalse(started["audio_autoplay"])
        _post(f"{self.base}/api/constellation-tour/step", {"direction": "next"})
        self.assertEqual(self.fake.posted_focus["target"], "Betelgeuse")
        _post(f"{self.base}/api/constellation-tour/step", {"direction": "next"})
        self.assertEqual(self.fake.posted_focus["target"], "Rigel")
        status, stopped = _post(f"{self.base}/api/constellation-tour/stop", {})
        self.assertEqual(self.fake.posted_focus["target"], "Betelgeuse")
        self.assertFalse(stopped["active"])

    def test_controls_and_narration(self):
        status, controls = _get(f"{self.base}/api/constellation-controls")
        self.assertTrue(controls["controls"]["lines"]["supported"])
        _post(f"{self.base}/api/constellation-controls", {"lines": False, "isolate": True})
        self.assertFalse(self.fake.properties["ConstellationMgr.linesDisplayed"]["value"])
        self.assertTrue(self.fake.properties["ConstellationMgr.isolateSelected"]["value"])
        status, narration = _get(f"{self.base}/api/narration?kind=constellation_overview&constellation=orion")
        self.assertEqual(narration["kind"], "constellation_overview")
        self.assertTrue(narration["listen_available"])
        self.assertFalse(narration["audio_autoplay"])


if __name__ == "__main__":
    unittest.main()
