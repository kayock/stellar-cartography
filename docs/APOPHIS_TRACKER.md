# Apophis 2029 Featured Tracker — R0.4

## Official designation

- IAU number: **99942**
- Name: **Apophis**
- Primary provisional designation: **2004 MN4**

The featured tracker uses the same watchlist foundation (`featured_kind: "apophis"`) — not a separate hard-coded page.

## Official data sources

| Data | API | Documentation |
|------|-----|----------------|
| Object ID, Earth close approaches | JPL SBDB API | https://ssd-api.jpl.nasa.gov/doc/sbdb.html |
| Observer ephemeris (optional) | JPL Horizons API | https://ssd-api.jpl.nasa.gov/doc/horizons.html |

No HTML scraping. No Sentry risk scraping.

## Encounter date and countdown

- Documented April **2029** close encounter (SBDB `ca_data` when supplied).
- Countdown is calculated **locally** from the documented encounter date (`2029-04-13T00:00:00Z` baseline).
- Countdown is informational only — **not** a risk assessment.

## Risk status

SBDB does not provide a simple machine-readable “current risk conclusion” field suitable for automatic display. When unavailable, the UI shows:

> Current official risk status was not retrieved automatically. Check the official source.

Links to official JPL CNEOS resources are provided. The app never hard-codes a permanent safety conclusion.

## Observer location and privacy

| Case | Behavior |
|------|----------|
| Observer lat/lon supplied | Rounded to 2 decimals; altitude rounded; sent to Horizons as `SITE_COORD` |
| Not supplied | Geocentric fallback `500@399` (Earth geocenter) |
| Hard-coded user location | **Never** — no silent Pueblo or private coordinates |

The panel states what observer context was used and when data was retrieved.

## Refresh rules

- Manual refresh only (no background polling)
- Minimum interval: **60 seconds** between refreshes
- In-flight duplicate suppression
- Stale async responses ignored after generation bump

## Removing the tracker

Use **Remove** on the watchlist entry. Apophis is never forced into the watchlist automatically.

## Exclusions

Starlink and general satellite tracking are out of scope for R0.4.
