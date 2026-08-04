"""
cosmic_signal_registry.py

Load and validate the curated Cosmic Signal Deck registry
(app/data/cosmic_signal_registry.json). Matching reuses Solar System
canonical IDs from solar_system_media_registry and supplements deep-space
aliases declared in this registry only.

URL validation covers the initial HTTPS URL (scheme, host allow-list, length,
control characters). It does not follow or enforce redirect chains; that
requires a later server media proxy.
"""

from __future__ import annotations

import json
import re
import urllib.parse
from functools import lru_cache
from pathlib import Path
from typing import Any

from . import solar_system_media_registry as ss_registry

REGISTRY_PATH = Path(__file__).resolve().parent / "data" / "cosmic_signal_registry.json"

MEDIA_TYPES = frozenset(
    {
        "instrument_signal",
        "data_audification",
        "data_sonification",
        "mission_audio",
        "historical_recording",
        "contextual_audio",
    }
)
RELEVANCE_LEVELS = frozenset(
    {"exact_target", "related_body", "related_mission", "general_featured"}
)
MEDIA_KINDS = frozenset({"audio", "video"})

MAX_URL_LEN = 2000
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_UNSAFE_URL_CHAR_RE = re.compile(r'[\s"\'<>]')

REQUIRED_ENTRY_FIELDS = (
    "id",
    "title",
    "enabled",
    "target_ids",
    "target_aliases",
    "related_body_ids",
    "related_missions",
    "relevance_capabilities",
    "media_type",
    "short_explanation",
    "mapping_explanation",
    "what_it_does_not_prove",
    "media_format",
    "media_kind",
    "media_url",
    "source_page_url",
    "credits",
    "attribution",
    "accessibility_description",
    "verified_date",
    "verification_notes",
    "final_resolved_media_host",
)


class RegistryError(ValueError):
    """Raised when the Cosmic Signal registry is malformed."""


@lru_cache(maxsize=1)
def load_registry() -> dict[str, Any]:
    raw = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    validate_registry(raw)
    return raw


def reload_registry() -> dict[str, Any]:
    load_registry.cache_clear()
    return load_registry()


def registry_public_payload() -> dict[str, Any]:
    """Return the validated registry for the local API (no secrets)."""
    return load_registry()


def _require_list_of_str(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(x, str) for x in value):
        raise RegistryError(f"Registry field '{field}' must be a list of strings.")
    return value


def is_allowed_url(
    url: str | None,
    *,
    allowed_hosts: frozenset[str] | set[str],
) -> bool:
    """Validate an initial URL. Does not follow redirects."""
    if not url or not isinstance(url, str):
        return False
    if len(url) > MAX_URL_LEN:
        return False
    if _CONTROL_CHAR_RE.search(url) or _UNSAFE_URL_CHAR_RE.search(url):
        return False
    try:
        parsed = urllib.parse.urlparse(url.strip())
    except Exception:  # noqa: BLE001
        return False
    scheme = (parsed.scheme or "").lower()
    if scheme in {"javascript", "data", "file", "blob"}:
        return False
    if scheme != "https":
        return False
    if parsed.username or parsed.password:
        return False
    host = (parsed.hostname or "").lower()
    return host in {h.lower() for h in allowed_hosts}


def validate_registry(raw: dict[str, Any]) -> None:
    if not isinstance(raw, dict):
        raise RegistryError("Registry root must be an object.")
    for key in ("allowed_media_hosts", "allowed_source_hosts", "allowed_poster_hosts"):
        _require_list_of_str(raw.get(key), key)
    if not isinstance(raw.get("entries"), list):
        raise RegistryError("Registry 'entries' must be a list.")
    if not isinstance(raw.get("deep_space_targets"), list):
        raise RegistryError("Registry 'deep_space_targets' must be a list.")

    media_hosts = frozenset(raw["allowed_media_hosts"])
    source_hosts = frozenset(raw["allowed_source_hosts"])
    poster_hosts = frozenset(raw["allowed_poster_hosts"])
    seen_ids: set[str] = set()
    deep_ids = set()

    for target in raw["deep_space_targets"]:
        if not isinstance(target, dict) or not isinstance(target.get("id"), str):
            raise RegistryError("Each deep_space_targets item needs a string id.")
        deep_ids.add(target["id"])
        _require_list_of_str(target.get("aliases") or [], "deep_space_targets.aliases")

    for entry in raw["entries"]:
        if not isinstance(entry, dict):
            raise RegistryError("Each entry must be an object.")
        for field in REQUIRED_ENTRY_FIELDS:
            if field not in entry:
                raise RegistryError(f"Entry missing required field '{field}'.")
        entry_id = entry["id"]
        if not isinstance(entry_id, str) or not entry_id:
            raise RegistryError("Entry id must be a non-empty string.")
        if entry_id in seen_ids:
            raise RegistryError(f"Duplicate entry id '{entry_id}'.")
        seen_ids.add(entry_id)

        if entry["media_type"] not in MEDIA_TYPES:
            raise RegistryError(f"Invalid media_type for '{entry_id}'.")
        if entry["media_kind"] not in MEDIA_KINDS:
            raise RegistryError(f"Invalid media_kind for '{entry_id}'.")
        caps = _require_list_of_str(entry["relevance_capabilities"], "relevance_capabilities")
        if not caps or any(c not in RELEVANCE_LEVELS for c in caps):
            raise RegistryError(f"Invalid relevance_capabilities for '{entry_id}'.")
        _require_list_of_str(entry["target_ids"], "target_ids")
        _require_list_of_str(entry["target_aliases"], "target_aliases")
        _require_list_of_str(entry["related_body_ids"], "related_body_ids")
        _require_list_of_str(entry["related_missions"], "related_missions")

        for body_id in list(entry["target_ids"]) + list(entry["related_body_ids"]):
            if body_id in deep_ids:
                continue
            if ss_registry.get_entry(body_id) is None:
                raise RegistryError(
                    f"Unknown target/body id '{body_id}' in entry '{entry_id}'."
                )

        if entry.get("enabled"):
            if not is_allowed_url(entry["media_url"], allowed_hosts=media_hosts):
                raise RegistryError(f"Unsafe media_url for enabled entry '{entry_id}'.")
            if not is_allowed_url(entry["source_page_url"], allowed_hosts=source_hosts):
                raise RegistryError(f"Unsafe source_page_url for enabled entry '{entry_id}'.")
            for optional_url_field in ("thumbnail_url", "poster_url", "captions_url"):
                val = entry.get(optional_url_field)
                if val is None or val == "":
                    continue
                hosts = poster_hosts
                if optional_url_field == "captions_url":
                    hosts = source_hosts | poster_hosts
                if not is_allowed_url(val, allowed_hosts=hosts):
                    raise RegistryError(f"Unsafe {optional_url_field} for '{entry_id}'.")
            verified = entry.get("verified_date")
            if not isinstance(verified, str) or "T" not in verified:
                raise RegistryError(
                    f"enabled entry '{entry_id}' needs ISO verified_date with timezone."
                )
            if not entry.get("final_resolved_media_host"):
                raise RegistryError(
                    f"enabled entry '{entry_id}' needs final_resolved_media_host from curation."
                )


def _normalize_name(value: str | None) -> str:
    if not value or not isinstance(value, str):
        return ""
    return " ".join(value.strip().lower().split())


def deep_space_targets_by_id() -> dict[str, dict[str, Any]]:
    return {
        t["id"]: t
        for t in load_registry().get("deep_space_targets", [])
        if isinstance(t, dict) and isinstance(t.get("id"), str)
    }


def resolve_canonical_target_id(raw_name: str | None) -> str | None:
    """Resolve a Stellarium name to a canonical id.

    Prefer Solar System media registry IDs, then Cosmic Signal deep-space targets.
    Exact id or exact alias only — never substring matching.
    """
    key = _normalize_name(raw_name)
    if not key:
        return None

    ss_id = ss_registry.normalize_media_target_id(key)
    if ss_id:
        return ss_id

    deep = deep_space_targets_by_id()
    if key in deep:
        return key

    candidates: list[tuple[int, str]] = []
    for entry_id, entry in deep.items():
        for alias in entry.get("aliases") or []:
            alias_key = _normalize_name(alias)
            if alias_key == key:
                candidates.append((-len(alias_key), entry_id))
    if not candidates:
        return None
    candidates.sort()
    return candidates[0][1]


def resolve_target_ids_from_selection(target: dict[str, Any] | None) -> list[str]:
    if not target or not isinstance(target, dict):
        return []
    found: list[str] = []
    for raw in (target.get("name"), target.get("alt_name")):
        resolved = resolve_canonical_target_id(raw if isinstance(raw, str) else None)
        if resolved and resolved not in found:
            found.append(resolved)
    return found


def enabled_entries() -> list[dict[str, Any]]:
    return [e for e in load_registry()["entries"] if e.get("enabled")]


def _entry_matches_exact(entry: dict[str, Any], target_ids: list[str], names: list[str]) -> bool:
    id_set = set(entry.get("target_ids") or [])
    if any(tid in id_set for tid in target_ids):
        return True
    aliases = {_normalize_name(a) for a in (entry.get("target_aliases") or [])}
    return any(n in aliases for n in names if n)


def match_signals_for_target(
    target: dict[str, Any] | None,
    *,
    allow_featured: bool = True,
) -> dict[str, Any]:
    """Return structured match result for the Cosmic Signal Deck."""
    reg = load_registry()
    target_ids = resolve_target_ids_from_selection(target)
    names = [
        _normalize_name(target.get("name") if target else None),
        _normalize_name(target.get("alt_name") if target else None),
    ]
    names = [n for n in names if n]

    exact: list[dict[str, Any]] = []
    related_body: list[dict[str, Any]] = []
    related_mission: list[dict[str, Any]] = []
    featured: list[dict[str, Any]] = []

    for entry in enabled_entries():
        caps = set(entry.get("relevance_capabilities") or [])
        if _entry_matches_exact(entry, target_ids, names) and "exact_target" in caps:
            exact.append(_present(entry, "exact_target"))
            continue

        related_bodies = set(entry.get("related_body_ids") or [])
        if any(tid in related_bodies for tid in target_ids) and "related_body" in caps:
            related_body.append(_present(entry, "related_body"))
            continue

        missions = {_normalize_name(m) for m in (entry.get("related_missions") or [])}
        mission_keys = set(target_ids) | set(names)
        if missions.intersection(mission_keys) and "related_mission" in caps:
            related_mission.append(_present(entry, "related_mission"))
            continue

        if allow_featured and "general_featured" in caps:
            featured.append(_present(entry, "general_featured"))

    primary = None
    relevance = None
    if exact:
        primary = exact[0]
        relevance = "exact_target"
    elif related_body:
        primary = related_body[0]
        relevance = "related_body"
    elif related_mission:
        primary = related_mission[0]
        relevance = "related_mission"
    elif allow_featured and featured:
        primary = featured[0]
        relevance = "general_featured"

    return {
        "ok": True,
        "canonical_target_ids": target_ids,
        "exact": exact,
        "related_body": related_body,
        "related_mission": related_mission,
        "featured": featured if allow_featured else [],
        "primary": primary,
        "relevance": relevance,
        "empty_exact_message": "No exact curated signal is available for this target.",
        "redirect_limitation_notice": reg.get("redirect_limitation_notice"),
        "deck_title": reg.get("deck_title"),
        "deck_subtitle": reg.get("deck_subtitle"),
    }


def _present(entry: dict[str, Any], relevance: str) -> dict[str, Any]:
    return {
        "id": entry["id"],
        "title": entry["title"],
        "relevance": relevance,
        "media_type": entry["media_type"],
        "conversion_method": entry.get("conversion_method"),
        "processing_notes": entry.get("processing_notes"),
        "observatories": entry.get("observatories") or [],
        "spacecraft": entry.get("spacecraft") or [],
        "instruments": entry.get("instruments") or [],
        "data_domains": entry.get("data_domains") or [],
        "short_explanation": entry["short_explanation"],
        "mapping_explanation": entry["mapping_explanation"],
        "what_it_does_not_prove": entry["what_it_does_not_prove"],
        "recorded_or_created_date": entry.get("recorded_or_created_date"),
        "duration_sec": entry.get("duration_sec"),
        "media_format": entry["media_format"],
        "media_kind": entry["media_kind"],
        "media_url": entry["media_url"],
        "source_page_url": entry["source_page_url"],
        "thumbnail_url": entry.get("thumbnail_url"),
        "poster_url": entry.get("poster_url"),
        "credits": entry["credits"],
        "attribution": entry["attribution"],
        "accessibility_description": entry["accessibility_description"],
        "transcript_text": entry.get("transcript_text"),
        "captions_url": entry.get("captions_url"),
        "final_resolved_media_host": entry.get("final_resolved_media_host"),
        "verified_date": entry.get("verified_date"),
    }
