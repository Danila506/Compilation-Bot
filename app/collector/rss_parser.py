from __future__ import annotations

from datetime import datetime
from email.utils import parsedate_to_datetime
import re
from typing import Any
from xml.etree import ElementTree as ET

from app.collector.base import RawDocumentPayload


def _first_image_url(*values: str | None) -> str:
    for value in values:
        if not value:
            continue
        match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', value, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        if value.startswith("http") and any(ext in value.lower() for ext in [".jpg", ".jpeg", ".png", ".webp"]):
            return value.strip()
    return ""


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            return parsedate_to_datetime(value)
        except Exception:  # noqa: BLE001
            return None


def parse_feed_items(feed_url: str, feed_text: str, limit_per_feed: int, source_prefix: str) -> list[RawDocumentPayload]:
    root = ET.fromstring(feed_text)
    payloads: list[RawDocumentPayload] = []

    rss_items = root.findall("./channel/item")
    if rss_items:
        for item in rss_items[: max(1, limit_per_feed)]:
            title = (item.findtext("title") or "").strip()
            url = (item.findtext("link") or "").strip()
            guid = (item.findtext("guid") or url or title).strip()
            content = (item.findtext("description") or "").strip()
            published_at = parse_datetime(item.findtext("pubDate"))
            enclosure = item.find("enclosure")
            enclosure_url = enclosure.attrib.get("url", "") if enclosure is not None else ""
            media_content = item.find("{http://search.yahoo.com/mrss/}content")
            media_thumbnail = item.find("{http://search.yahoo.com/mrss/}thumbnail")
            media_url = media_content.attrib.get("url", "") if media_content is not None else ""
            thumbnail_url = media_thumbnail.attrib.get("url", "") if media_thumbnail is not None else ""
            image_url = _first_image_url(thumbnail_url, media_url, enclosure_url, content)
            if not guid or not url:
                continue
            payloads.append(
                RawDocumentPayload(
                    external_id=f"{source_prefix}:{feed_url}:{guid}",
                    url=url,
                    title=title or "RSS item",
                    content=content,
                    published_at=published_at,
                    meta={"feed_url": feed_url, "image_url": image_url},
                )
            )
        return payloads

    ns: dict[str, Any] = {"atom": "http://www.w3.org/2005/Atom"}
    entries = root.findall("atom:entry", ns)
    for entry in entries[: max(1, limit_per_feed)]:
        title = (entry.findtext("atom:title", default="", namespaces=ns) or "").strip()
        link_el = entry.find("atom:link", ns)
        url = link_el.attrib.get("href", "").strip() if link_el is not None else ""
        guid = (entry.findtext("atom:id", default="", namespaces=ns) or url or title).strip()
        summary = (entry.findtext("atom:summary", default="", namespaces=ns) or "").strip()
        content = (entry.findtext("atom:content", default="", namespaces=ns) or summary).strip()
        media_thumbnail = entry.find("{http://search.yahoo.com/mrss/}thumbnail")
        thumbnail_url = media_thumbnail.attrib.get("url", "") if media_thumbnail is not None else ""
        image_url = _first_image_url(thumbnail_url, content, summary)
        published = entry.findtext("atom:published", default="", namespaces=ns) or entry.findtext(
            "atom:updated",
            default="",
            namespaces=ns,
        )
        published_at = parse_datetime(published)
        if not guid or not url:
            continue
        payloads.append(
            RawDocumentPayload(
                external_id=f"{source_prefix}:{feed_url}:{guid}",
                url=url,
                title=title or "Atom entry",
                content=content,
                published_at=published_at,
                meta={"feed_url": feed_url, "image_url": image_url},
            )
        )
    return payloads
