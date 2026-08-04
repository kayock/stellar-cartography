# Cosmic Signal Deck

**Status:** Slice 2 catalog expansion implemented in R0.5.0 development  
**Tagline:** Listen to the data. See how we know.

## Purpose

Present curated, officially sourced astronomical sonifications, instrument
signals, mission audio, and related recordings for the current target — without
implying that every item is literal sound traveling through space.

## Layout

Two-column outer layout is preserved:

- Left: target controls, NASA Public Media, watchlist
- Right (main content), top to bottom:
  1. Cosmic Signal Deck (full width)
  2. ESASky Archive Viewer
  3. Survey-layer controls / MAST discovery

No layout redesign in Slice 2. Player and page structure remain Slice 1.

## Registry

Single editable source:

`app/data/cosmic_signal_registry.json`

Python validates it (`app/cosmic_signal_registry.py`). The browser loads the same
file through the local application server:

- `GET /api/cosmic-signal-registry`
- `GET /api/cosmic-signal-match?name=&alt_name=&allow_featured=`

There is **no** hand-written JavaScript registry mirror.

Solar System canonical IDs and aliases are reused from
`app/data/solar_system_media_registry.json`. Deep-space aliases live only under
`deep_space_targets` in the Cosmic Signal registry.

## Enabled catalog (Slice 2)

Fifteen enabled entries (five from Slice 1 + ten verified additions).

### Slice 1 (unchanged)

| Entry | Classification | Canonical targets |
|-------|----------------|-------------------|
| Voyager 1 Interstellar Plasma Waves (PIA17045) | `data_audification` | featured / related Sun–Voyager path |
| Vela Pulsar | `data_sonification` | `vela_pulsar` |
| Crab Nebula | `data_sonification` | `crab_nebula` |
| Cassiopeia A | `data_sonification` | `cassiopeia_a` |
| Galactic Center / Sgr A* | `data_sonification` | `sagittarius_a` |

### Slice 2 additions

| Entry | Classification | Canonical ID / aliases (verified) |
|-------|----------------|-----------------------------------|
| MSH 15-52 / PSR B1509-58 | `data_sonification` | `msh_15_52` — MSH 15-52, PSR B1509-58, B1509-58, SNR G320.4-01.2 |
| M74 / Phantom Galaxy | `data_sonification` | `m74` — M74, Messier 74, NGC 628, Phantom Galaxy |
| Supernova 1987A | `data_sonification` | `sn_1987a` — SN 1987A, Supernova 1987A, SN87A |
| M87 | `data_sonification` | `m87` — M87, Messier 87, NGC 4486, Virgo A |
| Andromeda Galaxy / M31 | `data_sonification` | `m31` — M31, Messier 31, Andromeda Galaxy, NGC 224 |
| Jupiter | `data_sonification` | reuses Solar System `jupiter` |
| Saturn | `data_sonification` | reuses Solar System `saturn` |
| Uranus | `data_sonification` | reuses Solar System `uranus` |
| Southern Ring Nebula | `data_sonification` | `southern_ring_nebula` — Southern Ring Nebula, NGC 3132 |
| Stephan’s Quintet | `data_sonification` | `stephans_quintet` — Stephan's Quintet, HCG 92, Hickson Compact Group 92 |

One primary composite sonification is enabled per target. Alternate
wavelength-only tracks are recorded in `verification_notes` for a later
multi-track feature and are **not** enabled here.

### Intentionally omitted aliases

- Bare `andromeda` (constellation false-match risk)
- Informal “Hand of God” as a canonical or matching alias
- Broad substrings such as `ring`, `87`, or bare `m`

### Deferred / rejected for this slice

| Candidate issue | Reason |
|-----------------|--------|
| Saturn `sound/saturn.html` body copy | Official sound-page HTML incorrectly describes Uranus (CMS paste). Enabled entry uses Chandra photo album `photo/2026/sonify11/` for provenance; composite MP4 still verified on `www.chandra.si.edu`. |
| Per-wavelength alternate MP4s | Deferred (one primary composite per target). |
| Media proxy / scraping / YouTube | Out of architecture; failing candidates must be removed, not accommodated. |

## Official hosts

**Source pages:** `www.chandra.si.edu`, `chandra.si.edu`, `www.jpl.nasa.gov`  
**Initial / final media hosts (verified):** `www.chandra.si.edu`, `assets.science.nasa.gov`

## Redirect limitation

Slice 1 validates the **initial** HTTPS media URL (scheme, allow-listed host,
length, control characters). The browser may follow redirects afterward.
Full redirect-chain enforcement would require a later server media proxy.

Curation records `final_resolved_media_host` after manual verification.

## Playback rules

- Native `<audio controls preload="none">` / `<video controls preload="none">`
- Media `src` assigned only after explicit **Play signal**
- No autoplay, no media prefetch
- Poster allowed only when Online Archive Mode is on and an entry is shown
- Target change / Stop / Online Mode off clears `src`
- Online Mode off → zero Cosmic Signal registry/match/media/poster requests

## Independence

Failures affect only Cosmic Signal Deck state — not MAST, ESASky, NASA Public
Media, watchlist, or Apophis.

## Browser / playback notes

- Playback is browser-direct to official HTTPS media URLs (no application proxy).
- Native controls handle pause, seek (when the format supports it), and volume.
- Poster failure must not block Play.
- Initial-host allow-listing does not guarantee post-redirect host identity.
