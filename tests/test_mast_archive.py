import json
import os
import unittest

from app import mast_archive

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "sample_responses")


def _load(name: str) -> dict:
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as f:
        return json.load(f)


class TestMastArchive(unittest.TestCase):
    def test_hst_confirmed_count(self):
        payload = _load("mast_hst_count.json")
        result = mast_archive.parse_mast_count_response(payload, "hst")
        self.assertEqual(result["status"], "confirmed")
        self.assertEqual(result["count"], 14)

    def test_jwst_nircam_confirmed_count(self):
        payload = _load("mast_jwst_nircam_count.json")
        result = mast_archive.parse_mast_count_response(payload, "jwst_nircam")
        self.assertEqual(result["status"], "confirmed")
        self.assertEqual(result["count"], 3)

    def test_jwst_miri_no_coverage(self):
        payload = _load("mast_jwst_miri_empty.json")
        result = mast_archive.parse_mast_count_response(payload, "jwst_miri")
        self.assertEqual(result["status"], "no_coverage")
        self.assertEqual(result["count"], 0)

    def test_archive_unavailable_malformed(self):
        result = mast_archive.parse_mast_count_response({"status": "ERROR"}, "hst")
        self.assertEqual(result["status"], "malformed")

    def test_malformed_response(self):
        def bad_fetch(_req, _timeout):
            raise json.JSONDecodeError("x", "doc", 0)

        result = mast_archive.lookup_archive_availability(10.0, 41.0, "hst", fetcher=bad_fetch)
        self.assertEqual(result["status"], "unavailable")

    def test_oversized_response(self):
        def big_fetch(_req, _timeout):
            raise ValueError("Response too large")

        result = mast_archive.lookup_archive_availability(10.0, 41.0, "hst", fetcher=big_fetch)
        self.assertEqual(result["status"], "unavailable")

    def test_untrusted_metadata_sanitized(self):
        payload = {
            "status": "COMPLETE",
            "data": [
                {
                    "obs_id": "test\x00id",
                    "instrument_name": "ACS",
                    "cal_start_time": "2020-01-01",
                    "intentType": "science",
                }
            ],
        }
        rows = mast_archive._observation_rows(payload, "hst")
        self.assertEqual(rows[0]["observation_id"], "testid")

    def test_unexpected_url_host_rejected(self):
        self.assertFalse(mast_archive.is_allowed_source_url("https://evil.example/obs"))

    def test_deep_sky_and_solar_system_coords(self):
        for ra, dec in [(83.63, -5.39), (0.0, 0.0)]:
            coords = mast_archive.normalize_coords(ra, dec)
            self.assertIsNotNone(coords)

    def test_observation_list_bounded(self):
        data = [{"obs_id": f"obs{i}", "instrument_name": "ACS", "intentType": "science"} for i in range(40)]
        payload = {"status": "COMPLETE", "data": data}
        rows = mast_archive._observation_rows(payload, "hst")
        self.assertLessEqual(len(rows), mast_archive.MAX_OBSERVATIONS)


if __name__ == "__main__":
    unittest.main()
