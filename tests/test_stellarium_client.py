import json
import unittest

from app.stellarium_client import StellariumClient
from tests.fixtures.fake_stellarium_server import FakeStellariumServer, load_sample, canned_json


class TestStellariumUnavailable(unittest.TestCase):
    def test_connection_refused_when_nothing_listening(self):
        # Nothing is listening on this port -> connection refused.
        client = StellariumClient(base_url="http://127.0.0.1:1", timeout=0.5)
        self.assertFalse(client.check_connection())
        result = client.get_selection()
        self.assertFalse(result.ok)
        self.assertFalse(result.connected)
        self.assertIsNotNone(result.error)

    def test_manual_mode_still_works_when_stellarium_down(self):
        # This is really a coords-module concern, but confirms the client
        # failure doesn't raise and the app can fall back independently.
        client = StellariumClient(base_url="http://127.0.0.1:1", timeout=0.5)
        result = client.get_selection()
        self.assertFalse(result.ok)
        # No exception raised -- the caller can proceed to manual entry.


class TestCheckConnectionFailureSafe(unittest.TestCase):
    """check_connection() must never raise -- only genuine network
    unreachability should report connected=False; any real HTTP response,
    however malformed its body, is still evidence something is listening
    and must report connected=True (repair request item 3)."""

    def test_malformed_json_main_status_still_connected(self):
        server = FakeStellariumServer(main_status_body=load_sample("malformed_response.txt"))
        server.start()
        try:
            client = StellariumClient(base_url=server.base_url, timeout=2)
            self.assertTrue(client.check_connection())
        finally:
            server.stop()

    def test_invalid_utf8_main_status_still_connected(self):
        server = FakeStellariumServer(main_status_body=b"\xff\xfe\x00\x01not valid utf-8")
        server.start()
        try:
            client = StellariumClient(base_url=server.base_url, timeout=2)
            self.assertTrue(client.check_connection())
        finally:
            server.stop()

    def test_oversized_main_status_still_connected(self):
        from app.stellarium_client import MAX_RESPONSE_BYTES

        oversized = b'{"padding": "' + (b"x" * (MAX_RESPONSE_BYTES + 100)) + b'"}'
        server = FakeStellariumServer(main_status_body=oversized)
        server.start()
        try:
            client = StellariumClient(base_url=server.base_url, timeout=2)
            self.assertTrue(client.check_connection())
        finally:
            server.stop()

    def test_ordinary_valid_status_connected(self):
        server = FakeStellariumServer(main_status_body=canned_json({"status": "ok"}))
        server.start()
        try:
            client = StellariumClient(base_url=server.base_url, timeout=2)
            self.assertTrue(client.check_connection())
        finally:
            server.stop()

    def test_unreachable_status_not_connected(self):
        client = StellariumClient(base_url="http://127.0.0.1:1", timeout=0.5)
        self.assertFalse(client.check_connection())


class TestNoSelectedObject(unittest.TestCase):
    def test_empty_object_response(self):
        server = FakeStellariumServer(objects_info_body=load_sample("empty_selection_response.json"))
        server.start()
        try:
            client = StellariumClient(base_url=server.base_url, timeout=2)
            self.assertTrue(client.check_connection())
            result = client.get_selection()
            self.assertFalse(result.ok)
            self.assertTrue(result.connected)
            self.assertIn("Nothing is currently selected", result.error)
        finally:
            server.stop()


class TestMalformedJson(unittest.TestCase):
    def test_malformed_json_body(self):
        server = FakeStellariumServer(objects_info_body=load_sample("malformed_response.txt"))
        server.start()
        try:
            client = StellariumClient(base_url=server.base_url, timeout=2)
            result = client.get_selection()
            self.assertFalse(result.ok)
            self.assertTrue(result.connected)
            self.assertIn("malformed JSON", result.error)
        finally:
            server.stop()


class TestMultipleCoordinateFormats(unittest.TestCase):
    def _run(self, sample_name, expect_name=None):
        server = FakeStellariumServer(objects_info_body=load_sample(sample_name))
        server.start()
        try:
            client = StellariumClient(base_url=server.base_url, timeout=2)
            result = client.get_selection()
            self.assertTrue(result.ok, msg=f"failed for {sample_name}: {result.error}")
            self.assertIsNotNone(result.ra_deg)
            self.assertIsNotNone(result.dec_deg)
            if expect_name:
                self.assertEqual(result.name, expect_name)
            return result
        finally:
            server.stop()

    def test_decimal_response(self):
        self._run("decimal_response.json", expect_name="M 31")

    def test_sexagesimal_response(self):
        r = self._run("sexagesimal_response.json", expect_name="M 42")
        self.assertLess(r.dec_deg, 0)

    def test_vector_response(self):
        r = self._run("vector_response.json", expect_name="Polaris")
        self.assertGreater(r.dec_deg, 80)

    def test_negative_dec_response(self):
        r = self._run("negative_dec_response.json")
        self.assertLess(r.dec_deg, 0)

    def test_ra_wraparound_response(self):
        r = self._run("ra_wraparound_response.json")
        self.assertGreaterEqual(r.ra_deg, 0)
        self.assertLess(r.ra_deg, 360)

    def test_minimal_generic_fields(self):
        self._run("minimal_generic_fields_response.json", expect_name="Some Object")


class TestBoundedNetworkPayload(unittest.TestCase):
    def test_oversized_response_is_rejected(self):
        from app import stellarium_client as sc

        huge_padding = "x" * (sc.MAX_RESPONSE_BYTES + 1000)
        body = canned_json({"name": "Huge", "raJ2000deg": 1.0, "decJ2000deg": 1.0, "padding": huge_padding})
        server = FakeStellariumServer(objects_info_body=body)
        server.start()
        try:
            client = StellariumClient(base_url=server.base_url, timeout=5)
            result = client.get_selection()
            self.assertFalse(result.ok)
            self.assertTrue(result.connected)
            self.assertIn("unexpectedly large", result.error)
        finally:
            server.stop()

    def test_normal_sized_response_still_works(self):
        body = canned_json({"name": "Normal", "raJ2000deg": 1.0, "decJ2000deg": 1.0})
        server = FakeStellariumServer(objects_info_body=body)
        server.start()
        try:
            client = StellariumClient(base_url=server.base_url, timeout=2)
            result = client.get_selection()
            self.assertTrue(result.ok)
        finally:
            server.stop()


class TestFovOptional(unittest.TestCase):
    def test_missing_fov_is_tolerated(self):
        # The fake server's default /api/main/status has no "view" key at
        # all -- get_selection() must still succeed, with fov_deg simply
        # left as None.
        body = canned_json({"name": "No FoV", "raJ2000deg": 5.0, "decJ2000deg": 5.0})
        server = FakeStellariumServer(objects_info_body=body)
        server.start()
        try:
            client = StellariumClient(base_url=server.base_url, timeout=2)
            result = client.get_selection()
            self.assertTrue(result.ok)
            self.assertIsNone(result.fov_deg)
        finally:
            server.stop()

    def test_fov_is_sourced_from_main_status_not_selection(self):
        # Regression test: FoV must be read from GET /api/main/status
        # ("view.fov"), never from the /api/objects/info selection
        # payload, even if a stray "fov" key happens to be present there.
        objects_info_body = canned_json(
            {"name": "Has Stray Fov Key", "raJ2000deg": 5.0, "decJ2000deg": 5.0, "fov": 999.0}
        )
        main_status_body = load_sample("main_status_with_fov.json")
        server = FakeStellariumServer(
            objects_info_body=objects_info_body, main_status_body=main_status_body
        )
        server.start()
        try:
            client = StellariumClient(base_url=server.base_url, timeout=2)
            result = client.get_selection()
            self.assertTrue(result.ok)
            # Comes from main_status_with_fov.json ("view.fov": 5.2), not
            # the misleading "fov": 999.0 in the selection payload.
            self.assertAlmostEqual(result.fov_deg, 5.2, places=3)
        finally:
            server.stop()

    def test_fov_lookup_failure_does_not_fail_selection(self):
        # If /api/main/status 500s, selection must still succeed with
        # fov_deg left as None.
        objects_info_body = canned_json({"name": "Ok Object", "raJ2000deg": 5.0, "decJ2000deg": 5.0})
        server = FakeStellariumServer(
            objects_info_body=objects_info_body,
            main_status_body=b"not json",
            main_status_status=200,
        )
        server.start()
        try:
            client = StellariumClient(base_url=server.base_url, timeout=2)
            result = client.get_selection()
            self.assertTrue(result.ok)
            self.assertIsNone(result.fov_deg)
        finally:
            server.stop()


class TestAboutObjectMetadata(unittest.TestCase):
    def test_rich_metadata_extracted(self):
        server = FakeStellariumServer(objects_info_body=load_sample("rich_metadata_response.json"))
        server.start()
        try:
            client = StellariumClient(base_url=server.base_url, timeout=2)
            result = client.get_selection()
            self.assertTrue(result.ok)
            self.assertEqual(result.name, "M 31")
            self.assertEqual(result.alt_name, "Andromeda Galaxy")
            self.assertEqual(result.object_type, "galaxy")
            self.assertEqual(result.object_subtype, "SA(s)b")
            self.assertIn("NGC 224", result.catalogue_designations)
            self.assertEqual(result.constellation, "Andromeda")
            self.assertAlmostEqual(result.apparent_magnitude, 3.44, places=2)
        finally:
            server.stop()

    def test_missing_optional_metadata_is_none_not_invented(self):
        body = canned_json({"name": "Bare Object", "raJ2000deg": 1.0, "decJ2000deg": 1.0})
        server = FakeStellariumServer(objects_info_body=body)
        server.start()
        try:
            client = StellariumClient(base_url=server.base_url, timeout=2)
            result = client.get_selection()
            self.assertTrue(result.ok)
            self.assertIsNone(result.object_subtype)
            self.assertIsNone(result.catalogue_designations)
            self.assertIsNone(result.constellation)
            self.assertIsNone(result.apparent_magnitude)
        finally:
            server.stop()

    def test_official_documented_getinfo_shape_succeeds(self):
        # Proves the exact documented Stellarium getInfoMap payload (from
        # the R0.1.1 audit findings) is parsed correctly end-to-end through
        # StellariumClient, including the new About-This-Object fields.
        server = FakeStellariumServer(
            objects_info_body=load_sample("official_getinfo_shape_response.json")
        )
        server.start()
        try:
            client = StellariumClient(base_url=server.base_url, timeout=2)
            result = client.get_selection()
            self.assertTrue(result.ok, msg=result.error)
            self.assertEqual(result.name, "M 31")
            self.assertEqual(result.alt_name, "Andromeda Galaxy")
            self.assertEqual(result.object_category, "Nebula")
            self.assertEqual(result.object_type, "galaxy")
            self.assertEqual(result.constellation, "And")
            self.assertAlmostEqual(result.apparent_magnitude, 3.44, places=2)
            self.assertAlmostEqual(result.angular_size_deg, 3.167, places=3)
            self.assertAlmostEqual(result.altitude_deg, 35.2, places=2)
            self.assertAlmostEqual(result.azimuth_deg, 122.8, places=2)
            self.assertIs(result.above_horizon, True)
            self.assertAlmostEqual(result.ra_deg, 10.68470, places=4)
            self.assertAlmostEqual(result.dec_deg, 41.26875, places=4)
        finally:
            server.stop()

    def test_moon_selection_fields_parsed(self):
        server = FakeStellariumServer(objects_info_body=load_sample("moon_response.json"))
        server.start()
        try:
            client = StellariumClient(base_url=server.base_url, timeout=2)
            result = client.get_selection()
            self.assertTrue(result.ok, msg=result.error)
            self.assertEqual(result.name, "Moon")
            self.assertEqual(result.object_category, "Planet")
            self.assertEqual(result.object_type, "moon")
            self.assertAlmostEqual(result.angular_size_deg, 0.518, places=3)
        finally:
            server.stop()

    def test_saturn_selection_fields_parsed(self):
        server = FakeStellariumServer(objects_info_body=load_sample("saturn_response.json"))
        server.start()
        try:
            client = StellariumClient(base_url=server.base_url, timeout=2)
            result = client.get_selection()
            self.assertTrue(result.ok, msg=result.error)
            self.assertEqual(result.name, "Saturn")
            self.assertEqual(result.object_category, "Planet")
            self.assertEqual(result.object_type, "planet")
            self.assertAlmostEqual(result.angular_size_deg, 0.037, places=3)
        finally:
            server.stop()

    def test_type_and_object_type_kept_distinct(self):
        body = canned_json(
            {
                "name": "Split Fields",
                "type": "Nebula",
                "object-type": "planetary nebula",
                "raJ2000deg": 1.0,
                "decJ2000deg": 1.0,
            }
        )
        server = FakeStellariumServer(objects_info_body=body)
        server.start()
        try:
            client = StellariumClient(base_url=server.base_url, timeout=2)
            result = client.get_selection()
            self.assertTrue(result.ok)
            self.assertEqual(result.object_category, "Nebula")
            self.assertEqual(result.object_type, "planetary nebula")
        finally:
            server.stop()

    def test_new_about_fields_absent_when_not_supplied(self):
        body = canned_json({"name": "Bare Object", "raJ2000deg": 1.0, "decJ2000deg": 1.0})
        server = FakeStellariumServer(objects_info_body=body)
        server.start()
        try:
            client = StellariumClient(base_url=server.base_url, timeout=2)
            result = client.get_selection()
            self.assertTrue(result.ok)
            self.assertIsNone(result.object_category)
            self.assertIsNone(result.angular_size_deg)
            self.assertIsNone(result.altitude_deg)
            self.assertIsNone(result.azimuth_deg)
            self.assertIsNone(result.above_horizon)
        finally:
            server.stop()

    def test_sentinel_magnitude_rejected(self):
        server = FakeStellariumServer(objects_info_body=load_sample("sentinel_magnitude_response.json"))
        server.start()
        try:
            client = StellariumClient(base_url=server.base_url, timeout=2)
            result = client.get_selection()
            self.assertTrue(result.ok)
            # 99.99 is a common "unknown" sentinel, not a real apparent
            # magnitude -- must not be surfaced as if it were real data.
            self.assertIsNone(result.apparent_magnitude)
        finally:
            server.stop()


class TestNonFiniteOptionalMetadataOmitted(unittest.TestCase):
    """Requirement 4: NaN/Infinity/-Infinity in optional metadata fields
    (magnitude, angular size, altitude, azimuth) and in FoV must be omitted
    (None), never surfaced as a bogus value, and must never crash parsing."""

    def test_non_finite_magnitude_omitted(self):
        body = canned_json(
            {"name": "Bad Mag", "raJ2000deg": 1.0, "decJ2000deg": 1.0, "vmag": float("nan")}
        )
        server = FakeStellariumServer(objects_info_body=body)
        server.start()
        try:
            client = StellariumClient(base_url=server.base_url, timeout=2)
            result = client.get_selection()
            self.assertTrue(result.ok)
            self.assertIsNone(result.apparent_magnitude)
        finally:
            server.stop()

    def test_non_finite_angular_size_altitude_azimuth_omitted(self):
        body = canned_json(
            {
                "name": "Bad Metadata",
                "raJ2000deg": 1.0,
                "decJ2000deg": 1.0,
                "size-dd": float("inf"),
                "altitude": float("-inf"),
                "azimuth": float("nan"),
            }
        )
        server = FakeStellariumServer(objects_info_body=body)
        server.start()
        try:
            client = StellariumClient(base_url=server.base_url, timeout=2)
            result = client.get_selection()
            self.assertTrue(result.ok)
            self.assertIsNone(result.angular_size_deg)
            self.assertIsNone(result.altitude_deg)
            self.assertIsNone(result.azimuth_deg)
        finally:
            server.stop()

    def test_non_finite_string_metadata_omitted(self):
        body = canned_json(
            {
                "name": "Bad String Metadata",
                "raJ2000deg": 1.0,
                "decJ2000deg": 1.0,
                "vmag": "NaN",
                "azimuth": "Infinity",
            }
        )
        server = FakeStellariumServer(objects_info_body=body)
        server.start()
        try:
            client = StellariumClient(base_url=server.base_url, timeout=2)
            result = client.get_selection()
            self.assertTrue(result.ok)
            self.assertIsNone(result.apparent_magnitude)
            self.assertIsNone(result.azimuth_deg)
        finally:
            server.stop()

    def test_non_finite_fov_from_main_status_omitted(self):
        objects_info_body = canned_json({"name": "Ok Object", "raJ2000deg": 5.0, "decJ2000deg": 5.0})
        main_status_body = canned_json({"view": {"fov": float("nan")}})
        server = FakeStellariumServer(
            objects_info_body=objects_info_body, main_status_body=main_status_body
        )
        server.start()
        try:
            client = StellariumClient(base_url=server.base_url, timeout=2)
            result = client.get_selection()
            self.assertTrue(result.ok)
            self.assertIsNone(result.fov_deg)
        finally:
            server.stop()

    def test_non_finite_coordinates_yield_failed_selection_not_a_crash(self):
        body = canned_json({"name": "Bad Coords", "raJ2000deg": float("inf"), "decJ2000deg": 1.0})
        server = FakeStellariumServer(objects_info_body=body)
        server.start()
        try:
            client = StellariumClient(base_url=server.base_url, timeout=2)
            result = client.get_selection()
            self.assertFalse(result.ok)
            self.assertIsNotNone(result.error)
        finally:
            server.stop()


if __name__ == "__main__":
    unittest.main()
