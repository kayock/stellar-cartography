"""Tests for discovery contracts (query_status vs result_type, dedupe provenance)."""

from __future__ import annotations

import unittest

from app.discovery import models as m


class TestDiscoveryModels(unittest.TestCase):
    def test_item_requires_result_type(self):
        with self.assertRaises(ValueError):
            m.make_discovery_item(
                provider="mast",
                source_or_mission="HST",
                target_name="M42",
                target_category="nebula",
                query_type="archive",
                query_strategy="cone_0.01",
                wavelength_domain="visible",
                result_type=None,  # type: ignore[arg-type]
                match_basis="cone_candidate",
            )

    def test_non_item_statuses_listed(self):
        for status in (
            "zero_results",
            "timeout",
            "unavailable",
            "rate_limited",
            "malformed_response",
            "unsupported",
            "ephemeris_required",
        ):
            self.assertIn(status, m.NON_ITEM_QUERY_STATUSES)
            outcome = m.make_query_outcome(
                provider="mast",
                query_status=status,
                query_strategy="cone_0.01",
                message="test",
            )
            self.assertIsNone(outcome["result_type"])

    def test_match_basis_precedence(self):
        self.assertEqual(
            m.prefer_match_basis(["cone_candidate", "exact_target_name", "resolved_position"]),
            "exact_target_name",
        )
        self.assertEqual(
            m.prefer_match_basis(["cone_candidate", "alias_match"]),
            "alias_match",
        )
        self.assertEqual(
            m.prefer_match_basis(["resolved_position", "cone_candidate"]),
            "resolved_position",
        )

    def test_dedupe_merges_provenance(self):
        a = m.make_discovery_item(
            provider="mast",
            source_or_mission="HST",
            target_name="M42",
            target_category=None,
            query_type="archive",
            query_strategy="exact_target_name",
            wavelength_domain="visible",
            result_type="archive_observation",
            match_basis="exact_target_name",
            observation_id="obs1",
            search_radius_deg=None,
            aliases_used=["M42"],
        )
        b = m.make_discovery_item(
            provider="mast",
            source_or_mission="HST",
            target_name="M42",
            target_category=None,
            query_type="archive",
            query_strategy="cone_0.05",
            wavelength_domain="visible",
            result_type="archive_observation",
            match_basis="cone_candidate",
            observation_id="obs1",
            search_radius_deg=0.05,
            aliases_used=["Orion Nebula"],
            warnings=["positional candidate only"],
        )
        merged_list = m.dedupe_items_by_observation([a, b])
        self.assertEqual(len(merged_list), 1)
        merged = merged_list[0]
        self.assertEqual(merged["match_basis"], "exact_target_name")
        self.assertCountEqual(merged["match_bases"], ["exact_target_name", "cone_candidate"])
        self.assertCountEqual(merged["query_strategies"], ["exact_target_name", "cone_0.05"])
        self.assertCountEqual(merged["aliases_used"], ["M42", "Orion Nebula"])
        self.assertEqual(merged["smallest_successful_radius_deg"], 0.05)
        self.assertIn("positional candidate only", merged["warnings"])

    def test_counts_concept_after_dedupe(self):
        items = [
            m.make_discovery_item(
                provider="mast",
                source_or_mission="HST",
                target_name="X",
                target_category=None,
                query_type="archive",
                query_strategy="cone_0.01",
                wavelength_domain="visible",
                result_type="archive_observation",
                match_basis="cone_candidate",
                observation_id="dup",
                search_radius_deg=0.01,
            ),
            m.make_discovery_item(
                provider="mast",
                source_or_mission="HST",
                target_name="X",
                target_category=None,
                query_type="archive",
                query_strategy="cone_0.05",
                wavelength_domain="visible",
                result_type="archive_observation",
                match_basis="cone_candidate",
                observation_id="dup",
                search_radius_deg=0.05,
            ),
            m.make_discovery_item(
                provider="mast",
                source_or_mission="HST",
                target_name="X",
                target_category=None,
                query_type="archive",
                query_strategy="exact_target_name",
                wavelength_domain="visible",
                result_type="archive_observation",
                match_basis="exact_target_name",
                observation_id="other",
            ),
        ]
        deduped = m.dedupe_items_by_observation(items)
        self.assertEqual(len(deduped), 2)

    def test_validate_bundle_rejects_item_without_result_type(self):
        bundle = m.empty_bundle()
        bundle["items"].append({"provider": "mast", "result_type": None, "match_basis": "cone_candidate"})
        errors = m.validate_bundle(bundle)
        self.assertTrue(any("result_type" in e for e in errors))


class TestDiscoveryOrchestrator(unittest.TestCase):
    def test_provider_failure_isolation(self):
        from app.discovery.orchestrator import run_discovery

        class Good:
            name = "good"

            def discover(self, context):
                return {
                    "items": [
                        m.make_discovery_item(
                            provider="good",
                            source_or_mission="HST",
                            target_name=context.get("target_name"),
                            target_category=None,
                            query_type="archive",
                            query_strategy="cone_0.01",
                            wavelength_domain="visible",
                            result_type="archive_observation",
                            match_basis="cone_candidate",
                            observation_id="a1",
                        )
                    ],
                    "query_outcomes": [
                        m.make_query_outcome(
                            provider="good",
                            query_status="success",
                            query_strategy="cone_0.01",
                        )
                    ],
                    "warnings": [],
                    "capability_notes": [],
                }

        class Bad:
            name = "bad"

            def discover(self, context):
                raise RuntimeError("boom")

        bundle = run_discovery({"target_name": "M42"}, [Good(), Bad()])
        self.assertEqual(len(bundle["items"]), 1)
        statuses = [o["query_status"] for o in bundle["query_outcomes"]]
        self.assertIn("unavailable", statuses)
        self.assertTrue(any("isolation" in w.lower() or "failed" in w.lower() for w in bundle["warnings"]))

    def test_zero_results_are_outcomes_not_items(self):
        from app.discovery.orchestrator import run_discovery

        class Empty:
            name = "mast"

            def discover(self, context):
                return {
                    "items": [],
                    "query_outcomes": [
                        m.make_query_outcome(
                            provider="mast",
                            query_status="zero_results",
                            query_strategy="cone_0.01",
                            message=(
                                "No matching observations were returned by this provider "
                                "for this position and search radius."
                            ),
                        )
                    ],
                    "warnings": [],
                    "capability_notes": [],
                }

        bundle = run_discovery({}, [Empty()])
        self.assertEqual(bundle["items"], [])
        self.assertEqual(bundle["query_outcomes"][0]["query_status"], "zero_results")
        self.assertIsNone(bundle["query_outcomes"][0]["result_type"])
        self.assertNotIn("does not exist", (bundle["query_outcomes"][0].get("message") or "").lower())


if __name__ == "__main__":
    unittest.main()
