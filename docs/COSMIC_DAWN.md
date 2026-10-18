# Cosmic Dawn

Interactive Stellar Cartography Special on the early Universe.

## Classifications

- RECONSTRUCTION — Planck CMB maps
- OBSERVATION — Hubble HUDF / JWST deep fields
- SIMULATION — first-star / early-structure visuals
- ILLUSTRATION — timeline & reionization labs
- THEORETICAL MODEL — redshift teaching aid / 21-cm concepts

## Stellarium

Present-day optical sky only — never claimed to render Cosmic Dawn.

- CMB → unavailable (all-sky microwave)
- HUDF / first-stars context → Fornax Cluster host-sky
- JWST frontier → Abell 2744 (Pandora's Cluster)

## API

- `GET /api/cosmic-dawn`
- `GET /api/cosmic-dawn/object/{id}`
- `GET /api/cosmic-dawn/timeline?progress=`
- `GET /api/cosmic-dawn/redshift?z=`
- `GET /api/cosmic-dawn/reionization?progress=`
- `GET /api/cosmic-dawn/structure?progress=`
- `GET /api/cosmic-dawn/21cm`
- `GET /api/cosmic-dawn/narration?segment=`
- `POST /api/cosmic-dawn/focus` `{ "object_id": "jwst_pandora" }`

Narration autoplay is off. Stellarium URL remains `--stellarium-url`.
