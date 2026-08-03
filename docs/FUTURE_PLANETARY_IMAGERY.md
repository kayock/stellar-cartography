# Future dedicated planetary imagery — design note

**Status:** Partially implemented — see **`docs/PLANETARY_IMAGE_PILOT.md`** for the R0.3 pilot (Moon, Jupiter, Saturn via NASA Images API).  
**Original note (R0.2):** Design research for PDS / PSA paths.  
**Scope of R0.2:** Solar System Awareness (detection, honest ESASky guidance, bounded FoV).

This note records official-source research for a possible future feature that would show **close-up planetary photographs** for Solar System targets selected in Stellarium, complementing (not replacing) the existing ESASky HiPS archive viewer.

---

## Problem statement

ESASky's HiPS layers are **all-sky survey mosaics**. For Solar System coordinates they typically show the background survey field at the object's RA/Dec, not a disk-resolved planet image. R0.2 addresses this honestly in the UI; a future release could optionally fetch purpose-built planetary imagery when Online Archive Mode is enabled.

---

## Official sources surveyed

### NASA Planetary Data System (PDS)

| Item | Detail |
|------|--------|
| **Primary docs** | [PDS APIs portal](https://nasa-pds.github.io/pds-api/), [Search API user guide](https://nasa-pds.github.io/pds-api/guides/search.html) |
| **Search endpoint** | `https://pds.nasa.gov/api/search/1/` (REST, JSON/XML via `Accept` header) |
| **Imaging node** | [PDS Cartography and Imaging Sciences (IMG)](https://pds-imaging.jpl.nasa.gov/) — curated imaging datasets across missions |
| **Authentication** | Public read access; no API key required for search/metadata in documented examples |
| **License / attribution** | PDS data are generally public domain / NASA open data; each product label carries mission-specific citation requirements — must be read per product, not assumed globally |
| **Uncertainty** | PDS Search API documentation warns servers may not be fully populated for all examples; query results can be empty or 404 for some datasets. Products are **archival observation metadata**, not necessarily a single "best current photo" per planet |

**Relevance:** Strong for mission-specific FITS/JPEG products (e.g. Cassini, Juno, MRO). Weak as a one-click "show me Saturn now" unless heavily filtered by target, instrument, and observation type.

### ESA Planetary Science Archive (PSA)

| Item | Detail |
|------|--------|
| **Primary docs** | [PSA interfaces](https://cosmos.esa.int/web/psa/psa-interfaces), [PSA documentation](https://www.cosmos.esa.int/web/psa/documentation) |
| **Programmatic access** | EPN-TAP (Europlanet Table Access Protocol), TAP sync endpoint e.g. `https://psa.esa.int/psa-tap/tap/sync` |
| **Protocol standard** | [IVOA EPN-TAP 2.0 recommendation](https://www.ivoa.net/documents/EPNTAP/20220822/REC-EPNTAP-2.0.html) — ADQL queries over EPNCore metadata |
| **Other access** | Web UI, SFTP (`psaftp.esac.esa.int`); PDS4 products also exposed via NASA-hosted PSA PDS API (`https://pds.nasa.gov/api/search-psa/1/` per EPSC 2024 interoperability paper) |
| **Authentication** | Public data: anonymous access; proprietary mission data may require authenticated access during proprietary periods |
| **License / attribution** | ESA mission data; ESA/NASA PDS archiving guides apply — cite mission, instrument, and product ID from the label |
| **Uncertainty** | EPN-TAP returns metadata and file links, not rendered thumbnails by default. Query complexity is high; "latest global view of Jupiter" is a non-trivial ADQL/product-selection problem |

**Relevance:** Excellent for ESA mission observations (Mars Express, Rosetta, etc.). Same UX gap as PDS: archive-first, not outreach gallery-first.

### NASA APOD / outreach galleries (not recommended as primary API)

NASA APOD and mission outreach pages publish beautiful planetary images but **lack a stable, documented query API** suitable for automated coordinate-to-image mapping. Scraping would violate this project's boundaries. Any future feature should prefer **documented archive APIs** (PDS, PSA/EPN-TAP) or explicitly licensed static asset partnerships — not HTML scraping.

---

## Proposed future architecture (high level)

```
Stellarium selection
       │
       ▼
SolarSystem.isSolarSystemTarget()  ──already in R0.2──► notice panel + bounded ESASky FoV
       │
       ▼ (future, Online Archive Mode only)
PlanetaryImageryService (new module)
       │
       ├── Query PDS Search API / PSA EPN-TAP by target name + body match
       ├── Prefer pre-rendered browse derivatives when label provides URL
       ├── Fall back: "no suitable image found" (honest, like HiPS missing-layer UX)
       └── Display attribution line from product metadata (mission, date, license)
```

**Design principles (aligned with existing app boundaries):**

1. **Offline-first preserved** — planetary imagery fetch only when user enables Online Archive Mode, same privacy boundary as ESASky.
2. **No scraping** — only documented REST/TAP endpoints.
3. **No invented precision** — show observation date and mission; never imply "live" appearance unless metadata supports it.
4. **Separate from ESASky iframe** — likely a dedicated panel or secondary viewer; ESASky remains the all-sky archive browser.
5. **Optional API keys** — evaluate whether any tier requires registration; R0.2 adds none.

---

## Recommended next steps (post-R0.2 freeze)

1. Prototype PDS Search queries filtered by `target_name` (e.g. `Saturn`) and `product_type` image/browse derivatives.
2. Evaluate PSA EPN-TAP for overlapping ESA mission coverage vs PDS.
3. Define UX for attribution block (mission, observation time, product ID, link to full archive entry).
4. Add contract tests against recorded fixture responses (no live network in CI), mirroring existing fake Stellarium / ESASky test patterns.
5. Revisit MAST Hubble/JWST **Solar System** coverage separately from deep-sky MAST search — different product classes and search facets.

---

## Licensing summary (honest)

| Source | API availability | Typical license | Caveats |
|--------|------------------|-----------------|---------|
| NASA PDS | Documented REST Search API | Public domain / open NASA data | Per-product citation; not all products have browse JPEGs |
| ESA PSA / EPN-TAP | Documented TAP/ADQL | ESA mission terms + PDS standards | Proprietary periods; complex queries |
| ESASky HiPS | Documented JS API (R0.1.x) | ESA ESASky terms | All-sky surveys, poor Solar System disk imagery |

**Conclusion:** A credible future feature is feasible using **PDS Search API** and **PSA EPN-TAP**, but it requires substantial product-selection logic, clear attribution UI, and explicit "archive observation vs current appearance" wording — the same honesty standard applied in R0.2's Solar System notice panel.
