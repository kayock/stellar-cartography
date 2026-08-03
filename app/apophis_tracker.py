"""
apophis_tracker.py

Featured Apophis (99942) tracker using official JPL SSD APIs only:
  - SBDB API (https://ssd-api.jpl.nasa.gov/doc/sbdb.html)
  - Horizons API (https://ssd-api.jpl.nasa.gov/doc/horizons.html)

Risk status is not scraped from Sentry or HTML pages. When no documented
machine-readable risk field is returned, the result states that explicitly.
"""

from __future__ import annotations

import json
import logging
import math
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Callable, Optional

logger = logging.getLogger("stellar_archive_bridge.apophis_tracker")

SBDB_URL = "https://ssd-api.jpl.nasa.gov/sbdb.api"
HORIZONS_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"

APOPHIS_SEARCH = "99942"
APOPHIS_ENCOUNTER_ISO = "2029-04-13T00:00:00Z"
MIN_REFRESH_INTERVAL_SEC = 60
REQUEST_TIMEOUT_SEC = 12
MAX_RESPONSE_BYTES = 512 * 1024

ALLOWED_HOSTS = frozenset({"ssd-api.jpl.nasa.gov", "ssd.jpl.nasa.gov"})

_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_APRIL_2029_CD_RE = re.compile(r"2029[-\s]Apr", re.IGNORECASE)
_SOE_EOE_RE = re.compile(r"\$\$SOE\s*(.*?)\s*\$\$EOE", re.DOTALL)


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


def is_allowed_url(url: str | None) -> bool:
    if not url or not isinstance(url, str):
        return False
    try:
        parsed = urllib.parse.urlparse(url.strip())
    except Exception:  # noqa: BLE001
        return False
    if parsed.scheme != "https":
        return False
    host = (parsed.hostname or "").lower()
    return host in ALLOWED_HOSTS or host.endswith(".jpl.nasa.gov")


def _default_fetch(url: str, timeout: float) -> dict | str:
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "FOXAI-StellarCartography/0.4"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise ValueError("Response too large")
        text = raw.decode("utf-8")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text


def compute_countdown_days(encounter_iso: str = APOPHIS_ENCOUNTER_ISO) -> int | None:
    try:
        encounter = datetime.fromisoformat(encounter_iso.replace("Z", "+00:00"))
    except ValueError:
        return None
    now = datetime.now(timezone.utc)
    delta = encounter.date() - now.date()
    return delta.days


def _is_earth_body(body: str | None) -> bool:
    return bool(body and body.lower().startswith("earth"))


def _pick_april_2029_earth_encounter(ca_data: list | None) -> dict | None:
    """Select the documented April 2029 Earth close approach, never the first row."""
    if not isinstance(ca_data, list):
        return None
    matches: list[dict] = []
    for row in ca_data:
        if not isinstance(row, dict):
            continue
        body = sanitize_text(row.get("body"), max_len=20)
        if not _is_earth_body(body):
            continue
        cd = sanitize_text(row.get("cd"), max_len=40) or ""
        if _APRIL_2029_CD_RE.search(cd):
            matches.append(row)
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        return matches[0]
    return None


def parse_sbdb_response(payload: dict) -> dict:
    if not isinstance(payload, dict):
        return {"ok": False, "status": "malformed", "error": "Unexpected SBDB response."}

    obj = payload.get("object")
    if not isinstance(obj, dict):
        code = payload.get("code")
        msg = sanitize_text(payload.get("message"), max_len=200)
        return {
            "ok": False,
            "status": "not_found" if code == "300" else "error",
            "error": msg or "Object not found in SBDB.",
        }

    ca_row = _pick_april_2029_earth_encounter(payload.get("ca_data"))
    encounter_date = None
    nominal_distance_au = None
    encounter_date_unavailable = False
    if ca_row:
        encounter_date = sanitize_text(ca_row.get("cd") or ca_row.get("jd"), max_len=40)
        try:
            nominal_distance_au = float(ca_row.get("dist"))
        except (TypeError, ValueError):
            nominal_distance_au = None
    else:
        encounter_date_unavailable = True

    designation = sanitize_text(obj.get("des") or obj.get("fullname"), max_len=40)
    name = sanitize_text(obj.get("name") or obj.get("fullname"), max_len=80)
    spkid = sanitize_text(obj.get("spkid"), max_len=20)

    return {
        "ok": True,
        "status": "ok",
        "designation": designation or "99942",
        "name": name or "99942 Apophis",
        "spkid": spkid,
        "encounter_date": encounter_date,
        "encounter_date_unavailable": encounter_date_unavailable,
        "nominal_close_approach_distance_au": nominal_distance_au,
        "risk_status": None,
        "risk_status_available": False,
        "risk_status_notice": (
            "Current official risk status was not retrieved automatically. "
            "Check the official source."
        ),
        "source_agency": "NASA/JPL CNEOS",
        "source_links": {
            "sbdb": f"https://ssd.jpl.nasa.gov/tools/sbdb_lookup.html#/?sstr={APOPHIS_SEARCH}",
            "cneos": "https://cneos.jpl.nasa.gov/",
        },
    }


def _round_observer(value: object, decimals: int = 2) -> float | None:
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(num):
        return None
    return round(num, decimals)


def build_horizons_url(
    *,
    observer_lat: float | None = None,
    observer_lon: float | None = None,
    observer_alt_m: float | None = None,
) -> str:
    params = {
        "format": "json",
        "COMMAND": "'2099942'",
        "EPHEM_TYPE": "'OBSERVER'",
        "CENTER": "'500@399'" if observer_lat is None or observer_lon is None else "'coord@399'",
        "START_TIME": "'now'",
        "STOP_TIME": "'now'",
        "QUANTITIES": "'1,9,20'",
        "CAL_FORMAT": "'CAL'",
        "TIME_DIGITS": "'MINUTES'",
        "ANG_FORMAT": "'DEG'",
    }
    if observer_lat is not None and observer_lon is not None:
        alt_km = (observer_alt_m or 0.0) / 1000.0
        lon = _round_observer(observer_lon, 2)
        lat = _round_observer(observer_lat, 2)
        params["SITE_COORD"] = f"'{lon},{lat},{round(alt_km, 1)}'"
    query = urllib.parse.urlencode(params)
    return f"{HORIZONS_URL}?{query}"


def extract_horizons_ephemeris_section(text: str) -> str | None:
    match = _SOE_EOE_RE.search(text)
    if not match:
        return None
    return match.group(1).strip()


def _parse_ephemeris_data_line(line: str) -> dict | None:
    parts = [p.strip() for p in line.split(",")]
    if len(parts) < 4:
        return None
    joined = line.lower()
    if "r.a" in joined or joined.startswith("date") or "$" in line:
        return None
    if not parts[0] or parts[0][0] not in "0123456789":
        return None
    try:
        ra_deg = float(parts[1])
        dec_deg = float(parts[2])
        distance_au = float(parts[3])
    except (IndexError, ValueError):
        return None
    if not math.isfinite(ra_deg) or not math.isfinite(dec_deg) or not math.isfinite(distance_au):
        return None
    if ra_deg < 0.0 or ra_deg > 360.0:
        return None
    if dec_deg < -90.0 or dec_deg > 90.0:
        return None
    epoch = sanitize_text(parts[0], max_len=40)
    return {
        "ra_deg": ra_deg,
        "dec_deg": dec_deg,
        "distance_au": distance_au,
        "epoch": epoch,
    }


def parse_horizons_result_text(text: str) -> dict:
    section = extract_horizons_ephemeris_section(text)
    if not section:
        return {
            "ok": False,
            "status": "malformed",
            "error": "Horizons response missing ephemeris section ($$SOE/$$EOE).",
        }
    for line in section.splitlines():
        line = line.strip()
        if not line:
            continue
        parsed = _parse_ephemeris_data_line(line)
        if parsed:
            return {"ok": True, "status": "ok", **parsed}
    return {
        "ok": False,
        "status": "malformed",
        "error": "Could not parse Horizons ephemeris rows.",
    }


def parse_horizons_observer_text(text: str) -> dict:
    """Backward-compatible alias for tests and text-only payloads."""
    return parse_horizons_result_text(text)


def parse_horizons_response(payload: dict | str) -> dict:
    if isinstance(payload, dict):
        result = payload.get("result")
        if isinstance(result, str):
            return parse_horizons_result_text(result)
        return {"ok": False, "status": "malformed", "error": "Unexpected Horizons JSON response."}
    if isinstance(payload, str):
        return parse_horizons_result_text(payload)
    return {"ok": False, "status": "malformed", "error": "Could not parse Horizons ephemeris."}


def lookup_apophis_tracker(
    *,
    observer_lat: float | None = None,
    observer_lon: float | None = None,
    observer_alt_m: float | None = None,
    fetcher: Optional[Callable[[str, float], dict | str]] = None,
    timeout: float = REQUEST_TIMEOUT_SEC,
) -> dict:
    fetch = fetcher or _default_fetch
    retrieved_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    sbdb_url = (
        f"{SBDB_URL}?sstr={urllib.parse.quote(APOPHIS_SEARCH)}"
        f"&ca-data=1&ca-body=Earth&ca-time=cd&full-prec=1"
    )
    try:
        sbdb_payload = fetch(sbdb_url, timeout)
    except TimeoutError:
        return {"ok": False, "status": "timeout", "error": "JPL SBDB did not respond in time.", "retrieved_at": retrieved_at}
    except urllib.error.HTTPError as exc:
        return {
            "ok": False,
            "status": "http_error",
            "error": f"JPL SBDB returned HTTP {exc.code}.",
            "retrieved_at": retrieved_at,
        }
    except (urllib.error.URLError, OSError, ValueError):
        logger.info("Apophis SBDB lookup failed", exc_info=True)
        return {"ok": False, "status": "error", "error": "Could not retrieve Apophis SBDB data.", "retrieved_at": retrieved_at}

    if not isinstance(sbdb_payload, dict):
        return {"ok": False, "status": "malformed", "error": "Unexpected SBDB response.", "retrieved_at": retrieved_at}

    normalized = parse_sbdb_response(sbdb_payload)
    normalized["retrieved_at"] = retrieved_at
    normalized["countdown_days"] = compute_countdown_days()
    normalized["encounter_date_documented"] = APOPHIS_ENCOUNTER_ISO
    normalized["countdown_notice"] = (
        "Countdown is calculated locally from the documented April 2029 close-encounter date; "
        "it is not a live risk assessment."
    )

    observer_used = None
    if observer_lat is not None and observer_lon is not None:
        observer_used = {
            "latitude_deg": _round_observer(observer_lat, 2),
            "longitude_deg": _round_observer(observer_lon, 2),
            "altitude_m": _round_observer(observer_alt_m or 0.0, 0),
            "source": "client_supplied",
        }
    else:
        observer_used = {"source": "geocentric_fallback", "center": "500@399 (Earth geocenter)"}

    normalized["observer_context"] = observer_used
    normalized["observer_privacy_notice"] = (
        "Observer coordinates are sent to JPL Horizons only when you request ephemeris refresh "
        "and Stellarium (or you) supply them. Values are rounded before transmission. "
        "When unavailable, a geocentric fallback is used."
    )

    horizons_url = build_horizons_url(
        observer_lat=observer_lat,
        observer_lon=observer_lon,
        observer_alt_m=observer_alt_m,
    )
    try:
        horizons_payload = fetch(horizons_url, timeout)
        ephem = parse_horizons_response(horizons_payload)
    except Exception:  # noqa: BLE001
        ephem = {"ok": False, "status": "unavailable", "error": "Observer ephemeris unavailable."}

    normalized["ephemeris"] = ephem
    normalized["ephemeris_epoch"] = retrieved_at if ephem.get("ok") else None
    return normalized
