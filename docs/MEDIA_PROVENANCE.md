# Media provenance and redistribution

Stellar Cartography prefers **remote references** (official agency URLs) over
bundling large media binaries in git.

## Policy for public GitHub

| Category | In git? | Notes |
|----------|---------|--------|
| Source code, registries, Specials JSON | Yes | Attribution fields in registries |
| Small UI icons / SVG authored for the project | Yes if project-owned | Credit in README |
| NASA / ESA / STScI / ESO / Chandra / LIGO / EHT / survey images | Prefer **URL only** | Follow each agency’s media guidelines |
| Stellarium AppImage / Windows installer | **No** | External dependency |
| TTS / LLM model weights | **No** | Optional external services |
| `runtime_data/*` caches | **No** | Generated at runtime |

## Agency notes (non-legal summary)

Always verify current agency terms before redistribution:

- **NASA** media is often freely usable with credit; check Image Policy / NASA Media Usage Guidelines.
- **ESA / Hubble / JWST / STScI** often allow educational use with credit; check per-release notices.
- **ESO** has explicit credit and non-commercial caveats on some products.
- **Chandra (CXC)** / **LIGO** / **EHT** / surveys: follow the credit lines shipped with each product page.

Cartography Specials store `credit`, `source_url`, and `classification` fields so
the UI can show provenance without redistributing the binary.

## Local caches

`runtime_data/official_media_cache/` and narration caches are machine-local and
must stay out of the public repository (see `.gitignore`).

## Project license vs third-party media

The **MIT License** in the repository root applies to Stellar Cartography
**project-owned** source code, documentation authored for this project, and
project configuration/registry structure.

It does **not** relicense third-party imagery, multimedia, survey products,
or Stellarium. Those retain their respective agency / author terms; Cartography
typically **links** to them with credit rather than redistributing binaries.
