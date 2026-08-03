"""
discovery_service.py

Slice 1 entry point used by the local server: run MAST discovery and return
a payload that feeds both the discovery panel and badge compatibility.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from app import mast_archive
from app.discovery.compat import discovery_api_payload
from app.discovery.orchestrator import run_discovery
from app.discovery.providers.mast import MastDiscoveryProvider


def run_mast_discovery(
    *,
    ra_deg: float | None,
    dec_deg: float | None,
    target_name: str | None = None,
    alt_name: str | None = None,
    aliases: list[str] | None = None,
    target_category: str | None = None,
    missions: list[str] | None = None,
    moving_target: bool = False,
    fetcher: Optional[Callable[[dict, float], dict]] = None,
) -> dict:
    missions = missions or list(mast_archive.MISSION_CONFIGS.keys())
    context: dict[str, Any] = {
        "ra_deg": ra_deg,
        "dec_deg": dec_deg,
        "target_name": target_name,
        "alt_name": alt_name,
        "aliases": aliases or [],
        "target_category": target_category,
        "missions": missions,
        "moving_target": moving_target,
    }
    provider = MastDiscoveryProvider(fetcher=fetcher)
    bundle = run_discovery(context, [provider])
    return discovery_api_payload(bundle, missions=missions)
