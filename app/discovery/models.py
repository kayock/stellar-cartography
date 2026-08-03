"""
Discovery contracts for FOXAI Stellar Cartography R0.5.0 Slice 1.

Query outcomes (provider call results) are separate from scientific discovery
items. Failures, zeros, unsupported targets, and ephemeris requirements must
never be represented as scientific result types.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Optional

QUERY_STATUSES = frozenset(
    {
        "success",
        "zero_results",
        "unavailable",
        "timeout",
        "rate_limited",
        "malformed_response",
        "unsupported",
        "ephemeris_required",
    }
)

# Statuses that must never produce DiscoveryBundle.items entries.
NON_ITEM_QUERY_STATUSES = frozenset(
    {
        "zero_results",
        "unavailable",
        "timeout",
        "rate_limited",
        "malformed_response",
        "unsupported",
        "ephemeris_required",
    }
)

RESULT_TYPES = frozenset(
    {
        "public_media_asset",
        "archive_observation",
        "science_image_product",
        "spectrum",
        "catalog_detection",
        "mission_metadata",
        "object_information",
        "contextual_information",
    }
)

MATCH_BASES = frozenset(
    {
        "exact_target_name",
        "alias_match",
        "resolved_position",
        "footprint_overlap",
        "cone_candidate",
    }
)

# Primary match-basis precedence when merging duplicate observations.
MATCH_BASIS_PRECEDENCE = (
    "exact_target_name",
    "alias_match",
    "footprint_overlap",
    "resolved_position",
    "cone_candidate",
)

DOMAINS = frozenset(
    {
        "visible",
        "infrared",
        "ultraviolet",
        "xray",
        "radio",
        "planetary_imagery",
        "catalogs_metadata",
        "contextual",
        "other",
    }
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def prefer_match_basis(bases: list[str] | tuple[str, ...] | set[str]) -> str | None:
    """Return the highest-precedence match_basis from a collection."""
    present = {b for b in bases if b in MATCH_BASES}
    if not present:
        return None
    for basis in MATCH_BASIS_PRECEDENCE:
        if basis in present:
            return basis
    return None


def make_query_outcome(
    *,
    provider: str,
    query_status: str,
    query_strategy: str,
    target_name: str | None = None,
    target_category: str | None = None,
    mission: str | None = None,
    wavelength_domain: str | None = None,
    search_radius_deg: float | None = None,
    coordinates: dict | None = None,
    message: str | None = None,
    raw_provider_status: str | None = None,
    warnings: list[str] | None = None,
    retrieval_timestamp: str | None = None,
) -> dict:
    if query_status not in QUERY_STATUSES:
        raise ValueError(f"Invalid query_status: {query_status}")
    return {
        "provider": provider,
        "query_status": query_status,
        "query_strategy": query_strategy,
        "target_name": target_name,
        "target_category": target_category,
        "mission": mission,
        "wavelength_domain": wavelength_domain,
        "search_radius_deg": search_radius_deg,
        "coordinates": coordinates,
        "message": message,
        "raw_provider_status": raw_provider_status,
        "warnings": list(warnings or []),
        "retrieval_timestamp": retrieval_timestamp or utc_now_iso(),
        # Explicit: outcomes are not scientific items.
        "result_type": None,
    }


def make_discovery_item(
    *,
    provider: str,
    source_or_mission: str,
    target_name: str | None,
    target_category: str | None,
    query_type: str,
    query_strategy: str,
    wavelength_domain: str | None,
    result_type: str,
    match_basis: str,
    observation_id: str | None = None,
    instrument: str | None = None,
    observation_date: str | None = None,
    observation_date_range: str | None = None,
    coordinates: dict | None = None,
    search_radius_deg: float | None = None,
    treated_as_moving: bool = False,
    provenance_url: str | None = None,
    confidence_or_evidence: str | None = None,
    warnings: list[str] | None = None,
    raw_provider_status: str | None = None,
    summary: str | None = None,
    aliases_used: list[str] | None = None,
    retrieval_timestamp: str | None = None,
    result_count: int | None = None,
) -> dict:
    if result_type is None or result_type not in RESULT_TYPES:
        raise ValueError("Every discovery item must have a non-null result_type")
    if match_basis not in MATCH_BASES:
        raise ValueError(f"Invalid match_basis: {match_basis}")
    return {
        "provider": provider,
        "source_or_mission": source_or_mission,
        "target_name": target_name,
        "target_category": target_category,
        "query_type": query_type,
        "query_strategy": query_strategy,
        "query_strategies": [query_strategy] if query_strategy else [],
        "wavelength_domain": wavelength_domain,
        "result_type": result_type,
        "match_basis": match_basis,
        "match_bases": [match_basis],
        "observation_id": observation_id,
        "instrument": instrument,
        "observation_date": observation_date,
        "observation_date_range": observation_date_range,
        "coordinates": coordinates,
        "search_radius_deg": search_radius_deg,
        "radii_used_deg": [search_radius_deg] if search_radius_deg is not None else [],
        "smallest_successful_radius_deg": search_radius_deg,
        "aliases_used": list(aliases_used or []),
        "treated_as_fixed_or_moving": "moving" if treated_as_moving else "fixed",
        "provenance_url": provenance_url,
        "retrieval_timestamp": retrieval_timestamp or utc_now_iso(),
        "confidence_or_evidence": confidence_or_evidence,
        "warnings": list(warnings or []),
        "raw_provider_status": raw_provider_status,
        "summary": summary,
        "result_count": result_count,
    }


def empty_bundle() -> dict:
    return {
        "items": [],
        "query_outcomes": [],
        "warnings": [],
        "capability_notes": [],
    }


def merge_discovery_items(existing: dict, incoming: dict) -> dict:
    """
    Merge duplicate observation hits, preserving provenance from every strategy.

    Dedup key is expected to already match (caller groups by observation identity).
    """
    merged = deepcopy(existing)

    strategies = list(merged.get("query_strategies") or [])
    for s in incoming.get("query_strategies") or ([incoming.get("query_strategy")] if incoming.get("query_strategy") else []):
        if s and s not in strategies:
            strategies.append(s)
    merged["query_strategies"] = strategies
    if strategies:
        merged["query_strategy"] = strategies[0]

    bases = list(merged.get("match_bases") or [])
    for b in incoming.get("match_bases") or ([incoming.get("match_basis")] if incoming.get("match_basis") else []):
        if b and b not in bases:
            bases.append(b)
    merged["match_bases"] = bases
    primary = prefer_match_basis(bases)
    if primary:
        merged["match_basis"] = primary

    aliases = list(merged.get("aliases_used") or [])
    for a in incoming.get("aliases_used") or []:
        if a and a not in aliases:
            aliases.append(a)
    merged["aliases_used"] = aliases

    radii: list[float] = []
    for r in (merged.get("radii_used_deg") or []) + (incoming.get("radii_used_deg") or []):
        if r is None:
            continue
        try:
            fr = float(r)
        except (TypeError, ValueError):
            continue
        if fr not in radii:
            radii.append(fr)
    if incoming.get("search_radius_deg") is not None:
        try:
            fr = float(incoming["search_radius_deg"])
            if fr not in radii:
                radii.append(fr)
        except (TypeError, ValueError):
            pass
    merged["radii_used_deg"] = radii
    if radii:
        smallest = min(radii)
        merged["smallest_successful_radius_deg"] = smallest
        # Keep search_radius_deg as the smallest successful radius for display.
        merged["search_radius_deg"] = smallest

    # Prefer richer fields when missing on existing.
    for key in (
        "instrument",
        "observation_date",
        "observation_date_range",
        "provenance_url",
        "summary",
        "coordinates",
        "confidence_or_evidence",
    ):
        if not merged.get(key) and incoming.get(key):
            merged[key] = incoming[key]

    warn = list(merged.get("warnings") or [])
    for w in incoming.get("warnings") or []:
        if w and w not in warn:
            warn.append(w)
    merged["warnings"] = warn
    return merged


def dedupe_items_by_observation(items: list[dict]) -> list[dict]:
    """Merge items that share the same provider + observation_id (+ mission)."""
    grouped: dict[str, dict] = {}
    order: list[str] = []
    passthrough: list[dict] = []

    for item in items:
        obs_id = item.get("observation_id")
        if not obs_id:
            passthrough.append(item)
            continue
        key = "|".join(
            [
                str(item.get("provider") or ""),
                str(item.get("source_or_mission") or ""),
                str(obs_id),
            ]
        )
        if key not in grouped:
            grouped[key] = deepcopy(item)
            # Normalize list fields
            if not grouped[key].get("query_strategies"):
                qs = grouped[key].get("query_strategy")
                grouped[key]["query_strategies"] = [qs] if qs else []
            if not grouped[key].get("match_bases"):
                mb = grouped[key].get("match_basis")
                grouped[key]["match_bases"] = [mb] if mb else []
            if grouped[key].get("radii_used_deg") is None:
                grouped[key]["radii_used_deg"] = []
            order.append(key)
        else:
            grouped[key] = merge_discovery_items(grouped[key], item)

    return [grouped[k] for k in order] + passthrough


def validate_bundle(bundle: dict) -> list[str]:
    """Return a list of contract violations (empty if valid)."""
    errors: list[str] = []
    if not isinstance(bundle, dict):
        return ["bundle must be a dict"]
    for key in ("items", "query_outcomes", "warnings", "capability_notes"):
        if key not in bundle or not isinstance(bundle[key], list):
            errors.append(f"bundle.{key} must be a list")
    for i, item in enumerate(bundle.get("items") or []):
        if not isinstance(item, dict):
            errors.append(f"items[{i}] must be a dict")
            continue
        if item.get("result_type") is None or item.get("result_type") not in RESULT_TYPES:
            errors.append(f"items[{i}] must have a non-null result_type")
        if item.get("match_basis") not in MATCH_BASES:
            errors.append(f"items[{i}] has invalid match_basis")
    for i, outcome in enumerate(bundle.get("query_outcomes") or []):
        if not isinstance(outcome, dict):
            errors.append(f"query_outcomes[{i}] must be a dict")
            continue
        status = outcome.get("query_status")
        if status not in QUERY_STATUSES:
            errors.append(f"query_outcomes[{i}] has invalid query_status")
        if status in NON_ITEM_QUERY_STATUSES and outcome.get("result_type") not in (None,):
            errors.append(f"query_outcomes[{i}] must not carry a scientific result_type")
    return errors


def bundle_to_jsonable(bundle: dict) -> dict:
    """Shallow copy suitable for JSON serialization."""
    return {
        "items": list(bundle.get("items") or []),
        "query_outcomes": list(bundle.get("query_outcomes") or []),
        "warnings": list(bundle.get("warnings") or []),
        "capability_notes": list(bundle.get("capability_notes") or []),
    }
