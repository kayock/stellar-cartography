"""
MAST discovery provider — multi-strategy CAOM search (R0.5.0 Slice 1).

Uses the official MAST Portal API v0 (https://mast.stsci.edu/api/v0/).
Name/free-text search is supplementary to position strategies.
Exact aliases are tried before bounded wildcard free-text.
Widened cones are match_basis=cone_candidate only.
"""

from __future__ import annotations

import json
import logging
import math
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Optional

from app import mast_archive
from app.discovery.models import (
    dedupe_items_by_observation,
    empty_bundle,
    make_discovery_item,
    make_query_outcome,
)

logger = logging.getLogger("stellar_archive_bridge.discovery.mast")

PROVIDER_NAME = "mast"

# Radius ladder (degrees). Wider radii are positional candidates only.
RADIUS_LADDER_DEG = (0.01, 0.05, 0.2)
DEFAULT_RESOLVED_RADIUS_DEG = 0.01

ZERO_RESULT_MESSAGE = (
    "No matching observations were returned by this provider "
    "for this position and search radius."
)
CONE_CANDIDATE_WARNING = (
    "Positional candidate only: a widened or coordinate cone match is not proof "
    "that the selected object was the observation target."
)
MOVING_NOT_EVALUATED = (
    "Historical archive coverage for this moving object was not evaluated."
)

MISSION_DOMAIN = {
    "hst": "visible",
    "jwst_nircam": "infrared",
    "jwst_miri": "infrared",
}


def _normalize_alias(value: str | None) -> str | None:
    if not value or not isinstance(value, str):
        return None
    text = " ".join(value.strip().split())
    return text or None


def collect_aliases(context: dict) -> list[str]:
    """Preferred name first, then unique aliases (case-insensitive)."""
    ordered: list[str] = []
    seen: set[str] = set()

    def add(raw: object) -> None:
        if isinstance(raw, (list, tuple)):
            for part in raw:
                add(part)
            return
        norm = _normalize_alias(str(raw) if raw is not None else None)
        if not norm:
            return
        key = norm.casefold()
        if key in seen:
            return
        seen.add(key)
        ordered.append(norm)

    add(context.get("target_name"))
    add(context.get("preferred_name"))
    add(context.get("aliases"))
    add(context.get("alt_name"))
    add(context.get("catalogue_designations"))
    return ordered


def _coords_from_context(context: dict) -> tuple[float, float] | None:
    return mast_archive.normalize_coords(context.get("ra_deg"), context.get("dec_deg"))


def _classify_fetch_error(exc: BaseException) -> str:
    if isinstance(exc, TimeoutError):
        return "timeout"
    if isinstance(exc, urllib.error.HTTPError):
        if exc.code == 429:
            return "rate_limited"
        return "unavailable"
    if isinstance(exc, json.JSONDecodeError):
        return "malformed_response"
    if isinstance(exc, ValueError) and "too large" in str(exc).lower():
        return "malformed_response"
    return "unavailable"


def _default_fetch(request_obj: dict, timeout: float) -> dict:
    return mast_archive._default_fetch(request_obj, timeout)


def _mission_filters(mission: str) -> list[dict]:
    cfg = mast_archive.MISSION_CONFIGS[mission]
    return mast_archive._build_filters(cfg)


def build_filtered_position_list_request(ra: float, dec: float, radius: float, mission: str) -> dict:
    return {
        "service": "Mast.Caom.Filtered.Position",
        "params": {
            "columns": "obs_id,obs_collection,instrument_name,t_min,t_max,cal_start_time,dataproduct_type,intentType,target_name",
            "filters": _mission_filters(mission),
            "position": f"{ra}, {dec}, {radius}",
        },
        "format": "json",
        "pagesize": mast_archive.MAX_OBSERVATIONS,
        "page": 1,
        "removenullcolumns": True,
        "timeout": mast_archive.REQUEST_TIMEOUT_SEC,
    }


def build_filtered_target_name_request(mission: str, target_name: str, *, free_text: bool) -> dict:
    filters = _mission_filters(mission)
    if free_text:
        # Bounded wildcard — supplementary after exact alias miss.
        safe = target_name.replace("%", "").replace("'", "")
        filters.append(
            {
                "paramName": "target_name",
                "values": [],
                "freeText": f"%{safe}%",
            }
        )
        strategy_note = "free_text"
    else:
        filters.append({"paramName": "target_name", "values": [target_name]})
        strategy_note = "exact"
    _ = strategy_note
    return {
        "service": "Mast.Caom.Filtered",
        "params": {
            "columns": "obs_id,obs_collection,instrument_name,t_min,t_max,cal_start_time,dataproduct_type,intentType,target_name",
            "filters": filters,
        },
        "format": "json",
        "pagesize": mast_archive.MAX_OBSERVATIONS,
        "page": 1,
        "removenullcolumns": True,
        "timeout": mast_archive.REQUEST_TIMEOUT_SEC,
    }


def build_name_lookup_request(name: str) -> dict:
    return {
        "service": "Mast.Name.Lookup",
        "params": {"input": name, "format": "json"},
        "format": "json",
        "timeout": mast_archive.REQUEST_TIMEOUT_SEC,
    }


def parse_name_lookup_coords(payload: dict) -> tuple[float, float] | None:
    if not isinstance(payload, dict):
        return None
    # Common shapes: resolvedCoordinate list, or data rows with ra/dec.
    for key in ("resolvedCoordinate", "resolvedCoordinates", "data"):
        block = payload.get(key)
        if isinstance(block, list) and block:
            row = block[0]
            if not isinstance(row, dict):
                continue
            for ra_key, dec_key in (("ra", "decl"), ("ra", "dec"), ("s_ra", "s_dec")):
                if ra_key in row and dec_key in row:
                    coords = mast_archive.normalize_coords(row.get(ra_key), row.get(dec_key))
                    if coords:
                        return coords
    return None


def _result_type_for_row(row: dict) -> str:
    product = mast_archive.sanitize_text(row.get("dataproduct_type"), max_len=40)
    if product and "spectr" in product.lower():
        return "spectrum"
    return "archive_observation"


def _domain_for_mission(mission: str) -> str:
    return MISSION_DOMAIN.get(mission, "other")


def _rows_to_items(
    payload: dict,
    *,
    mission: str,
    query_strategy: str,
    match_basis: str,
    target_name: str | None,
    target_category: str | None,
    aliases_used: list[str] | None,
    search_radius_deg: float | None,
    coordinates: dict | None,
    cone_candidate: bool,
) -> list[dict]:
    if not isinstance(payload, dict):
        return []
    if payload.get("status") not in (None, "COMPLETE", "OK"):
        return []
    data = payload.get("data")
    if not isinstance(data, list):
        return []
    # Count-only payloads are not observation lists.
    if data and isinstance(data[0], dict) and any(k.startswith("COUNT") for k in data[0]):
        return []

    cfg = mast_archive.MISSION_CONFIGS[mission]
    items: list[dict] = []
    for row in data[: mast_archive.MAX_OBSERVATIONS]:
        if not isinstance(row, dict):
            continue
        obs_id = mast_archive.sanitize_text(row.get("obs_id"), max_len=80)
        if not obs_id:
            continue
        instrument = mast_archive.sanitize_text(row.get("instrument_name"), max_len=80)
        source_link = (
            "https://mast.stsci.edu/portal/Mashup/Clients/Mast/Portal/Mast.html?obsid="
            + urllib.parse.quote(obs_id)
        )
        if not mast_archive.is_allowed_source_url(source_link):
            source_link = None
        warnings = [CONE_CANDIDATE_WARNING] if cone_candidate else []
        summary = (
            f"{cfg['label']} archive observation {obs_id}"
            + (f" ({instrument})" if instrument else "")
        )
        if cone_candidate:
            summary += " — positional candidate only"
        items.append(
            make_discovery_item(
                provider=PROVIDER_NAME,
                source_or_mission=cfg["label"],
                target_name=target_name,
                target_category=target_category,
                query_type="archive_search",
                query_strategy=query_strategy,
                wavelength_domain=_domain_for_mission(mission),
                result_type=_result_type_for_row(row),
                match_basis=match_basis,
                observation_id=obs_id,
                instrument=instrument,
                observation_date=mast_archive._format_obs_date(row),
                coordinates=coordinates,
                search_radius_deg=search_radius_deg,
                provenance_url=source_link,
                confidence_or_evidence=match_basis,
                warnings=warnings,
                raw_provider_status=str(payload.get("status") or "COMPLETE"),
                summary=summary,
                aliases_used=aliases_used,
            )
        )
    return items


class MastDiscoveryProvider:
    name = PROVIDER_NAME

    def __init__(self, fetcher: Optional[Callable[[dict, float], dict]] = None):
        self._fetcher = fetcher or _default_fetch

    def discover(self, context: dict[str, Any]) -> dict:
        bundle = empty_bundle()
        missions = context.get("missions") or list(mast_archive.MISSION_CONFIGS.keys())
        missions = [m for m in missions if m in mast_archive.MISSION_CONFIGS]
        if not missions:
            bundle["query_outcomes"].append(
                make_query_outcome(
                    provider=PROVIDER_NAME,
                    query_status="unsupported",
                    query_strategy="mission_filter",
                    message="No supported MAST missions were requested.",
                )
            )
            return bundle

        moving = bool(context.get("moving_target") or context.get("treated_as_moving"))
        if moving:
            bundle["capability_notes"].append(MOVING_NOT_EVALUATED)
            bundle["query_outcomes"].append(
                make_query_outcome(
                    provider=PROVIDER_NAME,
                    query_status="ephemeris_required",
                    query_strategy="moving_object_guard",
                    target_name=context.get("target_name"),
                    target_category=context.get("target_category"),
                    message=MOVING_NOT_EVALUATED,
                )
            )
            # Slice 1: do not claim historical moving-object archive matching.
            return bundle

        aliases = collect_aliases(context)
        coords = _coords_from_context(context)
        target_name = aliases[0] if aliases else context.get("target_name")
        target_category = context.get("target_category")

        for mission in missions:
            self._discover_mission(
                bundle,
                mission=mission,
                aliases=aliases,
                coords=coords,
                target_name=target_name if isinstance(target_name, str) else None,
                target_category=target_category if isinstance(target_category, str) else None,
            )

        bundle["items"] = dedupe_items_by_observation(bundle["items"])
        return bundle

    def _fetch(self, request_obj: dict) -> tuple[dict | None, str | None]:
        try:
            payload = self._fetcher(request_obj, mast_archive.REQUEST_TIMEOUT_SEC)
        except Exception as exc:  # noqa: BLE001
            return None, _classify_fetch_error(exc)
        if not isinstance(payload, dict):
            return None, "malformed_response"
        return payload, None

    def _discover_mission(
        self,
        bundle: dict,
        *,
        mission: str,
        aliases: list[str],
        coords: tuple[float, float] | None,
        target_name: str | None,
        target_category: str | None,
    ) -> None:
        domain = _domain_for_mission(mission)
        strategy_statuses: list[str] = []

        # --- 1) Exact target_name aliases ---
        exact_items: list[dict] = []
        if aliases:
            for alias in aliases:
                strategy = f"exact_target_name:{mission}"
                req = build_filtered_target_name_request(mission, alias, free_text=False)
                payload, err = self._fetch(req)
                if err:
                    strategy_statuses.append(err)
                    bundle["query_outcomes"].append(
                        make_query_outcome(
                            provider=PROVIDER_NAME,
                            query_status=err,
                            query_strategy=strategy,
                            target_name=target_name,
                            mission=mission,
                            wavelength_domain=domain,
                            message=f"MAST exact target_name strategy failed ({err}).",
                        )
                    )
                    continue
                items = _rows_to_items(
                    payload or {},
                    mission=mission,
                    query_strategy=strategy,
                    match_basis="exact_target_name",
                    target_name=target_name,
                    target_category=target_category,
                    aliases_used=[alias],
                    search_radius_deg=None,
                    coordinates=None,
                    cone_candidate=False,
                )
                if items:
                    exact_items.extend(items)
                    strategy_statuses.append("success")
                    bundle["query_outcomes"].append(
                        make_query_outcome(
                            provider=PROVIDER_NAME,
                            query_status="success",
                            query_strategy=strategy,
                            target_name=target_name,
                            mission=mission,
                            wavelength_domain=domain,
                            message=f"Exact target_name match for alias '{alias}'.",
                        )
                    )
                    break
                strategy_statuses.append("zero_results")
                bundle["query_outcomes"].append(
                    make_query_outcome(
                        provider=PROVIDER_NAME,
                        query_status="zero_results",
                        query_strategy=strategy,
                        target_name=target_name,
                        mission=mission,
                        wavelength_domain=domain,
                        message=ZERO_RESULT_MESSAGE,
                    )
                )

            # --- 2) Bounded free-text only after exact aliases all missed ---
            if not exact_items and aliases:
                primary = aliases[0]
                strategy = f"target_name_freetext:{mission}"
                req = build_filtered_target_name_request(mission, primary, free_text=True)
                payload, err = self._fetch(req)
                if err:
                    strategy_statuses.append(err)
                    bundle["query_outcomes"].append(
                        make_query_outcome(
                            provider=PROVIDER_NAME,
                            query_status=err,
                            query_strategy=strategy,
                            target_name=target_name,
                            mission=mission,
                            wavelength_domain=domain,
                            message=f"MAST free-text target_name strategy failed ({err}).",
                        )
                    )
                else:
                    items = _rows_to_items(
                        payload or {},
                        mission=mission,
                        query_strategy=strategy,
                        match_basis="alias_match",
                        target_name=target_name,
                        target_category=target_category,
                        aliases_used=[primary],
                        search_radius_deg=None,
                        coordinates=None,
                        cone_candidate=False,
                    )
                    if items:
                        exact_items.extend(items)
                        strategy_statuses.append("success")
                        bundle["query_outcomes"].append(
                            make_query_outcome(
                                provider=PROVIDER_NAME,
                                query_status="success",
                                query_strategy=strategy,
                                target_name=target_name,
                                mission=mission,
                                wavelength_domain=domain,
                                message="Supplementary free-text target_name match.",
                                warnings=["Free-text alias match is supplementary; verify target identity."],
                            )
                        )
                    else:
                        strategy_statuses.append("zero_results")
                        bundle["query_outcomes"].append(
                            make_query_outcome(
                                provider=PROVIDER_NAME,
                                query_status="zero_results",
                                query_strategy=strategy,
                                target_name=target_name,
                                mission=mission,
                                wavelength_domain=domain,
                                message=ZERO_RESULT_MESSAGE,
                            )
                        )

        bundle["items"].extend(exact_items)

        # --- 3) Resolved position via Mast.Name.Lookup ---
        if aliases:
            strategy = f"name_lookup_cone:{mission}"
            payload, err = self._fetch(build_name_lookup_request(aliases[0]))
            if err:
                strategy_statuses.append(err)
                bundle["query_outcomes"].append(
                    make_query_outcome(
                        provider=PROVIDER_NAME,
                        query_status=err,
                        query_strategy=strategy,
                        target_name=target_name,
                        mission=mission,
                        wavelength_domain=domain,
                        message=f"MAST name lookup failed ({err}).",
                    )
                )
            else:
                resolved = parse_name_lookup_coords(payload or {})
                if not resolved:
                    strategy_statuses.append("zero_results")
                    bundle["query_outcomes"].append(
                        make_query_outcome(
                            provider=PROVIDER_NAME,
                            query_status="zero_results",
                            query_strategy=strategy,
                            target_name=target_name,
                            mission=mission,
                            wavelength_domain=domain,
                            message="Name lookup did not resolve to coordinates.",
                        )
                    )
                else:
                    ra, dec = resolved
                    coord_dict = {"ra_deg": ra, "dec_deg": dec, "frame": "ICRS"}
                    list_req = build_filtered_position_list_request(
                        ra, dec, DEFAULT_RESOLVED_RADIUS_DEG, mission
                    )
                    list_payload, list_err = self._fetch(list_req)
                    if list_err:
                        strategy_statuses.append(list_err)
                        bundle["query_outcomes"].append(
                            make_query_outcome(
                                provider=PROVIDER_NAME,
                                query_status=list_err,
                                query_strategy=strategy,
                                target_name=target_name,
                                mission=mission,
                                wavelength_domain=domain,
                                search_radius_deg=DEFAULT_RESOLVED_RADIUS_DEG,
                                coordinates=coord_dict,
                                message=f"Resolved-position cone failed ({list_err}).",
                            )
                        )
                    else:
                        items = _rows_to_items(
                            list_payload or {},
                            mission=mission,
                            query_strategy=strategy,
                            match_basis="resolved_position",
                            target_name=target_name,
                            target_category=target_category,
                            aliases_used=[aliases[0]],
                            search_radius_deg=DEFAULT_RESOLVED_RADIUS_DEG,
                            coordinates=coord_dict,
                            cone_candidate=False,
                        )
                        if items:
                            bundle["items"].extend(items)
                            strategy_statuses.append("success")
                            bundle["query_outcomes"].append(
                                make_query_outcome(
                                    provider=PROVIDER_NAME,
                                    query_status="success",
                                    query_strategy=strategy,
                                    target_name=target_name,
                                    mission=mission,
                                    wavelength_domain=domain,
                                    search_radius_deg=DEFAULT_RESOLVED_RADIUS_DEG,
                                    coordinates=coord_dict,
                                    message="Observations near name-resolved coordinates.",
                                )
                            )
                        else:
                            strategy_statuses.append("zero_results")
                            bundle["query_outcomes"].append(
                                make_query_outcome(
                                    provider=PROVIDER_NAME,
                                    query_status="zero_results",
                                    query_strategy=strategy,
                                    target_name=target_name,
                                    mission=mission,
                                    wavelength_domain=domain,
                                    search_radius_deg=DEFAULT_RESOLVED_RADIUS_DEG,
                                    coordinates=coord_dict,
                                    message=ZERO_RESULT_MESSAGE,
                                )
                            )

        # --- 4) Coordinate cone radius ladder ---
        if coords:
            ra, dec = coords
            coord_dict = {"ra_deg": ra, "dec_deg": dec, "frame": "ICRS"}
            found_at_smaller = False
            for radius in RADIUS_LADDER_DEG:
                strategy = f"cone_{radius}:{mission}"
                # Escalation: still query each radius for provenance, but mark >0.01 as candidates.
                payload, err = self._fetch(build_filtered_position_list_request(ra, dec, radius, mission))
                if err:
                    strategy_statuses.append(err)
                    bundle["query_outcomes"].append(
                        make_query_outcome(
                            provider=PROVIDER_NAME,
                            query_status=err,
                            query_strategy=strategy,
                            target_name=target_name,
                            mission=mission,
                            wavelength_domain=domain,
                            search_radius_deg=radius,
                            coordinates=coord_dict,
                            message=f"Cone search failed ({err}).",
                        )
                    )
                    continue
                cone_candidate = radius > RADIUS_LADDER_DEG[0]
                items = _rows_to_items(
                    payload or {},
                    mission=mission,
                    query_strategy=strategy,
                    match_basis="cone_candidate" if cone_candidate else "cone_candidate",
                    # Even the default cone is a positional candidate unless name-matched.
                    target_name=target_name,
                    target_category=target_category,
                    aliases_used=None,
                    search_radius_deg=radius,
                    coordinates=coord_dict,
                    cone_candidate=True,
                )
                # Primary basis for default small cone remains cone_candidate (not proof of target).
                if items:
                    # If we already found at a smaller radius, larger radius still merges provenance
                    # via dedupe; keep querying for merge of radii_used.
                    bundle["items"].extend(items)
                    strategy_statuses.append("success")
                    found_at_smaller = True
                    msg = ZERO_RESULT_MESSAGE  # noqa: F841 — replaced below
                    bundle["query_outcomes"].append(
                        make_query_outcome(
                            provider=PROVIDER_NAME,
                            query_status="success",
                            query_strategy=strategy,
                            target_name=target_name,
                            mission=mission,
                            wavelength_domain=domain,
                            search_radius_deg=radius,
                            coordinates=coord_dict,
                            message=(
                                "Cone search returned observation records (positional candidates)."
                            ),
                            warnings=[CONE_CANDIDATE_WARNING],
                        )
                    )
                    # Optional short-circuit: if smallest radius succeeded, still run wider for
                    # provenance merge — keep running (approved: preserve radii used).
                else:
                    strategy_statuses.append("zero_results")
                    bundle["query_outcomes"].append(
                        make_query_outcome(
                            provider=PROVIDER_NAME,
                            query_status="zero_results",
                            query_strategy=strategy,
                            target_name=target_name,
                            mission=mission,
                            wavelength_domain=domain,
                            search_radius_deg=radius,
                            coordinates=coord_dict,
                            message=ZERO_RESULT_MESSAGE,
                        )
                    )
                _ = found_at_smaller
        elif not aliases:
            bundle["query_outcomes"].append(
                make_query_outcome(
                    provider=PROVIDER_NAME,
                    query_status="unsupported",
                    query_strategy=f"mission:{mission}",
                    mission=mission,
                    wavelength_domain=domain,
                    message="MAST discovery requires coordinates and/or a target name.",
                )
            )
