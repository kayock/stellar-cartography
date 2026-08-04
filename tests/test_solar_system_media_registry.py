"""Tests for the data-driven Solar System NASA public-media registry."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from app import planetary_image
from app import solar_system_media_registry as registry

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "app" / "data" / "solar_system_media_registry.json"
JS_PATH = ROOT / "app" / "static" / "lib" / "solar_system_media_registry.js"

MAJOR_PLANETS = (
    "mercury",
    "venus",
    "earth",
    "mars",
    "jupiter",
    "saturn",
    "uranus",
    "neptune",
)

DWARF_PLANETS = ("pluto", "ceres", "eris", "haumea", "makemake")

MAJOR_MOONS = {
    "phobos": "mars",
    "deimos": "mars",
    "io": "jupiter",
    "europa": "jupiter",
    "ganymede": "jupiter",
    "callisto": "jupiter",
    "titan": "saturn",
    "enceladus": "saturn",
    "rhea": "saturn",
    "iapetus": "saturn",
    "mimas": "saturn",
    "miranda": "uranus",
    "ariel": "uranus",
    "umbriel": "uranus",
    "titania": "uranus",
    "oberon": "uranus",
    "triton": "neptune",
    "charon": "pluto",
}


class TestRegistryCompleteness(unittest.TestCase):
    def test_sun_and_major_planets_resolve(self):
        self.assertEqual(registry.normalize_media_target_id("Sun"), "sun")
        for planet in MAJOR_PLANETS:
            self.assertEqual(registry.normalize_media_target_id(planet), planet)
            entry = registry.get_entry(planet)
            self.assertIsNotNone(entry)
            self.assertTrue(entry["search_terms"])
            self.assertTrue(entry["moving_object"])

    def test_dwarf_planets_resolve(self):
        for body in DWARF_PLANETS:
            self.assertEqual(registry.normalize_media_target_id(body), body)
            self.assertEqual(registry.get_entry(body)["target_class"], "dwarf_planet")

    def test_major_moons_resolve_with_parents(self):
        for moon_id, parent in MAJOR_MOONS.items():
            entry = registry.get_entry(moon_id)
            self.assertIsNotNone(entry, moon_id)
            self.assertEqual(entry["parent_body"], parent)
            self.assertEqual(entry["target_class"], "moon")

    def test_aliases_resolve_deterministically(self):
        self.assertEqual(registry.normalize_media_target_id("Luna"), "moon")
        self.assertEqual(registry.normalize_media_target_id("terra"), "earth")
        self.assertEqual(registry.normalize_media_target_id("1 Ceres"), "ceres")
        self.assertEqual(registry.normalize_media_target_id("THE MOON"), "moon")

    def test_json_and_js_registry_parity(self):
        data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
        js_text = JS_PATH.read_text(encoding="utf-8")
        self.assertIn('"id": "mars"', js_text)
        py_ids = {e["id"] for e in data["entries"]}
        self.assertEqual(py_ids, set(registry.all_entry_ids()))
        for entry_id in ("mars", "uranus", "neptune", "europa", "titan", "charon"):
            self.assertIn(f'"id": "{entry_id}"', js_text)


class TestBoundedSearches(unittest.TestCase):
    def test_mars_uranus_neptune_issue_bounded_searches(self):
        for target_id, needle in (
            ("mars", "Mars"),
            ("uranus", "Uranus"),
            ("neptune", "Neptune"),
        ):
            url = planetary_image.build_search_url(target_id)
            self.assertIsNotNone(url)
            self.assertTrue(url.startswith("https://images-api.nasa.gov/search?"))
            self.assertIn("media_type=image", url)
            self.assertIn(needle, urllib_unquote(url))
            # Must not be a bare single generic word alone as the only query intent
            self.assertIn("planet", urllib_unquote(url).lower())


def urllib_unquote(url: str) -> str:
    import urllib.parse

    return urllib.parse.unquote(url)


class TestRelevanceFiltering(unittest.TestCase):
    def test_rejects_irrelevant_sun_hit(self):
        entry = registry.get_entry("sun")
        self.assertFalse(
            registry.item_is_relevant(
                entry,
                title="Sunny day at the beach",
                description="People enjoy the sun",
                keywords="vacation",
            )
        )

    def test_accepts_relevant_sun_hit(self):
        entry = registry.get_entry("sun")
        self.assertTrue(
            registry.item_is_relevant(
                entry,
                title="SDO observes the Sun",
                description="Solar photosphere in extreme ultraviolet",
                keywords="Sun, SDO, solar",
            )
        )

    def test_rejects_earth_without_context(self):
        entry = registry.get_entry("earth")
        self.assertFalse(
            registry.item_is_relevant(
                entry,
                title="Down to Earth advice",
                description="An earthy metaphor",
                keywords="speech",
            )
        )

    def test_rejects_moon_without_context(self):
        entry = registry.get_entry("moon")
        self.assertFalse(
            registry.item_is_relevant(
                entry,
                title="Honeymoon destination",
                description="A romantic moonlit evening",
                keywords="travel",
            )
        )

    def test_rejects_io_without_parent_context(self):
        entry = registry.get_entry("io")
        self.assertFalse(
            registry.item_is_relevant(
                entry,
                title="Io",
                description="A short label",
                keywords=None,
            )
        )

    def test_accepts_io_with_jupiter_context(self):
        entry = registry.get_entry("io")
        self.assertTrue(
            registry.item_is_relevant(
                entry,
                title="Io volcano",
                description="Galilean moon of Jupiter",
                keywords="Io, Jupiter",
            )
        )


class TestPublicMediaClassification(unittest.TestCase):
    def test_found_results_are_public_media_asset(self):
        payload = {
            "collection": {
                "items": [
                    {
                        "data": [
                            {
                                "title": "Mars planet surface",
                                "description": "Mars",
                                "keywords": ["Mars", "planet"],
                                "nasa_id": "PIAMARS1",
                                "center": "JPL",
                                "date_created": "2020-01-01",
                            }
                        ],
                        "links": [
                            {
                                "href": "https://images-assets.nasa.gov/image/PIAMARS1/PIAMARS1~thumb.jpg",
                                "rel": "preview",
                            }
                        ],
                    }
                ]
            }
        }
        result = planetary_image.parse_nasa_images_response(payload, "mars")
        self.assertEqual(result["status"], "found")
        self.assertEqual(result["result_type"], "public_media_asset")
        self.assertEqual(result["media_label"], "NASA public archive media")
        self.assertEqual(result["searched_target"], "Mars")

    def test_irrelevant_items_yield_empty_message(self):
        payload = {
            "collection": {
                "items": [
                    {
                        "data": [
                            {
                                "title": "Unrelated galaxy cluster",
                                "description": "Deep field",
                                "nasa_id": "X1",
                            }
                        ],
                        "links": [
                            {
                                "href": "https://images-assets.nasa.gov/image/X1/X1~thumb.jpg",
                                "rel": "preview",
                            }
                        ],
                    }
                ]
            }
        }
        result = planetary_image.parse_nasa_images_response(payload, "mars")
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(
            result["error"],
            "No relevant NASA public-media result was returned for this target.",
        )
        self.assertIsNone(result["result_type"])
        self.assertNotIn("no imagery", (result["error"] or "").lower())
        self.assertNotIn("scientific data", (result["error"] or "").lower())


if __name__ == "__main__":
    unittest.main()
