"""
server.py

A small local web application server built on the Python standard library
(http.server). It serves the FOXAI Stellar Cartography UI and exposes a
tiny read-only JSON API that proxies Stellarium's Remote Control plug-in.

This server talks to Stellarium locally and, when the browser requests
``/api/planetary-image`` (Online Archive Mode only on the client side),
proxies a minimal NASA Images API lookup using only the normalized pilot
target identifier (moon|jupiter|saturn). ESASky (sky.esa.int) traffic
remains browser-direct and is not proxied here.
"""

from __future__ import annotations

import json
import logging
import mimetypes
import os
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import apophis_tracker
from . import coords
from . import mast_archive
from . import planetary_image
from . import watchlist_store
from .stellarium_client import StellariumClient, SelectionResult

APP_ROOT = watchlist_store.resolve_app_root()

logger = logging.getLogger("stellar_archive_bridge.server")

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

# Only these extensions are ever served as static files, and only from
# STATIC_DIR (path traversal is blocked below regardless).
_ALLOWED_STATIC_EXTENSIONS = {".html", ".js", ".css", ".svg", ".png", ".ico", ".json"}


def _selection_to_dict(result: SelectionResult) -> dict:
    return {
        "ok": result.ok,
        "connected": result.connected,
        "name": result.name,
        "alt_name": result.alt_name,
        "object_category": result.object_category,
        "object_type": result.object_type,
        "object_subtype": result.object_subtype,
        "catalogue_designations": result.catalogue_designations,
        "constellation": result.constellation,
        "apparent_magnitude": result.apparent_magnitude,
        "angular_size_deg": result.angular_size_deg,
        "altitude_deg": result.altitude_deg,
        "azimuth_deg": result.azimuth_deg,
        "above_horizon": result.above_horizon,
        "ra_deg": result.ra_deg,
        "dec_deg": result.dec_deg,
        "ra_sexagesimal": result.ra_sexagesimal,
        "dec_sexagesimal": result.dec_sexagesimal,
        "fov_deg": result.fov_deg,
        "error": result.error,
    }


def make_handler(
    stellarium_client: StellariumClient,
    planetary_fetcher=None,
    archive_fetcher=None,
    apophis_fetcher=None,
    watchlist_root: str | None = None,
):
    class Handler(BaseHTTPRequestHandler):
        server_version = "FOXAIStellarCartography/0.4.0"

        def log_message(self, fmt, *args):  # quieter default logging
            logger.debug("%s - %s", self.address_string(), fmt % args)

        # -- helpers ---------------------------------------------------

        def _send_json(self, status: int, payload: dict) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _read_json_body(self, max_bytes: int = 256 * 1024) -> dict | None:
            length = int(self.headers.get("Content-Length", "0") or "0")
            if length <= 0 or length > max_bytes:
                return None
            raw = self.rfile.read(length)
            try:
                payload = json.loads(raw.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return None
            return payload if isinstance(payload, dict) else None

        def _send_static(self, rel_path: str) -> None:
            if rel_path in ("", "/"):
                rel_path = "index.html"
            rel_path = rel_path.lstrip("/")

            # Block path traversal defensively even though urlparse already
            # gives us a normalized path.
            safe_root = os.path.realpath(STATIC_DIR)
            candidate = os.path.realpath(os.path.join(STATIC_DIR, rel_path))
            if not candidate.startswith(safe_root + os.sep) and candidate != safe_root:
                self._send_json(403, {"error": "forbidden"})
                return

            _, ext = os.path.splitext(candidate)
            if ext not in _ALLOWED_STATIC_EXTENSIONS:
                self._send_json(404, {"error": "not found"})
                return

            if not os.path.isfile(candidate):
                self._send_json(404, {"error": "not found"})
                return

            content_type, _ = mimetypes.guess_type(candidate)
            content_type = content_type or "application/octet-stream"
            with open(candidate, "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        # -- routing -----------------------------------------------------

        def do_GET(self):  # noqa: N802 (stdlib naming convention)
            parsed = urlparse(self.path)
            path = parsed.path

            if path == "/api/status":
                # check_connection() already handles the documented failure
                # modes (unreachable, malformed/oversized/non-UTF-8
                # response) internally and never raises for those. This
                # try/except is a last-resort backstop so /api/status can
                # never take the request handler down with it regardless --
                # the bridge's own status endpoint must always answer with
                # valid JSON, even in the face of a completely unexpected
                # failure talking to whatever is on the configured port.
                try:
                    connected = stellarium_client.check_connection()
                except Exception:  # noqa: BLE001 - deliberate last-resort backstop
                    logger.exception("Unexpected error while checking Stellarium connection")
                    connected = False
                self._send_json(200, {"connected": connected})
                return

            if path == "/api/selection":
                result = stellarium_client.get_selection()
                status = 200 if result.ok else 200  # always 200; ok flag carries state
                self._send_json(status, _selection_to_dict(result))
                return

            if path == "/api/planetary-image":
                qs = parse_qs(parsed.query)
                target = (qs.get("target") or [""])[0]
                result = planetary_image.lookup_planetary_image(
                    target,
                    fetcher=planetary_fetcher,
                )
                self._send_json(200, result)
                return

            if path == "/api/archive-availability":
                qs = parse_qs(parsed.query)
                mission = (qs.get("mission") or [""])[0]
                ra_text = (qs.get("ra") or [""])[0]
                dec_text = (qs.get("dec") or [""])[0]
                include_obs = (qs.get("include_observations") or ["0"])[0] in ("1", "true", "yes")
                try:
                    ra = float(ra_text)
                    dec = float(dec_text)
                except ValueError:
                    self._send_json(
                        200,
                        mast_archive._build_result(
                            ok=False,
                            status="error",
                            error="Invalid coordinates.",
                        ),
                    )
                    return
                result = mast_archive.lookup_archive_availability(
                    ra,
                    dec,
                    mission,
                    include_observations=include_obs,
                    fetcher=archive_fetcher,
                )
                self._send_json(200, result)
                return

            if path == "/api/watchlist":
                root = watchlist_root or APP_ROOT
                result = watchlist_store.load_watchlist_result(root)
                payload = {
                    "ok": result["ok"],
                    "status": result["status"],
                    "document": result["document"],
                    "entry_count": result["entry_count"],
                    "storage_path": result["storage_path"],
                    "storage_path_relative": result["storage_path_relative"],
                    "recovered_from_backup": result["recovered_from_backup"],
                    "error": result["error"],
                }
                self._send_json(200 if result["ok"] else 500, payload)
                return

            if path == "/api/apophis-tracker":
                qs = parse_qs(parsed.query)
                lat = lon = alt = None
                if qs.get("observer_lat") and qs.get("observer_lon"):
                    try:
                        lat = float((qs.get("observer_lat") or [""])[0])
                        lon = float((qs.get("observer_lon") or [""])[0])
                        alt = float((qs.get("observer_alt") or ["0"])[0])
                    except ValueError:
                        lat = lon = alt = None
                result = apophis_tracker.lookup_apophis_tracker(
                    observer_lat=lat,
                    observer_lon=lon,
                    observer_alt_m=alt,
                    fetcher=apophis_fetcher,
                )
                self._send_json(200, result)
                return

            if path == "/api/manual/validate":
                qs = parse_qs(parsed.query)
                ra_text = (qs.get("ra") or [""])[0]
                dec_text = (qs.get("dec") or [""])[0]
                ra = coords.parse_manual_ra(ra_text)
                dec = coords.parse_manual_dec(dec_text)
                if ra is None or dec is None:
                    self._send_json(
                        200,
                        {
                            "ok": False,
                            "error": "Could not parse RA/Dec. Use decimal degrees "
                            "(e.g. 83.63) or sexagesimal (e.g. 05h35m17s / -05d23m28s).",
                        },
                    )
                    return
                self._send_json(
                    200,
                    {
                        "ok": True,
                        "ra_deg": ra,
                        "dec_deg": dec,
                        "ra_sexagesimal": coords.format_sexagesimal_ra(ra),
                        "dec_sexagesimal": coords.format_sexagesimal_dec(dec),
                    },
                )
                return

            if path.startswith("/static/"):
                self._send_static(path[len("/static/"):])
                return

            if path == "/" or path == "/index.html":
                self._send_static("index.html")
                return

            self._send_json(404, {"error": "not found"})

        def do_PUT(self):  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path != "/api/watchlist":
                self._send_json(404, {"error": "not found"})
                return
            payload = self._read_json_body()
            if payload is None or "document" not in payload:
                self._send_json(400, {"ok": False, "error": "Expected JSON body with document field."})
                return
            try:
                saved = watchlist_store.save_watchlist(payload["document"], app_root=watchlist_root or APP_ROOT)
            except OSError:
                logger.exception("Watchlist save failed")
                self._send_json(500, {"ok": False, "error": "Could not save watchlist."})
                return
            self._send_json(
                200,
                {
                    "ok": True,
                    "document": saved,
                    "entry_count": len(saved.get("entries", [])),
                    "storage_path": watchlist_store.watchlist_path(watchlist_root or APP_ROOT),
                    "storage_path_relative": watchlist_store.watchlist_relative_path(),
                },
            )

        def do_HEAD(self):  # noqa: N802
            self.send_response(200)
            self.end_headers()

    return Handler


def find_free_port(preferred: int = 8765) -> int:
    """Return `preferred` if free, otherwise an OS-assigned free port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", preferred))
            return preferred
        except OSError:
            pass
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def run_server(
    host: str = "127.0.0.1",
    port: int = 8765,
    stellarium_base_url: str = "http://127.0.0.1:8090",
    planetary_fetcher=None,
    archive_fetcher=None,
    apophis_fetcher=None,
    watchlist_root: str | None = None,
):
    client = StellariumClient(base_url=stellarium_base_url)
    handler_cls = make_handler(
        client,
        planetary_fetcher=planetary_fetcher,
        archive_fetcher=archive_fetcher,
        apophis_fetcher=apophis_fetcher,
        watchlist_root=watchlist_root,
    )
    httpd = ThreadingHTTPServer((host, port), handler_cls)
    return httpd


def serve_forever_in_thread(httpd: ThreadingHTTPServer) -> threading.Thread:
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return t
