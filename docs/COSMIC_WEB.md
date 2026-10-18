# Cosmic Web

Interactive Stellar Cartography exhibit on the large-scale cosmic web.

## Distinctions

- **ILLUSTRATION** — structure-growth lab (synthetic educational positions)
- **OBSERVATION** — telescope/survey products
- **RECONSTRUCTION** — survey-based large-scale maps
- **SIMULATION** — cosmological simulation visualizations

## API

- `GET /api/cosmic-web`
- `GET /api/cosmic-web/object/{id}`
- `GET /api/cosmic-web/structure?step=&progress=&layer_galaxies=&layer_filaments=&layer_nodes=&layer_voids=`
- `GET /api/cosmic-web/narration?segment=`
- `POST /api/cosmic-web/focus` `{ "object_id": "..." }`

Stellarium base URL remains external (`run.py --stellarium-url`). Feature code does not hard-code LAN hosts.

## Tests

```bash
.venv/bin/python -m unittest tests.test_cosmic_web tests.test_light_echoes tests.test_exhibit
```
