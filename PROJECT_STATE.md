# Project state — Stellar Cartography

**As of:** 2026-10-18  
**Status:** Six-Special series **complete**; public GitHub repository **live**  
**Repository:** https://github.com/kayock/stellar-cartography  
**License:** MIT (`LICENSE`)  
**Test baseline:** **513** Python tests (`python3 -m unittest discover -s tests`)

## Current product

Stellar Cartography is a stdlib Python + browser UI that drives **Stellarium
Remote Control** and presents:

- **Stories of the Sky** (constellation tours / exhibits)
- **Six Specials:** Light Echoes · Cosmic Web · Gravitational Waves · Black Holes · Galactic Encounters · Cosmic Dawn
- Earlier archive / watchlist / Solar System / Cosmic Signal / Spectrum Gallery features

Stellarium (including Windows Stellarium on another machine) is configured via
`--stellarium-url` / `STELLAR_CARTOGRAPHY_STELLARIUM_URL` — no LAN-specific values
are required in the public tree.

## Explicit exclusions

- Bundled Stellarium AppImage / installer
- Cloud API keys (none required for core use)
- Starlink / general satellite tracking
- Relicensing of third-party agency media (linked with credit; see `docs/MEDIA_PROVENANCE.md`)

## Historical baselines

| Milestone | Notes |
|-----------|--------|
| R0.4.0 | Archive lights, watchlist, Apophis — receipt under `receipts/baseline_r0.4.0/` |
| R0.5.0 development slices | Discovery, Cosmic Signal Deck, Spectrum Gallery (pre-Specials) |
| Six Specials | Complete / public |
| Public GitHub | First publish verified; presentation cleanup ongoing |

Historical README / Start Here text: `docs/history/`.

## Validation

- Python: **513/513** (`python3 -m unittest discover -s tests`)
- Optional Node: `node --test tests/frontend/*.test.js` (not part of the 513 count)
