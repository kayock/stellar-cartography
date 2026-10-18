# Stellar Cartography — Public Presentation Cleanup

**Date:** 2026-10-18  
**Repository:** https://github.com/kayock/stellar-cartography  
**Branch:** `main`  
**Scope:** Documentation, public launchers, screenshots, optional CI — no application behavior changes.

---

## Verdict

Presentation cleanup + live screenshot gallery validated; pushed to `main` (no tag).

---

## Documentation / launcher fixes

### 1. `CONTRIBUTING.md`

- Removed nonexistent `frontend/package.json` / `npm ci` / `npm test`
- Documented `tests/frontend/*.test.js` with `node --test tests/frontend/*.test.js`

### 2. `START_HERE.md`

- Rewrote as current public entry point
- Historical R0.4.0 text → `docs/history/START_HERE_R0.4.0.md`

### 3. `PROJECT_STATE.md`

- Six Specials complete; public GitHub live; **513** Python baseline
- No LAN addresses

### 4. Windows launcher

- Added `Start_Stellar_Cartography.bat`
- `Start_FOXAI_Stellar_Cartography.bat` kept as compatibility wrapper

### 5. `LICENSE_RECOMMENDATION.md`

- Removed (MIT already in `LICENSE`; third-party notes in `docs/MEDIA_PROVENANCE.md`)

### 6. `README.md`

- Focused public README; historical body → `docs/history/R0.4.0_PRODUCT_README.md`
- Clone URL: `https://github.com/kayock/stellar-cartography.git`
- Live screenshot gallery (hero + compact six-Special table)

### 7. Links

Local Markdown links in README, START_HERE, CONTRIBUTING, SECURITY, PUBLIC_INSTALL, PROJECT_STATE — verified.

### 8. CI

Added `.github/workflows/tests.yml` — Python unittest + Node `node:test` (no npm packages).

---

## Screenshots

Captured from **live** production UI (application content only; no browser chrome).

| File | Subject |
|------|---------|
| `docs/images/stellar-cartography-home.png` | Home / main view |
| `docs/images/special-light-echoes.png` | Light Echoes |
| `docs/images/special-cosmic-web.png` | Cosmic Web |
| `docs/images/special-gravitational-waves.png` | Gravitational Waves |
| `docs/images/special-black-holes.png` | Black Holes |
| `docs/images/special-galactic-encounters.png` | Galactic Encounters |
| `docs/images/special-cosmic-dawn.png` | Cosmic Dawn |
| `docs/images/stories-of-the-sky.png` | Stories of the Sky (optional) |

Image privacy: strings scan clean of private LAN addresses and home/library paths. Visible network text limited to loopback Remote Control examples and public ESASky hostname in UI copy.

---

## Clone URL replacement

- `README.md` → real GitHub URL
- `docs/PUBLIC_INSTALL.md` → real GitHub URL

---

## Regression

| Suite | Result |
|-------|--------|
| Python `unittest discover -s tests` | **513 PASS** |
| Node `node --test tests/frontend/*.test.js` | **254 PASS** (optional; not part of 513) |
| Production `:8775` | Untouched / healthy during docs work |

---

## Privacy recheck (tracked docs)

Scanned changed Markdown / workflows / images for private LAN and home-directory paths — **clean**.
