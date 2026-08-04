# Solar System NASA Public Media

**Status:** Expanded in R0.5.0 workstream (Solar System Media Expansion).  
**Origin:** R0.3 Planetary Image Pilot (Moon / Jupiter / Saturn).  
**Classification:** `public_media_asset` only — not calibrated science imagery and not proof of current appearance.

---

## Registry

Targets are resolved from the data-driven registry:

- `app/data/solar_system_media_registry.json` (source of truth)
- `app/solar_system_media_registry.py` (server loader + relevance)
- `app/static/lib/solar_system_media_registry.js` (browser/Node export; parity-tested)

Each entry includes: canonical id, display name, aliases, parent body (moons), target class, moving-object flag, and bounded NASA Images search terms, plus relevance / generic-guard context terms.

Supported at minimum: Sun, Mercury–Neptune, Pluto, Ceres, Eris, Haumea, Makemake, and major moons (Phobos, Deimos, Io, Europa, Ganymede, Callisto, Titan, Enceladus, Rhea, Iapetus, Mimas, Miranda, Ariel, Umbriel, Titania, Oberon, Triton, Charon).

Bodies not in the registry show an honest unsupported message without a NASA request. Stars and deep-sky objects hide the panel entirely.

Name matching uses Stellarium's reported `name` / `alt_name` only.

---

## Official data source

**NASA Images and Video Library API**

| Item | Detail |
|------|--------|
| Documentation | https://images-api.nasa.gov/docs/ |
| Search endpoint | `https://images-api.nasa.gov/search` |
| Authentication | None required |
| Image CDN | `https://images-assets.nasa.gov/` (HTTPS only) |
| Details pages | `https://images.nasa.gov/details/{nasa_id}` |

Returned items are labeled **NASA public archive media** and typed `public_media_asset`.

Relevance filtering rejects hits that do not sufficiently mention the target (and parent/context for moons; extra context for generic words such as sun / earth / moon).

Empty result copy:

> No relevant NASA public-media result was returned for this target.

This must not claim that no imagery or scientific data exists.

---

## Online data flow and privacy boundary

```
User enables Online Archive Mode
       │
       ▼
Stellarium selection (local only)
       │
       ▼ (registry Solar System target + Online Archive Mode on)
Browser ──GET /api/planetary-image?target=<id>──► local Python server
       │                                              │
       │                                              ▼
       │                              NASA Images API (images-api.nasa.gov)
       │                              bounded search term from registry only
       │                                              │
       ◄──────── normalized JSON ◄──────────────────┘
       │
       ▼
NASA Public Media panel (separate from ESASky Survey Layers and MAST Science Discovery)
```

**Privacy:**

- Lookup runs **only** when Online Archive Mode is enabled **and** the target resolves in the media registry.
- Online Archive Mode off produces zero NASA media requests.
- The browser sends only the normalized registry id to the local server.
- The local server forwards only the bounded registry search term to NASA.
- No Stellarium metadata, coordinates, local paths, FOXAI workspace content, or machine identity are sent.

---

## UI separation

Keep visibly separate:

1. **NASA Public Media** — this panel (`/api/planetary-image`)
2. **MAST Science Discovery** — discovery panel / badges
3. **ESASky Survey Layers** — HiPS layer controls

---

## Stale-response and target switching

- Duplicate-request suppression and generation-based stale guards are preserved.
- Switching targets clears the previous target's media immediately (loading / unsupported / empty replace the prior image).
- Unsupported or empty results clear old imagery.
- Late responses for a previous target must not overwrite a newer target's panel.
