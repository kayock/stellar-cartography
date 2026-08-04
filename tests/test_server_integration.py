import json
import unittest
import urllib.request
import urllib.error
from pathlib import Path

from app.server import run_server
from app.stellarium_client import StellariumClient
from tests.fixtures.fake_stellarium_server import (
    FakeStellariumServer,
    load_sample,
    canned_json,
)


def _get(url):
    with urllib.request.urlopen(url, timeout=3) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


class ServerTestBase(unittest.TestCase):
    stellarium_base_url = "http://127.0.0.1:1"  # nothing listening, by default

    def setUp(self):
        self.httpd = run_server(host="127.0.0.1", port=0, stellarium_base_url=self.stellarium_base_url)
        import threading

        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.httpd.server_address[1]
        self.base = f"http://127.0.0.1:{self.port}"

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=2)


class TestStatusEndpointWhenStellariumDown(ServerTestBase):
    def test_status_reports_disconnected(self):
        status, data = _get(f"{self.base}/api/status")
        self.assertEqual(status, 200)
        self.assertFalse(data["connected"])

    def test_selection_reports_not_ok_but_no_crash(self):
        status, data = _get(f"{self.base}/api/selection")
        self.assertEqual(status, 200)
        self.assertFalse(data["ok"])
        self.assertFalse(data["connected"])
        self.assertIsNotNone(data["error"])


class TestManualModeIndependentOfStellarium(ServerTestBase):
    def test_manual_validate_works_with_stellarium_down(self):
        status, data = _get(f"{self.base}/api/manual/validate?ra=10.5&dec=-41.2")
        self.assertEqual(status, 200)
        self.assertTrue(data["ok"])
        self.assertAlmostEqual(data["ra_deg"], 10.5, places=3)
        self.assertAlmostEqual(data["dec_deg"], -41.2, places=3)

    def test_manual_validate_sexagesimal(self):
        status, data = _get(f"{self.base}/api/manual/validate?ra=05h35m17s&dec=-05d23m28s")
        self.assertTrue(data["ok"])
        self.assertLess(data["dec_deg"], 0)

    def test_manual_validate_invalid_input(self):
        status, data = _get(f"{self.base}/api/manual/validate?ra=banana&dec=banana")
        self.assertTrue(data["ok"] is False)
        self.assertIsNotNone(data.get("error"))

    def test_index_page_served(self):
        req = urllib.request.Request(f"{self.base}/")
        with urllib.request.urlopen(req, timeout=3) as resp:
            self.assertEqual(resp.status, 200)
            body = resp.read().decode("utf-8")
            self.assertIn("FOXAI Stellar Cartography", body)

    def test_static_asset_served(self):
        req = urllib.request.Request(f"{self.base}/static/styles.css")
        with urllib.request.urlopen(req, timeout=3) as resp:
            self.assertEqual(resp.status, 200)
            self.assertIn("text/css", resp.headers.get("Content-Type", ""))


class TestPathTraversalProtection(ServerTestBase):
    def test_dotdot_traversal_blocked(self):
        # urllib will normalize some of this, so try a couple of encodings.
        for suffix in ["../server.py", "..%2Fserver.py", "..\\server.py"]:
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(f"{self.base}/static/{suffix}", timeout=3)
            self.assertIn(ctx.exception.code, (403, 404))

    def test_disallowed_extension_blocked(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(f"{self.base}/static/../run.py", timeout=3)
        self.assertIn(ctx.exception.code, (403, 404))

    def test_unknown_route_is_404(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(f"{self.base}/definitely/not/a/route", timeout=3)
        self.assertEqual(ctx.exception.code, 404)


class TestSelectionEndpointWithFakeStellarium(unittest.TestCase):
    def setUp(self):
        self.fake = FakeStellariumServer(
            objects_info_body=canned_json({"name": "M 31", "raJ2000deg": 10.6847, "decJ2000deg": 41.26875})
        )
        self.fake.start()
        self.httpd = run_server(host="127.0.0.1", port=0, stellarium_base_url=self.fake.base_url)
        import threading

        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.httpd.server_address[1]
        self.base = f"http://127.0.0.1:{self.port}"

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=2)
        self.fake.stop()

    def test_status_connected(self):
        status, data = _get(f"{self.base}/api/status")
        self.assertTrue(data["connected"])

    def test_selection_ok(self):
        status, data = _get(f"{self.base}/api/selection")
        self.assertTrue(data["ok"])
        self.assertEqual(data["name"], "M 31")
        self.assertAlmostEqual(data["ra_deg"], 10.6847, places=3)
        # New About-This-Object fields must be present in the payload shape
        # even when the fake server didn't supply them (as None).
        for key in (
            "object_category",
            "object_subtype",
            "catalogue_designations",
            "constellation",
            "apparent_magnitude",
            "angular_size_deg",
            "altitude_deg",
            "azimuth_deg",
            "above_horizon",
        ):
            self.assertIn(key, data)


class TestStatusEndpointFailureSafe(unittest.TestCase):
    """/api/status must always return valid bridge JSON and must not take
    the request handler down, even when whatever is listening on the
    configured port (Stellarium or otherwise) answers with malformed,
    non-UTF-8, or oversized content (repair request item 3)."""

    def _run_against(self, main_status_body):
        fake = FakeStellariumServer(main_status_body=main_status_body)
        fake.start()
        httpd = run_server(host="127.0.0.1", port=0, stellarium_base_url=fake.base_url)
        import threading

        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        port = httpd.server_address[1]
        try:
            status, data = _get(f"http://127.0.0.1:{port}/api/status")
            self.assertEqual(status, 200)
            self.assertIn("connected", data)
            self.assertTrue(data["connected"])
        finally:
            httpd.shutdown()
            httpd.server_close()
            thread.join(timeout=2)
            fake.stop()

    def test_malformed_json_main_status(self):
        self._run_against(load_sample("malformed_response.txt"))

    def test_invalid_utf8_main_status(self):
        self._run_against(b"\xff\xfe\x00\x01not valid utf-8")

    def test_oversized_main_status(self):
        from app.stellarium_client import MAX_RESPONSE_BYTES

        self._run_against(b'{"padding": "' + (b"x" * (MAX_RESPONSE_BYTES + 100)) + b'"}')


class TestOfficialDocumentedShapeEndToEnd(unittest.TestCase):
    """StellariumClient -> /api/selection -> frontend target model.

    Proves the exact documented Stellarium getInfoMap payload from the
    R0.1.1 audit findings (numeric raJ2000/decJ2000, iauConstellation,
    size-dd, altitude, azimuth, above-horizon) survives all the way through
    the real HTTP server to the JSON the frontend consumes.
    """

    def setUp(self):
        self.fake = FakeStellariumServer(
            objects_info_body=load_sample("official_getinfo_shape_response.json"),
            main_status_body=load_sample("main_status_with_fov.json"),
        )
        self.fake.start()
        self.httpd = run_server(host="127.0.0.1", port=0, stellarium_base_url=self.fake.base_url)
        import threading

        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.httpd.server_address[1]
        self.base = f"http://127.0.0.1:{self.port}"

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=2)
        self.fake.stop()

    def test_official_shape_reaches_frontend_payload(self):
        status, data = _get(f"{self.base}/api/selection")
        self.assertEqual(status, 200)
        self.assertTrue(data["ok"], msg=data.get("error"))
        self.assertEqual(data["name"], "M 31")
        self.assertEqual(data["alt_name"], "Andromeda Galaxy")
        self.assertEqual(data["object_category"], "Nebula")
        self.assertEqual(data["object_type"], "galaxy")
        self.assertEqual(data["constellation"], "And")
        self.assertAlmostEqual(data["apparent_magnitude"], 3.44, places=2)
        self.assertAlmostEqual(data["angular_size_deg"], 3.167, places=3)
        self.assertAlmostEqual(data["altitude_deg"], 35.2, places=2)
        self.assertAlmostEqual(data["azimuth_deg"], 122.8, places=2)
        self.assertIs(data["above_horizon"], True)
        self.assertAlmostEqual(data["ra_deg"], 10.68470, places=4)
        self.assertAlmostEqual(data["dec_deg"], 41.26875, places=4)
        # FoV comes from the distinct /api/main/status response, not the
        # selection payload, and must still reach the frontend.
        self.assertAlmostEqual(data["fov_deg"], 5.2, places=2)


class TestSolarSystemSelectionEndToEnd(unittest.TestCase):
    """Moon and Saturn Stellarium shapes reach /api/selection for frontend detection."""

    def _run_selection(self, sample_name):
        fake = FakeStellariumServer(
            objects_info_body=load_sample(sample_name),
            main_status_body=load_sample("main_status_with_fov.json"),
        )
        fake.start()
        httpd = run_server(host="127.0.0.1", port=0, stellarium_base_url=fake.base_url)
        import threading

        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        port = httpd.server_address[1]
        try:
            status, data = _get(f"http://127.0.0.1:{port}/api/selection")
            self.assertEqual(status, 200)
            return data
        finally:
            httpd.shutdown()
            httpd.server_close()
            thread.join(timeout=2)
            fake.stop()

    def test_moon_reaches_frontend_payload(self):
        data = self._run_selection("moon_response.json")
        self.assertTrue(data["ok"], msg=data.get("error"))
        self.assertEqual(data["object_category"], "Planet")
        self.assertEqual(data["object_type"], "moon")
        self.assertAlmostEqual(data["angular_size_deg"], 0.518, places=3)

    def test_saturn_reaches_frontend_payload(self):
        data = self._run_selection("saturn_response.json")
        self.assertTrue(data["ok"], msg=data.get("error"))
        self.assertEqual(data["object_category"], "Planet")
        self.assertEqual(data["object_type"], "planet")
        self.assertAlmostEqual(data["angular_size_deg"], 0.037, places=3)


class TestPlanetaryImageEndpoint(ServerTestBase):
    FIXTURES = Path(__file__).resolve().parent / "fixtures" / "sample_responses"

    def _fixture_fetch(self, name):
        payload = json.loads((self.FIXTURES / name).read_text(encoding="utf-8"))

        def fetch(_url, _timeout):
            return payload

        return fetch

    def setUp(self):
        self.httpd = run_server(host="127.0.0.1", port=0, planetary_fetcher=self._fixture_fetch("nasa_images_moon.json"))
        import threading

        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.httpd.server_address[1]
        self.base = f"http://127.0.0.1:{self.port}"

    def test_moon_endpoint_returns_normalized_json(self):
        status, data = _get(f"{self.base}/api/planetary-image?target=moon")
        self.assertEqual(status, 200)
        self.assertEqual(data["status"], "found")
        self.assertEqual(data["target_id"], "moon")
        self.assertIn("images-assets.nasa.gov", data["image_url"])

    def test_mars_is_registry_supported(self):
        status, data = _get(f"{self.base}/api/planetary-image?target=mars")
        self.assertEqual(status, 200)
        # Fixture is Moon media; Mars is supported but irrelevant hits → unavailable.
        self.assertNotEqual(data["status"], "unsupported")
        self.assertEqual(data["status"], "unavailable")
        self.assertIn("public-media", data.get("error") or "")

    def test_unsupported_target(self):
        status, data = _get(f"{self.base}/api/planetary-image?target=1P%2FHalley")
        self.assertEqual(status, 200)
        self.assertEqual(data["status"], "unsupported")


class TestR040Endpoints(ServerTestBase):
    FIXTURES = Path(__file__).resolve().parent / "fixtures" / "sample_responses"

    def _fixture_fetch(self, name):
        payload = json.loads((self.FIXTURES / name).read_text(encoding="utf-8"))

        def fetch(_req, _timeout):
            return payload

        return fetch

    def _sbdb_fetch(self, url, _timeout):
        if "sbdb.api" in url:
            return json.loads((self.FIXTURES / "sbdb_apophis.json").read_text(encoding="utf-8"))
        return (self.FIXTURES / "horizons_apophis_text.txt").read_text(encoding="utf-8")

    def setUp(self):
        import tempfile

        self.tmp = tempfile.TemporaryDirectory()
        self.httpd = run_server(
            host="127.0.0.1",
            port=0,
            archive_fetcher=self._fixture_fetch("mast_hst_count.json"),
            apophis_fetcher=self._sbdb_fetch,
            watchlist_root=self.tmp.name,
        )
        import threading

        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.httpd.server_address[1]
        self.base = f"http://127.0.0.1:{self.port}"

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=2)
        self.tmp.cleanup()

    def test_archive_availability_endpoint(self):
        status, data = _get(f"{self.base}/api/archive-availability?ra=10&dec=41&mission=hst")
        self.assertEqual(status, 200)
        self.assertEqual(data["status"], "confirmed")
        self.assertEqual(data["count"], 14)

    def test_discovery_endpoint_returns_bundle_and_badges(self):
        # Use a discovery-aware fetcher that returns list/name fixtures.
        fixtures = self.FIXTURES

        def discovery_fetch(request_obj, _timeout):
            service = request_obj.get("service")
            if service == "Mast.Name.Lookup":
                return json.loads((fixtures / "mast_name_lookup_m42.json").read_text(encoding="utf-8"))
            if service in ("Mast.Caom.Filtered", "Mast.Caom.Filtered.Position"):
                return json.loads((fixtures / "mast_hst_list.json").read_text(encoding="utf-8"))
            return json.loads((fixtures / "mast_empty_list.json").read_text(encoding="utf-8"))

        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=2)
        self.httpd = run_server(
            host="127.0.0.1",
            port=0,
            archive_fetcher=self._fixture_fetch("mast_hst_count.json"),
            discovery_fetcher=discovery_fetch,
            apophis_fetcher=self._sbdb_fetch,
            watchlist_root=self.tmp.name,
        )
        import threading

        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.httpd.server_address[1]
        self.base = f"http://127.0.0.1:{self.port}"

        status, data = _get(
            f"{self.base}/api/discovery?ra=83.8&dec=-5.4&name=M42&missions=hst"
        )
        self.assertEqual(status, 200)
        self.assertTrue(data["ok"])
        self.assertIn("items", data["bundle"])
        self.assertIn("query_outcomes", data["bundle"])
        self.assertIn("hst", data["badges"])
        self.assertEqual(data["badges"]["hst"]["status"], "confirmed")
        for item in data["bundle"]["items"]:
            self.assertIsNotNone(item.get("result_type"))

    def test_watchlist_get_put(self):
        status, data = _get(f"{self.base}/api/watchlist")
        self.assertEqual(status, 200)
        self.assertTrue(data["ok"])
        doc = {"schema_version": 1, "entries": []}
        req = urllib.request.Request(
            f"{self.base}/api/watchlist",
            data=json.dumps({"document": doc}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="PUT",
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            saved = json.loads(resp.read().decode("utf-8"))
        self.assertTrue(saved["ok"])

    def test_apophis_tracker_endpoint(self):
        status, data = _get(f"{self.base}/api/apophis-tracker")
        self.assertEqual(status, 200)
        self.assertTrue(data["ok"])
        self.assertEqual(data["designation"], "99942")

    def test_watchlist_persists_across_server_restart(self):
        from app import watchlist_store

        moon = watchlist_store.entry_from_target(
            {"name": "Moon", "ra_deg": 1.0, "dec_deg": 2.0, "object_type": "moon", "source": "manual"}
        )
        apophis = watchlist_store.build_apophis_seed_entry()
        moon["personal_note"] = 'She said "hello"\nline two'
        moon["favorite"] = True
        doc = watchlist_store.normalize_document({"schema_version": 1, "entries": [moon, apophis]})
        req = urllib.request.Request(
            f"{self.base}/api/watchlist",
            data=json.dumps({"document": doc}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="PUT",
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            saved = json.loads(resp.read().decode("utf-8"))
        self.assertTrue(saved["ok"])
        self.assertEqual(saved["entry_count"], 2)

        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=2)

        self.httpd = run_server(
            host="127.0.0.1",
            port=0,
            archive_fetcher=self._fixture_fetch("mast_hst_count.json"),
            apophis_fetcher=self._sbdb_fetch,
            watchlist_root=self.tmp.name,
        )
        import threading

        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.httpd.server_address[1]
        self.base = f"http://127.0.0.1:{self.port}"

        status, data = _get(f"{self.base}/api/watchlist")
        self.assertEqual(status, 200)
        self.assertTrue(data["ok"])
        self.assertEqual(data["entry_count"], 2)
        self.assertEqual(data["storage_path_relative"], "runtime_data/tracked_objects.json")
        names = {e["display_name"] for e in data["document"]["entries"]}
        self.assertIn("Moon", names)
        self.assertIn("99942 Apophis", names)
        moon_entry = next(e for e in data["document"]["entries"] if e["display_name"] == "Moon")
        self.assertEqual(moon_entry["personal_note"], 'She said "hello"\nline two')
        self.assertTrue(moon_entry["favorite"])


if __name__ == "__main__":
    unittest.main()
