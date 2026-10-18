"""
experience.py

Pure helpers for the Sky Time Machine, postcard, comparison, motion
track, sonification plan, event-strip foundation, and narration hook.

Stellarium I/O stays in stellarium_client.py. This module never talks
to the network and never invents observational values.
"""

from __future__ import annotations

import math
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

UNIX_JD_EPOCH = 2440587.5
J2000_JD = 2451545.0
MAX_NAME_LEN = 80
ALTITUDE_MIN_M = -500.0
ALTITUDE_MAX_M = 9000.0
LAT_MIN, LAT_MAX = -90.0, 90.0
LON_MIN, LON_MAX = -180.0, 180.0

_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_to_jd(dt: datetime) -> float:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return UNIX_JD_EPOCH + dt.timestamp() / 86400.0


def jd_to_utc(jd: float) -> datetime:
    if not isinstance(jd, (int, float)) or isinstance(jd, bool) or not math.isfinite(jd):
        raise ValueError("Julian Day must be a finite number.")
    return datetime.fromtimestamp((float(jd) - UNIX_JD_EPOCH) * 86400.0, tz=timezone.utc)


def parse_utc(text: str, *, min_year: int = 1600, max_year: int = 2500) -> datetime:
    raw = (text or "").strip()
    if not raw:
        raise ValueError("UTC date/time is required.")
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError("UTC date/time must be ISO-8601 (e.g. 2020-01-01T00:00:00Z).") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    year = dt.year
    if year < min_year or year > max_year:
        raise ValueError(f"UTC year must be between {min_year} and {max_year}.")
    return dt


def parse_lat_lon_alt(payload: dict) -> tuple[float, float, float]:
    lat = _require_finite(payload.get("latitude"), "latitude", LAT_MIN, LAT_MAX)
    lon = _require_finite(payload.get("longitude"), "longitude", LON_MIN, LON_MAX)
    alt_raw = payload.get("altitude", 0)
    if alt_raw in (None, ""):
        alt = 0.0
    else:
        alt = _require_finite(alt_raw, "altitude", ALTITUDE_MIN_M, ALTITUDE_MAX_M)
    return lat, lon, alt


def sanitize_place_name(name: Any) -> str:
    if name is None:
        return ""
    text = _CONTROL_CHARS.sub("", str(name)).strip()
    return text[:MAX_NAME_LEN]


def time_machine_presets(now: Optional[datetime] = None) -> list[dict]:
    now = now or utc_now()
    year_ago = _shift_years(now, -1)
    decade_ago = _shift_years(now, -10)
    return [
        {"id": "now", "label": "Now", "utc": _iso(now), "description": "Return Stellarium to the current clock time."},
        {"id": "year_ago", "label": "1 year ago", "utc": _iso(year_ago), "description": "Same UTC clock time, one year earlier."},
        {"id": "decade_ago", "label": "10 years ago", "utc": _iso(decade_ago), "description": "Same UTC clock time, ten years earlier."},
    ]


def validate_time_machine_request(payload: Any, now: Optional[datetime] = None) -> dict:
    if not isinstance(payload, dict):
        return {"ok": False, "error": "Expected a JSON object."}

    apply_time = bool(payload.get("apply_time"))
    apply_location = bool(payload.get("apply_location"))
    reconstruction = bool(payload.get("reconstruction") or payload.get("historical_reconstruction"))
    if not apply_time and not apply_location:
        return {"ok": False, "error": "Choose Apply for time and/or location. Nothing is sent to Stellarium automatically."}

    now = now or utc_now()
    preset = payload.get("preset")
    if preset in ("", None):
        preset = None
    if preset is not None and preset not in {"now", "year_ago", "decade_ago"}:
        return {"ok": False, "error": "Unknown preset. Use now, year_ago, or decade_ago."}

    try:
        if apply_time:
            if preset == "now":
                utc = now
            elif preset == "year_ago":
                utc = _shift_years(now, -1)
            elif preset == "decade_ago":
                utc = _shift_years(now, -10)
            else:
                utc = parse_utc(
                    str(payload.get("utc") or ""),
                    min_year=800 if reconstruction else 1600,
                )
        else:
            utc = None

        lat = lon = alt = None
        place = ""
        planet = "Earth"
        if apply_location:
            lat, lon, alt = parse_lat_lon_alt(payload)
            place = sanitize_place_name(payload.get("name"))
            planet_raw = sanitize_place_name(payload.get("planet") or "Earth") or "Earth"
            if planet_raw.lower() != "earth":
                return {"ok": False, "error": "Only Earth locations are supported in this pass."}
            planet = "Earth"
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}

    result = {
        "ok": True,
        "error": None,
        "apply_time": apply_time,
        "apply_location": apply_location,
        "preset": preset,
        "utc": _iso(utc) if utc else None,
        "jday": utc_to_jd(utc) if utc else None,
        "latitude": lat,
        "longitude": lon,
        "altitude": alt,
        "name": place,
        "planet": planet,
        "timerate": 0.0,
        "reconstruction": reconstruction,
        "reconstruction_label": "astronomical reconstruction" if reconstruction else None,
    }
    return result


def stellarium_time_params(validated: dict) -> dict:
    return {"time": f"{validated['jday']:.8f}", "timerate": "0"}


def stellarium_location_params(validated: dict) -> dict:
    return {
        "latitude": f"{validated['latitude']:.8f}",
        "longitude": f"{validated['longitude']:.8f}",
        "altitude": f"{int(round(validated['altitude']))}",
        "name": validated["name"] or "Cartography location",
        "planet": "Earth",
    }


def extract_sky_status(status_payload: Any) -> dict:
    empty = {
        "ok": False,
        "utc": None,
        "local": None,
        "jday": None,
        "is_time_now": None,
        "time_zone": None,
        "latitude": None,
        "longitude": None,
        "altitude": None,
        "location_name": None,
        "planet": None,
        "fov_deg": None,
        "selection_heading": None,
    }
    if not isinstance(status_payload, dict) or not status_payload:
        return empty
    time = status_payload.get("time") if isinstance(status_payload.get("time"), dict) else {}
    loc = status_payload.get("location") if isinstance(status_payload.get("location"), dict) else {}
    view = status_payload.get("view") if isinstance(status_payload.get("view"), dict) else {}
    heading = _selection_heading(status_payload.get("selectioninfo"))
    fov = view.get("fov")
    fov_val = float(fov) if isinstance(fov, (int, float)) and not isinstance(fov, bool) and math.isfinite(fov) else None
    jday = time.get("jday")
    jday_val = float(jday) if isinstance(jday, (int, float)) and not isinstance(jday, bool) and math.isfinite(jday) else None
    return {
        "ok": True,
        "utc": time.get("utc") if isinstance(time.get("utc"), str) else None,
        "local": time.get("local") if isinstance(time.get("local"), str) else None,
        "jday": jday_val,
        "is_time_now": time.get("isTimeNow") if isinstance(time.get("isTimeNow"), bool) else None,
        "time_zone": time.get("timeZone") if isinstance(time.get("timeZone"), str) else None,
        "latitude": _optional_float(loc.get("latitude")),
        "longitude": _optional_float(loc.get("longitude")),
        "altitude": _optional_float(loc.get("altitude")),
        "location_name": loc.get("name") if isinstance(loc.get("name"), str) else None,
        "planet": loc.get("planet") if isinstance(loc.get("planet"), str) else None,
        "fov_deg": fov_val,
        "selection_heading": heading,
    }


def extra_selection_fields(raw_info: Any) -> dict:
    if not isinstance(raw_info, dict):
        return {"distance_au": None, "distance_km": None}
    return {
        "distance_au": _optional_float(raw_info.get("distance")),
        "distance_km": _optional_float(raw_info.get("distance-km")),
    }


def build_object_card(selection: dict, sky: Optional[dict] = None, extras: Optional[dict] = None) -> dict:
    extras = extras or {}
    sky = sky or {}
    fields = []

    def add(label: str, value: Any, kind: str = "text") -> None:
        if value is None or value == "":
            return
        fields.append({"label": label, "value": value, "kind": kind})

    add("Name", selection.get("name"))
    add("Alternate name", selection.get("alt_name"))
    add("Category", selection.get("object_category"))
    add("Type", selection.get("object_type"))
    add("Subtype", selection.get("object_subtype"))
    add("Constellation", selection.get("constellation"))
    add("RA (J2000)", selection.get("ra_sexagesimal") or _fmt_deg(selection.get("ra_deg")))
    add("Dec (J2000)", selection.get("dec_sexagesimal") or _fmt_deg(selection.get("dec_deg")))
    add("Altitude", _fmt_deg(selection.get("altitude_deg")))
    add("Azimuth", _fmt_deg(selection.get("azimuth_deg")))
    add("Magnitude", _fmt_num(selection.get("apparent_magnitude"), 2))
    if extras.get("distance_au") is not None:
        add("Distance", f"{extras['distance_au']:.3f} AU")
    elif extras.get("distance_km") is not None:
        add("Distance", f"{extras['distance_km']:.0f} km")
    add("FoV", _fmt_deg(selection.get("fov_deg") if selection.get("fov_deg") is not None else sky.get("fov_deg")))
    if isinstance(selection.get("above_horizon"), bool):
        add("Above horizon", "Yes" if selection["above_horizon"] else "No")
    add("Sky UTC", sky.get("utc"))
    add("Location", sky.get("location_name"))

    family = classify_object(selection)
    media = local_media_hints(selection)
    for hint in media:
        add("Local media", f"{hint.get('label')} ({hint.get('source')})")
    return {
        "ok": bool(selection.get("ok")),
        "family": family,
        "fields": fields,
        "media": media,
        "unavailable_note": "Fields Stellarium or Cartography did not report are omitted.",
    }


def local_media_hints(selection: dict) -> list[dict]:
    """Point at existing local registries. Never fetches NASA or invents imagery."""
    hints: list[dict] = []
    if not isinstance(selection, dict):
        return hints
    try:
        from . import solar_system_media_registry as ssm
    except Exception:
        return hints
    for raw in (selection.get("name"), selection.get("alt_name")):
        tid = ssm.normalize_media_target_id(raw if isinstance(raw, str) else None)
        entry = ssm.get_entry(tid) if tid else None
        if entry:
            hints.append(
                {
                    "kind": "solar_system_media",
                    "id": tid,
                    "label": entry.get("display_name") or tid,
                    "source": "solar_system_media_registry",
                    "note": "NASA public-media lookup remains in the existing NASA Public Media panel.",
                }
            )
            break
    return hints


def classify_object(selection: dict) -> str:
    blob = " ".join(
        str(selection.get(k) or "")
        for k in ("object_category", "object_type", "object_subtype", "name")
    ).lower()
    if "satellit" in blob or "starlink" in blob or "oneweb" in blob:
        return "satellite"
    if "planet" in blob or blob.strip() in {"moon", "sun"}:
        return "planet"
    if "asteroid" in blob or "comet" in blob or "minor" in blob:
        return "small_body"
    if "galax" in blob or "nebula" in blob or "cluster" in blob or "quasar" in blob:
        return "deep_sky"
    if "star" in blob:
        return "star"
    return "other"


def motion_track(selection: dict, sky: dict, now: Optional[datetime] = None) -> dict:
    """Apparent alt/az of the current J2000 RA/Dec over a class-specific window.

    This uses the current coordinates as fixed. Solar-system RA/Dec themselves
    change; the note states that honestly.
    """
    ra = _optional_float(selection.get("ra_deg"))
    dec = _optional_float(selection.get("dec_deg"))
    lat = _optional_float(sky.get("latitude"))
    lon = _optional_float(sky.get("longitude"))
    if None in (ra, dec, lat, lon):
        return {
            "ok": False,
            "available": False,
            "reason": "RA/Dec and observer latitude/longitude are required.",
            "points": [],
        }

    family = classify_object(selection)
    if family == "satellite":
        hours = (-0.25, 0.0, 0.25)
        window = "±15 minutes"
    elif family in {"planet", "small_body"}:
        hours = (-12.0, 0.0, 12.0)
        window = "±12 hours"
    else:
        hours = (-6.0, 0.0, 6.0)
        window = "±6 hours"

    origin = None
    if sky.get("utc"):
        try:
            origin = parse_utc(str(sky["utc"]))
        except ValueError:
            origin = None
    origin = origin or now or utc_now()

    points = []
    for hour in hours:
        when = origin + timedelta(hours=hour)
        alt, az = equatorial_to_horizontal(ra, dec, lat, lon, when)
        label = "NOW" if hour == 0 else ("PAST" if hour < 0 else "FUTURE")
        points.append(
            {
                "label": label,
                "offset_hours": hour,
                "utc": _iso(when),
                "altitude_deg": alt,
                "azimuth_deg": az,
            }
        )

    note = (
        "Apparent sky path from the current J2000 RA/Dec and observer location. "
        "Coordinates are held fixed; Solar System objects also move in RA/Dec."
    )
    return {
        "ok": True,
        "available": True,
        "family": family,
        "window": window,
        "axis": "PAST ----- NOW ----- FUTURE",
        "points": points,
        "note": note,
    }


def equatorial_to_horizontal(ra_deg: float, dec_deg: float, lat_deg: float, lon_deg: float, when: datetime) -> tuple[float, float]:
    jd = utc_to_jd(when)
    d = jd - J2000_JD
    gmst_hours = 18.697374558 + 24.06570982441908 * d
    lst_hours = (gmst_hours + lon_deg / 15.0) % 24.0
    ha_deg = (lst_hours * 15.0 - ra_deg + 360.0) % 360.0
    if ha_deg > 180.0:
        ha_deg -= 360.0
    lat = math.radians(lat_deg)
    dec = math.radians(dec_deg)
    ha = math.radians(ha_deg)
    alt = math.asin(math.sin(lat) * math.sin(dec) + math.cos(lat) * math.cos(dec) * math.cos(ha))
    az = math.atan2(
        -math.sin(ha),
        math.tan(dec) * math.cos(lat) - math.sin(lat) * math.cos(ha),
    )
    az_deg = (math.degrees(az) + 360.0) % 360.0
    return math.degrees(alt), az_deg


def sonify_plan(selection: dict, sky: dict) -> dict:
    """Map a computed altitude series to a deterministic pitch plan.

    This is data sonification, not a recording of a physical sound.
    """
    track = motion_track(selection, sky)
    if not track.get("available"):
        return {
            "ok": False,
            "available": False,
            "reason": track.get("reason") or "Not enough numeric data to sonify.",
            "samples": [],
            "mapping": None,
        }

    dense = []
    ra = selection["ra_deg"]
    dec = selection["dec_deg"]
    lat = sky["latitude"]
    lon = sky["longitude"]
    origin = parse_utc(track["points"][1]["utc"])
    span = abs(track["points"][0]["offset_hours"])
    steps = 24
    for i in range(steps + 1):
        hour = -span + (2 * span) * (i / steps)
        when = origin + timedelta(hours=hour)
        alt, _az = equatorial_to_horizontal(ra, dec, lat, lon, when)
        dense.append({"t": i / steps, "altitude_deg": alt})

    alts = [p["altitude_deg"] for p in dense]
    lo, hi = min(alts), max(alts)
    spread = hi - lo if hi != lo else 1.0
    samples = []
    for point in dense:
        norm = (point["altitude_deg"] - lo) / spread
        freq = 220.0 + norm * 440.0
        samples.append({"t": point["t"], "value": norm, "frequency_hz": round(freq, 2)})

    return {
        "ok": True,
        "available": True,
        "duration_sec": 4.0,
        "samples": samples,
        "mapping": {
            "x": "time across the apparent-altitude window",
            "y": "normalized altitude -> oscillator frequency 220–660 Hz",
            "disclaimer": "Data Sonification: an audible mapping of numbers, not the physical sound of the object.",
        },
    }


def spectrum_axis(entries: list[dict], active_id: Optional[str] = None) -> dict:
    """Discrete wavelength markers from existing gallery entries. No fake curve."""
    marks = []
    for entry in entries or []:
        if not isinstance(entry, dict) or not entry.get("enabled", True):
            continue
        marks.append(
            {
                "id": entry.get("id"),
                "label": entry.get("wavelength") or entry.get("title"),
                "observatory": entry.get("observatory"),
                "source_page_url": entry.get("source_page_url"),
                "credits": entry.get("credits"),
                "active": entry.get("id") == active_id,
            }
        )
    return {
        "ok": True,
        "available": bool(marks),
        "marks": marks,
        "axis_label": "Curated wavelength views (not a measured intensity spectrum)",
        "empty_reason": None if marks else "No curated spectrum views are registered for this target.",
    }


def postcard_metadata(selection: dict, sky: dict, extras: Optional[dict] = None) -> dict:
    extras = extras or {}
    card = build_object_card(selection, sky, extras)
    return {
        "ok": True,
        "kind": "sky_postcard",
        "generated_utc": _iso(utc_now()),
        "screenshot": {
            "available": False,
            "reason": "Stellarium Remote Control does not expose a screenshot endpoint in this build.",
        },
        "sky": {
            "utc": sky.get("utc"),
            "local": sky.get("local"),
            "is_time_now": sky.get("is_time_now"),
            "location_name": sky.get("location_name"),
            "latitude": sky.get("latitude"),
            "longitude": sky.get("longitude"),
            "altitude": sky.get("altitude"),
            "fov_deg": sky.get("fov_deg"),
        },
        "selection": {
            "name": selection.get("name"),
            "object_category": selection.get("object_category"),
            "object_type": selection.get("object_type"),
            "constellation": selection.get("constellation"),
            "ra_deg": selection.get("ra_deg"),
            "dec_deg": selection.get("dec_deg"),
            "ra_sexagesimal": selection.get("ra_sexagesimal"),
            "dec_sexagesimal": selection.get("dec_sexagesimal"),
            "fov_deg": selection.get("fov_deg"),
            "altitude_deg": selection.get("altitude_deg"),
            "azimuth_deg": selection.get("azimuth_deg"),
            "apparent_magnitude": selection.get("apparent_magnitude"),
            "distance_au": extras.get("distance_au"),
        },
        "fields": card["fields"],
        "note": "Rendered locally by Stellar Cartography. Not uploaded.",
    }


def compare_snapshots(a: dict, b: dict) -> dict:
    """Compare two metadata snapshots. Does not start a second Stellarium."""
    if not isinstance(a, dict) or not isinstance(b, dict):
        return {"ok": False, "error": "Both snapshots must be JSON objects."}

    def pack(src: dict) -> dict:
        sel = src.get("selection") if isinstance(src.get("selection"), dict) else src
        sky = src.get("sky") if isinstance(src.get("sky"), dict) else src
        return {
            "name": sel.get("name"),
            "utc": sky.get("utc") or sel.get("utc"),
            "location_name": sky.get("location_name") or sel.get("location_name"),
            "latitude": _optional_float(sky.get("latitude") if sky.get("latitude") is not None else sel.get("latitude")),
            "longitude": _optional_float(sky.get("longitude") if sky.get("longitude") is not None else sel.get("longitude")),
            "ra_deg": _optional_float(sel.get("ra_deg")),
            "dec_deg": _optional_float(sel.get("dec_deg")),
            "altitude_deg": _optional_float(sel.get("altitude_deg")),
            "azimuth_deg": _optional_float(sel.get("azimuth_deg")),
            "fov_deg": _optional_float(sel.get("fov_deg") if sel.get("fov_deg") is not None else sky.get("fov_deg")),
            "above_horizon": sel.get("above_horizon") if isinstance(sel.get("above_horizon"), bool) else None,
        }

    left, right = pack(a), pack(b)
    rows = []
    for key, label in (
        ("name", "Selected object"),
        ("utc", "UTC"),
        ("location_name", "Location"),
        ("latitude", "Latitude"),
        ("longitude", "Longitude"),
        ("ra_deg", "RA (deg)"),
        ("dec_deg", "Dec (deg)"),
        ("altitude_deg", "Altitude (deg)"),
        ("azimuth_deg", "Azimuth (deg)"),
        ("fov_deg", "FoV (deg)"),
        ("above_horizon", "Above horizon"),
    ):
        va, vb = left.get(key), right.get(key)
        delta = None
        if isinstance(va, (int, float)) and isinstance(vb, (int, float)) and not isinstance(va, bool) and not isinstance(vb, bool):
            delta = vb - va
        rows.append({"field": label, "a": va, "b": vb, "delta": delta, "changed": va != vb})
    return {"ok": True, "rows": rows, "note": "Metadata comparison of two captured states. One Stellarium session remains authoritative."}


def event_strip_foundation(sky: Optional[dict] = None) -> dict:
    return {
        "ok": True,
        "available": False,
        "events": [],
        "sky_utc": (sky or {}).get("utc"),
        "note": (
            "No local conjunction/eclipse catalog is shipped in this pass. "
            "A future curated JSON file or Stellarium plugin catalog "
            "(Meteor Showers, Solar System events) can populate this strip."
        ),
        "required_later": "A small date-indexed local event catalog with name, kind, utc, and optional object aliases.",
    }


def narration_payload(
    selection: dict,
    sky: Optional[dict] = None,
    *,
    kind: str = "selection",
    constellation: Optional[dict] = None,
    tour: Optional[dict] = None,
) -> dict:
    sky = sky or {}
    kind_key = (kind or "selection").strip()
    if kind_key == "exhibit_step":
        from . import exhibit

        extra = exhibit.narration_payload(
            (constellation or {}).get("exhibit_id") if isinstance(constellation, dict) else None,
            (tour or {}).get("step_index") if isinstance(tour, dict) else None,
        )
        extra["audio_autoplay"] = False
        extra["listen_available"] = True
        extra["label"] = "Cartography Narration"
        return extra
    if kind_key in {"constellation_overview", "tour_step", "object_transition"}:
        from . import constellation_story

        extra = constellation_story.constellation_narration(
            kind_key,
            story=constellation,
            selection=selection,
            tour=tour,
        )
        extra["sky_utc"] = sky.get("utc")
        media = _official_media_narration(selection)
        extra.update(media)
        if media.get("official_media_note"):
            extra["text"] = (str(extra.get("text") or "") + " " + media["official_media_note"]).strip()
            extra["summary"] = extra["text"]
        extra["listen_available"] = True
        extra["audio_autoplay"] = False
        extra["label"] = "Cartography Narration"
        extra["interface"] = {
            "intent": "Cartography-authored text is sent to a local TTS renderer. The TTS service does not invent astronomy content.",
            "wired": ["father_fox", "kayock_voice"],
            "payload": {"text": extra.get("text"), "source": "stellar-cartography-constellation-story"},
        }
        return extra

    parts = []
    if selection.get("name"):
        parts.append(str(selection["name"]))
    if selection.get("object_type") or selection.get("object_category"):
        parts.append(f"is a {selection.get('object_type') or selection.get('object_category')}")
    if selection.get("constellation"):
        parts.append(f"in {selection['constellation']}")
    if selection.get("ra_sexagesimal") and selection.get("dec_sexagesimal"):
        parts.append(f"at RA {selection['ra_sexagesimal']}, Dec {selection['dec_sexagesimal']}")
    if sky.get("utc"):
        parts.append(f"Stellarium time {sky['utc']}")
    if sky.get("location_name"):
        parts.append(f"from {sky['location_name']}")
    summary = ", ".join(parts) + "." if parts else "No current Stellarium selection."
    payload = {
        "ok": True,
        "listen_available": True,
        "feature_flag": "narration_hook",
        "kind": "selection",
        "title": selection.get("name") or "Stellarium selection",
        "text": summary,
        "summary": summary,
        "source_object": selection.get("name"),
        "constellation": selection.get("constellation"),
        "step_index": None,
        "total_steps": None,
        "label": "Cartography Narration",
        "audio_autoplay": False,
        "interface": {
            "intent": "Cartography-authored text is sent to a local TTS renderer. The TTS service does not invent astronomy content.",
            "wired": ["father_fox", "kayock_voice"],
            "payload": {"text": summary, "source": "stellar-cartography-local"},
        },
    }
    media = _official_media_narration(selection)
    payload.update(media)
    if media.get("official_media_note"):
        payload["text"] = (payload["text"] + " " + media["official_media_note"]).strip()
        payload["summary"] = payload["text"]
        payload["interface"]["payload"]["text"] = payload["text"]
    payload["audio_autoplay"] = False
    return payload


def _official_media_narration(selection: dict) -> dict:
    try:
        from . import official_media

        return official_media.curated_narration_fields(selection)
    except Exception:  # noqa: BLE001 - narration must still return text
        return {
            "official_media_title": None,
            "official_media_provider": None,
            "official_media_relation": None,
            "official_media_source_url": None,
            "official_media_note": None,
            "audio_autoplay": False,
        }


def _shift_years(dt: datetime, years: int) -> datetime:
    try:
        return dt.replace(year=dt.year + years)
    except ValueError:
        return dt.replace(year=dt.year + years, day=28)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _require_finite(value: Any, label: str, lo: float, hi: float) -> float:
    if isinstance(value, bool) or value is None or value == "":
        raise ValueError(f"{label} is required.")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a number.") from exc
    if not math.isfinite(number) or number < lo or number > hi:
        raise ValueError(f"{label} must be between {lo} and {hi}.")
    return number


def _optional_float(value: Any) -> Optional[float]:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return float(value)
    if isinstance(value, str):
        try:
            number = float(value.strip())
        except ValueError:
            return None
        return number if math.isfinite(number) else None
    return None


def _fmt_deg(value: Any) -> Optional[str]:
    number = _optional_float(value)
    if number is None:
        return None
    return f"{number:.3f}°"


def _fmt_num(value: Any, places: int) -> Optional[str]:
    number = _optional_float(value)
    if number is None:
        return None
    return f"{number:.{places}f}"


def _selection_heading(html: Any) -> Optional[str]:
    if not isinstance(html, str) or not html.strip():
        return None
    match = re.search(r"<h2[^>]*>(.*?)</h2>", html, flags=re.I | re.S)
    if not match:
        return None
    text = re.sub(r"<[^>]+>", "", match.group(1)).strip()
    return text or None
