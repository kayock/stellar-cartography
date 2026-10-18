# Public install (outside Kayock LAN)

This guide is for a clean checkout as an outside user would receive it.

## Prerequisites

- Python **3.9+**
- Modern browser (Chromium / Firefox / Edge)
- **Stellarium** with **Remote Control** plugin enabled (separate install)
- Optional: Node.js 18+ only if running frontend tests
- Optional: local TTS (Father Fox / Kayock Voice style HTTPS endpoint)

## 1. Get the source

```bash
git clone <YOUR_GITHUB_URL> stellar-cartography
cd stellar-cartography
```

## 2. Install Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Runtime uses the Python standard library only; `requirements.txt` pins the
supported Python version.

## 3. Configure Stellarium Remote Control

In Stellarium:

1. Enable the **Remote Control** plugin
2. Note the listen address/port (often `http://127.0.0.1:8090` on the Stellarium machine)
3. Allow access from the machine running Cartography (firewall / bind settings)

Example — both apps on one machine:

```bash
export STELLAR_CARTOGRAPHY_STELLARIUM_URL=http://127.0.0.1:8090
```

Example — Stellarium on another host on your LAN:

```bash
export STELLAR_CARTOGRAPHY_STELLARIUM_URL=http://STELLARIUM_HOST:8090
```

Copy `.env.example` to `.env` if you prefer file-based documentation of variables
(CLI flags still work; see `run.py --help`).

## 4. Start Cartography

If `start.sh` is not executable after clone:

```bash
chmod +x start.sh start-production.example.sh
```

```bash
./start.sh --host 127.0.0.1 --port 8775 --stellarium-url "$STELLAR_CARTOGRAPHY_STELLARIUM_URL"
```

Or use the example launcher:

```bash
cp start-production.example.sh start-production.sh
# edit STELLAR_CARTOGRAPHY_STELLARIUM_URL inside
./start-production.sh
```

Open `http://127.0.0.1:8775` (or your chosen host/port).

## 5. Verify Stellarium

Use the UI connection status / sky controls, or hit Cartography’s health/API
endpoints that report Stellarium reachability. If connection fails, confirm
Remote Control is listening and the URL matches.

## 6. Tests

```bash
python3 -m unittest discover -s tests -v
```

Some tests that require a live Stellarium instance may skip or soft-fail when
Remote Control is unreachable; core Specials and registry tests should run offline.

## Troubleshooting

| Symptom | Check |
|---------|--------|
| UI won’t start | Port in use; Python version |
| Stellarium “unavailable” | Remote Control URL, firewall, plugin enabled |
| TTS blocked | Only loopback + `STELLAR_CARTOGRAPHY_TTS_HOSTS` are allowed |
| Missing Specials | Ensure `app/specials/` and registries were included in the checkout |
