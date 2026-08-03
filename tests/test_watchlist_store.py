import json
import os
import tempfile
import unittest

from app import watchlist_store


class TestWatchlistStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_add_remove_favorite_note(self):
        doc = watchlist_store.empty_document()
        entry = watchlist_store.entry_from_target(
            {"name": "M31", "ra_deg": 10.0, "dec_deg": 41.0, "source": "manual"}
        )
        doc = watchlist_store.normalize_document({"schema_version": 1, "entries": [entry]})
        self.assertEqual(len(doc["entries"]), 1)
        doc["entries"][0]["favorite"] = True
        doc["entries"][0]["personal_note"] = "test note"
        saved = watchlist_store.save_watchlist(doc, app_root=self.root)
        self.assertTrue(saved["entries"][0]["favorite"])
        self.assertEqual(saved["entries"][0]["personal_note"], "test note")

    def test_duplicate_add_handling(self):
        entry = watchlist_store.entry_from_target(
            {"name": "M31", "ra_deg": 10.0, "dec_deg": 41.0, "object_type": "galaxy", "source": "manual"}
        )
        entry2 = watchlist_store.entry_from_target(
            {"name": "Andromeda", "ra_deg": 10.00001, "dec_deg": 41.00001, "object_type": "galaxy", "source": "manual"}
        )
        doc = watchlist_store.normalize_document({"schema_version": 1, "entries": [entry, entry2]})
        self.assertEqual(len(doc["entries"]), 1)

    def test_atomic_save_and_backup(self):
        doc = watchlist_store.empty_document()
        watchlist_store.save_watchlist(doc, app_root=self.root)
        path = watchlist_store.watchlist_path(self.root)
        bak = watchlist_store.backup_path(self.root)
        doc["entries"] = [watchlist_store.entry_from_target({"name": "A", "ra_deg": 1, "dec_deg": 2, "source": "manual"})]
        watchlist_store.save_watchlist(doc, app_root=self.root)
        self.assertTrue(os.path.isfile(path))
        self.assertTrue(os.path.isfile(bak))

    def test_malformed_json_recovery(self):
        runtime = watchlist_store.default_runtime_dir(self.root)
        os.makedirs(runtime, exist_ok=True)
        path = watchlist_store.watchlist_path(self.root)
        bak = watchlist_store.backup_path(self.root)
        good = watchlist_store.empty_document()
        with open(bak, "w", encoding="utf-8") as f:
            json.dump(good, f)
        with open(path, "w", encoding="utf-8") as f:
            f.write("{bad")
        loaded = watchlist_store.load_watchlist_result(app_root=self.root)
        self.assertTrue(loaded["ok"])
        self.assertEqual(loaded["status"], "recovered_from_backup")

    def test_load_failed_not_silent_empty(self):
        runtime = watchlist_store.default_runtime_dir(self.root)
        os.makedirs(runtime, exist_ok=True)
        path = watchlist_store.watchlist_path(self.root)
        with open(path, "w", encoding="utf-8") as f:
            f.write("{bad")
        loaded = watchlist_store.load_watchlist_result(app_root=self.root)
        self.assertFalse(loaded["ok"])
        self.assertEqual(loaded["status"], "load_failed")
        self.assertIsNone(loaded["document"])

    def test_persisted_entries_survive_restart(self):
        moon = watchlist_store.entry_from_target(
            {"name": "Moon", "ra_deg": 1.0, "dec_deg": 2.0, "object_type": "moon", "source": "manual", "alt_name": "Moon"}
        )
        apophis = watchlist_store.build_apophis_seed_entry()
        doc = watchlist_store.normalize_document({"schema_version": 1, "entries": [moon, apophis]})
        watchlist_store.save_watchlist(doc, app_root=self.root)
        first = watchlist_store.load_watchlist_result(app_root=self.root)
        second = watchlist_store.load_watchlist_result(app_root=self.root)
        self.assertEqual(first["entry_count"], 2)
        self.assertEqual(second["entry_count"], 2)
        self.assertEqual(second["document"]["entries"][0]["display_name"], "Moon")

    def test_same_storage_path_when_cwd_changes(self):
        moon = watchlist_store.entry_from_target(
            {"name": "Moon", "ra_deg": 1.0, "dec_deg": 2.0, "object_type": "moon", "source": "manual"}
        )
        watchlist_store.save_watchlist({"schema_version": 1, "entries": [moon]}, app_root=self.root)
        original_cwd = os.getcwd()
        other = tempfile.mkdtemp()
        try:
            os.chdir(other)
            loaded = watchlist_store.load_watchlist_result(app_root=self.root)
            self.assertEqual(loaded["entry_count"], 1)
            self.assertEqual(loaded["document"]["entries"][0]["display_name"], "Moon")
        finally:
            os.chdir(original_cwd)
            import shutil
            shutil.rmtree(other, ignore_errors=True)

    def test_apophis_tracker_cache_roundtrip(self):
        summary = watchlist_store.apophis_summary_from_api(
            {"ok": True, "designation": "99942", "encounter_date": "2029-Apr-13 00:00", "retrieved_at": "2026-01-01T00:00:00Z"}
        )
        entry = watchlist_store.build_apophis_seed_entry()
        entry["tracker_cache"] = {"kind": "apophis", "retrieved_at": "2026-01-01T00:00:00Z", "summary": summary}
        doc = watchlist_store.normalize_document({"schema_version": 1, "entries": [entry]})
        saved = watchlist_store.save_watchlist(doc, app_root=self.root)
        self.assertIsNotNone(saved["entries"][0].get("tracker_cache"))

    def test_partial_write_recovery(self):
        runtime = watchlist_store.default_runtime_dir(self.root)
        os.makedirs(runtime, exist_ok=True)
        path = watchlist_store.watchlist_path(self.root)
        with open(path, "w", encoding="utf-8") as f:
            f.write('{"schema_version": 1, "entries": [')
        loaded = watchlist_store.load_watchlist(app_root=self.root)
        self.assertEqual(loaded["entries"], [])

    def test_schema_version_handling(self):
        doc = watchlist_store.normalize_document({"schema_version": 99, "entries": []})
        self.assertEqual(doc["schema_version"], watchlist_store.SCHEMA_VERSION)

    def test_apophis_seed_entry(self):
        entry = watchlist_store.build_apophis_seed_entry()
        self.assertEqual(entry["featured_kind"], "apophis")
        self.assertEqual(entry["provider_identifiers"]["jpl_sbdb"], "99942")

    def test_multiline_note_with_quotes_roundtrip(self):
        note = 'She said "hello"\nline two'
        entry = watchlist_store.entry_from_target(
            {"name": "Moon", "ra_deg": 1.0, "dec_deg": 2.0, "object_type": "moon", "source": "manual"}
        )
        entry["personal_note"] = note
        doc = watchlist_store.normalize_document({"schema_version": 1, "entries": [entry]})
        watchlist_store.save_watchlist(doc, app_root=self.root)
        loaded = watchlist_store.load_watchlist_result(app_root=self.root)
        self.assertEqual(loaded["document"]["entries"][0]["personal_note"], note)


if __name__ == "__main__":
    unittest.main()
