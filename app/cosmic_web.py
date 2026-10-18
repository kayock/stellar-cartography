"""
cosmic_web.py

Cosmic Web scientific exhibit helpers.

Registry loading, illustrative structure-growth state, narration, and Stellarium
sky-anchor metadata. No hard-coded deployment hosts; Stellarium URL stays external.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

REGISTRY_PATH = Path(__file__).resolve().parent / "data" / "cosmic_web_registry.json"
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
CLASSIFICATIONS = frozenset({"illustration", "observation", "reconstruction", "simulation"})


class CosmicWebError(ValueError):
    """Invalid Cosmic Web registry or request."""


def _require_str(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CosmicWebError(f"Missing or invalid '{field}'.")
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
        raise CosmicWebError("Registry must be an object.")
    for field in ("id", "title", "science", "structure_demo", "objects", "narration"):
        if field not in raw:
            raise CosmicWebError(f"Registry missing '{field}'.")
    if raw.get("id") != "cosmic_web":
        raise CosmicWebError("Registry id must be 'cosmic_web'.")
    science = raw["science"]
    for key in (
        "what_is",
        "not_uniform",
        "gravity_dark_matter",
        "filaments_nodes_voids",
        "observation_vs_simulation",
        "takeaway",
    ):
        _require_str(science.get(key), f"science.{key}")
    narration = raw["narration"]
    for key in (
        "intro",
        "fluctuations",
        "gravity",
        "filaments",
        "voids",
        "surveys",
        "night_sky",
        "closing",
    ):
        _require_str(narration.get(key), f"narration.{key}")
    demo = raw["structure_demo"]
    if not isinstance(demo, dict) or demo.get("kind") != "illustrative":
        raise CosmicWebError("structure_demo.kind must be 'illustrative'.")
    steps = demo.get("time_steps")
    if not isinstance(steps, list) or len(steps) < 2:
        raise CosmicWebError("structure_demo.time_steps must list at least two steps.")
    for step in steps:
        if not isinstance(step, dict) or not _ID_RE.match(str(step.get("id") or "")):
            raise CosmicWebError("Invalid structure time step id.")
        if not isinstance(step.get("progress"), (int, float)):
            raise CosmicWebError("Structure time step progress must be numeric.")
    allowed = {h.lower() for h in (raw.get("provenance_hosts_allowed") or [])}
    seen: set[str] = set()
    enabled = 0
    for obj in raw["objects"]:
        _validate_object(obj, allowed)
        oid = obj["id"]
        if oid in seen:
            raise CosmicWebError(f"Duplicate object id '{oid}'.")
        seen.add(oid)
        if obj.get("enabled"):
            enabled += 1
    if enabled < 1:
        raise CosmicWebError("At least one enabled cosmic-web object is required.")


def _validate_object(obj: Any, allowed_hosts: set[str]) -> None:
    if not isinstance(obj, dict):
        raise CosmicWebError("Each object must be an object.")
    oid = obj.get("id")
    if not isinstance(oid, str) or not _ID_RE.match(oid):
        raise CosmicWebError("Invalid object id.")
    _require_str(obj.get("name"), "name")
    _require_str(obj.get("stellarium_search"), "stellarium_search")
    _require_str(obj.get("summary"), "summary")
    media = obj.get("media")
    if not isinstance(media, dict):
        raise CosmicWebError(f"Object '{oid}' missing media.")
    classification = _require_str(media.get("classification"), "media.classification").lower()
    if classification not in CLASSIFICATIONS:
        raise CosmicWebError(f"Object '{oid}' media.classification invalid.")
    page = _require_str(media.get("source_page_url"), "media.source_page_url")
    image = _require_str(media.get("image_url"), "media.image_url")
    _require_str(media.get("credit"), "media.credit")
    if allowed_hosts:
        if not _host_ok(page, allowed_hosts):
            raise CosmicWebError(f"Object '{oid}' source_page_url host not allowlisted.")
        if not _host_ok(image, allowed_hosts):
            raise CosmicWebError(f"Object '{oid}' image_url host not allowlisted.")
    sources = obj.get("sources")
    if not isinstance(sources, list) or not sources:
        raise CosmicWebError(f"Object '{oid}' needs sources.")
    for src in sources:
        if not isinstance(src, dict):
            raise CosmicWebError(f"Object '{oid}' has invalid source entry.")
        _require_str(src.get("title"), "source.title")
        url = _require_str(src.get("url"), "source.url")
        if allowed_hosts and not _host_ok(url, allowed_hosts):
            raise CosmicWebError(f"Object '{oid}' source url host not allowlisted.")
        cls = (src.get("classification") or "").lower()
        if cls and cls not in CLASSIFICATIONS:
            raise CosmicWebError(f"Object '{oid}' source classification invalid.")


def list_payload() -> dict[str, Any]:
    reg = load_registry()
    return {
        "ok": True,
        "id": reg["id"],
        "title": reg["title"],
        "subtitle": reg.get("subtitle"),
        "description": reg.get("description"),
        "estimated_minutes": reg.get("estimated_minutes"),
        "source_note": reg.get("source_note"),
        "illustrative_disclaimer": reg.get("illustrative_disclaimer"),
        "classification_legend": reg.get("classification_legend") or {},
        "science": reg["science"],
        "narration_keys": list((reg.get("narration") or {}).keys()),
        "structure_demo": {
            "kind": reg["structure_demo"]["kind"],
            "label": reg["structure_demo"].get("label"),
            "layers": list(reg["structure_demo"].get("layers") or []),
            "step_count": len(reg["structure_demo"]["time_steps"]),
        },
        "objects": [_object_summary(o) for o in reg["objects"] if o.get("enabled")],
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
        return {"ok": False, "error": "Unknown cosmic-web object."}
    return {
        "ok": True,
        "object": _object_public(obj),
        "illustrative_disclaimer": load_registry().get("illustrative_disclaimer"),
        "classification_legend": load_registry().get("classification_legend") or {},
        "audio_autoplay": False,
    }


def structure_state(
    step_id: str | None = None,
    progress: float | None = None,
    layers: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Illustrative structure-growth visualization state."""
    demo = load_registry()["structure_demo"]
    steps = list(demo["time_steps"])
    chosen = None
    if step_id:
        for step in steps:
            if step["id"] == step_id:
                chosen = step
                break
        if chosen is None:
            return {"ok": False, "error": "Unknown structure step.", "kind": "illustrative"}
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

    default_show = dict(chosen.get("show") or {})
    active_layers = {
        "galaxies": True,
        "filaments": True,
        "nodes": True,
        "voids": True,
    }
    if isinstance(layers, dict):
        for key in active_layers:
            if key in layers:
                active_layers[key] = bool(layers[key])
    else:
        for key, value in default_show.items():
            if key in active_layers:
                active_layers[key] = bool(value)

    return {
        "ok": True,
        "kind": "illustrative",
        "label": demo.get("label") or "ILLUSTRATIVE COSMIC WEB",
        "classification": "illustration",
        "disclaimer": load_registry().get("illustrative_disclaimer"),
        "measured_reconstruction": False,
        "step": chosen,
        "layers": active_layers,
        "available_layers": list(demo.get("layers") or []),
        "seed_points": demo.get("seed_points") or [],
        "filament_paths": demo.get("filament_paths") or [],
        "node_points": demo.get("node_points") or [],
        "void_regions": demo.get("void_regions") or [],
        "time_steps": [
            {"id": s["id"], "label": s["label"], "progress": s["progress"]} for s in steps
        ],
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
        "intro": "The Universe is not random",
        "fluctuations": "From small differences",
        "gravity": "Gravity and dark matter",
        "filaments": "Filaments and nodes",
        "voids": "The great voids",
        "surveys": "How surveys map the web",
        "night_sky": "Looking from Earth",
        "closing": "Takeaway",
    }
    return {
        "ok": True,
        "kind": "cosmic_web",
        "segment": key,
        "title": title_map.get(key, key),
        "text": narration[key],
        "listen_available": True,
        "audio_autoplay": False,
        "feature_flag": "narration_hook",
    }


def focus_request(object_id: str | None) -> dict[str, Any]:
    obj = object_by_id(object_id)
    if not obj:
        return {"ok": False, "error": "Unknown cosmic-web object.", "stellarium_required": False}
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
        "role": "sky_anchor",
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
    if hasattr(sel, "__dict__") and not isinstance(sel, dict):
        payload = {
            "name": getattr(sel, "name", None),
            "alt_name": getattr(sel, "alt_name", None),
        }
    if not isinstance(payload, dict):
        return names
    for key in ("name", "alt_name", "localized-name", "english-name"):
        value = payload.get(key)
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
    if stellarium_client is None or not hasattr(stellarium_client, "focus_object"):
        return {
            **meta,
            "focused": False,
            "fov_set": False,
            "connected": False,
            "message": "Stellarium is unavailable; exhibit content still works.",
        }
    posted = False
    fov_set = False
    try:
        posted = bool(stellarium_client.focus_object(meta["stellarium_search"]))
        fov = meta.get("stellarium_fov_deg")
        if posted and fov is not None and hasattr(stellarium_client, "set_fov"):
            fov_set = bool(stellarium_client.set_fov(float(fov)))
    except Exception as exc:  # noqa: BLE001
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
        message = (
            "Sky anchor focused in Stellarium."
            if match_mode != "host_sky"
            else "Host-sky anchor focused in Stellarium."
        )
    elif posted:
        message = (
            "Stellarium accepted the focus command but the selection did not match. "
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
    media = obj.get("media") or {}
    return {
        "id": obj["id"],
        "name": obj["name"],
        "short_name": obj.get("short_name") or obj["name"],
        "object_type": obj.get("object_type"),
        "structure_role": obj.get("structure_role"),
        "stellarium_search": obj["stellarium_search"],
        "stellarium_fov_deg": obj.get("stellarium_fov_deg"),
        "stellarium_match_mode": obj.get("stellarium_match_mode") or "exact",
        "constellation": obj.get("constellation"),
        "summary": obj["summary"],
        "media_title": media.get("title"),
        "media_classification": media.get("classification"),
        "media_organization": media.get("organization"),
    }


def _object_public(obj: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": obj["id"],
        "name": obj["name"],
        "short_name": obj.get("short_name") or obj["name"],
        "object_type": obj.get("object_type"),
        "structure_role": obj.get("structure_role"),
        "stellarium_search": obj["stellarium_search"],
        "stellarium_fov_deg": obj.get("stellarium_fov_deg"),
        "stellarium_match_mode": obj.get("stellarium_match_mode") or "exact",
        "stellarium_note": obj.get("stellarium_note"),
        "constellation": obj.get("constellation"),
        "summary": obj["summary"],
        "why_suitable": obj.get("why_suitable"),
        "teaching_points": obj.get("teaching_points") or [],
        "media": dict(obj.get("media") or {}),
        "sources": obj.get("sources") or [],
    }
