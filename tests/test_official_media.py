"""Targeted tests for the Official Media Layer. NASA is always mocked."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import cosmic_signal_registry
from app import official_media
from app.server import run_server


FIXTURES = Path(__file__).resolve().parent / "fixtures" / "sample_responses"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _fetcher_for(*payloads: dict):
    calls = []

    def fetch(url: str, timeout: float) -> dict:
        calls.append(url)
        if "asset/" in url:
            return _load("nasa_asset_video.json")
        if calls.count(url) > len(payloads):
            return payloads[-1]
        return payloads[min(len(calls) - 1, len(payloads) - 1)]

    fetch.calls = calls
    return fetch


class TestQueryAndUrlSafety(unittest.TestCase):
    def test_malformed_empty_query(self):
        result = official_media.validate_search_query("")
        self.assertFalse(result["ok"])

    def test_rejects_arbitrary_url_query(self):
        result = official_media.validate_search_query("https://evil.example/media.mp4")
        self.assertFalse(result["ok"])
        self.assertIn("URL", result["error"])

    def test_refuses_non_nasa_fetch(self):
        with self.assertRaises(official_media.OfficialMediaError):
            official_media._default_fetch("https://evil.example/search", 1)

    def test_malformed_item_id(self):
        result = official_media.get_item("../etc/passwd")
        self.assertFalse(result["ok"])
        self.assertIn("Malformed", result["error"])

    def test_rejects_unsafe_media_url(self):
        item = official_media.normalize_media_item(
            {
                "id": "nasa:X",
                "provider": "nasa",
                "media_url": "https://evil.example/a.mp4",
                "source_page_url": "https://evil.example/details/X",
            }
        )
        self.assertIsNone(item["media_url"])
        self.assertIsNone(item["source_page_url"])


class TestNasaParsingAndRanking(unittest.TestCase):
    def test_normalized_nasa_parse(self):
        items = official_media.parse_nasa_search_items(_load("nasa_media_jupiter.json"))
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["provider"], "nasa")
        self.assertEqual(items[0]["nasa_id"], "PIA21641")
        self.assertTrue(items[0]["source_page_url"].startswith("https://images.nasa.gov/details/"))
        self.assertFalse(items[0]["audio_autoplay"])

    def test_exact_object_match(self):
        items = official_media.parse_nasa_search_items(_load("nasa_media_jupiter.json"))
        terms = official_media.collect_object_terms({"name": "Jupiter"})
        ranked = official_media.rank_items(items, terms)
        self.assertTrue(ranked)
        self.assertEqual(ranked[0]["relation"], "exact")

    def test_alias_match(self):
        items = official_media.parse_nasa_search_items(_load("nasa_media_casa.json"))
        terms = official_media.collect_object_terms({"name": "Cas A"})
        ranked = official_media.rank_items(items, terms)
        self.assertTrue(any(i["relation"] == "exact" for i in ranked))

    def test_orion_nebula_is_related_for_betelgeuse(self):
        items = official_media.parse_nasa_search_items(_load("nasa_media_orion.json"))
        terms = official_media.collect_object_terms(
            {"name": "Betelgeuse", "constellation": "Ori"}
        )
        ranked = official_media.rank_items(items, terms)
        self.assertTrue(ranked)
        self.assertEqual(ranked[0]["relation"], "general")
        self.assertNotEqual(ranked[0]["relation"], "exact")

    def test_irrelevant_results_rejected(self):
        items = official_media.parse_nasa_search_items(_load("nasa_media_irrelevant.json"))
        terms = official_media.collect_object_terms({"name": "TYC 9999-1234-1"})
        ranked = official_media.rank_items(items, terms)
        self.assertEqual(ranked, [])

    def test_duplicate_suppression(self):
        items = official_media.parse_nasa_search_items(_load("nasa_media_duplicate.json"))
        self.assertEqual(len(items), 2)
        unique = official_media.suppress_duplicates(items)
        self.assertEqual(len(unique), 1)

    def test_playable_asset_and_captions(self):
        items = official_media.parse_nasa_search_items(_load("nasa_media_casa.json"))
        video = next(i for i in items if i["media_type"] == "video")
        with tempfile.TemporaryDirectory() as tmp:
            updated = official_media.attach_playable_asset(
                video,
                fetcher=_fetcher_for(_load("nasa_asset_video.json")),
                cache_dir=tmp,
            )
        self.assertTrue(updated["playable_inline"])
        self.assertTrue(str(updated["media_url"]).endswith(".mp4"))
        self.assertTrue(updated["caption_available"])


class TestCache(unittest.TestCase):
    def test_cache_hit_avoids_second_fetch(self):
        fetcher = _fetcher_for(_load("nasa_media_jupiter.json"))
        with tempfile.TemporaryDirectory() as tmp:
            first = official_media.search_nasa("Jupiter", fetcher=fetcher, cache_dir=tmp, now=1000)
            second = official_media.search_nasa("Jupiter", fetcher=fetcher, cache_dir=tmp, now=1001)
        self.assertFalse(first["cache_hit"])
        self.assertTrue(second["cache_hit"])
        self.assertEqual(len(fetcher.calls), 1)

    def test_cache_expiration(self):
        fetcher = _fetcher_for(_load("nasa_media_jupiter.json"), _load("nasa_media_jupiter.json"))
        with tempfile.TemporaryDirectory() as tmp:
            official_media.search_nasa("Jupiter", fetcher=fetcher, cache_dir=tmp, now=1000)
            expired = official_media.search_nasa("Jupiter", fetcher=fetcher, cache_dir=tmp, now=1000 + official_media.CACHE_TTL_OK_SEC + 1)
        self.assertFalse(expired["cache_hit"])
        self.assertEqual(len(fetcher.calls), 2)

    def test_upstream_failure_is_cached_briefly(self):
        def boom(url, timeout):
            raise TimeoutError("nope")

        with tempfile.TemporaryDirectory() as tmp:
            first = official_media.search_nasa("Jupiter", fetcher=boom, cache_dir=tmp, now=50)
            second = official_media.search_nasa("Jupiter", fetcher=boom, cache_dir=tmp, now=51)
        self.assertFalse(first["ok"])
        self.assertEqual(first["status"], "timeout")
        self.assertTrue(second["cache_hit"])


class TestChandraAndCosmicReuse(unittest.TestCase):
    def test_chandra_exact_casa(self):
        terms = official_media.collect_object_terms({"name": "Cassiopeia A"})
        items = official_media.match_chandra(terms)
        ids = {i["id"] for i in items}
        self.assertIn("chandra:casa_sonification", ids)
        self.assertIn("chandra:casa_great_observatories_image", ids)

    def test_cosmic_signal_reused_not_duplicated(self):
        terms = official_media.collect_object_terms({"name": "Cassiopeia A"})
        nasa = official_media.parse_nasa_search_items(_load("nasa_media_casa.json"))
        nasa[0]["title"] = "Cassiopeia A Sonification"
        nasa[0]["signal_category"] = "sonification"
        nasa[0]["media_type"] = "sonification"
        ranked = official_media.rank_items(official_media.match_chandra(terms) + nasa, terms)
        sonify = [i for i in ranked if i.get("signal_category") == "sonification"]
        self.assertEqual(len(sonify), 1)
        self.assertTrue(sonify[0]["reuse_cosmic_signal"])
        self.assertEqual(sonify[0]["cosmic_signal_id"], "cassiopeia_a_chandra_sonification")
        self.assertFalse(sonify[0]["playable_inline"])
        self.assertIsNone(sonify[0]["media_url"])

    def test_existing_signal_count_preserved(self):
        self.assertEqual(official_media.cosmic_signal_entry_count(), 21)
        enabled = [e for e in cosmic_signal_registry.load_registry()["entries"] if e.get("enabled")]
        self.assertEqual(len(enabled), 21)

    def test_no_second_signal_registry(self):
        self.assertTrue(official_media.CHANDRA_REGISTRY_PATH.exists())
        raw = json.loads(official_media.CHANDRA_REGISTRY_PATH.read_text(encoding="utf-8"))
        for entry in raw["entries"]:
            if entry.get("reuse_cosmic_signal"):
                self.assertTrue(entry.get("cosmic_signal_id"))


class TestContextAndNarration(unittest.TestCase):
    def test_no_media_state(self):
        result = official_media.media_context(
            {"name": "TYC 9999-1234-1"},
            include_nasa=True,
            fetcher=_fetcher_for(_load("nasa_media_irrelevant.json")),
        )
        self.assertTrue(result["ok"])
        self.assertTrue(result["empty"])
        self.assertIsNone(result["featured"])
        self.assertFalse(result["audio_autoplay"])

    def test_media_types(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = official_media.search_media(
                "Jupiter",
                media_type="video",
                fetcher=_fetcher_for(_load("nasa_media_jupiter.json")),
                cache_dir=tmp,
            )
        self.assertTrue(any(i["media_type"] == "video" for i in result["items"]))

    def test_narration_metadata(self):
        fields = official_media.curated_narration_fields({"name": "Cassiopeia A"})
        self.assertEqual(fields["official_media_provider"], "Chandra X-ray Center")
        self.assertEqual(fields["official_media_relation"], "exact")
        self.assertIn("chandra.si.edu", fields["official_media_source_url"])
        self.assertIn("not official NASA narration", fields["official_media_note"])
        self.assertFalse(fields["audio_autoplay"])
        self.assertIn("sonification", fields["official_media_note"])
        self.assertNotIn("http", fields["official_media_note"])

    def test_exact_nasa_media_is_mentioned(self):
        fields = official_media.media_narration_fields(
            {"name": "Orion Nebula"},
            {
                "relation": "exact",
                "provider": "nasa",
                "provider_label": "NASA",
                "title": "Orion Nebula",
                "media_type": "image",
            },
        )
        self.assertIn("Image and Video Library", fields["official_media_note"])
        self.assertNotIn("http", fields["official_media_note"])

    def test_weak_general_media_is_not_narrated_as_exact(self):
        fields = official_media.media_narration_fields(
            {"name": "TYC 1234-5678-1"},
            {
                "relation": "general",
                "provider": "nasa",
                "title": "Star field",
                "media_type": "image",
            },
        )
        self.assertIsNone(fields["official_media_note"])
        self.assertIsNone(fields["official_media_title"])

    def test_related_media_is_not_narrated_as_exact(self):
        fields = official_media.media_narration_fields(
            {"name": "Betelgeuse"},
            {
                "relation": "related",
                "provider": "chandra",
                "title": "Nearby remnant",
                "signal_category": "sonification",
            },
        )
        self.assertIsNone(fields["official_media_note"])

    def test_experience_narration_includes_media_fields(self):
        from app import experience

        payload = experience.narration_payload({"name": "Cassiopeia A", "ok": True})
        self.assertEqual(payload["official_media_title"], "Cassiopeia A Sonification")
        self.assertFalse(payload["audio_autoplay"])


class TestServerMediaEndpoints(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        fetcher = _fetcher_for(_load("nasa_media_jupiter.json"), _load("nasa_asset_video.json"))
        self.httpd = run_server(
            host="127.0.0.1",
            port=0,
            stellarium_base_url="http://127.0.0.1:1",
            media_fetcher=fetcher,
            media_cache_dir=self.tmp.name,
        )
        import threading

        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.httpd.server_address[1]}"

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=2)
        self.tmp.cleanup()

    def _get(self, path: str):
        import urllib.request

        with urllib.request.urlopen(self.base + path, timeout=3) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))

    def _get_status(self, path: str) -> int:
        import urllib.error
        import urllib.request

        try:
            with urllib.request.urlopen(self.base + path, timeout=3) as resp:
                return resp.status
        except urllib.error.HTTPError as exc:
            exc.read()
            exc.close()
            return exc.code

    def test_search_endpoint(self):
        status, data = self._get("/api/media/search?q=Jupiter&media_type=all")
        self.assertEqual(status, 200)
        self.assertTrue(data["items"])
        self.assertFalse(data["audio_autoplay"])

    def test_context_endpoint(self):
        status, data = self._get("/api/media/context?object=Cassiopeia%20A")
        self.assertEqual(status, 200)
        self.assertFalse(data["empty"])
        self.assertTrue(data["featured"]["reuse_cosmic_signal"] or data["featured"]["provider"] in {"chandra", "nasa"})

    def test_item_endpoint_chandra(self):
        status, data = self._get("/api/media/item/chandra:casa_sonification")
        self.assertEqual(status, 200)
        self.assertEqual(data["item"]["cosmic_signal_id"], "cassiopeia_a_chandra_sonification")

    def test_malformed_item_404(self):
        self.assertEqual(self._get_status("/api/media/item/not-valid"), 404)

    def test_no_autoplay_flag(self):
        _, data = self._get("/api/media/context?object=Jupiter")
        self.assertFalse(data["audio_autoplay"])
