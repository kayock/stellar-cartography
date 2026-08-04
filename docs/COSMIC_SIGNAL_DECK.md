# Cosmic Signal Deck

**Status:** Slice 1 implemented in R0.5.0 development  
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
