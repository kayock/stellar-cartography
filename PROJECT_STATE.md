# Project state — FOXAI Stellar Cartography R0.4.0

**As of:** 2026-07-31  
**Release:** R0.4.0 — Archive Lights, Watchlist, Apophis Tracker (final, live-validated)  
**Baseline:** R0.3.0 — Planetary Image Pilot (promoted, protected)

## Prior release (unchanged)

**R0.3.0 release:** `FOXAI_StellarCartography_R0.3.0_20260731.zip`  
SHA-256: `b2a635ba6ef5e9b16d9aae5b8d01dc030a6e90bad50d3439942b4e2b5669c665`  
Validation at freeze: Python 121/121, Node 78/78

## R0.4.0 scope delivered

| Requirement | Status |
|-------------|--------|
| MAST archive-availability lights (Hubble, JWST NIRCam, JWST MIRI) | Done |
| 0.01° MAST search radius; truthful accessible states | Done |
| Local Tracked Objects watchlist (portable JSON, atomic writes, backup recovery) | Done |
| Notes, favorites, unified Tracked Object Details | Done |
| Apophis 2029 featured tracker (JPL SBDB + Horizons) | Done |
| April 2029 encounter selection; Horizons $$SOE/$$EOE parsing | Done |
| Apophis does not navigate sky on placeholder 0,0; explicit Use Ephemeris Position | Done |
| Watchlist load-failure protections; write blocking until successful load | Done |
| Apophis 60-second refresh rate limit honored | Done |
| Preserve R0.3 planetary pilot + R0.2 Solar System + R0.1.4 ESASky queue | Done |
| Automated tests | Done (161 Python, 134 Node) |
| Documentation | Done (`docs/ARCHIVE_AVAILABILITY.md`, `docs/TRACKED_OBJECTS.md`, `docs/APOPHIS_TRACKER.md`) |
| Release packaging | **Complete** |

## Explicit exclusions (R0.4)

- Starlink tracking
- General artificial-satellite tracking
- MAST browser UI or FITS download
- Continuous background monitoring
- Planetary imagery beyond Moon/Jupiter/Saturn

## Validation at freeze

- Python: **161/161**
- Node: **134/134**
- Python compilation: pass
- JavaScript syntax checks: pass
- ResourceWarning-as-error Python run: pass

## User data

Personal watchlist files (`runtime_data/tracked_objects.json` and `.bak`) are **not** shipped in the release ZIP. Back up before upgrading; restore into `runtime_data\` of an extracted copy for personal use.
