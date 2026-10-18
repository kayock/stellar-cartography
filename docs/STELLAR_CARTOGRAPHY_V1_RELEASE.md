# Stellar Cartography — v1.0.0 Release

**Date:** 2026-10-18  
**Repository:** https://github.com/kayock/stellar-cartography  
**Release URL:** https://github.com/kayock/stellar-cartography/releases/tag/v1.0.0  
**Tag:** `v1.0.0`  
**Target commit:** `a7ec083b55ae0b5a867048c749932bf8ae9cb013`

---

## Verdict

# V1.0.0 PUBLISHED / VERIFIED

---

## Markdown fix summary

`docs/PUBLIC_INSTALL.md` §6 Tests had nested/broken code fences (Python and Node
commands shared one fence; an extra closing fence broke rendering).

Fixed to:

- Python command in its own `bash` fence
- Optional Node frontend command in a separate `bash` fence
- Explanatory text outside fences
- Troubleshooting Specials path corrected (no nonexistent `app/specials/`)

Commit: `a7ec083` — *Fix public install test Markdown*  
Also notes `v1.0.0` in `CHANGELOG.md`.

---

## Validation before release

| Check | Result |
|-------|--------|
| Markdown fences (key docs) | Balanced |
| Relative links (README, START_HERE, PUBLIC_INSTALL, CONTRIBUTING, SECURITY, PROJECT_STATE) | OK |
| Screenshot gallery paths | All present under `docs/images/` |
| Python `unittest discover -s tests` | **513 PASS** |
| Node `node --test tests/frontend/*.test.js` | **254 PASS** |
| Privacy scan (tracked public files) | **Clean** (LAN ops docs remain gitignored only) |
| GitHub Actions on `a7ec083` | **success** — https://github.com/kayock/stellar-cartography/actions/runs/39100580531 |

---

## Release

| Field | Value |
|-------|--------|
| Title | Stellar Cartography v1.0.0 |
| Tag | `v1.0.0` |
| Target | `a7ec083` |
| Assets attached | None (GitHub source archives only) |
| Excluded | Stellarium binaries, models, private configs, logs, LAN launchers |

### Source archive spot-check

Tag archive contains LICENSE, Specials sources, screenshot gallery; does **not**
contain `start-production.sh` or `stellarium/`.

---

## Post-release verification

| Check | Result |
|-------|--------|
| Tag exists on origin | Yes |
| Release public | Yes |
| MIT license recognized | Yes |
| CI green on release tip | Yes |
| Production `:8775` | Healthy — Stellarium `connected: true` |

---

## Verdict (repeat)

**V1.0.0 PUBLISHED / VERIFIED**
