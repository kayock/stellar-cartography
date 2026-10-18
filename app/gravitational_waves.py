"""
gravitational_waves.py

Gravitational Waves exhibit helpers: registry, illustrative labs, events,
narration, and Stellarium sky-anchor metadata. No hard-coded deployment hosts.
"""

from __future__ import annotations

import json
import math
import re
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

REGISTRY_PATH = Path(__file__).resolve().parent / "data" / "gravitational_waves_registry.json"
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
CLASSIFICATIONS = frozenset(
    {
        "illustration",
        "real_detector_data",
        "simulation",
        "sonification",
        "observation",
        "reconstruction",
    }
)


class GravitationalWavesError(ValueError):
    """Invalid gravitational-waves registry or request."""


def _require_str(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GravitationalWavesError(f"Missing or invalid '{field}'.")
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
        raise GravitationalWavesError("Registry must be an object.")
    for field in (
        "id",
        "title",
        "science",
        "wave_lab",
        "interferometer_lab",
        "chirp_lab",
        "events",
        "narration",
        "detectors",
    ):
        if field not in raw:
            raise GravitationalWavesError(f"Registry missing '{field}'.")
    if raw.get("id") != "gravitational_waves":
        raise GravitationalWavesError("Registry id must be 'gravitational_waves'.")
    for key in (
        "what_is",
        "not_rubber_sheet",
        "detection",
        "chirp",
        "network",
        "multimessenger",
        "takeaway",
    ):
        _require_str(raw["science"].get(key), f"science.{key}")
    for key in (
        "spacetime",
        "interferometer",
        "inspiral",
        "chirp",
        "gw150914",
        "gw170817",
        "network",
        "multimessenger",
        "closing",
    ):
        _require_str(raw["narration"].get(key), f"narration.{key}")
    if raw["wave_lab"].get("kind") != "illustrative":
        raise GravitationalWavesError("wave_lab.kind must be illustrative.")
    if raw["chirp_lab"].get("classification") != "sonification":
        raise GravitationalWavesError("chirp_lab must be classified as sonification.")
    _require_str(raw["chirp_lab"].get("audio_label"), "chirp_lab.audio_label")
    allowed = {h.lower() for h in (raw.get("provenance_hosts_allowed") or [])}
    seen: set[str] = set()
    enabled = 0
    for event in raw["events"]:
        _validate_event(event, allowed)
        eid = event["id"]
        if eid in seen:
            raise GravitationalWavesError(f"Duplicate event id '{eid}'.")
        seen.add(eid)
        if event.get("enabled"):
            enabled += 1
    if enabled < 2:
        raise GravitationalWavesError("At least two enabled events are required.")
    if not isinstance(raw.get("detectors"), list) or len(raw["detectors"]) < 2:
        raise GravitationalWavesError("detectors list required.")


def _validate_event(event: Any, allowed_hosts: set[str]) -> None:
    if not isinstance(event, dict):
        raise GravitationalWavesError("Each event must be an object.")
    eid = event.get("id")
    if not isinstance(eid, str) or not _ID_RE.match(eid):
        raise GravitationalWavesError("Invalid event id.")
    _require_str(event.get("name"), "name")
    _require_str(event.get("source_type"), "source_type")
    _require_str(event.get("detection_date"), "detection_date")
    _require_str(event.get("significance"), "significance")
    _require_str(event.get("localization_note"), "localization_note")
    media = event.get("media")
    if not isinstance(media, dict):
        raise GravitationalWavesError(f"Event '{eid}' missing media.")
    classification = _require_str(media.get("classification"), "media.classification").lower()
    if classification not in CLASSIFICATIONS:
        raise GravitationalWavesError(f"Event '{eid}' media.classification invalid.")
    page = _require_str(media.get("source_page_url"), "media.source_page_url")
    image = _require_str(media.get("image_url"), "media.image_url")
    if allowed_hosts:
        if not _host_ok(page, allowed_hosts):
            raise GravitationalWavesError(f"Event '{eid}' source_page_url host not allowlisted.")
        if not _host_ok(image, allowed_hosts):
            raise GravitationalWavesError(f"Event '{eid}' image_url host not allowlisted.")
    sources = event.get("sources")
    if not isinstance(sources, list) or not sources:
        raise GravitationalWavesError(f"Event '{eid}' needs sources.")
    for src in sources:
        url = _require_str(src.get("url"), "source.url")
        _require_str(src.get("title"), "source.title")
        if allowed_hosts and not _host_ok(url, allowed_hosts):
            raise GravitationalWavesError(f"Event '{eid}' source url host not allowlisted.")


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
        "wave_lab": {
            "kind": reg["wave_lab"]["kind"],
            "label": reg["wave_lab"].get("label"),
            "classification": reg["wave_lab"].get("classification"),
            "polarizations": list(reg["wave_lab"].get("polarizations") or []),
        },
        "interferometer_lab": {
            "kind": reg["interferometer_lab"]["kind"],
            "label": reg["interferometer_lab"].get("label"),
            "phase_count": len(reg["interferometer_lab"].get("phases") or []),
        },
        "chirp_lab": {
            "kind": reg["chirp_lab"]["kind"],
            "label": reg["chirp_lab"].get("label"),
            "classification": reg["chirp_lab"].get("classification"),
            "audio_label": reg["chirp_lab"].get("audio_label"),
            "stage_count": len(reg["chirp_lab"].get("stages") or []),
        },
        "detectors": list(reg.get("detectors") or []),
        "events": [_event_summary(e) for e in reg["events"] if e.get("enabled")],
        "audio_autoplay": False,
    }


def event_by_id(event_id: str | None) -> dict[str, Any] | None:
    if not event_id or not isinstance(event_id, str):
        return None
    for event in load_registry()["events"]:
        if event.get("id") == event_id and event.get("enabled"):
            return event
    return None


def object_by_id(object_id: str | None) -> dict[str, Any] | None:
    """Alias for exhibit validation (events are the selectable objects)."""
    return event_by_id(object_id)


def event_payload(event_id: str | None) -> dict[str, Any]:
    event = event_by_id(event_id)
    if not event:
        return {"ok": False, "error": "Unknown gravitational-wave event."}
    return {
        "ok": True,
        "event": _event_public(event),
        "classification_legend": load_registry().get("classification_legend") or {},
        "audio_autoplay": False,
    }


def wave_state(
    *,
    polarization: str = "plus",
    phase: float = 0.0,
    amplitude: float | None = None,
) -> dict[str, Any]:
    lab = load_registry()["wave_lab"]
    pol = (polarization or "plus").strip().lower()
    if pol not in ("plus", "cross"):
        return {"ok": False, "error": "polarization must be 'plus' or 'cross'."}
    try:
        ph = float(phase)
    except (TypeError, ValueError):
        return {"ok": False, "error": "phase must be a number."}
    ph = ph % (2 * math.pi)
    amp = lab.get("default_amplitude", 0.35) if amplitude is None else float(amplitude)
    amp = max(0.0, min(float(lab.get("max_amplitude", 0.55)), amp))
    n = int(lab.get("ring_points") or 24)
    points = []
    for i in range(n):
        theta = 2 * math.pi * i / n
        # Plus: stretch x / squeeze y; Cross: stretch along diagonals.
        if pol == "plus":
            sx = 1.0 + amp * math.cos(ph)
            sy = 1.0 - amp * math.cos(ph)
            x = 50 + 28 * math.cos(theta) * sx
            y = 50 + 28 * math.sin(theta) * sy
        else:
            # cross polarization rotates the stretch axes by 45 deg
            c, s = math.cos(theta), math.sin(theta)
            # rotate into diagonal basis
            u = (c + s) / math.sqrt(2)
            v = (-c + s) / math.sqrt(2)
            su = 1.0 + amp * math.cos(ph)
            sv = 1.0 - amp * math.cos(ph)
            ur, vr = u * su, v * sv
            x = 50 + 28 * (ur - vr) / math.sqrt(2)
            y = 50 + 28 * (ur + vr) / math.sqrt(2)
        points.append({"x": round(x, 3), "y": round(y, 3)})
    return {
        "ok": True,
        "kind": "illustrative",
        "classification": "illustration",
        "label": lab.get("label"),
        "disclaimer": load_registry().get("illustrative_disclaimer"),
        "polarization": pol,
        "phase": ph,
        "amplitude": amp,
        "exaggerated": True,
        "points": points,
        "grid": _grid_points(pol, ph, amp),
    }


def _grid_points(pol: str, phase: float, amp: float) -> list[dict[str, Any]]:
    pts = []
    for ix in range(-2, 3):
        for iy in range(-2, 3):
            x0, y0 = ix / 2.5, iy / 2.5
            if pol == "plus":
                x = x0 * (1 + amp * math.cos(phase))
                y = y0 * (1 - amp * math.cos(phase))
            else:
                # cross in diagonal basis
                u = (x0 + y0) / math.sqrt(2)
                v = (-x0 + y0) / math.sqrt(2)
                u *= 1 + amp * math.cos(phase)
                v *= 1 - amp * math.cos(phase)
                x = (u - v) / math.sqrt(2)
                y = (u + v) / math.sqrt(2)
            pts.append({"x": round(50 + 16 * x, 3), "y": round(50 + 16 * y, 3)})
    return pts


def interferometer_state(phase_id: str | None = None, progress: float | None = None) -> dict[str, Any]:
    lab = load_registry()["interferometer_lab"]
    phases = list(lab.get("phases") or [])
    chosen = None
    if phase_id:
        for p in phases:
            if p.get("id") == phase_id:
                chosen = p
                break
        if chosen is None:
            return {"ok": False, "error": "Unknown interferometer phase."}
    else:
        if progress is None:
            chosen = phases[0]
        else:
            try:
                pval = max(0.0, min(1.0, float(progress)))
            except (TypeError, ValueError):
                return {"ok": False, "error": "progress must be a number."}
            chosen = min(phases, key=lambda s: abs(float(s["progress"]) - pval))
    return {
        "ok": True,
        "kind": "illustrative",
        "classification": "illustration",
        "label": lab.get("label"),
        "phase": chosen,
        "phases": [{"id": p["id"], "label": p["label"], "progress": p["progress"]} for p in phases],
        "disclaimer": load_registry().get("illustrative_disclaimer"),
    }


def chirp_state(stage_id: str | None = None, progress: float | None = None) -> dict[str, Any]:
    lab = load_registry()["chirp_lab"]
    stages = list(lab.get("stages") or [])
    chosen = None
    if stage_id:
        for s in stages:
            if s.get("id") == stage_id:
                chosen = s
                break
        if chosen is None:
            return {"ok": False, "error": "Unknown chirp stage."}
    else:
        if progress is None:
            chosen = stages[0]
        else:
            try:
                pval = max(0.0, min(1.0, float(progress)))
            except (TypeError, ValueError):
                return {"ok": False, "error": "progress must be a number."}
            chosen = min(stages, key=lambda s: abs(float(s["progress"]) - pval))
    # simple illustrative waveform samples
    samples = []
    freq = float(chosen.get("freq_hz") or 200)
    amp = float(chosen.get("amp") or 0.3)
    for i in range(64):
        t = i / 64.0
        samples.append(round(amp * math.sin(2 * math.pi * (3 + freq / 120.0) * t), 4))
    return {
        "ok": True,
        "kind": "illustrative",
        "classification": "sonification",
        "label": lab.get("label"),
        "audio_label": lab.get("audio_label"),
        "is_detector_band_audio": False,
        "is_frequency_shifted_representation": True,
        "is_space_sound": False,
        "stage": chosen,
        "stages": [
            {"id": s["id"], "label": s["label"], "progress": s["progress"], "freq_hz": s.get("freq_hz")}
            for s in stages
        ],
        "waveform_samples": samples,
        "playable_tone": {
            "freq_hz": freq,
            "amp": amp,
            "duration_sec": 0.35,
            "classification": "sonification",
        },
    }


def network_payload() -> dict[str, Any]:
    reg = load_registry()
    return {
        "ok": True,
        "detectors": list(reg.get("detectors") or []),
        "explanation": reg["science"]["network"],
        "localization_honesty": (
            "Arrival-time and antenna-pattern differences constrain a probability region. "
            "That region may be large; it is not automatically a single sky coordinate."
        ),
        "classification": "illustration",
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
    titles = {
        "spacetime": "Ripples in spacetime",
        "interferometer": "How interferometers listen",
        "inspiral": "Binary inspiral",
        "chirp": "The chirp",
        "gw150914": "GW150914",
        "gw170817": "GW170817",
        "network": "Detector networks",
        "multimessenger": "Multi-messenger astronomy",
        "closing": "Takeaway",
    }
    return {
        "ok": True,
        "kind": "gravitational_waves",
        "segment": key,
        "title": titles.get(key, key),
        "text": narration[key],
        "listen_available": True,
        "audio_autoplay": False,
        "feature_flag": "narration_hook",
    }


def focus_request(event_id: str | None) -> dict[str, Any]:
    event = event_by_id(event_id)
    if not event:
        return {"ok": False, "error": "Unknown gravitational-wave event.", "stellarium_required": False}
    mode = event.get("stellarium_match_mode") or "exact"
    search = event.get("stellarium_search")
    return {
        "ok": True,
        "object_id": event["id"],
        "event_id": event["id"],
        "name": event["name"],
        "stellarium_search": search,
        "stellarium_fov_deg": event.get("stellarium_fov_deg"),
        "stellarium_match_mode": mode,
        "stellarium_note": event.get("stellarium_note"),
        "localization_note": event.get("localization_note"),
        "stellarium_required": False,
        "role": "sky_anchor",
    }


def _selection_blob(stellarium_client: Any) -> dict[str, Any]:
    if stellarium_client is None or not hasattr(stellarium_client, "get_selection"):
        return {}
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


def apply_focus(stellarium_client: Any, event_id: str | None) -> dict[str, Any]:
    meta = focus_request(event_id)
    if not meta.get("ok"):
        return meta
    event = event_by_id(event_id) or {}
    mode = meta.get("stellarium_match_mode") or "exact"
    if mode == "unavailable" or not meta.get("stellarium_search"):
        return {
            **meta,
            "focused": False,
            "fov_set": False,
            "connected": stellarium_client is not None,
            "message": meta.get("stellarium_note")
            or "No precise Stellarium host for this event; see localization note.",
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
    accepted = [n.lower() for n in (event.get("stellarium_accept_names") or []) if isinstance(n, str)]
    matched = bool({n.lower() for n in names}.intersection(accepted)) if posted else False
    if not matched and mode == "coordinate_host" and posted:
        dec = blob.get("dec_deg")
        hint = event.get("stellarium_dec_hint")
        tol = float(event.get("stellarium_dec_tolerance_deg") or 5.0)
        if isinstance(dec, (int, float)) and isinstance(hint, (int, float)):
            if abs(float(dec) - float(hint)) <= tol:
                matched = True
                names = names or ["Unnamed object"]
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


def _event_summary(event: dict[str, Any]) -> dict[str, Any]:
    media = event.get("media") or {}
    return {
        "id": event["id"],
        "name": event["name"],
        "short_name": event.get("short_name") or event["name"],
        "source_type": event.get("source_type"),
        "detection_date": event.get("detection_date"),
        "detectors": list(event.get("detectors") or []),
        "summary": event.get("summary"),
        "stellarium_search": event.get("stellarium_search"),
        "stellarium_match_mode": event.get("stellarium_match_mode"),
        "media_classification": media.get("classification"),
        "media_title": media.get("title"),
    }


def _event_public(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": event["id"],
        "name": event["name"],
        "short_name": event.get("short_name") or event["name"],
        "source_type": event.get("source_type"),
        "detection_date": event.get("detection_date"),
        "detectors": list(event.get("detectors") or []),
        "significance": event.get("significance"),
        "localization_note": event.get("localization_note"),
        "summary": event.get("summary"),
        "teaching_points": event.get("teaching_points") or [],
        "stellarium_search": event.get("stellarium_search"),
        "stellarium_fov_deg": event.get("stellarium_fov_deg"),
        "stellarium_match_mode": event.get("stellarium_match_mode"),
        "stellarium_note": event.get("stellarium_note"),
        "media": dict(event.get("media") or {}),
        "sources": event.get("sources") or [],
    }
