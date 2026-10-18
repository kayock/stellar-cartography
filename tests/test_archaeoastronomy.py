"""Archaeoastronomy Visual Mode, confidence, and READY-only promotion."""

from __future__ import annotations

import copy
import unittest

from app import archaeoastronomy
from app import constellation_story
from app import experience


class TestEligibilityAndTypes(unittest.TestCase):
    def test_story_types_are_eligible(self):
        fajada = constellation_story.get_story("ancestral_puebloan_fajada_sun_dagger")
        chaco = constellation_story.get_story("ancestral_puebloan_chaco_cardinal")
        holly = constellation_story.get_story("ancestral_puebloan_holly_solstice_panel")
        templo = constellation_story.get_story("mexica_templo_mayor_solar")
        tian = constellation_story.get_story("mexica_tianquiztli")
        orion = constellation_story.get_story("orion")
        self.assertEqual(fajada["story_type"], "archaeoastronomy")
        self.assertEqual(holly["story_type"], "horizon_calendar")
        self.assertTrue(archaeoastronomy.is_eligible_story(fajada))
        self.assertTrue(archaeoastronomy.is_eligible_story(chaco))
        self.assertTrue(archaeoastronomy.is_eligible_story(holly))
        self.assertTrue(archaeoastronomy.is_eligible_story(templo))
        self.assertFalse(archaeoastronomy.is_eligible_story(tian))
        self.assertFalse(archaeoastronomy.is_eligible_story(orion))
        payload = constellation_story.story_payload("ancestral_puebloan_fajada_sun_dagger")
        self.assertTrue(payload["archaeoastronomy_eligible"])
        self.assertFalse(constellation_story.story_payload("mexica_tianquiztli")["archaeoastronomy_eligible"])


class TestConfidenceAndDisputedIsolation(unittest.TestCase):
    def test_primary_badges_only_strong_or_scholarly(self):
        for sid in (
            "ancestral_puebloan_fajada_sun_dagger",
            "ancestral_puebloan_chaco_cardinal",
            "ancestral_puebloan_holly_solstice_panel",
            "mexica_templo_mayor_solar",
        ):
            visual = archaeoastronomy.visual_payload(sid)
            self.assertTrue(visual["ok"])
            self.assertTrue(archaeoastronomy.primary_badge_allowed(visual["confidence"]))
            self.assertIn(visual["confidence_label"], ("STRONG EVIDENCE", "SCHOLARLY INTERPRETATION"))
            for claim in visual["primary_claims"]:
                self.assertTrue(archaeoastronomy.primary_badge_allowed(claim["confidence"]))
                self.assertNotIn(claim["confidence"], ("disputed", "speculative"))

    def test_disputed_stays_in_research_context(self):
        fajada = archaeoastronomy.visual_payload("ancestral_puebloan_fajada_sun_dagger")
        chaco = archaeoastronomy.visual_payload("ancestral_puebloan_chaco_cardinal")
        disputed = {c["id"] for c in fajada["research_context"] if c["confidence"] == "disputed"}
        self.assertIn("lunar_standstill", disputed)
        self.assertTrue(any(c["id"] == "casa_rinconada_niche" for c in chaco["research_context"]))
        self.assertFalse(any(c["id"] == "lunar_standstill" for c in fajada["primary_claims"]))
        self.assertFalse(any(c["id"] == "casa_rinconada_niche" for c in chaco["primary_claims"]))


class TestSchematicsAndSources(unittest.TestCase):
    def test_fajada_schematic_is_interpretive(self):
        visual = archaeoastronomy.visual_payload("ancestral_puebloan_fajada_sun_dagger")
        self.assertEqual(visual["visual_mode"], "fajada_schematic")
        self.assertEqual(visual["schematic_label"], "interpretive schematic")
        self.assertIn("interpretive schematic", visual["precision_note"].lower())
        self.assertEqual(visual["schematic"]["kind"], "fajada_slabs")
        self.assertFalse(visual["applies_stellarium_time"])

    def test_chaco_orientation_omits_unsupported_alignments(self):
        visual = archaeoastronomy.visual_payload("ancestral_puebloan_chaco_cardinal")
        self.assertEqual(visual["visual_mode"], "cardinal_architecture")
        self.assertEqual(visual["schematic"]["axes"], ["north_south", "east_west"])
        self.assertIn("casa_rinconada_niche_light", visual["schematic"]["omitted"])
        self.assertIn("lunar_standstill", visual["schematic"]["omitted"])

    def test_every_visual_claim_maps_to_a_source(self):
        for sid in (
            "ancestral_puebloan_fajada_sun_dagger",
            "ancestral_puebloan_chaco_cardinal",
            "ancestral_puebloan_holly_solstice_panel",
            "mexica_templo_mayor_solar",
        ):
            visual = archaeoastronomy.visual_payload(sid)
            for claim in visual["primary_claims"] + visual["research_context"]:
                self.assertTrue(claim["sources"], claim)
                for src in claim["sources"]:
                    self.assertTrue(src["title"])
                    self.assertTrue(src["institution"])

    def test_idealized_horizon_label(self):
        visual = archaeoastronomy.visual_payload("ancestral_puebloan_fajada_sun_dagger")
        self.assertEqual(visual["horizon_model"], "idealized")
        self.assertIn("idealized", visual["horizon_note"].lower())
        self.assertEqual(visual["solar_path"]["label"], "idealized horizon")
        eq = archaeoastronomy.sunrise_sunset_azimuths(36.06, 0.0)
        self.assertAlmostEqual(eq["sunrise_azimuth_deg"], 90.0, places=1)
        self.assertAlmostEqual(eq["sunset_azimuth_deg"], 270.0, places=1)
        summer = archaeoastronomy.sunrise_sunset_azimuths(36.06, 23.44)
        self.assertLess(summer["sunrise_azimuth_deg"], 90.0)


class TestTimeMachineExplicit(unittest.TestCase):
    def test_visual_payload_does_not_apply_time(self):
        visual = archaeoastronomy.visual_payload("ancestral_puebloan_fajada_sun_dagger")
        self.assertFalse(visual["applies_stellarium_time"])
        for date in visual["historical_dates"]:
            self.assertTrue(date["apply_requires_explicit_action"])
            self.assertFalse(date["silent_apply"])
            self.assertEqual(date["kind"], "astronomical_reconstruction")

    def test_historical_request_requires_apply_time_flag(self):
        req = archaeoastronomy.historical_time_request(
            "ancestral_puebloan_fajada_sun_dagger",
            "fajada_ad1000_solstice",
        )
        self.assertTrue(req["ok"])
        self.assertTrue(req["apply_time"])
        self.assertFalse(req["apply_location"])
        self.assertFalse(req["silent_apply"])
        self.assertEqual(req["kind"], "astronomical_reconstruction")
        validated = experience.validate_time_machine_request(req)
        self.assertTrue(validated["ok"])
        self.assertTrue(validated["reconstruction"])
        self.assertEqual(validated["reconstruction_label"], "astronomical reconstruction")
        self.assertTrue(validated["utc"].startswith("1000-"))

    def test_ordinary_time_machine_still_rejects_year_1000(self):
        blocked = experience.validate_time_machine_request(
            {"apply_time": True, "utc": "1000-06-21T19:00:00Z"}
        )
        self.assertFalse(blocked["ok"])
        self.assertIn("1600", blocked["error"])

    def test_no_apply_means_no_stellarium_change(self):
        empty = experience.validate_time_machine_request({"utc": "1000-06-21T19:00:00Z", "reconstruction": True})
        self.assertFalse(empty["ok"])
        self.assertIn("Nothing is sent", empty["error"])


class TestSitePrivacyAndFoundation(unittest.TestCase):
    def test_public_park_coords_are_rounded(self):
        visual = archaeoastronomy.visual_payload("ancestral_puebloan_fajada_sun_dagger")
        coords = visual["site_context"]["coordinates"]
        self.assertEqual(coords["precision"], "public_park_vicinity")
        self.assertEqual(coords["latitude"], 36.06)
        self.assertIn("not a restricted", coords["note"].lower())

    def test_sensitive_coordinates_are_withheld(self):
        site = {
            "latitude": 36.12345,
            "longitude": -107.98765,
            "coordinates_public": True,
            "coordinates_sensitivity": "restricted",
        }
        self.assertIsNone(archaeoastronomy.public_site_coordinates(site))

    def test_mesa_verde_is_foundation_only(self):
        self.assertIsNone(archaeoastronomy.get_entry("mesa_verde_sun_temple", production_only=True))
        hidden = archaeoastronomy.visual_payload("mesa_verde_sun_temple")
        self.assertFalse(hidden["ok"])
        foundation = archaeoastronomy.foundation_entry("mesa_verde_sun_temple")
        self.assertTrue(foundation["foundation_only"])
        self.assertEqual(foundation["promotion_status"], "RESEARCH_MORE")
        self.assertFalse(foundation["production"])
        self.assertIsNone(constellation_story.get_story("mesa_verde_sun_temple"))


class TestNarrationAndComparison(unittest.TestCase):
    def test_narration_uses_inference_wording(self):
        story = constellation_story.get_story("ancestral_puebloan_fajada_sun_dagger")
        spoken = constellation_story.constellation_narration("archaeoastronomy", story=story)
        text = spoken["text"].lower()
        self.assertTrue(
            "researchers have interpreted" in text or "archaeological evidence suggests" in text
            or "strongly supported" in text
        )
        self.assertNotIn("oral constellation story", spoken["text"].replace("not a living oral constellation story", ""))
        self.assertIn("not a living oral constellation story", spoken["text"])
        self.assertFalse(spoken["audio_autoplay"])

    def test_same_sky_uses_observational_function_for_archaeo(self):
        compared = constellation_story.compare_stories("ancestral_puebloan_fajada_sun_dagger")
        self.assertEqual(compared["comparison_kind"], "similar_observational_function")
        self.assertIn("similar observational function", compared["note"].lower())
        ids = {t["id"] for t in compared["traditions"]}
        self.assertIn("ancestral_puebloan_holly_solstice_panel", ids)
        self.assertIn("mexica_templo_mayor_solar", ids)
        self.assertNotIn("mexica_tianquiztli", ids)

    def test_pleiades_comparison_is_not_forced_archaeo(self):
        compared = constellation_story.compare_stories("Pleiades")
        self.assertEqual(compared["comparison_kind"], "same_sky_object")
        cultures = {t["culture_id"] for t in compared["traditions"]}
        self.assertIn("mexica", cultures)
        self.assertNotIn("chinese", cultures)


class TestReadyOnlyAndRestricted(unittest.TestCase):
    def test_holly_is_ready_and_anasazi_is_search_only(self):
        story = constellation_story.get_story("ancestral_puebloan_holly_solstice_panel")
        self.assertTrue(story["enabled"])
        self.assertEqual(story["culture_name"], "Ancestral Puebloan")
        self.assertIn("Anasazi", story["search_aliases"])
        self.assertNotEqual(story["canonical_name"], "Anasazi")
        matches = constellation_story.resolve_stories("Anasazi")
        self.assertIn("ancestral_puebloan_holly_solstice_panel", {m["id"] for m in matches})

    def test_restricted_dine_story_still_rejected(self):
        raw = copy.deepcopy(constellation_story.load_registry())
        raw["entries"].append(
            {
                "id": "dine_dilyehe_restricted_visual",
                "story_kind": "cultural_sky_story",
                "culture_id": "dine",
                "culture_name": "Diné",
                "tradition_name": "Diné",
                "canonical_name": "Dilyéhé",
                "abbreviation": "",
                "aliases": [],
                "sky_culture": "dine",
                "mythology_summary": "Restricted seasonal story.",
                "science_summary": "Pleiades.",
                "major_objects": [],
                "notable_deep_sky_objects": [],
                "story_order": [],
                "cosmic_signal_tags": [],
                "spectrum_tags": [],
                "media_tags": [],
                "source_notes": ["restricted"],
                "source_urls": [
                    {
                        "title": "x",
                        "institution": "y",
                        "url": "https://example.org",
                        "supports": "z",
                    }
                ],
                "source_quality": "cultural_organization",
                "source_people": "Diné",
                "public_story_status": "restricted",
                "enabled": True,
            }
        )
        with self.assertRaises(constellation_story.ConstellationStoryError):
            constellation_story.validate_registry(raw)

    def test_no_dine_or_apache_production_stories(self):
        ids = {e["id"] for e in constellation_story.enabled_stories()}
        self.assertNotIn("dine_dilyehe", ids)
        self.assertNotIn("mescalero_star_clock", ids)
        self.assertEqual(constellation_story.list_constellations("dine")["stories"], [])
        self.assertEqual(constellation_story.list_constellations("hopi")["stories"], [])


if __name__ == "__main__":
    unittest.main()
