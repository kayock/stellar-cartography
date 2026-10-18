"""
stellarium_client.py

Talks to a locally-running Stellarium Remote Control plug-in
(https://stellarium.org, "Remote Control" plug-in, default localhost:8090).

Design goals:
    * Never crash the bridge app if Stellarium is closed, the plug-in is
      disabled, or nothing is selected.
    * Treat the JSON shape as version-variable. Only ever log a *sanitized*
      shape description (top-level key names + value types) on parse
      failure -- never raw field values, since those could (in principle)
      contain user-entered object notes.
    * Selection and status remain GET-only.
    * Time/location writes happen only through explicit Time Machine helpers
      (POST /api/main/time, /api/location/setlocationfields, /api/stelaction/do).
"""

from __future__ import annotations

import json
import logging
import math
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Optional

from . import coords

logger = logging.getLogger("stellar_archive_bridge.stellarium_client")

DEFAULT_BASE_URL = "http://127.0.0.1:8090"
DEFAULT_TIMEOUT_SECONDS = 2.5

# Stellarium selection payloads are small JSON objects (a few KB at most).
# Cap what we'll read to guard against a misbehaving endpoint on the port.
MAX_RESPONSE_BYTES = 2 * 1024 * 1024  # 2 MB


class ResponseTooLargeError(Exception):
    pass


@dataclass
class SelectionResult:
    ok: bool
    connected: bool
    name: Optional[str] = None
    alt_name: Optional[str] = None
    object_category: Optional[str] = None  # Stellarium's documented "type" field (e.g. "Nebula")
    object_type: Optional[str] = None  # Stellarium's documented "object-type" field (e.g. "galaxy")
    object_subtype: Optional[str] = None
    catalogue_designations: Optional[str] = None
    constellation: Optional[str] = None
    apparent_magnitude: Optional[float] = None
    angular_size_deg: Optional[float] = None
    altitude_deg: Optional[float] = None
    azimuth_deg: Optional[float] = None
    above_horizon: Optional[bool] = None
    ra_deg: Optional[float] = None
    dec_deg: Optional[float] = None
    ra_sexagesimal: Optional[str] = None
    dec_sexagesimal: Optional[str] = None
    # fov_deg is NOT part of Stellarium's selected-object response. It is
    # read separately from GET /api/main/status ("view.fov") and merged in
    # here for convenience. It is always optional: failure to obtain it
    # must never prevent a selection from succeeding.
    fov_deg: Optional[float] = None
    error: Optional[str] = None
    raw_shape: Optional[dict] = field(default=None, repr=False)


class StellariumClient:
    def __init__(self, base_url: str = DEFAULT_BASE_URL, timeout: float = DEFAULT_TIMEOUT_SECONDS):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    # -- low level -----------------------------------------------------

    def _get_json(self, path: str) -> Any:
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(url, method="GET", headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # nosec B310 - local-only, fixed scheme
            raw = resp.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise ResponseTooLargeError(
                f"Stellarium response exceeded {MAX_RESPONSE_BYTES} bytes; refusing to parse."
            )
        return json.loads(raw.decode("utf-8"))

    # -- public API ------------------------------------------------------

    def check_connection(self) -> bool:
        """Lightweight reachability check. Any HTTP response counts as
        'connected' even if the specific endpoint 404s, since that still
        proves the Remote Control plug-in is listening.

        Semantics (documented per the repair request):
          * Network unreachable (can't open a socket / times out / DNS,
            etc.): connected=False -- nothing is listening.
          * A real HTTP response came back, even if its body is
            malformed/non-JSON/non-UTF-8/oversized, or the endpoint 404s:
            connected=True. Something *is* listening and answering HTTP on
            this port -- that's everything this lightweight check claims
            to know. It never inspects, returns, or logs the raw response
            body/content; parsing that body is /api/selection's job, and
            failures there are reported separately.
        """
        try:
            self._get_json("/api/main/status")
            return True
        except urllib.error.HTTPError:
            # Plug-in is listening but this particular endpoint errored --
            # still counts as reachable.
            return True
        except (urllib.error.URLError, OSError, TimeoutError):
            return False
        except (json.JSONDecodeError, UnicodeDecodeError, ResponseTooLargeError) as exc:
            # Something answered on this port with an HTTP response, but
            # its body wasn't parseable JSON (malformed JSON, invalid
            # UTF-8) or exceeded MAX_RESPONSE_BYTES. That's still a real
            # response from a real listener -- log only the sanitized
            # exception type/reason (never raw response bytes) and treat
            # it as reachable rather than letting the exception propagate
            # and take down the /api/status request handler.
            logger.warning(
                "Stellarium /api/main/status reachability check got an unparseable response (%s): %s",
                exc.__class__.__name__,
                exc,
            )
            return True

    def get_selection(self) -> SelectionResult:
        try:
            payload = self._get_json("/api/objects/info?format=json")
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            return SelectionResult(
                ok=False,
                connected=False,
                error=f"Could not reach Stellarium Remote Control on {self.base_url} ({exc.__class__.__name__}).",
            )
        except json.JSONDecodeError as exc:
            logger.warning("Stellarium returned malformed JSON: %s", exc)
            return SelectionResult(
                ok=False,
                connected=True,
                error="Stellarium responded but sent malformed JSON.",
            )
        except ResponseTooLargeError as exc:
            logger.warning("Stellarium response rejected: %s", exc)
            return SelectionResult(
                ok=False,
                connected=True,
                error="Stellarium's response was unexpectedly large and was rejected.",
            )

        result = self._parse_selection_payload(payload)
        if result.ok:
            result.fov_deg = self._get_fov_from_main_status()
        return result

    def _get_fov_from_main_status(self) -> Optional[float]:
        """Read the current field of view from GET /api/main/status
        ("view.fov"). The selected-object response does not carry FoV, so
        this is always a separate request. Any failure here (unreachable,
        malformed, missing field) yields None rather than raising --
        failing to obtain FoV must never prevent selection from
        succeeding."""
        try:
            status_payload = self._get_json("/api/main/status")
        except (urllib.error.URLError, OSError, TimeoutError, json.JSONDecodeError, ResponseTooLargeError):
            return None
        if not isinstance(status_payload, dict):
            return None
        view = status_payload.get("view")
        if not isinstance(view, dict):
            return None
        fov = view.get("fov")
        if isinstance(fov, (int, float)) and not isinstance(fov, bool):
            fov = float(fov)
            return fov if math.isfinite(fov) else None
        if isinstance(fov, str):
            try:
                fov = float(fov.strip())
            except ValueError:
                return None
            return fov if math.isfinite(fov) else None
        return None

    # -- parsing -----------------------------------------------------------

    def _parse_selection_payload(self, payload: Any) -> SelectionResult:
        if not isinstance(payload, dict) or not payload:
            self._log_sanitized_shape(payload, reason="empty or non-object payload")
            return SelectionResult(
                ok=False,
                connected=True,
                error="Nothing is currently selected in Stellarium.",
            )

        name = _first_str(payload, ("name", "english-name", "englishName", "designation"))
        alt_name = _first_str(
            payload,
            ("localized-name", "localizedName", "name-i18n", "alt-name", "altName"),
        )
        # Stellarium's documented shape distinguishes a broad "type" (e.g.
        # "Nebula") from a more specific "object-type" (e.g. "galaxy").
        # These are kept as two separate, tolerant fields rather than
        # merged, per the "Object category" / "Detailed type" UI labels.
        object_category = _first_str(payload, ("type", "objectCategory"))
        object_type = _first_str(payload, ("object-type", "objectType", "otype"))
        object_subtype = _first_str(
            payload,
            ("morpho-type", "morphological-type", "morphologicalType", "subtype", "object-subtype", "sp-type", "spectral-type"),
        )
        catalogue_designations = _first_str(
            payload,
            (
                "catalog-descriptions",
                "catalog-designations",
                "catalogDesignations",
                "extra-designations",
                "extraDesignations",
                "other-designations",
                "aka",
                "designations",
            ),
        )
        constellation = _first_str(
            payload,
            ("constellation", "iau-constellation", "iauConstellation", "constellation-abbreviation", "const"),
        )
        apparent_magnitude = _first_float(payload, ("vmag", "mag", "magnitude", "apparent-magnitude", "apparentMagnitude"))
        if apparent_magnitude is not None and abs(apparent_magnitude) > 40:
            # Real apparent magnitudes span roughly -27 (Sun) to about +30
            # (faintest telescopic detections). Values far outside that are
            # almost always a catalog's "unknown" sentinel (e.g. 99, -99),
            # not real data -- don't display them as if they were.
            apparent_magnitude = None

        coord_result = coords.extract_j2000_radec(payload)
        if not coord_result.ok:
            self._log_sanitized_shape(payload, reason=coord_result.reason or "coordinate extraction failed")
            return SelectionResult(
                ok=False,
                connected=True,
                error="Stellarium's selection response did not contain a recognizable "
                "RA/Dec representation. See the log for the sanitized field shape.",
            )

        angular_size_deg = _first_float(payload, ("size-dd", "angular-size-dd", "sizeDd"))
        altitude_deg = _first_float(payload, ("altitude", "alt"))
        azimuth_deg = _first_float(payload, ("azimuth", "az"))
        above_horizon = _first_bool(payload, ("above-horizon", "aboveHorizon"))

        return SelectionResult(
            ok=True,
            connected=True,
            name=name or "Unnamed object",
            alt_name=alt_name,
            object_category=object_category,
            object_type=object_type,
            object_subtype=object_subtype,
            catalogue_designations=catalogue_designations,
            constellation=constellation,
            apparent_magnitude=apparent_magnitude,
            angular_size_deg=angular_size_deg,
            altitude_deg=altitude_deg,
            azimuth_deg=azimuth_deg,
            above_horizon=above_horizon,
            ra_deg=coord_result.ra_deg,
            dec_deg=coord_result.dec_deg,
            ra_sexagesimal=coords.format_sexagesimal_ra(coord_result.ra_deg),
            dec_sexagesimal=coords.format_sexagesimal_dec(coord_result.dec_deg),
            # fov_deg is filled in separately by get_selection() from
            # GET /api/main/status -- it is never present in this payload.
        )

    @staticmethod
    def _log_sanitized_shape(payload: Any, reason: str) -> None:
        """Log only the *shape* of a failed response (key names + value
        types), never raw values, to help diagnose version drift without
        leaking potentially sensitive content into logs."""
        if isinstance(payload, dict):
            shape = {k: type(v).__name__ for k, v in payload.items()}
        else:
            shape = {"__root_type__": type(payload).__name__}
        logger.warning("Stellarium selection parse failed (%s). Sanitized shape: %s", reason, shape)

    def get_main_status(self) -> Any:
        """Return GET /api/main/status JSON, or None on transport failure."""
        try:
            return self._get_json("/api/main/status")
        except (urllib.error.URLError, OSError, TimeoutError, json.JSONDecodeError, ResponseTooLargeError):
            return None

    def get_objects_info_raw(self) -> Any:
        try:
            return self._get_json("/api/objects/info?format=json")
        except (urllib.error.URLError, OSError, TimeoutError, json.JSONDecodeError, ResponseTooLargeError):
            return None

    def _post_form(self, path: str, fields: dict) -> bool:
        url = f"{self.base_url}{path}"
        body = urllib.parse.urlencode(fields).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # nosec B310 - local-only, fixed scheme
                resp.read(256)
            return True
        except (urllib.error.URLError, OSError, TimeoutError, urllib.error.HTTPError):
            return False

    def apply_time(self, jday: float, timerate: float = 0.0) -> bool:
        rate = "0" if float(timerate) == 0 else str(timerate)
        return self._post_form("/api/main/time", {"time": f"{float(jday):.8f}", "timerate": rate})

    def return_to_now(self) -> bool:
        return self._post_form("/api/stelaction/do", {"id": "actionReturn_To_Current_Time"})

    def apply_location(
        self,
        latitude: float,
        longitude: float,
        altitude: float = 0.0,
        name: str = "",
        planet: str = "Earth",
    ) -> bool:
        return self._post_form(
            "/api/location/setlocationfields",
            {
                "latitude": f"{float(latitude):.8f}",
                "longitude": f"{float(longitude):.8f}",
                "altitude": str(int(round(float(altitude)))),
                "name": name or "Cartography location",
                "planet": planet or "Earth",
            },
        )

    def focus_object(self, target: str) -> bool:
        """Select and center an object in the existing Stellarium session."""
        name = (target or "").strip()
        if not name or len(name) > 160:
            return False
        return self._post_form("/api/main/focus", {"target": name})

    def set_fov(self, fov_deg: float) -> bool:
        if not isinstance(fov_deg, (int, float)) or isinstance(fov_deg, bool):
            return False
        value = float(fov_deg)
        if not math.isfinite(value) or value <= 0 or value > 240:
            return False
        return self._post_form("/api/main/fov", {"fov": f"{value:.4f}"})

    def get_stel_properties(self) -> dict:
        try:
            payload = self._get_json("/api/stelproperty/list")
        except (urllib.error.URLError, OSError, TimeoutError, json.JSONDecodeError, ResponseTooLargeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def get_sky_culture_id(self) -> Optional[str]:
        entry = self.get_stel_properties().get("StelSkyCultureMgr.currentSkyCultureID")
        if isinstance(entry, dict):
            value = entry.get("value")
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    def get_constellation_properties(self) -> dict:
        return self.get_stel_properties()

    def set_stel_property(self, prop_id: str, value: Any) -> bool:
        name = (prop_id or "").strip()
        if not name or len(name) > 160:
            return False
        if isinstance(value, bool):
            encoded = "true" if value else "false"
        else:
            encoded = str(value)
        return self._post_form("/api/stelproperty/set", {"id": name, "value": encoded})



def _first_str(payload: dict, keys: tuple) -> Optional[str]:
    for key in keys:
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return None


def _first_float(payload: dict, keys: tuple) -> Optional[float]:
    """Return the first finite numeric value found under `keys`.

    NaN/Infinity/-Infinity (numeric or numeric-string) are treated as
    absent: this optional metadata (magnitude, angular size, altitude,
    azimuth) is simply omitted rather than surfaced as a bogus value.
    """
    for key in keys:
        val = payload.get(key)
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


def _first_bool(payload: dict, keys: tuple) -> Optional[bool]:
    for key in keys:
        if key not in payload:
            continue
        val = payload[key]
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            lowered = val.strip().lower()
            if lowered in ("true", "1", "yes"):
                return True
            if lowered in ("false", "0", "no"):
                return False
    return None
