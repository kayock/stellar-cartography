"""Tests for MAST multi-strategy discovery and badge compatibility."""

from __future__ import annotations

import json
import os
import unittest

from app.discovery import compat
from app.discovery.providers import mast as mast_provider
from app.discovery.service import run_mast_discovery

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "sample_responses")


def _load(name: str):
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as f:
        return json.load(f)


class RoutingFetcher:
    """Route MAST requests to fixtures by service name."""

    def __init__(self, *, list_payload=None, empty=None, name_payload=None, fail_services=None):
        self.list_payload = list_payload if list_payload is not None else _load("mast_hst_list.json")
        self.empty = empty if empty is not None else _load("mast_empty_list.json")
        self.name_payload = name_payload if name_payload is not None else _load("mast_name_lookup_m42.json")
        self.fail_services = set(fail_services or [])
        self.calls = []

    def __call__(self, request_obj, timeout):
        self.calls.append(request_obj)
        service = request_obj.get("service")
        if service in self.fail_services:
            raise TimeoutError("simulated timeout")
        if service == "Mast.Name.Lookup":
            return self.name_payload
        if service == "Mast.Caom.Filtered":
            filters = (request_obj.get("params") or {}).get("filters") or []
            # Exact target_name with values list non-empty → return hits for M42
            for f in filters:
                if f.get("paramName") == "target_name":
                    if f.get("values"):
                        return self.list_payload
                    if f.get("freeText"):
                        return self.list_payload
            return self.empty
        if service == "Mast.Caom.Filtered.Position":
            return self.list_payload
        return self.empty


class TestMastDiscovery(unittest.TestCase):
    def test_exact_alias_before_freetext(self):
        fetcher = RoutingFetcher()
        provider = mast_provider.MastDiscoveryProvider(fetcher=fetcher)
        bundle = provider.discover(
            {
                "ra_deg": 83.8,
                "dec_deg": -5.4,
                "target_name": "M42",
                "missions": ["hst"],
            }
        )
        strategies = [c.get("service") for c in fetcher.calls]
        # First Filtered call should be exact (no freeText) before any freeText.
        filtered = [c for c in fetcher.calls if c.get("service") == "Mast.Caom.Filtered"]
        self.assertTrue(filtered)
        first_filters = filtered[0]["params"]["filters"]
        name_filter = [f for f in first_filters if f.get("paramName") == "target_name"][0]
        self.assertTrue(name_filter.get("values"))
        self.assertFalse(name_filter.get("freeText"))
        # Free-text should not run when exact succeeded.
        free_text_calls = [
            c
            for c in filtered
            if any(f.get("freeText") for f in c["params"]["filters"] if f.get("paramName") == "target_name")
        ]
        self.assertEqual(free_text_calls, [])
        self.assertTrue(any(i.get("match_basis") == "exact_target_name" for i in bundle["items"]))
        _ = strategies

    def test_freetext_only_after_exact_miss(self):
        def fetch(request_obj, _timeout):
            service = request_obj.get("service")
            if service == "Mast.Caom.Filtered":
                filters = request_obj["params"]["filters"]
                name_f = [f for f in filters if f.get("paramName") == "target_name"][0]
                if name_f.get("values"):
                    return _load("mast_empty_list.json")
                if name_f.get("freeText"):
                    return _load("mast_hst_list.json")
                return _load("mast_empty_list.json")
            if service == "Mast.Name.Lookup":
                return _load("mast_name_lookup_m42.json")
            return _load("mast_empty_list.json")

        provider = mast_provider.MastDiscoveryProvider(fetcher=fetch)
        bundle = provider.discover(
            {"target_name": "Orion Nebula", "missions": ["hst"], "ra_deg": 83.8, "dec_deg": -5.4}
        )
        self.assertTrue(any(i.get("match_basis") == "alias_match" for i in bundle["items"]))

    def test_dedupe_across_strategies_merges_provenance(self):
        fetcher = RoutingFetcher()
        provider = mast_provider.MastDiscoveryProvider(fetcher=fetcher)
        bundle = provider.discover(
            {
                "ra_deg": 83.8,
                "dec_deg": -5.4,
                "target_name": "M42",
                "missions": ["hst"],
            }
        )
        # Same obs_ids from name + cone should merge.
        ids = [i["observation_id"] for i in bundle["items"]]
        self.assertEqual(len(ids), len(set(ids)))
        for item in bundle["items"]:
            self.assertGreaterEqual(len(item.get("query_strategies") or []), 1)
            self.assertTrue(item.get("match_bases"))

    def test_counts_after_dedupe(self):
        fetcher = RoutingFetcher()
        payload = run_mast_discovery(
            ra_deg=83.8,
            dec_deg=-5.4,
            target_name="M42",
            missions=["hst"],
            fetcher=fetcher,
        )
        badge = payload["badges"]["hst"]
        self.assertEqual(badge["status"], "confirmed")
        self.assertEqual(badge["count"], len(payload["bundle"]["items"]))

    def test_cone_candidate_warning(self):
        fetcher = RoutingFetcher(list_payload=_load("mast_empty_list.json"))
        # Force only cone hits by emptying name strategies via empty list for Filtered
        # and list for Position — adjust: name returns empty, cone returns list.
        calls = {"n": 0}

        def fetch(request_obj, _timeout):
            service = request_obj.get("service")
            if service == "Mast.Name.Lookup":
                return {"status": "COMPLETE", "resolvedCoordinate": []}
            if service == "Mast.Caom.Filtered":
                return _load("mast_empty_list.json")
            if service == "Mast.Caom.Filtered.Position":
                return _load("mast_hst_list.json")
            return _load("mast_empty_list.json")

        provider = mast_provider.MastDiscoveryProvider(fetcher=fetch)
        bundle = provider.discover(
            {"ra_deg": 83.8, "dec_deg": -5.4, "target_name": "M42", "missions": ["hst"]}
        )
        self.assertTrue(bundle["items"])
        for item in bundle["items"]:
            self.assertEqual(item["match_basis"], "cone_candidate")
            self.assertTrue(any("positional candidate" in w.lower() for w in item["warnings"]))
        _ = calls

    def test_zero_results_honest_message(self):
        fetcher = RoutingFetcher(list_payload=_load("mast_empty_list.json"), empty=_load("mast_empty_list.json"))

        def fetch(request_obj, _timeout):
            if request_obj.get("service") == "Mast.Name.Lookup":
                return {"status": "COMPLETE", "resolvedCoordinate": []}
            return _load("mast_empty_list.json")

        provider = mast_provider.MastDiscoveryProvider(fetcher=fetch)
        bundle = provider.discover(
            {"ra_deg": 10.0, "dec_deg": 20.0, "target_name": "Nowhere", "missions": ["hst"]}
        )
        self.assertEqual(bundle["items"], [])
        zeros = [o for o in bundle["query_outcomes"] if o["query_status"] == "zero_results"]
        self.assertTrue(zeros)
        cone_zeros = [o for o in zeros if "cone_" in (o.get("query_strategy") or "")]
        self.assertTrue(cone_zeros)
        for o in cone_zeros:
            self.assertIn("No matching observations were returned", o["message"])
        for o in zeros:
            self.assertNotIn("does not exist", (o["message"] or "").lower())
            self.assertIsNone(o["result_type"])

    def test_moving_target_not_historically_evaluated(self):
        provider = mast_provider.MastDiscoveryProvider(fetcher=RoutingFetcher())
        bundle = provider.discover(
            {
                "ra_deg": 1.0,
                "dec_deg": 2.0,
                "target_name": "Apophis",
                "missions": ["hst"],
                "moving_target": True,
            }
        )
        self.assertEqual(bundle["items"], [])
        self.assertTrue(
            any(o["query_status"] == "ephemeris_required" for o in bundle["query_outcomes"])
        )
        self.assertTrue(
            any("Historical archive coverage" in n for n in bundle["capability_notes"])
        )

    def test_timeout_isolation_partial_success(self):
        def fetch(request_obj, _timeout):
            service = request_obj.get("service")
            if service == "Mast.Caom.Filtered.Position":
                raise TimeoutError("slow")
            if service == "Mast.Name.Lookup":
                return _load("mast_name_lookup_m42.json")
            if service == "Mast.Caom.Filtered":
                return _load("mast_hst_list.json")
            return _load("mast_empty_list.json")

        provider = mast_provider.MastDiscoveryProvider(fetcher=fetch)
        bundle = provider.discover(
            {"ra_deg": 83.8, "dec_deg": -5.4, "target_name": "M42", "missions": ["hst"]}
        )
        self.assertTrue(bundle["items"])
        self.assertTrue(any(o["query_status"] == "timeout" for o in bundle["query_outcomes"]))
        badge = compat.mission_badge_from_bundle(bundle, "hst")
        self.assertEqual(badge["status"], "confirmed")
        self.assertTrue(badge.get("partial_failure"))


class TestBadgeCompat(unittest.TestCase):
    def test_no_coverage_only_when_all_strategies_normal_zero(self):
        from app.discovery.models import empty_bundle, make_query_outcome

        bundle = empty_bundle()
        for strategy in ("exact_target_name:hst", "cone_0.01:hst"):
            bundle["query_outcomes"].append(
                make_query_outcome(
                    provider="mast",
                    query_status="zero_results",
                    query_strategy=strategy,
                    mission="hst",
                    message=mast_provider.ZERO_RESULT_MESSAGE,
                )
            )
        badge = compat.mission_badge_from_bundle(bundle, "hst")
        self.assertEqual(badge["status"], "no_coverage")

    def test_failure_without_items_is_unavailable_not_no_coverage(self):
        from app.discovery.models import empty_bundle, make_query_outcome

        bundle = empty_bundle()
        bundle["query_outcomes"].append(
            make_query_outcome(
                provider="mast",
                query_status="timeout",
                query_strategy="cone_0.01:hst",
                mission="hst",
                message="timed out",
            )
        )
        bundle["query_outcomes"].append(
            make_query_outcome(
                provider="mast",
                query_status="zero_results",
                query_strategy="exact_target_name:hst",
                mission="hst",
                message=mast_provider.ZERO_RESULT_MESSAGE,
            )
        )
        badge = compat.mission_badge_from_bundle(bundle, "hst")
        self.assertEqual(badge["status"], "unavailable")


if __name__ == "__main__":
    unittest.main()
