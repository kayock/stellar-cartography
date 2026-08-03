import math
import unittest

from app import coords


class TestDecimalFields(unittest.TestCase):
    def test_decimal_degree_fields(self):
        payload = {"raJ2000deg": 10.68470, "decJ2000deg": 41.26875}
        result = coords.extract_j2000_radec(payload)
        self.assertTrue(result.ok)
        self.assertAlmostEqual(result.ra_deg, 10.68470, places=4)
        self.assertAlmostEqual(result.dec_deg, 41.26875, places=4)
        self.assertEqual(result.source, "decimal_degree_fields")

    def test_decimal_fields_as_strings(self):
        payload = {"raDeg": "83.822083", "decDeg": "-5.391111"}
        result = coords.extract_j2000_radec(payload)
        self.assertTrue(result.ok)
        self.assertAlmostEqual(result.ra_deg, 83.822083, places=4)
        self.assertAlmostEqual(result.dec_deg, -5.391111, places=4)

    def test_documented_numeric_raJ2000_decJ2000_are_first_class(self):
        # Regression test: Stellarium's *documented* getInfoMap shape uses
        # numeric raJ2000/decJ2000 directly (decimal degrees) -- these must
        # be recognized as decimal fields, not only as possible
        # sexagesimal strings.
        payload = {
            "name": "M 31",
            "localized-name": "Andromeda Galaxy",
            "type": "Nebula",
            "object-type": "galaxy",
            "raJ2000": 10.68470,
            "decJ2000": 41.26875,
            "iauConstellation": "And",
            "vmag": 3.44,
            "size-dd": 3.167,
            "altitude": 35.2,
            "azimuth": 122.8,
            "above-horizon": True,
        }
        result = coords.extract_j2000_radec(payload)
        self.assertTrue(result.ok)
        self.assertAlmostEqual(result.ra_deg, 10.68470, places=4)
        self.assertAlmostEqual(result.dec_deg, 41.26875, places=4)
        self.assertEqual(result.source, "decimal_degree_fields")

    def test_numeric_raJ2000_decJ2000_preferred_over_legacy_deg_aliases(self):
        # When both the documented numeric fields and a legacy alias are
        # present, the documented fields win (they're tried first).
        payload = {"raJ2000": 10.0, "decJ2000": 20.0, "raJ2000deg": 99.0, "decJ2000deg": -99.0}
        result = coords.extract_j2000_radec(payload)
        self.assertTrue(result.ok)
        self.assertAlmostEqual(result.ra_deg, 10.0, places=4)
        self.assertAlmostEqual(result.dec_deg, 20.0, places=4)

    def test_sexagesimal_raJ2000_still_falls_back_correctly(self):
        # A sexagesimal string under the same documented key name must
        # still be recognized (via the sexagesimal-text strategy) since
        # not every Stellarium build sends numeric values.
        payload = {"raJ2000": "0h42m44.3s", "decJ2000": "+41d16m09s"}
        result = coords.extract_j2000_radec(payload)
        self.assertTrue(result.ok)
        self.assertEqual(result.source, "sexagesimal_text_fields")


class TestSexagesimalFields(unittest.TestCase):
    def test_ra_dec_sexagesimal_hms_dms(self):
        payload = {"raJ2000": "5h35m17.3s", "decJ2000": "-05d23m28s"}
        result = coords.extract_j2000_radec(payload)
        self.assertTrue(result.ok)
        # 5h35m17.3s -> (5 + 35/60 + 17.3/3600) * 15
        expected_ra = (5 + 35 / 60 + 17.3 / 3600) * 15
        self.assertAlmostEqual(result.ra_deg, expected_ra, places=3)
        expected_dec = -(5 + 23 / 60 + 28 / 3600)
        self.assertAlmostEqual(result.dec_deg, expected_dec, places=3)
        self.assertEqual(result.source, "sexagesimal_text_fields")

    def test_negative_declination_preserved(self):
        payload = {"raJ2000": "0h24m05.7s", "decJ2000": "-72d04m53s"}
        result = coords.extract_j2000_radec(payload)
        self.assertTrue(result.ok)
        self.assertLess(result.dec_deg, 0)
        expected_dec = -(72 + 4 / 60 + 53 / 3600)
        self.assertAlmostEqual(result.dec_deg, expected_dec, places=3)

    def test_generic_colon_and_space_separated_format(self):
        payload = {"ra": "12:34:56.7", "dec": "+45 30 10"}
        result = coords.extract_j2000_radec(payload)
        self.assertTrue(result.ok)
        expected_ra = (12 + 34 / 60 + 56.7 / 3600) * 15
        self.assertAlmostEqual(result.ra_deg, expected_ra, places=3)
        expected_dec = 45 + 30 / 60 + 10 / 3600
        self.assertAlmostEqual(result.dec_deg, expected_dec, places=3)

    def test_positive_declination_no_sign(self):
        payload = {"raJ2000": "0h42m44.3s", "decJ2000": "41d16m09s"}
        result = coords.extract_j2000_radec(payload)
        self.assertTrue(result.ok)
        self.assertGreater(result.dec_deg, 0)


class TestVectorFields(unittest.TestCase):
    def test_vX_vY_vZ_components(self):
        # Vector pointing close to +X axis => ra ~ 0, dec ~ 0
        payload = {"vX": 1.0, "vY": 0.0, "vZ": 0.0}
        result = coords.extract_j2000_radec(payload)
        self.assertTrue(result.ok)
        self.assertAlmostEqual(result.ra_deg, 0.0, places=3)
        self.assertAlmostEqual(result.dec_deg, 0.0, places=3)
        self.assertEqual(result.source, "j2000_direction_vector")

    def test_named_list_vector(self):
        payload = {"name": "Polaris", "j2000Pos": [-0.0592, 0.0177, 0.9980]}
        result = coords.extract_j2000_radec(payload)
        self.assertTrue(result.ok)
        # Polaris is near the north celestial pole.
        self.assertGreater(result.dec_deg, 85.0)

    def test_nested_dict_vector(self):
        payload = {"position": {"x": 0.0, "y": 1.0, "z": 0.0}}
        result = coords.extract_j2000_radec(payload)
        self.assertTrue(result.ok)
        self.assertAlmostEqual(result.ra_deg, 90.0, places=3)
        self.assertAlmostEqual(result.dec_deg, 0.0, places=3)

    def test_zero_length_vector_rejected(self):
        payload = {"vX": 0.0, "vY": 0.0, "vZ": 0.0}
        result = coords.extract_j2000_radec(payload)
        self.assertFalse(result.ok)

    def test_vector_round_trip_matches_known_object(self):
        # RA=210 deg, Dec=-30 deg converted to a unit vector and back.
        ra0, dec0 = 210.0, -30.0
        ra_rad, dec_rad = math.radians(ra0), math.radians(dec0)
        x = math.cos(dec_rad) * math.cos(ra_rad)
        y = math.cos(dec_rad) * math.sin(ra_rad)
        z = math.sin(dec_rad)
        payload = {"vX": x, "vY": y, "vZ": z}
        result = coords.extract_j2000_radec(payload)
        self.assertTrue(result.ok)
        self.assertAlmostEqual(result.ra_deg, ra0, places=3)
        self.assertAlmostEqual(result.dec_deg, dec0, places=3)


class TestRaWraparound(unittest.TestCase):
    def test_ra_near_360_stays_in_range(self):
        payload = {"raJ2000deg": 359.75, "decJ2000deg": 1.5}
        result = coords.extract_j2000_radec(payload)
        self.assertTrue(result.ok)
        self.assertGreaterEqual(result.ra_deg, 0.0)
        self.assertLess(result.ra_deg, 360.0)
        self.assertAlmostEqual(result.ra_deg, 359.75, places=3)

    def test_negative_ra_wraps_into_range(self):
        payload = {"raJ2000deg": -10.0, "decJ2000deg": 0.0}
        result = coords.extract_j2000_radec(payload)
        self.assertTrue(result.ok)
        self.assertAlmostEqual(result.ra_deg, 350.0, places=3)

    def test_ra_over_360_wraps_into_range(self):
        payload = {"raJ2000deg": 370.0, "decJ2000deg": 0.0}
        result = coords.extract_j2000_radec(payload)
        self.assertTrue(result.ok)
        self.assertAlmostEqual(result.ra_deg, 10.0, places=3)


class TestFailureModes(unittest.TestCase):
    def test_non_dict_payload(self):
        result = coords.extract_j2000_radec(["not", "a", "dict"])
        self.assertFalse(result.ok)
        self.assertIn("not a JSON object", result.reason)

    def test_empty_payload(self):
        result = coords.extract_j2000_radec({})
        self.assertFalse(result.ok)

    def test_no_recognizable_fields(self):
        payload = {"name": "Mystery Object", "vmag": 5.2}
        result = coords.extract_j2000_radec(payload)
        self.assertFalse(result.ok)
        self.assertIsNotNone(result.reason)

    def test_unparsable_sexagesimal_falls_through(self):
        payload = {"raJ2000": "not-a-coordinate", "decJ2000": "also-not-one"}
        result = coords.extract_j2000_radec(payload)
        self.assertFalse(result.ok)


class TestNonFiniteValuesRejected(unittest.TestCase):
    """Requirement 4: NaN/Infinity/-Infinity (numeric or numeric-string)
    must never produce a nan/inf coordinate, and must never crash sexagesimal
    formatting -- extraction must return ok:false instead."""

    def test_numeric_nan_decimal_field_rejected(self):
        payload = {"raJ2000deg": float("nan"), "decJ2000deg": 10.0}
        result = coords.extract_j2000_radec(payload)
        self.assertFalse(result.ok)
        self.assertIsNone(result.ra_deg)
        self.assertIsNone(result.dec_deg)

    def test_numeric_infinity_decimal_field_rejected(self):
        payload = {"raJ2000deg": float("inf"), "decJ2000deg": 10.0}
        result = coords.extract_j2000_radec(payload)
        self.assertFalse(result.ok)

    def test_numeric_negative_infinity_decimal_field_rejected(self):
        payload = {"raJ2000deg": 10.0, "decJ2000deg": float("-inf")}
        result = coords.extract_j2000_radec(payload)
        self.assertFalse(result.ok)

    def test_string_nan_decimal_field_rejected(self):
        payload = {"raJ2000deg": "nan", "decJ2000deg": "10.0"}
        result = coords.extract_j2000_radec(payload)
        self.assertFalse(result.ok)

    def test_string_infinity_decimal_field_rejected(self):
        payload = {"raJ2000deg": "Infinity", "decJ2000deg": "10.0"}
        result = coords.extract_j2000_radec(payload)
        self.assertFalse(result.ok)

    def test_string_negative_infinity_decimal_field_rejected(self):
        payload = {"raJ2000deg": "10.0", "decJ2000deg": "-Infinity"}
        result = coords.extract_j2000_radec(payload)
        self.assertFalse(result.ok)

    def test_non_finite_falls_through_to_a_later_finite_alias(self):
        # A non-finite value under one alias must not poison the whole
        # extraction if a later, finite alias is also present.
        payload = {"raJ2000": float("nan"), "raJ2000deg": 10.0, "decJ2000deg": 20.0}
        result = coords.extract_j2000_radec(payload)
        self.assertTrue(result.ok)
        self.assertAlmostEqual(result.ra_deg, 10.0, places=4)

    def test_vector_component_nan_rejected(self):
        payload = {"vX": float("nan"), "vY": 0.0, "vZ": 0.0}
        result = coords.extract_j2000_radec(payload)
        self.assertFalse(result.ok)

    def test_vector_component_infinity_rejected(self):
        payload = {"vX": float("inf"), "vY": 0.0, "vZ": 0.0}
        result = coords.extract_j2000_radec(payload)
        self.assertFalse(result.ok)

    def test_named_list_vector_with_nan_rejected(self):
        payload = {"j2000Pos": [float("nan"), 0.0177, 0.9980]}
        result = coords.extract_j2000_radec(payload)
        self.assertFalse(result.ok)

    def test_named_list_vector_with_infinity_rejected(self):
        payload = {"j2000Pos": [float("inf"), 0.0177, 0.9980]}
        result = coords.extract_j2000_radec(payload)
        self.assertFalse(result.ok)

    def test_nested_dict_vector_with_nan_rejected(self):
        payload = {"position": {"x": float("nan"), "y": 1.0, "z": 0.0}}
        result = coords.extract_j2000_radec(payload)
        self.assertFalse(result.ok)

    def test_direct_vector_to_radec_call_with_non_finite_input_rejected(self):
        # Defense-in-depth check on the internal helper itself.
        result = coords._vector_to_radec(float("nan"), 0.0, 1.0)
        self.assertFalse(result.ok)

    def test_direct_finalize_call_with_non_finite_input_rejected(self):
        result = coords._finalize(float("inf"), 10.0, source="test")
        self.assertFalse(result.ok)
        result = coords._finalize(10.0, float("-inf"), source="test")
        self.assertFalse(result.ok)


class TestManualEntryParsing(unittest.TestCase):
    def test_decimal_ra_dec(self):
        self.assertAlmostEqual(coords.parse_manual_ra("83.63"), 83.63, places=3)
        self.assertAlmostEqual(coords.parse_manual_dec("-5.39"), -5.39, places=3)

    def test_sexagesimal_ra_dec(self):
        ra = coords.parse_manual_ra("05h35m17s")
        dec = coords.parse_manual_dec("-05d23m28s")
        self.assertIsNotNone(ra)
        self.assertIsNotNone(dec)
        self.assertLess(dec, 0)

    def test_invalid_manual_entry(self):
        self.assertIsNone(coords.parse_manual_ra("banana"))
        self.assertIsNone(coords.parse_manual_dec("banana"))

    def test_manual_dec_clamped(self):
        self.assertEqual(coords.parse_manual_dec("120"), 90.0)
        self.assertEqual(coords.parse_manual_dec("-120"), -90.0)

    def test_manual_ra_rejects_nan_and_infinity_numeric_strings(self):
        for text in ("nan", "NaN", "inf", "Infinity", "-inf", "-Infinity"):
            with self.subTest(text=text):
                self.assertIsNone(coords.parse_manual_ra(text))

    def test_manual_dec_rejects_nan_and_infinity_numeric_strings(self):
        for text in ("nan", "NaN", "inf", "Infinity", "-inf", "-Infinity"):
            with self.subTest(text=text):
                self.assertIsNone(coords.parse_manual_dec(text))


class TestFormatting(unittest.TestCase):
    def test_format_sexagesimal_ra(self):
        text = coords.format_sexagesimal_ra(10.68470)
        self.assertTrue(text.startswith("00h"))
        self.assertIn("m", text)
        self.assertIn("s", text)

    def test_format_sexagesimal_dec_negative(self):
        text = coords.format_sexagesimal_dec(-41.26875)
        self.assertTrue(text.startswith("-"))

    def test_seconds_rounding_carries_into_minutes(self):
        # Regression test: 210.5 deg RA previously rendered as the invalid
        # "14h01m60.00s" due to a float-rounding boundary; it must carry
        # into the next minute instead.
        text = coords.format_sexagesimal_ra(210.5)
        self.assertEqual(text, "14h02m00.00s")
        self.assertNotIn("60.00s", text)

    def test_minutes_rounding_carries_into_degrees(self):
        # Construct a value whose minutes/seconds land exactly on a 60
        # boundary after rounding, and confirm it carries into whole
        # degrees rather than displaying "60m".
        text = coords.format_sexagesimal_dec(-(41 + 59.999 / 60))
        self.assertNotIn("60m", text)
        self.assertNotIn("60.00s", text)


if __name__ == "__main__":
    unittest.main()
