"""Curated exhibit schema, API, narration, and Stellarium safety tests."""

from __future__ import annotations

import copy
import json
import unittest
import urllib.error
import urllib.request

from app import archaeoastronomy
from app import constellation_story
from app import exhibit
from app import experience
from app.server import run_server
from tests.fixtures.fake_stellarium_server import FakeStellariumServer, load_sample, canned_json


def _get(url: str):
    with urllib.request.urlopen(url, timeout=3) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def _get_error(url: str):
    try:
        return _get(url)
    except urllib.error.HTTPError as exc:
        body = json.loads(exc.read().decode("utf-8"))
        return exc.code, body


def _post(url: str, payload: dict):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=3) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


class TestExhibitSchema(unittest.TestCase):
    def test_registry_and_southwestern_schema(self):
        exhibit.reload_registry()
        payload = exhibit.exhibit_payload("southwestern_skies")
        self.assertTrue(payload["ok"])
        card = payload["exhibit"]
        self.assertEqual(card["id"], "southwestern_skies")
        self.assertEqual(card["step_count"], 10)
        self.assertEqual(card["estimated_minutes"], 20)
        self.assertFalse(payload["auto_advance_default"])
        self.assertFalse(payload["audio_autoplay"])
        types = [step["step_type"] for step in card["steps"]]
        self.assertEqual(types[0], "intro")
        self.assertEqual(types[-1], "outro")
        self.assertIn("same_sky_comparison", types)
        self.assertIn("archaeoastronomy", types)
        self.assertIn("historical_reconstruction", types)
        self.assertIn("cultural_story", types)

    def test_step_ordering_and_ids(self):
        card = exhibit.exhibit_payload("southwestern_skies")["exhibit"]
        indexes = [step["index"] for step in card["steps"]]
        self.assertEqual(indexes, list(range(10)))
        self.assertEqual(len({step["step_id"] for step in card["steps"]}), 10)

    def test_invalid_exhibit_id(self):
        self.assertIsNone(exhibit.get_exhibit("not_an_exhibit"))
        self.assertFalse(exhibit.exhibit_payload("not_an_exhibit")["ok"])
        self.assertFalse(exhibit.exhibit_payload("../etc/passwd")["ok"])

    def test_evidence_and_sources_present(self):
        card = exhibit.exhibit_payload("southwestern_skies")["exhibit"]
        self.assertTrue(card["sources"])
        sourced = [group for group in card["sources"] if group["sources"]]
        self.assertGreaterEqual(len(sourced), 5)
        for group in sourced:
            for src in group["sources"]:
                self.assertTrue(src.get("title"))
                self.assertTrue(src.get("institution"))
                self.assertNotIn("raw research", str(src).lower())

    def test_unsupported_story_reference_rejected(self):
        raw = copy.deepcopy(exhibit.load_registry()["exhibits"][0])
        raw["id"] = "bad_story_ref"
        raw["story_ids"] = ["taurus", "not_a_real_story"]
        raw["steps"] = [
            {
                "step_id": "bad_step",
                "step_type": "constellation_story",
                "title": "Bad",
                "story_id": "not_a_real_story",
            }
        ]
        with self.assertRaises(exhibit.ExhibitError) as ctx:
            exhibit.validate_exhibit(raw)
        self.assertIn("unsupported story", str(ctx.exception).lower())

    def test_restricted_story_cannot_appear(self):
        original = constellation_story.get_story
        restricted = dict(original("orion") or {"id": "orion", "enabled": True})
        restricted["public_story_status"] = "restricted"

        def _fake_get(story_id):
            if story_id == "orion":
                return restricted
            return original(story_id)

        constellation_story.get_story = _fake_get
        try:
            with self.assertRaises(exhibit.ExhibitError) as ctx:
                exhibit._require_ready_story("orion", exhibit_id="restricted_exhibit")
            self.assertIn("restricted", str(ctx.exception).lower())
        finally:
            constellation_story.get_story = original

        raw = copy.deepcopy(exhibit.get_exhibit("exhibit_smoke_orion"))
        raw["id"] = "restricted_exhibit"
        raw["enabled"] = True
        raw["story_ids"] = ["restricted_missing"]
        raw["steps"] = [
            {
                "step_id": "restricted_step",
                "step_type": "cultural_story",
                "title": "Restricted",
                "story_id": "restricted_missing",
            }
        ]
        with self.assertRaises(exhibit.ExhibitError):
            exhibit.validate_exhibit(raw)

    def test_only_ready_production_stories(self):
        for story_id in exhibit.get_exhibit("southwestern_skies")["story_ids"]:
            story = constellation_story.get_story(story_id)
            self.assertIsNotNone(story)
            self.assertTrue(story.get("enabled"))
            self.assertNotIn(story.get("public_story_status"), exhibit.RESTRICTED_STATUSES)
            self.assertNotIn(constellation_story._story_culture_id(story), exhibit.BLOCKED_CULTURES_UNLESS_READY)
        for step in exhibit.get_exhibit("southwestern_skies")["steps"]:
            visual_id = step.get("archaeo_visual_id")
            if visual_id:
                visual = archaeoastronomy.get_entry(visual_id, production_only=True)
                self.assertIsNotNone(visual)
                self.assertEqual(visual.get("promotion_status"), "READY")

    def test_no_deferred_living_southwest_stories(self):
        card = exhibit.get_exhibit("southwestern_skies")
        story_blob = " ".join(card["story_ids"] + list(card.get("culture_scope") or [])).lower()
        for token in ("dine", "diné", "navajo", "apache", "hopi", "zuni", "acoma", "taos"):
            self.assertNotIn(token, story_blob)
        for story_id in card["story_ids"]:
            culture = constellation_story._story_culture_id(constellation_story.get_story(story_id))
            self.assertNotIn(culture, exhibit.BLOCKED_CULTURES_UNLESS_READY)

    def test_foundation_visual_rejected(self):
        raw = copy.deepcopy(exhibit.get_exhibit("exhibit_smoke_orion"))
        raw["id"] = "bad_visual"
        raw["story_ids"] = ["orion"]
        raw["steps"] = [
            {
                "step_id": "mesa",
                "step_type": "archaeoastronomy",
                "title": "Mesa",
                "story_id": "orion",
                "archaeo_visual_id": "mesa_verde_sun_temple",
            }
        ]
        with self.assertRaises(exhibit.ExhibitError):
            exhibit.validate_exhibit(raw)

    def test_historical_step_explicit_action_flag(self):
        step = next(
            item
            for item in exhibit.get_exhibit("southwestern_skies")["steps"]
            if item["step_type"] == "historical_reconstruction"
        )
        self.assertTrue(step["user_action_required"])
        self.assertTrue(step["time_machine_action"]["apply_requires_explicit_action"])
        self.assertFalse(step["time_machine_action"]["silent_apply"])
        confirm = exhibit.historical_confirmation(step)
        self.assertTrue(confirm["apply_requires_explicit_action"])
        self.assertFalse(confirm["silent_apply"])
        self.assertIn("AD 1050", confirm["prompt"])
        self.assertIn("modern astronomical simulation", confirm["explanation"].lower())
        self.assertEqual(confirm["apply_label"], "Apply Historical Sky")

    def test_restore_state_payload(self):
        captured = {
            "selected_object": "Mars",
            "restore_search_name": "Mars",
            "fov_deg": 12.5,
            "utc": "2026-01-01T00:00:00Z",
            "jday": 2460000.5,
            "is_time_now": False,
            "latitude": 36.06,
            "longitude": -107.96,
            "location_name": "Monument",
            "constellation_controls": {"lines": True, "labels": False},
        }
        payload = exhibit.restore_state_payload(captured)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["selected_object"], "Mars")
        self.assertEqual(payload["fov_deg"], 12.5)
        self.assertFalse(payload["applies_time_silently"])
        self.assertIn("restore", payload["note"].lower())

    def test_exhibit_narration_text(self):
        intro = exhibit.narration_payload("southwestern_skies", 0)
        self.assertEqual(intro["kind"], "exhibit_step")
        self.assertFalse(intro["audio_autoplay"])
        self.assertIn("living traditions", intro["text"].lower())
        self.assertIn("archaeological interpretation", intro["text"].lower())
        same = exhibit.narration_payload("southwestern_skies", 1)
        text = same["text"].lower()
        self.assertIn("taurus", text)
        self.assertIn("matariki", text)
        self.assertIn("thurayy", text)
        self.assertIn("tianquiztli", text)
        self.assertIn("distinct", text)
        chaco = exhibit.narration_payload("southwestern_skies", 2)
        self.assertIn("archaeological", chaco["text"].lower())
        fajada = exhibit.narration_payload("southwestern_skies", 3)
        self.assertTrue("researchers interpret" in fajada["text"].lower() or "researchers have interpreted" in fajada["text"].lower() or "archaeological interpretation" in fajada["text"].lower())
        holly = exhibit.narration_payload("southwestern_skies", 4)
        self.assertIn("holly", holly["text"].lower())
        historical = exhibit.narration_payload("southwestern_skies", 5)
        self.assertIn("modern astronomical simulation", historical["text"].lower())
        templo = exhibit.narration_payload("southwestern_skies", 6)
        self.assertIn("mexica", templo["text"].lower())
        self.assertNotIn("maya classroom", templo["text"].lower())
        tian = exhibit.narration_payload("southwestern_skies", 7)
        self.assertIn("mexica historical sources", tian["text"].lower())
        self.assertIn("not a modern nahua", tian["text"].lower())
        close = exhibit.narration_payload("southwestern_skies", 8)
        self.assertIn("does not claim a shared origin", close["text"].lower())

    def test_media_refs_resolve_to_existing_systems(self):
        view = exhibit.step_payload("southwestern_skies", 1)
        media = view["step"]["media"]
        self.assertEqual(media["signals"]["registry"], "cosmic_signal_registry")
        self.assertTrue(media["manual_only"])
        self.assertFalse(media["autoplay"])
        smoke = exhibit.step_payload("exhibit_smoke_orion", 1)
        self.assertEqual(smoke["step"]["story_id"], "orion")

    def test_modern_iau_step_has_no_archaeo_badge(self):
        view = exhibit.step_payload("exhibit_smoke_orion", 1)
        labels = [item["label"] for item in view["step"]["evidence_badges"]]
        self.assertNotIn("STRONG EVIDENCE", labels)
        self.assertNotIn("SCHOLARLY INTERPRETATION", labels)

    def test_chaco_and_fajada_badges(self):
        chaco = exhibit.step_payload("southwestern_skies", 2)
        labels = [item["label"] for item in chaco["step"]["evidence_badges"]]
        self.assertIn("STRONG EVIDENCE", labels)
        fajada = exhibit.step_payload("southwestern_skies", 3)
        labels = [item["label"] for item in fajada["step"]["evidence_badges"]]
        self.assertIn("SCHOLARLY INTERPRETATION", labels)
        self.assertEqual(fajada["step"]["visual"]["schematic_label"], "interpretive schematic")

    def test_smoke_fixture_hidden_from_list(self):
        listed = {item["id"] for item in exhibit.list_exhibits()["exhibits"]}
        self.assertIn("southwestern_skies", listed)
        self.assertIn("hear_the_universe", listed)
        self.assertIn("ancient_skywatchers", listed)
        self.assertNotIn("exhibit_smoke_orion", listed)
        self.assertTrue(exhibit.exhibit_payload("exhibit_smoke_orion")["ok"])


class TestHearTheUniverseExhibit(unittest.TestCase):
    def setUp(self):
        exhibit.reload_registry()

    def test_schema_and_duration(self):
        payload = exhibit.exhibit_payload("hear_the_universe")
        self.assertTrue(payload["ok"])
        card = payload["exhibit"]
        self.assertEqual(card["id"], "hear_the_universe")
        self.assertEqual(card["theme"], "scientific_audio")
        self.assertEqual(card["step_count"], 11)
        self.assertEqual(card["estimated_minutes"], 22)
        self.assertFalse(payload["audio_autoplay"])
        self.assertFalse(payload["auto_advance_default"])
        types = [step["step_type"] for step in card["steps"]]
        self.assertEqual(types[0], "intro")
        self.assertEqual(types[-1], "outro")
        self.assertIn("cosmic_signal", types)
        self.assertIn("data_sonification", types)
        self.assertNotIn("hear_the_universe", exhibit.list_exhibits()["future_exhibit_ids"])

    def test_inventory_covers_enabled_signals(self):
        from app import cosmic_signal_registry

        inventory = exhibit.cosmic_signal_inventory()
        enabled = {entry["id"] for entry in cosmic_signal_registry.enabled_entries()}
        self.assertEqual({row["id"] for row in inventory}, enabled)
        self.assertEqual(len(inventory), 21)
        by_id = {row["id"]: row for row in inventory}
        self.assertEqual(by_id["jupiter_juno_waves_bow_shock"]["suitability"], "exhibit_primary")
        self.assertTrue(by_id["jupiter_juno_waves_bow_shock"]["direct_measurement_derived"])
        self.assertFalse(by_id["jupiter_juno_waves_bow_shock"]["sonification"])
        self.assertEqual(by_id["voyager1_interstellar_plasma_pia17045"]["suitability"], "exhibit_primary")
        self.assertTrue(by_id["voyager1_interstellar_plasma_pia17045"]["audification"])
        self.assertEqual(by_id["cassiopeia_a_chandra_sonification"]["suitability"], "exhibit_primary")
        self.assertTrue(by_id["cassiopeia_a_chandra_sonification"]["sonification"])
        self.assertEqual(by_id["msh_15_52_chandra_ixpe_sonification"]["suitability"], "exhibit_related")
        self.assertTrue(by_id["msh_15_52_chandra_ixpe_sonification"]["timing_pulsation_based"])
        self.assertFalse(by_id["crab_nebula_chandra_sonification"]["timing_pulsation_based"])

    def test_only_enabled_canonical_signals_and_no_duplicates(self):
        card = exhibit.get_exhibit("hear_the_universe")
        primaries = []
        for step in card["steps"]:
            sid = step.get("cosmic_signal_id")
            if sid:
                self.assertIsNotNone(exhibit._signal_entry(sid))
                primaries.append(sid)
            for extra in (step.get("related_signal_ids") or []) + (step.get("cosmic_signal_ids") or []):
                self.assertIsNotNone(exhibit._signal_entry(extra))
            if step.get("compare_signal_id"):
                self.assertIsNotNone(exhibit._signal_entry(step["compare_signal_id"]))
        self.assertEqual(len(primaries), len(set(primaries)))
        self.assertEqual(primaries.count("cassiopeia_a_chandra_sonification"), 1)

    def test_signal_classifications_and_hearing_cards(self):
        jupiter = exhibit.step_payload("hear_the_universe", 1)
        labels = [item["label"] for item in jupiter["step"]["evidence_badges"]]
        self.assertIn("MEASURED SIGNAL", labels)
        self.assertIn("MEASUREMENT-DERIVED AUDIO", labels)
        self.assertNotIn("DATA SONIFICATION", labels)
        card = jupiter["step"]["hearing_card"]
        self.assertEqual(card["title"], "What Am I Hearing?")
        self.assertIn("Waves", card["source_instrument_mission"])
        self.assertIn("University of Iowa", card["provider"])
        self.assertTrue(card["mapping_documented"])
        crab = exhibit.step_payload("hear_the_universe", 3)
        crab_labels = [item["label"] for item in crab["step"]["evidence_badges"]]
        self.assertIn("DATA SONIFICATION", crab_labels)
        self.assertNotIn("PULSE / TIMING DATA", crab_labels)
        casa = exhibit.step_payload("hear_the_universe", 4)
        self.assertEqual(casa["step"]["media"]["signals"]["canonical_id"], "cassiopeia_a_chandra_sonification")
        self.assertEqual(len(casa["step"]["media"]["signals"]["ranked"]), 1)
        self.assertFalse(casa["step"]["media"]["autoplay"])
        self.assertTrue(casa["step"]["media"]["manual_only"])
        voyager = exhibit.step_payload("hear_the_universe", 7)
        voyager_labels = [item["label"] for item in voyager["step"]["evidence_badges"]]
        self.assertIn("AUDIFICATION", voyager_labels)
        compare = exhibit.step_payload("hear_the_universe", 8)
        generated = compare["step"]["media"]["generated_hearing_card"]
        official = compare["step"]["media"]["compare_signal"]["hearing_card"]
        self.assertEqual(generated["transformation_type"], "GENERATED CARTOGRAPHY SONIFICATION")
        self.assertTrue(generated["generated"])
        self.assertFalse(official["generated"])
        self.assertEqual(official["transformation_type"], "DATA SONIFICATION")
        self.assertNotEqual(generated["provider"], official["provider"])

    def test_no_unsupported_mapping_claims(self):
        fake = {
            "id": "undocumented",
            "media_type": "data_sonification",
            "attribution": "Test",
        }
        card = exhibit.hearing_card(fake)
        self.assertEqual(card["frequency_mapping"], exhibit.MAPPING_UNAVAILABLE)
        self.assertEqual(card["time_scaling"], exhibit.MAPPING_UNAVAILABLE)
        self.assertFalse(card["mapping_documented"])
        saturn = exhibit.hearing_card(exhibit._signal_entry("saturn_chandra_cassini_sonification"))
        self.assertIn("right", saturn["frequency_mapping"].lower())
        self.assertNotIn("invented", saturn["frequency_mapping"].lower())

    def test_object_focus_mapping_documents_galactic_center(self):
        rows = exhibit.object_focus_map(exhibit.get_exhibit("hear_the_universe"))
        by_step = {row["step_id"]: row for row in rows}
        self.assertEqual(by_step["htu_jupiter"]["stellarium_focus"], "Jupiter")
        self.assertEqual(by_step["htu_saturn"]["stellarium_focus"], "Saturn")
        self.assertEqual(by_step["htu_crab"]["stellarium_focus"], "Crab Nebula")
        self.assertEqual(by_step["htu_casa"]["stellarium_focus"], "Cassiopeia A")
        self.assertEqual(by_step["htu_gcenter"]["stellarium_focus"], "Sagittarius A East")
        self.assertIn("Sagittarius A*", by_step["htu_gcenter"]["search_name_note"])
        self.assertEqual(by_step["htu_andromeda"]["stellarium_focus"], "Andromeda Galaxy")

    def test_sources_and_media_provenance(self):
        payload = exhibit.exhibit_payload("hear_the_universe")
        sourced = [group for group in payload["exhibit"]["sources"] if group["sources"]]
        self.assertGreaterEqual(len(sourced), 7)
        casa = exhibit.step_payload("hear_the_universe", 4)
        self.assertTrue(casa["step"]["media"]["spectra"]["ranked"])
        self.assertTrue(casa["step"]["media"].get("official_media_title"))
        self.assertFalse(casa["audio_autoplay"])
        saturn = exhibit.step_payload("hear_the_universe", 2)
        self.assertIn("Enceladus", saturn["narration"]["text"])

    def test_narration_distinguishes_providers_and_strips_urls(self):
        intro = exhibit.narration_payload("hear_the_universe", 0)
        self.assertIn("pressure wave", intro["text"].lower())
        self.assertIn("vacuum", intro["text"].lower())
        self.assertNotIn("http", intro["text"].lower())
        gcenter = exhibit.narration_payload("hear_the_universe", 5)
        self.assertIn("data sonification", gcenter["text"].lower())
        self.assertIn("nasa", gcenter["text"].lower())
        compare = exhibit.narration_payload("hear_the_universe", 8)
        self.assertIn("cartography is generating", compare["text"].lower())
        self.assertIn("nasa and chandra provide", compare["text"].lower())
        outro = exhibit.narration_payload("hear_the_universe", 10)
        self.assertIn("not hearing the vacuum", outro["text"].lower())
        for index in range(11):
            text = exhibit.narration_payload("hear_the_universe", index)["text"]
            self.assertNotIn("http://", text)
            self.assertNotIn("https://", text)
            self.assertFalse(exhibit.narration_payload("hear_the_universe", index)["audio_autoplay"])

    def test_duplicate_primary_signal_rejected(self):
        raw = copy.deepcopy(exhibit.get_exhibit("hear_the_universe"))
        raw["id"] = "dup_signals"
        raw["steps"][4]["cosmic_signal_id"] = "jupiter_juno_waves_bow_shock"
        with self.assertRaises(exhibit.ExhibitError) as ctx:
            exhibit.validate_exhibit(raw)
        self.assertIn("duplicates primary", str(ctx.exception).lower())

    def test_unknown_signal_rejected(self):
        raw = copy.deepcopy(exhibit.get_exhibit("hear_the_universe"))
        raw["id"] = "bad_signal"
        raw["steps"][1]["cosmic_signal_id"] = "not_a_real_signal"
        with self.assertRaises(exhibit.ExhibitError):
            exhibit.validate_exhibit(raw)


class TestExhibitApiAndStellarium(unittest.TestCase):
    def setUp(self):
        exhibit.reset_session()
        status = canned_json(
            {
                "time": {
                    "utc": "2026-10-10T04:00:00",
                    "jday": 2460963.6666667,
                    "isTimeNow": True,
                    "timeZone": "UTC",
                },
                "location": {
                    "latitude": 39.1,
                    "longitude": -104.85,
                    "altitude": 1600,
                    "name": "Monument",
                    "planet": "Earth",
                },
                "view": {"fov": 20},
            }
        )
        info = load_sample("official_getinfo_shape_response.json")
        self.fake = FakeStellariumServer(objects_info_body=info, main_status_body=status)
        self.fake.start()
        self.httpd = run_server(host="127.0.0.1", port=0, stellarium_base_url=self.fake.base_url)
        self.port = self.httpd.server_address[1]
        self.base = f"http://127.0.0.1:{self.port}"
        import threading

        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=2)
        self.fake.stop()
        exhibit.reset_session()

    def test_list_and_get_endpoints(self):
        status, data = _get(f"{self.base}/api/exhibits")
        self.assertEqual(status, 200)
        ids = [item["id"] for item in data["exhibits"]]
        self.assertIn("southwestern_skies", ids)
        self.assertIn("hear_the_universe", ids)
        self.assertIn("ancient_skywatchers", ids)
        self.assertNotIn("exhibit_smoke_orion", ids)
        status, data = _get(f"{self.base}/api/exhibit/southwestern_skies")
        self.assertEqual(status, 200)
        self.assertEqual(data["exhibit"]["step_count"], 10)
        status, data = _get(f"{self.base}/api/exhibit/southwestern_skies/step/1")
        self.assertTrue(data["ok"])
        self.assertEqual(data["step"]["step_type"], "same_sky_comparison")
        code, data = _get_error(f"{self.base}/api/exhibit/nope")
        self.assertEqual(code, 404)
        self.assertFalse(data["ok"])

    def test_start_does_not_change_time(self):
        status, data = _post(f"{self.base}/api/exhibit/southwestern_skies/start", {})
        self.assertEqual(status, 200)
        self.assertTrue(data["ok"])
        self.assertFalse(data["audio_autoplay"])
        self.assertEqual(data["step_index"], 0)
        self.assertIsNone(self.fake.posted_time)
        self.assertIn("captured_state", data)
        self.assertIn("restore_payload", data)

    def test_navigation_and_no_silent_time(self):
        _post(f"{self.base}/api/exhibit/southwestern_skies/start", {})
        for _ in range(5):
            status, data = _post(f"{self.base}/api/exhibit/southwestern_skies/step", {"direction": "next"})
            self.assertTrue(data["ok"])
            self.assertFalse(data["applies_time_silently"])
        self.assertEqual(data["step"]["step_type"], "historical_reconstruction")
        self.assertTrue(data["step"]["historical_confirmation"]["required"])
        self.assertIsNone(self.fake.posted_time)
        status, applied = _post(
            f"{self.base}/api/exhibit/southwestern_skies/step",
            {"action": "apply_historical"},
        )
        self.assertTrue(applied["ok"])
        self.assertTrue(applied["historical_applied"])
        self.assertEqual(applied["reconstruction_label"], "astronomical reconstruction")
        self.assertIsNotNone(self.fake.posted_time)
        self.assertIn("timerate", self.fake.posted_time)

    def test_stop_restore_payload(self):
        started = _post(f"{self.base}/api/exhibit/southwestern_skies/start", {})[1]
        status, data = _post(f"{self.base}/api/exhibit/southwestern_skies/stop", {"restore": True})
        self.assertEqual(status, 200)
        self.assertFalse(data["active"])
        self.assertIn("restore_payload", data)
        self.assertEqual(data["restore_payload"]["location_name"], started["captured_state"]["location_name"])

    def test_narration_endpoint_exhibit_step(self):
        status, data = _get(f"{self.base}/api/narration?kind=exhibit_step&exhibit=southwestern_skies&step=0")
        self.assertEqual(status, 200)
        self.assertEqual(data["kind"], "exhibit_step")
        self.assertFalse(data["audio_autoplay"])
        self.assertTrue(data["text"])

    def test_experience_kind_exhibit_step(self):
        payload = experience.narration_payload({}, {}, kind="exhibit_step")
        self.assertEqual(payload["kind"], "exhibit_step")
        self.assertFalse(payload["audio_autoplay"])

    def test_hear_the_universe_start_no_autoplay_or_time_change(self):
        status, data = _post(f"{self.base}/api/exhibit/hear_the_universe/start", {})
        self.assertEqual(status, 200)
        self.assertTrue(data["ok"])
        self.assertFalse(data["audio_autoplay"])
        self.assertFalse(data["media_autoplay"])
        self.assertEqual(data["step"]["step_type"], "intro")
        self.assertTrue(data["step"]["sound_explainer"])
        self.assertIsNone(self.fake.posted_time)
        status, nxt = _post(f"{self.base}/api/exhibit/hear_the_universe/step", {"direction": "next"})
        self.assertEqual(nxt["step"]["cosmic_signal_id"], "jupiter_juno_waves_bow_shock")
        self.assertFalse(nxt["audio_autoplay"])
        self.assertEqual(nxt["step"]["stellarium_focus"], "Jupiter")
        stopped = _post(f"{self.base}/api/exhibit/hear_the_universe/stop", {"restore": True})[1]
        self.assertFalse(stopped["active"])
        self.assertIn("restore_payload", stopped)

    def test_ancient_skywatchers_start_and_historical_explicit(self):
        status, data = _post(f"{self.base}/api/exhibit/ancient_skywatchers/start", {})
        self.assertEqual(status, 200)
        self.assertTrue(data["ok"])
        self.assertFalse(data["audio_autoplay"])
        self.assertEqual(data["step"]["step_id"], "asw_intro")
        self.assertIsNone(self.fake.posted_time)
        view = data
        while view.get("has_next") and view["step"]["step_type"] != "historical_reconstruction":
            view = _post(f"{self.base}/api/exhibit/ancient_skywatchers/step", {"direction": "next"})[1]
        self.assertEqual(view["step"]["step_type"], "historical_reconstruction")
        self.assertTrue(view["step"]["historical_confirmation"]["required"])
        self.assertIsNone(self.fake.posted_time)
        applied = _post(
            f"{self.base}/api/exhibit/ancient_skywatchers/step",
            {"action": "apply_historical"},
        )[1]
        self.assertTrue(applied["ok"])
        self.assertTrue(applied["historical_applied"])
        self.assertEqual(applied["reconstruction_label"], "astronomical reconstruction")
        self.assertIsNotNone(self.fake.posted_time)
        stopped = _post(f"{self.base}/api/exhibit/ancient_skywatchers/stop", {"restore": True})[1]
        self.assertFalse(stopped["active"])
        self.assertIn("restore_payload", stopped)


class TestAncientSkywatchersExhibit(unittest.TestCase):
    def setUp(self):
        exhibit.reload_registry()

    def test_schema_and_duration(self):
        payload = exhibit.exhibit_payload("ancient_skywatchers")
        self.assertTrue(payload["ok"])
        card = payload["exhibit"]
        self.assertEqual(card["id"], "ancient_skywatchers")
        self.assertEqual(card["theme"], "historical_astronomy")
        self.assertEqual(card["step_count"], 14)
        self.assertEqual(card["estimated_minutes"], 28)
        self.assertFalse(payload["audio_autoplay"])
        types = [step["step_type"] for step in card["steps"]]
        self.assertEqual(types[0], "intro")
        self.assertEqual(types[-1], "outro")
        self.assertIn("archaeoastronomy", types)
        self.assertIn("historical_reconstruction", types)
        self.assertIn("same_sky_comparison", types)
        self.assertNotIn("ancient_skywatchers", exhibit.list_exhibits()["future_exhibit_ids"])
        self.assertTrue(card["tools_of_the_sky"])

    def test_production_stories_only_and_deferred_excluded(self):
        card = exhibit.get_exhibit("ancient_skywatchers")
        for story_id in card["story_ids"]:
            story = constellation_story.get_story(story_id)
            self.assertIsNotNone(story)
            self.assertTrue(story.get("enabled"))
            self.assertNotIn(story.get("public_story_status"), exhibit.RESTRICTED_STATUSES)
            self.assertNotIn(constellation_story._story_culture_id(story), exhibit.BLOCKED_CULTURES_UNLESS_READY)
        blob = " ".join(card["story_ids"] + list(card.get("culture_scope") or [])).lower()
        for token in ("dine", "diné", "navajo", "apache", "hopi", "zuni", "acoma", "taos", "mesa_verde"):
            self.assertNotIn(token, blob)
        self.assertNotIn("mesa_verde_sun_temple", json.dumps(card))

    def test_inventory_covers_exhibit_stories(self):
        inventory = exhibit.ancient_skywatchers_inventory()
        ids = {row["story_visual"] for row in inventory}
        self.assertEqual(ids, set(exhibit.get_exhibit("ancient_skywatchers")["story_ids"]))
        by_id = {row["story_visual"]: row for row in inventory}
        self.assertEqual(by_id["ancestral_puebloan_chaco_cardinal"]["confidence"], "strong_evidence")
        self.assertEqual(by_id["ancestral_puebloan_fajada_sun_dagger"]["confidence"], "scholarly_interpretation")

    def test_evidence_and_teaching_cards(self):
        chaco = exhibit.step_payload("ancient_skywatchers", 2)
        labels = [item["label"] for item in chaco["step"]["evidence_badges"]]
        self.assertIn("STRONG EVIDENCE", labels)
        self.assertIn("ARCHAEOLOGICAL INFERENCE", labels)
        self.assertTrue(chaco["step"]["how_they_knew"]["fields"])
        self.assertIn("cardinal", " ".join(f["text"].lower() for f in chaco["step"]["how_they_knew"]["fields"]))
        fajada = exhibit.step_payload("ancient_skywatchers", 3)
        labels = [item["label"] for item in fajada["step"]["evidence_badges"]]
        self.assertIn("SCHOLARLY INTERPRETATION", labels)
        self.assertEqual(fajada["step"]["visual"]["schematic_label"], "interpretive schematic")
        holly = exhibit.step_payload("ancient_skywatchers", 4)
        self.assertTrue(holly["step"]["how_they_knew"])
        templo = exhibit.step_payload("ancient_skywatchers", 5)
        text = templo["narration"]["text"].lower()
        self.assertIn("mexica", text)
        self.assertNotIn("maya classroom", text)
        tian = exhibit.step_payload("ancient_skywatchers", 6)
        labels = [item["label"] for item in tian["step"]["evidence_badges"]]
        self.assertIn("HISTORICAL SOURCE", labels)
        self.assertTrue(tian["step"]["scientific_view"])
        thurayya = exhibit.step_payload("ancient_skywatchers", 7)
        labels = [item["label"] for item in thurayya["step"]["evidence_badges"]]
        self.assertIn("CULTURAL SKY KNOWLEDGE", labels)
        self.assertNotIn("arab mythology", thurayya["narration"]["text"].lower())
        matariki = exhibit.step_payload("ancient_skywatchers", 8)
        labels = [item["label"] for item in matariki["step"]["evidence_badges"]]
        self.assertIn("CULTURAL SKY KNOWLEDGE", labels)
        self.assertIn("COMMUNITY-SOURCED", labels)
        self.assertIn("iwi", matariki["narration"]["text"].lower())
        self.assertIn("not generalize", matariki["narration"]["text"].lower())
        beidou = exhibit.step_payload("ancient_skywatchers", 9)
        labels = [item["label"] for item in beidou["step"]["evidence_badges"]]
        self.assertIn("CULTURAL SKY KNOWLEDGE", labels)
        self.assertIn("xingguan", beidou["narration"]["text"].lower())
        self.assertIn("not iau", beidou["narration"]["text"].lower())
        sufi = exhibit.step_payload("ancient_skywatchers", 10)
        labels = [item["label"] for item in sufi["step"]["evidence_badges"]]
        self.assertIn("HISTORICAL ASTRONOMY", labels)
        sufi_text = sufi["narration"]["text"].lower()
        self.assertTrue("ṣūfī" in sufi_text or "sufi" in sufi_text)
        self.assertIn("not merged", sufi_text)

    def test_historical_reconstruction_requires_explicit_action(self):
        step = next(
            item
            for item in exhibit.get_exhibit("ancient_skywatchers")["steps"]
            if item["step_type"] == "historical_reconstruction"
        )
        self.assertTrue(step["user_action_required"])
        self.assertTrue(step["time_machine_action"]["apply_requires_explicit_action"])
        self.assertFalse(step["time_machine_action"]["silent_apply"])
        confirm = exhibit.historical_confirmation(step)
        self.assertTrue(confirm["apply_requires_explicit_action"])
        self.assertIn("AD 1050", confirm["prompt"])
        self.assertEqual(step["time_machine_action"]["date_id"], "chaco_ad1050_equinox")

    def test_no_unsupported_exact_dates_or_urls_in_narration(self):
        for index in range(14):
            text = exhibit.narration_payload("ancient_skywatchers", index)["text"]
            self.assertNotIn("http://", text)
            self.assertNotIn("https://", text)
            self.assertFalse(exhibit.narration_payload("ancient_skywatchers", index)["audio_autoplay"])
        intro = exhibit.narration_payload("ancient_skywatchers", 0)["text"].lower()
        self.assertIn("naked-eye", intro)
        self.assertNotIn("primitive", intro)
        compare = exhibit.narration_payload("ancient_skywatchers", 11)["text"].lower()
        self.assertIn("distinct", compare)
        self.assertNotIn("shared origin", compare)
        outro = exhibit.narration_payload("ancient_skywatchers", 13)["text"].lower()
        self.assertIn("not all doing the same thing", outro)

    def test_sources_resolve_and_cosmic_signal_stays_secondary(self):
        payload = exhibit.exhibit_payload("ancient_skywatchers")
        sourced = [group for group in payload["exhibit"]["sources"] if group["sources"]]
        self.assertGreaterEqual(len(sourced), 8)
        for group in sourced:
            for src in group["sources"]:
                self.assertTrue(src.get("title"))
                self.assertTrue(src.get("institution"))
        chaco = exhibit.step_payload("ancient_skywatchers", 2)
        self.assertTrue(chaco["step"]["media"].get("suppress_cosmic_signal"))
        self.assertTrue(chaco["step"]["media"]["signals"]["empty"])
        self.assertFalse(chaco["step"]["media"]["autoplay"])
        tools = exhibit.step_payload("ancient_skywatchers", 13)
        self.assertTrue(tools["step"]["tools_of_the_sky"])
        lunar_ids = {item.get("id") for item in tools["step"]["tools_of_the_sky"]}
        self.assertNotIn("lunar_cycle", lunar_ids)

    def test_object_focus_mapping(self):
        rows = exhibit.object_focus_map(exhibit.get_exhibit("ancient_skywatchers"))
        by_step = {row["step_id"]: row for row in rows}
        self.assertEqual(by_step["asw_chaco"]["stellarium_focus"], "Sun")
        self.assertEqual(by_step["asw_tianquiztli"]["stellarium_focus"], "Pleiades")
        self.assertEqual(by_step["asw_beidou"]["stellarium_focus"], "Dubhe")
        self.assertEqual(by_step["asw_sufi"]["stellarium_focus"], "Vega")


if __name__ == "__main__":
    unittest.main()
