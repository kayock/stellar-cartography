"""
Discovery orchestrator — isolates provider failures and merges bundles.

One failed or rate-limited provider must not erase successful results from
others. Slice 1 typically runs MAST only.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Iterable, Optional

from .models import (
    bundle_to_jsonable,
    dedupe_items_by_observation,
    empty_bundle,
    make_query_outcome,
    validate_bundle,
)

logger = logging.getLogger("stellar_archive_bridge.discovery.orchestrator")


def _merge_fragments(fragments: Iterable[dict]) -> dict:
    bundle = empty_bundle()
    for frag in fragments:
        if not isinstance(frag, dict):
            continue
        bundle["items"].extend(frag.get("items") or [])
        bundle["query_outcomes"].extend(frag.get("query_outcomes") or [])
        for w in frag.get("warnings") or []:
            if w and w not in bundle["warnings"]:
                bundle["warnings"].append(w)
        for n in frag.get("capability_notes") or []:
            if n and n not in bundle["capability_notes"]:
                bundle["capability_notes"].append(n)
    bundle["items"] = dedupe_items_by_observation(bundle["items"])
    return bundle


def run_discovery(
    context: dict[str, Any],
    providers: list[Any],
    *,
    provider_runner: Optional[Callable[[Any, dict], dict]] = None,
) -> dict:
    """
    Execute providers and return a validated DiscoveryBundle.

    ``provider_runner`` defaults to ``provider.discover(context)``. Tests may
    inject a fake runner.
    """
    fragments: list[dict] = []
    runner = provider_runner or (lambda p, ctx: p.discover(ctx))

    for provider in providers:
        name = getattr(provider, "name", None) or getattr(provider, "__name__", "unknown")
        try:
            frag = runner(provider, context)
        except Exception:  # noqa: BLE001 - deliberate isolation boundary
            logger.info("Discovery provider crashed provider=%s", name, exc_info=True)
            frag = {
                "items": [],
                "query_outcomes": [
                    make_query_outcome(
                        provider=str(name),
                        query_status="unavailable",
                        query_strategy="orchestrator_isolation",
                        target_name=context.get("target_name"),
                        target_category=context.get("target_category"),
                        message="Provider raised an unexpected error; other providers were not affected.",
                    )
                ],
                "warnings": [f"Provider '{name}' failed in isolation; other results were preserved."],
                "capability_notes": [],
            }
        if not isinstance(frag, dict):
            frag = {
                "items": [],
                "query_outcomes": [
                    make_query_outcome(
                        provider=str(name),
                        query_status="malformed_response",
                        query_strategy="orchestrator_isolation",
                        message="Provider returned a non-dict fragment.",
                    )
                ],
                "warnings": [],
                "capability_notes": [],
            }
        # Strip any accidental non-item statuses that were stuffed into items.
        safe_items = []
        for item in frag.get("items") or []:
            if isinstance(item, dict) and item.get("result_type"):
                safe_items.append(item)
        frag = {
            "items": safe_items,
            "query_outcomes": list(frag.get("query_outcomes") or []),
            "warnings": list(frag.get("warnings") or []),
            "capability_notes": list(frag.get("capability_notes") or []),
        }
        fragments.append(frag)

    bundle = _merge_fragments(fragments)
    errors = validate_bundle(bundle)
    if errors:
        bundle["warnings"].append("Discovery bundle failed internal validation: " + "; ".join(errors[:5]))
    return bundle_to_jsonable(bundle)
