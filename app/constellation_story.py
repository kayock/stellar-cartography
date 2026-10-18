"""
constellation_story.py

Constellation Story Deck — local story model, detection, Cosmic Signal /
Spectrum relevance, and guided-tour state.

Implementation map (Phase 1 findings):
  * SelectionResult.constellation already reads Stellarium iauConstellation.
  * Remote Control can focus objects (POST /api/main/focus), set FoV,
    and toggle ConstellationMgr lines/labels/boundaries/art/isolate.
  * Sky culture is readable as StelSkyCultureMgr.currentSkyCultureID.
  * Constellations are selectable by English name via focus, not by
    listobjectsbytype?type=Constellation (empty).
  * No second Cosmic Signal or Spectrum registry is created here.

This module never talks to the network. Stellarium I/O stays in
stellarium_client.py. Tour session state is in-process only.
"""

from __future__ import annotations

import re
import threading
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from . import archaeoastronomy
from . import cosmic_signal_registry
from . import solar_system_media_registry as ss_registry
from . import spectrum_gallery_registry

REGISTRY_PATH = Path(__file__).resolve().parent / "data" / "constellation_story_registry.json"

_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
_STORY_RELATION = ("exact", "related", "general")
_STORY_KINDS = ("iau_constellation", "cultural_sky_story")
_SOURCE_QUALITY = frozenset(
    {
        "stellarium_skyculture",
        "museum",
        "university",
        "observatory",
        "cultural_organization",
        "scholarly",
    }
)
_EVIDENCE_TYPES = frozenset(
    {
        "community_sourced",
        "scholarly_ethnographic",
        "archaeological_inference",
        "modern_reconstruction",
    }
)
_MOTIF_RELATIONSHIPS = frozenset(
    {
        "independent_similarity",
        "regional_parallel",
        "possible_cultural_exchange",
        "documented_exchange",
        "unknown",
    }
)
CULTURE_CATALOG = (
    {"id": "modern", "label": "Modern IAU", "stellarium_ids": ("modern", "modern_iau")},
    {"id": "chinese", "label": "Chinese", "stellarium_ids": ("chinese", "chinese_chenzhuo", "modern_chinese")},
    {
        "id": "arabic_peninsula",
        "label": "Arabic (Arabian Peninsula tradition)",
        "stellarium_ids": ("arabic_arabian_peninsula", "arabic_indigenous"),
    },
    {
        "id": "arabic_sufi",
        "label": "Medieval Islamic astronomy (al-Ṣūfī)",
        "stellarium_ids": ("arabic_al-sufi",),
    },
    {"id": "maori", "label": "Māori", "stellarium_ids": ("maori",)},
    {
        "id": "ancestral_puebloan",
        "label": "Ancestral Puebloan",
        "stellarium_ids": (),
    },
    {
        "id": "mexica",
        "label": "Mexica (historical)",
        "stellarium_ids": ("aztec",),
    },
)

SUPPORTED_CONSTELLATION_CONTROLS = {
    "lines": "ConstellationMgr.linesDisplayed",
    "labels": "ConstellationMgr.namesDisplayed",
    "boundaries": "ConstellationMgr.boundariesDisplayed",
    "artwork": "ConstellationMgr.artDisplayed",
    "isolate": "ConstellationMgr.isolateSelected",
}

UNSUPPORTED_CONSTELLATION_CONTROLS = (
    {
        "id": "select_constellation_by_object_type",
        "reason": (
            "GET /api/objects/listobjectsbytype?type=Constellation returns []. "
            "Use search/focus with the English constellation name instead."
        ),
    },
)

_tour_lock = threading.Lock()
_tour_session: Optional[dict[str, Any]] = None


class ConstellationStoryError(ValueError):
    """Raised when the constellation story registry is malformed."""


@lru_cache(maxsize=1)
def load_registry() -> dict[str, Any]:
    import json

    raw = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    validate_registry(raw)
    return raw


def reload_registry() -> dict[str, Any]:
    load_registry.cache_clear()
    return load_registry()


def validate_registry(raw: dict[str, Any]) -> None:
    if not isinstance(raw, dict):
        raise ConstellationStoryError("Registry root must be an object.")
    if not isinstance(raw.get("entries"), list) or not raw["entries"]:
        raise ConstellationStoryError("Registry 'entries' must be a non-empty list.")
    seen: set[str] = set()
    for entry in raw["entries"]:
        if not isinstance(entry, dict):
            raise ConstellationStoryError("Each constellation entry must be an object.")
        cid = entry.get("id")
        if not isinstance(cid, str) or not _ID_RE.fullmatch(cid):
            raise ConstellationStoryError("Constellation id must be a slug.")
        if cid in seen:
            raise ConstellationStoryError(f"Duplicate constellation id '{cid}'.")
        seen.add(cid)
        kind = entry.get("story_kind") or "iau_constellation"
        if kind not in _STORY_KINDS:
            raise ConstellationStoryError(f"Entry '{cid}' has unsupported story_kind.")
        required = (
            "canonical_name",
            "sky_culture",
            "mythology_summary",
            "science_summary",
        )
        if kind == "iau_constellation":
            required = required + ("abbreviation",)
        for field in required:
            if not isinstance(entry.get(field), str) or not str(entry.get(field)).strip():
                raise ConstellationStoryError(f"Entry '{cid}' missing '{field}'.")
        if kind == "iau_constellation" and not str(entry.get("abbreviation") or "").strip():
            raise ConstellationStoryError(f"Entry '{cid}' missing IAU abbreviation.")
        if kind == "cultural_sky_story":
            _validate_cultural_provenance(entry)
        _validate_optional_southwest_fields(entry)
        for list_field in (
            "aliases",
            "major_objects",
            "notable_deep_sky_objects",
            "story_order",
            "cosmic_signal_tags",
            "spectrum_tags",
            "media_tags",
            "source_notes",
        ):
            if not isinstance(entry.get(list_field), list):
                raise ConstellationStoryError(f"Entry '{cid}' field '{list_field}' must be a list.")
        objects = _entry_objects(entry)
        object_ids = {obj["id"] for obj in objects}
        object_ids.add(cid)
        for step_id in entry["story_order"]:
            if step_id not in object_ids:
                raise ConstellationStoryError(
                    f"Entry '{cid}' story_order refers to unknown id '{step_id}'."
                )
        if not isinstance(entry.get("enabled"), bool):
            raise ConstellationStoryError(f"Entry '{cid}' needs boolean 'enabled'.")


def _validate_cultural_provenance(entry: dict[str, Any]) -> None:
    cid = entry.get("id")
    for field in ("culture_id", "culture_name", "tradition_name", "source_quality"):
        if not isinstance(entry.get(field), str) or not entry[field].strip():
            raise ConstellationStoryError(f"Cultural story '{cid}' missing '{field}'.")
    if entry.get("source_quality") not in _SOURCE_QUALITY:
        raise ConstellationStoryError(f"Cultural story '{cid}' has unsupported source_quality.")
    notes = entry.get("source_notes")
    urls = entry.get("source_urls")
    if not isinstance(notes, list) or not notes:
        raise ConstellationStoryError(f"Cultural story '{cid}' missing source provenance notes.")
    if not isinstance(urls, list) or not urls:
        raise ConstellationStoryError(f"Cultural story '{cid}' missing source provenance.")
    for src in urls:
        if not isinstance(src, dict):
            raise ConstellationStoryError(f"Cultural story '{cid}' source_urls must be objects.")
        for key in ("title", "institution", "url", "supports"):
            if not isinstance(src.get(key), str) or not src[key].strip():
                raise ConstellationStoryError(
                    f"Cultural story '{cid}' source missing '{key}'."
                )
        if not str(src["url"]).lower().startswith(("http://", "https://")):
            raise ConstellationStoryError(f"Cultural story '{cid}' source url is invalid.")
    if not isinstance(entry.get("source_people"), str) or not entry["source_people"].strip():
        raise ConstellationStoryError(f"Cultural story '{cid}' missing source_people.")
    status = entry.get("public_story_status") or "public"
    if status in {"restricted", "deferred_restricted"}:
        raise ConstellationStoryError(f"Cultural story '{cid}' is restricted and cannot be enabled.")


def _validate_optional_southwest_fields(entry: dict[str, Any]) -> None:
    cid = entry.get("id")
    evidence = entry.get("evidence_type")
    if evidence is not None:
        if evidence not in _EVIDENCE_TYPES:
            raise ConstellationStoryError(f"Entry '{cid}' has unsupported evidence_type.")
    aliases = entry.get("search_aliases")
    if aliases is not None and not isinstance(aliases, list):
        raise ConstellationStoryError(f"Entry '{cid}' search_aliases must be a list.")
    motifs = entry.get("shared_motifs")
    if motifs is None:
        return
    if not isinstance(motifs, list):
        raise ConstellationStoryError(f"Entry '{cid}' shared_motifs must be a list.")
    for motif in motifs:
        if not isinstance(motif, dict):
            raise ConstellationStoryError(f"Entry '{cid}' shared motif must be an object.")
        rel = motif.get("relationship_status")
        if rel not in _MOTIF_RELATIONSHIPS:
            raise ConstellationStoryError(f"Entry '{cid}' shared motif missing relationship_status.")
        if rel == "documented_exchange" and not motif.get("source_support"):
            raise ConstellationStoryError(
                f"Entry '{cid}' documented_exchange motif needs cited source_support."
            )


def enabled_stories() -> list[dict[str, Any]]:
    return [e for e in load_registry()["entries"] if e.get("enabled")]


def enabled_stories_for_culture(culture_id: str | None) -> list[dict[str, Any]]:
    if not culture_id or culture_id in {"all", "*"}:
        return enabled_stories()
    key = _normalize_id(culture_id)
    return [e for e in enabled_stories() if _story_culture_id(e) == key]


def _story_culture_id(story: dict[str, Any]) -> str:
    if story.get("culture_id"):
        return _normalize_id(story["culture_id"])
    if (story.get("story_kind") or "iau_constellation") == "cultural_sky_story":
        return _normalize_id(story.get("sky_culture"))
    return "modern"


def _story_kind(story: dict[str, Any]) -> str:
    return story.get("story_kind") or "iau_constellation"


def get_story(constellation_id: str | None) -> dict[str, Any] | None:
    cid = _normalize_id(constellation_id)
    if not cid:
        return None
    for entry in enabled_stories():
        if entry["id"] == cid:
            return entry
    return None


def resolve_story(token: str | None) -> dict[str, Any] | None:
    """Resolve an IAU abbreviation, id, canonical name, or alias.

    Prefer a modern IAU story when several share a name.
    """
    matches = resolve_stories(token)
    if not matches:
        return None
    for entry in matches:
        if _story_kind(entry) == "iau_constellation":
            return entry
    return matches[0]


def resolve_stories(token: str | None) -> list[dict[str, Any]]:
    key = _normalize_name(token)
    if not key:
        return []
    found: list[dict[str, Any]] = []
    for entry in enabled_stories():
        candidates = [
            entry["id"],
            entry["canonical_name"],
            entry.get("abbreviation"),
            entry.get("native_name"),
            entry.get("translated_name"),
            *list(entry.get("aliases") or []),
            *list(entry.get("search_aliases") or []),
        ]
        for obj in _entry_objects(entry):
            candidates.extend([obj.get("id"), obj.get("name"), obj.get("search_name"), *(obj.get("aliases") or [])])
        if key in {_normalize_name(c) for c in candidates if c}:
            found.append(entry)
    return found


def list_constellations(culture: str | None = None) -> dict[str, Any]:
    reg = load_registry()
    stories = enabled_stories_for_culture(culture)
    return {
        "ok": True,
        "deck_title": reg.get("deck_title") or "Stories of the Sky",
        "deck_subtitle": reg.get("deck_subtitle"),
        "default_sky_culture": reg.get("default_sky_culture"),
        "sky_culture_note": reg.get("sky_culture_note"),
        "selected_culture": culture or "all",
        "cultures": list_cultures()["cultures"],
        "constellations": [_story_list_item(e) for e in stories],
        "stories": [_story_list_item(e) for e in stories],
    }


def list_cultures() -> dict[str, Any]:
    counts: dict[str, int] = {}
    for entry in enabled_stories():
        cid = _story_culture_id(entry)
        counts[cid] = counts.get(cid, 0) + 1
    cultures = []
    for item in CULTURE_CATALOG:
        cultures.append(
            {
                **item,
                "stellarium_ids": list(item["stellarium_ids"]),
                "story_count": counts.get(item["id"], 0),
                "enabled": counts.get(item["id"], 0) > 0,
            }
        )
    unknown = [cid for cid in counts if cid not in {c["id"] for c in CULTURE_CATALOG}]
    for cid in unknown:
        cultures.append(
            {
                "id": cid,
                "label": cid,
                "stellarium_ids": [],
                "story_count": counts[cid],
                "enabled": True,
            }
        )
    return {"ok": True, "cultures": cultures}


def _story_list_item(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": entry["id"],
        "canonical_name": entry["canonical_name"],
        "abbreviation": entry.get("abbreviation") or "",
        "sky_culture": entry.get("sky_culture"),
        "culture_id": _story_culture_id(entry),
        "culture_name": entry.get("culture_name") or ("Modern IAU" if _story_kind(entry) == "iau_constellation" else entry.get("sky_culture")),
        "tradition_name": entry.get("tradition_name"),
        "story_kind": _story_kind(entry),
        "native_name": entry.get("native_name"),
        "translated_name": entry.get("translated_name"),
        "search_aliases": list(entry.get("search_aliases") or []),
        "evidence_type": entry.get("evidence_type"),
        "story_type": entry.get("story_type"),
        "archaeoastronomy_eligible": archaeoastronomy.is_eligible_story(entry),
        "source_people": entry.get("source_people"),
        "enabled": True,
        "object_count": len(_entry_objects(entry)),
        "step_count": len(entry.get("story_order") or []),
        "iau_overlap": list(entry.get("iau_overlap") or ([entry.get("abbreviation")] if entry.get("abbreviation") else [])),
    }


def _section_labels(story: dict[str, Any], kind: str) -> dict[str, str]:
    if kind != "cultural_sky_story":
        story_label = "Modern IAU Story"
    elif story.get("evidence_type") == "archaeological_inference":
        story_label = "Archaeological Interpretation"
    elif story.get("living_tradition") is False:
        story_label = "Historical Source"
    else:
        story_label = "Traditional Story"
    return {
        "story": story_label,
        "science": "Scientific View",
        "media": "Official NASA Media",
        "signal": "Cosmic Signal",
        "sources": "Sources & Context",
    }


def _source_context(story: dict[str, Any]) -> dict[str, Any]:
    sources = [s for s in (story.get("source_urls") or []) if isinstance(s, dict)]
    primary = sources[0] if sources else {}
    return {
        "people": story.get("source_people"),
        "tradition": story.get("tradition_name") or story.get("culture_name"),
        "evidence_type": story.get("evidence_type"),
        "institution": primary.get("institution"),
        "title": primary.get("title"),
        "date": primary.get("date") or story.get("source_date"),
        "note": story.get("terminology_note") or story.get("cultural_note"),
        "sources": sources,
    }


def detect_constellation(
    selection: dict[str, Any] | None,
    *,
    culture: str | None = None,
) -> dict[str, Any]:
    """Detect story context from a Cartography/Stellarium selection."""
    selection = selection if isinstance(selection, dict) else {}
    raw_abbr = selection.get("constellation")
    raw_name = selection.get("name") or selection.get("alt_name")
    matches: list[dict[str, Any]] = []
    seen: set[str] = set()
    for token in (raw_name, raw_abbr, selection.get("catalogue_designations")):
        for entry in resolve_stories(token if isinstance(token, str) else None):
            if entry["id"] in seen:
                continue
            seen.add(entry["id"])
            matches.append(entry)
    culture_key = _normalize_id(culture) if culture and culture not in {"all", "*"} else ""
    preferred = [m for m in matches if _story_culture_id(m) == culture_key] if culture_key else matches
    pool = preferred or matches
    story = None
    for entry in pool:
        if _story_kind(entry) == "iau_constellation":
            story = entry
            break
    if story is None and pool:
        story = pool[0]
    iau = None
    if isinstance(raw_abbr, str) and raw_abbr.strip():
        iau = raw_abbr.strip()
    elif story and story.get("abbreviation"):
        iau = story["abbreviation"]
    available = bool(story)
    return {
        "ok": True,
        "detected": bool(iau or story or matches),
        "iau_abbreviation": iau,
        "story_id": story["id"] if story else None,
        "canonical_name": story["canonical_name"] if story else None,
        "story_available": available,
        "control_visible": available,
        "control_label": "Open Stories of the Sky" if available else None,
        "matching_stories": [_story_list_item(m) for m in matches],
        "selected_culture": culture_key or None,
        "empty_reason": None
        if available
        else (
            "No curated sky story is available for this selection."
            if iau
            else "This selection has no constellation context."
        ),
    }


def story_payload(
    constellation_id: str | None,
    *,
    selection: dict[str, Any] | None = None,
    sky_culture_live: str | None = None,
) -> dict[str, Any]:
    if constellation_id is not None and not _valid_requested_id(constellation_id):
        return {"ok": False, "error": "Malformed constellation id."}
    story = get_story(constellation_id) or resolve_story(constellation_id)
    if not story:
        return {"ok": False, "error": "Unknown constellation story."}
    culture = _culture_view(story, sky_culture_live)
    objects = _entry_objects(story)
    signals = match_signals_for_constellation(story, selection)
    spectra = match_spectra_for_constellation(story, selection)
    media = match_media_for_constellation(story)
    kind = _story_kind(story)
    live_sync = bool(sky_culture_live) and _normalize_name(sky_culture_live) in {
        _normalize_name(x) for x in ([story.get("sky_culture")] + list(story.get("stellarium_culture_ids") or []))
    }
    return {
        "ok": True,
        "id": story["id"],
        "canonical_name": story["canonical_name"],
        "abbreviation": story.get("abbreviation") or "",
        "story_kind": kind,
        "culture_id": _story_culture_id(story),
        "culture_name": story.get("culture_name") or culture["display_name"],
        "tradition_name": story.get("tradition_name"),
        "native_name": story.get("native_name"),
        "translated_name": story.get("translated_name"),
        "source_people": story.get("source_people"),
        "source_region": story.get("source_region"),
        "source_quality": story.get("source_quality"),
        "source_urls": story.get("source_urls") or [],
        "source_context": _source_context(story),
        "evidence_type": story.get("evidence_type"),
        "living_tradition": bool(story.get("living_tradition")),
        "public_story_status": story.get("public_story_status") or "public",
        "search_aliases": list(story.get("search_aliases") or []),
        "terminology_note": story.get("terminology_note"),
        "archaeological_context": story.get("archaeological_context"),
        "shared_motifs": list(story.get("shared_motifs") or []),
        "related_story_ids": list(story.get("related_story_ids") or []),
        "iau_overlap": list(story.get("iau_overlap") or []),
        "cultural_note": story.get("cultural_note"),
        "sky_culture": culture["story_sky_culture"],
        "sky_culture_live": sky_culture_live,
        "sky_culture_synchronized": bool(culture["synchronized"] or live_sync),
        "sky_culture_display": culture["display_name"],
        "stellarium_sky_culture": sky_culture_live,
        "stellarium_culture_is_distinct": not bool(culture["synchronized"] or live_sync),
        "culture_specific_name": culture["constellation_name"],
        "mythology_summary": culture["mythology_summary"],
        "science_summary": story["science_summary"],
        "story_summary": story.get("story_summary") or culture["mythology_summary"],
        "section_labels": _section_labels(story, kind),
        "story_type": story.get("story_type"),
        "archaeoastronomy_eligible": archaeoastronomy.is_eligible_story(story),
        "major_objects": story.get("major_objects") or [],
        "notable_deep_sky_objects": story.get("notable_deep_sky_objects") or [],
        "story_order": list(story.get("story_order") or []),
        "source_notes": story.get("source_notes") or [],
        "signals": signals,
        "spectra": spectra,
        "media": media,
        "comparison": compare_stories(story["id"], selection=selection),
        "audio_autoplay": False,
        "tour_hint": "Stellarium does not move until you start the guided tour.",
    }


def constellation_context(
    selection: dict[str, Any] | None,
    *,
    include_story: bool = False,
    sky_culture_live: str | None = None,
    culture: str | None = None,
    story_id: str | None = None,
) -> dict[str, Any]:
    detected = detect_constellation(selection, culture=culture)
    requested = get_story(story_id) if story_id else None
    payload = {
        "ok": True,
        "context": detected,
        "audio_autoplay": False,
        "sky_culture_live": sky_culture_live,
        "stellarium_sky_culture": {
            "id": sky_culture_live,
            "label": sky_culture_live or "unknown",
            "distinct_from_story_culture": True,
            "note": "Stellarium's active rendering culture is independent of the Cartography story selector unless the ids actually match.",
        },
        "cultures": list_cultures()["cultures"],
    }
    chosen_id = (requested or {}).get("id") or detected.get("story_id")
    if include_story and chosen_id:
        payload["story"] = story_payload(
            chosen_id,
            selection=selection,
            sky_culture_live=sky_culture_live,
        )
        payload["stellarium_sky_culture"]["distinct_from_story_culture"] = bool(
            (payload["story"] or {}).get("stellarium_culture_is_distinct")
        )
    return payload


def compare_stories(
    token: str | None,
    *,
    selection: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Same physical sky, different human traditions — only when mappings are strong."""
    matches: list[dict[str, Any]] = []
    seen: set[str] = set()
    tokens = [token]
    if not token and isinstance(selection, dict):
        tokens.extend([selection.get("name"), selection.get("alt_name"), selection.get("constellation")])
    for raw in tokens:
        for entry in resolve_stories(raw if isinstance(raw, str) else None):
            if entry["id"] in seen:
                continue
            seen.add(entry["id"])
            matches.append(entry)
    primary = get_story(token) or (matches[0] if matches else None)
    extra_ids: list[str] = []
    if primary:
        extra_ids.extend(str(x) for x in (primary.get("related_story_ids") or []) if x)
        for motif in primary.get("shared_motifs") or []:
            if not isinstance(motif, dict):
                continue
            extra_ids.extend(str(x) for x in (motif.get("tradition_story_ids") or []) if x)
    for eid in extra_ids:
        if eid in seen:
            continue
        extra = get_story(eid)
        if extra:
            seen.add(eid)
            matches.append(extra)
    strong = matches
    archaeo_ids = {e["id"] for e in strong if archaeoastronomy.is_eligible_story(e)}
    observational = len(archaeo_ids) >= 2 and bool(primary and primary["id"] in archaeo_ids)
    note = (
        "Similar observational function. Traditions remain separate; this is not a shared origin."
        if observational
        else "Traditions remain separate. Shared stars are the same physical objects, not a merged story."
    )
    return {
        "ok": True,
        "title": "Same sky — different stories",
        "available": len(strong) >= 2,
        "query": token,
        "comparison_kind": "similar_observational_function" if observational else "same_sky_object",
        "traditions": [
            {
                "id": e["id"],
                "story_kind": _story_kind(e),
                "culture_id": _story_culture_id(e),
                "culture_name": e.get("culture_name") or ("Modern IAU" if _story_kind(e) == "iau_constellation" else e.get("sky_culture")),
                "tradition_name": e.get("tradition_name") or "Modern IAU constellation figure",
                "story_name": e.get("native_name") or e["canonical_name"],
                "translated_name": e.get("translated_name") or e["canonical_name"],
                "source_quality": e.get("source_quality") or "iau_figure",
                "source_notes": e.get("source_notes") or [],
                "iau_overlap": e.get("iau_overlap") or ([e.get("abbreviation")] if e.get("abbreviation") else []),
                "story_type": e.get("story_type"),
                "comparison_kind": (
                    "similar_observational_function"
                    if e["id"] in archaeo_ids and observational
                    else "same_sky_object"
                ),
            }
            for e in strong
        ],
        "note": note,
        "audio_autoplay": False,
    }


def match_signals_for_constellation(
    story: dict[str, Any],
    selection: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Rank Cosmic Signal entries as exact / related / general.

    Reuses cosmic_signal_registry. Does not create a second audio catalog.
    """
    objects = _entry_objects(story)
    current_keys = set(_identity_keys_from_selection(selection))
    current_in_constellation = bool(current_keys and current_keys.intersection(_object_identity_keys(objects)))
    exact: list[dict[str, Any]] = []
    related: list[dict[str, Any]] = []
    general: list[dict[str, Any]] = []
    seen: set[str] = set()

    for obj in objects:
        obj_keys = _object_identity_keys([obj])
        current_is_this_object = bool(current_keys and current_keys.intersection(obj_keys))
        match = cosmic_signal_registry.match_signals_for_target(
            _selection_from_object(obj),
            allow_featured=False,
        )
        for entry in match.get("exact") or []:
            if entry["id"] in seen:
                continue
            seen.add(entry["id"])
            if current_keys and current_in_constellation and not current_is_this_object:
                presented = _present_signal(entry, "related", obj["id"])
                related.append(presented)
            else:
                exact.append(_present_signal(entry, "exact", obj["id"]))

    abbr = _normalize_name(story.get("abbreviation"))
    cid = _normalize_name(story.get("id"))
    specific_tags = {
        _normalize_name(t)
        for t in (story.get("cosmic_signal_tags") or [])
        if _normalize_name(t) in {abbr, cid, _normalize_name(story.get("canonical_name"))}
    }

    for entry in cosmic_signal_registry.enabled_entries():
        if entry["id"] in seen:
            continue
        relation = _signal_story_relation(entry, abbr, cid, specific_tags)
        if relation == "related":
            presented = _present_signal(
                cosmic_signal_registry._present(entry, entry.get("relevance_capabilities", ["related_body"])[0]),
                "related",
                None,
            )
            seen.add(presented["id"])
            related.append(presented)
        elif relation == "general":
            presented = _present_signal(
                cosmic_signal_registry._present(entry, "general_featured"),
                "general",
                None,
            )
            seen.add(presented["id"])
            general.append(presented)

    ranked = exact + related + general
    return {
        "ok": True,
        "exact": exact,
        "related": related,
        "general": general,
        "ranked": ranked,
        "empty": not ranked,
        "empty_message": "No curated Cosmic Signal is associated with this constellation yet.",
        "registry": "cosmic_signal_registry",
        "audio_autoplay": False,
    }


def match_spectra_for_constellation(
    story: dict[str, Any],
    selection: dict[str, Any] | None = None,
) -> dict[str, Any]:
    objects = _entry_objects(story)
    exact: list[dict[str, Any]] = []
    related: list[dict[str, Any]] = []
    seen: set[str] = set()
    current_keys = set(_identity_keys_from_selection(selection))

    for obj in objects:
        obj_keys = _object_identity_keys([obj])
        current_is_this_object = bool(current_keys and current_keys.intersection(obj_keys))
        match = spectrum_gallery_registry.match_spectrum_for_target(
            _selection_from_object(obj),
            allow_all_sky=False,
        )
        for entry in match.get("available_views") or []:
            if entry["id"] in seen:
                continue
            seen.add(entry["id"])
            item = dict(entry)
            item["object_id"] = obj["id"]
            if current_keys and not current_is_this_object:
                item["story_relation"] = "related"
                related.append(item)
            else:
                item["story_relation"] = "exact"
                exact.append(item)

    ranked = exact + related
    return {
        "ok": True,
        "exact": exact,
        "related": related,
        "ranked": ranked,
        "empty": not ranked,
        "empty_message": "No curated Spectrum Gallery image is associated with this constellation yet.",
        "registry": "spectrum_gallery_registry",
    }


def match_media_for_constellation(story: dict[str, Any]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for obj in _entry_objects(story):
        target_id = ss_registry.normalize_media_target_id(obj.get("name"))
        if not target_id:
            target_id = ss_registry.normalize_media_target_id(obj.get("id"))
        if not target_id:
            continue
        entry = ss_registry.get_entry(target_id)
        if not entry:
            continue
        items.append(
            {
                "id": entry.get("id"),
                "title": entry.get("title") or entry.get("id"),
                "object_id": obj["id"],
                "source": "solar_system_media_registry",
            }
        )
    return {
        "ok": True,
        "items": items,
        "empty": not items,
        "empty_message": "No Solar System / planetary media is associated with this constellation.",
        "registry": "solar_system_media_registry",
    }


def story_steps(story: dict[str, Any]) -> list[dict[str, Any]]:
    by_id = {obj["id"]: obj for obj in _entry_objects(story)}
    steps: list[dict[str, Any]] = []
    for index, step_id in enumerate(story.get("story_order") or []):
        if step_id == story["id"]:
            if _story_kind(story) == "cultural_sky_story":
                continue
            obj = {
                "id": story["id"],
                "name": story["canonical_name"],
                "search_name": story["canonical_name"],
                "kind": "constellation",
                "aliases": list(story.get("aliases") or []),
                "designations": [story.get("abbreviation") or ""],
                "notes": story["science_summary"],
                "fov_deg": 45,
            }
        else:
            obj = dict(by_id.get(step_id) or {})
        if not obj:
            continue
        steps.append(
            {
                "index": index,
                "object_id": obj["id"],
                "name": obj.get("name"),
                "search_name": obj.get("search_name") or obj.get("name"),
                "kind": obj.get("kind"),
                "notes": obj.get("notes") or "",
                "fov_deg": obj.get("fov_deg"),
                "designations": obj.get("designations") or [],
            }
        )
    return steps


def reset_tour() -> None:
    global _tour_session
    with _tour_lock:
        _tour_session = None


def get_tour_session() -> dict[str, Any] | None:
    with _tour_lock:
        if _tour_session is None:
            return None
        return dict(_tour_session)


def start_tour(
    constellation_id: str | None,
    original_selection: dict[str, Any] | None,
) -> dict[str, Any]:
    global _tour_session
    if constellation_id is not None and not _valid_requested_id(constellation_id):
        return {"ok": False, "error": "Malformed constellation id.", "audio_autoplay": False}
    story = get_story(constellation_id) or resolve_story(constellation_id)
    if not story:
        return {"ok": False, "error": "Unknown constellation story.", "audio_autoplay": False}
    steps = story_steps(story)
    if not steps:
        return {"ok": False, "error": "This constellation story has no tour steps.", "audio_autoplay": False}
    original = _remember_selection(original_selection)
    session = {
        "active": True,
        "constellation_id": story["id"],
        "step_index": 0,
        "total_steps": len(steps),
        "original_selection": original,
        "audio_autoplay": False,
    }
    with _tour_lock:
        _tour_session = session
    return {"ok": True, **_tour_view(story, session, steps)}


def step_tour(direction: str) -> dict[str, Any]:
    global _tour_session
    with _tour_lock:
        session = _tour_session
        if not session or not session.get("active"):
            return {"ok": False, "error": "No constellation tour is active.", "audio_autoplay": False}
        story = get_story(session["constellation_id"])
        if not story:
            return {"ok": False, "error": "Active tour constellation is no longer available.", "audio_autoplay": False}
        steps = story_steps(story)
        delta = -1 if str(direction).lower() in {"prev", "previous", "back"} else 1
        nxt = session["step_index"] + delta
        if nxt < 0 or nxt >= len(steps):
            view = _tour_view(story, session, steps)
            view["ok"] = True
            view["bounded"] = True
            return view
        session["step_index"] = nxt
        session["audio_autoplay"] = False
        _tour_session = session
        return {"ok": True, **_tour_view(story, session, steps)}


def stop_tour() -> dict[str, Any]:
    global _tour_session
    with _tour_lock:
        session = _tour_session
        _tour_session = None
    if not session:
        return {"ok": True, "active": False, "restored": False, "audio_autoplay": False}
    return {
        "ok": True,
        "active": False,
        "restored": True,
        "original_selection": session.get("original_selection"),
        "restore_search_name": (session.get("original_selection") or {}).get("restore_search_name"),
        "audio_autoplay": False,
    }


def tour_status() -> dict[str, Any]:
    session = get_tour_session()
    if not session:
        return {"ok": True, "active": False, "audio_autoplay": False}
    story = get_story(session["constellation_id"])
    if not story:
        return {"ok": True, "active": False, "audio_autoplay": False}
    return {"ok": True, **_tour_view(story, session, story_steps(story))}


def apply_tour_to_stellarium(client: Any, tour: dict[str, Any]) -> dict[str, Any]:
    """Focus the current tour step. Never starts audio."""
    if not tour.get("ok") or not tour.get("active"):
        return tour
    step = tour.get("step") or {}
    search = step.get("search_name")
    focused = False
    if search and hasattr(client, "focus_object"):
        focused = bool(client.focus_object(search))
    fov = step.get("fov_deg")
    if focused and isinstance(fov, (int, float)) and hasattr(client, "set_fov"):
        client.set_fov(float(fov))
    selection = None
    if hasattr(client, "get_selection"):
        result = client.get_selection()
        if hasattr(result, "ok"):
            selection = {
                "ok": result.ok,
                "connected": result.connected,
                "name": result.name,
                "alt_name": result.alt_name,
                "object_type": result.object_type,
                "catalogue_designations": result.catalogue_designations,
                "constellation": result.constellation,
                "ra_deg": result.ra_deg,
                "dec_deg": result.dec_deg,
                "error": result.error,
            }
    tour = dict(tour)
    tour["focused"] = focused
    tour["selection"] = selection
    tour["audio_autoplay"] = False
    if selection:
        story = get_story(tour.get("constellation_id"))
        if story:
            tour["signals"] = match_signals_for_constellation(story, selection)
            tour["spectra"] = match_spectra_for_constellation(story, selection)
    return tour


def restore_original_selection(client: Any, stop_result: dict[str, Any]) -> dict[str, Any]:
    search = stop_result.get("restore_search_name")
    restored = False
    if search and hasattr(client, "focus_object"):
        restored = bool(client.focus_object(search))
    out = dict(stop_result)
    out["restored"] = restored
    out["audio_autoplay"] = False
    if hasattr(client, "get_selection"):
        result = client.get_selection()
        out["selection"] = {
            "ok": getattr(result, "ok", False),
            "connected": getattr(result, "connected", False),
            "name": getattr(result, "name", None),
            "alt_name": getattr(result, "alt_name", None),
            "constellation": getattr(result, "constellation", None),
        }
    return out


def constellation_controls_payload(properties: dict[str, Any] | None) -> dict[str, Any]:
    props = properties if isinstance(properties, dict) else {}
    controls = {}
    for key, prop_id in SUPPORTED_CONSTELLATION_CONTROLS.items():
        entry = props.get(prop_id)
        value = entry.get("value") if isinstance(entry, dict) else entry
        controls[key] = {
            "id": key,
            "property": prop_id,
            "supported": True,
            "value": bool(value) if isinstance(value, bool) else None,
        }
    return {
        "ok": True,
        "controls": controls,
        "unsupported": list(UNSUPPORTED_CONSTELLATION_CONTROLS),
        "sky_culture_live": _property_string(props, "StelSkyCultureMgr.currentSkyCultureID"),
    }


def parse_control_request(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {"ok": False, "error": "Expected a JSON object."}
    requested = payload.get("controls") if isinstance(payload.get("controls"), dict) else payload
    updates = []
    unknown = []
    for key, value in requested.items():
        if key in {"controls", "ok"}:
            continue
        if key not in SUPPORTED_CONSTELLATION_CONTROLS:
            unknown.append(key)
            continue
        if not isinstance(value, bool):
            return {"ok": False, "error": f"Control '{key}' must be a boolean."}
        updates.append({"id": key, "property": SUPPORTED_CONSTELLATION_CONTROLS[key], "value": value})
    if unknown and not updates:
        return {
            "ok": False,
            "error": "Unsupported constellation control.",
            "unsupported": unknown,
        }
    return {"ok": True, "updates": updates, "ignored": unknown}


def constellation_narration(
    kind: str,
    *,
    story: dict[str, Any] | None = None,
    selection: dict[str, Any] | None = None,
    tour: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Cartography-authored spoken text. TTS services do not invent this content."""
    selection = selection if isinstance(selection, dict) else {}
    tour = tour if isinstance(tour, dict) else {}
    step = tour.get("step") if isinstance(tour.get("step"), dict) else {}
    constellation_name = (story or {}).get("canonical_name") or selection.get("constellation")
    source_object = step.get("name") or selection.get("name")
    step_index = tour.get("step_index")
    total_steps = tour.get("total_steps")
    kind_key = (kind or "constellation_overview").strip()
    if kind_key == "archaeoastronomy":
        visual = archaeoastronomy.visual_payload((story or {}).get("id"))
        text = _clip_spoken(archaeoastronomy.narration_text(visual), 500)
        return {
            "ok": True,
            "listen_available": True,
            "feature_flag": "narration_hook",
            "kind": kind_key,
            "title": f"{(story or {}).get('canonical_name') or 'Archaeoastronomy'} — visual mode",
            "text": text,
            "summary": text,
            "source_object": source_object,
            "constellation": constellation_name,
            "step_index": step_index,
            "total_steps": total_steps,
            "label": "Cartography Narration",
            "audio_autoplay": False,
            "interface": {
                "intent": "Cartography-authored text is sent to a local TTS renderer. The TTS service does not invent astronomy content.",
                "wired": ["father_fox", "kayock_voice"],
                "payload": {"text": text, "source": "stellar-cartography-archaeoastronomy"},
            },
        }
    if kind_key == "tour_step":
        title = f"{constellation_name or 'Constellation'} — {source_object or 'tour step'}"
        tradition = (story or {}).get("tradition_name")
        step_lead = (
            f"{source_object} is step {(step_index or 0) + 1} of {total_steps or 0} in {constellation_name}."
            if source_object and constellation_name
            else "Tour step."
        )
        if story and _story_kind(story) == "cultural_sky_story" and tradition:
            step_lead = f"In the {tradition} represented by this story, {step_lead}"
        text = _clip_spoken(
            _join_sentences(
                [
                    step_lead,
                    step.get("notes"),
                ]
            ),
            400,
        )
    elif kind_key == "object_transition":
        title = f"Moving to {source_object or 'the next object'}"
        text = _clip_spoken(
            _join_sentences(
                [
                    f"The tour is moving to {source_object} in {constellation_name}."
                    if source_object
                    else "The tour is moving to the next object.",
                    step.get("notes"),
                ]
            ),
            250,
        )
    else:
        title = constellation_name or "Sky story"
        tradition = (story or {}).get("tradition_name")
        if story and (story or {}).get("narration_lead"):
            opener = str(story["narration_lead"]).strip()
        elif story and (story or {}).get("evidence_type") == "archaeological_inference":
            opener = (
                "This archaeological interpretation of Ancestral Puebloan observations suggests "
                f"{(story or {}).get('native_name') or constellation_name} is a public archaeoastronomy "
                "record, not a living oral constellation story."
            )
        elif story and _story_kind(story) == "cultural_sky_story" and tradition:
            opener = f"In the {tradition} represented by this story, {(story or {}).get('native_name') or constellation_name} is a sourced sky grouping, not an IAU constellation boundary."
        elif constellation_name:
            opener = f"{constellation_name} ({(story or {}).get('abbreviation')}) is a modern IAU constellation."
        else:
            opener = "No constellation story is available."
        text = _clip_spoken(
            _join_sentences(
                [
                    opener,
                    (story or {}).get("science_summary"),
                    (story or {}).get("mythology_summary"),
                ]
            ),
            900,
        )
    text = _strip_urls(text)
    return {
        "ok": True,
        "listen_available": True,
        "feature_flag": "narration_hook",
        "kind": kind_key,
        "title": title,
        "text": text,
        "summary": text,
        "source_object": source_object,
        "constellation": constellation_name,
        "step_index": step_index,
        "total_steps": total_steps,
        "label": "Cartography Narration",
        "audio_autoplay": False,
        "interface": {
            "intent": "Cartography-authored text is sent to a local TTS renderer. The TTS service does not invent astronomy content.",
            "wired": ["father_fox", "kayock_voice"],
            "payload": {"text": text, "source": "stellar-cartography-constellation-story"},
        },
    }


def _entry_objects(story: dict[str, Any]) -> list[dict[str, Any]]:
    objects: list[dict[str, Any]] = []
    for group in ("major_objects", "notable_deep_sky_objects"):
        for obj in story.get(group) or []:
            if isinstance(obj, dict) and isinstance(obj.get("id"), str):
                objects.append(obj)
    return objects


def _culture_view(story: dict[str, Any], live_id: str | None) -> dict[str, Any]:
    cultures = [c for c in (story.get("cultures") or []) if isinstance(c, dict)]
    story_culture = story.get("sky_culture") or "modern"
    chosen = None
    synchronized = False
    if live_id:
        for culture in cultures:
            if _normalize_name(culture.get("id")) == _normalize_name(live_id):
                chosen = culture
                synchronized = True
                break
    if chosen is None:
        for culture in cultures:
            if _normalize_name(culture.get("id")) == _normalize_name(story_culture):
                chosen = culture
                break
    if chosen is None:
        chosen = {
            "id": story_culture,
            "name": "Modern IAU" if story_culture == "modern" else story_culture,
            "constellation_name": story["canonical_name"],
            "mythology_summary": story.get("mythology_summary"),
        }
    return {
        "story_sky_culture": story_culture,
        "synchronized": synchronized,
        "display_name": chosen.get("name") or story_culture,
        "constellation_name": chosen.get("constellation_name") or story["canonical_name"],
        "mythology_summary": chosen.get("mythology_summary") or story.get("mythology_summary"),
    }


def _selection_from_object(obj: dict[str, Any]) -> dict[str, Any]:
    designations = " - ".join(obj.get("designations") or [])
    return {
        "name": obj.get("name"),
        "alt_name": obj.get("search_name"),
        "catalogue_designations": designations or None,
    }


def _object_identity_keys(objects: list[dict[str, Any]]) -> set[str]:
    keys: set[str] = set()
    for obj in objects:
        for raw in (
            obj.get("id"),
            obj.get("name"),
            obj.get("search_name"),
            *(obj.get("aliases") or []),
            *(obj.get("designations") or []),
        ):
            for token in cosmic_signal_registry._catalog_identity_keys(raw if isinstance(raw, str) else None):
                keys.add(token)
    return keys


def _identity_keys_from_selection(selection: dict[str, Any] | None) -> list[str]:
    keys: list[str] = []
    for raw in cosmic_signal_registry.selection_identity_strings(selection):
        for token in cosmic_signal_registry._catalog_identity_keys(raw):
            if token and token not in keys:
                keys.append(token)
    return keys


def _signal_matches_keys(entry: dict[str, Any], keys: set[str]) -> bool:
    aliases = {cosmic_signal_registry._normalize_name(a) for a in (entry.get("target_aliases") or [])}
    aliases.update(cosmic_signal_registry._normalize_name(a) for a in (entry.get("target_ids") or []))
    return bool(keys.intersection(aliases))


def _spectrum_matches_keys(entry: dict[str, Any], keys: set[str]) -> bool:
    aliases = {cosmic_signal_registry._normalize_name(a) for a in (entry.get("target_ids") or [])}
    aliases.update(cosmic_signal_registry._normalize_name(entry.get("title")))
    return bool(keys.intersection({k for k in aliases if k}))


def _signal_story_relation(
    entry: dict[str, Any],
    abbr: str,
    constellation_id: str,
    specific_tags: set[str],
) -> str | None:
    entry_const = _normalize_name(entry.get("constellation"))
    related = {_normalize_name(x) for x in (entry.get("related_constellations") or [])}
    if entry_const and entry_const in {abbr, constellation_id}:
        return "related"
    if related.intersection({abbr, constellation_id}):
        return "related"
    tags = {_normalize_name(t) for t in (entry.get("story_tags") or [])}
    if specific_tags and tags.intersection(specific_tags):
        return "related"
    return None


def _present_signal(entry: dict[str, Any], relation: str, object_id: str | None) -> dict[str, Any]:
    presented = dict(entry)
    presented["story_relation"] = relation if relation in _STORY_RELATION else "general"
    presented["relation_label"] = {"exact": "Exact", "related": "Related", "general": "General"}[presented["story_relation"]]
    presented["object_id"] = object_id
    presented["hearing_label"] = "What am I hearing?"
    return presented


def _remember_selection(selection: dict[str, Any] | None) -> dict[str, Any]:
    selection = selection if isinstance(selection, dict) else {}
    restore = selection.get("alt_name") or selection.get("name")
    return {
        "name": selection.get("name"),
        "alt_name": selection.get("alt_name"),
        "constellation": selection.get("constellation"),
        "ra_deg": selection.get("ra_deg"),
        "dec_deg": selection.get("dec_deg"),
        "restore_search_name": restore,
    }


def _tour_view(story: dict[str, Any], session: dict[str, Any], steps: list[dict[str, Any]]) -> dict[str, Any]:
    index = int(session.get("step_index") or 0)
    step = steps[index] if 0 <= index < len(steps) else None
    selection = _selection_from_object(step) if step else None
    return {
        "active": True,
        "constellation_id": story["id"],
        "canonical_name": story["canonical_name"],
        "abbreviation": story.get("abbreviation") or "",
        "step_index": index,
        "total_steps": len(steps),
        "step": step,
        "has_previous": index > 0,
        "has_next": index + 1 < len(steps),
        "original_selection": session.get("original_selection"),
        "signals": match_signals_for_constellation(story, selection),
        "spectra": match_spectra_for_constellation(story, selection),
        "narration": constellation_narration("tour_step", story=story, selection=selection, tour={"step": step, "step_index": index, "total_steps": len(steps)}),
        "audio_autoplay": False,
    }


def _property_string(properties: dict[str, Any], key: str) -> str | None:
    entry = properties.get(key)
    if isinstance(entry, dict):
        value = entry.get("value")
        return value.strip() if isinstance(value, str) and value.strip() else None
    if isinstance(entry, str) and entry.strip():
        return entry.strip()
    return None


def _normalize_name(value: Any) -> str:
    if not value or not isinstance(value, str):
        return ""
    return " ".join(value.strip().lower().split())


def _normalize_id(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip().lower()


def _valid_requested_id(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    raw = value.strip()
    if not raw or "/" in raw or "\\" in raw or ".." in raw:
        return False
    return bool(_ID_RE.fullmatch(raw.lower()) or resolve_story(raw))


def _join_sentences(parts: list[Any]) -> str:
    cleaned = [str(p).strip().rstrip(".") for p in parts if isinstance(p, str) and p.strip()]
    return (". ".join(cleaned) + ".") if cleaned else "No narration is available."


def _strip_urls(text: str) -> str:
    return re.sub(r"https?://\S+", "", text or "").replace("  ", " ").strip()


def _clip_spoken(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    clipped = text[: max_chars - 1].rsplit(" ", 1)[0].rstrip(".,;:")
    return clipped + "."
