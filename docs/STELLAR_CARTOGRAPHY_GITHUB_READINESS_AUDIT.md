# Stellar Cartography — GitHub Release-Readiness Audit

**Date:** 2026-10-18  
**Auditor environment:** Cursor Station (STATION_HOST) → production tree on Ubuntu Portable  
**Production root:** `/path/to/stellar-cartography`  
**Production UI:** `:8775` (verified healthy after changes)  
**Publish status:** **Not published.** No push. No GitHub auth changes.

---

## Verdict

# NEEDS FIXES

The **intended public tree** (export snapshot) is close to ready: clean-clone install works, **513 PASS**, no LAN in export, config is parameterized, README/docs/.gitignore improved, media policy documented.

Blocking items before calling **READY FOR GITHUB**:

1. **Public source is not yet in the real Git index** — Six Specials, Stories, TTS, `start.sh`, `.env.example`, and related docs remain **untracked** on the production branch. An outside `git clone` of the current repo **would not** receive the finished suite. A validated **export snapshot** proves what *should* be committed; that commit has **not** been made (and must not be pushed yet without owner approval).
2. **No `LICENSE` file** — `LICENSE_RECOMMENDATION.md` recommends MIT; owner must explicitly choose and add a license before public release.
3. **Pre-publish commit hygiene** — Local-only assets (`stellarium/` ~1.7G, `start-production.sh` with LAN defaults, Windows migration / upgrade reports) must stay gitignored and never staged.

Once (1) and (2) are done and a final re-scan of the staged tree is clean, re-run clean-clone from that commit → then **READY FOR GITHUB**.

---

## Phase 1 — Repository inventory

| Item | Finding |
|------|---------|
| Repository root | `/path/to/stellar-cartography` |
| Branch | `feature/r0.5.0-archive-solar-expansion` |
| Remotes | **None** |
| Commits | 22 (R0.4 / Cosmic Signal / Spectrum Gallery lineage) |
| Tracked | Core R0.4 app, older docs, receipts |
| Untracked (required for public product) | Specials modules/registries/JS/tests, Stories/exhibit/experience, TTS, Chandra registry, `start.sh`, public docs, scripts, research notes, etc. (~94 `??` paths at audit time) |
| Untracked / local-only | `stellarium/` (~1.7G AppImage tree), `backups/`, `runtime_data/` caches/logs, `.venv/`, `start-production.sh` (LAN), Windows migration + upgrade reports |
| Generated | `runtime_data/official_media_cache/`, `narration_cache/`, `__pycache__` |
| Media in `app/` | No bundled jpg/png/mp4 found — remote URL registries |
| Tests | Python `unittest` + optional Node frontend tests |
| Startup | `start.sh`, `start-production.example.sh`, local `start-production.sh` (gitignored), Windows `.bat` |

**Must not ship publicly:** `stellarium/`, AppImages, `.venv`, caches, logs, backups, LAN launcher, ops/upgrade reports with machine details, `.env` with real hosts.

---

## Phase 2 — Secrets / personal data

### A. Current-tree exposure

| Class | Result |
|-------|--------|
| API keys / cloud tokens / passwords | **None found** |
| SSH / private keys | **None found** |
| Email addresses | **None found** in public-facing paths |
| Home paths `/~` | Absent from `app/` / tests / public templates after fixes |
| LAN IPs | **Only** in local `start-production.sh` (gitignored) — intentional Kayock deployment |
| Product names (Father Fox / Kayock Voice) | Present as optional TTS provider labels — intentional, not credentials |
| Competition / session artifacts | Not found |

### B. Historical exposure (Git)

- Secret-pattern scan across commits: **no real credentials** (hits were words like “token”, “password” in URL-parsing / docs denying secrets).
- LAN IP string search in history: **no historical commits** embedding `PORTABLE_HOST` / `STELLARIUM_HOST` (those lived in untracked ops files / launcher).
- Largest tracked files are source/docs (~100KB), not binaries.

**Note:** Deleting secrets from the working tree is not enough if they were ever committed. Here, history looks clean of credentials and LAN; still re-scan after the first public-oriented commit.

---

## Phase 3 — Machine-specific assumptions

| Reference | Classification | Action taken |
|-----------|----------------|--------------|
| `STELLARIUM_HOST:8090` in `start-production.sh` | Local-only operational | Kept; file **gitignored**; public template uses `127.0.0.1:8090` |
| `PORTABLE_HOST` TTS allowlist in `tts_client.py` | Was release blocker | **Parameterized** via `STELLAR_CARTOGRAPHY_TTS_HOSTS` (default loopback only); production launcher exports host for local TTS |
| `/path/to/kayock-library`, Ubuntu Portable comments | Local docs / old comments | Ops docs gitignored; `start.sh` comments sanitized |
| `STATION_HOST` | Audit host only | Not in product tree |
| Stellarium default `http://127.0.0.1:8090` | Acceptable default | Env + CLI: `STELLAR_CARTOGRAPHY_STELLARIUM_URL` / `--stellarium-url` |

Production still uses LAN Stellarium URL via local launcher — **:8775 remains connected** (`/api/status` → `{"connected": true}`).

---

## Phase 4 — Configuration model

Added / improved:

- `.env.example` — host, port, Stellarium URL, TTS hosts (no real LAN values)
- `run.py` — reads `STELLAR_CARTOGRAPHY_HOST`, `STELLAR_CARTOGRAPHY_PORT`, `STELLAR_CARTOGRAPHY_STELLARIUM_URL` (and `PORT` / `STELLARIUM_URL` aliases)
- `start-production.example.sh` — public launcher template
- TTS allowlist via `STELLAR_CARTOGRAPHY_TTS_HOSTS`

---

## Phase 5 — Dependency audit

| Layer | Requirement |
|-------|-------------|
| Runtime | **Python ≥ 3.9**, **stdlib only** (`requirements.txt` documents floor; no pip packages) |
| Optional tests | `unittest` (stdlib); Node ≥ 18 for `tests/frontend/*.test.js` (no npm packages required for `node --test`) |
| External | **Stellarium** + **Remote Control** plugin (not bundled) |
| Optional | Local HTTPS TTS on ports 8765/8766 (Father Fox / Kayock Voice style) |
| Browser | Modern Chromium / Firefox / Edge |

No undocumented pip/system packages required beyond Python 3.

---

## Phase 6 — Media / licensing / provenance

- Specials use **remote agency URLs** + credit / classification fields in registries.
- No large agency binaries found under `app/`.
- Documented policy: `docs/MEDIA_PROVENANCE.md`.
- Redistribution of NASA/ESA/STScI/ESO/Chandra/LIGO/EHT/survey media: prefer link + attribution; do not assume “viewable” ⇒ “rehost in git”.
- `runtime_data/*` caches remain local / gitignored.

---

## Phase 7 — Software license

- **No `LICENSE` in tree.**
- Added `LICENSE_RECOMMENDATION.md` (suggests **MIT**; owner must choose).
- Stellarium documented as external dependency — **do not bundle**.

---

## Phase 8 — `.gitignore` work

Expanded to exclude: venvs, caches, `stellarium/`, AppImages, backups, logs, `.env`, local `start-production.sh`, LAN ops/upgrade docs, narration/media caches.

Does **not** ignore Specials source/registries required to run the app.

---

## Phase 9–10 — README / install experience

- Public **Quick start** prepended to `README.md` (features, Specials, config table, architecture).
- `docs/PUBLIC_INSTALL.md` — clone → venv → configure Stellarium → start → test → troubleshooting.
- `CONTRIBUTING.md`, `SECURITY.md`.
- Example launcher without LAN defaults.

Historical R0.4 README body retained below the new front matter.

---

## Phase 11 — Clean-clone procedure and result

**Procedure used** (simulates outside GitHub user receiving the *intended* public tree):

1. Rsync production → `/tmp/stellar-cartography-public-src` excluding local-only paths (see `build_public_export.sh`).
2. `git init` + commit snapshot (local only; not a publish).
3. `git clone` → `/tmp/stellar-cartography-clean-clone`.
4. Follow public docs: `python3 -m venv .venv`, `pip install -r requirements.txt`, `./start.sh …`.
5. Run `python3 -m unittest discover -s tests -q`.

| Check | Result |
|-------|--------|
| LAN/path scan in clone | **None** |
| Dependency install | OK |
| Ephemeral UI start (`:18776`) | HTTP 200 |
| Stellarium without RC | `connected: false` (expected) |
| Test suite | **Ran 513 tests — OK** |
| Export size | ~4.1M source (no AppImage) |

**Why not `git clone` of the real repo?** Current branch lacks remotes and omits untracked Specials — that clone would be an incomplete product. Fix = commit the public set before publish.

---

## Phase 12 — Tests

| Suite | Result |
|-------|--------|
| A. Production working tree | **Ran 513 tests — OK** |
| B. Clean clone | **Ran 513 tests — OK** |

Baseline met (≥ 513 PASS). No tests weakened. Live Stellarium not required for unit suite (fake fixtures). Environment-specific soft behavior: live `/api/status` connected only when RC is reachable.

---

## Phase 13 — Public-user review (post-fix)

| Question | Answer |
|----------|--------|
| What is this in 30s? | Yes — README Quick start |
| Install from README? | Yes — plus `docs/PUBLIC_INSTALL.md` |
| Stellarium required? | Yes — documented |
| Enable Remote Control? | Yes — install doc |
| Config examples? | `.env.example`, example launcher |
| Six Specials clear? | Yes — listed in README + per-Special docs |
| Media credits? | Registries + `MEDIA_PROVENANCE.md` |
| Troubleshooting? | Public install doc |
| Assumes Eric’s machines? | **Not in public export**; local launcher still does (gitignored) |
| Embarrassing/private exposure? | Ops/upgrade LAN docs excluded from export/gitignore |

---

## Phase 14 — GitHub structure (prepared, not published)

| Artifact | Status |
|----------|--------|
| README.md | Improved |
| LICENSE | **Missing — owner action** |
| LICENSE_RECOMMENDATION.md | Added |
| .gitignore | Improved |
| docs/PUBLIC_INSTALL.md, MEDIA_PROVENANCE.md | Added |
| CONTRIBUTING.md, SECURITY.md | Added |
| Issue templates / CHANGELOG churn | Skipped (existing CHANGELOG left as-is) |

---

## Phase 15 — Release asset plan

| Asset | GitHub? |
|-------|---------|
| Source, registries, Specials, tests, docs | **Yes** (after commit) |
| Small project-owned UI assets | Yes |
| Large agency media | Prefer remote URLs / release assets only if license-clear |
| Stellarium installer / AppImage | **No** |
| Models / TTS weights | **No** |
| Local config / logs / backups / caches | **No** |

---

## Phase 16 — Final re-scan

| Check | Status |
|-------|--------|
| Secrets in public export | Clean |
| LAN in public export | Clean |
| Production `:8775` | **Healthy** — UI 200, `connected: true` |
| Production tests | 513 OK |
| Clean-clone tests | 513 OK |
| Untracked required files in real git | **Still present — blocker** |
| LICENSE | **Missing — blocker** |
| Unrelated projects touched | **None** |
| Stellarium / `:12434` disturbed | **No** (status check only) |

---

## Remaining blockers (exact)

1. **Commit (do not push yet)** the public file set into the real repository (or create a release branch) so a normal clone matches the validated export. Keep gitignored LAN/ops/stellarium out of the commit.
2. **Add `LICENSE`** after explicit owner choice (MIT recommended).
3. Optional polish before public: trim “FOXAI” branding consistency in titles if desired; confirm research notes under `research/` are intended for public cultural documentation.

---

## Exact files changed / added this audit

**Modified (production tree):**

- `app/tts_client.py` — env-based TTS allowlist
- `app/data/tts_providers.json` — tls_note without hard-coded LAN
- `run.py` — env defaults for host/port/Stellarium URL
- `start-production.sh` — local-only; TTS env + configurable Stellarium URL (still LAN defaults; **gitignored**)
- `start.sh` — portable comments
- `.gitignore` — public hygiene
- `README.md` — public Quick start prepended

**Added:**

- `.env.example`
- `start-production.example.sh`
- `LICENSE_RECOMMENDATION.md`
- `CONTRIBUTING.md`
- `SECURITY.md`
- `docs/PUBLIC_INSTALL.md`
- `docs/MEDIA_PROVENANCE.md`
- `docs/STELLAR_CARTOGRAPHY_GITHUB_READINESS_AUDIT.md` (this file)

**Validation artifacts (ephemeral on Portable):**

- `/tmp/stellar-cartography-public-src`
- `/tmp/stellar-cartography-clean-clone`
- `/tmp/sc-gh-ready/build_public_export.sh`

---

## Success-condition scorecard

| # | Condition | Met? |
|---|-----------|------|
| 1 | No secrets exposed | **Yes** (tree + history) |
| 2 | No required runtime files only outside repo | **Partial** — present on disk / in export; **not** in git index |
| 3 | LAN configurable | **Yes** |
| 4 | Dependencies documented | **Yes** |
| 5 | README for outside user | **Yes** |
| 6 | Stellarium setup documented | **Yes** |
| 7 | Media/provenance reviewed | **Yes** |
| 8 | `.gitignore` appropriate | **Yes** |
| 9 | Clean-clone install works | **Yes** (export snapshot) |
| 10 | Clean-clone tests pass | **Yes** (513) |
| 11 | Production ≥ 513 PASS | **Yes** (513) |
| 12 | Production `:8775` healthy | **Yes** |
| 13 | No unrelated projects changed | **Yes** |

---

## Verdict (repeat)

**NEEDS FIXES** — public *content* validated; public *Git publish* blocked until Specials/docs are committed to the real repo and a `LICENSE` is chosen. Do not push until those are done and re-scanned.
