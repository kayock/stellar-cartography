"""
solar_system_media_registry.py

Data-driven Solar System public-media registry for NASA Images lookups.
Source of truth: app/data/solar_system_media_registry.json
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

REGISTRY_PATH = Path(__file__).resolve().parent / "data" / "solar_system_media_registry.json"

_EMPTY_MEDIA_MESSAGE = (
    "No relevant NASA public-media result was returned for this target."
)

RESULT_TYPE_PUBLIC_MEDIA = "public_media_asset"
MEDIA_LABEL = "NASA public archive media"


@lru_cache(maxsize=1)
def load_registry() -> dict[str, Any]:
    raw = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("entries"), list):
        raise ValueError("Solar System media registry is malformed.")
    return raw


def get_media_label() -> str:
    reg = load_registry()
    return str(reg.get("media_label") or MEDIA_LABEL)


def get_result_type() -> str:
    reg = load_registry()
    return str(reg.get("result_type") or RESULT_TYPE_PUBLIC_MEDIA)


def entries_by_id() -> dict[str, dict[str, Any]]:
    return {e["id"]: e for e in load_registry()["entries"] if isinstance(e, dict) and "id" in e}


def all_entry_ids() -> tuple[str, ...]:
    return tuple(sorted(entries_by_id().keys()))


def get_entry(target_id: str | None) -> dict[str, Any] | None:
    if not target_id or not isinstance(target_id, str):
        return None
    return entries_by_id().get(target_id.strip().lower())


def normalize_media_target_id(raw: str | None) -> str | None:
    """Accept a canonical id or known alias; return canonical id or None."""
    if not raw or not isinstance(raw, str):
        return None
    key = raw.strip().lower()
    by_id = entries_by_id()
    if key in by_id:
        return key
    # Deterministic alias resolution: longest alias first, then stable id order.
    candidates: list[tuple[int, str, str]] = []
    for entry_id, entry in by_id.items():
        aliases = entry.get("aliases") or []
        if not isinstance(aliases, list):
            continue
        for alias in aliases:
            if not isinstance(alias, str):
                continue
            alias_key = alias.strip().lower()
            if alias_key == key:
                candidates.append((-len(alias_key), entry_id, alias_key))
    if not candidates:
        return None
    candidates.sort()
    return candidates[0][1]


def primary_search_query(entry: dict[str, Any]) -> str:
    terms = entry.get("search_terms") or []
    if isinstance(terms, list) and terms:
        first = terms[0]
        if isinstance(first, str) and first.strip():
            return first.strip()
    return str(entry.get("display_name") or entry["id"])


def _word_or_phrase_present(haystack: str, term: str) -> bool:
    term = term.strip().lower()
    if not term:
        return False
    if " " in term:
        return term in haystack
    return bool(re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", haystack))


def item_is_relevant(
    entry: dict[str, Any],
    *,
    title: str | None,
    description: str | None,
    keywords: str | None,
) -> bool:
    """Reject NASA hits that do not sufficiently mention the target."""
    parts = [p for p in (title, description, keywords) if isinstance(p, str) and p.strip()]
    haystack = " ".join(parts).lower()
    if not haystack:
        return False

    relevance_terms = entry.get("relevance_terms") or [entry.get("display_name", "")]
    if not any(_word_or_phrase_present(haystack, str(t)) for t in relevance_terms if t):
        return False

    parent_id = entry.get("parent_body")
    if parent_id:
        parent = get_entry(str(parent_id))
        parent_name = (parent or {}).get("display_name") or parent_id
        context = list(entry.get("context_terms") or [])
        context.extend([str(parent_name), str(parent_id), "moon", "satellite"])
        if not any(_word_or_phrase_present(haystack, str(t)) for t in context if t):
            # Distinctive moon names still need parent/moon context to avoid
            # unrelated uses of short names (e.g. Io, Rhea, Ariel).
            return False

    if entry.get("generic_guard"):
        context_terms = entry.get("context_terms") or []
        if not any(_word_or_phrase_present(haystack, str(t)) for t in context_terms if t):
            return False

    return True


def empty_result_message() -> str:
    return _EMPTY_MEDIA_MESSAGE
