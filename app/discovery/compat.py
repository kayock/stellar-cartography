"""
Badge / legacy response compatibility for discovery bundles (Slice 1).

Conservative mapping rules:
- ``no_coverage`` only when every required MAST strategy completed normally
  (success or zero_results) and no relevant items were found.
- If any strategy timed out / unavailable / rate-limited / malformed and no
  items were found → ``unavailable`` (not no_coverage).
- If items were found but another strategy failed → ``confirmed`` plus a
  partial-failure warning.
"""

from __future__ import annotations

from app import mast_archive

FAILURE_STATUSES = frozenset(
    {"timeout", "unavailable", "rate_limited", "malformed_response"}
)
NORMAL_COMPLETION = frozenset({"success", "zero_results"})


def _mission_label(mission: str) -> str | None:
    cfg = mast_archive.MISSION_CONFIGS.get(mission) or {}
    return cfg.get("label")


def _items_for_mission(bundle: dict, mission: str) -> list[dict]:
    label = _mission_label(mission)
    items = []
    for item in bundle.get("items") or []:
        if not isinstance(item, dict):
            continue
        src = (item.get("source_or_mission") or "").strip()
        # Also accept mission key in query_strategy suffixes.
        strategies = item.get("query_strategies") or []
        strat_hit = any(str(s).endswith(":" + mission) or str(s).endswith(mission) for s in strategies)
        if label and src == label:
            items.append(item)
        elif strat_hit:
            items.append(item)
    return items


def _outcomes_for_mission(bundle: dict, mission: str) -> list[dict]:
    out = []
    for outcome in bundle.get("query_outcomes") or []:
        if not isinstance(outcome, dict):
            continue
        if outcome.get("mission") == mission:
            out.append(outcome)
            continue
        strategy = str(outcome.get("query_strategy") or "")
        if strategy.endswith(":" + mission) or f":{mission}" in strategy:
            out.append(outcome)
    return out


def mission_badge_from_bundle(bundle: dict, mission: str) -> dict:
    """
    Map a DiscoveryBundle to the R0.4 archive-availability light/API shape
    for one mission key (hst | jwst_nircam | jwst_miri).
    """
    if mission not in mast_archive.MISSION_CONFIGS:
        return mast_archive._build_result(
            ok=False,
            status="error",
            error="Unsupported mission identifier.",
        )

    items = _items_for_mission(bundle, mission)
    outcomes = _outcomes_for_mission(bundle, mission)
    warnings = list(bundle.get("warnings") or [])

    failure_outcomes = [o for o in outcomes if o.get("query_status") in FAILURE_STATUSES]
    normal_outcomes = [o for o in outcomes if o.get("query_status") in NORMAL_COMPLETION]

    observations = []
    for item in items[: mast_archive.MAX_OBSERVATIONS]:
        observations.append(
            {
                "mission": item.get("source_or_mission"),
                "instrument": item.get("instrument"),
                "observation_id": item.get("observation_id"),
                "observation_date": item.get("observation_date"),
                "preview_available": False,
                "source_link": item.get("provenance_url"),
                "match_basis": item.get("match_basis"),
                "query_strategies": item.get("query_strategies") or [],
            }
        )

    # Deduped count only.
    count = len(items)

    if count > 0:
        if failure_outcomes:
            warnings.append(
                "Partial provider failure: some MAST strategies failed, but "
                "confirmed observations from successful strategies were preserved."
            )
        result = mast_archive._build_result(
            ok=True,
            status="confirmed",
            mission=mission,
            count=count,
            observations=observations,
        )
        result["warnings"] = warnings
        result["partial_failure"] = bool(failure_outcomes)
        return result

    # No items: distinguish true zero vs incomplete query set.
    if failure_outcomes:
        err = failure_outcomes[0].get("message") or "Archive check unavailable."
        result = mast_archive._build_result(
            ok=False,
            status="unavailable",
            mission=mission,
            error=err,
        )
        result["warnings"] = warnings
        return result

    if outcomes and all(o.get("query_status") in NORMAL_COMPLETION for o in outcomes):
        result = mast_archive._build_result(
            ok=True,
            status="no_coverage",
            mission=mission,
            count=0,
            observations=[],
        )
        result["warnings"] = warnings
        result["honest_zero"] = True
        return result

    if not outcomes:
        # No strategies ran for this mission (e.g. moving-object guard only).
        moving_notes = [
            o
            for o in (bundle.get("query_outcomes") or [])
            if o.get("query_status") == "ephemeris_required"
        ]
        if moving_notes:
            result = mast_archive._build_result(
                ok=False,
                status="unavailable",
                mission=mission,
                error=moving_notes[0].get("message")
                or "Historical archive coverage for this moving object was not evaluated.",
            )
            result["warnings"] = warnings
            result["query_status"] = "ephemeris_required"
            return result
        return mast_archive._build_result(
            ok=False,
            status="unavailable",
            mission=mission,
            error="Archive check unavailable.",
        )

    # Mixed non-failure abnormal statuses (unsupported, etc.)
    return mast_archive._build_result(
        ok=False,
        status="unavailable",
        mission=mission,
        error="Archive check unavailable.",
    )


def badges_from_bundle(bundle: dict, missions: list[str] | None = None) -> dict:
    missions = missions or list(mast_archive.MISSION_CONFIGS.keys())
    return {m: mission_badge_from_bundle(bundle, m) for m in missions if m in mast_archive.MISSION_CONFIGS}


def discovery_api_payload(bundle: dict, *, missions: list[str] | None = None) -> dict:
    """JSON payload for GET /api/discovery — feeds panel and badge adapter."""
    return {
        "ok": True,
        "bundle": {
            "items": list(bundle.get("items") or []),
            "query_outcomes": list(bundle.get("query_outcomes") or []),
            "warnings": list(bundle.get("warnings") or []),
            "capability_notes": list(bundle.get("capability_notes") or []),
        },
        "badges": badges_from_bundle(bundle, missions),
    }
