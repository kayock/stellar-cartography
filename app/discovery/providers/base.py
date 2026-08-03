"""Provider adapter protocol for discovery (Slice 1)."""

from __future__ import annotations

from typing import Any, Protocol


class DiscoveryProvider(Protocol):
    """Stable internal interface for archive/discovery providers."""

    name: str

    def discover(self, context: dict[str, Any]) -> dict:
        """
        Return a DiscoveryBundle fragment:
          {items, query_outcomes, warnings, capability_notes}

        Must never raise for ordinary provider/network failures — those become
        query_outcomes. Unexpected bugs may still raise and are isolated by
        the orchestrator.
        """
        ...
