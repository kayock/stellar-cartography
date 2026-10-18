# Start Here — FOXAI Stellar Cartography R0.4.0

> R0.4.0 adds **MAST archive-availability lights** (Hubble/JWST), a **Tracked Objects**
> watchlist with notes and unified details, and a featured **Apophis 2029 tracker**
> on top of R0.3.0 Planetary Image Pilot and R0.2.0 Solar System Awareness.
> See README.md, `docs/ARCHIVE_AVAILABILITY.md`, `docs/TRACKED_OBJECTS.md`, and
> `docs/APOPHIS_TRACKER.md`.

## 1. Launch it

**Windows:** double-click `Start_FOXAI_Stellar_Cartography.bat`.

**Any OS with Python 3.9+:** run `python run.py` from this folder.

A browser tab opens automatically at `http://127.0.0.1:<port>/`.

## 2. Try it with Stellarium (optional)

1. Open Stellarium and enable the Remote Control plug-in (`localhost:8090`).
2. Select an object in Stellarium.
3. Click **Use Stellarium Selection** in the app.

**Moon, Jupiter, or Saturn:** with **Online Archive Mode** on, the **Planetary Archive Image**
panel fetches NASA outreach imagery (archival — not live).

**Solar System notice:** ESASky shows survey background, not disk-resolved photos.

## 3. Tracked Objects (local watchlist)

- Entries persist in `runtime_data/tracked_objects.json` beside this folder.
- Add the current target, favorite, write notes (**Save Note**), and **Open Details**.
- Load status shows path, entry count, and backup recovery when applicable.
- If load fails, the list shows unavailable — not “empty” — and writes are blocked until **Retry Load** succeeds.

## 4. Apophis tracker

- **Add Apophis Tracker** or **Open Apophis Tracker** (no duplicate).
- Shows JPL SBDB/HORIZONS data, April 2029 encounter, cached summary when offline.
- Opening Apophis **does not** move the sky viewer to RA 0°, Dec 0°.
- After a successful refresh with Horizons ephemeris, use **Use Ephemeris Position** explicitly.
- **Refresh Selected** honors a 60-second minimum between JPL requests.

## 5. Archive imagery

1. Turn on **Online Archive Mode**.
2. Click **Open in ESASky**.
3. Use imagery buttons; Hubble/JWST buttons show MAST availability lights (metadata counts only).

## Restoring personal watchlist data

The release ZIP does **not** include your watchlist. After extracting a clean copy:

1. Copy your backed-up files into `runtime_data\`:
   - `tracked_objects.json`
   - `tracked_objects.json.bak` (optional)
2. Restart the app.

## Troubleshooting

* **Watchlist could not be loaded:** ensure the local server is running; click **Retry Load**.
* **Apophis shows no sky position:** expected until Horizons ephemeris is retrieved; use **Refresh Selected** when online.
* **Planetary panel unsupported:** pilot is Moon, Jupiter, Saturn only.
* **No MAST lights:** Online Archive Mode must be on.

See `README.md` for architecture, privacy, and boundaries.
