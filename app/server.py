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
from . import cosmic_signal_registry
from . import spectrum_gallery_registry
from . import planetary_image
from . import watchlist_store
from .discovery import service as discovery_service
from .stellarium_client import StellariumClient, SelectionResult
from . import archaeoastronomy
from . import constellation_story
from . import exhibit
from . import experience
from . import official_media
from . import light_echoes
from . import cosmic_web
from . import gravitational_waves
from . import black_holes
from . import galactic_encounters
from . import cosmic_dawn
from . import tts_client

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
    discovery_fetcher=None,
    apophis_fetcher=None,
    watchlist_root: str | None = None,
    media_fetcher=None,
    media_cache_dir: str | None = None,
    tts_config: dict | None = None,
    tts_cache_dir: str | None = None,
    tts_transport=None,
):
    class Handler(BaseHTTPRequestHandler):
        server_version = "FOXAIStellarCartography/0.5.0-dev"

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

            if path == "/api/sky-state":
                self._send_json(200, _sky_state_payload(stellarium_client))
                return

            if path == "/api/time-machine/presets":
                self._send_json(200, {"ok": True, "presets": experience.time_machine_presets()})
                return

            if path == "/api/events":
                status_payload = stellarium_client.get_main_status()
                sky = experience.extract_sky_status(status_payload)
                self._send_json(200, experience.event_strip_foundation(sky))
                return

            if path == "/api/narration":
                qs = parse_qs(parsed.query)
                kind = (qs.get("kind") or ["selection"])[0]
                constellation_id = (qs.get("constellation") or qs.get("id") or [""])[0]
                exhibit_id = (qs.get("exhibit") or [""])[0]
                step_raw = (qs.get("step") or qs.get("n") or [""])[0]
                self._send_json(
                    200,
                    _narration_payload(
                        stellarium_client,
                        kind=kind,
                        constellation_id=constellation_id,
                        exhibit_id=exhibit_id,
                        step_index=exhibit.parse_step_index(step_raw) if step_raw != "" else None,
                    ),
                )
                return

            if path == "/api/cosmic-dawn":
                self._send_json(200, cosmic_dawn.list_payload())
                return

            if path.startswith("/api/cosmic-dawn/object/"):
                object_id = path[len("/api/cosmic-dawn/object/") :]
                payload = cosmic_dawn.object_payload(object_id)
                self._send_json(200 if payload.get("ok") else 404, payload)
                return

            if path == "/api/cosmic-dawn/timeline":
                qs = parse_qs(parsed.query)
                epoch = (qs.get("epoch") or [None])[0]
                progress_raw = (qs.get("progress") or [None])[0]
                progress = None
                if progress_raw not in (None, ""):
                    try:
                        progress = float(progress_raw)
                    except ValueError:
                        self._send_json(400, {"ok": False, "error": "progress must be a number."})
                        return
                self._send_json(200, cosmic_dawn.timeline_state(epoch_id=epoch, progress=progress))
                return

            if path == "/api/cosmic-dawn/redshift":
                qs = parse_qs(parsed.query)
                z_raw = (qs.get("z") or [None])[0]
                z = None
                if z_raw not in (None, ""):
                    try:
                        z = float(z_raw)
                    except ValueError:
                        self._send_json(400, {"ok": False, "error": "z must be a number."})
                        return
                self._send_json(200, cosmic_dawn.redshift_state(z=z))
                return

            if path == "/api/cosmic-dawn/reionization":
                qs = parse_qs(parsed.query)
                stage = (qs.get("stage") or [None])[0]
                progress_raw = (qs.get("progress") or [None])[0]
                progress = None
                if progress_raw not in (None, ""):
                    try:
                        progress = float(progress_raw)
                    except ValueError:
                        self._send_json(400, {"ok": False, "error": "progress must be a number."})
                        return
                self._send_json(200, cosmic_dawn.reionization_state(stage_id=stage, progress=progress))
                return

            if path == "/api/cosmic-dawn/structure":
                qs = parse_qs(parsed.query)
                progress_raw = (qs.get("progress") or [None])[0]
                progress = None
                if progress_raw not in (None, ""):
                    try:
                        progress = float(progress_raw)
                    except ValueError:
                        self._send_json(400, {"ok": False, "error": "progress must be a number."})
                        return
                self._send_json(200, cosmic_dawn.structure_state(progress=progress))
                return

            if path == "/api/cosmic-dawn/21cm":
                self._send_json(200, cosmic_dawn.twenty_one_cm_payload())
                return

            if path == "/api/cosmic-dawn/narration":
                qs = parse_qs(parsed.query)
                segment = (qs.get("segment") or [""])[0]
                payload = cosmic_dawn.narration_segment(segment)
                self._send_json(200 if payload.get("ok") else 404, payload)
                return

            if path == "/api/galactic-encounters":
                self._send_json(200, galactic_encounters.list_payload())
                return

            if path.startswith("/api/galactic-encounters/object/"):
                object_id = path[len("/api/galactic-encounters/object/") :]
                payload = galactic_encounters.object_payload(object_id)
                self._send_json(200 if payload.get("ok") else 404, payload)
                return

            if path == "/api/galactic-encounters/encounter":
                qs = parse_qs(parsed.query)
                stage = (qs.get("stage") or [None])[0]
                progress_raw = (qs.get("progress") or [None])[0]
                mass_ratio = (qs.get("mass_ratio") or [None])[0]
                orientation = (qs.get("orientation") or [None])[0]
                progress = None
                if progress_raw not in (None, ""):
                    try:
                        progress = float(progress_raw)
                    except ValueError:
                        self._send_json(400, {"ok": False, "error": "progress must be a number."})
                        return
                self._send_json(
                    200,
                    galactic_encounters.encounter_state(
                        stage_id=stage,
                        progress=progress,
                        mass_ratio_id=mass_ratio,
                        orientation_id=orientation,
                    ),
                )
                return

            if path == "/api/galactic-encounters/tidal":
                qs = parse_qs(parsed.query)
                strength_raw = (qs.get("strength") or [None])[0]
                strength = None
                if strength_raw not in (None, ""):
                    try:
                        strength = float(strength_raw)
                    except ValueError:
                        self._send_json(400, {"ok": False, "error": "strength must be a number."})
                        return
                self._send_json(200, galactic_encounters.tidal_state(strength=strength))
                return

            if path == "/api/galactic-encounters/stars-gas":
                qs = parse_qs(parsed.query)
                mode = (qs.get("mode") or [None])[0]
                self._send_json(200, galactic_encounters.stars_gas_state(mode=mode))
                return

            if path == "/api/galactic-encounters/merger":
                qs = parse_qs(parsed.query)
                mode = (qs.get("mode") or [None])[0]
                self._send_json(200, galactic_encounters.merger_state(mode=mode))
                return

            if path == "/api/galactic-encounters/future":
                self._send_json(200, galactic_encounters.future_payload())
                return

            if path == "/api/galactic-encounters/narration":
                qs = parse_qs(parsed.query)
                segment = (qs.get("segment") or [""])[0]
                payload = galactic_encounters.narration_segment(segment)
                self._send_json(200 if payload.get("ok") else 404, payload)
                return

            if path == "/api/black-holes":
                self._send_json(200, black_holes.list_payload())
                return

            if path.startswith("/api/black-holes/object/"):
                object_id = path[len("/api/black-holes/object/") :]
                payload = black_holes.object_payload(object_id)
                self._send_json(200 if payload.get("ok") else 404, payload)
                return

            if path == "/api/black-holes/scale":
                qs = parse_qs(parsed.query)
                example_id = (qs.get("example_id") or [None])[0]
                mass_raw = (qs.get("mass_solar") or [None])[0]
                mass = None
                if mass_raw not in (None, ""):
                    try:
                        mass = float(mass_raw)
                    except ValueError:
                        self._send_json(400, {"ok": False, "error": "mass_solar must be a number."})
                        return
                self._send_json(200, black_holes.scale_state(example_id=example_id, mass_solar=mass))
                return

            if path == "/api/black-holes/approach":
                qs = parse_qs(parsed.query)
                region_id = (qs.get("region") or [None])[0]
                progress_raw = (qs.get("progress") or [None])[0]
                progress = None
                if progress_raw not in (None, ""):
                    try:
                        progress = float(progress_raw)
                    except ValueError:
                        self._send_json(400, {"ok": False, "error": "progress must be a number."})
                        return
                self._send_json(200, black_holes.approach_state(region_id=region_id, progress=progress))
                return

            if path == "/api/black-holes/lensing":
                qs = parse_qs(parsed.query)
                strength_raw = (qs.get("strength") or [None])[0]
                phase_raw = (qs.get("phase") or [None])[0]
                strength = None
                phase = None
                if strength_raw not in (None, ""):
                    try:
                        strength = float(strength_raw)
                    except ValueError:
                        self._send_json(400, {"ok": False, "error": "strength must be a number."})
                        return
                if phase_raw not in (None, ""):
                    try:
                        phase = float(phase_raw)
                    except ValueError:
                        self._send_json(400, {"ok": False, "error": "phase must be a number."})
                        return
                self._send_json(200, black_holes.lensing_state(strength=strength, phase=phase))
                return

            if path == "/api/black-holes/tidal":
                qs = parse_qs(parsed.query)
                example_id = (qs.get("example_id") or [None])[0]
                self._send_json(200, black_holes.tidal_state(example_id=example_id))
                return

            if path == "/api/black-holes/narration":
                qs = parse_qs(parsed.query)
                segment = (qs.get("segment") or [""])[0]
                payload = black_holes.narration_segment(segment)
                self._send_json(200 if payload.get("ok") else 404, payload)
                return

            if path == "/api/gravitational-waves":
                self._send_json(200, gravitational_waves.list_payload())
                return

            if path.startswith("/api/gravitational-waves/event/"):
                event_id = path[len("/api/gravitational-waves/event/") :]
                payload = gravitational_waves.event_payload(event_id)
                self._send_json(200 if payload.get("ok") else 404, payload)
                return

            if path == "/api/gravitational-waves/wave":
                qs = parse_qs(parsed.query)
                pol = (qs.get("polarization") or ["plus"])[0]
                phase_raw = (qs.get("phase") or ["0"])[0]
                amp_raw = (qs.get("amplitude") or [None])[0]
                try:
                    phase = float(phase_raw)
                except ValueError:
                    self._send_json(400, {"ok": False, "error": "phase must be a number."})
                    return
                amplitude = None
                if amp_raw not in (None, ""):
                    try:
                        amplitude = float(amp_raw)
                    except ValueError:
                        self._send_json(400, {"ok": False, "error": "amplitude must be a number."})
                        return
                self._send_json(200, gravitational_waves.wave_state(polarization=pol, phase=phase, amplitude=amplitude))
                return

            if path == "/api/gravitational-waves/interferometer":
                qs = parse_qs(parsed.query)
                phase_id = (qs.get("phase") or [None])[0]
                progress_raw = (qs.get("progress") or [None])[0]
                progress = None
                if progress_raw not in (None, ""):
                    try:
                        progress = float(progress_raw)
                    except ValueError:
                        self._send_json(400, {"ok": False, "error": "progress must be a number."})
                        return
                self._send_json(200, gravitational_waves.interferometer_state(phase_id=phase_id, progress=progress))
                return

            if path == "/api/gravitational-waves/chirp":
                qs = parse_qs(parsed.query)
                stage = (qs.get("stage") or [None])[0]
                progress_raw = (qs.get("progress") or [None])[0]
                progress = None
                if progress_raw not in (None, ""):
                    try:
                        progress = float(progress_raw)
                    except ValueError:
                        self._send_json(400, {"ok": False, "error": "progress must be a number."})
                        return
                self._send_json(200, gravitational_waves.chirp_state(stage_id=stage, progress=progress))
                return

            if path == "/api/gravitational-waves/network":
                self._send_json(200, gravitational_waves.network_payload())
                return

            if path == "/api/gravitational-waves/narration":
                qs = parse_qs(parsed.query)
                segment = (qs.get("segment") or [""])[0]
                payload = gravitational_waves.narration_segment(segment)
                self._send_json(200 if payload.get("ok") else 404, payload)
                return

            if path == "/api/cosmic-web":
                self._send_json(200, cosmic_web.list_payload())
                return

            if path.startswith("/api/cosmic-web/object/"):
                object_id = path[len("/api/cosmic-web/object/") :]
                payload = cosmic_web.object_payload(object_id)
                self._send_json(200 if payload.get("ok") else 404, payload)
                return

            if path == "/api/cosmic-web/structure":
                qs = parse_qs(parsed.query)
                step = (qs.get("step") or [None])[0]
                progress_raw = (qs.get("progress") or [None])[0]
                progress = None
                if progress_raw not in (None, ""):
                    try:
                        progress = float(progress_raw)
                    except ValueError:
                        self._send_json(400, {"ok": False, "error": "progress must be a number."})
                        return
                layers = {}
                for key in ("galaxies", "filaments", "nodes", "voids"):
                    raw = (qs.get("layer_" + key) or [None])[0]
                    if raw in (None, ""):
                        continue
                    layers[key] = raw in ("1", "true", "yes", "on")
                self._send_json(
                    200,
                    cosmic_web.structure_state(
                        step_id=step,
                        progress=progress,
                        layers=layers or None,
                    ),
                )
                return

            if path == "/api/cosmic-web/narration":
                qs = parse_qs(parsed.query)
                segment = (qs.get("segment") or [""])[0]
                payload = cosmic_web.narration_segment(segment)
                self._send_json(200 if payload.get("ok") else 404, payload)
                return

            if path == "/api/light-echoes":
                self._send_json(200, light_echoes.list_payload())
                return

            if path.startswith("/api/light-echoes/object/"):
                object_id = path[len("/api/light-echoes/object/") :]
                payload = light_echoes.object_payload(object_id)
                self._send_json(200 if payload.get("ok") else 404, payload)
                return

            if path == "/api/light-echoes/geometry":
                qs = parse_qs(parsed.query)
                step = (qs.get("step") or [None])[0]
                progress_raw = (qs.get("progress") or [None])[0]
                progress = None
                if progress_raw not in (None, ""):
                    try:
                        progress = float(progress_raw)
                    except ValueError:
                        self._send_json(400, {"ok": False, "error": "progress must be a number."})
                        return
                self._send_json(200, light_echoes.geometry_state(step_id=step, progress=progress))
                return

            if path == "/api/light-echoes/narration":
                qs = parse_qs(parsed.query)
                segment = (qs.get("segment") or [""])[0]
                payload = light_echoes.narration_segment(segment)
                self._send_json(200 if payload.get("ok") else 404, payload)
                return

            if path == "/api/exhibits":
                qs = parse_qs(parsed.query)
                include_fixtures = (qs.get("include_fixtures") or ["0"])[0] in ("1", "true", "yes")
                self._send_json(200, exhibit.list_exhibits(include_fixtures=include_fixtures))
                return

            if path.startswith("/api/exhibit/"):
                handled = _handle_exhibit_get(self, path)
                if handled:
                    return

            if path == "/api/tts/providers":
                self._send_json(200, _tts_providers_payload(tts_config, tts_transport))
                return

            if path == "/api/tts/status":
                self._send_json(200, _tts_status_payload())
                return

            if path in {"/api/constellations", "/api/stories"}:
                qs = parse_qs(parsed.query)
                culture = (qs.get("culture") or [""])[0]
                self._send_json(200, constellation_story.list_constellations(culture or None))
                return

            if path == "/api/story-cultures":
                self._send_json(200, constellation_story.list_cultures())
                return

            if path == "/api/story-compare":
                qs = parse_qs(parsed.query)
                query = (qs.get("q") or qs.get("object") or [""])[0]
                selection = _selection_to_dict(stellarium_client.get_selection())
                self._send_json(200, constellation_story.compare_stories(query or selection.get("name"), selection=selection))
                return

            if path == "/api/constellation-context":
                qs = parse_qs(parsed.query)
                include_story = (qs.get("include_story") or ["0"])[0] in ("1", "true", "yes")
                culture = (qs.get("culture") or [""])[0] or None
                story_id = (qs.get("story") or qs.get("id") or [""])[0] or None
                selection = _selection_to_dict(stellarium_client.get_selection())
                live_culture = stellarium_client.get_sky_culture_id()
                self._send_json(
                    200,
                    constellation_story.constellation_context(
                        selection,
                        include_story=include_story,
                        sky_culture_live=live_culture,
                        culture=culture,
                        story_id=story_id,
                    ),
                )
                return

            if path == "/api/constellation-controls":
                props = stellarium_client.get_constellation_properties()
                self._send_json(200, constellation_story.constellation_controls_payload(props))
                return

            if path == "/api/constellation-tour":
                self._send_json(200, constellation_story.tour_status())
                return

            if path == "/api/archaeoastronomy":
                qs = parse_qs(parsed.query)
                visual_id = (qs.get("id") or qs.get("story") or [""])[0]
                self._send_json(200, archaeoastronomy.visual_payload(visual_id or None))
                return

            if path.startswith("/api/constellation/"):
                constellation_id = path[len("/api/constellation/") :]
                selection = _selection_to_dict(stellarium_client.get_selection())
                live_culture = stellarium_client.get_sky_culture_id()
                result = constellation_story.story_payload(
                    constellation_id,
                    selection=selection,
                    sky_culture_live=live_culture,
                )
                self._send_json(200 if result.get("ok") else 404, result)
                return

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

            if path == "/api/media/search":
                qs = parse_qs(parsed.query)
                query = (qs.get("q") or qs.get("query") or qs.get("object") or [""])[0]
                media_type = (qs.get("media_type") or ["all"])[0]
                object_name = (qs.get("object") or [""])[0] or None
                selection = _selection_to_dict(stellarium_client.get_selection())
                result = official_media.search_media(
                    query,
                    object_name=object_name,
                    media_type=media_type,
                    selection=selection,
                    fetcher=media_fetcher,
                    cache_dir=media_cache_dir,
                )
                self._send_json(200, result)
                return

            if path == "/api/media/context":
                qs = parse_qs(parsed.query)
                object_name = (qs.get("object") or qs.get("name") or [""])[0] or None
                media_type = (qs.get("media_type") or ["all"])[0]
                selection = _selection_to_dict(stellarium_client.get_selection())
                tour = constellation_story.tour_status()
                if not object_name and tour.get("active") and isinstance(tour.get("step"), dict):
                    object_name = tour["step"].get("search_name") or tour["step"].get("name")
                result = official_media.media_context(
                    selection,
                    object_name=object_name,
                    media_type=media_type,
                    fetcher=media_fetcher,
                    cache_dir=media_cache_dir,
                )
                self._send_json(200, result)
                return

            if path.startswith("/api/media/item/"):
                item_id = path[len("/api/media/item/") :]
                result = official_media.get_item(
                    item_id,
                    fetcher=media_fetcher,
                    cache_dir=media_cache_dir,
                )
                self._send_json(200 if result.get("ok") else 404, result)
                return

            if path == "/api/cosmic-signal-registry":
                try:
                    payload = cosmic_signal_registry.registry_public_payload()
                except cosmic_signal_registry.RegistryError as exc:
                    self._send_json(500, {"ok": False, "error": str(exc)})
                    return
                self._send_json(200, {"ok": True, "registry": payload})
                return

            if path == "/api/cosmic-signal-match":
                qs = parse_qs(parsed.query)
                name = (qs.get("name") or [""])[0]
                alt_name = (qs.get("alt_name") or [""])[0]
                catalogue_designations = (qs.get("catalogue_designations") or [""])[0]
                allow_featured = (qs.get("allow_featured") or ["1"])[0] not in (
                    "0",
                    "false",
                    "no",
                )
                target = {
                    "name": name or None,
                    "alt_name": alt_name or None,
                    "catalogue_designations": catalogue_designations or None,
                }
                try:
                    result = cosmic_signal_registry.match_signals_for_target(
                        target,
                        allow_featured=allow_featured,
                    )
                except cosmic_signal_registry.RegistryError as exc:
                    self._send_json(500, {"ok": False, "error": str(exc)})
                    return
                self._send_json(200, result)
                return

            if path == "/api/spectrum-gallery-registry":
                try:
                    payload = spectrum_gallery_registry.registry_public_payload()
                except spectrum_gallery_registry.SpectrumRegistryError as exc:
                    self._send_json(500, {"ok": False, "error": str(exc)})
                    return
                self._send_json(200, {"ok": True, "registry": payload})
                return

            if path == "/api/spectrum-gallery-match":
                qs = parse_qs(parsed.query)
                name = (qs.get("name") or [""])[0]
                alt_name = (qs.get("alt_name") or [""])[0]
                catalogue_designations = (qs.get("catalogue_designations") or [""])[0]
                allow_all_sky = (qs.get("allow_all_sky") or ["1"])[0] not in (
                    "0",
                    "false",
                    "no",
                )
                target = {
                    "name": name or None,
                    "alt_name": alt_name or None,
                    "catalogue_designations": catalogue_designations or None,
                }
                try:
                    result = spectrum_gallery_registry.match_spectrum_for_target(
                        target,
                        allow_all_sky=allow_all_sky,
                    )
                except spectrum_gallery_registry.SpectrumRegistryError as exc:
                    self._send_json(500, {"ok": False, "error": str(exc)})
                    return
                self._send_json(200, result)
                return

            if path == "/api/archive-availability":
                # R0.4 compatibility endpoint (single-strategy facade).
                # The R0.5 UI should use /api/discovery instead and must not
                # also call this endpoint for the same target selection.
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

            if path == "/api/discovery":
                qs = parse_qs(parsed.query)
                ra_text = (qs.get("ra") or [""])[0]
                dec_text = (qs.get("dec") or [""])[0]
                name = (qs.get("name") or [""])[0] or None
                alt_name = (qs.get("alt_name") or [""])[0] or None
                category = (qs.get("target_category") or [""])[0] or None
                moving = (qs.get("moving_target") or ["0"])[0] in ("1", "true", "yes")
                missions_raw = (qs.get("missions") or [""])[0]
                missions = [m.strip() for m in missions_raw.split(",") if m.strip()] or None
                ra = dec = None
                if ra_text and dec_text:
                    try:
                        ra = float(ra_text)
                        dec = float(dec_text)
                    except ValueError:
                        self._send_json(
                            200,
                            {
                                "ok": False,
                                "error": "Invalid coordinates.",
                                "bundle": {
                                    "items": [],
                                    "query_outcomes": [],
                                    "warnings": [],
                                    "capability_notes": [],
                                },
                                "badges": {},
                            },
                        )
                        return
                # Prefer an explicit discovery_fetcher; fall back to archive_fetcher
                # so existing test harnesses keep working.
                fetch = discovery_fetcher if discovery_fetcher is not None else archive_fetcher
                payload = discovery_service.run_mast_discovery(
                    ra_deg=ra,
                    dec_deg=dec,
                    target_name=name,
                    alt_name=alt_name,
                    target_category=category,
                    missions=missions,
                    moving_target=moving,
                    fetcher=fetch,
                )
                self._send_json(200, payload)
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

        def do_POST(self):  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path
            payload = self._read_json_body() or {}

            if path == "/api/time-machine":
                validated = experience.validate_time_machine_request(payload)
                if not validated.get("ok"):
                    self._send_json(200, validated)
                    return
                if not stellarium_client.check_connection():
                    self._send_json(200, {"ok": False, "error": "Stellarium Remote Control is not reachable."})
                    return
                applied = []
                if validated["apply_time"]:
                    if validated.get("preset") == "now":
                        ok = stellarium_client.return_to_now()
                    else:
                        ok = stellarium_client.apply_time(validated["jday"], validated["timerate"])
                    if not ok:
                        self._send_json(200, {"ok": False, "error": "Stellarium rejected the time update."})
                        return
                    applied.append("time")
                if validated["apply_location"]:
                    ok = stellarium_client.apply_location(
                        validated["latitude"],
                        validated["longitude"],
                        validated["altitude"],
                        validated["name"],
                        validated["planet"],
                    )
                    if not ok:
                        self._send_json(200, {"ok": False, "error": "Stellarium rejected the location update."})
                        return
                    applied.append("location")
                state = _sky_state_payload(stellarium_client)
                state["ok"] = True
                state["applied"] = applied
                state["request"] = {
                    k: validated[k]
                    for k in (
                        "utc",
                        "jday",
                        "preset",
                        "latitude",
                        "longitude",
                        "name",
                        "reconstruction",
                        "reconstruction_label",
                    )
                }
                self._send_json(200, state)
                return

            if path == "/api/postcard":
                self._send_json(200, _postcard_payload(stellarium_client))
                return

            if path == "/api/compare":
                result = experience.compare_snapshots(payload.get("a"), payload.get("b"))
                self._send_json(200, result)
                return

            if path == "/api/cosmic-dawn/focus":
                object_id = None
                if isinstance(payload, dict):
                    object_id = payload.get("object_id") or payload.get("event_id")
                self._send_json(200, cosmic_dawn.apply_focus(stellarium_client, object_id))
                return

            if path == "/api/galactic-encounters/focus":
                object_id = None
                if isinstance(payload, dict):
                    object_id = payload.get("object_id") or payload.get("event_id")
                self._send_json(200, galactic_encounters.apply_focus(stellarium_client, object_id))
                return

            if path == "/api/black-holes/focus":
                object_id = None
                if isinstance(payload, dict):
                    object_id = payload.get("object_id") or payload.get("event_id")
                self._send_json(200, black_holes.apply_focus(stellarium_client, object_id))
                return

            if path == "/api/gravitational-waves/focus":
                event_id = None
                if isinstance(payload, dict):
                    event_id = payload.get("event_id") or payload.get("object_id")
                self._send_json(200, gravitational_waves.apply_focus(stellarium_client, event_id))
                return

            if path == "/api/cosmic-web/focus":
                object_id = payload.get("object_id") if isinstance(payload, dict) else None
                self._send_json(200, cosmic_web.apply_focus(stellarium_client, object_id))
                return

            if path == "/api/light-echoes/focus":
                object_id = payload.get("object_id") if isinstance(payload, dict) else None
                self._send_json(200, light_echoes.apply_focus(stellarium_client, object_id))
                return

            exhibit_post = _handle_exhibit_post(path, payload, stellarium_client)
            if exhibit_post is not None:
                self._send_json(200, exhibit_post)
                return

            if path == "/api/constellation-tour/start":
                constellation_id = payload.get("id") or payload.get("constellation")
                selection = _selection_to_dict(stellarium_client.get_selection())
                if not constellation_id:
                    constellation_id = constellation_story.detect_constellation(selection).get("story_id")
                result = constellation_story.start_tour(constellation_id, selection)
                if result.get("ok"):
                    result = constellation_story.apply_tour_to_stellarium(stellarium_client, result)
                self._send_json(200, result)
                return

            if path == "/api/constellation-tour/step":
                direction = payload.get("direction") or "next"
                result = constellation_story.step_tour(str(direction))
                if result.get("ok") and result.get("active"):
                    result = constellation_story.apply_tour_to_stellarium(stellarium_client, result)
                self._send_json(200, result)
                return

            if path == "/api/constellation-tour/stop":
                result = constellation_story.stop_tour()
                if result.get("restore_search_name"):
                    result = constellation_story.restore_original_selection(stellarium_client, result)
                self._send_json(200, result)
                return

            if path == "/api/constellation-controls":
                parsed_controls = constellation_story.parse_control_request(payload)
                if not parsed_controls.get("ok"):
                    self._send_json(200, parsed_controls)
                    return
                applied = []
                for update in parsed_controls.get("updates") or []:
                    ok = stellarium_client.set_stel_property(update["property"], update["value"])
                    applied.append({"id": update["id"], "ok": ok, "value": update["value"]})
                props = stellarium_client.get_constellation_properties()
                state = constellation_story.constellation_controls_payload(props)
                state["applied"] = applied
                self._send_json(200, state)
                return

            if path == "/api/tts/synthesize":
                self._send_json(*_tts_synthesize_response(payload, tts_config, tts_cache_dir, tts_transport))
                return

            if path == "/api/tts/stop":
                _TTS_STATUS["stopped_at"] = _utc_now()
                _TTS_STATUS["playing"] = False
                self._send_json(200, {"ok": True, "stopped": True, "label": tts_client.NARRATION_LABEL, "audio_autoplay": False})
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


def _spectrum_for_selection(selection: dict) -> dict:
    if not selection.get("ok"):
        return {
            "ok": True,
            "available": False,
            "marks": [],
            "empty_reason": "Select a target to look for curated spectrum views.",
        }
    try:
        match = spectrum_gallery_registry.match_spectrum_for_target(
            {
                "name": selection.get("name"),
                "alt_name": selection.get("alt_name"),
                "catalogue_designations": selection.get("catalogue_designations"),
            },
            allow_all_sky=False,
        )
    except Exception:  # noqa: BLE001 - spectrum decoration must never fail sky-state
        return {
            "ok": True,
            "available": False,
            "marks": [],
            "empty_reason": "Spectrum registry unavailable.",
        }
    entries = list(match.get("available_views") or [])
    primary = match.get("primary")
    if isinstance(primary, dict) and primary not in entries:
        entries = [primary] + entries
    active_id = primary.get("id") if isinstance(primary, dict) else None
    return experience.spectrum_axis(entries, active_id)


def _sky_state_payload(stellarium_client: StellariumClient) -> dict:
    status_payload = stellarium_client.get_main_status()
    sky = experience.extract_sky_status(status_payload)
    selection_result = stellarium_client.get_selection()
    selection = _selection_to_dict(selection_result)
    raw_info = stellarium_client.get_objects_info_raw()
    extras = experience.extra_selection_fields(raw_info)
    card = experience.build_object_card(selection, sky, extras)
    motion = experience.motion_track(selection, sky)
    sonify = (
        experience.sonify_plan(selection, sky)
        if selection.get("ok")
        else {"ok": False, "available": False, "reason": "No current selection.", "samples": []}
    )
    return {
        "ok": bool(sky.get("ok") or selection.get("connected")),
        "connected": bool(selection.get("connected") or sky.get("ok")),
        "sky": sky,
        "selection": selection,
        "extras": extras,
        "card": card,
        "motion": motion,
        "sonify": sonify,
        "spectrum": _spectrum_for_selection(selection),
        "events": experience.event_strip_foundation(sky),
        "narration": experience.narration_payload(selection, sky),
        "constellation": constellation_story.constellation_context(
            selection,
            include_story=False,
            sky_culture_live=stellarium_client.get_sky_culture_id(),
        ),
    }


def _postcard_payload(stellarium_client: StellariumClient) -> dict:
    state = _sky_state_payload(stellarium_client)
    return experience.postcard_metadata(state.get("selection") or {}, state.get("sky") or {}, state.get("extras") or {})


def _handle_exhibit_get(handler, path: str) -> bool:
    rest = path[len("/api/exhibit/") :]
    parts = [part for part in rest.split("/") if part]
    if not parts:
        handler._send_json(404, {"error": "not found"})
        return True
    exhibit_id = parts[0]
    if len(parts) == 1:
        result = exhibit.exhibit_payload(exhibit_id)
        handler._send_json(200 if result.get("ok") else 404, result)
        return True
    if len(parts) == 3 and parts[1] == "step":
        index = exhibit.parse_step_index(parts[2])
        if index is None:
            handler._send_json(200, {"ok": False, "error": "Exhibit step is out of range.", "audio_autoplay": False})
            return True
        result = exhibit.step_payload(exhibit_id, index)
        handler._send_json(200 if result.get("ok") else 404, result)
        return True
    return False


def _handle_exhibit_post(path: str, payload: dict, stellarium_client: StellariumClient) -> dict | None:
    if not path.startswith("/api/exhibit/"):
        return None
    rest = path[len("/api/exhibit/") :]
    parts = [part for part in rest.split("/") if part]
    if len(parts) != 2:
        return None
    exhibit_id, action = parts
    if action == "start":
        selection = _selection_to_dict(stellarium_client.get_selection())
        return exhibit.start_exhibit(exhibit_id, stellarium_client, selection)
    if action == "step":
        direction = payload.get("direction") or "next"
        return exhibit.step_exhibit(str(direction), stellarium_client, payload)
    if action == "stop":
        restore = payload.get("restore")
        if restore is None:
            restore = True
        return exhibit.stop_exhibit(stellarium_client, restore=bool(restore))
    return None


def _narration_payload(
    stellarium_client: StellariumClient,
    *,
    kind: str = "selection",
    constellation_id: str = "",
    exhibit_id: str = "",
    step_index: int | None = None,
) -> dict:
    if (kind or "").strip() == "exhibit_step":
        payload = exhibit.narration_payload(exhibit_id, step_index)
        payload["audio_autoplay"] = False
        return payload
    state = _sky_state_payload(stellarium_client)
    selection = state.get("selection") or {}
    story = None
    tour = constellation_story.tour_status() if kind in {"tour_step", "object_transition"} else None
    if constellation_id or (tour and tour.get("constellation_id")):
        story = constellation_story.get_story(constellation_id or (tour or {}).get("constellation_id"))
    elif selection:
        detected = constellation_story.detect_constellation(selection)
        if detected.get("story_id"):
            story = constellation_story.get_story(detected["story_id"])
    payload = experience.narration_payload(
        selection,
        state.get("sky") or {},
        kind=kind,
        constellation=story,
        tour=tour,
    )
    payload.update(official_media.curated_narration_fields(selection))
    payload["audio_autoplay"] = False
    return payload


_TTS_STATUS: dict = {
    "playing": False,
    "request_id": None,
    "provider": None,
    "voice": None,
    "generated_at": None,
    "stopped_at": None,
}


def _utc_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _tts_providers_payload(config, transport) -> dict:
    try:
        cfg = config or tts_client.load_config()
    except tts_client.TTSError as exc:
        return tts_client.error_payload(exc)
    return tts_client.providers_payload(config=cfg, transport=transport)


def _tts_status_payload() -> dict:
    return {
        "ok": True,
        "label": tts_client.NARRATION_LABEL,
        "audio_autoplay": False,
        **_TTS_STATUS,
    }


def _tts_synthesize_response(payload, config, cache_dir, transport) -> tuple[int, dict]:
    body = payload if isinstance(payload, dict) else {}
    try:
        cfg = config or tts_client.load_config()
        result = tts_client.synthesize(
            body.get("text") or "",
            body.get("provider") or "",
            voice=body.get("voice"),
            request_id=body.get("request_id"),
            profile=body.get("profile"),
            context=body.get("context") or "constellation_overview",
            raw_request=body,
            config=cfg,
            cache_dir=cache_dir,
            transport=transport,
        )
        _TTS_STATUS.update(
            {
                "playing": False,
                "request_id": result.get("request_id"),
                "provider": result.get("provider"),
                "voice": result.get("voice"),
                "generated_at": result.get("generated_at"),
            }
        )
        return 200, tts_client.synthesize_payload(result)
    except tts_client.TTSError as exc:
        return 200, tts_client.error_payload(exc)


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
    discovery_fetcher=None,
    apophis_fetcher=None,
    watchlist_root: str | None = None,
    media_fetcher=None,
    media_cache_dir: str | None = None,
    tts_config: dict | None = None,
    tts_cache_dir: str | None = None,
    tts_transport=None,
):
    constellation_story.reset_tour()
    exhibit.reset_session()
    client = StellariumClient(base_url=stellarium_base_url)
    handler_cls = make_handler(
        client,
        planetary_fetcher=planetary_fetcher,
        archive_fetcher=archive_fetcher,
        discovery_fetcher=discovery_fetcher,
        apophis_fetcher=apophis_fetcher,
        watchlist_root=watchlist_root,
        media_fetcher=media_fetcher,
        media_cache_dir=media_cache_dir,
        tts_config=tts_config,
        tts_cache_dir=tts_cache_dir,
        tts_transport=tts_transport,
    )
    httpd = ThreadingHTTPServer((host, port), handler_cls)
    return httpd


def serve_forever_in_thread(httpd: ThreadingHTTPServer) -> threading.Thread:
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return t
