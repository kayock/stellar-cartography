"""Discovery package — R0.5.0 Slice 1."""

from .models import (
    MATCH_BASES,
    MATCH_BASIS_PRECEDENCE,
    NON_ITEM_QUERY_STATUSES,
    QUERY_STATUSES,
    RESULT_TYPES,
    dedupe_items_by_observation,
    empty_bundle,
    make_discovery_item,
    make_query_outcome,
    merge_discovery_items,
    prefer_match_basis,
    validate_bundle,
)
from .orchestrator import run_discovery

__all__ = [
    "MATCH_BASES",
    "MATCH_BASIS_PRECEDENCE",
    "NON_ITEM_QUERY_STATUSES",
    "QUERY_STATUSES",
    "RESULT_TYPES",
    "dedupe_items_by_observation",
    "empty_bundle",
    "make_discovery_item",
    "make_query_outcome",
    "merge_discovery_items",
    "prefer_match_basis",
    "run_discovery",
    "validate_bundle",
]
