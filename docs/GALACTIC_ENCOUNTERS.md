# Galactic Encounters

Interactive Stellar Cartography Special on galaxy interactions and mergers.

## Classifications

- ILLUSTRATION — encounter / tidal / stars-gas labs
- OBSERVATION — Hubble Antennae, M51, Mice
- FUTURE PREDICTION — Milky Way–Andromeda forward models (uncertain)
- SIMULATION — when simulation stills are used

## Stellarium

- Antennae → `NGC 4038`
- Whirlpool → `M51`
- Mice → `NGC 4676`
- MW–M31 future → `Andromeda Galaxy` (present-day sky context)

## API

- `GET /api/galactic-encounters`
- `GET /api/galactic-encounters/object/{id}`
- `GET /api/galactic-encounters/encounter?progress=&mass_ratio=&orientation=`
- `GET /api/galactic-encounters/tidal?strength=`
- `GET /api/galactic-encounters/stars-gas?mode=`
- `GET /api/galactic-encounters/merger?mode=`
- `GET /api/galactic-encounters/future`
- `GET /api/galactic-encounters/narration?segment=`
- `POST /api/galactic-encounters/focus` `{ "object_id": "antennae" }`

Stellarium URL remains external (`--stellarium-url`). Narration autoplay is off.
