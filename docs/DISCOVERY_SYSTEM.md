# Discovery System — R0.5.0 Slice 1

**Status:** Implemented in development (not a final R0.5.0 release package).

## Purpose

Replace narrow HST/JWST yes/no archive lights with an honest multi-strategy
discovery path that distinguishes:

- scientific **items** (`DiscoveryBundle.items`)
- provider **query outcomes** (`DiscoveryBundle.query_outcomes`)
- warnings and capability notes

A zero cone search must never be presented as “no Hubble/JWST/X-ray/infrared
information exists.”

## Contracts

### `query_status` (outcomes only)

`success`, `zero_results`, `unavailable`, `timeout`, `rate_limited`,
`malformed_response`, `unsupported`, `ephemeris_required`

Non-success statuses create **query outcomes only** — never fake scientific
items.

### `result_type` (items only; required and non-null)

`public_media_asset`, `archive_observation`, `science_image_product`,
`spectrum`, `catalog_detection`, `mission_metadata`, `object_information`,
`contextual_information`

### `match_basis`

`exact_target_name` → `alias_match` → `footprint_overlap` →
`resolved_position` → `cone_candidate` (precedence when merging)

Widened or coordinate cone hits are **`cone_candidate`** only — positional
candidates, not proof the selected object was the observation target.

## MAST strategies (Slice 1)

1. Exact `target_name` aliases (before any wildcard)
2. Bounded free-text `target_name` only after exact aliases miss
3. `Mast.Name.Lookup` → resolved-position cone
4. Coordinate cone radius ladder: 0.01°, 0.05°, 0.2°

Deduplication merges provenance across strategies (strategies, match bases,
aliases, radii, smallest successful radius). Counts are post-dedup.

## Moving objects (Slice 1 limit)

Solar System / moving targets receive:

> Historical archive coverage for this moving object was not evaluated.

R0.5.0 does **not** perform exhaustive historical per-observation-epoch
archive matching.

## API

- `GET /api/discovery` — primary; response includes `bundle` + `badges`
- Frontend: **one** discovery request feeds the panel **and** badge adapter
- Do **not** also call `/api/archive-availability` for the same selection
- Online Archive Mode off → zero discovery/archive requests
- `/api/archive-availability` remains as an R0.4 compatibility facade

## Badge compatibility (conservative)

- `no_coverage` only when every required MAST strategy completed normally
  (`success` or `zero_results`) and no items were found
- Any timeout / unavailable / rate_limited / malformed with no items →
  `unavailable`
- Items found while another strategy failed → `confirmed` + partial-failure
  warning

## Explicitly not in Slice 1

- IRSA
- HEASARC
- Historical moving-object archive matching
- Final R0.5.0 release receipt / package

## Official sources

- MAST Portal API v0: https://mast.stsci.edu/api/v0/
- Services: https://mast.stsci.edu/api/v0/_services.html

No new third-party runtime dependencies. No API key required for MAST.
