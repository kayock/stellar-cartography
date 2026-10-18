"""
exhibit.py

Curated exhibit / story-path mode. Steps reference existing stories,
archaeoastronomy visuals, Cosmic Signal, Official Media, Spectrum, and
the Sky Time Machine. This module never starts a second Stellarium
process and never applies historical time unless the caller is explicit.
"""

from __future__ import annotations

import json
import re
import threading
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from . import archaeoastronomy
from . import constellation_story
from . import cosmic_signal_registry
from . import experience
from . import official_media
from . import spectrum_gallery_registry
from . import light_echoes
from . import cosmic_web
from . import gravitational_waves
from . import black_holes
from . import galactic_encounters
from . import cosmic_dawn

REGISTRY_PATH = Path(__file__).resolve().parent / "data" / "exhibit_registry.json"

_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
STEP_TYPES = frozenset(
    {
        "intro",
        "constellation_story",
        "cultural_story",
        "object_focus",
        "archaeoastronomy",
        "historical_reconstruction",
        "same_sky_comparison",
        "cosmic_signal",
        "official_media",
        "spectrum",
        "data_sonification",
        "light_echo",
        "cosmic_web",
        "gravitational_waves",
        "black_holes",
        "galactic_encounters",
        "cosmic_dawn",
        "outro",
    }
)
SAFE_AUTO_ADVANCE_TYPES = frozenset(
    {
        "intro",
        "constellation_story",
        "cultural_story",
        "object_focus",
        "archaeoastronomy",
        "same_sky_comparison",
        "light_echo",
        "cosmic_web",
        "gravitational_waves",
        "black_holes",
        "galactic_encounters",
        "cosmic_dawn",
        "outro",
    }
)
MEDIA_STEP_TYPES = frozenset({"cosmic_signal", "official_media", "spectrum", "data_sonification"})
RESTRICTED_STATUSES = frozenset({"restricted", "deferred_restricted", "deferred"})
BLOCKED_CULTURES_UNLESS_READY = frozenset(
    {"dine", "navajo", "apache", "hopi", "zuni", "acoma", "taos"}
)
FUTURE_EXHIBIT_IDS = (
    "lives_of_the_stars",
    "same_sky_different_stories",
    "solar_system_time_machine",
    "cosmic_catastrophes",
    "navigation_by_stars",
)
EVIDENCE_BADGES = {
    "cultural_source": "CULTURAL SOURCE",
    "historical_source": "HISTORICAL SOURCE",
    "community_sourced": "COMMUNITY-SOURCED",
    "archaeological_inference": "ARCHAEOLOGICAL INFERENCE",
    "strong_evidence": "STRONG EVIDENCE",
    "scholarly_interpretation": "SCHOLARLY INTERPRETATION",
    "cultural_sky_knowledge": "CULTURAL SKY KNOWLEDGE",
    "historical_astronomy": "HISTORICAL ASTRONOMY",
    "scientific_media": "SCIENTIFIC MEDIA",
    "illustrative_geometry": "ILLUSTRATIVE GEOMETRY",
}
SIGNAL_CLASS_LABELS = {
    "measured_signal": "MEASURED SIGNAL",
    "measurement_derived_audio": "MEASUREMENT-DERIVED AUDIO",
    "audification": "AUDIFICATION",
    "data_sonification": "DATA SONIFICATION",
    "pulse_timing_data": "PULSE / TIMING DATA",
    "generated_cartography_sonification": "GENERATED CARTOGRAPHY SONIFICATION",
}
MAPPING_UNAVAILABLE = "Mapping details not available in the local source metadata."
PULSE_TIMING_HINTS = (
    "light curve",
    "pulse rate",
    "pulse timing",
    "pulsar timing",
    "timing data",
    "pulses almost",
)
STELLARIUM_FOCUS_BY_TARGET = {
    "jupiter": "Jupiter",
    "saturn": "Saturn",
    "crab_nebula": "Crab Nebula",
    "cassiopeia_a": "Cassiopeia A",
    "sagittarius_a": "Sagittarius A East",
    "m31": "Andromeda Galaxy",
}
STELLARIUM_FOCUS_NOTES = {
    "sagittarius_a": (
        "Sagittarius A* is not selectable in Stellarium 26.3 Remote Control; "
        "verified search_name is Sagittarius A East."
    ),
}
REQUIRED_EXHIBIT_FIELDS = (
    "id",
    "title",
    "subtitle",
    "description",
    "theme",
    "estimated_minutes",
    "culture_scope",
    "story_ids",
    "cover_media",
    "narrator_default",
    "source_note",
    "enabled",
    "steps",
)

_session_lock = threading.Lock()
_session: Optional[dict[str, Any]] = None


class ExhibitError(ValueError):
    pass


@lru_cache(maxsize=1)
def load_registry() -> dict[str, Any]:
    raw = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    validate_registry(raw)
    return raw


def reload_registry() -> dict[str, Any]:
    load_registry.cache_clear()
    return load_registry()


def validate_registry(raw: dict[str, Any]) -> None:
    if not isinstance(raw, dict) or not isinstance(raw.get("exhibits"), list):
        raise ExhibitError("Exhibit registry is invalid.")
    seen: set[str] = set()
    for exhibit in raw["exhibits"]:
        validate_exhibit(exhibit)
        eid = exhibit["id"]
        if eid in seen:
            raise ExhibitError(f"Duplicate exhibit id '{eid}'.")
        seen.add(eid)


def validate_exhibit(exhibit: dict[str, Any]) -> None:
    if not isinstance(exhibit, dict):
        raise ExhibitError("Each exhibit must be an object.")
    for field in REQUIRED_EXHIBIT_FIELDS:
        if field not in exhibit:
            raise ExhibitError(f"Exhibit missing '{field}'.")
    eid = exhibit.get("id")
    if not isinstance(eid, str) or not _ID_RE.match(eid):
        raise ExhibitError("Exhibit id is invalid.")
    if not isinstance(exhibit.get("title"), str) or not exhibit["title"].strip():
        raise ExhibitError(f"Exhibit '{eid}' missing title.")
    if not isinstance(exhibit.get("estimated_minutes"), (int, float)) or exhibit["estimated_minutes"] <= 0:
        raise ExhibitError(f"Exhibit '{eid}' estimated_minutes must be a positive number.")
    if not isinstance(exhibit.get("culture_scope"), list) or not exhibit["culture_scope"]:
        raise ExhibitError(f"Exhibit '{eid}' culture_scope must be a non-empty list.")
    if not isinstance(exhibit.get("story_ids"), list):
        raise ExhibitError(f"Exhibit '{eid}' story_ids must be a list.")
    if not isinstance(exhibit.get("enabled"), bool):
        raise ExhibitError(f"Exhibit '{eid}' enabled must be a boolean.")
    steps = exhibit.get("steps")
    if not isinstance(steps, list) or not steps:
        raise ExhibitError(f"Exhibit '{eid}' must have at least one step.")
    seen_steps: set[str] = set()
    for index, step in enumerate(steps):
        _validate_step(exhibit, step, index)
        sid = step["step_id"]
        if sid in seen_steps:
            raise ExhibitError(f"Exhibit '{eid}' has duplicate step_id '{sid}'.")
        seen_steps.add(sid)
    for story_id in exhibit["story_ids"]:
        _require_ready_story(story_id, exhibit_id=eid)
    _validate_unique_primary_signals(exhibit)


def _validate_step(exhibit: dict[str, Any], step: dict[str, Any], index: int) -> None:
    eid = exhibit["id"]
    if not isinstance(step, dict):
        raise ExhibitError(f"Exhibit '{eid}' step {index} must be an object.")
    step_id = step.get("step_id")
    if not isinstance(step_id, str) or not _ID_RE.match(step_id):
        raise ExhibitError(f"Exhibit '{eid}' step {index} has an invalid step_id.")
    step_type = step.get("step_type")
    if step_type not in STEP_TYPES:
        raise ExhibitError(f"Exhibit '{eid}' step '{step_id}' has unsupported step_type.")
    if not isinstance(step.get("title"), str) or not step["title"].strip():
        raise ExhibitError(f"Exhibit '{eid}' step '{step_id}' missing title.")
    for field in (
        "story_id",
        "constellation_id",
        "cultural_story_id",
        "archaeo_visual_id",
        "cosmic_signal_id",
        "compare_signal_id",
    ):
        value = step.get(field)
        if value in (None, ""):
            continue
        if not isinstance(value, str) or not _ID_RE.match(value):
            raise ExhibitError(f"Exhibit '{eid}' step '{step_id}' has invalid {field}.")
    for field in ("related_signal_ids", "cosmic_signal_ids"):
        values = step.get(field)
        if values in (None, ""):
            continue
        if not isinstance(values, list):
            raise ExhibitError(f"Exhibit '{eid}' step '{step_id}' {field} must be a list.")
        for item in values:
            if not isinstance(item, str) or not _ID_RE.match(item):
                raise ExhibitError(f"Exhibit '{eid}' step '{step_id}' has invalid {field} entry.")
            if not _signal_entry(item):
                raise ExhibitError(
                    f"Exhibit '{eid}' step '{step_id}' {field} entry '{item}' does not resolve."
                )
    for story_id in _step_story_ids(step):
        _require_ready_story(story_id, exhibit_id=eid)
        if story_id not in set(exhibit.get("story_ids") or []):
            raise ExhibitError(
                f"Exhibit '{eid}' step '{step_id}' references story '{story_id}' not listed on the exhibit."
            )
    visual_id = step.get("archaeo_visual_id")
    if visual_id:
        visual = archaeoastronomy.get_entry(visual_id, production_only=True)
        if not visual:
            raise ExhibitError(f"Exhibit '{eid}' step '{step_id}' has no production archaeo visual '{visual_id}'.")
        if visual.get("promotion_status") != "READY":
            raise ExhibitError(f"Exhibit '{eid}' step '{step_id}' visual '{visual_id}' is not READY.")
    signal_id = step.get("cosmic_signal_id")
    if signal_id and not _signal_entry(signal_id):
        raise ExhibitError(f"Exhibit '{eid}' step '{step_id}' cosmic_signal_id does not resolve.")
    compare_id = step.get("compare_signal_id")
    if compare_id and not _signal_entry(compare_id):
        raise ExhibitError(f"Exhibit '{eid}' step '{step_id}' compare_signal_id does not resolve.")
    cd_obj = step.get("cosmic_dawn_object_id")
    if cd_obj not in (None, ""):
        if not isinstance(cd_obj, str) or not _ID_RE.match(cd_obj):
            raise ExhibitError(f"Exhibit '{eid}' step '{step_id}' has invalid cosmic_dawn_object_id.")
        if not cosmic_dawn.object_by_id(cd_obj):
            raise ExhibitError(
                f"Exhibit '{eid}' step '{step_id}' cosmic_dawn_object_id '{cd_obj}' does not resolve."
            )
    ge_obj = step.get("galactic_encounters_object_id")
    if ge_obj not in (None, ""):
        if not isinstance(ge_obj, str) or not _ID_RE.match(ge_obj):
            raise ExhibitError(f"Exhibit '{eid}' step '{step_id}' has invalid galactic_encounters_object_id.")
        if not galactic_encounters.object_by_id(ge_obj):
            raise ExhibitError(
                f"Exhibit '{eid}' step '{step_id}' galactic_encounters_object_id '{ge_obj}' does not resolve."
            )
    bh_obj = step.get("black_holes_object_id")
    if bh_obj not in (None, ""):
        if not isinstance(bh_obj, str) or not _ID_RE.match(bh_obj):
            raise ExhibitError(f"Exhibit '{eid}' step '{step_id}' has invalid black_holes_object_id.")
        if not black_holes.object_by_id(bh_obj):
            raise ExhibitError(
                f"Exhibit '{eid}' step '{step_id}' black_holes_object_id '{bh_obj}' does not resolve."
            )
    gw_obj = step.get("gravitational_waves_event_id")
    if gw_obj not in (None, ""):
        if not isinstance(gw_obj, str) or not _ID_RE.match(gw_obj):
            raise ExhibitError(f"Exhibit '{eid}' step '{step_id}' has invalid gravitational_waves_event_id.")
        if not gravitational_waves.object_by_id(gw_obj):
            raise ExhibitError(
                f"Exhibit '{eid}' step '{step_id}' gravitational_waves_event_id '{gw_obj}' does not resolve."
            )
    cw_obj = step.get("cosmic_web_object_id")
    if cw_obj not in (None, ""):
        if not isinstance(cw_obj, str) or not _ID_RE.match(cw_obj):
            raise ExhibitError(f"Exhibit '{eid}' step '{step_id}' has invalid cosmic_web_object_id.")
        if not cosmic_web.object_by_id(cw_obj):
            raise ExhibitError(
                f"Exhibit '{eid}' step '{step_id}' cosmic_web_object_id '{cw_obj}' does not resolve."
            )
    le_obj = step.get("light_echo_object_id")
    if le_obj not in (None, ""):
        if not isinstance(le_obj, str) or not _ID_RE.match(le_obj):
            raise ExhibitError(f"Exhibit '{eid}' step '{step_id}' has invalid light_echo_object_id.")
        if not light_echoes.object_by_id(le_obj):
            raise ExhibitError(
                f"Exhibit '{eid}' step '{step_id}' light_echo_object_id '{le_obj}' does not resolve."
            )
    related = step.get("related_signal_ids") or []
    if signal_id and signal_id in related:
        raise ExhibitError(f"Exhibit '{eid}' step '{step_id}' related_signal_ids repeats the primary signal.")
    if step_type == "historical_reconstruction":
        if step.get("user_action_required") is not True:
            raise ExhibitError(f"Exhibit '{eid}' step '{step_id}' must require an explicit historical action.")
        action = step.get("time_machine_action")
        if not isinstance(action, dict):
            raise ExhibitError(f"Exhibit '{eid}' step '{step_id}' missing time_machine_action.")
        if action.get("apply_requires_explicit_action") is not True or action.get("silent_apply"):
            raise ExhibitError(f"Exhibit '{eid}' step '{step_id}' must not allow silent time changes.")
        request = archaeoastronomy.historical_time_request(action.get("visual_id") or "", action.get("date_id") or "")
        if not request.get("ok"):
            raise ExhibitError(f"Exhibit '{eid}' step '{step_id}' historical date does not resolve.")
        if request.get("silent_apply"):
            raise ExhibitError(f"Exhibit '{eid}' step '{step_id}' historical request is marked silent.")


def _require_ready_story(story_id: str, *, exhibit_id: str) -> dict[str, Any]:
    story = constellation_story.get_story(story_id)
    if not story:
        raise ExhibitError(f"Exhibit '{exhibit_id}' references unsupported story '{story_id}'.")
    status = story.get("public_story_status") or "public"
    if status in RESTRICTED_STATUSES:
        raise ExhibitError(f"Restricted or deferred story '{story_id}' cannot appear in an exhibit.")
    culture = constellation_story._story_culture_id(story)
    if culture in BLOCKED_CULTURES_UNLESS_READY:
        raise ExhibitError(f"Story '{story_id}' uses a deferred culture and cannot appear in an exhibit.")
    if not story.get("enabled"):
        raise ExhibitError(f"Story '{story_id}' is not a READY production story.")
    return story


def _step_signal_ids(step: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for key in ("cosmic_signal_id", "compare_signal_id"):
        value = step.get(key)
        if isinstance(value, str) and value:
            ids.append(value)
    for key in ("related_signal_ids", "cosmic_signal_ids"):
        extra = step.get(key)
        if isinstance(extra, list):
            ids.extend(str(item) for item in extra if item)
    seen: set[str] = set()
    out: list[str] = []
    for item in ids:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _step_story_ids(step: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for key in ("story_id", "constellation_id", "cultural_story_id"):
        value = step.get(key)
        if isinstance(value, str) and value:
            ids.append(value)
    extra = step.get("story_ids")
    if isinstance(extra, list):
        ids.extend(str(item) for item in extra if item)
    seen: set[str] = set()
    out: list[str] = []
    for item in ids:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _signal_entry(signal_id: str) -> dict[str, Any] | None:
    for entry in cosmic_signal_registry.load_registry().get("entries") or []:
        if isinstance(entry, dict) and entry.get("id") == signal_id and entry.get("enabled"):
            return entry
    return None


def _validate_unique_primary_signals(exhibit: dict[str, Any]) -> None:
    eid = exhibit["id"]
    seen: dict[str, str] = {}
    for step in exhibit.get("steps") or []:
        signal_id = step.get("cosmic_signal_id")
        if not signal_id:
            continue
        if signal_id in seen:
            raise ExhibitError(
                f"Exhibit '{eid}' duplicates primary cosmic_signal_id '{signal_id}' "
                f"on steps '{seen[signal_id]}' and '{step.get('step_id')}'."
            )
        seen[signal_id] = str(step.get("step_id") or "")


def classify_signal(entry: dict[str, Any] | None, *, generated: bool = False) -> list[str]:
    if generated:
        return ["generated_cartography_sonification"]
    if not isinstance(entry, dict):
        return []
    media_type = entry.get("media_type")
    classes: list[str] = []
    if media_type == "instrument_signal":
        classes.extend(["measured_signal", "measurement_derived_audio"])
    elif media_type == "data_audification":
        classes.extend(["audification", "measurement_derived_audio"])
    elif media_type == "data_sonification":
        classes.append("data_sonification")
    blob = " ".join(
        str(entry.get(key) or "")
        for key in ("conversion_method", "mapping_explanation")
    ).lower()
    if any(hint in blob for hint in PULSE_TIMING_HINTS) and "pulse_timing_data" not in classes:
        classes.append("pulse_timing_data")
    return classes


def signal_class_badges(ids: list[str]) -> list[dict[str, Any]]:
    badges = []
    seen: set[str] = set()
    for key in ids:
        label = SIGNAL_CLASS_LABELS.get(key)
        if not label or key in seen:
            continue
        seen.add(key)
        badges.append({"id": key, "label": label})
    return badges


def _join_meta(values: Any) -> str:
    if isinstance(values, str) and values.strip():
        return values.strip()
    if not isinstance(values, list):
        return ""
    parts = [str(item).strip() for item in values if str(item).strip()]
    return "; ".join(parts)


def _mapping_documented(entry: dict[str, Any] | None) -> bool:
    if not isinstance(entry, dict):
        return False
    return bool(str(entry.get("mapping_explanation") or "").strip() or str(entry.get("conversion_method") or "").strip())


def _time_scaling_from_entry(entry: dict[str, Any] | None) -> str:
    if not isinstance(entry, dict):
        return MAPPING_UNAVAILABLE
    blob = " ".join(
        str(entry.get(key) or "")
        for key in ("conversion_method", "mapping_explanation")
    ).lower()
    if not blob.strip():
        return MAPPING_UNAVAILABLE
    if "already" in blob and "hearing" in blob:
        return "Frequencies already in the human hearing range; amplified rather than pitch-mapped."
    if any(
        token in blob
        for token in ("left-to-right", "left to right", "right-to-left", "right to left", "bottom-to-top", "bottom to top")
    ):
        return "Image-scan time, not the original astrophysical event duration."
    return MAPPING_UNAVAILABLE


def hearing_card(entry: dict[str, Any] | None, *, generated: bool = False) -> dict[str, Any]:
    if generated:
        return {
            "title": "What Am I Hearing?",
            "source_instrument_mission": "Stellar Cartography Data Sonification",
            "original_data_type": "Computed apparent altitude of the current Stellarium selection",
            "transformation_type": SIGNAL_CLASS_LABELS["generated_cartography_sonification"],
            "time_scaling": "Four-second sweep across the apparent-altitude window.",
            "frequency_mapping": "Normalized altitude maps to oscillator frequency 220–660 Hz.",
            "literal_vs_mapped": (
                "This is an audible mapping of numbers, not the physical sound of the object "
                "and not an original observatory recording."
            ),
            "provider": "Stellar Cartography (local, generated)",
            "mapping_documented": True,
            "classification_ids": ["generated_cartography_sonification"],
            "classification_labels": [SIGNAL_CLASS_LABELS["generated_cartography_sonification"]],
            "generated": True,
        }
    entry = entry if isinstance(entry, dict) else {}
    documented = _mapping_documented(entry)
    mapping = str(entry.get("mapping_explanation") or "").strip()
    classes = classify_signal(entry)
    labels = [SIGNAL_CLASS_LABELS[key] for key in classes if key in SIGNAL_CLASS_LABELS]
    mission = _join_meta(
        list(entry.get("spacecraft") or [])
        + list(entry.get("observatories") or [])
        + list(entry.get("instruments") or [])
        + list(entry.get("related_missions") or [])
    )
    data_type = _join_meta(entry.get("data_domains")) or str(entry.get("media_type") or "")
    return {
        "title": "What Am I Hearing?",
        "source_instrument_mission": mission or MAPPING_UNAVAILABLE,
        "original_data_type": data_type or MAPPING_UNAVAILABLE,
        "transformation_type": labels[0] if labels else str(entry.get("media_type") or MAPPING_UNAVAILABLE),
        "time_scaling": _time_scaling_from_entry(entry) if documented else MAPPING_UNAVAILABLE,
        "frequency_mapping": mapping if documented and mapping else MAPPING_UNAVAILABLE,
        "literal_vs_mapped": str(entry.get("what_it_does_not_prove") or MAPPING_UNAVAILABLE),
        "provider": str(entry.get("attribution") or entry.get("credits") or MAPPING_UNAVAILABLE),
        "mapping_documented": documented,
        "classification_ids": classes,
        "classification_labels": labels,
        "generated": False,
        "signal_id": entry.get("id"),
        "media_type": entry.get("media_type"),
    }


def present_signal(entry: dict[str, Any]) -> dict[str, Any]:
    presented = cosmic_signal_registry._present(entry, (entry.get("relevance_capabilities") or ["exact_target"])[0])
    classes = classify_signal(entry)
    presented["classification_ids"] = classes
    presented["classification_labels"] = [SIGNAL_CLASS_LABELS[key] for key in classes if key in SIGNAL_CLASS_LABELS]
    presented["hearing_card"] = hearing_card(entry)
    presented["hearing_label"] = "What Am I Hearing?"
    presented["provider"] = entry.get("attribution")
    presented["source_page_url"] = entry.get("source_page_url")
    return presented


def object_focus_map(exhibit: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for step in exhibit.get("steps") or []:
        focus = step.get("stellarium_focus")
        if not focus:
            continue
        rows.append(
            {
                "step_id": step.get("step_id"),
                "object_name": step.get("object_name"),
                "stellarium_focus": focus,
                "stellarium_fov": step.get("stellarium_fov"),
                "search_name_note": step.get("stellarium_search_note"),
            }
        )
    return rows


def cosmic_signal_inventory() -> list[dict[str, Any]]:
    """Internal exhibit inventory of enabled Cosmic Signal Deck entries."""
    exhibit = get_exhibit("hear_the_universe") or {}
    primary_ids: set[str] = set()
    related_ids: set[str] = set()
    free_ids: set[str] = set()
    for step in exhibit.get("steps") or []:
        if step.get("cosmic_signal_id"):
            primary_ids.add(step["cosmic_signal_id"])
        for item in step.get("related_signal_ids") or []:
            related_ids.add(item)
        for item in step.get("cosmic_signal_ids") or []:
            free_ids.add(item)
        if step.get("compare_signal_id"):
            related_ids.add(step["compare_signal_id"])
    rows = []
    for entry in cosmic_signal_registry.enabled_entries():
        sid = entry["id"]
        classes = classify_signal(entry)
        target_ids = list(entry.get("target_ids") or [])
        target = target_ids[0] if target_ids else None
        spectrum_ids = []
        for spec in spectrum_gallery_registry.enabled_entries():
            spec_targets = set(spec.get("target_ids") or [])
            if target and target in spec_targets:
                spectrum_ids.append(spec["id"])
        official = None
        try:
            name = STELLARIUM_FOCUS_BY_TARGET.get(target or "", target)
            fields = official_media.curated_narration_fields({"ok": True, "name": name}) if name else {}
            official = fields.get("official_media_title")
        except Exception:  # noqa: BLE001
            official = None
        if sid in primary_ids:
            suitability = "exhibit_primary"
        elif sid in related_ids:
            suitability = "exhibit_related"
        elif sid in free_ids:
            suitability = "exhibit_free_listen"
        else:
            suitability = "available_not_featured"
        rows.append(
            {
                "id": sid,
                "title": entry.get("title"),
                "target_object": target,
                "provider_mission": entry.get("attribution"),
                "signal_type": entry.get("media_type"),
                "direct_measurement_derived": entry.get("media_type") in {"instrument_signal", "data_audification"},
                "audification": entry.get("media_type") == "data_audification",
                "sonification": entry.get("media_type") == "data_sonification",
                "timing_pulsation_based": "pulse_timing_data" in classes,
                "media_provenance": entry.get("source_page_url"),
                "associated_spectrum_ids": spectrum_ids[:3],
                "associated_official_media": official,
                "stellarium_focus": STELLARIUM_FOCUS_BY_TARGET.get(target or "") if target else None,
                "stellarium_search_note": STELLARIUM_FOCUS_NOTES.get(target or ""),
                "classification_ids": classes,
                "suitability": suitability,
            }
        )
    return rows


def list_exhibits(*, include_fixtures: bool = False) -> dict[str, Any]:
    exhibits = []
    for exhibit in load_registry().get("exhibits") or []:
        if not include_fixtures and (not exhibit.get("enabled") or exhibit.get("test_fixture")):
            continue
        exhibits.append(_exhibit_summary(exhibit))
    return {
        "ok": True,
        "exhibits": exhibits,
        "future_exhibit_ids": list(FUTURE_EXHIBIT_IDS),
        "audio_autoplay": False,
    }


def get_exhibit(exhibit_id: str | None, *, include_fixtures: bool = True) -> dict[str, Any] | None:
    key = (exhibit_id or "").strip()
    if not key or not _ID_RE.match(key):
        return None
    for exhibit in load_registry().get("exhibits") or []:
        if exhibit.get("id") != key:
            continue
        if not include_fixtures and (not exhibit.get("enabled") or exhibit.get("test_fixture")):
            return None
        return exhibit
    return None


def exhibit_payload(exhibit_id: str | None, *, include_fixtures: bool = True) -> dict[str, Any]:
    exhibit = get_exhibit(exhibit_id, include_fixtures=include_fixtures)
    if not exhibit:
        return {"ok": False, "error": "Unknown exhibit.", "audio_autoplay": False}
    steps = [_step_summary(exhibit, step, index) for index, step in enumerate(exhibit["steps"])]
    return {
        "ok": True,
        "exhibit": {
            **_exhibit_summary(exhibit),
            "description": exhibit.get("description"),
            "source_note": exhibit.get("source_note"),
            "narrator_default": exhibit.get("narrator_default"),
            "story_ids": list(exhibit.get("story_ids") or []),
            "steps": steps,
            "sources": exhibit_sources(exhibit),
            "cover": cover_payload(exhibit),
            "object_focus_map": object_focus_map(exhibit),
            "tools_of_the_sky": list(exhibit.get("tools_of_the_sky") or []),
        },
        "audio_autoplay": False,
        "auto_advance_default": False,
    }


def step_payload(exhibit_id: str | None, index: int) -> dict[str, Any]:
    exhibit = get_exhibit(exhibit_id)
    if not exhibit:
        return {"ok": False, "error": "Unknown exhibit.", "audio_autoplay": False}
    steps = exhibit["steps"]
    if index < 0 or index >= len(steps):
        return {"ok": False, "error": "Exhibit step is out of range.", "audio_autoplay": False}
    return {"ok": True, **_player_view(exhibit, index), "audio_autoplay": False}


def _exhibit_summary(exhibit: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": exhibit["id"],
        "title": exhibit.get("title"),
        "subtitle": exhibit.get("subtitle"),
        "theme": exhibit.get("theme"),
        "estimated_minutes": exhibit.get("estimated_minutes"),
        "culture_scope": list(exhibit.get("culture_scope") or []),
        "evidence_types": list(exhibit.get("evidence_types") or []),
        "enabled": bool(exhibit.get("enabled")),
        "test_fixture": bool(exhibit.get("test_fixture")),
        "step_count": len(exhibit.get("steps") or []),
        "source_note": exhibit.get("source_note"),
        "cover": cover_payload(exhibit),
    }


def _step_summary(exhibit: dict[str, Any], step: dict[str, Any], index: int) -> dict[str, Any]:
    return {
        "index": index,
        "step_id": step["step_id"],
        "step_type": step["step_type"],
        "title": step.get("title"),
        "optional": bool(step.get("optional")),
        "user_action_required": bool(step.get("user_action_required")),
        "apply_requires_explicit_action": _historical_requires_explicit(step),
        "silent_time_change": False,
    }


def cover_payload(exhibit: dict[str, Any]) -> dict[str, Any]:
    media = exhibit.get("cover_media") if isinstance(exhibit.get("cover_media"), dict) else {}
    return {
        "kind": media.get("kind") or "native_svg",
        "id": media.get("id") or exhibit.get("id"),
        "svg": _cover_svg(exhibit),
        "third_party_art": False,
    }


def _cover_svg(exhibit: dict[str, Any]) -> str:
    title = exhibit.get("title") or "Exhibit"
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 220" role="img" '
        f'aria-label="{_escape(title)} cover">'
        '<defs><linearGradient id="scExhibitSky" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0%" stop-color="#14102a"/><stop offset="100%" stop-color="#2a1c18"/>'
        "</linearGradient></defs>"
        '<rect width="640" height="220" fill="url(#scExhibitSky)"/>'
        '<circle cx="72" cy="36" r="1.4" fill="#f2f0fb"/>'
        '<circle cx="140" cy="58" r="1.1" fill="#f2f0fb"/>'
        '<circle cx="210" cy="28" r="1.6" fill="#f2f0fb"/>'
        '<circle cx="268" cy="70" r="1.2" fill="#f2f0fb"/>'
        '<circle cx="330" cy="40" r="1.8" fill="#f8e7b0"/>'
        '<circle cx="360" cy="52" r="1.2" fill="#f8e7b0"/>'
        '<circle cx="390" cy="38" r="1.4" fill="#f8e7b0"/>'
        '<circle cx="470" cy="48" r="1.1" fill="#f2f0fb"/>'
        '<circle cx="540" cy="30" r="1.5" fill="#f2f0fb"/>'
        '<circle cx="600" cy="64" r="1.2" fill="#f2f0fb"/>'
        '<path d="M0 168 L90 148 L170 172 L250 132 L340 168 L430 140 L520 176 L640 150 L640 220 L0 220 Z" fill="#1b2430"/>'
        '<path d="M120 176 L150 120 L180 176 Z" fill="#243044"/>'
        '<rect x="430" y="150" width="70" height="28" fill="#2c3344"/>'
        '<text x="24" y="118" fill="#f2f0fb" font-size="28" font-family="Georgia, serif">'
        f"{_escape(title)}</text>"
        '<text x="24" y="146" fill="#c9c4e0" font-size="14" font-family="sans-serif">'
        "Cartography exhibit</text>"
        "</svg>"
    )


def exhibit_sources(exhibit: dict[str, Any]) -> list[dict[str, Any]]:
    grouped = []
    for index, step in enumerate(exhibit.get("steps") or []):
        rows = []
        for story_id in _step_story_ids(step):
            story = constellation_story.get_story(story_id)
            if not story:
                continue
            for src in story.get("source_urls") or []:
                if not isinstance(src, dict):
                    continue
                rows.append(
                    {
                        "institution": src.get("institution"),
                        "title": src.get("title"),
                        "evidence_type": story.get("evidence_type") or _story_evidence_key(story),
                        "supports": src.get("supports"),
                        "url": src.get("url"),
                    }
                )
        visual_id = step.get("archaeo_visual_id")
        if visual_id:
            visual = archaeoastronomy.visual_payload(visual_id)
            for src in visual.get("evidence_sources") or []:
                rows.append(
                    {
                        "institution": src.get("institution"),
                        "title": src.get("title"),
                        "evidence_type": src.get("evidence_type") or visual.get("confidence"),
                        "supports": src.get("interpretation_status") or "visual claim",
                        "url": src.get("url"),
                    }
                )
        for signal_id in _step_signal_ids(step):
            entry = _signal_entry(signal_id)
            if not entry:
                continue
            classes = classify_signal(entry, generated=False)
            generated = False
            rows.append(
                {
                    "institution": entry.get("attribution") or entry.get("credits"),
                    "title": entry.get("title"),
                    "evidence_type": SIGNAL_CLASS_LABELS.get(classes[0], entry.get("media_type")) if classes else entry.get("media_type"),
                    "supports": entry.get("what_it_does_not_prove") or entry.get("short_explanation"),
                    "url": entry.get("source_page_url"),
                    "signal_classification": [SIGNAL_CLASS_LABELS[key] for key in classes if key in SIGNAL_CLASS_LABELS],
                    "generated": generated,
                }
            )
        cd_id = step.get("cosmic_dawn_object_id")
        if cd_id:
            cd_obj = cosmic_dawn.object_by_id(cd_id)
            if cd_obj:
                for src in cd_obj.get("sources") or []:
                    rows.append(
                        {
                            "institution": src.get("organization"),
                            "title": src.get("title"),
                            "evidence_type": src.get("classification") or "scientific_media",
                            "supports": cd_obj.get("significance"),
                            "url": src.get("url"),
                        }
                    )
        ge_id = step.get("galactic_encounters_object_id")
        if ge_id:
            ge_obj = galactic_encounters.object_by_id(ge_id)
            if ge_obj:
                for src in ge_obj.get("sources") or []:
                    rows.append(
                        {
                            "institution": src.get("organization"),
                            "title": src.get("title"),
                            "evidence_type": src.get("classification") or "scientific_media",
                            "supports": ge_obj.get("significance"),
                            "url": src.get("url"),
                        }
                    )
        bh_id = step.get("black_holes_object_id")
        if bh_id:
            bh_obj = black_holes.object_by_id(bh_id)
            if bh_obj:
                for src in bh_obj.get("sources") or []:
                    rows.append(
                        {
                            "institution": src.get("organization"),
                            "title": src.get("title"),
                            "evidence_type": src.get("classification") or "scientific_media",
                            "supports": bh_obj.get("significance"),
                            "url": src.get("url"),
                        }
                    )
        gw_id = step.get("gravitational_waves_event_id")
        if gw_id:
            gw_ev = gravitational_waves.object_by_id(gw_id)
            if gw_ev:
                for src in gw_ev.get("sources") or []:
                    rows.append(
                        {
                            "institution": src.get("organization"),
                            "title": src.get("title"),
                            "evidence_type": src.get("classification") or "scientific_media",
                            "supports": gw_ev.get("summary"),
                            "url": src.get("url"),
                        }
                    )
        cw_id = step.get("cosmic_web_object_id")
        if cw_id:
            cw_obj = cosmic_web.object_by_id(cw_id)
            if cw_obj:
                for src in cw_obj.get("sources") or []:
                    rows.append(
                        {
                            "institution": src.get("organization"),
                            "title": src.get("title"),
                            "evidence_type": src.get("classification") or "scientific_media",
                            "supports": cw_obj.get("summary"),
                            "url": src.get("url"),
                        }
                    )
                media = cw_obj.get("media") or {}
                if media.get("source_page_url"):
                    rows.append(
                        {
                            "institution": media.get("organization"),
                            "title": media.get("title"),
                            "evidence_type": media.get("classification") or "scientific_media",
                            "supports": media.get("license_note") or media.get("credit"),
                            "url": media.get("source_page_url"),
                        }
                    )
        le_id = step.get("light_echo_object_id")
        if le_id:
            le_obj = light_echoes.object_by_id(le_id)
            if le_obj:
                for src in le_obj.get("sources") or []:
                    rows.append(
                        {
                            "institution": src.get("organization"),
                            "title": src.get("title"),
                            "evidence_type": "scientific_media",
                            "supports": le_obj.get("summary"),
                            "url": src.get("url"),
                        }
                    )
                media = le_obj.get("media") or {}
                if media.get("source_page_url"):
                    rows.append(
                        {
                            "institution": media.get("organization"),
                            "title": media.get("title"),
                            "evidence_type": "scientific_media",
                            "supports": media.get("license_note") or media.get("credit"),
                            "url": media.get("source_page_url"),
                        }
                    )
        if step.get("cartography_sonify"):
            rows.append(
                {
                    "institution": "Stellar Cartography",
                    "title": "Generated Cartography Data Sonification",
                    "evidence_type": SIGNAL_CLASS_LABELS["generated_cartography_sonification"],
                    "supports": "Local altitude-to-pitch mapping. Not an original physical audio recording.",
                    "url": None,
                    "signal_classification": [SIGNAL_CLASS_LABELS["generated_cartography_sonification"]],
                    "generated": True,
                }
            )
        grouped.append(
            {
                "step_index": index,
                "step_id": step.get("step_id"),
                "title": step.get("title"),
                "sources": rows,
            }
        )
    return grouped


def capture_state(stellarium_client: Any | None, selection: dict[str, Any] | None = None) -> dict[str, Any]:
    sky: dict[str, Any] = {}
    controls: dict[str, Any] = {}
    if stellarium_client is not None:
        status = stellarium_client.get_main_status() if hasattr(stellarium_client, "get_main_status") else None
        sky = experience.extract_sky_status(status)
        if hasattr(stellarium_client, "get_constellation_properties"):
            controls = constellation_story.constellation_controls_payload(
                stellarium_client.get_constellation_properties()
            ).get("controls") or {}
        if selection is None and hasattr(stellarium_client, "get_selection"):
            result = stellarium_client.get_selection()
            selection = {
                "ok": getattr(result, "ok", False),
                "name": getattr(result, "name", None),
                "fov_deg": getattr(result, "fov_deg", None),
            }
    selection = selection if isinstance(selection, dict) else {}
    remembered = constellation_story._remember_selection(selection)
    return {
        "selected_object": selection.get("name"),
        "restore_search_name": remembered.get("restore_search_name"),
        "fov_deg": selection.get("fov_deg") if selection.get("fov_deg") is not None else sky.get("fov_deg"),
        "utc": sky.get("utc"),
        "jday": sky.get("jday"),
        "is_time_now": sky.get("is_time_now"),
        "latitude": sky.get("latitude"),
        "longitude": sky.get("longitude"),
        "altitude": sky.get("altitude"),
        "location_name": sky.get("location_name"),
        "constellation_controls": {
            key: bool(item.get("value"))
            for key, item in controls.items()
            if isinstance(item, dict) and isinstance(item.get("value"), bool)
        },
    }


def restore_state_payload(captured: dict[str, Any] | None) -> dict[str, Any]:
    captured = captured if isinstance(captured, dict) else {}
    return {
        "ok": True,
        "restore": True,
        "selected_object": captured.get("selected_object"),
        "restore_search_name": captured.get("restore_search_name"),
        "fov_deg": captured.get("fov_deg"),
        "utc": captured.get("utc"),
        "jday": captured.get("jday"),
        "is_time_now": captured.get("is_time_now"),
        "latitude": captured.get("latitude"),
        "longitude": captured.get("longitude"),
        "altitude": captured.get("altitude"),
        "location_name": captured.get("location_name"),
        "constellation_controls": captured.get("constellation_controls") or {},
        "applies_time_silently": False,
        "note": "Original Stellarium selection, FoV, constellation toggles, time, and location are restored where captured.",
    }


def reset_session() -> None:
    global _session
    with _session_lock:
        _session = None


def get_session() -> dict[str, Any] | None:
    with _session_lock:
        return dict(_session) if _session else None


def start_exhibit(
    exhibit_id: str | None,
    stellarium_client: Any | None = None,
    original_selection: dict[str, Any] | None = None,
) -> dict[str, Any]:
    global _session
    if exhibit_id is not None and not _ID_RE.match(str(exhibit_id)):
        return {"ok": False, "error": "Malformed exhibit id.", "audio_autoplay": False}
    exhibit = get_exhibit(exhibit_id)
    if not exhibit:
        return {"ok": False, "error": "Unknown exhibit.", "audio_autoplay": False}
    captured = capture_state(stellarium_client, original_selection)
    session = {
        "active": True,
        "exhibit_id": exhibit["id"],
        "step_index": 0,
        "total_steps": len(exhibit["steps"]),
        "captured_state": captured,
        "historical_applied": False,
        "audio_autoplay": False,
    }
    with _session_lock:
        _session = session
    view = _player_view(exhibit, 0, session=session)
    if stellarium_client is not None:
        view = apply_step_to_stellarium(stellarium_client, view)
    view["ok"] = True
    view["started"] = True
    view["captured_state"] = captured
    view["restore_payload"] = restore_state_payload(captured)
    view["audio_autoplay"] = False
    return view


def step_exhibit(direction: str, stellarium_client: Any | None = None, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    global _session
    body = payload if isinstance(payload, dict) else {}
    action = str(body.get("action") or "").strip()
    with _session_lock:
        session = _session
        if not session or not session.get("active"):
            return {"ok": False, "error": "No exhibit is active.", "audio_autoplay": False}
        exhibit = get_exhibit(session["exhibit_id"])
        if not exhibit:
            return {"ok": False, "error": "Active exhibit is no longer available.", "audio_autoplay": False}
        if action == "apply_historical":
            result = _apply_historical(exhibit, session, stellarium_client)
            result.update(_player_view(exhibit, session["step_index"], session=session))
            result["ok"] = bool(result.get("ok", True))
            result["audio_autoplay"] = False
            return result
        delta = -1 if str(direction).lower() in {"prev", "previous", "back"} else 1
        nxt = session["step_index"] + delta
        if nxt < 0 or nxt >= len(exhibit["steps"]):
            view = _player_view(exhibit, session["step_index"], session=session)
            view["ok"] = True
            view["bounded"] = True
            view["audio_autoplay"] = False
            return view
        session["step_index"] = nxt
        _session = session
    view = _player_view(exhibit, session["step_index"], session=session)
    if stellarium_client is not None:
        view = apply_step_to_stellarium(stellarium_client, view)
    view["ok"] = True
    view["audio_autoplay"] = False
    return view


def stop_exhibit(stellarium_client: Any | None = None, *, restore: bool = True) -> dict[str, Any]:
    global _session
    with _session_lock:
        session = _session
        _session = None
    if not session:
        return {"ok": True, "active": False, "restored": False, "audio_autoplay": False}
    out = {
        "ok": True,
        "active": False,
        "exhibit_id": session.get("exhibit_id"),
        "restored": False,
        "restore_payload": restore_state_payload(session.get("captured_state")),
        "audio_autoplay": False,
    }
    if restore and stellarium_client is not None:
        out.update(restore_original_state(stellarium_client, session.get("captured_state") or {}))
    return out


def exhibit_status() -> dict[str, Any]:
    session = get_session()
    if not session:
        return {"ok": True, "active": False, "audio_autoplay": False}
    exhibit = get_exhibit(session["exhibit_id"])
    if not exhibit:
        return {"ok": True, "active": False, "audio_autoplay": False}
    return {"ok": True, **_player_view(exhibit, session["step_index"], session=session)}


def apply_step_to_stellarium(client: Any, view: dict[str, Any]) -> dict[str, Any]:
    """Focus / FoV / constellation toggles only. Never changes time."""
    out = dict(view)
    step = out.get("step") or {}
    focused = False
    search = step.get("stellarium_focus") or step.get("object_name")
    if search and hasattr(client, "focus_object"):
        focused = bool(client.focus_object(search))
    fov = step.get("stellarium_fov")
    if focused and isinstance(fov, (int, float)) and hasattr(client, "set_fov"):
        client.set_fov(float(fov))
    applied_controls = []
    controls = step.get("visual_controls") if isinstance(step.get("visual_controls"), dict) else {}
    parsed = constellation_story.parse_control_request(controls)
    if parsed.get("ok") and hasattr(client, "set_stel_property"):
        for update in parsed.get("updates") or []:
            ok = client.set_stel_property(update["property"], update["value"])
            applied_controls.append({"id": update["id"], "ok": ok, "value": update["value"]})
    out["focused"] = focused
    out["applied_controls"] = applied_controls
    out["applies_time"] = False
    out["applies_time_silently"] = False
    out["audio_autoplay"] = False
    return out


def restore_original_state(client: Any, captured: dict[str, Any]) -> dict[str, Any]:
    captured = captured if isinstance(captured, dict) else {}
    restored = {
        "selection": False,
        "fov": False,
        "time": False,
        "location": False,
        "controls": [],
    }
    if captured.get("is_time_now") and hasattr(client, "return_to_now"):
        restored["time"] = bool(client.return_to_now())
    elif captured.get("jday") is not None and hasattr(client, "apply_time"):
        restored["time"] = bool(client.apply_time(float(captured["jday"]), 0.0))
    if (
        captured.get("latitude") is not None
        and captured.get("longitude") is not None
        and hasattr(client, "apply_location")
    ):
        restored["location"] = bool(
            client.apply_location(
                float(captured["latitude"]),
                float(captured["longitude"]),
                float(captured.get("altitude") or 0),
                str(captured.get("location_name") or "Cartography location"),
                "Earth",
            )
        )
    search = captured.get("restore_search_name") or captured.get("selected_object")
    if search and hasattr(client, "focus_object"):
        restored["selection"] = bool(client.focus_object(search))
    if captured.get("fov_deg") is not None and hasattr(client, "set_fov"):
        restored["fov"] = bool(client.set_fov(float(captured["fov_deg"])))
    controls = captured.get("constellation_controls") if isinstance(captured.get("constellation_controls"), dict) else {}
    parsed = constellation_story.parse_control_request(controls)
    if parsed.get("ok") and hasattr(client, "set_stel_property"):
        for update in parsed.get("updates") or []:
            ok = client.set_stel_property(update["property"], update["value"])
            restored["controls"].append({"id": update["id"], "ok": ok, "value": update["value"]})
    return {
        "restored": any(
            [
                restored["selection"],
                restored["fov"],
                restored["time"],
                restored["location"],
                any(item.get("ok") for item in restored["controls"]),
            ]
        ),
        "restore_details": restored,
        "restore_payload": restore_state_payload(captured),
        "audio_autoplay": False,
    }


def historical_confirmation(step: dict[str, Any]) -> dict[str, Any] | None:
    if step.get("step_type") != "historical_reconstruction":
        return None
    action = step.get("time_machine_action") if isinstance(step.get("time_machine_action"), dict) else {}
    request = archaeoastronomy.historical_time_request(action.get("visual_id") or "", action.get("date_id") or "")
    if not request.get("ok"):
        return None
    year = None
    utc = request.get("utc") or ""
    if isinstance(utc, str) and len(utc) >= 4 and utc[:4].isdigit():
        year = utc[:4]
    return {
        "required": True,
        "apply_requires_explicit_action": True,
        "silent_apply": False,
        "prompt": f"View reconstructed sky for approximately AD {year or 'XXXX'}?",
        "explanation": (
            "This uses modern astronomical simulation. It is not direct archaeological evidence. "
            "This uses modern astronomical models to reconstruct the sky. "
            "It does not independently prove the archaeological or historical interpretation."
        ),
        "apply_label": "Apply Historical Sky",
        "reconstruction_label": "astronomical reconstruction",
        "restore_behavior": step.get("restore_behavior") or "defer_until_exit",
        "restore_note": "The original Stellarium time is restored when you exit the exhibit.",
        "time_machine_request": {
            "apply_time": True,
            "apply_location": False,
            "reconstruction": True,
            "utc": request.get("utc"),
            "preset": None,
        },
        "label": request.get("label"),
        "utc": request.get("utc"),
        "kind": "astronomical_reconstruction",
    }


def narration_for_step(exhibit: dict[str, Any], step: dict[str, Any], *, step_index: int) -> dict[str, Any]:
    text = _narration_text(exhibit, step)
    return {
        "ok": True,
        "listen_available": True,
        "feature_flag": "narration_hook",
        "kind": "exhibit_step",
        "title": step.get("title") or exhibit.get("title"),
        "text": text,
        "summary": text,
        "source_object": step.get("object_name"),
        "exhibit_id": exhibit.get("id"),
        "step_index": step_index,
        "total_steps": len(exhibit.get("steps") or []),
        "label": "Cartography Narration",
        "audio_autoplay": False,
        "interface": {
            "intent": "Cartography-authored text is sent to a local TTS renderer. The TTS service does not invent astronomy content.",
            "wired": ["father_fox", "kayock_voice"],
            "payload": {"text": text, "source": "stellar-cartography-exhibit-step"},
        },
    }


def narration_payload(exhibit_id: str | None, step_index: int | None = None) -> dict[str, Any]:
    exhibit = get_exhibit(exhibit_id)
    if not exhibit:
        session = get_session()
        if session:
            exhibit = get_exhibit(session.get("exhibit_id"))
            if step_index is None:
                step_index = session.get("step_index", 0)
    if not exhibit:
        return {"ok": False, "error": "Unknown exhibit.", "kind": "exhibit_step", "audio_autoplay": False}
    if step_index is None:
        step_index = 0
    steps = exhibit["steps"]
    if step_index < 0 or step_index >= len(steps):
        return {"ok": False, "error": "Exhibit step is out of range.", "kind": "exhibit_step", "audio_autoplay": False}
    return narration_for_step(exhibit, steps[step_index], step_index=step_index)


def _player_view(exhibit: dict[str, Any], index: int, session: dict[str, Any] | None = None) -> dict[str, Any]:
    step = exhibit["steps"][index]
    stories = [constellation_story.story_payload(sid) for sid in _step_story_ids(step)]
    stories = [item for item in stories if item.get("ok")]
    visual = archaeoastronomy.visual_payload(step["archaeo_visual_id"]) if step.get("archaeo_visual_id") else None
    comparison = _same_sky_items(step)
    media = _media_refs(step, stories)
    confirmation = historical_confirmation(step)
    evidence = evidence_badges(step, stories, visual)
    narration = narration_for_step(exhibit, step, step_index=index)
    return {
        "active": True,
        "exhibit_id": exhibit["id"],
        "title": exhibit.get("title"),
        "step_index": index,
        "total_steps": len(exhibit["steps"]),
        "progress_label": f"Step {index + 1} of {len(exhibit['steps'])}",
        "has_previous": index > 0,
        "has_next": index < len(exhibit["steps"]) - 1,
        "auto_advance_default": False,
        "auto_advance_safe": step["step_type"] in SAFE_AUTO_ADVANCE_TYPES,
        "step": {
            **step,
            "index": index,
            "evidence_badges": evidence,
            "stories": [
                {
                    "id": item.get("id"),
                    "canonical_name": item.get("canonical_name"),
                    "native_name": item.get("native_name"),
                    "culture_name": item.get("culture_name"),
                    "evidence_type": item.get("evidence_type"),
                    "living_tradition": item.get("living_tradition"),
                }
                for item in stories
            ],
            "visual": visual if visual and visual.get("ok") else None,
            "comparison": comparison,
            "media": media,
            "historical_confirmation": confirmation,
            "hearing_card": media.get("hearing_card"),
            "hearing_cards": media.get("hearing_cards") or [],
            "sound_explainer": step.get("sound_explainer"),
            "how_they_knew": how_they_knew_card(step),
            "place_context": place_context_card(step, stories, visual),
            "method_comparison": list(step.get("method_comparison") or []),
            "tools_of_the_sky": list(exhibit.get("tools_of_the_sky") or []) if step.get("show_tools_of_the_sky") else [],
            "scientific_view": bool(step.get("scientific_view")),
            "current_story": (stories[0].get("canonical_name") if stories else step.get("object_name")),
            "current_object": step.get("object_name") or step.get("stellarium_focus"),
            "current_site": ((visual or {}).get("site_context") or {}).get("site") if visual else None,
            "evidence_label": evidence[0]["label"] if evidence else None,
        },
        "narration": narration,
        "sources": exhibit_sources(exhibit),
        "historical_applied": bool((session or {}).get("historical_applied")),
        "audio_autoplay": False,
        "media_autoplay": False,
        "applies_time_silently": False,
    }


def evidence_badges(
    step: dict[str, Any],
    stories: list[dict[str, Any]],
    visual: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    badges: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(key: str) -> None:
        label = EVIDENCE_BADGES.get(key)
        if not label or key in seen:
            return
        seen.add(key)
        badges.append({"id": key, "label": label})

    if step.get("step_type") == "cosmic_dawn":
        add("illustrative_geometry")
        if step.get("cosmic_dawn_object_id") or step.get("scientific_view"):
            add("scientific_media")
    if step.get("step_type") == "galactic_encounters":
        add("illustrative_geometry")
        if step.get("galactic_encounters_object_id") or step.get("scientific_view"):
            add("scientific_media")
    if step.get("step_type") == "black_holes":
        add("illustrative_geometry")
        if step.get("black_holes_object_id") or step.get("scientific_view"):
            add("scientific_media")
    if step.get("step_type") == "gravitational_waves":
        add("illustrative_geometry")
        if step.get("gravitational_waves_event_id") or step.get("scientific_view"):
            add("scientific_media")
    if step.get("step_type") == "cosmic_web":
        add("illustrative_geometry")
        if step.get("cosmic_web_object_id") or step.get("scientific_view"):
            add("scientific_media")
    if step.get("step_type") == "light_echo":
        add("illustrative_geometry")
        if step.get("light_echo_object_id") or step.get("scientific_view"):
            add("scientific_media")

    step_type = step.get("step_type")
    if step_type in {"constellation_story", "object_focus"} and not any(
        item.get("evidence_type") for item in stories
    ):
        return []
    if step_type in {"intro", "outro"}:
        return []
    if visual and visual.get("ok"):
        add(visual.get("confidence") or "")
        site = visual.get("site_context") or {}
        if site.get("evidence_type") in EVIDENCE_BADGES:
            add(site["evidence_type"])
    if step_type == "historical_reconstruction":
        add("scholarly_interpretation")
    for story in stories:
        key = story.get("evidence_type") or _story_evidence_key(story)
        trad = _tradition_badge_key(story)
        if key == "scholarly_ethnographic":
            add("historical_source")
        elif key in EVIDENCE_BADGES and key != "cultural_source":
            add(key)
        if trad:
            add(trad)
        elif key == "archaeological_inference" or "historical_source" in seen:
            pass
        elif key == "cultural_source" or story.get("story_kind") == "cultural_sky_story" or story.get("culture_id") not in (None, "modern"):
            add("cultural_source")
        if story.get("culture_id") == "maori":
            add("community_sourced")
    for key in _step_classification_ids(step):
        label = SIGNAL_CLASS_LABELS.get(key)
        if not label or key in seen:
            continue
        seen.add(key)
        badges.append({"id": key, "label": label})
    return badges


def _step_classification_ids(step: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    if step.get("cartography_sonify"):
        ids.append("generated_cartography_sonification")
    primary = step.get("cosmic_signal_id") or step.get("compare_signal_id")
    if primary:
        ids.extend(classify_signal(_signal_entry(primary)))
    seen: set[str] = set()
    out: list[str] = []
    for key in ids:
        if key not in seen:
            seen.add(key)
            out.append(key)
    return out


def _tradition_badge_key(story: dict[str, Any]) -> str:
    culture = constellation_story._story_culture_id(story) if hasattr(constellation_story, "_story_culture_id") else story.get("culture_id")
    if culture == "arabic_sufi":
        return "historical_astronomy"
    if culture in {"maori", "arabic_peninsula", "chinese"}:
        return "cultural_sky_knowledge"
    return ""


def how_they_knew_card(step: dict[str, Any]) -> dict[str, Any] | None:
    card = step.get("how_they_knew")
    if not isinstance(card, dict) or not card:
        return None
    fields = []
    mapping = (
        ("observation_method", "Observation method"),
        ("repeated_pattern", "Repeated pattern"),
        ("astronomical_object", "Astronomical object"),
        ("environmental_calendar_role", "Environmental / calendar role"),
        ("architectural_relationship", "Architectural relationship"),
        ("evidence_type", "Evidence type"),
        ("uncertainty", "Uncertainty"),
    )
    for key, label in mapping:
        value = card.get(key)
        if isinstance(value, str) and value.strip():
            fields.append({"id": key, "label": label, "text": value.strip()})
    if not fields:
        return None
    return {
        "title": card.get("title") or "How Did They Know?",
        "fields": fields,
    }


def place_context_card(
    step: dict[str, Any],
    stories: list[dict[str, Any]],
    visual: dict[str, Any] | None,
) -> dict[str, Any] | None:
    authored = step.get("place_context") if isinstance(step.get("place_context"), dict) else {}
    site = (visual or {}).get("site_context") if isinstance((visual or {}).get("site_context"), dict) else {}
    story = stories[0] if stories else {}
    period = authored.get("period") or site.get("date_range")
    region = authored.get("region") or site.get("region")
    tradition = authored.get("tradition") or site.get("culture_label") or story.get("culture_name") or story.get("tradition_name")
    environment = authored.get("observing_environment")
    payload = {
        "period": period,
        "region": region,
        "tradition": tradition,
        "observing_environment": environment,
    }
    if not any(payload.values()):
        return None
    return payload


def ancient_skywatchers_inventory() -> list[dict[str, Any]]:
    """Internal matrix of production-ready material for Ancient Skywatchers."""
    exhibit = get_exhibit("ancient_skywatchers") or {}
    used: set[str] = set(exhibit.get("story_ids") or [])
    rows = []
    for story_id in used:
        story = constellation_story.get_story(story_id)
        if not story:
            continue
        visual = None
        if archaeoastronomy.get_entry(story_id, production_only=True):
            visual = archaeoastronomy.visual_payload(story_id)
        site = (visual or {}).get("site_context") or {}
        objects = []
        for group in ("major_objects", "notable_deep_sky_objects"):
            for obj in story.get(group) or []:
                if isinstance(obj, dict) and obj.get("search_name"):
                    objects.append(obj.get("search_name"))
        rows.append(
            {
                "story_visual": story_id,
                "culture_tradition": story.get("culture_name") or story.get("tradition_name"),
                "evidence_type": story.get("evidence_type") or _story_evidence_key(story) or _tradition_badge_key(story),
                "historical_period": site.get("date_range"),
                "astronomical_target": objects[0] if objects else None,
                "observational_method": ((visual or {}).get("visual_mode")),
                "purpose": story.get("story_summary"),
                "confidence": (visual or {}).get("confidence") or story.get("evidence_type"),
                "stellarium_target": objects[0] if objects else None,
                "media_available": bool(story.get("source_urls")),
                "exhibit_suitability": "exhibit_primary",
            }
        )
    return rows


def _story_evidence_key(story: dict[str, Any]) -> str:
    if story.get("evidence_type"):
        return str(story["evidence_type"])
    if story.get("source_quality") == "stellarium_skyculture":
        return "cultural_source"
    if story.get("story_kind") == "iau_constellation" or not story.get("culture_id") or story.get("culture_id") == "modern":
        return ""
    return "cultural_source"


def _same_sky_items(step: dict[str, Any]) -> list[dict[str, Any]]:
    items = []
    for story_id in _step_story_ids(step):
        story = constellation_story.get_story(story_id)
        if not story:
            continue
        items.append(
            {
                "id": story["id"],
                "culture_name": story.get("culture_name") or story.get("culture_id") or "Modern IAU",
                "native_name": story.get("native_name") or story.get("canonical_name"),
                "translated_name": story.get("translated_name"),
                "canonical_name": story.get("canonical_name"),
                "living_tradition": story.get("living_tradition"),
                "evidence_type": story.get("evidence_type") or _story_evidence_key(story),
            }
        )
    return items


def _media_refs(step: dict[str, Any], stories: list[dict[str, Any]]) -> dict[str, Any]:
    refs: dict[str, Any] = {
        "cosmic_signal_id": step.get("cosmic_signal_id"),
        "compare_signal_id": step.get("compare_signal_id"),
        "official_media": step.get("media_preference") == "official_media",
        "spectrum": step.get("step_type") == "spectrum" or step.get("media_preference") == "spectrum",
        "archaeo_visual_id": step.get("archaeo_visual_id"),
        "cartography_sonify": bool(step.get("cartography_sonify")),
        "manual_only": True,
        "autoplay": False,
        "duplicate_player": False,
        "signals": {"ranked": [], "empty": True, "registry": "cosmic_signal_registry"},
        "related_signals": [],
        "free_listen": [],
        "spectra": {"ranked": [], "empty": True, "registry": "spectrum_gallery_registry"},
        "official_media_note": None,
        "hearing_card": None,
        "hearing_cards": [],
        "generated_hearing_card": None,
        "scientific_view": bool(step.get("scientific_view")),
        "suppress_cosmic_signal": bool(step.get("suppress_cosmic_signal")),
    }
    primary = _signal_entry(step.get("cosmic_signal_id") or "") if step.get("cosmic_signal_id") else None
    if primary:
        presented = present_signal(primary)
        refs["signals"] = {
            "ranked": [presented],
            "empty": False,
            "registry": "cosmic_signal_registry",
            "canonical_id": presented["id"],
        }
        refs["hearing_card"] = presented["hearing_card"]
        refs["hearing_cards"].append(presented["hearing_card"])
    related = []
    for signal_id in step.get("related_signal_ids") or []:
        entry = _signal_entry(signal_id)
        if not entry:
            continue
        related.append(present_signal(entry))
    refs["related_signals"] = related
    free = []
    for signal_id in step.get("cosmic_signal_ids") or []:
        entry = _signal_entry(signal_id)
        if not entry:
            continue
        free.append(present_signal(entry))
    refs["free_listen"] = free
    if free and not primary:
        refs["signals"] = {
            "ranked": [],
            "empty": True,
            "registry": "cosmic_signal_registry",
        }
    compare = _signal_entry(step.get("compare_signal_id") or "") if step.get("compare_signal_id") else None
    if compare:
        presented = present_signal(compare)
        if not primary:
            refs["signals"] = {
                "ranked": [presented],
                "empty": False,
                "registry": "cosmic_signal_registry",
                "canonical_id": presented["id"],
                "compare_only": True,
            }
            refs["hearing_card"] = presented["hearing_card"]
        refs["hearing_cards"].append(presented["hearing_card"])
        refs["compare_signal"] = presented
    if step.get("cartography_sonify"):
        generated = hearing_card(None, generated=True)
        refs["generated_hearing_card"] = generated
        refs["hearing_cards"].append(generated)
        if refs["hearing_card"] is None:
            refs["hearing_card"] = generated
    object_name = step.get("object_name")
    if object_name:
        spec_match = spectrum_gallery_registry.match_spectrum_for_target(
            {"name": object_name},
            allow_all_sky=False,
        )
        primary_spec = spec_match.get("primary")
        if primary_spec:
            refs["spectra"] = {
                "ranked": [primary_spec],
                "empty": False,
                "registry": "spectrum_gallery_registry",
            }
        try:
            fields = official_media.curated_narration_fields({"ok": True, "name": object_name})
            if fields.get("official_media_title"):
                refs["official_media_note"] = fields.get("official_media_note")
                refs["official_media_title"] = fields.get("official_media_title")
                refs["official_media_provider"] = fields.get("official_media_provider")
        except Exception:  # noqa: BLE001 - media decoration must not fail the step
            pass
    for story in stories:
        raw = constellation_story.get_story(story.get("id"))
        if not raw:
            continue
        if not primary and not free and not step.get("suppress_cosmic_signal"):
            signals = constellation_story.match_signals_for_constellation(raw)
            if signals.get("ranked"):
                refs["signals"] = signals
        if refs["spectra"].get("empty"):
            spectra = constellation_story.match_spectra_for_constellation(raw)
            ranked = (spectra.get("ranked") or [])[:1]
            if ranked:
                refs["spectra"] = {
                    "ranked": ranked,
                    "empty": False,
                    "registry": "spectrum_gallery_registry",
                }
        if not refs.get("official_media_title"):
            try:
                fields = official_media.curated_narration_fields(
                    {"ok": True, "name": step.get("object_name") or raw.get("canonical_name")}
                )
                if fields.get("official_media_title"):
                    refs["official_media_note"] = fields.get("official_media_note")
                    refs["official_media_title"] = fields.get("official_media_title")
            except Exception:  # noqa: BLE001
                pass
    return refs


def _narration_text(exhibit: dict[str, Any], step: dict[str, Any]) -> str:
    authored = (step.get("narration_text") or "").strip()
    parts: list[str] = []
    if authored:
        parts.append(authored)
    stories = [constellation_story.get_story(sid) for sid in _step_story_ids(step)]
    stories = [story for story in stories if story]
    step_type = step.get("step_type")
    if step_type == "same_sky_comparison" and stories and not authored:
        names = []
        for story in stories:
            label = story.get("translated_name") or story.get("canonical_name") or story.get("native_name")
            culture = story.get("culture_name") or story.get("culture_id") or "Modern IAU"
            names.append(f"{culture}: {label}")
        parts.append("The same physical sky is shown through " + "; ".join(names) + ".")
        parts.append("These traditions remain distinct and are not merged.")
        for story in stories:
            if story.get("narration_lead"):
                parts.append(str(story["narration_lead"]).strip())
            elif story.get("cultural_note"):
                parts.append(str(story["cultural_note"]).strip())
            if story.get("id") == "mexica_tianquiztli":
                parts.append("In the Mexica historical sources represented here, this is historical Mexica language, not a modern Nahua or Maya classroom story.")
    elif step_type in {"archaeoastronomy", "historical_reconstruction"}:
        if not authored:
            visual_id = step.get("archaeo_visual_id")
            if visual_id:
                visual = archaeoastronomy.visual_payload(visual_id)
                parts.append(archaeoastronomy.narration_text(visual))
            for story in stories:
                if story.get("narration_lead"):
                    parts.append(str(story["narration_lead"]).strip())
                if story.get("cultural_note"):
                    parts.append(str(story["cultural_note"]).strip())
        if step_type == "historical_reconstruction":
            parts.append("This uses modern astronomical simulation. It is not direct archaeological evidence.")
            parts.append("It does not independently prove the archaeological or historical interpretation.")
            parts.append("Apply Historical Sky only if you want Stellarium to show the reconstructed date.")
    elif stories and not authored:
        story = stories[0]
        if story.get("narration_lead"):
            parts.append(str(story["narration_lead"]).strip())
        elif story.get("evidence_type") == "archaeological_inference":
            parts.append("Archaeological evidence suggests " + (story.get("story_summary") or story.get("canonical_name") or "this site") + ".")
        elif story.get("culture_id") == "mexica":
            parts.append(
                "In the Mexica historical sources represented here, "
                + (story.get("native_name") or story.get("canonical_name") or "this sky grouping")
                + " is a historical record, not a modern Nahua or Maya story."
            )
        elif story.get("story_kind") == "cultural_sky_story":
            parts.append(str(story.get("cultural_note") or story.get("story_summary") or story.get("mythology_summary") or "").strip())
        else:
            parts.append(f"{story.get('canonical_name')} is a modern IAU constellation.")
        if story.get("mythology_summary") and story.get("mythology_summary") not in parts:
            parts.append(str(story["mythology_summary"]).strip())
        if step.get("media_preference") == "official_media":
            parts.append("This cultural story is separate from the scientific media shown alongside it. Official media remains manual.")
    text = constellation_story._join_sentences([part for part in parts if part])
    return constellation_story._clip_spoken(constellation_story._strip_urls(text), 900)


def _historical_requires_explicit(step: dict[str, Any]) -> bool:
    if step.get("step_type") != "historical_reconstruction":
        return False
    action = step.get("time_machine_action") if isinstance(step.get("time_machine_action"), dict) else {}
    return action.get("apply_requires_explicit_action") is True and action.get("silent_apply") is not True


def _apply_historical(exhibit: dict[str, Any], session: dict[str, Any], stellarium_client: Any | None) -> dict[str, Any]:
    step = exhibit["steps"][session["step_index"]]
    confirmation = historical_confirmation(step)
    if not confirmation:
        return {"ok": False, "error": "This step has no historical reconstruction."}
    request = confirmation["time_machine_request"]
    validated = experience.validate_time_machine_request(request)
    if not validated.get("ok"):
        return {"ok": False, "error": validated.get("error") or "Historical request is invalid."}
    if stellarium_client is None:
        return {"ok": False, "error": "Stellarium client is required to apply a historical sky."}
    if not stellarium_client.check_connection():
        return {"ok": False, "error": "Stellarium Remote Control is not reachable."}
    ok = stellarium_client.apply_time(validated["jday"], validated["timerate"])
    if not ok:
        return {"ok": False, "error": "Stellarium rejected the time update."}
    session["historical_applied"] = True
    return {
        "ok": True,
        "historical_applied": True,
        "reconstruction_label": "astronomical reconstruction",
        "applied_utc": validated.get("utc"),
        "restore_behavior": step.get("restore_behavior") or "defer_until_exit",
        "applies_time_silently": False,
    }


def _escape(value: Any) -> str:
    return (
        str(value or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def parse_step_index(raw: Any) -> int | None:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value
