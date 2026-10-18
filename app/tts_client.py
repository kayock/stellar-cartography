"""
tts_client.py

Local TTS provider abstraction for Stellar Cartography narration.

Cartography owns the spoken text. Father Fox Voice and Kayock Voice are
speech renderers only. Father Fox /api/talk invokes an LLM and is never
called. Both providers synthesize through Kayock Voice POST /speak.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import ssl
import struct
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional
from urllib.parse import urlparse

from . import watchlist_store

logger = logging.getLogger("stellar_archive_bridge.tts_client")

CONFIG_PATH = Path(__file__).resolve().parent / "data" / "tts_providers.json"
PROVIDER_IDS = ("father_fox", "kayock_voice")
CONTEXTS = ("constellation_overview", "tour_step", "object", "object_transition", "selection", "exhibit_step")
FORBIDDEN_REQUEST_KEYS = frozenset(
    {"url", "endpoint", "command", "path", "tts_url", "base_url", "host", "shell", "file"}
)
def _tts_extra_hosts() -> frozenset[str]:
    """Optional comma-separated hosts from STELLAR_CARTOGRAPHY_TTS_HOSTS.

    Defaults to loopback only so public releases do not embed LAN addresses.
    Local deployments may add hosts, e.g.:
      export STELLAR_CARTOGRAPHY_TTS_HOSTS=tts.example.local
    """
    import os

    hosts = {"127.0.0.1", "localhost"}
    raw = (os.environ.get("STELLAR_CARTOGRAPHY_TTS_HOSTS") or "").strip()
    if raw:
        for part in raw.split(","):
            host = part.strip().lower()
            if host:
                hosts.add(host)
    return frozenset(hosts)


ALLOWED_TTS_PORTS = frozenset({8765, 8766})


def _tts_allowed_hosts() -> frozenset[str]:
    return _tts_extra_hosts()


def _tts_allowed_netlocs() -> frozenset[str]:
    return frozenset(f"{h}:{p}" for h in _tts_allowed_hosts() for p in ALLOWED_TTS_PORTS)


# Evaluated at import for callers/tests; re-read env if process sets it before import.
ALLOWED_TTS_HOSTS = _tts_allowed_hosts()
ALLOWED_TTS_NETLOCS = _tts_allowed_netlocs()
NARRATION_LABEL = "Cartography Narration"
Transport = Callable[..., Any]


class TTSError(Exception):
    def __init__(self, message: str, *, code: str = "tts_error", status: int = 400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status


def load_config(path: Path | None = None) -> dict[str, Any]:
    raw = json.loads((path or CONFIG_PATH).read_text(encoding="utf-8"))
    providers = raw.get("providers") or {}
    for pid, provider in providers.items():
        for key in ("health_url", "tts_url"):
            url = provider.get(key)
            if url and not is_allowed_local_tts_url(url):
                raise TTSError(
                    f"Provider {pid} {key} is not an allowed local TTS endpoint.",
                    code="unsafe_endpoint",
                    status=500,
                )
    return raw


def is_allowed_local_tts_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except Exception:  # noqa: BLE001
        return False
    if parsed.scheme != "https":
        return False
    if parsed.username or parsed.password:
        return False
    if parsed.path not in {"", "/", "/health", "/speak", "/voices"}:
        return False
    if parsed.query or parsed.fragment:
        return False
    host = (parsed.hostname or "").lower()
    port = parsed.port
    if not port:
        return False
    netloc = f"{host}:{port}"
    return netloc in _tts_allowed_netlocs() and host in _tts_allowed_hosts() and port in ALLOWED_TTS_PORTS


def default_cache_dir(app_root: str | None = None) -> Path:
    return Path(watchlist_store.default_runtime_dir(app_root)) / "narration_cache"


def _local_ssl_context(url: str) -> ssl.SSLContext | None:
    """Relax verification only for hardcoded local voice endpoints."""
    if not is_allowed_local_tts_url(url):
        return ssl.create_default_context()
    return ssl._create_unverified_context()


def default_transport(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: float = 3.0,
) -> dict[str, Any]:
    if not is_allowed_local_tts_url(url):
        raise TTSError("Refusing to contact a non-local or unlisted TTS endpoint.", code="unsafe_endpoint", status=400)
    data = None
    headers = {"Accept": "application/json, audio/wav, */*"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=_local_ssl_context(url)) as response:
            body = response.read()
            mime = (response.headers.get_content_type() or "").lower()
            return {"status": response.status, "body": body, "mime_type": mime}
    except urllib.error.HTTPError as exc:
        exc.read()
        raise TTSError(
            f"TTS service returned HTTP {exc.code}.",
            code="upstream_http",
            status=502,
        ) from exc
    except TimeoutError as exc:
        raise TTSError("Voice service timed out.", code="timeout", status=504) from exc
    except Exception as exc:  # noqa: BLE001
        raise TTSError("Voice service unavailable.", code="unavailable", status=503) from exc


def list_providers(config: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    cfg = config or load_config()
    out = []
    for pid in PROVIDER_IDS:
        provider = (cfg.get("providers") or {}).get(pid)
        if not provider:
            continue
        out.append(
            {
                "id": pid,
                "label": provider.get("label") or pid,
                "default_voice": provider.get("default_voice"),
                "default_profile": provider.get("default_profile"),
                "voices": list(provider.get("allowed_voices") or []),
                "profiles": list(provider.get("allowed_profiles") or []),
                "pure_tts": bool(provider.get("pure_tts")),
                "note": provider.get("note"),
            }
        )
    return out


def normalize_request(payload: dict[str, Any] | None, config: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = config or load_config()
    body = payload if isinstance(payload, dict) else {}
    forbidden = FORBIDDEN_REQUEST_KEYS.intersection(body)
    if forbidden:
        raise TTSError("TTS requests may not include endpoint, path, or command fields.", code="unsafe_field")
    text = str(body.get("text") or "").strip()
    max_chars = int(cfg.get("max_text_chars") or 2500)
    if not text:
        raise TTSError("Narration text is required.", code="empty_text")
    if len(text) > max_chars:
        raise TTSError(f"Narration text exceeds {max_chars} characters.", code="text_too_long")
    provider_id = str(body.get("provider") or "").strip()
    if provider_id not in PROVIDER_IDS:
        raise TTSError("Unknown TTS provider.", code="invalid_provider")
    provider = (cfg.get("providers") or {}).get(provider_id) or {}
    voice = str(body.get("voice") or provider.get("default_voice") or "").strip() or None
    profile = str(body.get("profile") or provider.get("default_profile") or "").strip() or None
    allowed_voices = set(provider.get("allowed_voices") or [])
    allowed_profiles = set(provider.get("allowed_profiles") or [])
    if voice and allowed_voices and voice not in allowed_voices:
        raise TTSError("Unsupported voice for this provider.", code="invalid_voice")
    if profile and allowed_profiles and profile not in allowed_profiles:
        raise TTSError("Unsupported voice profile for this provider.", code="invalid_voice")
    context = str(body.get("context") or "constellation_overview").strip()
    if context not in CONTEXTS:
        context = "constellation_overview"
    return {
        "text": text,
        "provider": provider_id,
        "voice": voice or provider.get("default_voice"),
        "profile": profile or provider.get("default_profile"),
        "context": context,
        "request_id": str(body.get("request_id") or _new_request_id()),
    }


def provider_health(
    provider_id: str,
    *,
    config: dict[str, Any] | None = None,
    transport: Transport | None = None,
) -> dict[str, Any]:
    cfg = config or load_config()
    provider = (cfg.get("providers") or {}).get(provider_id)
    if not provider:
        raise TTSError("Unknown TTS provider.", code="invalid_provider")
    health_url = provider["health_url"]
    timeout = float(cfg.get("health_timeout_sec") or 3)
    send = transport or default_transport
    try:
        result = send(health_url, method="GET", timeout=timeout)
        body = result.get("body") or b""
        payload = {}
        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception:  # noqa: BLE001
            payload = {}
        available = result.get("status") == 200 and str(payload.get("status") or "").lower() in {"ok", "healthy", ""}
        if result.get("status") == 200 and not payload:
            available = True
        return {
            "id": provider_id,
            "label": provider.get("label") or provider_id,
            "available": bool(available),
            "status": "available" if available else "unavailable",
            "voices": list(provider.get("allowed_voices") or []),
            "profiles": list(provider.get("allowed_profiles") or []),
            "default_voice": provider.get("default_voice"),
            "pure_tts": bool(provider.get("pure_tts")),
        }
    except TTSError:
        return {
            "id": provider_id,
            "label": provider.get("label") or provider_id,
            "available": False,
            "status": "unavailable",
            "voices": list(provider.get("allowed_voices") or []),
            "profiles": list(provider.get("allowed_profiles") or []),
            "default_voice": provider.get("default_voice"),
            "pure_tts": bool(provider.get("pure_tts")),
            "error": f"{provider.get('label') or provider_id} unavailable.",
        }


def providers_payload(
    *,
    config: dict[str, Any] | None = None,
    transport: Transport | None = None,
) -> dict[str, Any]:
    cfg = config or load_config()
    providers = [provider_health(pid, config=cfg, transport=transport) for pid in PROVIDER_IDS if (cfg.get("providers") or {}).get(pid)]
    return {
        "ok": True,
        "label": NARRATION_LABEL,
        "audio_autoplay": False,
        "tls_note": cfg.get("tls_note"),
        "providers": providers,
    }


def synthesize(
    text: str,
    provider: str,
    voice: Optional[str] = None,
    request_id: Optional[str] = None,
    *,
    profile: Optional[str] = None,
    context: str = "constellation_overview",
    raw_request: dict[str, Any] | None = None,
    config: dict[str, Any] | None = None,
    cache_dir: Path | None = None,
    transport: Transport | None = None,
    now: Optional[float] = None,
) -> dict[str, Any]:
    cfg = config or load_config()
    request_body = dict(raw_request) if isinstance(raw_request, dict) else {}
    request_body.update(
        {
            "text": text,
            "provider": provider,
            "voice": voice if voice is not None else request_body.get("voice"),
            "profile": profile if profile is not None else request_body.get("profile"),
            "context": context or request_body.get("context") or "constellation_overview",
            "request_id": request_id or request_body.get("request_id"),
        }
    )
    normalized = normalize_request(request_body, config=cfg)
    spec = (cfg.get("providers") or {}).get(normalized["provider"]) or {}
    send = transport or default_transport
    directory = Path(cache_dir) if cache_dir else default_cache_dir()
    cached = cache_get(normalized, cache_dir=directory, config=cfg, now=now)
    if cached:
        cached["cache_hit"] = True
        return cached

    health = provider_health(normalized["provider"], config=cfg, transport=send)
    if not health.get("available"):
        raise TTSError(
            f"{spec.get('label') or normalized['provider']} unavailable.",
            code="unavailable",
            status=503,
        )

    tts_url = spec["tts_url"]
    if not is_allowed_local_tts_url(tts_url):
        raise TTSError("Refusing to contact a non-local TTS endpoint.", code="unsafe_endpoint", status=400)
    timeout = float(cfg.get("request_timeout_sec") or 90)
    upstream = send(
        tts_url,
        method="POST",
        payload={"text": normalized["text"], "profile": normalized["profile"], "voice": normalized["voice"]},
        timeout=timeout,
    )
    audio = upstream.get("body") or b""
    if not audio:
        raise TTSError("Voice service returned no audio.", code="empty_audio", status=502)
    mime = upstream.get("mime_type") or "audio/wav"
    if "json" in mime:
        raise TTSError("Voice service did not return audio.", code="bad_audio", status=502)
    result = {
        "ok": True,
        "provider": normalized["provider"],
        "voice": normalized["voice"],
        "profile": normalized["profile"],
        "mime_type": "audio/wav" if "wav" in mime or audio[:4] == b"RIFF" else mime,
        "audio": audio,
        "duration_seconds": wav_duration_seconds(audio),
        "request_id": normalized["request_id"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cache_hit": False,
        "label": NARRATION_LABEL,
        "audio_autoplay": False,
        "context": normalized["context"],
    }
    cache_set(normalized, result, cache_dir=directory, config=cfg, now=now)
    return result


def synthesize_payload(result: dict[str, Any]) -> dict[str, Any]:
    audio = result.get("audio") or b""
    return {
        "ok": True,
        "provider": result.get("provider"),
        "voice": result.get("voice"),
        "profile": result.get("profile"),
        "mime_type": result.get("mime_type") or "audio/wav",
        "audio_base64": base64.b64encode(audio).decode("ascii"),
        "duration_seconds": result.get("duration_seconds"),
        "request_id": result.get("request_id"),
        "generated_at": result.get("generated_at"),
        "cache_hit": bool(result.get("cache_hit")),
        "label": NARRATION_LABEL,
        "audio_autoplay": False,
        "context": result.get("context"),
    }


def cache_key(normalized: dict[str, Any]) -> str:
    raw = "|".join(
        [
            str(normalized.get("provider") or ""),
            str(normalized.get("voice") or ""),
            str(normalized.get("profile") or ""),
            str(normalized.get("text") or ""),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def cache_get(
    normalized: dict[str, Any],
    *,
    cache_dir: Path,
    config: dict[str, Any],
    now: Optional[float] = None,
) -> dict[str, Any] | None:
    path = Path(cache_dir) / f"{cache_key(normalized)}.wav"
    meta_path = path.with_suffix(".json")
    if not path.is_file() or not meta_path.is_file():
        return None
    stamp = now if now is not None else time.time()
    age = stamp - path.stat().st_mtime
    if age > float(config.get("cache_max_age_sec") or 604800):
        return None
    audio = path.read_bytes()
    if not audio:
        return None
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
    meta["audio"] = audio
    meta["ok"] = True
    return meta


def cache_set(
    normalized: dict[str, Any],
    result: dict[str, Any],
    *,
    cache_dir: Path,
    config: dict[str, Any],
    now: Optional[float] = None,
) -> None:
    directory = Path(cache_dir)
    directory.mkdir(parents=True, exist_ok=True)
    key = cache_key(normalized)
    path = directory / f"{key}.wav"
    meta_path = directory / f"{key}.json"
    audio = result.get("audio") or b""
    if not audio:
        return
    path.write_bytes(audio)
    meta = {k: v for k, v in result.items() if k != "audio"}
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    cleanup_cache(directory, config=config, now=now)


def cleanup_cache(cache_dir: Path, *, config: dict[str, Any], now: Optional[float] = None) -> None:
    directory = Path(cache_dir)
    if not directory.is_dir():
        return
    stamp = now if now is not None else time.time()
    max_age = float(config.get("cache_max_age_sec") or 604800)
    max_bytes = int(config.get("cache_max_bytes") or 80 * 1024 * 1024)
    files = [p for p in directory.iterdir() if p.suffix == ".wav" and p.is_file()]
    files.sort(key=lambda p: p.stat().st_mtime)
    total = 0
    for path in files:
        meta = path.with_suffix(".json")
        age = stamp - path.stat().st_mtime
        if age > max_age:
            path.unlink(missing_ok=True)
            meta.unlink(missing_ok=True)
            continue
        total += path.stat().st_size
    while total > max_bytes and files:
        oldest = files.pop(0)
        if not oldest.exists():
            continue
        total -= oldest.stat().st_size
        oldest.unlink(missing_ok=True)
        oldest.with_suffix(".json").unlink(missing_ok=True)


def wav_duration_seconds(audio: bytes) -> float | None:
    if len(audio) < 44 or audio[0:4] != b"RIFF":
        return None
    try:
        byte_rate = struct.unpack_from("<I", audio, 28)[0]
        data_size = struct.unpack_from("<I", audio, 40)[0]
        if byte_rate > 0:
            return round(data_size / byte_rate, 3)
    except Exception:  # noqa: BLE001
        return None
    return None


def _new_request_id() -> str:
    return hashlib.sha256(f"{time.time_ns()}".encode("ascii")).hexdigest()[:16]


def error_payload(exc: TTSError) -> dict[str, Any]:
    return {
        "ok": False,
        "error": exc.message,
        "code": exc.code,
        "label": NARRATION_LABEL,
        "audio_autoplay": False,
    }
