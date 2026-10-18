# Black Holes

Interactive Stellar Cartography Special on black-hole astrophysics.

## Classifications

- ILLUSTRATION — scale/approach/lensing educational diagrams
- THEORETICAL MODEL — Schwarzschild radius / tidal scaling with stated assumptions
- RECONSTRUCTION — EHT VLBI images (M87*, Sgr A*)
- OBSERVATION — Chandra/NASA Cygnus X-1 material
- SIMULATION — when simulation media are used

## Stellarium

- **M87*** → galaxy `M87` (exact)
- **Cygnus X-1** → companion `HD 226868` (exact)
- **Sgr A*** → host-sky `NGC 6522` near Galactic Center (not a fake Sgr A* object)

## API

- `GET /api/black-holes`
- `GET /api/black-holes/object/{id}`
- `GET /api/black-holes/scale?example_id=`
- `GET /api/black-holes/approach?progress=`
- `GET /api/black-holes/lensing?strength=`
- `GET /api/black-holes/tidal?example_id=`
- `GET /api/black-holes/narration?segment=`
- `POST /api/black-holes/focus` `{ "object_id": "m87" }`

Stellarium URL remains external (`--stellarium-url`). Narration autoplay is off.
