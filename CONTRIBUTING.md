# Contributing

## Scope

Stellar Cartography is a browser UI that drives **Stellarium Remote Control** and
presents curated sky stories / Specials with classified media and optional local TTS.

## Local development

1. Python **3.9+** (stdlib only for runtime — see `requirements.txt`)
2. Optional Node.js **18+** for frontend unit tests under `tests/frontend/`
3. A running Stellarium instance with the Remote Control plugin enabled

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt   # documents Python version; no packages required
cp .env.example .env              # optional
./start.sh --host 127.0.0.1 --port 8775 --stellarium-url http://127.0.0.1:8090
```

On Windows you can also double-click `Start_Stellar_Cartography.bat`
(legacy `Start_FOXAI_Stellar_Cartography.bat` still works as a wrapper).

## Tests

Python (full suite — current public baseline **513** tests):

```bash
python3 -m unittest discover -s tests -v
```

Optional frontend contract tests (Node ≥ 18, no npm packages):

```bash
node --test tests/frontend/*.test.js
```

## Guidelines

- Prefer configuration via CLI flags / environment variables over hard-coded hosts
- Keep Specials self-contained (`app/<special>.py`, `app/data/*_registry.json`,
  `app/static/lib/<special>.js`, matching tests)
- Preserve classification honesty (observation vs simulation vs reconstruction, etc.)
- Do not commit secrets, LAN addresses, AppImages, or `runtime_data` caches
