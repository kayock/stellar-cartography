"""
coords.py

Tolerant coordinate extraction/normalization for Stellarium Remote Control
API responses.

Stellarium's *documented* getInfoMap JSON shape represents J2000 RA/Dec as
the numeric fields "raJ2000" and "decJ2000" (decimal degrees). Those are
this module's first-class, primary representation. Beyond that documented
shape, the response has also varied across Stellarium releases and plugin
versions in the wild, so this module additionally tolerates several other
shapes. It tries strategies, in order, and returns the first one that
produces a usable J2000 RA/Dec pair in decimal degrees:

    1. Direct decimal-degree fields -- numeric raJ2000 / decJ2000 (the
       documented Stellarium shape) plus several tolerated legacy/plugin
       aliases (e.g. raJ2000deg / decJ2000deg).
    2. Sexagesimal text fields under those *same* key names, e.g.
       raJ2000="0h42m44.3s", decJ2000="+41d16'9.4\"", "12:34:56.7",
       "-41 16 09" -- used when the value under raJ2000/decJ2000 isn't
       numeric.
    3. A J2000 unit direction vector (e.g. vX/vY/vZ or a 3-element list
       under a key such as "j2000Pos" or "jNowPos").

All results are normalized so that:
    * RA is wrapped into [0, 360).
    * Dec is clamped to [-90, 90] (and negative declinations are preserved
      correctly -- this is the most common source of parsing bugs).

Nothing in this module raises on unexpected input; callers get a
CoordinateResult with .ok describing success/failure plus a human-readable
reason for logging.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class CoordinateResult:
    ok: bool
    ra_deg: Optional[float] = None
    dec_deg: Optional[float] = None
    source: Optional[str] = None  # which strategy succeeded, for diagnostics
    reason: Optional[str] = None  # populated when ok is False


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

# Field name candidates, in priority order. Stellarium's *documented*
# getInfoMap JSON shape uses numeric "raJ2000"/"decJ2000" (decimal degrees)
# as its first-class coordinate fields, so those are tried first here.
# Several undocumented/legacy variants seen across versions/plugins are
# also tolerated as decimal fields. Because a value is only accepted by
# this strategy when it is actually numeric (or a numeric-looking string),
# the *same* key names ("raJ2000"/"decJ2000") safely fall through to the
# sexagesimal-text strategy below when Stellarium instead sends a
# sexagesimal string under that key -- there is no ambiguity between the
# two representations.
_RA_DECIMAL_KEYS = ("raJ2000", "raJ2000deg", "ra_j2000_deg", "raJ2000Deg", "raDeg", "ra_deg")
_DEC_DECIMAL_KEYS = ("decJ2000", "decJ2000deg", "dec_j2000_deg", "decJ2000Deg", "decDeg", "dec_deg")

_RA_TEXT_KEYS = ("raJ2000", "ra_j2000", "ra")
_DEC_TEXT_KEYS = ("decJ2000", "dec_j2000", "dec")

_VECTOR_KEYS = ("j2000Pos", "jnowPos", "j2000pos", "vec", "position", "direction")
_VECTOR_COMPONENT_SETS = (
    ("vX", "vY", "vZ"),
    ("x", "y", "z"),
    ("X", "Y", "Z"),
)


def extract_j2000_radec(payload: Any) -> CoordinateResult:
    """Try, in order, decimal fields -> sexagesimal text -> direction vector."""
    if not isinstance(payload, dict):
        return CoordinateResult(ok=False, reason="payload is not a JSON object")

    result = _try_decimal_fields(payload)
    if result.ok:
        return result

    result = _try_sexagesimal_fields(payload)
    if result.ok:
        return result

    result = _try_vector_fields(payload)
    if result.ok:
        return result

    return CoordinateResult(
        ok=False,
        reason="no recognizable RA/Dec representation found "
        "(tried decimal fields, sexagesimal text, and direction vector)",
    )


# ---------------------------------------------------------------------------
# Strategy 1: decimal degree fields
# ---------------------------------------------------------------------------

def _first_numeric(payload: dict, keys: tuple) -> Optional[float]:
    """Return the first finite numeric value found under `keys`.

    NaN, Infinity, and -Infinity (whether already numeric in the JSON, or
    parsed from a numeric-looking string such as "nan"/"inf"/"-infinity")
    are treated as though the field were absent, so callers never receive
    a non-finite value and downstream code never has to guard against it
    again.
    """
    for key in keys:
        if key in payload:
            val = payload[key]
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                fval = float(val)
                if math.isfinite(fval):
                    return fval
                continue
            if isinstance(val, str):
                try:
                    fval = float(val.strip())
                except ValueError:
                    continue
                if math.isfinite(fval):
                    return fval
                continue
    return None


def _try_decimal_fields(payload: dict) -> CoordinateResult:
    ra = _first_numeric(payload, _RA_DECIMAL_KEYS)
    dec = _first_numeric(payload, _DEC_DECIMAL_KEYS)
    if ra is None or dec is None:
        return CoordinateResult(ok=False)
    return _finalize(ra, dec, source="decimal_degree_fields")


# ---------------------------------------------------------------------------
# Strategy 2: sexagesimal text fields
# ---------------------------------------------------------------------------

# RA sexagesimal, hours-based: 0h42m44.3s / 0h 42m 44.3s / 0:42:44.3
_RA_SEXA_RE = re.compile(
    r"^\s*(?P<sign>[+-])?\s*(?P<h>\d+)\s*[h:]\s*(?P<m>\d+)\s*[m:]?\s*(?P<s>[\d.]+)\s*s?\s*$",
    re.IGNORECASE,
)

# Dec sexagesimal, degrees-based: +41d16'9.4" / -41d 16' 9.4" / -41:16:09 / 41 16 09
_DEC_SEXA_RE = re.compile(
    r"^\s*(?P<sign>[+-])?\s*(?P<d>\d+)\s*[d\u00b0:\s]\s*(?P<m>\d+)\s*['m:\s]?\s*(?P<s>[\d.]+)\s*[\"s]?\s*$",
    re.IGNORECASE,
)


def _parse_ra_sexagesimal(text: str) -> Optional[float]:
    match = _RA_SEXA_RE.match(text.strip())
    if not match:
        return None
    try:
        h = float(match.group("h"))
        m = float(match.group("m"))
        s = float(match.group("s"))
    except (TypeError, ValueError):
        return None
    hours = h + m / 60.0 + s / 3600.0
    deg = hours * 15.0
    if match.group("sign") == "-":
        # RA is not usually signed, but tolerate it defensively.
        deg = -deg
    return deg


def _parse_dec_sexagesimal(text: str) -> Optional[float]:
    match = _DEC_SEXA_RE.match(text.strip())
    if not match:
        return None
    try:
        d = float(match.group("d"))
        m = float(match.group("m"))
        s = float(match.group("s"))
    except (TypeError, ValueError):
        return None
    magnitude = d + m / 60.0 + s / 3600.0
    if match.group("sign") == "-":
        return -magnitude
    return magnitude


def _first_text(payload: dict, keys: tuple) -> Optional[str]:
    for key in keys:
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            return val
    return None


def _try_sexagesimal_fields(payload: dict) -> CoordinateResult:
    ra_text = _first_text(payload, _RA_TEXT_KEYS)
    dec_text = _first_text(payload, _DEC_TEXT_KEYS)
    if ra_text is None or dec_text is None:
        return CoordinateResult(ok=False)

    ra = _parse_ra_sexagesimal(ra_text)
    dec = _parse_dec_sexagesimal(dec_text)
    if ra is None or dec is None:
        return CoordinateResult(
            ok=False,
            reason=f"sexagesimal text present but unparsable (ra={ra_text!r}, dec={dec_text!r})",
        )
    return _finalize(ra, dec, source="sexagesimal_text_fields")


# ---------------------------------------------------------------------------
# Strategy 3: J2000 unit direction vector
# ---------------------------------------------------------------------------

def _try_vector_fields(payload: dict) -> CoordinateResult:
    # Case A: vector components directly on the payload (vX/vY/vZ, x/y/z...)
    for comp_keys in _VECTOR_COMPONENT_SETS:
        vals = [_first_numeric(payload, (k,)) for k in comp_keys]
        if all(v is not None for v in vals):
            return _vector_to_radec(*vals)

    # Case B: a nested list/tuple of 3 floats under a known key.
    for key in _VECTOR_KEYS:
        val = payload.get(key)
        if isinstance(val, (list, tuple)) and len(val) == 3:
            try:
                x, y, z = (float(v) for v in val)
            except (TypeError, ValueError):
                continue
            if not (math.isfinite(x) and math.isfinite(y) and math.isfinite(z)):
                continue
            return _vector_to_radec(x, y, z)
        if isinstance(val, dict):
            vals = [_first_numeric(val, (k,)) for k in ("x", "y", "z")]
            if all(v is not None for v in vals):
                return _vector_to_radec(*vals)

    return CoordinateResult(ok=False)


def _vector_to_radec(x: float, y: float, z: float) -> CoordinateResult:
    if not (math.isfinite(x) and math.isfinite(y) and math.isfinite(z)):
        return CoordinateResult(ok=False, reason="non-finite direction vector component")
    norm = math.sqrt(x * x + y * y + z * z)
    if norm == 0:
        return CoordinateResult(ok=False, reason="zero-length direction vector")
    x, y, z = x / norm, y / norm, z / norm
    ra = math.degrees(math.atan2(y, x))
    dec = math.degrees(math.asin(max(-1.0, min(1.0, z))))
    return _finalize(ra, dec, source="j2000_direction_vector")


# ---------------------------------------------------------------------------
# Shared normalization
# ---------------------------------------------------------------------------

def _finalize(ra_deg: float, dec_deg: float, source: str) -> CoordinateResult:
    if not math.isfinite(ra_deg) or not math.isfinite(dec_deg):
        return CoordinateResult(ok=False, reason="non-finite coordinate value (NaN or Infinity)")

    ra_norm = ra_deg % 360.0
    if ra_norm < 0:
        ra_norm += 360.0

    dec_clamped = max(-90.0, min(90.0, dec_deg))

    return CoordinateResult(ok=True, ra_deg=ra_norm, dec_deg=dec_clamped, source=source)


def _split_sexagesimal(total_units: float, unit_modulus: int) -> tuple:
    """Split a decimal quantity (hours or degrees) into (whole, minutes,
    seconds), rounding seconds to 2 decimal places and carrying any
    resulting 60.00 -> next minute, or 60 minutes -> next whole unit. This
    avoids display artefacts like '14h01m60.00s' that plain truncation
    produces due to floating-point rounding right at a boundary."""
    whole = int(total_units)
    m_total = (total_units - whole) * 60.0
    minutes = int(m_total)
    seconds = round((m_total - minutes) * 60.0, 2)

    if seconds >= 60.0:
        seconds -= 60.0
        minutes += 1
    if minutes >= 60:
        minutes -= 60
        whole += 1
    if unit_modulus:
        whole %= unit_modulus

    return whole, minutes, seconds


def format_sexagesimal_ra(ra_deg: float) -> str:
    hours_total = (ra_deg % 360.0) / 15.0
    h, m, s = _split_sexagesimal(hours_total, unit_modulus=24)
    return f"{h:02d}h{m:02d}m{s:05.2f}s"


def format_sexagesimal_dec(dec_deg: float) -> str:
    sign = "-" if dec_deg < 0 else "+"
    magnitude = abs(dec_deg)
    d, m, s = _split_sexagesimal(magnitude, unit_modulus=0)
    return f"{sign}{d:02d}d{m:02d}m{s:05.2f}s"


# ---------------------------------------------------------------------------
# Manual-entry parsing (used by the manual fallback form)
# ---------------------------------------------------------------------------

def parse_manual_ra(text: str) -> Optional[float]:
    """Accepts decimal degrees ('210.5') or sexagesimal RA ('14h02m00s').

    NaN, Infinity, and -Infinity -- whether typed directly (e.g. "nan",
    "inf", "-infinity", all valid Python float() spellings) or arising
    from a would-be sexagesimal parse -- are rejected outright (None)
    rather than silently normalized into a bogus value.
    """
    if text is None:
        return None
    text = text.strip()
    if not text:
        return None
    try:
        value = float(text)
    except ValueError:
        value = None
    if value is not None:
        if not math.isfinite(value):
            return None
        return value % 360.0 if value >= 0 else (value % 360.0 + 360.0) % 360.0
    ra = _parse_ra_sexagesimal(text)
    if ra is not None:
        if not math.isfinite(ra):
            return None
        norm = ra % 360.0
        return norm + 360.0 if norm < 0 else norm
    return None


def parse_manual_dec(text: str) -> Optional[float]:
    """Accepts decimal degrees ('-19.25') or sexagesimal Dec ('-19d15m00s').

    NaN, Infinity, and -Infinity are rejected outright (None) rather than
    silently clamped into a bogus in-range value.
    """
    if text is None:
        return None
    text = text.strip()
    if not text:
        return None
    try:
        value = float(text)
    except ValueError:
        value = None
    if value is not None:
        if not math.isfinite(value):
            return None
        return max(-90.0, min(90.0, value))
    dec = _parse_dec_sexagesimal(text)
    if dec is not None:
        if not math.isfinite(dec):
            return None
        return max(-90.0, min(90.0, dec))
    return None
