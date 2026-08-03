"""
planetary_image.py

Server-side client for the R0.3 Planetary Image Pilot.

Uses the documented NASA Images and Video Library API
(https://images-api.nasa.gov/docs/) — a primary official NASA machine-readable
endpoint that requires no API key. PDS Search API was evaluated during R0.2
research but is unsuitable for this pilot: target-field queries returned empty
results and keyword search did not yield reliable browse imagery.

Only the three pilot targets (Moon, Jupiter, Saturn) are accepted. The local
server sends only the normalized target identifier to NASA; no Stellarium
metadata, local paths, or machine identity are included.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Callable, Optional

logger = logging.getLogger("stellar_archive_bridge.planetary_image")

NASA_IMAGES_SEARCH_URL = "https://images-api.nasa.gov/search"
NASA_IMAGES_DETAILS_BASE = "https://images.nasa.gov/details/"
REQUEST_TIMEOUT_SEC = 10
MAX_RESPONSE_BYTES = 512 * 1024

PILOT_TARGETS: dict[str, dict[str, str]] = {
    "moon": {"search_query": "Moon", "display_name": "Moon"},
    "jupiter": {"search_query": "Jupiter", "display_name": "Jupiter"},
    "saturn": {"search_query": "Saturn", "display_name": "Saturn"},
}

ALLOWED_IMAGE_HOSTS = frozenset({"images-assets.nasa.gov"})
ALLOWED_SOURCE_LINK_HOSTS = frozenset({"images.nasa.gov"})

_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_UNSAFE_URL_CHAR_RE = re.compile(r'[\s"\'<>]')


def _url_has_unsafe_characters(url: str) -> bool:
    return bool(_UNSAFE_URL_CHAR_RE.search(url))


def normalize_pilot_target_id(raw: str | None) -> str | None:
    """Return a pilot target id (moon|jupiter|saturn) or None."""
    if not raw or not isinstance(raw, str):
        return None
    key = raw.strip().lower()
    return key if key in PILOT_TARGETS else None


def is_allowed_image_url(url: str | None) -> bool:
    """Accept only expected HTTPS NASA asset URLs."""
    if not url or not isinstance(url, str):
        return False
    if _url_has_unsafe_characters(url):
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
    return host in ALLOWED_IMAGE_HOSTS


def is_allowed_source_link(url: str | None) -> bool:
    """Accept only official NASA Images details pages."""
    if not url or not isinstance(url, str):
        return False
    if _url_has_unsafe_characters(url):
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
    if host not in ALLOWED_SOURCE_LINK_HOSTS:
        return False
    return parsed.path.startswith("/details/")


def sanitize_text(value: object, max_len: int = 500) -> str | None:
    """Treat remote metadata as untrusted plain text."""
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    text = _CONTROL_CHAR_RE.sub("", value.strip())
    if not text:
        return None
    if len(text) > max_len:
        text = text[: max_len - 1] + "…"
    return text


def _pick_image_link(links: list[dict] | None) -> str | None:
    if not links:
        return None
    preferred_rels = ("preview", "canonical", "alternate")
    for rel in preferred_rels:
        for link in links:
            if not isinstance(link, dict):
                continue
            if link.get("rel") != rel:
                continue
            href = link.get("href")
            if is_allowed_image_url(href):
                return href
    for link in links:
        if isinstance(link, dict) and is_allowed_image_url(link.get("href")):
            return link.get("href")
    return None


def _extract_keywords(data: dict) -> str | None:
    keywords = data.get("keywords")
    if not isinstance(keywords, list):
        return None
    cleaned = []
    for kw in keywords:
        text = sanitize_text(kw, max_len=80)
        if text:
            cleaned.append(text)
    if not cleaned:
        return None
    return ", ".join(cleaned[:8])


def _extract_nasa_center(data: dict) -> str | None:
    return sanitize_text(data.get("center"), max_len=80)


def _build_result(
    *,
    ok: bool,
    status: str,
    target_id: str | None = None,
    target_name: str | None = None,
    image_url: str | None = None,
    title: str | None = None,
    description: str | None = None,
    mission: str | None = None,
    nasa_center: str | None = None,
    keywords: str | None = None,
    instrument: str | None = None,
    image_date: str | None = None,
    source_agency: str = "NASA",
    credit: str | None = None,
    source_link: str | None = None,
    error: str | None = None,
) -> dict:
    return {
        "ok": ok,
        "status": status,
        "target_id": target_id,
        "target_name": target_name,
        "image_url": image_url if is_allowed_image_url(image_url) else None,
        "title": sanitize_text(title),
        "description": sanitize_text(description),
        "mission": sanitize_text(mission),
        "nasa_center": sanitize_text(nasa_center),
        "keywords": sanitize_text(keywords),
        "instrument": sanitize_text(instrument),
        "image_date": sanitize_text(image_date, max_len=40),
        "source_agency": sanitize_text(source_agency, max_len=40) or "NASA",
        "credit": sanitize_text(credit),
        "source_link": source_link if is_allowed_source_link(source_link) else None,
        "error": sanitize_text(error, max_len=200),
        "archive_notice": (
            "This is an archived NASA outreach image, not a live view. "
            "It does not show the current date, phase, orientation, or appearance "
            "at the Stellarium coordinates. It was not produced by Stellarium or ESASky."
        ),
    }


def parse_nasa_images_response(payload: dict, target_id: str) -> dict:
    """Normalize a NASA Images API search JSON body into a pilot result."""
    cfg = PILOT_TARGETS.get(target_id)
    if not cfg:
        return _build_result(ok=False, status="error", error="Unknown pilot target.")

    if not isinstance(payload, dict):
        return _build_result(
            ok=False,
            status="malformed",
            target_id=target_id,
            target_name=cfg["display_name"],
            error="Archive service returned an unexpected response.",
        )

    collection = payload.get("collection")
    if not isinstance(collection, dict):
        return _build_result(
            ok=False,
            status="malformed",
            target_id=target_id,
            target_name=cfg["display_name"],
            error="Archive service returned an unexpected response.",
        )

    items = collection.get("items")
    if not isinstance(items, list) or not items:
        return _build_result(
            ok=True,
            status="unavailable",
            target_id=target_id,
            target_name=cfg["display_name"],
            error="No suitable NASA archive image was found for this pilot target.",
        )

    for item in items:
        if not isinstance(item, dict):
            continue
        data_list = item.get("data")
        if not isinstance(data_list, list) or not data_list:
            continue
        data = data_list[0]
        if not isinstance(data, dict):
            continue

        image_url = _pick_image_link(item.get("links"))
        if not image_url:
            continue

        nasa_id = sanitize_text(data.get("nasa_id"), max_len=40)
        source_link = f"{NASA_IMAGES_DETAILS_BASE}{nasa_id}" if nasa_id else None
        credit = sanitize_text(data.get("secondary_creator")) or sanitize_text(data.get("photographer"))

        return _build_result(
            ok=True,
            status="found",
            target_id=target_id,
            target_name=cfg["display_name"],
            image_url=image_url,
            title=sanitize_text(data.get("title")) or cfg["display_name"],
            description=sanitize_text(data.get("description")),
            mission=None,
            nasa_center=_extract_nasa_center(data),
            keywords=_extract_keywords(data),
            instrument=None,
            image_date=sanitize_text(data.get("date_created"), max_len=40),
            source_agency="NASA",
            credit=credit,
            source_link=source_link,
        )

    return _build_result(
        ok=True,
        status="unavailable",
        target_id=target_id,
        target_name=cfg["display_name"],
        error="No suitable NASA archive image with a permitted HTTPS URL was found.",
    )


def _default_fetch(url: str, timeout: float) -> dict:
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "FOXAI-StellarCartography/0.3"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise ValueError("Response too large")
        return json.loads(raw.decode("utf-8"))


def lookup_planetary_image(
    target_id: str,
    fetcher: Optional[Callable[[str, float], dict]] = None,
    timeout: float = REQUEST_TIMEOUT_SEC,
) -> dict:
    """Look up an official NASA archive image for a pilot target id."""
    normalized = normalize_pilot_target_id(target_id)
    if not normalized:
        return _build_result(ok=False, status="unsupported", error="Target is not in the R0.3 pilot set.")

    cfg = PILOT_TARGETS[normalized]
    params = urllib.parse.urlencode(
        {
            "q": cfg["search_query"],
            "media_type": "image",
            "page_size": "5",
        }
    )
    url = f"{NASA_IMAGES_SEARCH_URL}?{params}"
    fetch = fetcher or _default_fetch

    try:
        payload = fetch(url, timeout)
    except TimeoutError:
        logger.info("Planetary image lookup timed out for target=%s", normalized)
        return _build_result(
            ok=False,
            status="timeout",
            target_id=normalized,
            target_name=cfg["display_name"],
            error="NASA archive service did not respond in time.",
        )
    except urllib.error.HTTPError as exc:
        logger.info("Planetary image HTTP error for target=%s code=%s", normalized, exc.code)
        return _build_result(
            ok=False,
            status="http_error",
            target_id=normalized,
            target_name=cfg["display_name"],
            error=f"NASA archive service returned HTTP {exc.code}.",
        )
    except (urllib.error.URLError, OSError, json.JSONDecodeError, ValueError):
        logger.info("Planetary image lookup failed for target=%s", normalized, exc_info=True)
        return _build_result(
            ok=False,
            status="error",
            target_id=normalized,
            target_name=cfg["display_name"],
            error="Could not retrieve a NASA archive image at this time.",
        )

    return parse_nasa_images_response(payload, normalized)
