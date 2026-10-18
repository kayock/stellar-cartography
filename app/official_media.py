"""
official_media.py

Official Media Layer for NASA Image and Video Library search plus a
small curated Chandra registry.

Implementation map (Phase 1):
  * planetary_image.py already searches images-api.nasa.gov for Solar
    System registry targets (images only). Reuse its sanitizers, host
    allowlists, and search URL. Do not replace that panel.
  * No generic official-media abstraction existed.
  * Object aliases already live in solar_system_media_registry,
    constellation stories, Cosmic Signal target_aliases, and selection
    name / alt_name / catalogue designations.
  * Story panel surfaces a compact Official Media section and links
    Cosmic Signal / Spectrum instead of duplicating those decks.

This module may talk to NASA only through an injected or default
fetcher. Cosmic Signal remains the canonical sonification player.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable, Optional

from . import cosmic_signal_registry
from . import planetary_image
from . import solar_system_media_registry as ss_registry
from . import watchlist_store

logger = logging.getLogger("stellar_archive_bridge.official_media")

NASA_SEARCH_URL = planetary_image.NASA_IMAGES_SEARCH_URL
NASA_DETAILS_BASE = planetary_image.NASA_IMAGES_DETAILS_BASE
NASA_ASSET_BASE = "https://images-api.nasa.gov/asset/"
REQUEST_TIMEOUT_SEC = 10
MAX_RESPONSE_BYTES = 512 * 1024
SEARCH_PAGE_SIZE = "15"
CACHE_TTL_OK_SEC = 6 * 3600
CACHE_TTL_FAIL_SEC = 300
MAX_QUERY_LEN = 80
MAX_ITEMS = 8
STORY_ALTERNATES = 3

CHANDRA_REGISTRY_PATH = Path(__file__).resolve().parent / "data" / "chandra_media_registry.json"

ALLOWED_MEDIA_HOSTS = frozenset(
    {
        "images-assets.nasa.gov",
        "www.chandra.si.edu",
        "chandra.si.edu",
    }
)
ALLOWED_SOURCE_HOSTS = frozenset(
    {
        "images.nasa.gov",
        "www.chandra.si.edu",
        "chandra.si.edu",
        "science.nasa.gov",
        "www.nasa.gov",
    }
)
ALLOWED_THUMB_HOSTS = ALLOWED_MEDIA_HOSTS
NASA_API_HOSTS = frozenset({"images-api.nasa.gov"})

NASA_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")
ITEM_ID_RE = re.compile(r"^(nasa|chandra|cosmic):[A-Za-z0-9._-]+$")
_WORD_RE = re.compile(r"[^a-z0-9]+")
_GENERIC_ONLY = frozenset(
    {
        "space",
        "nasa",
        "universe",
        "astronomy",
        "galaxy",
        "stars",
        "star",
        "sky",
        "cosmos",
        "science",
        "education",
        "image",
        "video",
        "photo",
    }
)
_SONIFY_RE = re.compile(r"sonif", re.I)
_PLAYABLE_EXT = (".mp4", ".m4v", ".webm", ".mp3", ".m4a", ".wav")
_CAPTION_EXT = (".vtt", ".srt")
_IMAGE_EXT = (".jpg", ".jpeg", ".png", ".gif", ".webp")

Fetcher = Callable[[str, float], dict]


class OfficialMediaError(ValueError):
    """Raised when the Chandra media registry is malformed."""


def _now() -> float:
    return time.time()


def normalize_query(raw: str | None) -> str:
    if not raw or not isinstance(raw, str):
        return ""
    text = planetary_image.sanitize_text(raw, max_len=MAX_QUERY_LEN) or ""
    text = _WORD_RE.sub(" ", text.lower()).strip()
    return text


def validate_search_query(raw: str | None) -> dict[str, Any]:
    if raw is None or not isinstance(raw, str) or not raw.strip():
        return {"ok": False, "error": "Search query is required."}
    text = raw.strip()
    if len(text) > MAX_QUERY_LEN:
        return {"ok": False, "error": "Search query is too long."}
    lowered = text.lower()
    if "://" in lowered or lowered.startswith("www."):
        return {"ok": False, "error": "Arbitrary URLs are not fetched. Enter an object name."}
    if planetary_image._CONTROL_CHAR_RE.search(text):
        return {"ok": False, "error": "Search query contains invalid characters."}
    if not normalize_query(text):
        return {"ok": False, "error": "Search query is empty after normalization."}
    return {"ok": True, "query": text.strip()}


def cache_key(provider: str, query: str, media_type: str | None = None) -> str:
    media = (media_type or "all").strip().lower()
    material = f"{provider}|{normalize_query(query)}|{media}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def default_cache_dir(app_root: str | None = None) -> str:
    return os.path.join(watchlist_store.default_runtime_dir(app_root), "official_media_cache")


def cache_get(
    key: str,
    *,
    cache_dir: str | None = None,
    now: Optional[float] = None,
) -> dict[str, Any] | None:
    path = os.path.join(cache_dir or default_cache_dir(), f"{key}.json")
    if not os.path.isfile(path):
        return None
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    expires = payload.get("expires_at")
    stamp = now if now is not None else _now()
    if not isinstance(expires, (int, float)) or stamp >= float(expires):
        return None
    return payload


def cache_set(
    key: str,
    payload: dict[str, Any],
    *,
    ok: bool,
    cache_dir: str | None = None,
    now: Optional[float] = None,
    ttl_ok: float = CACHE_TTL_OK_SEC,
    ttl_fail: float = CACHE_TTL_FAIL_SEC,
) -> dict[str, Any]:
    directory = cache_dir or default_cache_dir()
    os.makedirs(directory, exist_ok=True)
    stamp = now if now is not None else _now()
    record = {
        "key": key,
        "cached_at": stamp,
        "expires_at": stamp + (ttl_ok if ok else ttl_fail),
        "ok": bool(ok),
        "payload": payload,
    }
    dest = os.path.join(directory, f"{key}.json")
    fd, tmp = tempfile.mkstemp(prefix="omc-", suffix=".json", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(record, handle)
        os.replace(tmp, dest)
    except OSError:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return record


def is_allowed_url(url: str | None, hosts: frozenset[str], *, path_prefix: str | None = None) -> bool:
    if not url or not isinstance(url, str):
        return False
    if planetary_image._url_has_unsafe_characters(url):
        return False
    try:
        parsed = urllib.parse.urlparse(url.strip())
    except Exception:  # noqa: BLE001
        return False
    if parsed.scheme != "https":
        return False
    if parsed.username or parsed.password:
        return False
    host = (parsed.hostname or "").lower()
    if host not in hosts:
        return False
    if path_prefix and not (parsed.path or "").startswith(path_prefix):
        return False
    return True


def is_allowed_media_url(url: str | None) -> bool:
    return is_allowed_url(url, ALLOWED_MEDIA_HOSTS)


def is_allowed_source_url(url: str | None) -> bool:
    return is_allowed_url(url, ALLOWED_SOURCE_HOSTS)


def is_allowed_nasa_api_url(url: str | None) -> bool:
    return is_allowed_url(url, NASA_API_HOSTS, path_prefix="/")


def _empty_item_fields() -> dict[str, Any]:
    return {
        "id": None,
        "provider": None,
        "provider_label": None,
        "title": None,
        "description": None,
        "media_type": None,
        "media_url": None,
        "thumbnail_url": None,
        "preview_url": None,
        "caption_url": None,
        "transcript_url": None,
        "metadata_url": None,
        "source_page_url": None,
        "date_created": None,
        "center": None,
        "keywords": [],
        "nasa_id": None,
        "object_name": None,
        "object_aliases": [],
        "constellation": None,
        "provenance": None,
        "license_note": None,
        "relation": None,
        "confidence": None,
        "playable_inline": False,
        "downloadable": False,
        "cached_at": None,
        "audio_autoplay": False,
        "reuse_cosmic_signal": False,
        "cosmic_signal_id": None,
        "spectrum_id": None,
        "signal_category": None,
        "caption_available": False,
        "transcript_available": False,
    }


def normalize_media_item(raw: dict[str, Any] | None) -> dict[str, Any]:
    item = _empty_item_fields()
    if not isinstance(raw, dict):
        return item
    item.update(
        {
            "id": planetary_image.sanitize_text(raw.get("id"), max_len=80),
            "provider": planetary_image.sanitize_text(raw.get("provider"), max_len=40),
            "provider_label": planetary_image.sanitize_text(raw.get("provider_label"), max_len=80),
            "title": planetary_image.sanitize_text(raw.get("title"), max_len=160),
            "description": planetary_image.sanitize_media_description(raw.get("description")),
            "media_type": planetary_image.sanitize_text(raw.get("media_type"), max_len=40),
            "date_created": planetary_image.sanitize_text(raw.get("date_created"), max_len=40),
            "center": planetary_image.sanitize_text(raw.get("center"), max_len=80),
            "nasa_id": planetary_image.sanitize_text(raw.get("nasa_id"), max_len=40),
            "object_name": planetary_image.sanitize_text(raw.get("object_name"), max_len=80),
            "constellation": planetary_image.sanitize_text(raw.get("constellation"), max_len=40),
            "provenance": planetary_image.sanitize_text(raw.get("provenance"), max_len=400),
            "license_note": planetary_image.sanitize_text(raw.get("license_note"), max_len=240),
            "relation": _normalize_relation(raw.get("relation")),
            "confidence": _optional_confidence(raw.get("confidence")),
            "signal_category": planetary_image.sanitize_text(raw.get("signal_category"), max_len=40),
            "cosmic_signal_id": planetary_image.sanitize_text(raw.get("cosmic_signal_id"), max_len=80),
            "spectrum_id": planetary_image.sanitize_text(raw.get("spectrum_id"), max_len=80),
            "reuse_cosmic_signal": bool(raw.get("reuse_cosmic_signal")),
            "audio_autoplay": False,
            "playable_inline": bool(raw.get("playable_inline")),
            "downloadable": bool(raw.get("downloadable")),
            "cached_at": raw.get("cached_at") if isinstance(raw.get("cached_at"), (int, float, str)) else None,
        }
    )
    item["keywords"] = _string_list(raw.get("keywords"), 12, 80)
    item["object_aliases"] = _string_list(raw.get("object_aliases"), 12, 80)
    item["media_url"] = raw.get("media_url") if is_allowed_media_url(raw.get("media_url")) else None
    item["thumbnail_url"] = raw.get("thumbnail_url") if is_allowed_url(raw.get("thumbnail_url"), ALLOWED_THUMB_HOSTS) else None
    item["preview_url"] = raw.get("preview_url") if is_allowed_url(raw.get("preview_url"), ALLOWED_THUMB_HOSTS) else None
    item["caption_url"] = raw.get("caption_url") if is_allowed_media_url(raw.get("caption_url")) else None
    item["transcript_url"] = raw.get("transcript_url") if is_allowed_source_url(raw.get("transcript_url")) else None
    item["metadata_url"] = raw.get("metadata_url") if is_allowed_nasa_api_url(raw.get("metadata_url")) else None
    item["source_page_url"] = raw.get("source_page_url") if is_allowed_source_url(raw.get("source_page_url")) else None
    if item["reuse_cosmic_signal"]:
        item["playable_inline"] = False
        item["media_url"] = None
    elif item["media_url"] and _url_ext(item["media_url"]) in _PLAYABLE_EXT:
        item["playable_inline"] = True
    item["caption_available"] = bool(item["caption_url"])
    item["transcript_available"] = bool(item["transcript_url"] or item["description"])
    if item["media_type"] == "sonification":
        item["signal_category"] = item["signal_category"] or "sonification"
    return item


def _normalize_relation(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    key = value.strip().lower()
    if key in {"exact", "related", "general"}:
        return key
    return None


def _optional_confidence(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number < 0 or number > 1:
        return None
    return number


def _string_list(value: Any, limit: int, item_len: int) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for raw in value:
        text = planetary_image.sanitize_text(raw, max_len=item_len)
        if text:
            out.append(text)
        if len(out) >= limit:
            break
    return out


def _url_ext(url: str) -> str:
    path = urllib.parse.urlparse(url).path.lower()
    _, ext = os.path.splitext(path)
    return ext


def _phrase_in(haystack: str, phrase: str) -> bool:
    needle = normalize_query(phrase)
    if not needle:
        return False
    return f" {needle} " in f" {haystack} "


def collect_object_terms(selection: dict[str, Any] | None, extra_name: str | None = None) -> dict[str, Any]:
    selection = selection if isinstance(selection, dict) else {}
    names: list[str] = []
    for raw in (
        extra_name,
        selection.get("name"),
        selection.get("alt_name"),
        selection.get("object_name"),
    ):
        text = planetary_image.sanitize_text(raw, max_len=80)
        if text and text not in names:
            names.append(text)
    designations = selection.get("catalogue_designations")
    if isinstance(designations, str):
        for part in re.split(r"[,;/]", designations):
            text = planetary_image.sanitize_text(part, max_len=80)
            if text and text not in names:
                names.append(text)
    elif isinstance(designations, list):
        names.extend(_string_list(designations, 8, 80))

    aliases: list[str] = []
    ss_id = ss_registry.normalize_media_target_id(names[0] if names else None)
    if ss_id:
        entry = ss_registry.get_entry(ss_id)
        if entry:
            display = planetary_image.sanitize_text(entry.get("display_name"), max_len=80)
            if display and display not in names:
                names.append(display)
            aliases.extend(_string_list(entry.get("aliases"), 12, 80))

    from . import constellation_story

    for story in constellation_story.enabled_stories():
        for obj in list(story.get("major_objects") or []) + list(story.get("notable_deep_sky_objects") or []):
            if not isinstance(obj, dict):
                continue
            candidates = [obj.get("name"), obj.get("search_name"), *(obj.get("aliases") or []), *(obj.get("designations") or [])]
            if any(normalize_query(c) and normalize_query(c) in {normalize_query(n) for n in names} for c in candidates):
                for extra in candidates:
                    text = planetary_image.sanitize_text(extra, max_len=80)
                    if text and text not in names and text not in aliases:
                        aliases.append(text)

    for entry in chandra_entries():
        hay = [entry.get("object_name"), *(entry.get("object_aliases") or [])]
        known = {normalize_query(n) for n in names + aliases}
        if any(normalize_query(token) in known for token in hay):
            for extra in hay:
                text = planetary_image.sanitize_text(extra, max_len=80)
                if text and text not in names and text not in aliases:
                    aliases.append(text)

    constellation = planetary_image.sanitize_text(selection.get("constellation"), max_len=40)
    constellation_names: list[str] = []
    if constellation:
        constellation_names.append(constellation)
        resolved = constellation_story.resolve_story(constellation)
        if resolved:
            constellation_names.extend(
                [
                    resolved.get("canonical_name") or "",
                    resolved.get("abbreviation") or "",
                    *list(resolved.get("aliases") or []),
                ]
            )
    constellation_names = [n for n in _string_list(constellation_names, 8, 80) if n]
    primary = names[0] if names else extra_name
    return {
        "primary": planetary_image.sanitize_text(primary, max_len=80),
        "names": names,
        "aliases": aliases,
        "constellation": constellation,
        "constellation_names": constellation_names,
        "object_type": planetary_image.sanitize_text(selection.get("object_type"), max_len=80),
    }


def classify_relation(item: dict[str, Any], terms: dict[str, Any]) -> tuple[str | None, float]:
    title = normalize_query(item.get("title"))
    keywords = normalize_query(" ".join(item.get("keywords") or []))
    description = normalize_query(item.get("description"))
    hay_strong = f"{title} {keywords}".strip()
    hay_all = f"{title} {keywords} {description}".strip()
    if not hay_all:
        return None, 0.0

    object_terms = [t for t in (terms.get("names") or []) + (terms.get("aliases") or []) if normalize_query(t)]
    constellation_terms = [t for t in (terms.get("constellation_names") or []) if normalize_query(t)]
    tokens = set(hay_all.split())
    if tokens and tokens <= _GENERIC_ONLY:
        return None, 0.0

    for term in object_terms:
        if _phrase_in(title, term) or _phrase_in(keywords, term):
            return "exact", 0.95
    nasa_id = normalize_query(item.get("nasa_id"))
    if nasa_id:
        for term in object_terms:
            nterm = normalize_query(term)
            if len(nterm) >= 4 and _phrase_in(nasa_id, nterm):
                return "exact", 0.9
    for term in object_terms:
        if _phrase_in(description, term):
            return "related", 0.7
    object_hit = any(_phrase_in(hay_all, term) for term in object_terms)
    constellation_hit = any(_phrase_in(hay_all, term) for term in constellation_terms)
    if object_hit:
        return "related", 0.6
    if constellation_hit and not object_terms:
        return "general", 0.35
    if constellation_hit and object_terms:
        return "general", 0.3
    return None, 0.0


def suppress_duplicates(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for item in items:
        nasa_id = (item.get("nasa_id") or "").lower()
        title = normalize_query(item.get("title"))
        media_type = (item.get("media_type") or "").lower()
        key = nasa_id or f"{item.get('provider')}|{title}|{media_type}"
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def load_chandra_registry() -> dict[str, Any]:
    raw = json.loads(CHANDRA_REGISTRY_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("entries"), list):
        raise OfficialMediaError("Chandra media registry is malformed.")
    return raw


def chandra_entries() -> list[dict[str, Any]]:
    return [e for e in load_chandra_registry().get("entries") or [] if isinstance(e, dict) and e.get("enabled")]


def _chandra_to_item(entry: dict[str, Any]) -> dict[str, Any]:
    provider_label = load_chandra_registry().get("provider_label") or "Chandra X-ray Center"
    return normalize_media_item(
        {
            "id": f"chandra:{entry.get('id')}",
            "provider": "chandra",
            "provider_label": provider_label,
            "title": entry.get("title"),
            "description": entry.get("description"),
            "media_type": entry.get("media_type"),
            "media_url": entry.get("media_url"),
            "thumbnail_url": entry.get("thumbnail_url"),
            "preview_url": entry.get("thumbnail_url"),
            "source_page_url": entry.get("source_page_url"),
            "date_created": entry.get("date_created"),
            "center": entry.get("center"),
            "keywords": entry.get("keywords") or [],
            "object_name": entry.get("object_name"),
            "object_aliases": entry.get("object_aliases") or [],
            "constellation": entry.get("constellation"),
            "provenance": entry.get("provenance"),
            "license_note": load_chandra_registry().get("license_note"),
            "relation": entry.get("relation") or "exact",
            "confidence": 0.99 if entry.get("relation") == "exact" else 0.7,
            "reuse_cosmic_signal": entry.get("reuse_cosmic_signal"),
            "cosmic_signal_id": entry.get("cosmic_signal_id"),
            "spectrum_id": entry.get("spectrum_id"),
            "signal_category": entry.get("signal_category"),
            "playable_inline": False,
        }
    )


def match_chandra(terms: dict[str, Any]) -> list[dict[str, Any]]:
    needles = [normalize_query(t) for t in (terms.get("names") or []) + (terms.get("aliases") or []) if normalize_query(t)]
    if not needles:
        return []
    matched: list[dict[str, Any]] = []
    for entry in chandra_entries():
        hay = [entry.get("object_name"), *(entry.get("object_aliases") or [])]
        if any(normalize_query(token) in needles for token in hay):
            matched.append(_chandra_to_item(entry))
    return matched


def cosmic_signal_reuse_items(terms: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entry in match_chandra(terms):
        signal_id = entry.get("cosmic_signal_id")
        if not entry.get("reuse_cosmic_signal") or not signal_id or signal_id in seen:
            continue
        seen.add(signal_id)
        items.append(entry)
    return items


def parse_nasa_search_items(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    collection = payload.get("collection")
    if not isinstance(collection, dict):
        return []
    raw_items = collection.get("items")
    if not isinstance(raw_items, list):
        return []
    out: list[dict[str, Any]] = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            continue
        data_list = raw.get("data")
        if not isinstance(data_list, list) or not data_list or not isinstance(data_list[0], dict):
            continue
        data = data_list[0]
        nasa_id = planetary_image.sanitize_text(data.get("nasa_id"), max_len=40)
        if not nasa_id or not NASA_ID_RE.fullmatch(nasa_id):
            continue
        links = raw.get("links") if isinstance(raw.get("links"), list) else []
        thumb = _pick_link(links, _IMAGE_EXT)
        media = _pick_link(links, _PLAYABLE_EXT)
        caption = _pick_link(links, _CAPTION_EXT)
        media_type = str(data.get("media_type") or "image").strip().lower()
        if media_type not in {"image", "video", "audio"}:
            media_type = "image"
        keywords = data.get("keywords") if isinstance(data.get("keywords"), list) else []
        item = normalize_media_item(
            {
                "id": f"nasa:{nasa_id}",
                "provider": "nasa",
                "provider_label": "NASA Image and Video Library",
                "title": data.get("title"),
                "description": data.get("description"),
                "media_type": media_type,
                "media_url": media,
                "thumbnail_url": thumb,
                "preview_url": thumb,
                "caption_url": caption,
                "metadata_url": f"{NASA_ASSET_BASE}{nasa_id}",
                "source_page_url": f"{NASA_DETAILS_BASE}{nasa_id}",
                "date_created": data.get("date_created"),
                "center": data.get("center"),
                "keywords": keywords,
                "nasa_id": nasa_id,
                "provenance": (
                    "NASA Image and Video Library public-media search. Outreach asset, "
                    "not a calibrated science product and not proof of current appearance."
                ),
                "license_note": "NASA media generally available for public use with credit; see the official source page.",
                "signal_category": "ordinary_video" if media_type == "video" else (
                    "ordinary_audio" if media_type == "audio" else "ordinary_image"
                ),
            }
        )
        if _SONIFY_RE.search(item.get("title") or "") or _SONIFY_RE.search(item.get("description") or ""):
            item["signal_category"] = "sonification"
            item["media_type"] = "sonification"
        out.append(item)
    return out


def _pick_link(links: list[Any], extensions: tuple[str, ...]) -> str | None:
    for link in links:
        if not isinstance(link, dict):
            continue
        href = link.get("href")
        if is_allowed_media_url(href) and _url_ext(href) in extensions:
            return href
    return None


def parse_nasa_asset_files(payload: Any) -> dict[str, str | None]:
    files = {"media_url": None, "caption_url": None, "preview_url": None}
    if not isinstance(payload, dict):
        return files
    collection = payload.get("collection")
    items = collection.get("items") if isinstance(collection, dict) else None
    hrefs: list[str] = []
    if isinstance(items, list):
        for item in items:
            if isinstance(item, str):
                hrefs.append(item)
            elif isinstance(item, dict) and isinstance(item.get("href"), str):
                hrefs.append(item["href"])
    for href in hrefs:
        if not is_allowed_media_url(href):
            continue
        ext = _url_ext(href)
        if ext in _PLAYABLE_EXT and not files["media_url"]:
            files["media_url"] = href
        elif ext in _CAPTION_EXT and not files["caption_url"]:
            files["caption_url"] = href
        elif ext in _IMAGE_EXT and not files["preview_url"]:
            files["preview_url"] = href
    return files


def _default_fetch(url: str, timeout: float) -> dict:
    if not is_allowed_nasa_api_url(url):
        raise OfficialMediaError("Refusing to fetch a non-NASA API URL.")
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "FOXAI-StellarCartography/0.5"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise ValueError("Response too large")
        return json.loads(raw.decode("utf-8"))


def build_nasa_search_url(query: str, media_type: str | None = None) -> str:
    media = (media_type or "all").strip().lower()
    params = {"q": query, "page_size": SEARCH_PAGE_SIZE}
    if media in {"image", "video", "audio"}:
        params["media_type"] = media
    else:
        params["media_type"] = "image,video,audio"
    return f"{NASA_SEARCH_URL}?{urllib.parse.urlencode(params)}"


def search_nasa(
    query: str,
    *,
    media_type: str | None = None,
    fetcher: Fetcher | None = None,
    cache_dir: str | None = None,
    now: Optional[float] = None,
    use_cache: bool = True,
) -> dict[str, Any]:
    checked = validate_search_query(query)
    if not checked["ok"]:
        return {"ok": False, "status": "invalid", "error": checked["error"], "items": [], "audio_autoplay": False}
    key = cache_key("nasa", checked["query"], media_type)
    if use_cache:
        cached = cache_get(key, cache_dir=cache_dir, now=now)
        if cached:
            payload = dict(cached.get("payload") or {})
            payload["cache_hit"] = True
            payload["audio_autoplay"] = False
            return payload
    fetch = fetcher or _default_fetch
    url = build_nasa_search_url(checked["query"], media_type)
    try:
        raw = fetch(url, REQUEST_TIMEOUT_SEC)
        items = parse_nasa_search_items(raw)
        result = {
            "ok": True,
            "status": "found" if items else "empty",
            "error": None,
            "items": items,
            "query": checked["query"],
            "search_url": url,
            "cache_hit": False,
            "audio_autoplay": False,
        }
        if use_cache:
            cache_set(key, result, ok=True, cache_dir=cache_dir, now=now)
        return result
    except TimeoutError:
        result = {
            "ok": False,
            "status": "timeout",
            "error": "NASA media service did not respond in time.",
            "items": [],
            "query": checked["query"],
            "cache_hit": False,
            "audio_autoplay": False,
        }
    except urllib.error.HTTPError as exc:
        result = {
            "ok": False,
            "status": "http_error",
            "error": f"NASA media service returned HTTP {exc.code}.",
            "items": [],
            "query": checked["query"],
            "cache_hit": False,
            "audio_autoplay": False,
        }
    except (urllib.error.URLError, OSError, json.JSONDecodeError, ValueError, OfficialMediaError):
        logger.info("NASA official-media search failed for query=%s", checked["query"], exc_info=True)
        result = {
            "ok": False,
            "status": "error",
            "error": "Could not retrieve NASA official media at this time.",
            "items": [],
            "query": checked["query"],
            "cache_hit": False,
            "audio_autoplay": False,
        }
    if use_cache:
        cache_set(key, result, ok=False, cache_dir=cache_dir, now=now)
    return result


def attach_playable_asset(
    item: dict[str, Any],
    *,
    fetcher: Fetcher | None = None,
    cache_dir: str | None = None,
    now: Optional[float] = None,
) -> dict[str, Any]:
    if not item or item.get("provider") != "nasa" or item.get("reuse_cosmic_signal"):
        return item
    if item.get("media_url") or item.get("media_type") not in {"video", "audio"}:
        return item
    nasa_id = item.get("nasa_id")
    if not nasa_id or not NASA_ID_RE.fullmatch(nasa_id):
        return item
    key = cache_key("nasa-asset", nasa_id, item.get("media_type"))
    cached = cache_get(key, cache_dir=cache_dir, now=now)
    files = (cached or {}).get("payload") if cached else None
    if not isinstance(files, dict):
        fetch = fetcher or _default_fetch
        try:
            files = parse_nasa_asset_files(fetch(f"{NASA_ASSET_BASE}{nasa_id}", REQUEST_TIMEOUT_SEC))
            cache_set(key, files, ok=True, cache_dir=cache_dir, now=now)
        except Exception:  # noqa: BLE001 - featured playback is optional
            files = {}
            cache_set(key, files, ok=False, cache_dir=cache_dir, now=now)
    updated = dict(item)
    if files.get("media_url"):
        updated["media_url"] = files["media_url"]
        updated["playable_inline"] = True
    if files.get("caption_url"):
        updated["caption_url"] = files["caption_url"]
        updated["caption_available"] = True
    if files.get("preview_url") and not updated.get("thumbnail_url"):
        updated["thumbnail_url"] = files["preview_url"]
        updated["preview_url"] = files["preview_url"]
    return normalize_media_item(updated)


def rank_items(items: list[dict[str, Any]], terms: dict[str, Any]) -> list[dict[str, Any]]:
    ranked: list[dict[str, Any]] = []
    reuse_ids = {i.get("cosmic_signal_id") for i in items if i.get("reuse_cosmic_signal")}
    for item in items:
        if item.get("reuse_cosmic_signal"):
            ranked.append(item)
            continue
        if item.get("provider") == "nasa" and item.get("signal_category") == "sonification" and reuse_ids:
            continue
        relation, confidence = classify_relation(item, terms)
        if not relation:
            continue
        copy = dict(item)
        copy["relation"] = relation
        copy["confidence"] = confidence
        copy["object_name"] = terms.get("primary") or copy.get("object_name")
        copy["object_aliases"] = list(terms.get("aliases") or [])
        copy["constellation"] = terms.get("constellation") or copy.get("constellation")
        ranked.append(normalize_media_item(copy))
    ranked = suppress_duplicates(ranked)
    order = {"exact": 0, "related": 1, "general": 2}
    ranked.sort(key=lambda i: (order.get(i.get("relation") or "general", 9), -(i.get("confidence") or 0)))
    return ranked


def _group(items: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    groups = {"exact": [], "related": [], "general": []}
    for item in items:
        key = item.get("relation") if item.get("relation") in groups else "related"
        groups[key].append(item)
    return groups


def media_context(
    selection: dict[str, Any] | None,
    *,
    object_name: str | None = None,
    media_type: str | None = None,
    fetcher: Fetcher | None = None,
    cache_dir: str | None = None,
    now: Optional[float] = None,
    include_nasa: bool = True,
) -> dict[str, Any]:
    terms = collect_object_terms(selection, object_name)
    curated = match_chandra(terms)
    nasa_items: list[dict[str, Any]] = []
    nasa_status = "skipped"
    nasa_error = None
    if include_nasa and terms.get("primary"):
        result = _search_with_fallback(terms, media_type=media_type, fetcher=fetcher, cache_dir=cache_dir, now=now)
        nasa_items = result.get("items") or []
        nasa_status = result.get("status")
        nasa_error = result.get("error")
    ranked = rank_items(curated + nasa_items, terms)
    if ranked and ranked[0].get("media_type") in {"video", "audio"}:
        ranked[0] = attach_playable_asset(ranked[0], fetcher=fetcher, cache_dir=cache_dir, now=now)
    groups = _group(ranked)
    featured = ranked[0] if ranked else None
    alternates = ranked[1 : 1 + STORY_ALTERNATES]
    empty = not ranked
    return {
        "ok": True,
        "status": "empty" if empty else "found",
        "object_name": terms.get("primary"),
        "constellation": terms.get("constellation"),
        "featured": featured,
        "alternates": alternates,
        "card_exact": groups["exact"][0] if groups["exact"] else None,
        "card_related": groups["related"][0] if groups["related"] else None,
        "exact": groups["exact"],
        "related": groups["related"],
        "general": groups["general"],
        "items": ranked[:MAX_ITEMS],
        "empty": empty,
        "empty_message": (
            "No authoritative official media is currently associated with this object."
            if empty
            else None
        ),
        "nasa_status": nasa_status,
        "error": nasa_error,
        "audio_autoplay": False,
        "cosmic_signal_ids": sorted(
            {i.get("cosmic_signal_id") for i in ranked if i.get("cosmic_signal_id")}
        ),
    }


def _search_with_fallback(
    terms: dict[str, Any],
    *,
    media_type: str | None,
    fetcher: Fetcher | None,
    cache_dir: str | None,
    now: Optional[float],
) -> dict[str, Any]:
    queries: list[tuple[str, str]] = []
    primary = terms.get("primary")
    if primary:
        queries.append((primary, "object"))
    for alias in (terms.get("aliases") or [])[:2]:
        if normalize_query(alias) != normalize_query(primary):
            queries.append((alias, "alias"))
    constellation = (terms.get("constellation_names") or [None])[0]
    if primary and constellation:
        queries.append((f"{primary} {constellation}", "combo"))
    collected: list[dict[str, Any]] = []
    last = {"ok": True, "status": "empty", "items": [], "error": None}
    for query, kind in queries:
        last = search_nasa(
            query,
            media_type=media_type,
            fetcher=fetcher,
            cache_dir=cache_dir,
            now=now,
        )
        items = last.get("items") or []
        if kind == "combo":
            for item in items:
                item.setdefault("_query_kind", kind)
        collected.extend(items)
        probe_terms = terms if kind != "combo" else terms
        ranked = rank_items(items, probe_terms)
        if any(item.get("relation") == "exact" for item in ranked):
            break
    if not collected and constellation:
        last = search_nasa(
            constellation,
            media_type=media_type,
            fetcher=fetcher,
            cache_dir=cache_dir,
            now=now,
        )
        collected.extend(last.get("items") or [])
    last = dict(last)
    last["items"] = collected
    return last


def search_media(
    query: str,
    *,
    object_name: str | None = None,
    media_type: str | None = None,
    selection: dict[str, Any] | None = None,
    fetcher: Fetcher | None = None,
    cache_dir: str | None = None,
    now: Optional[float] = None,
) -> dict[str, Any]:
    checked = validate_search_query(query)
    if not checked["ok"]:
        return {
            "ok": False,
            "status": "invalid",
            "error": checked["error"],
            "items": [],
            "audio_autoplay": False,
        }
    terms = collect_object_terms(selection, object_name or checked["query"])
    nasa = search_nasa(
        checked["query"],
        media_type=media_type,
        fetcher=fetcher,
        cache_dir=cache_dir,
        now=now,
    )
    ranked = rank_items(nasa.get("items") or [], terms)
    if not ranked and nasa.get("ok"):
        query_norm = normalize_query(checked["query"])
        for item in nasa.get("items") or []:
            hay = normalize_query(" ".join([item.get("title") or "", " ".join(item.get("keywords") or [])]))
            if query_norm and query_norm in hay:
                copy = dict(item)
                copy["relation"] = "related"
                copy["confidence"] = 0.4
                ranked.append(normalize_media_item(copy))
        ranked = suppress_duplicates(ranked)
    return {
        "ok": bool(nasa.get("ok")),
        "status": nasa.get("status"),
        "error": nasa.get("error"),
        "query": checked["query"],
        "media_type": media_type or "all",
        "items": ranked[:MAX_ITEMS],
        "empty": not ranked,
        "empty_message": None if ranked else "No object-relevant NASA media for this query.",
        "cache_hit": bool(nasa.get("cache_hit")),
        "audio_autoplay": False,
    }


def get_item(
    item_id: str | None,
    *,
    fetcher: Fetcher | None = None,
    cache_dir: str | None = None,
    now: Optional[float] = None,
) -> dict[str, Any]:
    if not item_id or not isinstance(item_id, str) or not ITEM_ID_RE.fullmatch(item_id.strip()):
        return {"ok": False, "error": "Malformed media id.", "item": None, "audio_autoplay": False}
    item_id = item_id.strip()
    provider, raw_id = item_id.split(":", 1)
    if provider == "chandra":
        for entry in chandra_entries():
            if entry.get("id") == raw_id:
                return {"ok": True, "item": _chandra_to_item(entry), "audio_autoplay": False}
        return {"ok": False, "error": "Unknown curated media id.", "item": None, "audio_autoplay": False}
    if provider == "cosmic":
        return {"ok": False, "error": "Use the Cosmic Signal Deck for this entry.", "item": None, "audio_autoplay": False}
    if provider == "nasa":
        if not NASA_ID_RE.fullmatch(raw_id):
            return {"ok": False, "error": "Malformed NASA id.", "item": None, "audio_autoplay": False}
        result = search_nasa(raw_id, fetcher=fetcher, cache_dir=cache_dir, now=now)
        for item in result.get("items") or []:
            if item.get("nasa_id") == raw_id:
                return {
                    "ok": True,
                    "item": attach_playable_asset(item, fetcher=fetcher, cache_dir=cache_dir, now=now),
                    "audio_autoplay": False,
                }
        return {"ok": False, "error": "NASA media item was not found.", "item": None, "audio_autoplay": False}
    return {"ok": False, "error": "Unknown media provider.", "item": None, "audio_autoplay": False}


def curated_narration_fields(selection: dict[str, Any] | None) -> dict[str, Any]:
    terms = collect_object_terms(selection)
    curated = match_chandra(terms)
    featured = next((item for item in curated if item.get("relation") == "exact"), None)
    return media_narration_fields(selection, featured)


def media_narration_fields(selection: dict[str, Any] | None, item: dict[str, Any] | None) -> dict[str, Any]:
    empty = {
        "official_media_title": None,
        "official_media_provider": None,
        "official_media_relation": None,
        "official_media_source_url": None,
        "official_media_note": None,
        "audio_autoplay": False,
    }
    if not item or item.get("relation") != "exact":
        return empty
    name = (selection or {}).get("name") or item.get("object_name") or "this object"
    kind = str(item.get("signal_category") or item.get("media_type") or "media").replace("_", " ")
    provider = item.get("provider_label") or item.get("provider") or "official source"
    if item.get("provider") == "nasa":
        note = (
            f"NASA's Image and Video Library contains official imagery of {name}. "
            "This spoken text is Cartography narration and is not official NASA narration."
        )
    elif "sonif" in kind:
        note = (
            f"There is an official {provider} sonification available for this object. "
            "You can play it from the Cosmic Signal Deck. "
            "This spoken text is Cartography narration and is not official NASA narration."
        )
    else:
        note = (
            f"There is official {provider} {kind} available for this object. "
            "This spoken text is Cartography narration and is not official NASA narration."
        )
    return {
        "official_media_title": item.get("title"),
        "official_media_provider": item.get("provider_label") or item.get("provider"),
        "official_media_relation": "exact",
        "official_media_source_url": item.get("source_page_url"),
        "official_media_note": note,
        "audio_autoplay": False,
    }


def cosmic_signal_entry_count() -> int:
    return len([e for e in cosmic_signal_registry.load_registry().get("entries") or [] if e.get("enabled")])
