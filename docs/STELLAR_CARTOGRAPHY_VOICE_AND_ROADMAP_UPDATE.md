# Stellar Cartography — Voice Documentation + Future Exhibits Roadmap

**Date:** 2026-10-18  
**Repository:** https://github.com/kayock/stellar-cartography  
**Branch:** `main`  
**Scope:** Documentation only — no application behavior changes.

---

## Verdict

**PASS**

---

## Voice documentation added

New: [`docs/VOICE_AND_NARRATION.md`](VOICE_AND_NARRATION.md)

Covers:

- Narration hooks already present; TTS optional; core app works without speech
- User-triggered playback; autoplay off
- Father Fox / Kayock Voice as example local endpoints, not bundled deps
- `STELLAR_CARTOGRAPHY_TTS_HOSTS` allowlisting
- Practical integration shape from `app/tts_client.py`, `tts_providers.json`,
  `narration_tts.js`, and `/api/tts/*` / `/api/narration` routes
- No private LAN addresses

---

## README / PUBLIC_INSTALL / START_HERE

- README: stronger optional-voice feature wording + short Voice section + links
- `docs/PUBLIC_INSTALL.md`: optional voice section with generic host example
- `START_HERE.md`: pointer to voice doc

---

## Future exhibits roadmap

New: [`docs/FUTURE_EXHIBITS.md`](FUTURE_EXHIBITS.md)

- **Forgotten Contributions** — purpose, research topic list, sourcing standards
  (planning only; not implemented)
- Lunar Laboratory / first-person lunar exploration — planned concepts only
- Link to existing `docs/FUTURE_PLANETARY_IMAGERY.md`

No Forgotten Contributions implementation started.

---

## Privacy check

Tracked doc changes scanned for private LAN / home / library paths — **clean**.

---

## Tests / CI / commit

| Check | Result |
|-------|--------|
| Python 513 | **513 PASS** |
| Node 254 | **254 PASS** |
| CI | **success** — https://github.com/kayock/stellar-cartography/actions/runs/39101941270 |
| Commit | `e476314` (`e476314eb45128c9eb65ab0786dd691c9dc65e6a`) |
