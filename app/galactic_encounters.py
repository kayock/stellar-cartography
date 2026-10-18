"""Galactic Encounters Special — labs, objects, narration, Stellarium anchors.

No hard-coded deployment hosts.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

_REGISTRY_PATH = Path(__file__).resolve().parent / "data" / "galactic_encounters_registry.json"
_registry_cache: dict[str, Any] | None = None


class GalacticEncountersError(ValueError):
    pass


def reload_registry() -> dict[str, Any]:
    global _registry_cache
    _registry_cache = None
    return load_registry()


def load_registry() -> dict[str, Any]:
    global _registry_cache
    if _registry_cache is not None:
        return _registry_cache
    raw = json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))
    _validate(raw)
    _registry_cache = raw
    return raw


def _require_str(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GalacticEncountersError(f"Missing {label}")
    return value.strip()


def _validate(raw: dict[str, Any]) -> None:
    for key in (
        "id",
        "title",
        "objects",
        "encounter_lab",
        "tidal_lab",
        "stars_gas_lab",
        "merger_lab",
        "future_mw_m31",
        "narration",
        "classification_legend",
    ):
        if key not in raw:
            raise GalacticEncountersError(f"Registry missing {key}")
    if raw.get("id") != "galactic_encounters":
        raise GalacticEncountersError("Registry id must be galactic_encounters")
    objs = raw["objects"]
    if not isinstance(objs, list) or len(objs) < 4:
        raise GalacticEncountersError("Need at least four encounter objects")
    ids = set()
    for obj in objs:
        oid = _require_str(obj.get("id"), "object.id")
        if oid in ids:
            raise GalacticEncountersError(f"Duplicate object id {oid}")
        ids.add(oid)
        media = obj.get("media") or {}
        _require_str(media.get("classification"), f"{oid}.media.classification")
        _require_str(media.get("image_url"), f"{oid}.media.image_url")
    fut = raw["future_mw_m31"]
    if fut.get("classification") != "future_prediction":
        raise GalacticEncountersError("MW–M31 section must be future_prediction")
    for key in (
        "motion",
        "tides",
        "tails",
        "stars_gas",
        "antennae",
        "whirlpool",
        "major_minor",
        "remnants",
        "mw_m31",
        "closing",
    ):
        _require_str(raw["narration"].get(key), f"narration.{key}")


def object_by_id(object_id: str | None) -> dict[str, Any] | None:
    if not object_id:
        return None
    for obj in load_registry().get("objects") or []:
        if obj.get("id") == object_id:
            return obj
    return None


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
        "classification_legend": reg.get("classification_legend"),
        "science": reg.get("science"),
        "audio_autoplay": False,
        "narration_keys": list((reg.get("narration") or {}).keys()),
        "objects": [_object_summary(o) for o in reg["objects"]],
        "encounter_lab": {
            "label": reg["encounter_lab"].get("label"),
            "classification": reg["encounter_lab"].get("classification"),
            "disclaimer": reg["encounter_lab"].get("disclaimer"),
            "stages": [
                {"id": s["id"], "label": s["label"], "progress": s["progress"]}
                for s in reg["encounter_lab"].get("stages") or []
            ],
            "mass_ratios": reg["encounter_lab"].get("mass_ratios"),
            "orientations": reg["encounter_lab"].get("orientations"),
        },
        "tidal_lab": reg.get("tidal_lab"),
        "stars_gas_lab": reg.get("stars_gas_lab"),
        "merger_lab": reg.get("merger_lab"),
        "future_mw_m31": reg.get("future_mw_m31"),
    }


def object_payload(object_id: str | None) -> dict[str, Any]:
    obj = object_by_id(object_id)
    if not obj:
        return {"ok": False, "error": "Unknown galactic-encounter object."}
    return {
        "ok": True,
        "object": obj,
        "classification_legend": load_registry().get("classification_legend"),
    }


def encounter_state(
    stage_id: str | None = None,
    progress: float | None = None,
    mass_ratio_id: str | None = None,
    orientation_id: str | None = None,
) -> dict[str, Any]:
    lab = load_registry()["encounter_lab"]
    stages = list(lab.get("stages") or [])
    if not stages:
        return {"ok": False, "error": "No encounter stages configured."}
    chosen = stages[0]
    if stage_id:
        for s in stages:
            if s.get("id") == stage_id:
                chosen = s
                break
        else:
            return {"ok": False, "error": "Unknown encounter stage."}
    elif progress is not None:
        try:
            pval = float(progress)
        except (TypeError, ValueError):
            return {"ok": False, "error": "progress must be a number."}
        pval = max(0.0, min(1.0, pval))
        chosen = min(stages, key=lambda s: abs(float(s["progress"]) - pval))

    ratios = list(lab.get("mass_ratios") or [])
    ratio = ratios[0] if ratios else {"id": "equal", "ratio": 1.0, "label": "Equal"}
    if mass_ratio_id:
        for r in ratios:
            if r.get("id") == mass_ratio_id:
                ratio = r
                break
        else:
            return {"ok": False, "error": "Unknown mass ratio."}

    orients = list(lab.get("orientations") or [])
    orient = orients[0] if orients else {"id": "prograde", "label": "Prograde-style"}
    if orientation_id:
        for o in orients:
            if o.get("id") == orientation_id:
                orient = o
                break
        else:
            return {"ok": False, "error": "Unknown orientation."}

    p = float(chosen["progress"])
    # Pedagogical ellipse pair positions (not physics integration)
    sep = 38 - p * 28
    size_a = 10.0
    size_b = size_a / math.sqrt(float(ratio.get("ratio") or 1.0))
    stretch = 1.0 + p * (1.4 if orient.get("id") == "prograde" else 0.7)
    tail = max(0.0, (p - 0.35) * 40)
    return {
        "ok": True,
        "kind": "illustrative",
        "classification": "illustration",
        "label": lab.get("label"),
        "disclaimer": lab.get("disclaimer"),
        "stage": chosen,
        "stages": [{"id": s["id"], "label": s["label"], "progress": s["progress"]} for s in stages],
        "mass_ratio": ratio,
        "orientation": orient,
        "layout": {
            "separation": round(sep, 3),
            "size_a": round(size_a, 3),
            "size_b": round(size_b, 3),
            "stretch": round(stretch, 3),
            "tail_length": round(tail, 3),
            "bridge": p > 0.25,
        },
        "note": "Illustrative geometry only.",
    }


def tidal_state(strength: float | None = None) -> dict[str, Any]:
    lab = load_registry()["tidal_lab"]
    try:
        s = 0.65 if strength is None else float(strength)
    except (TypeError, ValueError):
        return {"ok": False, "error": "strength must be a number."}
    s = max(0.0, min(1.0, s))
    # Near vs far pull teaching vectors
    near_pull = 1.0 + s * 0.9
    far_pull = 1.0 - s * 0.45
    return {
        "ok": True,
        "kind": "illustrative",
        "classification": "illustration",
        "label": lab.get("label"),
        "disclaimer": lab.get("disclaimer"),
        "caption": lab.get("caption"),
        "strength": s,
        "near_side_pull": round(near_pull, 3),
        "far_side_pull": round(far_pull, 3),
        "differential": round(near_pull - far_pull, 3),
        "tail_extension": round(s * 22, 3),
        "scale_note": "Galaxy-scale tidal stretch — not black-hole horizon spaghettification.",
    }


def stars_gas_state(mode: str | None = None) -> dict[str, Any]:
    lab = load_registry()["stars_gas_lab"]
    modes = list(lab.get("modes") or [])
    chosen = modes[0]
    if mode:
        for m in modes:
            if m.get("id") == mode:
                chosen = m
                break
        else:
            return {"ok": False, "error": "Unknown stars/gas mode."}
    return {
        "ok": True,
        "kind": "illustrative",
        "classification": "illustration",
        "label": lab.get("label"),
        "mode": chosen,
        "modes": [{"id": m["id"], "label": m["label"]} for m in modes],
        "star_collision_likely": False,
        "gas_interaction_strong": chosen.get("id") in ("gas", "both"),
    }


def merger_state(mode: str | None = None) -> dict[str, Any]:
    lab = load_registry()["merger_lab"]
    modes = list(lab.get("modes") or [])
    chosen = modes[0]
    if mode:
        for m in modes:
            if m.get("id") == mode:
                chosen = m
                break
        else:
            return {"ok": False, "error": "Unknown merger mode."}
    return {
        "ok": True,
        "kind": "illustrative",
        "classification": "illustration",
        "mode": chosen,
        "modes": modes,
    }


def future_payload() -> dict[str, Any]:
    fut = load_registry()["future_mw_m31"]
    return {"ok": True, **fut}


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
    return {
        "ok": True,
        "segment": key,
        "text": narration[key],
        "audio_autoplay": False,
        "listen_available": True,
        "feature_flag": "narration_hook",
    }


def focus_request(object_id: str | None) -> dict[str, Any]:
    obj = object_by_id(object_id)
    if not obj:
        return {"ok": False, "error": "Unknown galactic-encounter object."}
    mode = obj.get("stellarium_match_mode") or "exact"
    return {
        "ok": True,
        "object_id": obj["id"],
        "name": obj.get("name"),
        "stellarium_search": obj.get("stellarium_search"),
        "stellarium_fov_deg": obj.get("stellarium_fov_deg"),
        "stellarium_match_mode": mode,
        "stellarium_note": obj.get("stellarium_note"),
        "stellarium_required": False,
        "role": "sky_anchor",
        "media_classification": (obj.get("media") or {}).get("classification"),
    }


def _selection_blob(stellarium_client: Any) -> dict[str, Any]:
    try:
        sel = stellarium_client.get_selection()
    except Exception:  # noqa: BLE001
        return {}
    if hasattr(sel, "__dict__") and not isinstance(sel, dict):
        return {
            "name": getattr(sel, "name", None),
            "alt_name": getattr(sel, "alt_name", None),
            "dec_deg": getattr(sel, "dec_deg", None),
            "ok": getattr(sel, "ok", None),
        }
    return sel if isinstance(sel, dict) else {}


def apply_focus(stellarium_client: Any, object_id: str | None) -> dict[str, Any]:
    meta = focus_request(object_id)
    if not meta.get("ok"):
        return meta
    obj = object_by_id(object_id) or {}
    mode = meta.get("stellarium_match_mode") or "exact"
    if mode == "unavailable" or not meta.get("stellarium_search"):
        return {
            **meta,
            "focused": False,
            "fov_set": False,
            "connected": stellarium_client is not None,
            "message": meta.get("stellarium_note") or "No Stellarium sky anchor.",
        }
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
        posted = bool(stellarium_client.focus_object(str(meta["stellarium_search"])))
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
    blob = _selection_blob(stellarium_client)
    names = []
    for key in ("name", "alt_name", "localized-name"):
        value = blob.get(key)
        if isinstance(value, str) and value.strip():
            names.append(value.strip())
    accepted = [n.lower() for n in (obj.get("stellarium_accept_names") or []) if isinstance(n, str)]
    matched = False
    if posted and accepted:
        lowered = {n.lower() for n in names}
        for a in accepted:
            if a in lowered or any(a in n.lower() for n in names):
                matched = True
                break
    if matched:
        message = "Sky anchor focused in Stellarium."
    elif posted:
        message = meta.get("stellarium_note") or "Focus posted but selection did not match expected host."
    else:
        message = "Stellarium did not select the object."
    return {
        **meta,
        "focused": matched,
        "focus_posted": posted,
        "fov_set": fov_set,
        "connected": True,
        "selection_names": names,
        "message": message,
    }


def _object_summary(obj: dict[str, Any]) -> dict[str, Any]:
    media = obj.get("media") or {}
    return {
        "id": obj["id"],
        "name": obj["name"],
        "short_name": obj.get("short_name") or obj["name"],
        "interaction_type": obj.get("interaction_type"),
        "summary": obj.get("significance"),
        "stellarium_search": obj.get("stellarium_search"),
        "stellarium_match_mode": obj.get("stellarium_match_mode"),
        "media_classification": media.get("classification"),
        "media_title": media.get("title"),
    }
