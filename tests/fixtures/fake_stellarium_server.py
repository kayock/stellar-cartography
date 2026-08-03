"""
fake_stellarium_server.py

A minimal in-process HTTP server that mimics just enough of Stellarium's
Remote Control plug-in for tests: GET /api/main/status and
GET /api/objects/info. Lets tests exercise the real network code path
(urllib -> localhost socket -> JSON parsing) without requiring Stellarium
or any internet access.

These two endpoints are documented as returning genuinely distinct JSON
shapes -- /api/objects/info describes the current selection, while
/api/main/status carries live viewer state such as the field of view under
"view.fov". This fake keeps them independently configurable so tests don't
accidentally rely on FoV leaking in through the selection payload.

Usage:
    server = FakeStellariumServer(objects_info_body=b'{"name": "M 31", ...}')
    server.start()
    ...
    server.stop()
    url = server.base_url
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional

# Default GET /api/main/status body: reachable, but no view.fov reported
# (mirrors a Stellarium build/plug-in state where FoV isn't available;
# get_selection() must tolerate this and simply omit fov_deg).
DEFAULT_MAIN_STATUS_BODY = b'{"status": "ok"}'


class FakeStellariumServer:
    def __init__(
        self,
        objects_info_body: bytes = b"{}",
        objects_info_status: int = 200,
        content_type: str = "application/json",
        simulate_no_response: bool = False,
        main_status_body: bytes = DEFAULT_MAIN_STATUS_BODY,
        main_status_status: int = 200,
    ):
        self.objects_info_body = objects_info_body
        self.objects_info_status = objects_info_status
        self.content_type = content_type
        self.simulate_no_response = simulate_no_response
        self.main_status_body = main_status_body
        self.main_status_status = main_status_status
        self._httpd: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    @property
    def base_url(self) -> str:
        assert self._httpd is not None
        host, port = self._httpd.server_address[:2]
        return f"http://127.0.0.1:{port}"

    def start(self) -> None:
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, fmt, *args):
                pass  # silence

            def do_GET(self):
                if outer.simulate_no_response:
                    # Close the connection without responding, simulating an
                    # unreachable / hung endpoint.
                    self.close_connection = True
                    return

                if self.path.startswith("/api/main/status"):
                    body = outer.main_status_body
                    self.send_response(outer.main_status_status)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return

                if self.path.startswith("/api/objects/info"):
                    body = outer.objects_info_body
                    self.send_response(outer.objects_info_status)
                    self.send_header("Content-Type", outer.content_type)
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return

                self.send_response(404)
                self.end_headers()

        self._httpd = HTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2)


def load_sample(name: str) -> bytes:
    """Load a sample sanitized Stellarium response from
    tests/fixtures/sample_responses/<name>."""
    import os

    path = os.path.join(os.path.dirname(__file__), "sample_responses", name)
    with open(path, "rb") as f:
        return f.read()


def canned_json(obj) -> bytes:
    return json.dumps(obj).encode("utf-8")
