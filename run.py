#!/usr/bin/env python3
"""
FOXAI Stellar Cartography - entry point.

Starts a local web server (stdlib http.server) and opens the bridge UI in
the default web browser. Standalone: does not touch the FOXAI Observation
Deck or any other FOXAI project files.

Usage:
    python run.py [--port PORT] [--stellarium-url URL] [--no-browser]
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
import webbrowser

from app.server import find_free_port, run_server
from app import watchlist_store

APP_ROOT = watchlist_store.resolve_app_root(os.path.dirname(os.path.abspath(__file__)))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="FOXAI Stellar Cartography R0.4.0")
    parser.add_argument("--port", type=int, default=None, help="Port to serve the UI on (default: auto)")
    parser.add_argument(
        "--stellarium-url",
        type=str,
        default="http://127.0.0.1:8090",
        help="Base URL of Stellarium's Remote Control plug-in (default: http://127.0.0.1:8090)",
    )
    parser.add_argument("--no-browser", action="store_true", help="Do not auto-open a browser tab")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose (DEBUG) logging")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger = logging.getLogger("stellar_archive_bridge")

    port = args.port or find_free_port()
    httpd = run_server(
        host="127.0.0.1",
        port=port,
        stellarium_base_url=args.stellarium_url,
        watchlist_root=APP_ROOT,
    )
    url = f"http://127.0.0.1:{port}/"

    logger.info("FOXAI Stellar Cartography R0.4.0 serving at %s", url)
    logger.info("Watchlist storage: %s", watchlist_store.watchlist_relative_path())
    logger.info("Expecting Stellarium Remote Control (if used) at %s", args.stellarium_url)
    logger.info("Press Ctrl+C to stop.")

    if not args.no_browser:
        # Give the server a brief moment before opening the tab.
        def _open():
            time.sleep(0.4)
            webbrowser.open(url)

        import threading

        threading.Thread(target=_open, daemon=True).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down.")
        httpd.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
