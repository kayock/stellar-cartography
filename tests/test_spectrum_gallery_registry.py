"""Tests for Spectrum Gallery registry matching and URL safety."""

from __future__ import annotations

import unittest
from pathlib import Path

from app import spectrum_gallery_registry as sgr

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_JSON = ROOT / "app" / "data" / "spectrum_gallery_registry.json"
JS_MIRROR = ROOT / "app" / "static" / "lib" / "spectrum_gallery_registry.js"


class TestSpectrumRegistry(unittest.TestCase):
    def test_single_json_source(self):
        self.assertTrue(REGISTRY_JSON.is_file())
        self.assertFalse(JS_MIRROR.exists())

    def test_registry_validates_and_enabled_count(self):
        sgr.reload_registry()
        enabled = sgr.enabled_entries()
        self.assertEqual(len(enabled), 23)
        wavelengths = {e["wavelength"] for e in enabled}
        self.assertTrue(wavelengths.issubset(set(sgr.load_registry()["wavelengths"])))


class TestSpectrumMatching(unittest.TestCase):
    def test_exact_targets_default_to_prior_primary(self):
        cases = (
            ("Crab Nebula", "crab_2018_chandra_hubble_spitzer"),
            ("Cassiopeia A", "casa_2005_great_observatories"),
            ("Sagittarius A*", "gcenter_2009_chandra_mosaic"),
            ("Messier 87", "m87_2021_chandra_composite"),
            ("Andromeda Galaxy", "m31_2006_chandra_xray"),
            ("Phantom Galaxy", "m74_2024_chandra_webb_hubble"),
            ("Vela Pulsar", "vela_2013_chandra_xray"),
            ("Jupiter", "jupiter_2005_chandra_xray"),
            ("Saturn", "saturn_2004_chandra_optical"),
        )
        for name, entry_id in cases:
            result = sgr.match_spectrum_for_target({"name": name})
            self.assertEqual(result["relevance"], "exact_target", name)
            self.assertEqual(result["primary"]["id"], entry_id, name)
            self.assertEqual(result["primary"]["relevance_label"], "Exact target")

    def test_multi_view_exact_targets(self):
        expected = {
            "Crab Nebula": [
                "crab_2018_chandra_hubble_spitzer",
                "crab_2018_chandra_xray",
                "crab_2018_hubble_optical",
                "crab_2018_spitzer_infrared",
            ],
            "Cassiopeia A": [
                "casa_2005_great_observatories",
                "casa_2005_chandra_xray",
                "casa_2005_hubble_optical",
                "casa_2005_spitzer_infrared",
            ],
            "Messier 87": [
                "m87_2021_chandra_composite",
                "m87_2001_chandra_xray",
                "m87_2001_hubble_optical",
                "m87_2001_vla_radio",
            ],
            "Sagittarius A*": [
                "gcenter_2009_chandra_mosaic",
                "galactic_2009_great_observatories",
                "galactic_2009_spitzer_infrared",
            ],
            "Andromeda Galaxy": [
                "m31_2006_chandra_xray",
                "m31_2010_optical",
            ],
            "Phantom Galaxy": [
                "m74_2024_chandra_webb_hubble",
                "m74_2024_chandra_xray",
            ],
        }
        for name, ids in expected.items():
            result = sgr.match_spectrum_for_target({"name": name})
            view_ids = [entry["id"] for entry in result["available_views"]]
            self.assertEqual(view_ids, ids, name)
            self.assertTrue(all(v["relevance"] == "exact_target" for v in result["available_views"]))
            # Planck must never appear as an exact wavelength view.
            self.assertFalse(any(v["id"].startswith("planck_") for v in result["available_views"]))

    def test_single_view_target_has_one_available_view(self):
        result = sgr.match_spectrum_for_target({"name": "Jupiter"})
        self.assertEqual(len(result["available_views"]), 1)
        self.assertEqual(result["available_views"][0]["id"], "jupiter_2005_chandra_xray")

    def test_m87_catalogue_designations_handoff(self):
        result = sgr.match_spectrum_for_target(
            {
                "name": "Virgo Galaxy",
                "alt_name": "Virgo Galaxy",
                "catalogue_designations": "M 87 - NGC 4486 - PGC 41361",
            }
        )
        self.assertEqual(result["relevance"], "exact_target")
        self.assertEqual(result["primary"]["id"], "m87_2021_chandra_composite")
        self.assertEqual(len(result["available_views"]), 4)

    def test_all_sky_context_for_unmatched_target(self):
        result = sgr.match_spectrum_for_target({"name": "Phobos"})
        self.assertEqual(result["relevance"], "all_sky_context")
        self.assertEqual(result["primary"]["id"], "planck_2013_cmb_allsky")
        self.assertEqual(result["primary"]["relevance_label"], "All-sky context")
        self.assertEqual(result["primary"]["wavelength"], "Microwave")
        self.assertEqual(result["available_views"], [])
        self.assertIn("not a photograph", result["primary"]["short_explanation"].lower())

    def test_all_sky_can_be_disabled(self):
        result = sgr.match_spectrum_for_target({"name": "Phobos"}, allow_all_sky=False)
        self.assertIsNone(result["primary"])
        self.assertEqual(
            result["empty_exact_message"],
            "No curated spectrum image is available for this target.",
        )

    def test_false_match_prevention(self):
        for name in ("87", "Virgo", "near M87", "ring", "andromeda"):
            result = sgr.match_spectrum_for_target({"name": name}, allow_all_sky=False)
            self.assertIsNone(result["primary"], name)


class TestSpectrumUrlSafety(unittest.TestCase):
    def test_official_hosts_only(self):
        from app import cosmic_signal_registry as csr

        hosts = set(sgr.load_registry()["allowed_image_hosts"])
        for entry in sgr.enabled_entries():
            self.assertTrue(csr.is_allowed_url(entry["image_url"], allowed_hosts=hosts), entry["id"])
        self.assertFalse(csr.is_allowed_url("https://evil.example/x.jpg", allowed_hosts=hosts))
        self.assertFalse(
            csr.is_allowed_url(
                "http://www.chandra.si.edu/photo/2018/crab/crab.jpg",
                allowed_hosts=hosts,
            )
        )


if __name__ == "__main__":
    unittest.main()
