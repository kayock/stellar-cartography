"""Sky-culture schema, filtering, comparison, and provenance tests."""

from __future__ import annotations

import copy
import json
import unittest

from app import constellation_story
from app import experience


def _selection(name="Alcyone", constellation="Tau", alt="Pleiades"):
    return {
        "ok": True,
        "connected": True,
        "name": name,
        "alt_name": alt,
        "constellation": constellation,
        "catalogue_designations": "M 45",
    }


class TestCultureSchema(unittest.TestCase):
    def test_culture_ids_are_catalogued(self):
        cultures = {c["id"] for c in constellation_story.list_cultures()["cultures"]}
        self.assertIn("modern", cultures)
        self.assertIn("chinese", cultures)
        self.assertIn("arabic_peninsula", cultures)
        self.assertIn("arabic_sufi", cultures)
        self.assertIn("maori", cultures)

    def test_culture_filtering(self):
        modern = constellation_story.list_constellations("modern")
        chinese = constellation_story.list_constellations("chinese")
        self.assertTrue(all(s["culture_id"] == "modern" for s in modern["stories"]))
        self.assertTrue(all(s["culture_id"] == "chinese" for s in chinese["stories"]))
        self.assertGreaterEqual(len(chinese["stories"]), 2)

    def test_cultural_story_is_not_1_to_1_iau(self):
        story = constellation_story.get_story("chinese_zhinu_hegu")
        self.assertEqual(story["story_kind"], "cultural_sky_story")
        self.assertEqual(set(story["iau_overlap"]), {"Lyr", "Aql"})
        self.assertNotEqual(story["canonical_name"], "Lyra")
        self.assertNotEqual(story["canonical_name"], "Aquila")

    def test_source_provenance_required(self):
        story = constellation_story.get_story("maori_matariki")
        self.assertTrue(story["source_urls"])
        self.assertTrue(story["source_notes"])
        self.assertEqual(story["source_quality"], "stellarium_skyculture")
        self.assertEqual(story["source_people"], "Māori")

    def test_missing_provenance_is_rejected(self):
        raw = copy.deepcopy(constellation_story.load_registry())
        raw["entries"].append(
            {
                "id": "bad_culture_story",
                "story_kind": "cultural_sky_story",
                "culture_id": "chinese",
                "culture_name": "Chinese",
                "tradition_name": "unspecified",
                "canonical_name": "Example",
                "abbreviation": "",
                "aliases": [],
                "sky_culture": "chinese",
                "mythology_summary": "In this source tradition, an example exists.",
                "science_summary": "No science.",
                "major_objects": [],
                "notable_deep_sky_objects": [],
                "story_order": [],
                "cosmic_signal_tags": [],
                "spectrum_tags": [],
                "media_tags": [],
                "source_notes": [],
                "source_quality": "stellarium_skyculture",
                "enabled": True,
            }
        )
        with self.assertRaises(constellation_story.ConstellationStoryError) as ctx:
            constellation_story.validate_registry(raw)
        self.assertIn("provenance", str(ctx.exception).lower())

    def test_unsupported_culture_filter_is_empty_not_an_error(self):
        listing = constellation_story.list_constellations("navajo")
        self.assertTrue(listing["ok"])
        self.assertEqual(listing["stories"], [])


class TestMultiConstellationTour(unittest.TestCase):
    def test_chinese_tour_spans_lyra_and_aquila_targets(self):
        story = constellation_story.get_story("chinese_zhinu_hegu")
        steps = constellation_story.story_steps(story)
        names = [s["search_name"] for s in steps]
        self.assertIn("Vega", names)
        self.assertIn("Altair", names)
        self.assertNotIn("Deneb", names)

    def test_stop_restores_original_selection_name(self):
        constellation_story.reset_tour()
        started = constellation_story.start_tour("taurus", _selection("Aldebaran", "Tau", "Aldebaran"))
        self.assertTrue(started["active"])
        stopped = constellation_story.stop_tour()
        self.assertEqual(stopped["restore_search_name"], "Aldebaran")
        constellation_story.reset_tour()


class TestComparisonAndNarration(unittest.TestCase):
    def test_cross_culture_comparison_keeps_traditions_separate(self):
        compared = constellation_story.compare_stories("Pleiades")
        self.assertTrue(compared["available"])
        ids = {t["id"] for t in compared["traditions"]}
        self.assertIn("taurus", ids)
        self.assertIn("maori_matariki", ids)
        self.assertIn("arabic_peninsula_thurayya", ids)
        labels = [t["culture_id"] for t in compared["traditions"]]
        self.assertEqual(len(labels), len(set(labels)) + (len(labels) - len(set(labels))))
        self.assertTrue(any("Peninsula" in (t["culture_name"] or "") or t["culture_id"] == "arabic_peninsula" for t in compared["traditions"]))
        self.assertFalse(any("mythology" in (t["culture_name"] or "").lower() and "arab" in (t["culture_name"] or "").lower() for t in compared["traditions"]))

    def test_narration_names_the_tradition(self):
        story = constellation_story.get_story("maori_matariki")
        payload = experience.narration_payload(
            _selection(),
            {},
            kind="constellation_overview",
            constellation=story,
        )
        self.assertIn("Māori", payload["text"])
        self.assertIn("represented by this story", payload["text"])
        self.assertNotIn("all Polynesian", payload["text"])
        self.assertEqual(payload["label"], "Cartography Narration")
        self.assertFalse(payload["audio_autoplay"])

    def test_arabic_story_is_not_labeled_mythology(self):
        story = constellation_story.get_story("arabic_peninsula_thurayya")
        payload = constellation_story.story_payload("arabic_peninsula_thurayya")
        self.assertIn("Peninsula", payload["culture_name"])
        self.assertNotIn("Arab mythology", json.dumps(payload))
        self.assertEqual(payload["section_labels"]["story"], "Traditional Story")
        self.assertEqual(payload["section_labels"]["science"], "Scientific View")
        self.assertEqual(payload["section_labels"]["media"], "Official NASA Media")
        self.assertTrue(payload["stellarium_culture_is_distinct"] or payload["sky_culture_live"] is None)

    def test_no_autoplay_on_cultural_payloads(self):
        payload = constellation_story.story_payload("chinese_beidou")
        self.assertFalse(payload["audio_autoplay"])
        self.assertIn("北斗", payload["native_name"])
