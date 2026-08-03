import json
import unittest
import urllib.error
from pathlib import Path

from app import planetary_image
from tests.fixtures.fake_stellarium_server import load_sample

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "sample_responses"


def _load_nasa_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class TestNormalizePilotTarget(unittest.TestCase):
    def test_accepts_pilot_ids(self):
        self.assertEqual(planetary_image.normalize_pilot_target_id("Moon"), "moon")
        self.assertEqual(planetary_image.normalize_pilot_target_id("JUPITER"), "jupiter")
        self.assertEqual(planetary_image.normalize_pilot_target_id(" saturn "), "saturn")

    def test_rejects_unknown_targets(self):
        self.assertIsNone(planetary_image.normalize_pilot_target_id("Mars"))
        self.assertIsNone(planetary_image.normalize_pilot_target_id(""))
        self.assertIsNone(planetary_image.normalize_pilot_target_id(None))


class TestUrlValidation(unittest.TestCase):
    def test_allows_official_nasa_asset_host(self):
        self.assertTrue(
            planetary_image.is_allowed_image_url(
                "https://images-assets.nasa.gov/image/PIA12235/PIA12235~thumb.jpg"
            )
        )

    def test_rejects_non_https(self):
        self.assertFalse(
            planetary_image.is_allowed_image_url(
                "http://images-assets.nasa.gov/image/PIA12235/PIA12235~thumb.jpg"
            )
        )

    def test_rejects_unexpected_host(self):
        self.assertFalse(planetary_image.is_allowed_image_url("https://evil.example.com/a.jpg"))

    def test_allows_official_nasa_details_link(self):
        self.assertTrue(
            planetary_image.is_allowed_source_link("https://images.nasa.gov/details/PIA12235")
        )

    def test_rejects_malformed_source_link(self):
        self.assertFalse(
            planetary_image.is_allowed_source_link('https://images.nasa.gov/details/PIA1" onclick="alert(1)')
        )
        self.assertFalse(planetary_image.is_allowed_source_link("https://evil.example.com/details/PIA1"))

    def test_rejects_unsafe_characters_in_image_url(self):
        self.assertFalse(
            planetary_image.is_allowed_image_url(
                'https://images-assets.nasa.gov/image/PIA1/PIA1~thumb.jpg" onerror="alert(1)'
            )
        )


class TestParseNasaImagesResponse(unittest.TestCase):
    def test_moon_lookup_normalized(self):
        result = planetary_image.parse_nasa_images_response(_load_nasa_fixture("nasa_images_moon.json"), "moon")
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "found")
        self.assertEqual(result["target_id"], "moon")
        self.assertEqual(result["target_name"], "Moon")
        self.assertIn("images-assets.nasa.gov", result["image_url"])
        self.assertEqual(result["title"], "Nearside of the Moon")
        self.assertEqual(result["source_agency"], "NASA")
        self.assertIsNone(result["mission"])
        self.assertEqual(result["nasa_center"], "JPL")
        self.assertEqual(result["keywords"], "Moon, LRO")

    def test_jupiter_lookup_normalized(self):
        result = planetary_image.parse_nasa_images_response(_load_nasa_fixture("nasa_images_jupiter.json"), "jupiter")
        self.assertEqual(result["status"], "found")
        self.assertEqual(result["target_id"], "jupiter")
        self.assertEqual(result["title"], "Jupiter Plume")

    def test_saturn_lookup_normalized(self):
        result = planetary_image.parse_nasa_images_response(_load_nasa_fixture("nasa_images_saturn.json"), "saturn")
        self.assertEqual(result["status"], "found")
        self.assertEqual(result["target_id"], "saturn")
        self.assertEqual(result["title"], "Saturn Atmosphere")

    def test_missing_image_url(self):
        result = planetary_image.parse_nasa_images_response(_load_nasa_fixture("nasa_images_no_image.json"), "moon")
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "unavailable")
        self.assertIsNone(result["image_url"])

    def test_missing_optional_metadata(self):
        payload = {
            "collection": {
                "items": [
                    {
                        "data": [{"title": "Minimal", "nasa_id": "PIA99999"}],
                        "links": [
                            {
                                "href": "https://images-assets.nasa.gov/image/PIA99999/PIA99999~thumb.jpg",
                                "rel": "preview",
                            }
                        ],
                    }
                ]
            }
        }
        result = planetary_image.parse_nasa_images_response(payload, "jupiter")
        self.assertEqual(result["status"], "found")
        self.assertIsNone(result["mission"])
        self.assertIsNone(result["nasa_center"])
        self.assertIsNone(result["keywords"])
        self.assertIsNone(result["instrument"])
        self.assertIsNone(result["image_date"])

    def test_generic_keywords_are_not_labeled_as_mission(self):
        result = planetary_image.parse_nasa_images_response(_load_nasa_fixture("nasa_images_jupiter.json"), "jupiter")
        self.assertIsNone(result["mission"])
        self.assertIn("Galileo", result["keywords"])
        self.assertNotIn("Mission", str(result.get("mission") or ""))

    def test_malformed_response(self):
        result = planetary_image.parse_nasa_images_response({"unexpected": True}, "saturn")
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "malformed")

    def test_rejects_unexpected_image_url_in_payload(self):
        payload = {
            "collection": {
                "items": [
                    {
                        "data": [{"title": "Bad", "nasa_id": "X"}],
                        "links": [{"href": "https://evil.example.com/x.jpg", "rel": "preview"}],
                    }
                ]
            }
        }
        result = planetary_image.parse_nasa_images_response(payload, "moon")
        self.assertEqual(result["status"], "unavailable")


class TestLookupPlanetaryImage(unittest.TestCase):
    def _fetch_fixture(self, fixture_name):
        def fetch(_url, _timeout):
            return _load_nasa_fixture(fixture_name)

        return fetch

    def test_successful_official_source_response(self):
        result = planetary_image.lookup_planetary_image("moon", fetcher=self._fetch_fixture("nasa_images_moon.json"))
        self.assertEqual(result["status"], "found")

    def test_unsupported_target(self):
        result = planetary_image.lookup_planetary_image("mars")
        self.assertEqual(result["status"], "unsupported")

    def test_service_timeout(self):
        def fetch(_url, _timeout):
            raise TimeoutError("timed out")

        result = planetary_image.lookup_planetary_image("jupiter", fetcher=fetch)
        self.assertEqual(result["status"], "timeout")

    def test_http_error(self):
        def fetch(_url, _timeout):
            raise urllib.error.HTTPError("https://example", 503, "fail", {}, None)

        result = planetary_image.lookup_planetary_image("saturn", fetcher=fetch)
        self.assertEqual(result["status"], "http_error")

    def test_malformed_fetch_response(self):
        def fetch(_url, _timeout):
            return "not-a-dict"

        result = planetary_image.lookup_planetary_image("moon", fetcher=fetch)
        self.assertEqual(result["status"], "malformed")


class TestSanitizeText(unittest.TestCase):
    def test_strips_control_characters(self):
        self.assertEqual(planetary_image.sanitize_text("hello\x00world"), "helloworld")

    def test_safe_text_rendering_contract(self):
        self.assertEqual(planetary_image.sanitize_text("<script>alert(1)</script>"), "<script>alert(1)</script>")


if __name__ == "__main__":
    unittest.main()
