"""Black Holes Special — registry, labs, objects, narration, Stellarium sky anchors.

No hard-coded deployment hosts. Stellarium URL comes from the server client.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

_REGISTRY_PATH = Path(__file__).resolve().parent / "data" / "black_holes_registry.json"
_registry_cache: dict[str, Any] | None = None

# Schwarzschild radius: Rs (km) ≈ 2.953 * (M / Msun)
_RS_KM_PER_MSUN = 2.9532213

_COMPARISON_SCALES = [
    {"id": "earth", "label": "Earth diameter", "km": 12742},
    {"id": "moon", "label": "Moon diameter", "km": 3475},
    {"id": "sun", "label": "Sun diameter", "km": 1_392_700},
    {"id": "au", "label": "1 astronomical unit", "km": 149_597_870.7},
    {"id": "mercury_orbit", "label": "Mercury orbit (semi-major)", "km": 57_909_050},
]


class BlackHolesError(ValueError):
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
        raise BlackHolesError(f"Missing {label}")
    return value.strip()


def _validate(raw: dict[str, Any]) -> None:
    for key in (
        "id",
        "title",
        "objects",
        "scale_lab",
        "approach_lab",
        "lensing_lab",
        "tidal_lab",
        "narration",
        "classification_legend",
    ):
        if key not in raw:
            raise BlackHolesError(f"Registry missing {key}")
    if raw.get("id") != "black_holes":
        raise BlackHolesError("Registry id must be black_holes")
    objs = raw["objects"]
    if not isinstance(objs, list) or len(objs) < 3:
        raise BlackHolesError("Need at least three black-hole objects")
    ids = set()
    for obj in objs:
        oid = _require_str(obj.get("id"), "object.id")
        if oid in ids:
            raise BlackHolesError(f"Duplicate object id {oid}")
        ids.add(oid)
        _require_str(obj.get("name"), f"{oid}.name")
        media = obj.get("media") or {}
        _require_str(media.get("classification"), f"{oid}.media.classification")
        _require_str(media.get("image_url"), f"{oid}.media.image_url")
    for key in (
        "what_is",
        "horizon",
        "scale",
        "accretion",
        "lensing",
        "tidal",
        "sgr_a",
        "m87",
        "detection",
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
        "scale_lab": {
            "label": reg["scale_lab"].get("label"),
            "classification": reg["scale_lab"].get("classification"),
            "disclaimer": reg["scale_lab"].get("disclaimer"),
            "examples": [
                {"id": e["id"], "label": e["label"], "mass_solar": e["mass_solar"]}
                for e in reg["scale_lab"].get("examples") or []
            ],
        },
        "approach_lab": {
            "label": reg["approach_lab"].get("label"),
            "classification": reg["approach_lab"].get("classification"),
            "disclaimer": reg["approach_lab"].get("disclaimer"),
            "regions": [
                {"id": r["id"], "label": r["label"], "progress": r["progress"]}
                for r in reg["approach_lab"].get("regions") or []
            ],
        },
        "lensing_lab": {
            "label": reg["lensing_lab"].get("label"),
            "classification": reg["lensing_lab"].get("classification"),
            "disclaimer": reg["lensing_lab"].get("disclaimer"),
        },
        "accretion_lab": reg.get("accretion_lab"),
        "tidal_lab": {
            "label": reg["tidal_lab"].get("label"),
            "classification": reg["tidal_lab"].get("classification"),
            "disclaimer": reg["tidal_lab"].get("disclaimer"),
            "examples": reg["tidal_lab"].get("examples"),
        },
        "detection_methods": reg.get("detection_methods"),
    }


def object_payload(object_id: str | None) -> dict[str, Any]:
    obj = object_by_id(object_id)
    if not obj:
        return {"ok": False, "error": "Unknown black-hole object."}
    return {
        "ok": True,
        "object": obj,
        "classification_legend": load_registry().get("classification_legend"),
    }


def _schwarzschild_km(mass_solar: float) -> float:
    return float(mass_solar) * _RS_KM_PER_MSUN


def _comparisons(rs_km: float) -> list[dict[str, Any]]:
    rows = []
    for scale in _COMPARISON_SCALES:
        ratio = rs_km / float(scale["km"])
        rows.append(
            {
                "id": scale["id"],
                "label": scale["label"],
                "scale_km": scale["km"],
                "rs_over_scale": round(ratio, 6),
                "phrase": (
                    f"Rs ≈ {ratio:.2f}× {scale['label']}"
                    if ratio >= 0.01
                    else f"Rs is much smaller than {scale['label']}"
                ),
            }
        )
    return rows


def scale_state(example_id: str | None = None, mass_solar: float | None = None) -> dict[str, Any]:
    lab = load_registry()["scale_lab"]
    examples = list(lab.get("examples") or [])
    chosen = None
    if example_id:
        for ex in examples:
            if ex.get("id") == example_id:
                chosen = ex
                break
        if chosen is None:
            return {"ok": False, "error": "Unknown scale example."}
        mass = float(chosen["mass_solar"])
    elif mass_solar is not None:
        try:
            mass = float(mass_solar)
        except (TypeError, ValueError):
            return {"ok": False, "error": "mass_solar must be a number."}
        if not math.isfinite(mass) or mass <= 0 or mass > 1e12:
            return {"ok": False, "error": "mass_solar out of teaching range."}
        chosen = {"id": "custom", "label": "Custom mass", "mass_solar": mass, "note": "User-selected"}
    else:
        chosen = examples[0]
        mass = float(chosen["mass_solar"])

    rs_km = _schwarzschild_km(mass)
    return {
        "ok": True,
        "kind": "theoretical_model",
        "classification": lab.get("classification") or "theoretical_model",
        "label": lab.get("label"),
        "disclaimer": lab.get("disclaimer"),
        "example": chosen,
        "mass_solar": mass,
        "schwarzschild_radius_km": round(rs_km, 4),
        "schwarzschild_radius_m": round(rs_km * 1000.0, 1),
        "assumption": "non_rotating_schwarzschild",
        "comparisons": _comparisons(rs_km),
        "examples": [{"id": e["id"], "label": e["label"], "mass_solar": e["mass_solar"]} for e in examples],
    }


def approach_state(region_id: str | None = None, progress: float | None = None) -> dict[str, Any]:
    lab = load_registry()["approach_lab"]
    regions = list(lab.get("regions") or [])
    if not regions:
        return {"ok": False, "error": "No approach regions configured."}
    chosen = regions[0]
    if region_id:
        for r in regions:
            if r.get("id") == region_id:
                chosen = r
                break
        else:
            return {"ok": False, "error": "Unknown approach region."}
    elif progress is not None:
        try:
            pval = float(progress)
        except (TypeError, ValueError):
            return {"ok": False, "error": "progress must be a number."}
        pval = max(0.0, min(1.0, pval))
        chosen = min(regions, key=lambda s: abs(float(s["progress"]) - pval))
    return {
        "ok": True,
        "kind": "illustrative",
        "classification": lab.get("classification") or "illustration",
        "label": lab.get("label"),
        "disclaimer": lab.get("disclaimer"),
        "region": chosen,
        "regions": [{"id": r["id"], "label": r["label"], "progress": r["progress"]} for r in regions],
    }


def lensing_state(strength: float | None = None, phase: float | None = None) -> dict[str, Any]:
    lab = load_registry()["lensing_lab"]
    try:
        s = 0.55 if strength is None else float(strength)
        ph = 0.0 if phase is None else float(phase)
    except (TypeError, ValueError):
        return {"ok": False, "error": "strength and phase must be numbers."}
    s = max(0.0, min(1.0, s))
    ph = ph % (2 * math.pi)

    # Pedagogical star-field deflection (not GR geodesic integration)
    stars = []
    for i in range(36):
        ang = (i / 36.0) * 2 * math.pi + ph * 0.15
        r0 = 18 + (i % 5) * 7
        # Deflect outward/tangential near center with strength
        bend = s * (12.0 / max(r0, 8.0)) * 18.0
        x = 50 + (r0 + bend) * math.cos(ang)
        y = 50 + (r0 + bend * 0.85) * math.sin(ang)
        stars.append({"x": round(x, 3), "y": round(y, 3), "r": 0.7 + (i % 3) * 0.25})

    ring_r = 14 + s * 10
    return {
        "ok": True,
        "kind": "illustrative",
        "classification": "illustration",
        "label": lab.get("label") or "ILLUSTRATIVE RELATIVISTIC LENSING",
        "disclaimer": lab.get("disclaimer"),
        "strength": s,
        "phase": ph,
        "exaggerated": True,
        "shadow_radius": round(8 + s * 2, 3),
        "photon_ring_radius": round(ring_r, 3),
        "stars": stars,
        "einstein_ring_hint": s > 0.45,
        "note": "Not a precision ray-tracing reconstruction.",
    }


def tidal_state(example_id: str | None = None) -> dict[str, Any]:
    lab = load_registry()["tidal_lab"]
    examples = list(lab.get("examples") or [])
    chosen = examples[0]
    if example_id:
        for ex in examples:
            if ex.get("id") == example_id:
                chosen = ex
                break
        else:
            return {"ok": False, "error": "Unknown tidal example."}
    # Relative horizon tidal index ~ 1/M^2 vs stellar reference (teaching)
    mass = float(chosen["mass_solar"])
    ref = float(examples[0]["mass_solar"]) if examples else 10.0
    relative = (ref / mass) ** 2 if mass > 0 else 0.0
    return {
        "ok": True,
        "kind": "theoretical_model",
        "classification": lab.get("classification") or "theoretical_model",
        "label": lab.get("label"),
        "disclaimer": lab.get("disclaimer"),
        "example": chosen,
        "relative_horizon_tide_vs_stellar": relative,
        "interpretation": chosen.get("caption"),
        "examples": examples,
        "teaching_point": (
            "Horizon tidal gradient scales roughly as 1/M² for Schwarzschild holes; "
            "supermassive horizons can be locally gentler than stellar-mass ones."
        ),
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
        return {"ok": False, "error": "Unknown black-hole object."}
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
            "message": meta.get("stellarium_note") or "No Stellarium sky anchor for this object.",
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
    matched = bool({n.lower() for n in names}.intersection(accepted)) if posted else False
    if not matched and mode in ("host_sky", "coordinate_host") and posted:
        dec = blob.get("dec_deg")
        hint = obj.get("stellarium_dec_hint")
        tol = float(obj.get("stellarium_dec_tolerance_deg") or 8.0)
        if isinstance(dec, (int, float)) and isinstance(hint, (int, float)):
            if abs(float(dec) - float(hint)) <= tol:
                matched = True
                names = names or ["Unnamed object"]
        # Also accept if name contains NGC 6522 etc.
        if not matched and accepted:
            for n in names:
                for a in accepted:
                    if a and a in n.lower():
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
        "kind": obj.get("kind"),
        "mass_solar_approx": obj.get("mass_solar_approx"),
        "summary": obj.get("significance"),
        "stellarium_search": obj.get("stellarium_search"),
        "stellarium_match_mode": obj.get("stellarium_match_mode"),
        "media_classification": media.get("classification"),
        "media_title": media.get("title"),
    }
