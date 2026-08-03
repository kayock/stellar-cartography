# Planetary Image Pilot — R0.3

**Status:** Implemented in R0.3.0 (packaged).  
**Baseline:** FOXAI Stellar Cartography R0.2.0  
**Pilot targets:** Moon, Jupiter, Saturn only.

---

## Supported pilot targets

| Stellarium-reported name | Normalized id | Notes |
|------------------------|---------------|-------|
| Moon, Luna | `moon` | Requires Solar System classification from Stellarium fields |
| Jupiter | `jupiter` | Same |
| Saturn | `saturn` | Same |

Other Solar System bodies (Mars, Venus, comets, etc.) show an honest **unsupported** fallback — no network call. Stars and deep-sky objects hide the panel entirely.

Name matching uses Stellarium's reported `name` / `alt_name` only. Manual coordinate entry without Stellarium type fields is **not** classified as a pilot target.

---

## Official data source

**NASA Images and Video Library API**

| Item | Detail |
|------|--------|
| Documentation | https://images-api.nasa.gov/docs/ |
| Search endpoint | `https://images-api.nasa.gov/search` |
| Authentication | None required |
| Image CDN | `https://images-assets.nasa.gov/` (HTTPS only) |
| Attribution | `secondary_creator`, `nasa_id`, and `date_created` from API metadata; link to `https://images.nasa.gov/details/{nasa_id}` |

### Why not PDS Search API for this pilot?

PDS Search API (`https://pds.nasa.gov/api/search/1/`) remains the preferred long-term archive path (see `docs/FUTURE_PLANETARY_IMAGERY.md`). During R0.3 implementation it was **demonstrably insufficient** for a bounded browse-image pilot:

- `target_name eq "Saturn"` queries returned **zero hits**
- Keyword search returned unreliable/non-image results
- Product-level browse JPEG selection would require substantial mission-specific filtering beyond this pilot scope

NASA Images API provides documented, keyless, machine-readable search with stable HTTPS preview URLs suitable for outreach imagery with clear attribution.

---

## Online data flow and privacy boundary

```
User enables Online Archive Mode
       │
       ▼
Stellarium selection (local only) ──► target card + Solar System notice (R0.2)
       │
       ▼ (pilot target + Online Archive Mode on)
Browser ──GET /api/planetary-image?target=moon──► local Python server
       │                                              │
       │                                              ▼
       │                              NASA Images API (images-api.nasa.gov)
       │                              query: target name only (Moon/Jupiter/Saturn)
       │                                              │
       ◄──────── normalized JSON ◄──────────────────┘
       │
       ▼
Planetary Archive Image panel (separate from ESASky iframe)
```

**Privacy:**

- Planetary lookup runs **only** when Online Archive Mode is enabled **and** the target is a pilot Solar System body.
- The browser sends only the normalized pilot id (`moon`, `jupiter`, `saturn`) to the local server.
- The local server forwards only the corresponding search term to NASA (`Moon`, `Jupiter`, `Saturn`).
- No Stellarium metadata, coordinates, local paths, FOXAI workspace content, or machine identity are sent.
- ESASky traffic remains browser-direct (unchanged from R0.2).
- Ordinary browser/network metadata (IP, user agent) may still accompany HTTPS requests to NASA, as with any website visit.

---

## Archive image versus live appearance

The panel always displays this notice:

> This is an archived NASA outreach image, not a live view. It does not show the current date, phase, orientation, or appearance at the Stellarium coordinates. It was not produced by Stellarium or ESASky.

Metadata fields (mission, image date, credit, title) are shown when NASA provides them. Missing optional fields are omitted — never invented.

---

## Failure and fallback behavior

| Condition | Behavior |
|-----------|----------|
| Online Archive Mode off | Panel hidden; **zero** planetary network calls |
| Star / deep-sky target | Panel hidden |
| Unsupported Solar System target | Panel shown with honest unsupported message; no fetch |
| NASA timeout (10 s) | Error message in panel |
| HTTP error | Error message in panel |
| Malformed NASA response | Unavailable message |
| No permitted HTTPS image URL | Unavailable message |
| Rapid Moon → Jupiter → Saturn switching | Stale async responses ignored via generation token |

---

## Known limitations

- Pilot limited to three targets; no arbitrary planet search.
- NASA Images API returns outreach/catalog images, not necessarily the best scientific product for the target.
- First matching result with a permitted preview URL is used — not a curated “best current view”.
- Image date reflects NASA catalog metadata, not “now”.
- No ESA PSA/EPN-TAP integration in R0.3 (single official provider for this pilot).
- Manual targets without Stellarium Solar System type fields do not trigger the pilot.

---

## Adding future targets safely

1. Add an entry to `PILOT_TARGETS` in `app/planetary_image.py` with a vetted NASA search query.
2. Add name aliases to `PILOT_TARGET_ALIASES` in `app/static/lib/planetary_image.js`.
3. Add fixture JSON under `tests/fixtures/sample_responses/`.
4. Add unit/integration tests for lookup, URL validation, and UI panel behavior.
5. Update this document and `CHANGELOG.md`.
6. Verify NASA Images API returns stable HTTPS assets and attribution metadata for the new target before expanding the pilot list.

Do **not** expand beyond the mission-approved target set without a new release scope review.
