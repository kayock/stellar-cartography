# Archive Availability Lights — R0.4

**Status:** Implemented in R0.4.0 (development; not packaged).

## Scope

Archive-availability lights apply **only** to these imagery choices:

- Hubble (`hst`)
- JWST NIRCam (`jwst_nircam`)
- JWST MIRI (`jwst_miri`)

Other imagery buttons are unchanged.

## Official source

| Item | Detail |
|------|--------|
| Service | MAST Portal API v0 |
| Documentation | https://mast.stsci.edu/api/v0/ |
| Endpoint | `POST https://mast.stsci.edu/api/v0/invoke` |
| Query service | `Mast.Caom.Filtered.Position` |
| Authentication | None required |

## Data flow

```
Online Archive Mode ON + target loaded
       │
       ▼
Browser ──GET /api/archive-availability?ra=&dec=&mission=──► local Python server
       │                                                         │
       │                                                         ▼
       │                                            MAST API (mast.stsci.edu)
       │                                                         │
       ◄──────── normalized JSON (count + optional observation list) ◄──
       │
       ▼
Accessible badge on Hubble / JWST NIRCam / JWST MIRI buttons
```

When **Online Archive Mode is off**, the client makes **zero** archive requests.

## Search radius and count semantics

| Setting | Value |
|---------|-------|
| Search radius | **0.01°** (~36 arcsec), documented constant `ARCHIVE_SEARCH_RADIUS_DEG` |
| Count meaning | CAOM **observation records** within the cone matching mission/instrument filters |
| Not implied | Unique photographs, coordinate-specific preview availability, ESASky layer content |

## Accessible states

Each state includes text via badge `aria-label`, `title`, and visible label (not color alone):

| State | Example text |
|-------|----------------|
| Not checked | `Hubble: not checked` |
| Checking | `Hubble: checking archive` |
| Confirmed | `Hubble: 14 archive observations` |
| No coverage | `JWST MIRI: no confirmed observations near this position` |
| Unavailable | `Archive check unavailable` |
| Selected ESASky layer | `Hubble: currently selected ESASky layer` |

## Caching and rate limits

| Rule | Value |
|------|-------|
| Client cache TTL | 5 minutes per `(ra, dec, mission)` |
| Minimum repeat interval | 30 seconds |
| In-flight duplicate suppression | Same cache key while request pending |
| Stale responses | Ignored after target change (generation token) |
| Max observation list | 25 entries |

## Limitations

- HiPS layer presence in ESASky does **not** prove archive observations at the selected coordinates.
- Observation count ≠ unique images.
- Confirmed observation ≠ public preview exists.
- MAST metadata is rendered as plain text only; no remote HTML insertion.

## Future extension

Additional missions/instruments could add new `MISSION_CONFIGS` entries and imagery-button mappings. Starlink and general satellite tracking are **explicitly excluded** from R0.4.
