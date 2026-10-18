"""
archaeoastronomy.py

Archaeoastronomy Visual Mode helpers. No Stellarium I/O and no silent
time changes. Historical reconstruction is metadata only until the
existing Sky Time Machine receives an explicit apply_time request.
"""

from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Any

REGISTRY_PATH = Path(__file__).resolve().parent / "data" / "archaeoastronomy_registry.json"

ELIGIBLE_STORY_TYPES = frozenset(
    {
        "archaeoastronomy",
        "solar_alignment",
        "lunar_alignment",
        "architectural_alignment",
        "horizon_calendar",
        "solar_lunar_alignment",
    }
)
PRIMARY_CONFIDENCE = frozenset({"strong_evidence", "scholarly_interpretation"})
RESEARCH_CONFIDENCE = frozenset({"disputed", "speculative"})
ALL_CONFIDENCE = PRIMARY_CONFIDENCE | RESEARCH_CONFIDENCE
MEAN_OBLIQUITY_DEG = 23.44
SENSITIVE_COORD_FLAGS = frozenset({"restricted", "sensitive", "unpublished"})


class ArchaeoastronomyError(ValueError):
    pass


@lru_cache(maxsize=1)
def load_registry() -> dict[str, Any]:
    raw = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("entries"), list):
        raise ArchaeoastronomyError("Archaeoastronomy registry is invalid.")
    return raw


def reload_registry() -> dict[str, Any]:
    load_registry.cache_clear()
    return load_registry()


def eligible_story_types() -> frozenset[str]:
    return ELIGIBLE_STORY_TYPES


def is_eligible_story(story: dict[str, Any] | None) -> bool:
    if not isinstance(story, dict):
        return False
    return (story.get("story_type") or "") in ELIGIBLE_STORY_TYPES


def badge_label(level: str | None) -> str:
    mapping = {
        "strong_evidence": "STRONG EVIDENCE",
        "scholarly_interpretation": "SCHOLARLY INTERPRETATION",
        "disputed": "DISPUTED",
        "speculative": "SPECULATIVE",
    }
    return mapping.get(level or "", "")


def primary_badge_allowed(level: str | None) -> bool:
    return (level or "") in PRIMARY_CONFIDENCE


def sunrise_sunset_azimuths(latitude_deg: float, declination_deg: float) -> dict[str, float] | None:
    """Geometric rise/set on an idealized horizon (altitude 0), no refraction."""
    if not math.isfinite(latitude_deg) or not math.isfinite(declination_deg):
        return None
    if abs(latitude_deg) > 90 or abs(declination_deg) > 90:
        return None
    phi = math.radians(latitude_deg)
    dec = math.radians(declination_deg)
    ratio = math.sin(dec) / math.cos(phi) if abs(math.cos(phi)) > 1e-12 else math.inf
    if abs(ratio) > 1:
        return None
    offset = math.degrees(math.asin(ratio))
    return {
        "sunrise_azimuth_deg": round(90.0 - offset, 2),
        "sunset_azimuth_deg": round(270.0 + offset, 2),
        "declination_deg": declination_deg,
        "latitude_deg": latitude_deg,
    }


def idealized_solar_path(latitude_deg: float) -> dict[str, Any]:
    events = {
        "summer_solstice": MEAN_OBLIQUITY_DEG,
        "equinox": 0.0,
        "winter_solstice": -MEAN_OBLIQUITY_DEG,
    }
    markers = {}
    for name, dec in events.items():
        az = sunrise_sunset_azimuths(latitude_deg, dec)
        if az:
            markers[name] = az
    return {
        "horizon_model": "idealized",
        "label": "idealized horizon",
        "note": "Idealized horizon. Local terrain elevation is not modeled.",
        "latitude_deg": latitude_deg,
        "obliquity_deg": MEAN_OBLIQUITY_DEG,
        "events": markers,
    }


def public_site_coordinates(site: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(site, dict):
        return None
    if site.get("coordinates_sensitivity") in SENSITIVE_COORD_FLAGS:
        return None
    if site.get("coordinates_public") is not True:
        return None
    try:
        lat = float(site["latitude"])
        lon = float(site["longitude"])
    except (KeyError, TypeError, ValueError):
        return None
    if not math.isfinite(lat) or not math.isfinite(lon):
        return None
    if abs(lat) > 90 or abs(lon) > 180:
        return None
    return {
        "latitude": round(lat, 2),
        "longitude": round(lon, 2),
        "precision": "public_park_vicinity",
        "note": site.get("coordinates_note")
        or "Widely published park vicinity. Not a restricted feature GPS.",
    }


def get_entry(visual_id: str | None, *, production_only: bool = True) -> dict[str, Any] | None:
    key = (visual_id or "").strip()
    if not key:
        return None
    for entry in load_registry().get("entries") or []:
        if not isinstance(entry, dict) or entry.get("id") != key:
            continue
        if production_only and not entry.get("production"):
            return None
        return entry
    return None


def foundation_entry(visual_id: str | None) -> dict[str, Any] | None:
    return get_entry(visual_id, production_only=False)


def _source_map(entry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        src["id"]: src
        for src in (entry.get("sources") or [])
        if isinstance(src, dict) and src.get("id")
    }


def _claim_sources(claim: dict[str, Any], source_map: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for sid in claim.get("source_ids") or []:
        src = source_map.get(sid)
        if not src:
            raise ArchaeoastronomyError(f"Visual claim '{claim.get('id')}' cites unknown source '{sid}'.")
        rows.append(
            {
                "id": src["id"],
                "title": src.get("title"),
                "institution": src.get("institution"),
                "date": src.get("date"),
                "url": src.get("url"),
                "evidence_type": src.get("evidence_type"),
                "interpretation_status": src.get("interpretation_status"),
            }
        )
    if not rows:
        raise ArchaeoastronomyError(f"Visual claim '{claim.get('id')}' has no mapped source.")
    return rows


def _split_claims(entry: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    source_map = _source_map(entry)
    primary: list[dict[str, Any]] = []
    research: list[dict[str, Any]] = []
    for claim in entry.get("visual_claims") or []:
        if not isinstance(claim, dict):
            continue
        level = claim.get("confidence")
        if level not in ALL_CONFIDENCE:
            raise ArchaeoastronomyError(f"Claim '{claim.get('id')}' has unsupported confidence.")
        shown = claim.get("shown_in")
        row = {
            "id": claim.get("id"),
            "label": claim.get("label"),
            "confidence": level,
            "confidence_label": badge_label(level),
            "shown_in": shown,
            "sources": _claim_sources(claim, source_map),
        }
        if shown == "primary":
            if not primary_badge_allowed(level):
                raise ArchaeoastronomyError(
                    f"Primary claim '{claim.get('id')}' cannot use {level}."
                )
            primary.append(row)
        else:
            research.append(row)
    return primary, research


def site_context_card(entry: dict[str, Any]) -> dict[str, Any]:
    site = entry.get("site_context") if isinstance(entry.get("site_context"), dict) else {}
    return {
        "site": site.get("site"),
        "culture_label": site.get("culture_label"),
        "region": site.get("region"),
        "date_range": site.get("date_range"),
        "evidence_type": site.get("evidence_type"),
        "source_institution": site.get("source_institution"),
        "interpretation_status": site.get("interpretation_status"),
        "interpretation_label": badge_label(site.get("interpretation_status")),
        "coordinates": public_site_coordinates(site),
    }


def visual_payload(visual_id: str | None, *, production_only: bool = True) -> dict[str, Any]:
    entry = get_entry(visual_id, production_only=production_only)
    if not entry:
        return {"ok": False, "error": "No production archaeoastronomy visual for this story."}
    primary, research = _split_claims(entry)
    site = site_context_card(entry)
    lat = (site.get("coordinates") or {}).get("latitude")
    solar = idealized_solar_path(float(lat)) if isinstance(lat, (int, float)) else None
    return {
        "ok": True,
        "id": entry["id"],
        "production": bool(entry.get("production")),
        "promotion_status": entry.get("promotion_status"),
        "foundation_only": bool(entry.get("foundation_only")),
        "visual_mode": entry.get("visual_mode"),
        "story_type": entry.get("story_type"),
        "confidence": entry.get("confidence"),
        "confidence_label": badge_label(entry.get("confidence")),
        "schematic_label": entry.get("schematic_label") or "interpretive schematic",
        "precision_note": entry.get("precision_note"),
        "horizon_model": entry.get("horizon_model") or "idealized",
        "horizon_note": entry.get("horizon_note")
        or "Idealized horizon. Local terrain elevation is not modeled.",
        "site_context": site,
        "schematic": entry.get("schematic") or {},
        "primary_claims": primary,
        "research_context": research,
        "evidence_sources": [
            {
                "id": src.get("id"),
                "title": src.get("title"),
                "institution": src.get("institution"),
                "date": src.get("date"),
                "url": src.get("url"),
                "evidence_type": src.get("evidence_type"),
                "interpretation_status": src.get("interpretation_status"),
                "interpretation_label": badge_label(src.get("interpretation_status")),
            }
            for src in (entry.get("sources") or [])
            if isinstance(src, dict)
        ],
        "historical_dates": [
            {
                **date,
                "kind": "astronomical_reconstruction",
                "apply_requires_explicit_action": True,
                "silent_apply": False,
            }
            for date in (entry.get("historical_dates") or [])
            if isinstance(date, dict)
        ],
        "solar_path": solar,
        "reconstruction_label": "astronomical reconstruction",
        "reconstruction_note": (
            "A modern planetarium simulation can explore the historical sky only after "
            "you choose a date. The simulation does not prove the archaeological interpretation."
        ),
        "audio_autoplay": False,
        "applies_stellarium_time": False,
    }


def historical_time_request(visual_id: str, date_id: str) -> dict[str, Any]:
    """Build an explicit Time Machine payload. Does not talk to Stellarium."""
    entry = get_entry(visual_id, production_only=True)
    if not entry:
        return {"ok": False, "error": "No production visual for historical reconstruction."}
    chosen = None
    for date in entry.get("historical_dates") or []:
        if isinstance(date, dict) and date.get("id") == date_id:
            chosen = date
            break
    if not chosen:
        return {"ok": False, "error": "Unknown historical reconstruction date."}
    return {
        "ok": True,
        "apply_time": True,
        "apply_location": False,
        "reconstruction": True,
        "utc": chosen.get("utc"),
        "preset": None,
        "label": chosen.get("label"),
        "kind": "astronomical_reconstruction",
        "note": chosen.get("note"),
        "silent_apply": False,
    }


def narration_text(visual: dict[str, Any]) -> str:
    if not visual.get("ok"):
        return "No archaeoastronomy visual is available."
    confidence = visual.get("confidence")
    site = (visual.get("site_context") or {}).get("site") or visual.get("id")
    if confidence == "strong_evidence":
        lead = f"This alignment is strongly supported by public archaeological evidence at {site}."
    elif confidence == "scholarly_interpretation":
        lead = f"Researchers have interpreted {site} as a public archaeoastronomy record."
    else:
        lead = f"Archaeological evidence suggests an observational reading of {site}."
    return " ".join(
        [
            lead,
            visual.get("precision_note") or "",
            "This is archaeological inference, not a living oral constellation story.",
        ]
    ).strip()
