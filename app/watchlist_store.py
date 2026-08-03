"""
watchlist_store.py

Portable, user-owned JSON watchlist with versioned schema, atomic writes,
previous-valid-file backup, and safe recovery from malformed JSON.

Runtime data lives in ``runtime_data/tracked_objects.json`` beside the project
root (same directory as run.py). This path is excluded from release packaging.
"""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
import time
from typing import Callable, Optional

logger = logging.getLogger("stellar_archive_bridge.watchlist_store")

SCHEMA_VERSION = 1
MAX_ENTRIES = 500
MAX_NOTE_LEN = 500
MAX_NAME_LEN = 120

_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

RUNTIME_RELATIVE_PATH = os.path.join("runtime_data", "tracked_objects.json")


def resolve_app_root(app_root: str | None = None) -> str:
    """Return the absolute application root (directory containing run.py)."""
    if app_root:
        return os.path.abspath(app_root)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))


def default_runtime_dir(app_root: str | None = None) -> str:
    return os.path.join(resolve_app_root(app_root), "runtime_data")


def watchlist_path(app_root: str | None = None) -> str:
    return os.path.join(default_runtime_dir(app_root), "tracked_objects.json")


def watchlist_relative_path() -> str:
    return RUNTIME_RELATIVE_PATH.replace("\\", "/")


def backup_path(app_root: str | None = None) -> str:
    return os.path.join(default_runtime_dir(app_root), "tracked_objects.json.bak")


def empty_document() -> dict:
    return {"schema_version": SCHEMA_VERSION, "entries": []}


def sanitize_note(value: object) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    text = _CONTROL_CHAR_RE.sub("", value.strip())
    if len(text) > MAX_NOTE_LEN:
        text = text[: MAX_NOTE_LEN - 1] + "…"
    return text


def sanitize_text(value: object, max_len: int = 500) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    text = _CONTROL_CHAR_RE.sub("", value.strip())
    if not text:
        return None
    if len(text) > max_len:
        text = text[: max_len - 1] + "…"
    return text


def sanitize_display_name(value: object) -> str:
    if value is None:
        return "Unnamed target"
    if not isinstance(value, str):
        value = str(value)
    text = _CONTROL_CHAR_RE.sub("", value.strip())
    if not text:
        return "Unnamed target"
    if len(text) > MAX_NAME_LEN:
        text = text[: MAX_NAME_LEN - 1] + "…"
    return text


def _normalize_entry(entry: dict, now_iso: str | None = None) -> dict | None:
    if not isinstance(entry, dict):
        return None
    now = now_iso or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    try:
        ra = float(entry.get("saved_ra_deg"))
        dec = float(entry.get("saved_dec_deg"))
    except (TypeError, ValueError):
        return None
    watchlist_id = entry.get("watchlist_id")
    if not isinstance(watchlist_id, str) or not watchlist_id.strip():
        watchlist_id = f"wl_{int(time.time() * 1000)}"
    normalized = {
        "watchlist_id": watchlist_id.strip()[:64],
        "display_name": sanitize_display_name(entry.get("display_name")),
        "normalized_object_type": sanitize_display_name(entry.get("normalized_object_type") or "unknown"),
        "source_identifier": sanitize_display_name(entry.get("source_identifier") or "") or None,
        "saved_ra_deg": ra,
        "saved_dec_deg": dec,
        "coordinate_source": sanitize_display_name(entry.get("coordinate_source") or "unknown"),
        "date_added": sanitize_display_name(entry.get("date_added") or now) or now,
        "last_refreshed": entry.get("last_refreshed"),
        "favorite": bool(entry.get("favorite")),
        "personal_note": sanitize_note(entry.get("personal_note")),
        "featured_kind": entry.get("featured_kind"),
        "provider_identifiers": entry.get("provider_identifiers") if isinstance(entry.get("provider_identifiers"), dict) else {},
    }
    if normalized["featured_kind"] not in (None, "apophis"):
        normalized["featured_kind"] = None
    cache = entry.get("tracker_cache")
    if normalized["featured_kind"] == "apophis" and isinstance(cache, dict):
        normalized["tracker_cache"] = _normalize_tracker_cache(cache)
    else:
        normalized["tracker_cache"] = None
    return normalized


def _normalize_tracker_cache(cache: dict) -> dict | None:
    if cache.get("kind") != "apophis":
        return None
    summary = cache.get("summary")
    if not isinstance(summary, dict):
        return None
    return {
        "kind": "apophis",
        "retrieved_at": sanitize_text(cache.get("retrieved_at"), max_len=40),
        "summary": _normalize_apophis_summary(summary),
    }


def _normalize_apophis_summary(summary: dict) -> dict:
    """Bounded Apophis summary safe for JSON persistence."""
    ephem = summary.get("ephemeris") if isinstance(summary.get("ephemeris"), dict) else {}
    return {
        "ok": bool(summary.get("ok")),
        "designation": sanitize_text(summary.get("designation"), max_len=40),
        "name": sanitize_text(summary.get("name"), max_len=80),
        "countdown_days": summary.get("countdown_days") if isinstance(summary.get("countdown_days"), int) else None,
        "encounter_date": sanitize_text(summary.get("encounter_date"), max_len=40),
        "encounter_date_unavailable": bool(summary.get("encounter_date_unavailable")),
        "nominal_close_approach_distance_au": summary.get("nominal_close_approach_distance_au"),
        "retrieved_at": sanitize_text(summary.get("retrieved_at"), max_len=40),
        "source_agency": sanitize_text(summary.get("source_agency"), max_len=40),
        "risk_status_available": bool(summary.get("risk_status_available")),
        "risk_status_notice": sanitize_text(summary.get("risk_status_notice"), max_len=300),
        "countdown_notice": sanitize_text(summary.get("countdown_notice"), max_len=300),
        "observer_context": summary.get("observer_context") if isinstance(summary.get("observer_context"), dict) else None,
        "observer_privacy_notice": sanitize_text(summary.get("observer_privacy_notice"), max_len=300),
        "source_links": summary.get("source_links") if isinstance(summary.get("source_links"), dict) else {},
        "ephemeris": {
            "ok": bool(ephem.get("ok")),
            "ra_deg": ephem.get("ra_deg"),
            "dec_deg": ephem.get("dec_deg"),
            "distance_au": ephem.get("distance_au"),
            "epoch": sanitize_text(ephem.get("epoch"), max_len=40),
            "error": sanitize_text(ephem.get("error"), max_len=200),
        }
        if isinstance(ephem, dict)
        else None,
        "ephemeris_epoch": sanitize_text(summary.get("ephemeris_epoch"), max_len=40),
        "error": sanitize_text(summary.get("error"), max_len=200),
    }


def apophis_summary_from_api(api: dict) -> dict:
    """Extract a bounded summary dict from a live Apophis API response."""
    if not isinstance(api, dict):
        return {"ok": False, "error": "Invalid Apophis response."}
    return _normalize_apophis_summary(api)


def duplicate_key(entry: dict) -> str:
    if entry.get("featured_kind") == "apophis":
        return "featured:apophis"
    if entry.get("source_identifier"):
        return f"id:{entry['source_identifier'].lower()}"
    ra = round(float(entry["saved_ra_deg"]), 4)
    dec = round(float(entry["saved_dec_deg"]), 4)
    obj_type = (entry.get("normalized_object_type") or "unknown").lower()
    return f"coord:{obj_type}:{ra}:{dec}"


def merge_duplicate(existing: dict, incoming: dict) -> dict:
    merged = dict(existing)
    if incoming.get("personal_note"):
        merged["personal_note"] = incoming["personal_note"]
    merged["favorite"] = bool(existing.get("favorite")) or bool(incoming.get("favorite"))
    if incoming.get("display_name") and incoming["display_name"] != "Unnamed target":
        merged["display_name"] = incoming["display_name"]
    merged["saved_ra_deg"] = incoming["saved_ra_deg"]
    merged["saved_dec_deg"] = incoming["saved_dec_deg"]
    merged["coordinate_source"] = incoming.get("coordinate_source") or merged.get("coordinate_source")
    merged["last_refreshed"] = incoming.get("last_refreshed") or merged.get("last_refreshed")
    if incoming.get("tracker_cache"):
        merged["tracker_cache"] = incoming["tracker_cache"]
    if incoming.get("provider_identifiers"):
        merged["provider_identifiers"] = {
            **(merged.get("provider_identifiers") or {}),
            **incoming["provider_identifiers"],
        }
    return merged


def normalize_document(payload: object) -> dict:
    if not isinstance(payload, dict):
        return empty_document()
    version = payload.get("schema_version")
    if version != SCHEMA_VERSION:
        logger.info("Watchlist schema_version=%s migrated to %s", version, SCHEMA_VERSION)
    entries_in = payload.get("entries")
    if not isinstance(entries_in, list):
        entries_in = []
    seen: dict[str, dict] = {}
    for raw in entries_in[:MAX_ENTRIES]:
        entry = _normalize_entry(raw)
        if not entry:
            continue
        key = duplicate_key(entry)
        if key in seen:
            seen[key] = merge_duplicate(seen[key], entry)
        else:
            seen[key] = entry
    return {"schema_version": SCHEMA_VERSION, "entries": list(seen.values())}


def _read_file(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_watchlist(app_root: str | None = None) -> dict:
    result = load_watchlist_result(app_root)
    if result.get("document") is not None:
        return result["document"]
    return empty_document()


def load_watchlist_result(app_root: str | None = None) -> dict:
    root = resolve_app_root(app_root)
    path = watchlist_path(root)
    rel = watchlist_relative_path()
    bak = backup_path(root)

    if not os.path.isfile(path):
        doc = empty_document()
        return {
            "ok": True,
            "status": "empty",
            "document": doc,
            "entry_count": 0,
            "storage_path": path,
            "storage_path_relative": rel,
            "recovered_from_backup": False,
            "error": None,
        }

    try:
        doc = normalize_document(_read_file(path))
        return {
            "ok": True,
            "status": "loaded",
            "document": doc,
            "entry_count": len(doc.get("entries", [])),
            "storage_path": path,
            "storage_path_relative": rel,
            "recovered_from_backup": False,
            "error": None,
        }
    except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
        logger.warning("Watchlist primary file malformed; attempting backup recovery")

    if os.path.isfile(bak):
        try:
            doc = normalize_document(_read_file(bak))
            save_watchlist(doc, app_root=root)
            return {
                "ok": True,
                "status": "recovered_from_backup",
                "document": doc,
                "entry_count": len(doc.get("entries", [])),
                "storage_path": path,
                "storage_path_relative": rel,
                "recovered_from_backup": True,
                "error": None,
            }
        except (json.JSONDecodeError, OSError, UnicodeDecodeError):
            logger.warning("Watchlist backup also malformed")

    return {
        "ok": False,
        "status": "load_failed",
        "document": None,
        "entry_count": 0,
        "storage_path": path,
        "storage_path_relative": rel,
        "recovered_from_backup": False,
        "error": "Could not load the watchlist file or its backup.",
    }


def save_watchlist(
    document: dict,
    app_root: str | None = None,
    *,
    fsync: Callable[[int], None] | None = None,
) -> dict:
    normalized = normalize_document(document)
    runtime_dir = default_runtime_dir(app_root)
    os.makedirs(runtime_dir, exist_ok=True)
    path = watchlist_path(app_root)
    bak = backup_path(app_root)

    if os.path.isfile(path):
        try:
            with open(path, "rb") as src, open(bak, "wb") as dst:
                dst.write(src.read())
        except OSError:
            logger.warning("Could not write watchlist backup", exc_info=True)

    fd, tmp_path = tempfile.mkstemp(prefix="tracked_objects_", suffix=".json", dir=runtime_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(normalized, f, indent=2, sort_keys=True)
            f.write("\n")
            f.flush()
            if fsync:
                fsync(f.fileno())
        os.replace(tmp_path, path)
    except OSError:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
    return normalized


def entry_from_target(target: dict, *, featured_kind: str | None = None) -> dict:
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    provider: dict = {}
    if featured_kind == "apophis":
        provider = {"jpl_sbdb": "99942", "designation": "99942", "name": "Apophis"}
    return {
        "watchlist_id": f"wl_{int(time.time() * 1000)}",
        "display_name": sanitize_display_name(target.get("name")),
        "normalized_object_type": sanitize_display_name(target.get("object_type") or target.get("object_category") or "unknown"),
        "source_identifier": sanitize_display_name(target.get("alt_name") or "") or None,
        "saved_ra_deg": float(target["ra_deg"]),
        "saved_dec_deg": float(target["dec_deg"]),
        "coordinate_source": sanitize_display_name(target.get("source") or "stellarium"),
        "date_added": now,
        "last_refreshed": None,
        "favorite": False,
        "personal_note": "",
        "featured_kind": featured_kind,
        "provider_identifiers": provider,
    }


def build_apophis_seed_entry() -> dict:
    return entry_from_target(
        {
            "name": "99942 Apophis",
            "object_type": "asteroid",
            "alt_name": "2004 MN4",
            "ra_deg": 0.0,
            "dec_deg": 0.0,
            "source": "featured_tracker",
        },
        featured_kind="apophis",
    )
