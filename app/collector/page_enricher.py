from __future__ import annotations

from html import unescape
import re
from urllib.parse import urljoin

import httpx

from app.analyzer.normalize import clean_text


def _meta_content(html: str, key: str) -> str:
    patterns = [
        rf'<meta[^>]+property=["\']{re.escape(key)}["\'][^>]+content=["\']([^"\']+)["\']',
        rf'<meta[^>]+name=["\']{re.escape(key)}["\'][^>]+content=["\']([^"\']+)["\']',
        rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']{re.escape(key)}["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
        if match:
            return unescape(match.group(1)).strip()
    return ""


def _first_image(html: str, base_url: str) -> str:
    for key in ["og:image", "twitter:image"]:
        value = _meta_content(html, key)
        if value:
            return urljoin(base_url, value)
    match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', html, re.IGNORECASE)
    if match:
        return urljoin(base_url, match.group(1).strip())
    return ""


def extract_page_info(html: str, base_url: str) -> dict:
    title = _meta_content(html, "og:title") or _meta_content(html, "twitter:title")
    description = (
        _meta_content(html, "og:description")
        or _meta_content(html, "twitter:description")
        or _meta_content(html, "description")
    )
    body = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", html, flags=re.IGNORECASE | re.DOTALL)
    article_match = re.search(r"<article[^>]*>(.*?)</article>", body, re.IGNORECASE | re.DOTALL)
    body_text = clean_text(article_match.group(1) if article_match else body)
    pieces = [title, description, body_text[:6000]]
    return {
        "title": clean_text(title),
        "description": clean_text(description),
        "text": clean_text(" ".join(piece for piece in pieces if piece)),
        "image_url": _first_image(html, base_url),
    }


async def fetch_page_info(client: httpx.AsyncClient, url: str) -> dict:
    response = await client.get(url)
    response.raise_for_status()
    content_type = response.headers.get("content-type", "")
    if "html" not in content_type and "text" not in content_type:
        return {}
    return extract_page_info(response.text, str(response.url))
