"""
mast_archive.py

Server-side MAST CAOM archive-availability lookups for Hubble and JWST
(HST / JWST NIRCam / JWST MIRI only).

Uses the official MAST Portal API v0 (https://mast.stsci.edu/api/v0/) with
``Mast.Caom.Filtered.Position`` for cone search plus mission/instrument filters.
No API key required.

Observation counts are CAOM observation records near the coordinates — not
unique photographs and not proof of public preview availability.
"""

from __future__ import annotations

import json
import logging
import math
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Callable, Optional

logger = logging.getLogger("stellar_archive_bridge.mast_archive")

MAST_INVOKE_URL = "https://mast.stsci.edu/api/v0/invoke"
ALLOWED_HOSTS = frozenset({"mast.stsci.edu"})
ALLOWED_MAST_LINK_HOSTS = frozenset({"mast.stsci.edu", "archive.stsci.edu"})

REQUEST_TIMEOUT_SEC = 10
MAX_RESPONSE_BYTES = 512 * 1024
MAX_OBSERVATIONS = 25

# Documented default: 0.01° (~36 arcsec) cone search radius.
ARCHIVE_SEARCH_RADIUS_DEG = 0.01

_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_UNSAFE_URL_CHAR_RE = re.compile(r'[\s"\'<>]')

MISSION_CONFIGS: dict[str, dict] = {
    "hst": {
        "label": "Hubble",
        "obs_collection": "HST",
        "instrument_match": None,
    },
    "jwst_nircam": {
        "label": "JWST NIRCam",
        "obs_collection": "JWST",
        "instrument_match": "NIRCam",
    },
    "jwst_miri": {
        "label": "JWST MIRI",
        "obs_collection": "JWST",
        "instrument_match": "MIRI",
    },
}


def normalize_mission(raw: str | None) -> str | None:
    if not raw or not isinstance(raw, str):
        return None
    key = raw.strip().lower()
    return key if key in MISSION_CONFIGS else None


def normalize_coords(ra_deg: object, dec_deg: object) -> tuple[float, float] | None:
    try:
        ra = float(ra_deg)
        dec = float(dec_deg)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(ra) or not math.isfinite(dec):
        return None
    ra = ra % 360.0
    if dec < -90.0 or dec > 90.0:
        return None
    return ra, dec


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


def is_allowed_source_url(url: str | None) -> bool:
    if not url or not isinstance(url, str):
        return False
    if _UNSAFE_URL_CHAR_RE.search(url):
        return False
    try:
        parsed = urllib.parse.urlparse(url.strip())
    except Exception:  # noqa: BLE001
        return False
    if parsed.scheme != "https":
        return False
    if parsed.username or parsed.password:
        return False
    host = (parsed.hostname or "").lower()
    return host in ALLOWED_MAST_LINK_HOSTS


def _build_filters(cfg: dict) -> list[dict]:
    filters: list[dict] = [
        {"paramName": "obs_collection", "values": [cfg["obs_collection"]]},
    ]
    instrument = cfg.get("instrument_match")
    if instrument:
        filters.append(
            {
                "paramName": "instrument_name",
                "values": [],
                "freeText": f"%{instrument}%",
            }
        )
    return filters


def build_count_request(ra_deg: float, dec_deg: float, mission: str) -> dict:
    cfg = MISSION_CONFIGS[mission]
    position = f"{ra_deg}, {dec_deg}, {ARCHIVE_SEARCH_RADIUS_DEG}"
    return {
        "service": "Mast.Caom.Filtered.Position",
        "params": {
            "columns": "COUNT_BIG(*)",
            "filters": _build_filters(cfg),
            "position": position,
        },
        "format": "json",
        "timeout": REQUEST_TIMEOUT_SEC,
    }


def build_list_request(ra_deg: float, dec_deg: float, mission: str) -> dict:
    cfg = MISSION_CONFIGS[mission]
    position = f"{ra_deg}, {dec_deg}, {ARCHIVE_SEARCH_RADIUS_DEG}"
    return {
        "service": "Mast.Caom.Filtered.Position",
        "params": {
            "columns": "obs_id,obs_collection,instrument_name,t_min,t_max,cal_start_time,dataproduct_type,intentType",
            "filters": _build_filters(cfg),
            "position": position,
        },
        "format": "json",
        "pagesize": MAX_OBSERVATIONS,
        "page": 1,
        "removenullcolumns": True,
        "timeout": REQUEST_TIMEOUT_SEC,
    }


def _default_fetch(request_obj: dict, timeout: float) -> dict:
    body = urllib.parse.urlencode({"request": json.dumps(request_obj)}).encode("utf-8")
    req = urllib.request.Request(
        MAST_INVOKE_URL,
        data=body,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "FOXAI-StellarCartography/0.4",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise ValueError("Response too large")
        return json.loads(raw.decode("utf-8"))


def _extract_count(payload: dict) -> int | None:
    if not isinstance(payload, dict):
        return None
    if payload.get("status") not in (None, "COMPLETE", "OK"):
        return None
    data = payload.get("data")
    if not isinstance(data, list) or not data:
        return 0
    row = data[0]
    if not isinstance(row, dict):
        return None
    for key in ("COUNT_BIG(*)", "count", "COUNT"):
        if key in row:
            try:
                return int(row[key])
            except (TypeError, ValueError):
                return None
    return None


def _format_obs_date(row: dict) -> str | None:
    for key in ("cal_start_time", "t_min", "t_max"):
        val = sanitize_text(row.get(key), max_len=40)
        if val:
            return val
    return None


def _preview_available(row: dict) -> bool:
    intent = sanitize_text(row.get("intentType"), max_len=40)
    product = sanitize_text(row.get("dataproduct_type"), max_len=40)
    if intent and "science" in intent.lower():
        return True
    if product and product.lower() in {"image", "preview", "public"}:
        return True
    return False


def _observation_rows(payload: dict, mission: str) -> list[dict]:
    if not isinstance(payload, dict):
        return []
    if payload.get("status") not in (None, "COMPLETE", "OK"):
        return []
    data = payload.get("data")
    if not isinstance(data, list):
        return []
    cfg = MISSION_CONFIGS[mission]
    results: list[dict] = []
    for row in data[:MAX_OBSERVATIONS]:
        if not isinstance(row, dict):
            continue
        obs_id = sanitize_text(row.get("obs_id"), max_len=80)
        if not obs_id:
            continue
        instrument = sanitize_text(row.get("instrument_name"), max_len=80)
        source_link = f"https://mast.stsci.edu/portal/Mashup/Clients/Mast/Portal/Mast.html?obsid={urllib.parse.quote(obs_id)}"
        if not is_allowed_source_url(source_link):
            source_link = None
        results.append(
            {
                "mission": cfg["label"],
                "instrument": instrument,
                "observation_id": obs_id,
                "observation_date": _format_obs_date(row),
                "preview_available": _preview_available(row),
                "source_link": source_link,
            }
        )
    return results


def _build_result(
    *,
    ok: bool,
    status: str,
    mission: str | None = None,
    count: int | None = None,
    observations: list[dict] | None = None,
    search_radius_deg: float = ARCHIVE_SEARCH_RADIUS_DEG,
    error: str | None = None,
) -> dict:
    cfg = MISSION_CONFIGS.get(mission or "", {})
    return {
        "ok": ok,
        "status": status,
        "mission": mission,
        "mission_label": cfg.get("label"),
        "count": count,
        "observations": observations or [],
        "search_radius_deg": search_radius_deg,
        "count_semantics": (
            "CAOM observation records within the search cone matching mission/instrument filters. "
            "This is not a count of unique photographs and does not prove preview availability "
            "at the selected coordinates."
        ),
        "error": sanitize_text(error, max_len=200),
    }


def parse_mast_count_response(payload: dict, mission: str) -> dict:
    count = _extract_count(payload)
    if count is None:
        return _build_result(
            ok=False,
            status="malformed",
            mission=mission,
            error="Archive service returned an unexpected response.",
        )
    if count <= 0:
        return _build_result(ok=True, status="no_coverage", mission=mission, count=0, observations=[])
    return _build_result(ok=True, status="confirmed", mission=mission, count=count)


def lookup_archive_availability(
    ra_deg: float,
    dec_deg: float,
    mission: str,
    *,
    include_observations: bool = False,
    fetcher: Optional[Callable[[dict, float], dict]] = None,
    timeout: float = REQUEST_TIMEOUT_SEC,
) -> dict:
    normalized = normalize_mission(mission)
    coords = normalize_coords(ra_deg, dec_deg)
    if not normalized:
        return _build_result(ok=False, status="error", error="Unsupported mission identifier.")
    if not coords:
        return _build_result(ok=False, status="error", mission=normalized, error="Invalid coordinates.")

    ra, dec = coords
    fetch = fetcher or _default_fetch

    try:
        count_payload = fetch(build_count_request(ra, dec, normalized), timeout)
    except TimeoutError:
        return _build_result(
            ok=False,
            status="unavailable",
            mission=normalized,
            error="Archive check unavailable (request timed out).",
        )
    except urllib.error.HTTPError as exc:
        return _build_result(
            ok=False,
            status="unavailable",
            mission=normalized,
            error=f"Archive check unavailable (HTTP {exc.code}).",
        )
    except (urllib.error.URLError, OSError, json.JSONDecodeError, ValueError):
        logger.info("MAST archive lookup failed mission=%s", normalized, exc_info=True)
        return _build_result(
            ok=False,
            status="unavailable",
            mission=normalized,
            error="Archive check unavailable.",
        )

    parsed = parse_mast_count_response(count_payload, normalized)
    if parsed["status"] != "confirmed" or not include_observations:
        return parsed

    try:
        list_payload = fetch(build_list_request(ra, dec, normalized), timeout)
    except Exception:  # noqa: BLE001
        return parsed

    observations = _observation_rows(list_payload, normalized)
    parsed["observations"] = observations
    return parsed
