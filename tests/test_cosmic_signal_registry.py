"""Tests for Cosmic Signal Deck registry, matching, and URL safety."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from app import cosmic_signal_registry as csr
from app import solar_system_media_registry as ss

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_JSON = ROOT / "app" / "data" / "cosmic_signal_registry.json"
JS_MIRROR = ROOT / "app" / "static" / "lib" / "cosmic_signal_registry.js"


class TestSingleRegistrySource(unittest.TestCase):
    def test_only_json_registry_exists(self):
        self.assertTrue(REGISTRY_JSON.is_file())
        self.assertFalse(JS_MIRROR.exists(), "Hand-written JS registry mirror must not exist")

    def test_registry_validates(self):
        csr.reload_registry()
        data = csr.load_registry()
        self.assertEqual(len([e for e in data["entries"] if e.get("enabled")]), 5)

    def test_redirect_limitation_documented(self):
        notice = csr.load_registry().get("redirect_limitation_notice") or ""
        self.assertIn("redirect", notice.lower())
        self.assertIn("proxy", notice.lower())


class TestSolarSystemIdReuse(unittest.TestCase):
    def test_reuses_solar_system_canonical_ids(self):
        self.assertEqual(csr.resolve_canonical_target_id("Mars"), "mars")
        self.assertEqual(csr.resolve_canonical_target_id("Phobos"), "phobos")
        self.assertEqual(ss.normalize_media_target_id("Phobos"), "phobos")
        self.assertEqual(csr.resolve_canonical_target_id("Sun"), "sun")


class TestDeepSpaceMatching(unittest.TestCase):
    def test_exact_targets(self):
        for name, expected_id in (
            ("Vela Pulsar", "vela_pulsar_chandra_sonification"),
            ("Crab Nebula", "crab_nebula_chandra_sonification"),
            ("Cassiopeia A", "cassiopeia_a_chandra_sonification"),
            ("Sagittarius A*", "galactic_center_chandra_sonification"),
            ("Galactic Center", "galactic_center_chandra_sonification"),
        ):
            result = csr.match_signals_for_target({"name": name})
            self.assertEqual(result["relevance"], "exact_target", name)
            self.assertEqual(result["primary"]["id"], expected_id)
            self.assertNotEqual(result["relevance"], "general_featured")

    def test_aliases(self):
        self.assertEqual(csr.resolve_canonical_target_id("M1"), "crab_nebula")
        self.assertEqual(csr.resolve_canonical_target_id("Cas A"), "cassiopeia_a")
        self.assertEqual(csr.resolve_canonical_target_id("Sgr A*"), "sagittarius_a")

    def test_related_body_sun_gets_voyager(self):
        result = csr.match_signals_for_target({"name": "Sun"}, allow_featured=False)
        self.assertEqual(result["relevance"], "related_body")
        self.assertEqual(result["primary"]["id"], "voyager1_interstellar_plasma_pia17045")

    def test_featured_fallback_labeled(self):
        result = csr.match_signals_for_target({"name": "Phobos"}, allow_featured=True)
        self.assertEqual(result["relevance"], "general_featured")
        self.assertEqual(result["primary"]["relevance"], "general_featured")
        self.assertNotEqual(result["primary"]["relevance"], "exact_target")

    def test_featured_can_be_disabled(self):
        result = csr.match_signals_for_target({"name": "Phobos"}, allow_featured=False)
        self.assertIsNone(result["primary"])
        self.assertEqual(
            result["empty_exact_message"],
            "No exact curated signal is available for this target.",
        )


class TestFalseMatchPrevention(unittest.TestCase):
    def test_no_substring_sunlight(self):
        self.assertIsNone(csr.resolve_canonical_target_id("sunlight"))
        result = csr.match_signals_for_target({"name": "sunlight"}, allow_featured=False)
        self.assertIsNone(result["primary"])

    def test_no_titan_rocket_false_match(self):
        # Titan resolves to the moon via Solar System registry; no exact signal.
        self.assertEqual(csr.resolve_canonical_target_id("Titan"), "titan")
        result = csr.match_signals_for_target({"name": "Titan"}, allow_featured=False)
        self.assertIsNone(result["primary"])

    def test_europa_not_exact_signal(self):
        result = csr.match_signals_for_target({"name": "Europa"}, allow_featured=False)
        self.assertIsNone(result["primary"])


class TestMediaSemantics(unittest.TestCase):
    def test_voyager_is_audification_not_sonification(self):
        entry = next(
            e
            for e in csr.load_registry()["entries"]
            if e["id"] == "voyager1_interstellar_plasma_pia17045"
        )
        self.assertEqual(entry["media_type"], "data_audification")
        self.assertNotEqual(entry["media_type"], "data_sonification")
        self.assertIn("amplif", (entry.get("conversion_method") or "").lower())

    def test_chandra_entries_are_sonification(self):
        for entry_id in (
            "vela_pulsar_chandra_sonification",
            "crab_nebula_chandra_sonification",
            "cassiopeia_a_chandra_sonification",
            "galactic_center_chandra_sonification",
        ):
            entry = next(e for e in csr.load_registry()["entries"] if e["id"] == entry_id)
            self.assertEqual(entry["media_type"], "data_sonification")


class TestUrlValidation(unittest.TestCase):
    def test_allows_https_official_hosts(self):
        hosts = set(csr.load_registry()["allowed_media_hosts"])
        self.assertTrue(
            csr.is_allowed_url(
                "https://www.chandra.si.edu/sound/sounds/crab_all.mp4",
                allowed_hosts=hosts,
            )
        )

    def test_rejects_javascript_data_http_and_bad_hosts(self):
        hosts = set(csr.load_registry()["allowed_media_hosts"])
        self.assertFalse(csr.is_allowed_url("javascript:alert(1)", allowed_hosts=hosts))
        self.assertFalse(csr.is_allowed_url("data:text/plain,hi", allowed_hosts=hosts))
        self.assertFalse(
            csr.is_allowed_url("http://www.chandra.si.edu/sound/sounds/crab_all.mp4", allowed_hosts=hosts)
        )
        self.assertFalse(
            csr.is_allowed_url("https://evil.example/x.mp4", allowed_hosts=hosts)
        )
        self.assertFalse(
            csr.is_allowed_url(
                'https://www.chandra.si.edu/x.mp4" onload="alert(1)',
                allowed_hosts=hosts,
            )
        )


class TestCreditsAndProvenance(unittest.TestCase):
    def test_enabled_entries_have_credits_and_hosts(self):
        for entry in csr.enabled_entries():
            self.assertTrue(entry["credits"])
            self.assertTrue(entry["source_page_url"])
            self.assertTrue(entry["final_resolved_media_host"])
            self.assertIn("T", entry["verified_date"])


if __name__ == "__main__":
    unittest.main()
