"""
light_echoes.py

Light Echoes scientific exhibit helpers.

Pure registry loading, illustrative geometry time-state, narration segments,
and Stellarium focus metadata. Network I/O stays in server.py / stellarium_client.
Does not hard-code deployment hosts; Stellarium URL remains an external config.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

REGISTRY_PATH = Path(__file__).resolve().parent / "data" / "light_echoes_registry.json"
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


class LightEchoesError(ValueError):
    """Invalid Light Echoes registry or request."""


def _require_str(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LightEchoesError(f"Missing or invalid '{field}'.")
    return value.strip()


def _host_ok(url: str, allowed: set[str]) -> bool:
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:  # noqa: BLE001
        return False
    return host in allowed


@lru_cache(maxsize=1)
def load_registry() -> dict[str, Any]:
    raw = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    validate_registry(raw)
    return raw


def reload_registry() -> dict[str, Any]:
    load_registry.cache_clear()
    return load_registry()


def validate_registry(raw: dict[str, Any]) -> None:
    if not isinstance(raw, dict):
        raise LightEchoesError("Registry must be an object.")
    for field in ("id", "title", "science", "geometry_demo", "objects", "narration"):
        if field not in raw:
            raise LightEchoesError(f"Registry missing '{field}'.")
    if raw.get("id") != "light_echoes":
        raise LightEchoesError("Registry id must be 'light_echoes'.")
    science = raw["science"]
    if not isinstance(science, dict):
        raise LightEchoesError("science must be an object.")
    for key in ("what_is", "not_matter_expansion", "geometry", "apparent_superluminal", "takeaway"):
        _require_str(science.get(key), f"science.{key}")
    narration = raw["narration"]
    if not isinstance(narration, dict):
        raise LightEchoesError("narration must be an object.")
    for key in ("intro", "geometry", "apparent_expansion", "examples", "closing"):
        _require_str(narration.get(key), f"narration.{key}")
    demo = raw["geometry_demo"]
    if not isinstance(demo, dict) or demo.get("kind") != "illustrative":
        raise LightEchoesError("geometry_demo.kind must be 'illustrative'.")
    steps = demo.get("time_steps")
    if not isinstance(steps, list) or len(steps) < 2:
        raise LightEchoesError("geometry_demo.time_steps must list at least two steps.")
    for step in steps:
        if not isinstance(step, dict) or not _ID_RE.match(str(step.get("id") or "")):
            raise LightEchoesError("Invalid geometry time step id.")
        if not isinstance(step.get("progress"), (int, float)):
            raise LightEchoesError("Geometry time step progress must be numeric.")
    objects = raw["objects"]
    if not isinstance(objects, list) or not objects:
        raise LightEchoesError("objects must be a non-empty list.")
    allowed = {h.lower() for h in (raw.get("provenance_hosts_allowed") or [])}
    seen: set[str] = set()
    enabled = 0
    for obj in objects:
        _validate_object(obj, allowed)
        oid = obj["id"]
        if oid in seen:
            raise LightEchoesError(f"Duplicate object id '{oid}'.")
        seen.add(oid)
        if obj.get("enabled"):
            enabled += 1
    if enabled < 1:
        raise LightEchoesError("At least one enabled light-echo object is required.")


def _validate_object(obj: Any, allowed_hosts: set[str]) -> None:
    if not isinstance(obj, dict):
        raise LightEchoesError("Each object must be an object.")
    oid = obj.get("id")
    if not isinstance(oid, str) or not _ID_RE.match(oid):
        raise LightEchoesError("Invalid object id.")
    _require_str(obj.get("name"), "name")
    _require_str(obj.get("stellarium_search"), "stellarium_search")
    _require_str(obj.get("summary"), "summary")
    media = obj.get("media")
    if not isinstance(media, dict):
        raise LightEchoesError(f"Object '{oid}' missing media.")
    page = _require_str(media.get("source_page_url"), "media.source_page_url")
    image = _require_str(media.get("image_url"), "media.image_url")
    _require_str(media.get("credit"), "media.credit")
    _require_str(media.get("organization"), "media.organization")
    if allowed_hosts:
        if not _host_ok(page, allowed_hosts):
            raise LightEchoesError(f"Object '{oid}' source_page_url host not allowlisted.")
        if not _host_ok(image, allowed_hosts):
            raise LightEchoesError(f"Object '{oid}' image_url host not allowlisted.")
    sources = obj.get("sources")
    if not isinstance(sources, list) or not sources:
        raise LightEchoesError(f"Object '{oid}' needs sources.")
    for src in sources:
        if not isinstance(src, dict):
            raise LightEchoesError(f"Object '{oid}' has invalid source entry.")
        _require_str(src.get("title"), "source.title")
        url = _require_str(src.get("url"), "source.url")
        if allowed_hosts and not _host_ok(url, allowed_hosts):
            raise LightEchoesError(f"Object '{oid}' source url host not allowlisted.")


def list_payload() -> dict[str, Any]:
    reg = load_registry()
    objects = [_object_summary(o) for o in reg["objects"] if o.get("enabled")]
    return {
        "ok": True,
        "id": reg["id"],
        "title": reg["title"],
        "subtitle": reg.get("subtitle"),
        "description": reg.get("description"),
        "estimated_minutes": reg.get("estimated_minutes"),
        "source_note": reg.get("source_note"),
        "illustrative_disclaimer": reg.get("illustrative_disclaimer"),
        "science": reg["science"],
        "narration_keys": list((reg.get("narration") or {}).keys()),
        "geometry_demo": {
            "kind": reg["geometry_demo"]["kind"],
            "label": reg["geometry_demo"].get("label"),
            "step_count": len(reg["geometry_demo"]["time_steps"]),
        },
        "objects": objects,
        "audio_autoplay": False,
    }


def object_by_id(object_id: str | None) -> dict[str, Any] | None:
    if not object_id or not isinstance(object_id, str):
        return None
    for obj in load_registry()["objects"]:
        if obj.get("id") == object_id and obj.get("enabled"):
            return obj
    return None


def object_payload(object_id: str | None) -> dict[str, Any]:
    obj = object_by_id(object_id)
    if not obj:
        return {"ok": False, "error": "Unknown light-echo object."}
    return {
        "ok": True,
        "object": _object_public(obj),
        "illustrative_disclaimer": load_registry().get("illustrative_disclaimer"),
        "audio_autoplay": False,
    }


def geometry_state(step_id: str | None = None, progress: float | None = None) -> dict[str, Any]:
    """Return illustrative geometry visualization state.

    Prefer step_id; otherwise snap to the nearest time_steps entry by progress.
    """
    demo = load_registry()["geometry_demo"]
    steps = list(demo["time_steps"])
    chosen = None
    if step_id:
        for step in steps:
            if step["id"] == step_id:
                chosen = step
                break
        if chosen is None:
            return {"ok": False, "error": "Unknown geometry step.", "kind": "illustrative"}
    else:
        if progress is None:
            chosen = steps[0]
        else:
            try:
                p = float(progress)
            except (TypeError, ValueError):
                return {"ok": False, "error": "progress must be a number.", "kind": "illustrative"}
            p = max(0.0, min(1.0, p))
            chosen = min(steps, key=lambda s: abs(float(s["progress"]) - p))
    return {
        "ok": True,
        "kind": "illustrative",
        "label": demo.get("label") or "ILLUSTRATIVE geometry",
        "disclaimer": load_registry().get("illustrative_disclaimer"),
        "step": chosen,
        "nodes": demo.get("nodes") or {},
        "paths": {
            "direct": ["source", "observer"],
            "echo_near": ["source", "near", "observer"],
            "echo_far": ["source", "far", "observer"],
            "echo_sheet": ["source", "sheet", "observer"],
        },
        "time_steps": [
            {"id": s["id"], "label": s["label"], "progress": s["progress"]} for s in steps
        ],
        "measured_reconstruction": False,
    }


def narration_segment(segment: str | None) -> dict[str, Any]:
    narration = load_registry().get("narration") or {}
    key = (segment or "").strip()
    if key not in narration:
        return {
            "ok": False,
            "error": "Unknown narration segment.",
            "audio_autoplay": False,
            "listen_available": False,
        }
    title_map = {
        "intro": "What is a light echo?",
        "geometry": "Source, dust, observer",
        "apparent_expansion": "Apparent expansion",
        "examples": "Real examples",
        "closing": "Takeaway",
    }
    text = narration[key]
    return {
        "ok": True,
        "kind": "light_echoes",
        "segment": key,
        "title": title_map.get(key, key),
        "text": text,
        "listen_available": True,
        "audio_autoplay": False,
        "feature_flag": "narration_hook",
    }


def focus_request(object_id: str | None) -> dict[str, Any]:
    """Metadata for focusing an object in Stellarium (caller performs I/O)."""
    obj = object_by_id(object_id)
    if not obj:
        return {"ok": False, "error": "Unknown light-echo object.", "stellarium_required": False}
    fov = obj.get("stellarium_fov_deg")
    return {
        "ok": True,
        "object_id": obj["id"],
        "name": obj["name"],
        "stellarium_search": obj["stellarium_search"],
        "stellarium_fov_deg": float(fov) if isinstance(fov, (int, float)) else None,
        "stellarium_match_mode": obj.get("stellarium_match_mode") or "exact",
        "stellarium_note": obj.get("stellarium_note"),
        "stellarium_required": False,
    }


def _selection_names(stellarium_client: Any) -> list[str]:
    names: list[str] = []
    if stellarium_client is None or not hasattr(stellarium_client, "get_selection"):
        return names
    try:
        sel = stellarium_client.get_selection()
    except Exception:  # noqa: BLE001
        return names
    payload = sel
    if hasattr(sel, "__dict__"):
        payload = {
            "name": getattr(sel, "name", None),
            "alt_name": getattr(sel, "alt_name", None),
        }
    elif not isinstance(sel, dict):
        return names
    for key in ("name", "alt_name", "localized-name", "english-name"):
        value = payload.get(key) if isinstance(payload, dict) else None
        if isinstance(value, str) and value.strip():
            names.append(value.strip())
    return names


def _names_match(observed: list[str], accepted: list[str]) -> bool:
    obs = {n.lower() for n in observed}
    acc = {n.lower() for n in accepted if isinstance(n, str)}
    return bool(obs.intersection(acc))


def apply_focus(stellarium_client: Any, object_id: str | None) -> dict[str, Any]:
    meta = focus_request(object_id)
    if not meta.get("ok"):
        return meta
    obj = object_by_id(object_id) or {}
    accepted = list(obj.get("stellarium_accept_names") or [meta["stellarium_search"]])
    note = obj.get("stellarium_note")
    match_mode = obj.get("stellarium_match_mode") or "exact"
    if note:
        meta["stellarium_note"] = note
    meta["stellarium_match_mode"] = match_mode
    if stellarium_client is None or not hasattr(stellarium_client, "focus_object"):
        return {
            **meta,
            "focused": False,
            "fov_set": False,
            "connected": False,
            "message": "Stellarium is unavailable; exhibit content still works.",
        }
    search = meta["stellarium_search"]
    posted = False
    fov_set = False
    try:
        posted = bool(stellarium_client.focus_object(search))
        fov = meta.get("stellarium_fov_deg")
        if posted and fov is not None and hasattr(stellarium_client, "set_fov"):
            fov_set = bool(stellarium_client.set_fov(float(fov)))
    except Exception as exc:  # noqa: BLE001 - graceful degrade
        return {
            **meta,
            "focused": False,
            "fov_set": False,
            "connected": False,
            "error": f"Stellarium focus failed: {exc}",
            "message": "Could not reach Stellarium; exhibit content still works.",
        }
    observed = _selection_names(stellarium_client)
    matched = _names_match(observed, accepted) if posted else False
    if matched:
        message = "Focused in Stellarium."
        if match_mode == "host_sky":
            message = "Focused host-sky context in Stellarium."
    elif posted:
        message = (
            "Stellarium accepted the focus command but the selection did not match the expected object. "
            + (note or "Exhibit content still works without an exact sky lock.")
        )
    else:
        message = "Stellarium did not select the object."
    return {
        **meta,
        "focused": matched,
        "focus_posted": posted,
        "fov_set": fov_set,
        "connected": True,
        "selection_names": observed,
        "message": message,
    }


def _object_summary(obj: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": obj["id"],
        "name": obj["name"],
        "short_name": obj.get("short_name") or obj["name"],
        "object_type": obj.get("object_type"),
        "stellarium_search": obj["stellarium_search"],
        "stellarium_fov_deg": obj.get("stellarium_fov_deg"),
        "stellarium_match_mode": obj.get("stellarium_match_mode") or "exact",
        "stellarium_note": obj.get("stellarium_note"),
        "constellation": obj.get("constellation"),
        "summary": obj["summary"],
        "key_years": obj.get("key_years") or [],
        "media_title": (obj.get("media") or {}).get("title"),
        "media_organization": (obj.get("media") or {}).get("organization"),
    }


def _object_public(obj: dict[str, Any]) -> dict[str, Any]:
    media = dict(obj.get("media") or {})
    return {
        "id": obj["id"],
        "name": obj["name"],
        "short_name": obj.get("short_name") or obj["name"],
        "object_type": obj.get("object_type"),
        "stellarium_search": obj["stellarium_search"],
        "stellarium_fov_deg": obj.get("stellarium_fov_deg"),
        "stellarium_match_mode": obj.get("stellarium_match_mode") or "exact",
        "stellarium_note": obj.get("stellarium_note"),
        "constellation": obj.get("constellation"),
        "summary": obj["summary"],
        "why_suitable": obj.get("why_suitable"),
        "key_years": obj.get("key_years") or [],
        "teaching_points": obj.get("teaching_points") or [],
        "media": media,
        "sources": obj.get("sources") or [],
    }
