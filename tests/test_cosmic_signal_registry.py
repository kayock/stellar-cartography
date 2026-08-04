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
        self.assertEqual(len([e for e in data["entries"] if e.get("enabled")]), 15)
        self.assertEqual(len(data["entries"]), 15)

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
            ("MSH 15-52", "msh_15_52_chandra_ixpe_sonification"),
            ("Phantom Galaxy", "m74_chandra_webb_hubble_sonification"),
            ("SN 1987A", "sn_1987a_chandra_hubble_sonification"),
            ("Messier 87", "m87_chandra_vla_sonification"),
            ("Andromeda Galaxy", "m31_multiwavelength_sonification"),
            ("Jupiter", "jupiter_chandra_hubble_sonification"),
            ("Saturn", "saturn_chandra_cassini_sonification"),
            ("Uranus", "uranus_chandra_keck_sonification"),
            ("Southern Ring Nebula", "southern_ring_nebula_jwst_sonification"),
            ("Stephan's Quintet", "stephans_quintet_chandra_webb_sonification"),
        ):
            result = csr.match_signals_for_target({"name": name})
            self.assertEqual(result["relevance"], "exact_target", name)
            self.assertEqual(result["primary"]["id"], expected_id)
            self.assertNotEqual(result["relevance"], "general_featured")

    def test_aliases(self):
        self.assertEqual(csr.resolve_canonical_target_id("M1"), "crab_nebula")
        self.assertEqual(csr.resolve_canonical_target_id("Cas A"), "cassiopeia_a")
        self.assertEqual(csr.resolve_canonical_target_id("Sgr A*"), "sagittarius_a")
        self.assertEqual(csr.resolve_canonical_target_id("PSR B1509-58"), "msh_15_52")
        self.assertEqual(csr.resolve_canonical_target_id("NGC 628"), "m74")
        self.assertEqual(csr.resolve_canonical_target_id("SN87A"), "sn_1987a")
        self.assertEqual(csr.resolve_canonical_target_id("NGC 4486"), "m87")
        self.assertEqual(csr.resolve_canonical_target_id("Messier 31"), "m31")
        self.assertEqual(csr.resolve_canonical_target_id("NGC 3132"), "southern_ring_nebula")
        self.assertEqual(csr.resolve_canonical_target_id("HCG 92"), "stephans_quintet")

    def test_slice1_entries_still_present(self):
        ids = {e["id"] for e in csr.enabled_entries()}
        for entry_id in (
            "voyager1_interstellar_plasma_pia17045",
            "vela_pulsar_chandra_sonification",
            "crab_nebula_chandra_sonification",
            "cassiopeia_a_chandra_sonification",
            "galactic_center_chandra_sonification",
        ):
            self.assertIn(entry_id, ids)

    def test_no_duplicate_ids_or_media_urls(self):
        entries = csr.load_registry()["entries"]
        ids = [e["id"] for e in entries]
        urls = [e["media_url"] for e in entries]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(urls), len(set(urls)))

    def test_no_alias_collisions_across_deep_space_targets(self):
        seen: dict[str, str] = {}
        for target in csr.load_registry()["deep_space_targets"]:
            keys = [target["id"]] + list(target.get("aliases") or [])
            for key in keys:
                norm = " ".join(str(key).strip().lower().split())
                if norm in seen and seen[norm] != target["id"]:
                    self.fail(f"Alias collision for '{norm}': {seen[norm]} vs {target['id']}")
                seen[norm] = target["id"]

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

    def test_solar_system_planets_reuse_canonical_ids(self):
        self.assertEqual(csr.resolve_canonical_target_id("Jupiter"), "jupiter")
        self.assertEqual(csr.resolve_canonical_target_id("Saturn"), "saturn")
        self.assertEqual(csr.resolve_canonical_target_id("Uranus"), "uranus")
        self.assertEqual(ss.normalize_media_target_id("Jupiter"), "jupiter")


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

    def test_no_bare_andromeda_or_ring_or_number_false_match(self):
        self.assertIsNone(csr.resolve_canonical_target_id("andromeda"))
        self.assertIsNone(csr.resolve_canonical_target_id("ring"))
        self.assertIsNone(csr.resolve_canonical_target_id("87"))
        self.assertIsNone(csr.resolve_canonical_target_id("m"))
        self.assertIsNone(csr.resolve_canonical_target_id("hand of god"))


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
            "msh_15_52_chandra_ixpe_sonification",
            "m74_chandra_webb_hubble_sonification",
            "sn_1987a_chandra_hubble_sonification",
            "m87_chandra_vla_sonification",
            "m31_multiwavelength_sonification",
            "jupiter_chandra_hubble_sonification",
            "saturn_chandra_cassini_sonification",
            "uranus_chandra_keck_sonification",
            "southern_ring_nebula_jwst_sonification",
            "stephans_quintet_chandra_webb_sonification",
        ):
            entry = next(e for e in csr.load_registry()["entries"] if e["id"] == entry_id)
            self.assertEqual(entry["media_type"], "data_sonification", entry_id)

    def test_msh_pulsar_explanation_mentions_pulse_rate_and_observatories(self):
        entry = next(
            e for e in csr.load_registry()["entries"] if e["id"] == "msh_15_52_chandra_ixpe_sonification"
        )
        text = " ".join(
            [
                entry["mapping_explanation"],
                entry.get("conversion_method") or "",
                entry["short_explanation"],
            ]
        ).lower()
        self.assertIn("7", text)
        self.assertIn("pulse", text)
        self.assertIn("ixpe", text)
        self.assertIn("chandra", text)
        self.assertIn("bottom", text)

    def test_m74_distance_pitch_explanation(self):
        entry = next(
            e for e in csr.load_registry()["entries"] if e["id"] == "m74_chandra_webb_hubble_sonification"
        )
        text = (entry["mapping_explanation"] + " " + (entry.get("conversion_method") or "")).lower()
        self.assertIn("distance", text)
        self.assertIn("pitch", text)
        self.assertIn("center", text)

    def test_new_entries_not_general_featured(self):
        for entry in csr.enabled_entries():
            if entry["id"] == "voyager1_interstellar_plasma_pia17045":
                continue
            self.assertNotIn("general_featured", entry["relevance_capabilities"], entry["id"])


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
        allowed_media = set(csr.load_registry()["allowed_media_hosts"])
        allowed_source = set(csr.load_registry()["allowed_source_hosts"])
        for entry in csr.enabled_entries():
            self.assertTrue(entry["credits"], entry["id"])
            self.assertTrue(entry.get("attribution"), entry["id"])
            self.assertTrue(entry["source_page_url"], entry["id"])
            self.assertTrue(entry["final_resolved_media_host"], entry["id"])
            self.assertIn("T", entry["verified_date"], entry["id"])
            self.assertTrue(
                csr.is_allowed_url(entry["media_url"], allowed_hosts=allowed_media),
                entry["id"],
            )
            self.assertTrue(
                csr.is_allowed_url(entry["source_page_url"], allowed_hosts=allowed_source),
                entry["id"],
            )
            self.assertIn(
                entry["final_resolved_media_host"],
                allowed_media,
                entry["id"],
            )
            self.assertTrue(entry.get("mapping_explanation"), entry["id"])
            self.assertTrue(entry.get("what_it_does_not_prove"), entry["id"])
            self.assertTrue(entry.get("accessibility_description"), entry["id"])


if __name__ == "__main__":
    unittest.main()
