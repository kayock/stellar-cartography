"""Targeted tests for the Sky Time Machine and experience helpers."""

from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone

from app import experience
from app.server import run_server
from tests.fixtures.fake_stellarium_server import FakeStellariumServer, canned_json, load_sample


def _post(url: str, payload: dict):
    import urllib.request

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=3) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def _get(url: str):
    import urllib.request

    with urllib.request.urlopen(url, timeout=3) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


class TestTimeMachineValidation(unittest.TestCase):
    def test_rejects_silent_empty_apply(self):
        result = experience.validate_time_machine_request({})
        self.assertFalse(result["ok"])

    def test_rejects_bad_latitude(self):
        result = experience.validate_time_machine_request(
            {"apply_location": True, "latitude": 120, "longitude": 0}
        )
        self.assertFalse(result["ok"])
        self.assertIn("latitude", result["error"].lower())

    def test_now_preset_maps_to_current_clock(self):
        now = datetime(2026, 10, 10, 18, 0, tzinfo=timezone.utc)
        result = experience.validate_time_machine_request({"apply_time": True, "preset": "now"}, now=now)
        self.assertTrue(result["ok"])
        self.assertEqual(result["utc"], "2026-10-10T18:00:00Z")
        self.assertAlmostEqual(result["jday"], experience.utc_to_jd(now), places=6)

    def test_year_ago_preset(self):
        now = datetime(2026, 10, 10, 18, 0, tzinfo=timezone.utc)
        result = experience.validate_time_machine_request({"apply_time": True, "preset": "year_ago"}, now=now)
        self.assertTrue(result["ok"])
        self.assertEqual(result["utc"], "2025-10-10T18:00:00Z")

    def test_explicit_iso_time(self):
        result = experience.validate_time_machine_request(
            {"apply_time": True, "utc": "2000-01-01T12:00:00Z"}
        )
        self.assertTrue(result["ok"])
        self.assertAlmostEqual(result["jday"], 2451545.0, places=5)

    def test_rejects_non_earth_planet(self):
        result = experience.validate_time_machine_request(
            {"apply_location": True, "latitude": 10, "longitude": 10, "planet": "Mars"}
        )
        self.assertFalse(result["ok"])

    def test_command_mapping(self):
        validated = experience.validate_time_machine_request(
            {
                "apply_time": True,
                "apply_location": True,
                "utc": "2000-01-01T12:00:00Z",
                "latitude": 39.1,
                "longitude": -104.8,
                "name": "Monument",
            }
        )
        time_params = experience.stellarium_time_params(validated)
        loc_params = experience.stellarium_location_params(validated)
        self.assertEqual(time_params["timerate"], "0")
        self.assertIn("2451545", time_params["time"])
        self.assertEqual(loc_params["planet"], "Earth")
        self.assertEqual(loc_params["name"], "Monument")


class TestObjectCardAndPostcard(unittest.TestCase):
    def test_card_omits_missing_fields(self):
        card = experience.build_object_card({"ok": True, "name": "NotARealObjectXYZ", "object_type": "planet"})
        labels = [f["label"] for f in card["fields"]]
        self.assertIn("Name", labels)
        self.assertNotIn("Magnitude", labels)
        self.assertEqual(card["family"], "planet")
        self.assertEqual(card["media"], [])

    def test_unknown_target_has_no_media_hint(self):
        self.assertEqual(experience.local_media_hints({"name": "NotARealObjectXYZ"}), [])

    def test_satellite_family(self):
        card = experience.build_object_card({"ok": True, "name": "STARLINK-1", "object_type": "artificial satellite"})
        self.assertEqual(card["family"], "satellite")

    def test_postcard_without_screenshot(self):
        meta = experience.postcard_metadata(
            {"ok": True, "name": "Mars", "ra_deg": 1.0, "dec_deg": 2.0},
            {"utc": "2026-01-01T00:00:00Z", "location_name": "Monument", "fov_deg": 60},
        )
        self.assertTrue(meta["ok"])
        self.assertFalse(meta["screenshot"]["available"])
        self.assertEqual(meta["selection"]["name"], "Mars")


class TestCompareMotionSonify(unittest.TestCase):
    def test_compare_delta(self):
        result = experience.compare_snapshots(
            {"selection": {"altitude_deg": 10, "name": "Mars"}, "sky": {"utc": "2020-01-01T00:00:00Z"}},
            {"selection": {"altitude_deg": 20, "name": "Mars"}, "sky": {"utc": "2020-01-02T00:00:00Z"}},
        )
        alt = next(row for row in result["rows"] if row["field"].startswith("Altitude"))
        self.assertTrue(alt["changed"])
        self.assertAlmostEqual(alt["delta"], 10.0)

    def test_motion_requires_coords(self):
        track = experience.motion_track({"name": "x"}, {})
        self.assertFalse(track["available"])

    def test_motion_and_sonify_from_radec(self):
        selection = {"ok": True, "name": "Sirius", "object_type": "star", "ra_deg": 101.287, "dec_deg": -16.716}
        sky = {"latitude": 39.1, "longitude": -104.85, "utc": "2026-10-10T04:00:00Z"}
        track = experience.motion_track(selection, sky)
        self.assertTrue(track["available"])
        self.assertEqual(len(track["points"]), 3)
        plan = experience.sonify_plan(selection, sky)
        self.assertTrue(plan["available"])
        self.assertGreater(len(plan["samples"]), 8)
        self.assertIn("not the physical sound", plan["mapping"]["disclaimer"])

    def test_spectrum_empty(self):
        axis = experience.spectrum_axis([])
        self.assertFalse(axis["available"])

    def test_event_strip_is_foundation(self):
        strip = experience.event_strip_foundation({"utc": "2026-01-01T00:00:00Z"})
        self.assertFalse(strip["available"])
        self.assertEqual(strip["events"], [])

    def test_narration_not_wired(self):
        payload = experience.narration_payload({"name": "Mars", "object_type": "planet"}, {"utc": "2026-01-01T00:00:00Z"})
        self.assertTrue(payload["listen_available"])
        self.assertIn("Mars", payload["summary"])


class TestSkyStateEndpoint(unittest.TestCase):
    def setUp(self):
        status = canned_json(
            {
                "time": {
                    "utc": "2026-10-10T04:00:00",
                    "jday": 2460963.6666667,
                    "isTimeNow": True,
                    "timeZone": "UTC",
                },
                "location": {
                    "latitude": 39.1,
                    "longitude": -104.85,
                    "altitude": 1600,
                    "name": "Monument",
                    "planet": "Earth",
                },
                "view": {"fov": 5.2},
            }
        )
        info = load_sample("official_getinfo_shape_response.json")
        self.fake = FakeStellariumServer(objects_info_body=info, main_status_body=status)
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

    def test_sky_state_connected(self):
        status, data = _get(f"{self.base}/api/sky-state")
        self.assertEqual(status, 200)
        self.assertTrue(data["ok"])
        self.assertIn("sky", data)
        self.assertIn("selection", data)
        self.assertIn("card", data)
        self.assertIn("motion", data)
        self.assertIn("sonify", data)
        self.assertIn("events", data)
        self.assertFalse(data["events"]["available"])
        self.assertTrue(data["motion"]["available"])
        self.assertTrue(data["sonify"]["available"])
        self.assertEqual(data["sky"]["location_name"], "Monument")
        self.assertIsNone(self.fake.posted_time)

    def test_time_machine_validation_error(self):
        status, data = _post(f"{self.base}/api/time-machine", {})
        self.assertEqual(status, 200)
        self.assertFalse(data["ok"])

    def test_postcard_endpoint(self):
        status, data = _post(f"{self.base}/api/postcard", {})
        self.assertEqual(status, 200)
        self.assertTrue(data["ok"])
        self.assertFalse(data["screenshot"]["available"])

    def test_compare_endpoint(self):
        status, data = _post(
            f"{self.base}/api/compare",
            {
                "a": {"selection": {"altitude_deg": 1}, "sky": {"utc": "2020-01-01T00:00:00Z"}},
                "b": {"selection": {"altitude_deg": 2}, "sky": {"utc": "2020-01-02T00:00:00Z"}},
            },
        )
        self.assertTrue(data["ok"])
        self.assertTrue(any(row["changed"] for row in data["rows"]))

    def test_time_machine_maps_julian_day(self):
        status, data = _post(
            f"{self.base}/api/time-machine",
            {"apply_time": True, "utc": "2000-01-01T12:00:00Z"},
        )
        self.assertEqual(status, 200)
        self.assertTrue(data["ok"])
        self.assertIsNotNone(self.fake.posted_time)
        self.assertIn("2451545", self.fake.posted_time["time"])
        self.assertEqual(self.fake.posted_time["timerate"], "0")

    def test_time_machine_now_uses_supported_action(self):
        status, data = _post(f"{self.base}/api/time-machine", {"apply_time": True, "preset": "now"})
        self.assertTrue(data["ok"])
        self.assertEqual(self.fake.posted_action["id"], "actionReturn_To_Current_Time")

    def test_time_machine_location_mapping(self):
        status, data = _post(
            f"{self.base}/api/time-machine",
            {
                "apply_location": True,
                "latitude": 39.1,
                "longitude": -104.8,
                "name": "Monument",
            },
        )
        self.assertTrue(data["ok"])
        self.assertEqual(self.fake.posted_location["planet"], "Earth")
        self.assertEqual(self.fake.posted_location["name"], "Monument")


if __name__ == "__main__":
    unittest.main()
