# Voice and narration

Stellar Cartography is **voice-ready today**: narration hooks are built into the
UI and server. A TTS backend is **optional**. The core app (Stellarium bridge,
Stories of the Sky, Specials, archives) works without any speech service.

---

## What is already built in

- **Narration text** is produced by Cartography itself (stories, exhibit steps,
  Specials segments). The browser loads text via Cartography HTTP APIs such as
  `/api/narration` and per-Special `/api/<special>/narration` routes.
- **Speech audio** is optional. When a compatible local TTS endpoint is
  available, the UI can request synthesis through Cartography’s proxy:
  - `GET /api/tts/providers` — provider availability / labels
  - `GET /api/tts/status` — lightweight playback status
  - `POST /api/tts/synthesize` — synthesize narration audio
  - `POST /api/tts/stop` — stop / clear narration state
- The frontend module `app/static/lib/narration_tts.js` drives **user-triggered**
  play / pause / resume / stop controls. It sets `audio.autoplay = false`.
- Responses consistently mark `"audio_autoplay": false`. Nothing in the
  narration path is designed to start speaking without a user action.
- An optional **auto-advance after narration** checkbox exists in the UI; it
  only advances after user-initiated playback finishes. It is not browser
  autoplay of audio on page load.

Provider registry (defaults): `app/data/tts_providers.json`  
Client logic: `app/tts_client.py`

---

## Optional by design

| Without TTS | With a compatible local TTS |
|-------------|------------------------------|
| Full UI, Stellarium control, Specials, stories, text narration scripts | Same, plus spoken audio on demand |
| Provider status shows unavailable | Synthesize returns audio for play buttons |

You do **not** need a voice service to install or use Stellar Cartography.

---

## Father Fox / Kayock Voice (examples, not dependencies)

The default provider entries in `tts_providers.json` are labeled **Father Fox**
and **Kayock Voice**. Those names reflect the original lab deployment’s local
HTTPS speech services. They are **not** bundled with this repository and are
**not** required.

In that example configuration:

- Health checks use HTTPS `/health`
- Synthesis uses HTTPS `POST /speak`
- Cartography **never** calls Father Fox’s LLM `/api/talk` endpoint; it only
  sends Cartography-owned text to a `/speak`-style renderer
- Allowed local ports in code today are **8765** and **8766**
- Default URLs point at loopback (`127.0.0.1`)

Any compatible local service that matches the allowlisted URL shape and the
request body Cartography sends can be used by adjusting provider config (and
hosts, below). This project does **not** claim support for arbitrary cloud TTS
APIs.

---

## Allowlisting hosts (`STELLAR_CARTOGRAPHY_TTS_HOSTS`)

Outbound TTS URLs must pass `is_allowed_local_tts_url()` in `app/tts_client.py`:

- Scheme: **https** only
- No username/password in the URL
- Path must be one of: `/`, `/health`, `/speak`, `/voices` (or empty)
- No query string or fragment
- Port must be **8765** or **8766**
- Host must be **loopback** (`127.0.0.1` / `localhost`) **or** listed in:

```bash
export STELLAR_CARTOGRAPHY_TTS_HOSTS=tts.example.local
# comma-separated for multiple hosts
```

Set this in the environment **before** starting Cartography (for example in a
local launcher). Do not commit machine-specific hosts into the public tree.

TLS note: verification may be relaxed **only** for allowlisted local voice
endpoints (see `tls_note` in `tts_providers.json`). TLS is not disabled globally.

---

## Practical integration shape (as implemented)

### 1. Narration text (Cartography → browser)

Examples:

- `GET /api/narration?kind=…` (stories / exhibits / selection contexts)
- `GET /api/<special>/narration?segment=…` for Specials that expose segments

These return JSON narration payloads owned by Cartography. Exact query
parameters vary by route; see `app/server.py` and the Special modules.

### 2. Synthesize (browser → Cartography → local TTS)

`POST /api/tts/synthesize` with a JSON body. The server normalizes fields and
forwards to the configured provider `tts_url` roughly as:

```json
{ "text": "<cartography narration text>", "profile": "<profile>", "voice": "<voice>" }
```

Successful responses include base64 audio (`audio_base64`), mime type, and
`"audio_autoplay": false`. Audio may be cached under `runtime_data/narration_cache/`
(local, gitignored).

### 3. Compatibility expectation

A compatible backend is expected to:

1. Answer HTTPS health on an allowlisted host:port path `/health`
2. Accept HTTPS `POST /speak` with JSON `text` / `profile` / `voice`
3. Return audio bytes (typically WAV), not an LLM chat completion

Exact upstream HTTP status codes and headers beyond that are whatever the
configured transport accepts; Cartography validates allowlisting and treats
empty/non-audio bodies as errors.

---

## Specials and exhibits

Existing Specials (Light Echoes through Cosmic Dawn) and exhibit / story flows
can surface narration segments through the same pipeline: Cartography text
first, optional TTS second. Absence of TTS does not block reading the script
in the UI.

---

## Security / privacy reminders

- Prefer loopback TTS on the same machine as Cartography
- Use `STELLAR_CARTOGRAPHY_TTS_HOSTS` only for hosts you trust on your network
- Do not expose Cartography or TTS endpoints to the public Internet without
  additional hardening
- See also [`SECURITY.md`](../SECURITY.md)

---

## Related files

- `app/tts_client.py` — allowlist, synthesize, cache
- `app/data/tts_providers.json` — provider registry
- `app/static/lib/narration_tts.js` — UI controls (no autoplay)
- `docs/PUBLIC_INSTALL.md` — optional install notes
