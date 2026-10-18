# Changelog

## v1.0.0 — 2026-10-18

First stable public release on GitHub: six Specials complete, MIT license, public install docs, screenshot gallery, and CI.


## R0.4.0 — 2026-07-31 — Archive Lights, Watchlist, Apophis Tracker

**Release label:** final release (live-validated)  
**Prior release:** R0.3.0 (`FOXAI_StellarCartography_R0.3.0_20260731.zip`, SHA-256 `b2a635ba6ef5e9b16d9aae5b8d01dc030a6e90bad50d3439942b4e2b5669c665`)

### Added

- **MAST archive-availability lights** — Hubble, JWST NIRCam, JWST MIRI; 0.01° search radius; Online Archive Mode gate; accessible state labels (not color-only).
- **Tracked Objects watchlist** — portable JSON at `runtime_data/tracked_objects.json`; atomic writes; `.bak` recovery; notes, favorites, unified Tracked Object Details panel.
- **Apophis 2029 tracker** — JPL SBDB + Horizons proxy; April 2029 encounter selection; cached tracker data; 60-second refresh rate limit; explicit **Use Ephemeris Position** (no automatic 0,0 sky navigation).
- **Watchlist load-failure protections** — failed startup load does not masquerade as empty list; writes blocked until successful load; Retry Load.
- **New modules:** `app/mast_archive.py`, `app/watchlist_store.py`, `app/apophis_tracker.py`, and matching `app/static/lib/*.js`.
- **Documentation:** `docs/ARCHIVE_AVAILABILITY.md`, `docs/TRACKED_OBJECTS.md`, `docs/APOPHIS_TRACKER.md`.

### Preserved

- R0.3 Planetary Image Pilot (Moon/Jupiter/Saturn only).
- R0.2 Solar System Awareness, ESASky FoV, honest notice.
- R0.1.4 zombie-queue repair and Online Archive Mode boundaries.

### Test totals at freeze

- Python: **161/161**
- Node: **134/134**

---

## R0.4.0 — 2026-07-31 — Archive Lights, Watchlist, Apophis Tracker (development)

**Release label:** superseded by final R0.4.0 release above  
**Prior release:** R0.3.0 (`FOXAI_StellarCartography_R0.3.0_20260731.zip`, SHA-256 `b2a635ba6ef5e9b16d9aae5b8d01dc030a6e90bad50d3439942b4e2b5669c665`)

### Added

- **`app/mast_archive.py`** — MAST CAOM `Mast.Caom.Filtered.Position` proxy; HST/JWST NIRCam/JWST MIRI only.
- **`app/static/lib/archive_availability.js`** — archive light state machine, cache, rate limits, accessible labels.
- **`app/watchlist_store.py`** — portable JSON watchlist with atomic writes and backup recovery.
- **`app/static/lib/watchlist.js`** — watchlist pure helpers and duplicate merge rules.
- **`app/apophis_tracker.py`** — JPL SBDB + Horizons proxy for 99942 Apophis.
- **`app/static/lib/apophis_tracker.js`** — Apophis panel view-model and refresh guards.
- **Tracked Objects panel** — add/remove/favorite/note/select/refresh; Apophis featured entry optional.
- **Documentation** — `docs/ARCHIVE_AVAILABILITY.md`, `docs/TRACKED_OBJECTS.md`, `docs/APOPHIS_TRACKER.md`.

### Test totals (development)

- Python: **151/151**
- Node: **98/98**

---

## R0.3.0 — 2026-07-31 — Planetary Image Pilot

**Release label:** final release (live-validated)  
**Prior release:** R0.2.0 (`FOXAI_StellarCartography_R0.2.0_20260731.zip`, SHA-256 `0b52d8ca5bf67814f262fa25cc4efaec9cea68bd58af3d893b1cffe2d29bc23a`)

### Added

- **`app/planetary_image.py`** — server-side NASA Images and Video Library API client; normalized pilot result model; HTTPS URL allow-list; 10 s timeout.
- **`app/static/lib/planetary_image.js`** — pilot target resolution (Moon/Jupiter/Saturn), request deduplication, stale-response guards, unsupported-target cache reset, panel view-model.
- **`/api/planetary-image?target=moon|jupiter|saturn`** — local proxy endpoint (Online Archive Mode enforced client-side).
- **Planetary Archive Image panel** — separate from ESASky; shows official NASA outreach imagery with attribution when available; clearly labeled as archival, not live or current appearance.
- **`docs/PLANETARY_IMAGE_PILOT.md`** — pilot scope, NASA data flow, Online Archive Mode gating, safe URL/DOM handling, stale-response and duplicate-request rules, unsupported-target behavior, limitations.
- **Fixtures and tests** — NASA Images API sample responses; 25 new Python tests; 24 new Node tests (including audit repairs and Moon→Mars→Moon cache-state regression).

### Changed

- **`app/static/app.js`** — planetary panel sync on target/online-mode changes; DOM-safe rendering via `createElement`/`src`/`href` property assignment; preserves R0.2 Solar System notice and ESASky behavior.
- **`app/server.py`** — optional injectable planetary fetcher for tests; version 0.3.0.
- **Version strings** updated across README, START_HERE, BUILD_RECEIPT, run.py, server, index.html, batch launcher.

### Preserved

- R0.2 Solar System detection, notice panel, bounded ESASky FoV.
- R0.1.4 zombie-queue repair and all ESASky queue/target-switch behavior.
- Offline-first default; planetary lookup only when Online Archive Mode is on.

### Request-state rules (R0.3.0)

- **Late supported response** cannot overwrite an unsupported-target panel (generation bump).
- **Same-target in-flight duplicate** requests are suppressed.
- **Same-target repeat** suppressed while a successful result remains visible on that target.
- **Unsupported Solar System target** clears completed-target dedup so returning to Moon/Jupiter/Saturn fetches again.
- **Online Archive Mode off/on** resets request state for a fresh lookup.

### Live validation (Eric, 2026-07-31)

**Result: PASS**

- Moon, Jupiter, and Saturn load official NASA archive images and metadata.
- Planetary imagery clearly labeled as archival, not live or current appearance.
- Moon → Mars unsupported → Moon fetches and displays Moon again.
- Late supported-target responses do not overwrite unsupported-target states.
- Same-target in-flight duplicate requests suppressed.
- Online Archive Mode off/on resets correctly.
- Safe DOM construction and official-host URL validation active.
- NASA center and keywords labeled truthfully; generic keywords not presented as mission names.
- ESASky, Solar System FoV, and zombie-queue behavior unchanged.

### Test totals at freeze

- Python: **121/121**
- Node: **78/78**

---

## R0.2.0 — 2026-07-31 — Solar System Awareness

**Release label:** final release (live-validated)  
**Prior release:** R0.1.4 (`FOXAI_StellarCartography_R0.1.4_20260731.zip`, SHA-256 `fba71f0001cb8ff562e5597bf1ed1768c0a92d9b4ecc0e85ae8a50af4cad78ad`)

### Added

- **`app/static/lib/solar_system.js`** — pure Solar System detection, bounded ESASky FoV derivation, and honest notice copy.
- **Solar System notice panel** — appears when Stellarium reports a Moon, planet, or other safely identifiable Solar System type; explains that ESASky shows survey background at the target coordinates, not a disk-resolved photograph.
- **Dual FoV display** — target card shows both Stellarium FoV and the derived ESASky viewer FoV for Solar System objects.
- **`docs/FUTURE_PLANETARY_IMAGERY.md`** — design note for a future dedicated planetary-image feature (PDS / PSA research; no API integration in this release).
- **Fixtures and tests** — Moon and Saturn Stellarium sample responses; 13 new Node tests; 4 new Python tests.

### Changed

- **`app/static/app.js`** — routes ESASky `setFov` and iframe URL `fov` through `SolarSystem.deriveEsaskyFovDeg()` for Solar System targets only; deep-sky FoV behavior unchanged.
- **Version strings** updated across README, START_HERE, BUILD_RECEIPT, run.py, server, index.html, batch launcher.

### Preserved

- ESASky zombie-queue repair (`recoverZombieEsaskyQueueIfNeeded`).
- Target-change-during-load sync, selection-failure clearing, Online Archive Mode shutdown.
- Offline-first operation; Online Archive Mode remains explicit and optional.

### Test totals at freeze

- Python: **96/96**
- Node: **54/54**

---

## R0.1.4 — 2026-07-31 — promoted known-good

- Zombie ESASky queue lifecycle fix (`recoverZombieEsaskyQueueIfNeeded`).
- Product rename to FOXAI Stellar Cartography.
- Live validation: first-target open, post-load re-selection, manual ESASky search navigation.
- Python 92/92, Node 41/41.

(See README.md “What changed in R0.1.4” for full detail.)
