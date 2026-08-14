"""
spectrum_gallery_registry.py

Load and validate the curated Spectrum Gallery registry
(app/data/spectrum_gallery_registry.json). Target identity reuses Cosmic
Signal Deck helpers (canonical IDs, aliases, catalogue designations, and
safe Messier/NGC normalization). Matching remains exact whole-value only.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from . import cosmic_signal_registry as csr

REGISTRY_PATH = Path(__file__).resolve().parent / "data" / "spectrum_gallery_registry.json"

REQUIRED_ENTRY_FIELDS = (
    "id",
    "title",
    "enabled",
    "target_ids",
    "target_aliases",
    "wavelength",
    "relevance",
    "observatory",
    "short_explanation",
    "image_url",
    "source_page_url",
    "credits",
    "verified_at",
)

RELEVANCE_LABELS = {
    "exact_target": "Exact target",
    "target_region": "Target region",
    "all_sky_context": "All-sky context",
}


class SpectrumRegistryError(ValueError):
    """Raised when the Spectrum Gallery registry is malformed."""


@lru_cache(maxsize=1)
def load_registry() -> dict[str, Any]:
    raw = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    validate_registry(raw)
    return raw


def reload_registry() -> dict[str, Any]:
    load_registry.cache_clear()
    return load_registry()


def registry_public_payload() -> dict[str, Any]:
    return load_registry()


def enabled_entries() -> list[dict[str, Any]]:
    return [e for e in load_registry()["entries"] if e.get("enabled")]


def validate_registry(raw: dict[str, Any]) -> None:
    if not isinstance(raw, dict):
        raise SpectrumRegistryError("Spectrum registry root must be an object.")
    wavelengths = raw.get("wavelengths")
    if not isinstance(wavelengths, list) or not wavelengths:
        raise SpectrumRegistryError("Spectrum registry needs a wavelengths list.")
    wavelength_set = {str(w) for w in wavelengths}
    relevance_levels = raw.get("relevance_levels")
    if not isinstance(relevance_levels, list) or not relevance_levels:
        raise SpectrumRegistryError("Spectrum registry needs relevance_levels.")
    relevance_set = {str(r) for r in relevance_levels}
    image_hosts = set(raw.get("allowed_image_hosts") or [])
    source_hosts = set(raw.get("allowed_source_hosts") or [])
    if not image_hosts or not source_hosts:
        raise SpectrumRegistryError("Spectrum registry needs allow-listed hosts.")

    entries = raw.get("entries")
    if not isinstance(entries, list) or not entries:
        raise SpectrumRegistryError("Spectrum registry needs entries.")

    seen_ids: set[str] = set()
    seen_urls: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise SpectrumRegistryError("Each spectrum entry must be an object.")
        for field in REQUIRED_ENTRY_FIELDS:
            if field not in entry:
                raise SpectrumRegistryError(f"Spectrum entry missing '{field}'.")
        entry_id = entry["id"]
        if not isinstance(entry_id, str) or not entry_id.strip():
            raise SpectrumRegistryError("Spectrum entry id must be a non-empty string.")
        if entry_id in seen_ids:
            raise SpectrumRegistryError(f"Duplicate spectrum entry id '{entry_id}'.")
        seen_ids.add(entry_id)
        if not isinstance(entry.get("enabled"), bool):
            raise SpectrumRegistryError(f"Spectrum entry '{entry_id}' enabled must be bool.")
        if not isinstance(entry.get("target_ids"), list) or any(
            not isinstance(x, str) for x in entry["target_ids"]
        ):
            raise SpectrumRegistryError(f"Spectrum entry '{entry_id}' target_ids invalid.")
        if not isinstance(entry.get("target_aliases"), list) or any(
            not isinstance(x, str) for x in entry["target_aliases"]
        ):
            raise SpectrumRegistryError(f"Spectrum entry '{entry_id}' target_aliases invalid.")
        wavelength = entry.get("wavelength")
        if wavelength not in wavelength_set:
            raise SpectrumRegistryError(
                f"Spectrum entry '{entry_id}' has unsupported wavelength '{wavelength}'."
            )
        relevance = entry.get("relevance")
        if relevance not in relevance_set:
            raise SpectrumRegistryError(
                f"Spectrum entry '{entry_id}' has unsupported relevance '{relevance}'."
            )
        if relevance == "all_sky_context" and entry["target_ids"]:
            raise SpectrumRegistryError(
                f"All-sky spectrum entry '{entry_id}' must not bind target_ids."
            )
        if relevance != "all_sky_context" and not entry["target_ids"]:
            raise SpectrumRegistryError(
                f"Spectrum entry '{entry_id}' needs target_ids for non-context relevance."
            )
        for text_field in (
            "title",
            "observatory",
            "short_explanation",
            "credits",
            "verified_at",
        ):
            if not isinstance(entry.get(text_field), str) or not entry[text_field].strip():
                raise SpectrumRegistryError(
                    f"Spectrum entry '{entry_id}' needs non-empty '{text_field}'."
                )
        if "T" not in entry["verified_at"]:
            raise SpectrumRegistryError(
                f"Spectrum entry '{entry_id}' verified_at must be ISO with timezone."
            )
        image_url = entry.get("image_url")
        source_url = entry.get("source_page_url")
        if not csr.is_allowed_url(image_url, allowed_hosts=image_hosts):
            raise SpectrumRegistryError(f"Unsafe image_url for '{entry_id}'.")
        if not csr.is_allowed_url(source_url, allowed_hosts=source_hosts):
            raise SpectrumRegistryError(f"Unsafe source_page_url for '{entry_id}'.")
        if image_url in seen_urls:
            raise SpectrumRegistryError(f"Duplicate spectrum image_url '{image_url}'.")
        seen_urls.add(image_url)
        instrument = entry.get("instrument")
        if instrument is not None and not isinstance(instrument, str):
            raise SpectrumRegistryError(f"Spectrum entry '{entry_id}' instrument must be string.")


def _identity_keys(target: dict[str, Any] | None) -> list[str]:
    keys: list[str] = []
    for raw in csr.selection_identity_strings(target):
        for key in csr._catalog_identity_keys(raw):
            if key and key not in keys:
                keys.append(key)
    return keys


def _entry_matches(entry: dict[str, Any], target_ids: list[str], identity_keys: list[str]) -> bool:
    id_set = set(entry.get("target_ids") or [])
    if any(tid in id_set for tid in target_ids):
        return True
    alias_keys: set[str] = set()
    for alias in entry.get("target_aliases") or []:
        alias_keys.update(csr._catalog_identity_keys(alias))
    return any(key in alias_keys for key in identity_keys)


def _present(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": entry["id"],
        "title": entry["title"],
        "wavelength": entry["wavelength"],
        "relevance": entry["relevance"],
        "relevance_label": RELEVANCE_LABELS.get(entry["relevance"], entry["relevance"]),
        "observatory": entry["observatory"],
        "instrument": entry.get("instrument") or "",
        "short_explanation": entry["short_explanation"],
        "image_url": entry["image_url"],
        "source_page_url": entry["source_page_url"],
        "credits": entry["credits"],
    }


def match_spectrum_for_target(
    target: dict[str, Any] | None,
    *,
    allow_all_sky: bool = True,
) -> dict[str, Any]:
    """Return curated spectrum options for the current target."""
    reg = load_registry()
    target_ids = csr.resolve_target_ids_from_selection(target)
    identity_keys = _identity_keys(target)

    exact: list[dict[str, Any]] = []
    region: list[dict[str, Any]] = []
    all_sky: list[dict[str, Any]] = []

    for entry in enabled_entries():
        relevance = entry["relevance"]
        if relevance == "all_sky_context":
            if allow_all_sky:
                all_sky.append(_present(entry))
            continue
        if not _entry_matches(entry, target_ids, identity_keys):
            continue
        presented = _present(entry)
        if relevance == "exact_target":
            exact.append(presented)
        elif relevance == "target_region":
            region.append(presented)

    matched = exact + region
    options = matched + all_sky
    if matched:
        primary = matched[0]
        relevance = primary["relevance"]
        empty_message = None
    elif all_sky:
        primary = all_sky[0]
        relevance = "all_sky_context"
        empty_message = reg.get("empty_exact_message")
    else:
        primary = None
        relevance = None
        empty_message = reg.get("empty_exact_message")

    return {
        "ok": True,
        "gallery_title": reg.get("gallery_title") or "Spectrum Gallery",
        "gallery_subtitle": reg.get("gallery_subtitle")
        or "See the universe in another light.",
        "relevance": relevance,
        "empty_exact_message": empty_message,
        "primary": primary,
        "options": options,
        "matched_count": len(matched),
        "all_sky_count": len(all_sky),
    }
