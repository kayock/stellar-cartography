# Project state — FOXAI Stellar Cartography R0.5.0 (development)

**As of:** 2026-08-03  
**Release:** R0.5.0 — **in development** (Slice 1 + Solar System Media Expansion landed; not packaged)  
**Baseline:** R0.4.0 — preserved under `receipts/baseline_r0.4.0/` (immutable)

## Baseline receipt quarantine

R0.4.0 `BUILD_RECEIPT` / `SHA256SUMS` were moved byte-for-byte to:

- `receipts/baseline_r0.4.0/BUILD_RECEIPT_R0.4.0.json`
- `receipts/baseline_r0.4.0/SHA256SUMS_R0.4.0.txt`

Those checksum paths are historical evidence of the R0.4.0 archive layout —
**not** a current manifest for this working tree. There is no R0.5.0 release
receipt yet (`receipts/WORK_IN_PROGRESS.md`).

## Slice 1 delivered

| Requirement | Status |
|-------------|--------|
| Discovery contracts (`items` vs `query_outcomes`) | Done |
| Orchestrator + provider failure isolation | Done |
| Honest MAST multi-strategy discovery | Done |
| Dedup with merged provenance + match_basis | Done |
| Discovery panel skeleton | Done |
| Badge compatibility (conservative mapping) | Done |
| Single `/api/discovery` request (no duplicate archive-availability) | Done |
| Moving-object historical coverage not evaluated | Done |
| Automated tests | Done (Python 180, Node 141 at Slice 1 landing) |

## Solar System Media Expansion delivered

| Requirement | Status |
|-------------|--------|
| Data-driven Solar System media registry | Done |
| Sun, major planets, dwarfs, major moons | Done |
| NASA Images API + `public_media_asset` classification | Done |
| Relevance filtering / generic-guard | Done |
| Online Mode off → zero NASA media requests | Done |
| Stale / dedup / target-switch clear preserved | Done |
| Visibly separate from MAST + ESASky | Done |
| Automated tests | Done (Python 198, Node 175) |

## Explicit exclusions (still)

- IRSA / HEASARC adapters
- MAST science-product expansion
- Historical moving-object archive matching
- Final R0.5.0 packaging / release receipt
- Starlink / general satellite tracking
- New third-party runtime dependencies

## Validation (current worktree)

- Python: **198/198** (`PYTHONWARNINGS=error`)
- Node: **175/175**
