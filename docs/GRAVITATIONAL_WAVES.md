# Gravitational Waves Special

Interactive Stellar Cartography exhibit on gravitational-wave astronomy.

## What it teaches

- What gravitational waves are (spacetime distortions from accelerating masses)
- Compact-binary sources and the inspiral → merger → ringdown chirp
- How laser interferometers (LIGO/Virgo/KAGRA-class) measure tiny arm-length changes
- Why detector networks constrain sky localization (probability regions, not always a point)
- Multi-messenger follow-up, especially GW170817 / NGC 4993
- Honest classification of illustration / simulation / sonification / observation / real detector data

## Architecture

- `app/data/gravitational_waves_registry.json` — science, labs, events, detectors, narration, provenance hosts
- `app/data/gravitational_waves_exhibit.json` — curated 11-step exhibit walk
- `app/gravitational_waves.py` — registry loaders, wave/ifo/chirp/network payloads, Stellarium focus
- `app/static/lib/gravitational_waves.js` — canvases, controls, illustrative Web Audio chirp sonification
- Wired into `app/server.py`, `app/exhibit.py`, `index.html`, styles, exhibit.js (same pattern as Light Echoes / Cosmic Web)

## Classification honesty

| Tag | Meaning |
|-----|---------|
| illustration | Educational diagrams / exaggerated deformation lab |
| real_detector_data | Published LIGO/Virgo/GWOSC products |
| simulation | NR or instrument simulation media |
| sonification | Browser-generated or frequency-mapped audible tones — **not** space sound, **not** raw detector-band audio by default |
| observation | Electromagnetic telescope images |
| reconstruction | Derived sky maps / reconstructed properties |

Chirp audio in the UI is an **illustrative sonification** synthesized in the browser (frequency-shifted teaching tone). Labels state it is not original detector-band audio and not literal sound in vacuum.

## Stellarium

Stellarium is **sky context only** — it does not render gravitational waves.

- **GW150914**: `stellarium_match_mode=unavailable` (no unique host; localization was a broad region)
- **GW170817**: focuses **NGC 4993** (`coordinate_host`); verifies southern Declination when display name is empty

Deployment uses `--stellarium-url` (no hard-coded LAN IPs in feature modules).

## API (selected)

- `GET /api/gravitational-waves`
- `GET /api/gravitational-waves/wave?polarization=plus|cross&phase=&amplitude=`
- `GET /api/gravitational-waves/interferometer?phase=&progress=`
- `GET /api/gravitational-waves/chirp?stage=&progress=`
- `GET /api/gravitational-waves/network`
- `GET /api/gravitational-waves/event/{id}`
- `GET /api/gravitational-waves/narration?segment=`
- `POST /api/gravitational-waves/focus` `{ "event_id": "gw170817" }`
- Exhibit: `GET /api/exhibit/gravitational_waves`

Narration autoplay is **off**.

## Provenance hosts (allowlist)

Configured in registry `provenance_hosts_allowed` (ligo.org, gwosc.org, nasa.gov assets, eso.org, etc.). Media is linked, not bundled.

## Tests

`python3 -m unittest tests.test_gravitational_waves`

## Public release notes

- No hard-coded LAN addresses in GW feature code
- No credentials or personal paths
- Media linked with credit/license notes; do not redistribute without checking terms
