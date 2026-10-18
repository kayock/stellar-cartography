# Start Here — Stellar Cartography

Browser UI for **Stellarium**: select sky objects, open archive viewers, run
**Stories of the Sky**, and explore the six **Specials**.

## Requirements

- Python **3.9+**
- **Stellarium** with the **Remote Control** plugin (typically `http://127.0.0.1:8090`)
- A modern browser

Stellarium is installed separately — this repo does not bundle it.

## Quick launch

**Linux / macOS:**

```bash
./start.sh --host 127.0.0.1 --port 8775 --stellarium-url http://127.0.0.1:8090
```

**Windows:** double-click `Start_Stellar_Cartography.bat`  
(or the compatibility wrapper `Start_FOXAI_Stellar_Cartography.bat`).

Open the UI at `http://127.0.0.1:8775` (or the port you chose).

Full install, configuration, and troubleshooting: **[docs/PUBLIC_INSTALL.md](docs/PUBLIC_INSTALL.md)**.

## Six Specials

1. Light Echoes  
2. Cosmic Web  
3. Gravitational Waves  
4. Black Holes  
5. Galactic Encounters  
6. Cosmic Dawn  

See the matching docs under `docs/` (e.g. `docs/LIGHT_ECHOES.md`).

## Stories of the Sky

Constellation tours, exhibits, and related sky-culture material are part of the
same UI (alongside earlier archive / watchlist / Solar System features).

## Tests

```bash
python3 -m unittest discover -s tests -v
```

Optional Node frontend tests: `node --test tests/frontend/*.test.js` (Node ≥ 18).

## Voice (optional)

Narration hooks are built in; TTS is optional. See [docs/VOICE_AND_NARRATION.md](docs/VOICE_AND_NARRATION.md).

## More

- Product overview: [README.md](README.md)
- Media provenance: [docs/MEDIA_PROVENANCE.md](docs/MEDIA_PROVENANCE.md)
- Project status: [PROJECT_STATE.md](PROJECT_STATE.md)
- Historical R0.4.0 entry notes: [docs/history/START_HERE_R0.4.0.md](docs/history/START_HERE_R0.4.0.md)
