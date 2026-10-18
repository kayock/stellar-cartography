"""Southwestern / Mexica source-pack schema and labeling tests."""

from __future__ import annotations

import copy
import json
import unittest

from app import constellation_story
from app import experience


def _sel(name="Pleiades", constellation="Tau", alt="Pleiades"):
    return {
        "ok": True,
        "connected": True,
        "name": name,
        "alt_name": alt,
        "constellation": constellation,
        "catalogue_designations": "M 45",
    }


class TestSearchAliasesAndTerminology(unittest.TestCase):
    def test_search_aliases_resolve_anasazi_to_ancestral_puebloan(self):
        matches = constellation_story.resolve_stories("Anasazi")
        ids = {m["id"] for m in matches}
        self.assertIn("ancestral_puebloan_fajada_sun_dagger", ids)
        self.assertIn("ancestral_puebloan_chaco_cardinal", ids)
        self.assertIn("ancestral_puebloan_holly_solstice_panel", ids)
        for story in matches:
            self.assertEqual(story["culture_name"], "Ancestral Puebloan")
            self.assertNotEqual(story["canonical_name"], "Anasazi")
            self.assertIn("Anasazi", story.get("search_aliases") or [])
            self.assertIn("Ancestral Puebloan", story.get("terminology_note") or "")

    def test_display_prefers_ancestral_puebloan(self):
        payload = constellation_story.story_payload("ancestral_puebloan_fajada_sun_dagger")
        self.assertEqual(payload["culture_name"], "Ancestral Puebloan")
        self.assertNotIn("Anasazi", payload["canonical_name"])
        self.assertIn("Anasazi", payload["search_aliases"])


class TestEvidenceAndPeople(unittest.TestCase):
    def test_evidence_type_and_archaeological_label(self):
        payload = constellation_story.story_payload("ancestral_puebloan_fajada_sun_dagger")
        self.assertEqual(payload["evidence_type"], "archaeological_inference")
        self.assertFalse(payload["living_tradition"])
        self.assertEqual(payload["section_labels"]["story"], "Archaeological Interpretation")
        self.assertEqual(payload["section_labels"]["science"], "Scientific View")
        self.assertEqual(payload["section_labels"]["media"], "Official NASA Media")
        self.assertEqual(payload["section_labels"]["sources"], "Sources & Context")
        self.assertIn("Archaeological interpretations suggest", payload["mythology_summary"])

    def test_source_people_required(self):
        for sid in (
            "ancestral_puebloan_fajada_sun_dagger",
            "ancestral_puebloan_chaco_cardinal",
            "ancestral_puebloan_holly_solstice_panel",
            "mexica_tianquiztli",
            "mexica_templo_mayor_solar",
        ):
            story = constellation_story.get_story(sid)
            self.assertTrue(story["source_people"])

    def test_missing_source_people_is_rejected(self):
        raw = copy.deepcopy(constellation_story.load_registry())
        raw["entries"].append(
            {
                "id": "missing_people_story",
                "story_kind": "cultural_sky_story",
                "culture_id": "mexica",
                "culture_name": "Mexica (historical)",
                "tradition_name": "test",
                "canonical_name": "Test",
                "abbreviation": "",
                "aliases": [],
                "sky_culture": "mexica",
                "mythology_summary": "In the Mexica historical sources represented here, a test exists.",
                "science_summary": "None.",
                "major_objects": [],
                "notable_deep_sky_objects": [],
                "story_order": [],
                "cosmic_signal_tags": [],
                "spectrum_tags": [],
                "media_tags": [],
                "source_notes": ["note"],
                "source_urls": [
                    {
                        "title": "Example",
                        "institution": "UNAM",
                        "url": "https://www.unam.mx/",
                        "supports": "example",
                    }
                ],
                "source_quality": "scholarly",
                "enabled": True,
            }
        )
        with self.assertRaises(constellation_story.ConstellationStoryError) as ctx:
            constellation_story.validate_registry(raw)
        self.assertIn("source_people", str(ctx.exception))

    def test_restricted_story_is_rejected(self):
        raw = copy.deepcopy(constellation_story.load_registry())
        raw["entries"].append(
            {
                "id": "restricted_dine_example",
                "story_kind": "cultural_sky_story",
                "culture_id": "dine",
                "culture_name": "Diné",
                "tradition_name": "seasonal",
                "source_people": "Diné",
                "canonical_name": "Restricted",
                "abbreviation": "",
                "aliases": [],
                "sky_culture": "navajo",
                "mythology_summary": "Restricted.",
                "science_summary": "None.",
                "major_objects": [],
                "notable_deep_sky_objects": [],
                "story_order": [],
                "cosmic_signal_tags": [],
                "spectrum_tags": [],
                "media_tags": [],
                "source_notes": ["restricted"],
                "source_urls": [
                    {
                        "title": "Example",
                        "institution": "Navajo Nation",
                        "url": "https://www.navajo-nsn.gov/",
                        "supports": "example",
                    }
                ],
                "source_quality": "cultural_organization",
                "public_story_status": "restricted",
                "enabled": True,
            }
        )
        with self.assertRaises(constellation_story.ConstellationStoryError) as ctx:
            constellation_story.validate_registry(raw)
        self.assertIn("restricted", str(ctx.exception).lower())

    def test_no_enabled_restricted_stories(self):
        for story in constellation_story.enabled_stories():
            self.assertNotIn(story.get("public_story_status"), {"restricted", "deferred_restricted"})


class TestCommunityHandling(unittest.TestCase):
    def test_no_generic_pueblo_or_apache_story(self):
        ids = {s["id"] for s in constellation_story.enabled_stories()}
        self.assertNotIn("pueblo_sky_mythology", ids)
        self.assertNotIn("apache_sky", ids)
        apache = constellation_story.list_constellations("apache")
        self.assertEqual(apache["stories"], [])
        dine = constellation_story.list_constellations("dine")
        self.assertEqual(dine["stories"], [])
        hopi = constellation_story.list_constellations("hopi")
        self.assertEqual(hopi["stories"], [])

    def test_mexica_not_merged_with_generic_mesoamerica(self):
        story = constellation_story.get_story("mexica_tianquiztli")
        blob = json.dumps(story)
        self.assertEqual(story["culture_id"], "mexica")
        self.assertNotIn("Maya", story["culture_name"])
        self.assertNotIn("Aztec mythology", blob)
        self.assertNotIn("Mesoamerican mythology", blob)
        self.assertIn("historical mexica", blob.lower())

    def test_specific_pueblo_not_invented(self):
        for story in constellation_story.enabled_stories_for_culture("ancestral_puebloan"):
            self.assertEqual(story["culture_id"], "ancestral_puebloan")
            self.assertNotEqual(story.get("source_people"), "Pueblo")
            self.assertIn("Ancestral Puebloan", story["source_people"])


class TestMotifsAndComparison(unittest.TestCase):
    def test_shared_motif_does_not_imply_common_origin(self):
        story = constellation_story.get_story("mexica_tianquiztli")
        motifs = story.get("shared_motifs") or []
        self.assertTrue(motifs)
        for motif in motifs:
            self.assertEqual(motif["relationship_status"], "independent_similarity")
            self.assertNotIn("common origin", (motif.get("similarity_description") or "").lower().replace("not a shared origin", ""))
            self.assertIn("not", motif["similarity_description"].lower())

    def test_pleiades_comparison_keeps_mexica_separate(self):
        compared = constellation_story.compare_stories("Pleiades")
        cultures = {t["culture_id"] for t in compared["traditions"]}
        self.assertIn("modern", cultures)
        self.assertIn("maori", cultures)
        self.assertIn("arabic_peninsula", cultures)
        self.assertIn("mexica", cultures)
        self.assertNotIn("chinese", cultures)
        self.assertNotIn("arabic_sufi", cultures)
        names = [t.get("culture_name") for t in compared["traditions"]]
        self.assertTrue(any("Mexica" in (n or "") for n in names))
        self.assertFalse(any("mythology" in (n or "").lower() and "aztec" in (n or "").lower() for n in names))


class TestNarrationAndMedia(unittest.TestCase):
    def test_narration_identifies_ancestral_puebloan(self):
        story = constellation_story.get_story("ancestral_puebloan_fajada_sun_dagger")
        payload = experience.narration_payload(
            _sel("Sun", None, "Sun"),
            {},
            kind="constellation_overview",
            constellation=story,
        )
        self.assertIn("archaeological interpretation", payload["text"].lower())
        self.assertIn("Ancestral Puebloan", payload["text"])
        self.assertFalse(payload["audio_autoplay"])
        self.assertEqual(payload["label"], "Cartography Narration")

    def test_narration_identifies_mexica(self):
        story = constellation_story.get_story("mexica_tianquiztli")
        payload = experience.narration_payload(
            _sel(),
            {},
            kind="constellation_overview",
            constellation=story,
        )
        self.assertIn("Mexica historical sources", payload["text"])
        self.assertNotIn("Aztec mythology", payload["text"])
        self.assertFalse(payload["audio_autoplay"])

    def test_scientific_media_remains_labeled(self):
        payload = constellation_story.story_payload("mexica_tianquiztli")
        self.assertEqual(payload["section_labels"]["science"], "Scientific View")
        self.assertEqual(payload["section_labels"]["media"], "Official NASA Media")
        self.assertIn("not a Mexica source", payload["science_summary"])


class TestTours(unittest.TestCase):
    def test_solar_tour_uses_sun_and_restores(self):
        constellation_story.reset_tour()
        started = constellation_story.start_tour(
            "ancestral_puebloan_fajada_sun_dagger",
            _sel("Aldebaran", "Tau", "Aldebaran"),
        )
        self.assertTrue(started["active"])
        self.assertEqual(started["step"]["search_name"], "Sun")
        stopped = constellation_story.stop_tour()
        self.assertEqual(stopped["restore_search_name"], "Aldebaran")
        constellation_story.reset_tour()


if __name__ == "__main__":
    unittest.main()
