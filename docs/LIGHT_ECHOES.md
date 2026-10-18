# Light Echoes

Interactive Stellar Cartography exhibit about astronomical light echoes.

## Features

- Illustrative source → dust → observer geometry with a time slider (labeled **ILLUSTRATIVE**, not a measured reconstruction)
- Real documented examples: V838 Monocerotis, Cassiopeia A light echoes, SN 1987A
- Optional Stellarium focus through the existing server-side Remote Control client
- Curated ESA/Hubble and Chandra public outreach imagery with provenance
- User-controlled narration/TTS (autoplay off)

## API

- `GET /api/light-echoes`
- `GET /api/light-echoes/object/{id}`
- `GET /api/light-echoes/geometry?step=&progress=`
- `GET /api/light-echoes/narration?segment=`
- `POST /api/light-echoes/focus` with `{ "object_id": "..." }`

## Configuration

Stellarium base URL remains external (`run.py --stellarium-url`). Feature code does not hard-code LAN hosts.

## Tests

```bash
.venv/bin/python -m unittest tests.test_light_echoes tests.test_exhibit
```
