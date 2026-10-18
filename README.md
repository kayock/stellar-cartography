# Stellar Cartography

**Browser-based educational bridge for [Stellarium](https://stellarium.org/)** — select sky objects, open archive viewers, run curated **Stories of the Sky** and six **Specials**, with optional local narration/TTS.

> **Status:** Feature-complete for the six Specials series (Light Echoes → Cosmic Dawn) plus earlier archive / watchlist / Solar System work. Stellarium is an **external** dependency (do not expect an AppImage in this repo). Licensed under the **MIT License** — see `LICENSE`. Third-party media retain their own terms (`docs/MEDIA_PROVENANCE.md`).

---

## Features (at a glance)

- **Stellarium Remote Control** integration (exact name, host-sky, or coordinate hosting)
- **Stories of the Sky** / constellation tours and exhibit flows
- **Six Specials:** Light Echoes · Cosmic Web · Gravitational Waves · Black Holes · Galactic Encounters · Cosmic Dawn
- **NASA / Chandra / ESA / survey media** via remote URLs and provenance fields (not bundled binaries)
- **Optional local TTS** (Father Fox / Kayock Voice style HTTPS endpoints on loopback)
- **Stdlib-only Python runtime** (Python ≥ 3.9) — no pip packages required to run

---

## Quick start

```bash
git clone <YOUR_REPO_URL> stellar-cartography
cd stellar-cartography
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt   # documents Python ≥3.9; installs nothing else
cp .env.example .env              # optional documentation of env vars

# Stellarium Remote Control must be reachable (example: same machine)
./start.sh --host 127.0.0.1 --port 8775 --stellarium-url http://127.0.0.1:8090
```

Open `http://127.0.0.1:8775`. Full install, Windows Stellarium + Linux Cartography, and troubleshooting: **[docs/PUBLIC_INSTALL.md](docs/PUBLIC_INSTALL.md)**.

### Configuration

| Variable / flag | Purpose | Example |
|-----------------|---------|---------|
| `--host` / `STELLAR_CARTOGRAPHY_HOST` | Bind address | `127.0.0.1` or `0.0.0.0` |
| `--port` / `STELLAR_CARTOGRAPHY_PORT` | UI port | `8775` |
| `--stellarium-url` / `STELLAR_CARTOGRAPHY_STELLARIUM_URL` | Remote Control base | `http://127.0.0.1:8090` |
| `STELLAR_CARTOGRAPHY_TTS_HOSTS` | Extra TTS allowlist hosts | unset (loopback only) |

Public launcher template: `start-production.example.sh`.

### Prerequisites

- Python **3.9+**
- **Stellarium** with **Remote Control** plugin enabled
- Modern browser
- Optional: Node.js ≥ 18 for frontend unit tests only

### Tests

```bash
python3 -m unittest discover -s tests -v
```

---

## Architecture (short)

```
Browser UI ──► Cartography (Python stdlib http.server)
                    │
                    ├── Stellarium Remote Control (HTTP)
                    ├── Official media / NASA proxies (optional online)
                    └── Local TTS HTTPS (optional, allowlisted)
```

Specials live under `app/*` modules + `app/data/*_registry.json` + `app/static/lib/*.js`.

Media provenance: **[docs/MEDIA_PROVENANCE.md](docs/MEDIA_PROVENANCE.md)**. Contributing: **[CONTRIBUTING.md](CONTRIBUTING.md)**. Security: **[SECURITY.md](SECURITY.md)**.

---

## License

Stellar Cartography project code and project-authored docs are released under the **MIT License** (see [`LICENSE`](LICENSE)).

Third-party media and Stellarium are **not** covered by that grant — see [`docs/MEDIA_PROVENANCE.md`](docs/MEDIA_PROVENANCE.md).

## Attribution

Imagery and multimedia are typically **linked** from agency sources (NASA, ESA, STScI, ESO, Chandra, LIGO/Virgo/KAGRA, EHT, surveys, etc.). Credits appear in Specials registries and the UI. Stellarium is trademarked by its authors; this project does not redistribute Stellarium.

---

## Historical README (R0.4.0 lineage)

The sections below preserve the original R0.4.0 product documentation (ESASky bridge, archive lights, watchlist, Apophis). They remain accurate for those features; prefer the Quick start above for a fresh install.


# FOXAI Stellar Cartography — R0.4.0

A standalone, additive proof-of-concept sidecar for FOXAI. It lets you select
an object in **Stellarium**, pull that selection's J2000 coordinates through
Stellarium's local **Remote Control** HTTP API, and open an **ESASky**
archive viewer at the same coordinates with simple telescope/wavelength
imagery choices.

This is a separate, self-contained project. It does **not** modify the
FOXAI Observation Deck, Stellarium, or ESASky. It does not bundle Stellarium
or ESASky, and it does not require any API key.

> **R0.4.0 status:** **Archive Lights, Watchlist, and Apophis Tracker** release
> (live-validated). Adds MAST archive-availability lights (Hubble/JWST),
> portable Tracked Objects watchlist with notes and unified details, and a
> featured Apophis 2029 tracker using official JPL APIs. Preserves R0.3
> Planetary Image Pilot (Moon/Jupiter/Saturn), R0.2 Solar System Awareness,
> and R0.1.4 ESASky zombie-queue repair. **No Starlink or general satellite
> tracking in R0.4.**
>
> **Lineage:** R0.1.4 → **R0.2.0** (Solar System) → **R0.3.0** (Planetary
> Pilot) → **R0.4.0** (Archive lights, watchlist, Apophis).

---

## What it does

1. You select an object in Stellarium (with the Remote Control plug-in
   enabled on `localhost:8090`).
2. You press **"Use Stellarium Selection"** in this app.
3. The app asks Stellarium (locally) for the current selection via
   `GET /api/objects/info?format=json`, using Stellarium's *documented*
   getInfoMap shape (numeric `raJ2000` / `decJ2000` in decimal degrees) as
   the first-class coordinate representation, with tolerant sexagesimal-text
   and direction-vector fallbacks for other Stellarium/plugin variants.
4. It separately asks `GET /api/main/status` for the current field of view
   (`view.fov`) — FoV is never expected inside the selection response
   itself, and failing to read it never blocks a selection from succeeding.
5. It shows the object's preferred name, alternate designation (when
   available), object type, J2000 RA/Dec, and the current field of view
   (when available). An **"About This Object"** card additionally surfaces,
   whenever Stellarium actually reports them: catalogue/alternate
   designations, object category (`type`) and detailed type (`object-type`),
   subtype, constellation, apparent magnitude, angular size, current
   altitude/azimuth, and whether the object is currently above the horizon.
   A field is simply omitted (never shown as a blank or invented value) if
   Stellarium didn't supply it. A small number of implausible sentinel
   values some catalogs use for "unknown" (e.g. magnitude 99.99) are
   filtered out rather than displayed as real data.
6. If you turn on **Online Archive Mode**, it opens an embedded ESASky
   viewer at those coordinates and offers imagery buttons (Default Optical,
   Hubble, JWST NIRCam, JWST MIRI, WISE Infrared, Spitzer Infrared, Herschel
   Far-Infrared, X-Ray, Microwave). Each button asks ESASky's own catalogue
   of available all-sky imagery (HiPS layers) whether a matching layer
   exists for that telescope/wavelength, using explicit alias groups (e.g.
   "HST" or "Hubble" for the Hubble button; any of XMM-Newton / eROSITA /
   ROSAT / Chandra for X-Ray) rather than a rigid "every keyword must
   match" rule, and reports plainly if nothing matches — the app never
   assumes a telescope observed every target, and never claims that a
   missing layer means a telescope didn't observe the target (only that no
   matching ESASky layer was found).
7. **Solar System Awareness (R0.2.0):** when Stellarium reports a Moon,
   planet, or other safely identifiable Solar System type, a dedicated
   notice explains that ESASky shows the **sky-survey background** at those
   coordinates — not a close-up planetary photograph — and the app sends a
   **bounded ESASky viewer FoV** (see `PROJECT_STATE.md`) rather than
   Stellarium's often very wide field of view. The target card shows both
   Stellarium FoV and the derived ESASky viewer FoV.
8. **Planetary Image Pilot (R0.3.0):** when Online Archive Mode is on and
   Stellarium reports Moon, Jupiter, or Saturn, a separate **Planetary
   Archive Image** panel fetches an official NASA outreach image and
   metadata through the local `/api/planetary-image` proxy (NASA Images and
   Video Library API). Imagery is labeled as **archival** — not live or
   current appearance. Unsupported Solar System targets (e.g. Mars) show an
   honest fallback without a network call.
9. **Archive availability lights (R0.4.0):** when Online Archive Mode is on,
   Hubble and JWST imagery buttons show MAST metadata counts at the current
   target (0.01° search radius). Lights use accessible text labels — not
   color alone. Zero MAST requests when Online Archive Mode is off.
10. **Tracked Objects (R0.4.0):** local watchlist stored in
    `runtime_data/tracked_objects.json` with atomic writes and `.bak`
    recovery. Add/remove/favorite/note/**Open Details**; not continuous
    background monitoring.
11. **Apophis 2029 tracker (R0.4.0):** optional featured entry using JPL
    SBDB and Horizons; April 2029 encounter selection; cached offline
    summary; 60-second refresh minimum; **Use Ephemeris Position** for
    explicit sky navigation (opening Apophis does not use placeholder 0,0).

Stellarium is entirely optional. Everything also works with a **manual
target form** (name + decimal or sexagesimal RA/Dec), including when
Stellarium is closed or the Remote Control plug-in is off.

---

## What changed in R0.4.0

**Archive lights, watchlist, and Apophis tracker** on live-validated R0.3.0.

1. **`app/mast_archive.py`** — MAST CAOM position filter proxy; HST/JWST NIRCam/JWST MIRI; 0.01° radius; bounded responses.
2. **`app/watchlist_store.py`** — portable JSON watchlist; atomic writes; backup recovery; app-root path anchoring.
3. **`app/apophis_tracker.py`** — JPL SBDB + Horizons; April 2029 encounter rule; $$SOE/$$EOE ephemeris parsing.
4. **Tracked Objects UI** — load/save status, unified Tracked Object Details, explicit Save Note, Retry Load on failure.
5. **Apophis integrity** — no automatic 0,0 sky target; explicit Use Ephemeris Position; 60-second refresh rate limit.
6. **User data** — personal watchlist files excluded from release ZIP; restore from backup into `runtime_data\`.

See `docs/ARCHIVE_AVAILABILITY.md`, `docs/TRACKED_OBJECTS.md`, `docs/APOPHIS_TRACKER.md`.

---

## What changed in R0.3.0

**Planetary Image Pilot** on top of live-validated R0.2.0. Adds NASA archive
imagery for Moon, Jupiter, and Saturn only. Does not add MAST searching, FITS
download, or telescope control. Offline-first preserved.

1. **`app/planetary_image.py`** — server-side NASA Images and Video Library
   API client; normalized result model; HTTPS host allow-list (`images-assets.nasa.gov`,
   `images.nasa.gov`); 10 s timeout; truthful metadata (NASA center, keywords;
   mission only when explicitly populated).
2. **`app/static/lib/planetary_image.js`** — pure module for pilot target
   resolution, request deduplication, stale-response guards, unsupported-target
   cache reset, and panel view-model.
3. **Planetary Archive Image panel** — separate from ESASky; DOM-safe rendering
   via `createElement` and property assignment (no remote string interpolation
   into HTML attributes); archive truthfulness wording on every view.
4. **Online Archive Mode gating** — zero planetary network calls when offline;
   toggling off/on resets request state for a fresh lookup.
5. **Request-state rules** — late supported responses cannot overwrite
   unsupported-target states; same-target in-flight duplicates suppressed;
   same-target repeat suppressed while successful result remains visible;
   unsupported Solar System selection clears completed dedup so returning to
   Moon/Jupiter/Saturn fetches again.
6. **Tests** — NASA Images fixtures; 121 Python + 78 Node at freeze; includes
   stale-response, duplicate-fetch, DOM-safety, and Moon→Mars→Moon regression.
7. **`docs/PLANETARY_IMAGE_PILOT.md`** — pilot scope, data flow, privacy,
   limitations, and safe extension guide.

**Live validation PASS** (Eric, 2026-07-31): Moon/Jupiter/Saturn NASA images,
archive labeling, Moon→Mars→Moon refetch, stale-response guards, duplicate
suppression, Online Mode reset, ESASky and Solar System behavior preserved.

See also `CHANGELOG.md` and `PROJECT_STATE.md`.

---

## What changed in R0.2.0

**Solar System Awareness** on top of promoted R0.1.4. Does not add planetary-image
APIs, MAST searching, or FITS download. Offline-first preserved.

1. **`app/static/lib/solar_system.js`** — pure module for Solar System
   detection (Stellarium `object_category` / `object_type` fields only — no
   name guessing), bounded ESASky FoV derivation, and honest notice copy.
2. **Solar System notice panel** — labeled card explaining ESASky shows
   survey background at the target coordinates; HiPS may lack disk-resolved
   imagery; survey tiles are not the object's current appearance; navigation
   to reported RA/Dec is still correct.
3. **Bounded ESASky FoV** — Solar System targets never blindly forward wide
   Stellarium FoV (e.g. 60°). Derived FoV clamped to 0.15°–2.0° using
   angular size when reported (×4 margin) or 0.5° default. Stars, galaxies,
   and nebulae keep existing FoV pass-through.
4. **Tests** — Moon/Saturn fixtures; 13 Node + 4 Python tests for detection,
   FoV clamping, notice text, and ESASky navigation regressions.
5. **`docs/FUTURE_PLANETARY_IMAGERY.md`** — design note for future dedicated
   planetary photographs (NASA PDS / ESA PSA research only; not implemented).
6. **Live validation PASS** (Eric, 2026-07-31): Moon/planet detection,
   notice card, dual FoV display, Moon 2.000° vs Stellarium 60.000°, ESASky
   target updates, deep-sky unchanged, zombie-queue did not recur.

**Expected limitation:** ESASky HiPS layers did not show dedicated
disk-resolved Moon/planet images — blank or generic survey background is
normal. Dedicated planetary photos remain a future feature.

See also `CHANGELOG.md` and `PROJECT_STATE.md` for detection/FoV rules.

---

## What changed in R0.1.4

Promoted known-good release on top of R0.1.3. Product renamed from **FOXAI
Stellar Archive Bridge** to **FOXAI Stellar Cartography** in user-facing
labels only; internal Python logger names are unchanged. Does not touch the
Observation Deck, does not add MAST searching, and does not expand scope.

1. **Zombie ESASky queue lifecycle repaired.** After the first ESASky open,
   the one-shot iframe `load` handler always detached itself — even when
   `markReadyIfActive()` returned false (e.g. the session generation was
   cancelled while the iframe was still loading). That left
   `loadListenerAttached=true` and `ready=false` with no handler left to
   flush queued `goToRaDec`/`setFov` commands. The first target still
   looked correct (baked into the initial iframe URL), but later Stellarium
   selections updated the object panel while ESASky stayed on the previous
   view. Added `recoverZombieEsaskyQueueIfNeeded()` in `app.js`, called
   from `sendEsaskyCommand()` before `enqueueOrSend()`: when Online Archive
   Mode is on, a session has begun, the queue is not ready, no load handler
   is pending, and the iframe is already on `sky.esa.int`, it clears
   `cancelled` and calls the existing `EsaskyQueue.markReady()` to flush
   any stranded queue before dispatching the new command. Deliberately
   no-ops while `esaskyLoadHandler` is still attached (genuine in-flight
   load). Does not reload the iframe. Online Archive Mode shutdown/reset
   behavior and `replaceKey` navigation dedup are unchanged.
2. **Two browser-DOM integration regression tests added**
   (`tests/frontend/app_dom_integration.test.js`): post-load target switch
   (ESASky already `ready`, selecting target B must dispatch B's
   `goToRaDec`/`setFov`) and zombie-queue recovery (session started but
   never marked ready; selecting target B must still dispatch navigation).
   The zombie test failed against pre-fix `app.js` and passes with this
   repair; the post-load test passes on both (healthy path preserved).
3. **Live validation completed** against real Stellarium Remote Control and
   live ESASky: first-target open, post-load Stellarium re-selection, and
   viewer navigation after manual ESASky search all confirmed working.

---

## What changed in R0.1.3

A final narrow integration repair on top of R0.1.2. Does not touch the
Observation Deck, does not add MAST searching, and does not expand scope.

1. **Target changes during an in-flight ESASky load are now wired into the
   real `app.js` workflow, not just the pure queue module.**
   `renderTargetCard()`'s old check
   (`state.onlineMode && state.esaskyQueue.ready`) meant that if ESASky was
   still loading when the target changed, the target card would update but
   no `goToRaDec`/`setFov` was ever queued for the new target -- ESASky
   would finish loading on the *previous* target while the app displayed
   the new one. A shared `syncEsaskyToCurrentTarget()` function now runs
   from `renderTargetCard()` (the single path every successful Stellarium
   selection and successful manual entry already goes through): if the
   queue is ready it sends immediately, if the iframe is still loading it
   queues via the existing `replaceKey`-based `EsaskyQueue.enqueueOrSend()`
   so only the newest target's commands survive. It only acts once an
   ESASky session has actually begun (`state.esaskyQueue.loadListenerAttached`)
   -- toggling Online Archive Mode on, by itself, still never starts an
   iframe session. A new browser-DOM integration test
   (`tests/frontend/app_dom_integration.test.js`) runs the real `app.js`
   inside a Node `vm` context against a minimal dependency-free fake DOM
   (`tests/frontend/dom_stub.js`, `app_loader.js`), dispatching real click
   and iframe `load` events, and proves target A loading, then target B
   arriving before readiness, ends with only B's position/FoV dispatched
   and no trace of A left in the queue.
2. **A failed selection request via a thrown exception now clears the
   stale target too.** The `/api/selection` `{ok:false}` branch already
   called `clearStaleTargetAfterFailedSelection()`; the `catch` branch for
   a network failure or unparseable JSON only changed the visible message,
   leaving the previous `currentTarget`, "About This Object" card, and
   enabled "Open in ESASky" button fully active underneath it. Both
   branches now call the same `clearStaleTargetAfterFailedSelection()`.
   Covered by a new browser-DOM integration test
   (`tests/frontend/app_selection_failure.test.js`).
3. **`/api/status` is now failure-safe against a malformed response on the
   configured Stellarium port.** `StellariumClient.check_connection()`
   previously only caught unreachability errors
   (`URLError`/`OSError`/`TimeoutError`) and let `json.JSONDecodeError`,
   `UnicodeDecodeError`, and `ResponseTooLargeError` propagate, which would
   have taken the `/api/status` request handler down with them if
   `/api/main/status` (or an unrelated service on the same port) returned
   malformed, non-UTF-8, or oversized content. Semantics: network
   unreachable → `connected=false`; any real HTTP response, however
   malformed its body → `connected=true` (something *is* listening and
   answering). Raw response content is never logged or exposed, only the
   sanitized exception type. `server.py`'s `/api/status` handler also gets
   a last-resort `try/except` backstop around the call itself. Covered by
   new client-level tests (`tests/test_stellarium_client.py`,
   `TestCheckConnectionFailureSafe`) and server-integration tests
   (`tests/test_server_integration.py`, `TestStatusEndpointFailureSafe`)
   for malformed JSON, invalid UTF-8, oversized, ordinary-valid, and
   unreachable cases.

---

## What changed in R0.1.2

A narrower follow-up repair -- frontend browser-state correctness and
defensive numeric parsing. Does not touch imagery matching, changeHips
confirmation, or the Observation Deck; does not add MAST searching.

1. **Stale ESASky iframe load events fixed with a session-generation
   token.** `app/static/lib/esasky_queue.js` now tracks a `generation`
   number, bumped by `beginSession()` for every fresh ESASky navigation.
   A load handler must call `markReadyIfActive()` with the generation it
   captured; this is a no-op unless Online Archive Mode is still on and
   that generation is still current and non-cancelled. Turning Online
   Archive Mode off (`turnOnlineModeOff()`) invalidates the active
   generation *and* detaches the load handler before the iframe `src` is
   set to `about:blank` -- so a stale load firing on that `about:blank`
   navigation can no longer flip the queue to "ready" while the UI says
   offline. `queue.ready` is reset to `false` at the start of every fresh
   navigation, and at most one `load` listener is ever attached to the
   iframe at a time.
2. **Target changes during an in-flight load no longer get lost or
   stale.** `goToRaDec`/`setFov` commands queued while ESASky is still
   loading now carry a `replaceKey`; `EsaskyQueue.enqueueOrSend()` drops
   any previously queued command with the same key before appending the
   new one. Picking a new Stellarium selection or submitting new manual
   coordinates before the iframe finishes loading now always lands on the
   latest target and the latest field of view, never an old one the
   viewer "catches up" to after the fact -- and the queue never
   accumulates obsolete navigation commands.
3. **A failed/empty Stellarium selection no longer leaves a stale target
   actionable.** `TargetModel.buildFailedSelectionState()` (new, pure) plus
   `app.js`'s `clearStaleTargetAfterFailedSelection()` clear
   `currentTarget`, hide/clear the "About This Object" card, disable "Open
   in ESASky", clear active imagery-button styling, and cancel any
   in-flight `getAvailableHips`/`changeHips` request tied to the prior
   target -- rather than silently continuing to treat that prior target as
   current. An already-open ESASky iframe is left alone.
4. **Non-finite numeric values (NaN, Infinity, -Infinity) are rejected,
   not silently propagated.** `app/coords.py` and
   `app/stellarium_client.py` now use `math.isfinite()` everywhere a
   numeric value is parsed -- RA, Dec, direction-vector components, manual
   coordinate entry, field of view, apparent magnitude, angular size,
   altitude, and azimuth. A non-finite value (numeric or a numeric-looking
   string such as `"nan"` / `"inf"` / `"-Infinity"`) is treated as though
   that field were absent: coordinate extraction returns `ok:false`
   instead of producing `nan` or crashing during sexagesimal formatting,
   and optional metadata is simply omitted.
5. **Honest receipt hash language.** This file's own build receipt
   (`BUILD_RECEIPT.json`) no longer places a prior-pass ZIP hash in a field
   named as if it were the final package's hash -- a ZIP cannot contain its
   own final hash. `package.archive_sha256` is `null`, with
   `archive_sha256_location`/`archive_sha256_note` explaining why, and the
   exact final ZIP SHA-256 is reported directly in the delivery response
   instead.

---

## What changed in R0.1.1

Fixes made in response to an independent audit of R0.1.0:

1. **Documented Stellarium coordinates.** Numeric `raJ2000` / `decJ2000`
   (Stellarium's documented getInfoMap shape) are now first-class
   decimal-degree fields in `app/coords.py`, tried before any legacy/plugin
   alias. The same key names still fall back correctly to the sexagesimal
   parser when Stellarium sends a sexagesimal string under them instead.
2. **Field of view.** No longer read from the selection response. Sourced
   from a separate `GET /api/main/status` call (`view.fov`), merged in by
   `StellariumClient.get_selection()`. Missing/unreachable FoV never fails
   a selection.
3. **About This Object.** Added `object_category` (from `type`), angular
   size (`size-dd`), current altitude/azimuth, and above-horizon, alongside
   the existing R0.1.0 fields (subtype, catalogue designations, etc., all
   still supported via their original tolerant aliases).
4. **ESASky iframe readiness.** `getAvailableHips`, `changeHips`,
   `goToRaDec`, and `setFov` are now routed through a small command queue
   (`app/static/lib/esasky_queue.js`) that holds them until the iframe's
   `load` event fires, then flushes them in order. Nothing is silently
   dropped on the first click, and the load listener is attached at most
   once per iframe session.
5. **Imagery matching.** Replaced the old "every keyword must match"
   filter with explicit alias groups per button
   (`app/static/lib/imagery_matching.js`), with a `preferred` list used to
   pick the best layer when several match (e.g. "XMM-Newton EPIC color"
   preferred among X-ray options).
6. **Honest coverage language.** `getAvailableHips` confirming a layer
   *exists* is no longer described as confirming the telescope observed the
   target. Wording was corrected accordingly (see `app/static/lib/
   imagery_matching.js` usage in `app.js` and the in-app explainer text).
7. **changeHips confirmation.** `app/static/lib/changehips.js` interprets
   ESASky's response instead of reporting "Loaded" the instant the command
   is sent — success, documented failure (e.g. `extras.message`), and
   timeout are all handled distinctly. The default optical button follows
   the same rule.
8. **Online Archive Mode off, for real.** Turning it off
   (`app/static/lib/online_mode.js` + `app.js`'s `turnOnlineModeOff()`)
   cancels pending timers, blanks and hides the iframe, resets the
   readiness queue, clears active button styling, and blocks further
   ESASky commands until the user re-enables it.
9. **Tests match the shipped code.** The previously-unused
   `app/esasky_params.py` module was removed (it was tested but never
   wired into the real request path). Its safety guarantees (RA/Dec/FoV
   clamping, no unexpected keys) are instead enforced directly in
   `app.js`'s URL-parameter construction, and the pure JS matching/queueing
   logic that *is* actually used is now covered by build-time Node tests
   (see "Running the tests" below).

---

## Architecture

```
run.py                     Entry point: starts the local server, opens a browser tab
app/
  server.py                stdlib http.server app: serves the UI + a tiny
                            read-only JSON API that proxies Stellarium
  stellarium_client.py      Talks to Stellarium's Remote Control plug-in
                            (GET-only, bounded response size, tolerant
                            parsing; combines /api/objects/info with a
                            separate /api/main/status call for FoV)
  coords.py                 Tolerant RA/Dec extraction: Stellarium's
                            documented numeric raJ2000/decJ2000 fields
                            first, then legacy decimal aliases,
                            sexagesimal text, or a J2000 direction vector;
                            RA wraparound + Dec clamping; manual-entry
                            parsing
  static/
    index.html, app.js, styles.css   The UI (dark/purple FOXAI style).
                            app.js talks to ESASky directly via its
                            documented postMessage JavaScript API and
                            URL parameters — this app's local server is
                            never in that path. app.js is DOM glue only;
                            it delegates to the pure modules below.
    lib/
      imagery_matching.js   Alias-group HiPS layer matching (pure, no DOM)
      esasky_queue.js       Iframe-readiness command queue (pure, no DOM)
      changehips.js          changeHips success/failure/timeout interpretation
      target_model.js        Maps /api/selection, /api/manual/validate JSON
                              into the frontend's target model
      solar_system.js        Solar System detection, bounded ESASky FoV,
                              honest notice copy (pure, no DOM)
      online_mode.js          Online-Archive-Mode-off shutdown state
docs/
  FUTURE_PLANETARY_IMAGERY.md  Design note — future planetary-image feature
tests/                      Python unit + integration tests (stdlib unittest)
  fixtures/fake_stellarium_server.py  In-process fake Stellarium server,
                            with genuinely distinct /api/objects/info and
                            /api/main/status responses
  fixtures/sample_responses/           Sanitized sample Stellarium JSON shapes
  frontend/                 Build-time Node tests (node:test) for
                            app/static/lib/*.js -- the actual matching,
                            queueing, and shutdown logic used at runtime
```

No third-party runtime dependencies. Everything is Python standard library
(`http.server`, `urllib`, `json`, `webbrowser`, `argparse`) plus plain
HTML/CSS/JS in the browser. Node is used only at build/CI time to validate
`app/static/lib/*.js`; it is never required to run the shipped application.

### Why no scraping / no automation

Per the project boundaries, this app never scrapes ESASky web pages and
never automates mouse/keyboard input. All ESASky interaction uses ESASky's
own **documented** embedding mechanisms:

* URL query parameters for the initial view
  (`hide_welcome`, `hide_banner_info`, `sci`, `cooframe`, `target`, `fov`) —
  see ESASky's "URL Parameters" documentation.
* The ESASky JavaScript API via `postMessage` for live updates
  (`goToRaDec`, `setFov`, `getAvailableHips`, `changeHips`) — see ESASky's
  "JavaScript API" documentation. These are only ever sent after the
  iframe has finished loading (see `app/static/lib/esasky_queue.js`).

### How "no coverage" reporting works

For telescope-specific buttons (Hubble, JWST NIRCam, JWST MIRI, WISE,
Spitzer, Herschel, X-Ray, Microwave), the app sends ESASky a
`getAvailableHips` request and searches the **response it gets back** for a
layer name matching that telescope/wavelength, using the alias groups in
`app/static/lib/imagery_matching.js` (e.g. "HST" or "Hubble" for the Hubble
button; JWST + NIRCam together for JWST NIRCam; any of XMM-Newton/eROSITA/
ROSAT/Chandra for X-Ray). Only if a match is found does it call `changeHips`
to load it, and even then it waits for ESASky's own confirmation
(`app/static/lib/changehips.js`) before reporting success. If ESASky's
response contains no match, the app says "No matching ESASky visualization
layer was found" — it does **not** claim the telescope never observed the
target, only that no matching all-sky layer was found; confirming a layer
*exists* also does not by itself prove the selected coordinates have image
coverage in it (a blank area in the viewer means no imagery there).

The **Default Optical** button requests ESASky's well-known default all-sky
optical survey ("DSS2 color") directly, since that layer is always present
— but it still waits for ESASky's confirmation rather than reporting
"Loaded" immediately, the same as every other button.

---

## Privacy: "Online Archive Mode"

Archive access is off by default and clearly labeled. When you turn on
**Online Archive Mode**:

* Your browser talks **directly** to `sky.esa.int`. This app's local Python
  server is not in that path and never sees or logs that traffic.
* This app itself deliberately sends only the target name (when
  necessary — not sent by default, since the app sends numeric RA/Dec
  instead), RA, Dec, and the requested field of view / search radius. No
  FOXAI workspace data, local file paths, Observation Deck records, or
  machine identity are ever included in what this app sends.
* That said, like any website your browser visits, ordinary
  browser/network metadata (e.g. your IP address, user agent string) may
  still accompany requests to ESASky regardless of what this app sends —
  this app has no ability to strip that, since the browser talks to ESASky
  directly.
* No API key is required or used in R0.1.1 through R0.1.4.
* Turning Online Archive Mode off actually tears the session down: pending
  ESASky timers/requests are cancelled, the iframe's `src` is cleared to
  `about:blank` and hidden, the readiness queue and active-button styling
  are reset, and no further ESASky commands are sent until you explicitly
  turn it back on.

Everything Stellarium-related stays fully local: this app's server only
ever calls `127.0.0.1:8090` (or whatever `--stellarium-url` you configure),
and only with `GET` requests against read-only info endpoints.

---

## Running it

### Windows (one click)

Double-click **`Start_FOXAI_Stellar_Cartography.bat`**. It finds Python 3,
starts the local server, and opens your browser.

### From a terminal (any OS)

```
python run.py
```

Options:

```
python run.py --port 8765                          # pick a specific port
python run.py --stellarium-url http://127.0.0.1:8090  # default shown
python run.py --no-browser                          # don't auto-open a tab
```

### Using it with Stellarium

1. In Stellarium, open the **Remote Control** plug-in settings and enable
   it on `localhost`, port `8090` (the default).
2. Select an object in Stellarium.
3. In the bridge app, press **"Use Stellarium Selection."**

If Stellarium isn't running, or the plug-in is off, the connection
indicator shows "Not connected" and you can still use the **Manual Target
Entry** form.

---

## Running the tests

### Python (unit + integration)

```
python -m unittest discover -s tests -v
```

No network access or real Stellarium installation is required — tests use
an in-process fake Stellarium server (`tests/fixtures/fake_stellarium_server.py`,
which serves genuinely distinct `/api/objects/info` and `/api/main/status`
responses) and sanitized sample response fixtures
(`tests/fixtures/sample_responses/`), including the exact documented
Stellarium getInfoMap payload from the R0.1.1 audit findings.

Coverage includes: Stellarium unavailable, no selected object, malformed
JSON, multiple coordinate field formats (documented numeric raJ2000/decJ2000,
legacy decimal aliases, sexagesimal, J2000 vector), negative declination, RA
wraparound near 0°/360°, field of view sourced from `/api/main/status`
independently of selection, the full set of About-This-Object fields,
bounded network payload size, path-traversal protection on the static file
server, and fully manual (Stellarium-less) operation.

### Frontend (build-time only)

```
node --test tests/frontend/*.test.js
```

Requires Node >= 18 (uses the built-in `node:test` runner — no npm install,
no dependencies). This exercises the *actual* pure logic modules used by
`app.js` at runtime (`app/static/lib/*.js`): imagery alias-group matching
(including "HST ACS matches Hubble", "XMM-Newton EPIC color matches
X-ray", "AllWISE color matches WISE", unrelated layers not matching, and
empty-list handling), the ESASky iframe-readiness command queue (commands
queued before readiness and flushed in order once), changeHips
success/failure/timeout interpretation, the `/api/selection` → frontend
target-model mapping (proving the documented numeric coordinates survive
unchanged), and the Online-Archive-Mode-off shutdown contract. It also runs
two browser-DOM integration tests (`app_dom_integration.test.js`,
`app_selection_failure.test.js`) that load the *real* `app/static/app.js`
into a Node `vm` context against a minimal, dependency-free fake DOM
(`dom_stub.js`, `app_loader.js`) and dispatch real click/change/`load`
events against it -- these are what prove the target-change-during-load fix
and the selection-failure fix actually took effect in `app.js` itself, not
only in the pure modules it calls. Node is **not** required to run the
shipped application — only to validate these modules at build/CI time.

---

## Boundaries (through R0.4.0)

This release intentionally does **not**:

* Download FITS science files.
* Query private/protected observations.
* Control any telescope.
* Modify Stellarium, the Observation Deck, or ESASky.
* Bundle Stellarium or ESASky.
* Track Starlink or general artificial satellites.
* Perform continuous background watchlist monitoring.
* Embed secrets, telemetry, or any API key.
* Search MAST with arbitrary UI scraping (server uses documented CAOM filter only).
* Provide planetary imagery for targets beyond Moon/Jupiter/Saturn in the R0.3 pilot.
* Ship personal watchlist JSON in the release archive (user-owned runtime data).

### Future (not in R0.4.0)

Additional planetary targets, MAST outreach imagery search, multi-provider aggregation —
see `docs/FUTURE_PLANETARY_IMAGERY.md` and `docs/PLANETARY_IMAGE_PILOT.md`.

---

## Known remaining live-validation steps

R0.4.0 completed live validation for archive lights, watchlist persistence,
Apophis tracker behavior, and preserved R0.3 planetary pilot validation.

* Confirming ESASky's *actual* postMessage response shape for `changeHips`
  (success/failure/`extras.message`) against what
  `app/static/lib/changehips.js` expects on future ESASky builds.
* Clicking each imagery button against live ESASky HiPS listings after
  major ESASky updates to confirm the alias groups in
  `app/static/lib/imagery_matching.js` still select sensible layers.
* Toggling Online Archive Mode off while an ESASky navigation is still
  in flight, in a real browser, after ESASky or browser updates.
* Pointing `--stellarium-url` at an unrelated local service and confirming
  `/api/status` keeps returning valid JSON.

## Known limitations

* **Planetary pilot scope:** Moon, Jupiter, and Saturn only. Other Solar
  System targets (e.g. Mars) show an honest unsupported message without fetch.
* **Archive vs live:** NASA Images API returns outreach/browse imagery; the
  panel states this is archival, not live or current appearance.
* **Solar System in ESASky:** HiPS survey layers are not designed for
  disk-resolved Moon/planet views; blank or generic background at Solar
  System coordinates is expected (R0.2.0 explains this in the notice panel).
  Use the Planetary Archive Image panel for Moon/Jupiter/Saturn.
* **Manual entry:** Solar System detection and planetary pilot resolution
  require Stellarium type fields; manually entered coordinates are not
  classified as Solar System or pilot targets.
* Coordinate parsing supports the Stellarium field-name variants documented
  in `app/coords.py`; a very unusual future Stellarium JSON shape may still
  fail gracefully (with a sanitized shape logged) rather than crash.
* The imagery-availability check depends on ESASky returning a
  `getAvailableHips` response within ~5 seconds; if ESASky is slow or the
  response format changes in a way this app doesn't recognize, it reports
  "could not confirm" rather than silently failing quiet. The same 5-second
  timeout applies to `changeHips` confirmation.

## Light Echoes (Upgrade #1)

Interactive scientific exhibit on light echoes: illustrative source–dust–observer geometry, curated real examples (V838 Mon, Cas A echoes, SN 1987A), optional Stellarium focus via existing Remote Control client, and user-controlled narration. Data: `app/data/light_echoes_registry.json`. Docs: `docs/LIGHT_ECHOES.md`.

## Cosmic Web (Upgrade #2)

Interactive exhibit on large-scale structure: illustrative structure-growth lab with layer toggles, survey/simulation media with OBSERVATION/RECONSTRUCTION/SIMULATION/ILLUSTRATION badges, and Stellarium sky anchors. Data: `app/data/cosmic_web_registry.json`. Docs: `docs/COSMIC_WEB.md`.

## Gravitational Waves (Upgrade #3)

Interactive Special: illustrative plus/cross polarization, interferometer diagram, inspiral chirp (browser sonification clearly labeled), GW150914/GW170817 event cards, detector network localization honesty, multi-messenger section, Stellarium sky anchor for NGC 4993. Data: `app/data/gravitational_waves_registry.json`. Docs: `docs/GRAVITATIONAL_WAVES.md`.

## Black Holes (Upgrade #4)

Interactive Special: Schwarzschild scale lab, approach regions, illustrative lensing, accretion appearance notes, tidal comparison, EHT reconstructions for M87*/Sgr A*, Cygnus X-1, detection methods linking to Gravitational Waves. Data: `app/data/black_holes_registry.json`. Docs: `docs/BLACK_HOLES.md`.

## Galactic Encounters (Upgrade #5)

Interactive Special: illustrative encounter stages, galaxy-scale tides, stars-vs-gas, major/minor mergers, Antennae/M51/Mice observations, and a model-dependent Milky Way–Andromeda future section. Data: `app/data/galactic_encounters_registry.json`. Docs: `docs/GALACTIC_ENCOUNTERS.md`.

## Cosmic Dawn (Upgrade #6)

Final Special in the six-upgrade series: illustrative timeline, redshift teaching aid, Planck CMB reconstruction, dark ages, cautious first-star language, reionization bubbles, JWST deep-field observations, conservative 21-cm frontier, and present-day Stellarium anchors only. Data: `app/data/cosmic_dawn_registry.json`. Docs: `docs/COSMIC_DAWN.md`.

