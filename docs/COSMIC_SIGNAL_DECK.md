# Cosmic Signal Deck

**Status:** Slice 4 solar/near-Earth signals added in R0.5.0 development  
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
  2. Spectrum Gallery
  3. ESASky Archive Viewer
  4. Survey-layer controls / MAST discovery

No layout redesign. Player and page structure remain Slice 1.

## Registry

Single editable source:

`app/data/cosmic_signal_registry.json`

Python validates it (`app/cosmic_signal_registry.py`). The browser loads the same
file through the local application server:

- `GET /api/cosmic-signal-registry`
- `GET /api/cosmic-signal-match?name=&alt_name=&catalogue_designations=&allow_featured=`

There is **no** hand-written JavaScript registry mirror.

Solar System canonical IDs and aliases are reused from
`app/data/solar_system_media_registry.json`. Deep-space aliases live only under
`deep_space_targets` in the Cosmic Signal registry.

## Multi-signal selection

When more than one exact-target signal matches, the deck shows a compact
**Available signals** button row. Changing the selection stops playback, clears
media `src`, updates explanation/credits, and requires Play again. No playlist
or autoplay.

## Enabled catalog

**21** enabled entries total.

### Slice 4 — Solar & near-Earth

| Entry | Target | Classification | Mission / instrument | Media host |
|-------|--------|----------------|----------------------|------------|
| Earth Chorus Waves | `earth` | `instrument_signal` | Van Allen Probes EMFISIS | `svs.gsfc.nasa.gov` |
| Earth Lightning Whistlers | `earth` | `instrument_signal` | Van Allen Probe A EMFISIS | `space.physics.uiowa.edu` |
| Venus Ionosphere Radio Signal | `venus` | `data_sonification` | Parker Solar Probe FIELDS | `svs.gsfc.nasa.gov` |
| Jupiter Bow Shock | `jupiter` | `instrument_signal` | Juno Waves | `space.physics.uiowa.edu` |
| Jupiter Auroral Radio Emission | `jupiter` | `instrument_signal` | Juno Waves | `space.physics.uiowa.edu` |
| Europa Flyby Plasma Waves | `europa` | `instrument_signal` | Juno Waves | `space.physics.uiowa.edu` |

### Rejected / deferred in Slice 4

| Candidate | Reason |
|-----------|--------|
| Juno Morse-code HI (PIA17744) | Official photojournal/NASA Science pages SSL or 403; Images API empty; no verified direct playable asset |
| Magnetosphere drum (THEMIS/HARP) | No stable official browser-direct media asset found |
| SOHO Sounds of the Sun | Official SOHO/Stanford sound pages 404 or SSL handshake failure |
| Parker solar-wind plasma scream | News/photojournal blocked or asset path unverified |
| Ganymede Juno Waves (PIA25030) | NASA asset CDN 403/404; no Iowa Waves clip located |
| Io / Jupiter radio (Io-specific) | No verified Io-exact direct asset; Jupiter auroral radio enabled instead |

### Earlier slices

Slice 1–2 deep-space and Solar System Chandra sonifications remain enabled,
including Voyager as `data_audification` featured fallback.

## Official hosts (Slice 4 additions)

**Source / media:** `svs.gsfc.nasa.gov`, `space.physics.uiowa.edu` (Van Allen Probes EMFISIS and Juno Waves instrument-team archives)

## Playback rules

- Native `<audio controls preload="none">` / `<video controls preload="none">`
- Media `src` assigned only after explicit **Play signal**
- No autoplay, no media prefetch
- Target change / Stop / Online Mode off / signal switch clears `src`
- Online Mode off → zero Cosmic Signal registry/match/media/poster requests

## Independence

Failures affect only Cosmic Signal Deck state — not Spectrum Gallery, MAST,
ESASky, NASA Public Media, watchlist, or Apophis.
