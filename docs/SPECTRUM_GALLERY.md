# Spectrum Gallery

**Status:** Slice 5 multi-view expansion in R0.5.0 development  
**Tagline:** See the universe in another light.

## Purpose

Show curated official multiwavelength imagery for the current target — one
selected view at a time — without implying false-color equals human vision.

## Registry

Single editable source: `app/data/spectrum_gallery_registry.json`

Local APIs:

- `GET /api/spectrum-gallery-registry`
- `GET /api/spectrum-gallery-match?...`

## Multi-view (Slice 5)

When a target has **more than one exact-target** curated image, Spectrum Gallery
shows a compact **Available views** button row. Switching a view replaces the
image and metadata only; it does not change Stellarium selection, Cosmic Signal
Deck, ESASky, MAST, or NASA Public Media.

Planck all-sky fallback is never presented as a wavelength button for a matched
target.

Default view remains the previously accepted Slice 3 entry (first matching
registry order).

## Enabled catalog

**23** enabled entries total (10 Slice 3 + 13 Slice 5).

### Targets with multiple views

| Target | Views |
|--------|-------|
| Crab Nebula | Multiwavelength, X-ray, Visible, Infrared |
| Cassiopeia A | Multiwavelength, X-ray, Visible, Infrared |
| Galactic Center / Sgr A* | X-ray, Multiwavelength, Infrared |
| M87 | Multiwavelength, X-ray, Visible, Radio |
| Andromeda (M31) | X-ray, Visible |
| M74 | Multiwavelength, X-ray |

### Rejected / deferred in Slice 5

| Candidate | Reason |
|-----------|--------|
| Webb-native CDN Crab/Cas A stills | Not needed; Chandra release layers verified first |
| Additional Galactic Center X-ray mosaics | Duplicate wavelength of existing default |
| Vela / Saturn / Jupiter alternate views | Deferred; single-view remains adequate |
| Unstable Chandra paths returning 503 | Skipped after HEAD failures |

## Playback / network rules

- Only the currently selected view assigns `img.src`
- No preload of alternate wavelength images
- Online Mode off → zero Spectrum Gallery requests
- Target switch clears selected view and defaults to the new primary
