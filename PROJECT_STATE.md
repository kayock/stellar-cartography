# Project state — FOXAI Stellar Cartography R0.5.0 (development)

**As of:** 2026-08-03  
**Release:** R0.5.0 — **in development** (Slice 1 landed; not packaged)  
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

## Explicit exclusions (still)

- IRSA / HEASARC adapters
- Historical moving-object archive matching
- Final R0.5.0 packaging / release receipt
- Starlink / general satellite tracking
- New third-party runtime dependencies

## Validation at Slice 1 landing

- Python: **180/180**
- Node: **141/141**
