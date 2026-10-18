"""Cosmic Dawn Special — timeline, labs, objects, narration, Stellarium anchors.

No hard-coded deployment hosts. Stellarium shows present-day sky only.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

_REGISTRY_PATH = Path(__file__).resolve().parent / "data" / "cosmic_dawn_registry.json"
_registry_cache: dict[str, Any] | None = None


class CosmicDawnError(ValueError):
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
        raise CosmicDawnError(f"Missing {label}")
    return value.strip()


def _validate(raw: dict[str, Any]) -> None:
    for key in (
        "id",
        "title",
        "objects",
        "timeline_lab",
        "redshift_lab",
        "reionization_lab",
        "structure_lab",
        "twenty_one_cm",
        "narration",
        "classification_legend",
    ):
        if key not in raw:
            raise CosmicDawnError(f"Registry missing {key}")
    if raw.get("id") != "cosmic_dawn":
        raise CosmicDawnError("Registry id must be cosmic_dawn")
    objs = raw["objects"]
    if not isinstance(objs, list) or len(objs) < 4:
        raise CosmicDawnError("Need at least four cosmic-dawn objects")
    ids = set()
    for obj in objs:
        oid = _require_str(obj.get("id"), "object.id")
        if oid in ids:
            raise CosmicDawnError(f"Duplicate object id {oid}")
        ids.add(oid)
        media = obj.get("media") or {}
        _require_str(media.get("classification"), f"{oid}.media.classification")
        _require_str(media.get("image_url"), f"{oid}.media.image_url")
    if raw["twenty_one_cm"].get("classification") not in ("theoretical_model", "illustration"):
        raise CosmicDawnError("21-cm section must stay theoretical/illustration-level")
    for key in (
        "lookback",
        "recombination",
        "cmb",
        "dark_ages",
        "first_stars",
        "first_galaxies",
        "reionization",
        "jwst",
        "twenty_one_cm",
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
        "timeline_lab": {
            "label": reg["timeline_lab"].get("label"),
            "classification": reg["timeline_lab"].get("classification"),
            "disclaimer": reg["timeline_lab"].get("disclaimer"),
            "epochs": [
                {"id": e["id"], "label": e["label"], "progress": e["progress"], "z_approx": e.get("z_approx")}
                for e in reg["timeline_lab"].get("epochs") or []
            ],
        },
        "redshift_lab": reg.get("redshift_lab"),
        "reionization_lab": {
            "label": reg["reionization_lab"].get("label"),
            "classification": reg["reionization_lab"].get("classification"),
            "disclaimer": reg["reionization_lab"].get("disclaimer"),
            "stages": [
                {"id": s["id"], "label": s["label"], "progress": s["progress"]}
                for s in reg["reionization_lab"].get("stages") or []
            ],
        },
        "structure_lab": reg.get("structure_lab"),
        "twenty_one_cm": reg.get("twenty_one_cm"),
    }


def object_payload(object_id: str | None) -> dict[str, Any]:
    obj = object_by_id(object_id)
    if not obj:
        return {"ok": False, "error": "Unknown cosmic-dawn object."}
    return {
        "ok": True,
        "object": obj,
        "classification_legend": load_registry().get("classification_legend"),
        "stellarium_is_present_day_only": True,
    }


def timeline_state(epoch_id: str | None = None, progress: float | None = None) -> dict[str, Any]:
    lab = load_registry()["timeline_lab"]
    epochs = list(lab.get("epochs") or [])
    if not epochs:
        return {"ok": False, "error": "No timeline epochs configured."}
    chosen = epochs[0]
    if epoch_id:
        for e in epochs:
            if e.get("id") == epoch_id:
                chosen = e
                break
        else:
            return {"ok": False, "error": "Unknown timeline epoch."}
    elif progress is not None:
        try:
            pval = float(progress)
        except (TypeError, ValueError):
            return {"ok": False, "error": "progress must be a number."}
        pval = max(0.0, min(1.0, pval))
        chosen = min(epochs, key=lambda s: abs(float(s["progress"]) - pval))
    return {
        "ok": True,
        "kind": "illustrative",
        "classification": "illustration",
        "label": lab.get("label"),
        "disclaimer": lab.get("disclaimer"),
        "epoch": chosen,
        "epochs": [
            {
                "id": e["id"],
                "label": e["label"],
                "progress": e["progress"],
                "z_approx": e.get("z_approx"),
                "age_note": e.get("age_note"),
            }
            for e in epochs
        ],
        "approximate": True,
    }


def redshift_state(z: float | None = None) -> dict[str, Any]:
    lab = load_registry()["redshift_lab"]
    try:
        zval = 6.0 if z is None else float(z)
    except (TypeError, ValueError):
        return {"ok": False, "error": "z must be a number."}
    zval = max(0.0, min(20.0, zval))
    # Very rough teaching scale factor a = 1/(1+z); not a distance calculator
    scale = 1.0 / (1.0 + zval)
    lookback_hint = "local Universe" if zval < 0.5 else ("recent galaxies" if zval < 2 else ("early galaxies" if zval < 10 else "near Cosmic Dawn frontier"))
    return {
        "ok": True,
        "kind": "theoretical_model",
        "classification": "theoretical_model",
        "label": lab.get("label"),
        "disclaimer": lab.get("disclaimer"),
        "points": lab.get("points"),
        "z": zval,
        "scale_factor_teaching": round(scale, 4),
        "lookback_hint": lookback_hint,
        "not_ordinary_doppler_only": True,
        "note": "Teaching aid only — not a precision cosmology calculator.",
    }


def reionization_state(stage_id: str | None = None, progress: float | None = None) -> dict[str, Any]:
    lab = load_registry()["reionization_lab"]
    stages = list(lab.get("stages") or [])
    chosen = stages[0]
    if stage_id:
        for s in stages:
            if s.get("id") == stage_id:
                chosen = s
                break
        else:
            return {"ok": False, "error": "Unknown reionization stage."}
    elif progress is not None:
        try:
            pval = float(progress)
        except (TypeError, ValueError):
            return {"ok": False, "error": "progress must be a number."}
        pval = max(0.0, min(1.0, pval))
        chosen = min(stages, key=lambda s: abs(float(s["progress"]) - pval))
    p = float(chosen["progress"])
    bubbles = []
    n = 1 + int(p * 8)
    for i in range(n):
        ang = (i / max(n, 1)) * 2 * math.pi
        r = 4 + p * 10
        bubbles.append(
            {
                "x": round(50 + 22 * math.cos(ang) * (0.3 + p), 3),
                "y": round(50 + 18 * math.sin(ang) * (0.3 + p), 3),
                "r": round(r * (0.5 + 0.08 * i), 3),
            }
        )
    return {
        "ok": True,
        "kind": "illustrative",
        "classification": "illustration",
        "label": lab.get("label"),
        "disclaimer": lab.get("disclaimer"),
        "stage": chosen,
        "stages": [{"id": s["id"], "label": s["label"], "progress": s["progress"]} for s in stages],
        "bubbles": bubbles,
        "ionized_fraction_teaching": round(p, 3),
        "active_research": True,
    }


def structure_state(progress: float | None = None) -> dict[str, Any]:
    lab = load_registry()["structure_lab"]
    try:
        p = 0.4 if progress is None else float(progress)
    except (TypeError, ValueError):
        return {"ok": False, "error": "progress must be a number."}
    p = max(0.0, min(1.0, p))
    # Tiny synthetic density peaks that grow
    seeds = [(30, 40), (55, 55), (70, 35), (45, 70), (62, 62)]
    peaks = []
    for i, (x, y) in enumerate(seeds):
        amp = 2 + p * (6 + i)
        peaks.append({"x": x, "y": y, "r": round(amp, 3), "halo": p > 0.35})
    return {
        "ok": True,
        "kind": "illustrative",
        "classification": "illustration",
        "label": lab.get("label"),
        "disclaimer": lab.get("disclaimer"),
        "progress": p,
        "peaks": peaks,
        "related_special": lab.get("related_special"),
        "note": "Early-stage teaching field — open Cosmic Web Special for survey-scale structure.",
    }


def twenty_one_cm_payload() -> dict[str, Any]:
    block = load_registry()["twenty_one_cm"]
    return {
        "ok": True,
        **block,
        "detection_overstated": False,
        "conservative": True,
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
        return {"ok": False, "error": "Unknown cosmic-dawn object."}
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
        "role": "present_day_sky_anchor",
        "stellarium_shows_early_universe": False,
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
            "message": meta.get("stellarium_note")
            or "No optical Stellarium anchor—early-Universe content still works.",
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
        for n in names:
            nl = n.lower()
            for a in accepted:
                if a == nl or a in nl or nl in a:
                    matched = True
                    break
            if matched:
                break
    if matched:
        message = "Present-day sky anchor focused (not early-Universe rendering)."
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
        "kind": obj.get("kind"),
        "summary": obj.get("significance"),
        "stellarium_search": obj.get("stellarium_search"),
        "stellarium_match_mode": obj.get("stellarium_match_mode"),
        "media_classification": media.get("classification"),
        "media_title": media.get("title"),
    }
