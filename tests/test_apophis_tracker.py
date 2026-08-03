import json
import os
import unittest
from datetime import datetime, timezone

from app import apophis_tracker

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "sample_responses")


class TestApophisTracker(unittest.TestCase):
    def test_add_remove_normalization(self):
        with open(os.path.join(FIXTURES, "sbdb_apophis.json"), encoding="utf-8") as f:
            payload = json.load(f)
        result = apophis_tracker.parse_sbdb_response(payload)
        self.assertTrue(result["ok"])
        self.assertEqual(result["designation"], "99942")
        self.assertEqual(result["name"], "Apophis")

    def test_countdown_calculation(self):
        days = apophis_tracker.compute_countdown_days(
            encounter_iso="2029-04-13T00:00:00Z"
        )
        expected = (
            datetime(2029, 4, 13, tzinfo=timezone.utc).date()
            - datetime.now(timezone.utc).date()
        ).days
        self.assertEqual(days, expected)

    def test_missing_optional_fields(self):
        result = apophis_tracker.parse_sbdb_response({"object": {"des": "99942", "name": "Apophis"}})
        self.assertIsNone(result.get("nominal_close_approach_distance_au"))

    def test_timeout(self):
        def slow(_url, _timeout):
            raise TimeoutError()

        result = apophis_tracker.lookup_apophis_tracker(fetcher=slow)
        self.assertEqual(result["status"], "timeout")

    def test_http_error(self):
        import urllib.error

        def http_err(_url, _timeout):
            raise urllib.error.HTTPError(url="x", code=500, msg="err", hdrs=None, fp=None)

        result = apophis_tracker.lookup_apophis_tracker(fetcher=http_err)
        self.assertEqual(result["status"], "http_error")

    def test_malformed_response(self):
        result = apophis_tracker.parse_sbdb_response("not a dict")
        self.assertEqual(result["status"], "malformed")

    def test_risk_status_unavailable(self):
        with open(os.path.join(FIXTURES, "sbdb_apophis.json"), encoding="utf-8") as f:
            payload = json.load(f)
        result = apophis_tracker.parse_sbdb_response(payload)
        self.assertFalse(result["risk_status_available"])
        self.assertIn("not retrieved automatically", result["risk_status_notice"])

    def test_observer_coordinate_fallback(self):
        url = apophis_tracker.build_horizons_url()
        self.assertIn("500%40399", url.replace("'", "%27"))

    def test_no_hardcoded_user_location(self):
        url = apophis_tracker.build_horizons_url(observer_lat=38.25, observer_lon=-104.6, observer_alt_m=1400)
        self.assertIn("SITE_COORD", url)

    def test_horizons_parse(self):
        with open(os.path.join(FIXTURES, "horizons_apophis_text.txt"), encoding="utf-8") as f:
            text = f.read()
        parsed = apophis_tracker.parse_horizons_result_text(text)
        self.assertTrue(parsed["ok"])
        self.assertAlmostEqual(parsed["ra_deg"], 180.123456)
        self.assertAlmostEqual(parsed["dec_deg"], 45.654321)

    def test_horizons_json_wrapper(self):
        with open(os.path.join(FIXTURES, "horizons_apophis.json"), encoding="utf-8") as f:
            payload = json.load(f)
        parsed = apophis_tracker.parse_horizons_response(payload)
        self.assertTrue(parsed["ok"])
        self.assertAlmostEqual(parsed["ra_deg"], 180.123456)

    def test_horizons_truncated_json(self):
        with open(os.path.join(FIXTURES, "horizons_truncated.json"), encoding="utf-8") as f:
            payload = json.load(f)
        parsed = apophis_tracker.parse_horizons_response(payload)
        self.assertFalse(parsed["ok"])
        self.assertIn("ephemeris section", parsed["error"])

    def test_april_2029_encounter_selected_from_out_of_order_list(self):
        with open(os.path.join(FIXTURES, "sbdb_apophis_out_of_order.json"), encoding="utf-8") as f:
            payload = json.load(f)
        result = apophis_tracker.parse_sbdb_response(payload)
        self.assertTrue(result["ok"])
        self.assertIn("2029-Apr", result["encounter_date"])
        self.assertAlmostEqual(result["nominal_close_approach_distance_au"], 0.0002541)
        self.assertFalse(result["encounter_date_unavailable"])

    def test_missing_april_2029_encounter_unavailable(self):
        payload = {
            "object": {"des": "99942", "name": "Apophis"},
            "ca_data": [{"body": "Earth", "cd": "1905-Dec-26 05:03", "dist": 0.27}],
        }
        result = apophis_tracker.parse_sbdb_response(payload)
        self.assertTrue(result["encounter_date_unavailable"])
        self.assertIsNone(result["encounter_date"])


if __name__ == "__main__":
    unittest.main()
