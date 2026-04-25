from __future__ import annotations

from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any
from xml.etree import ElementTree as ET

from app.collector.base import RawDocumentPayload


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
            if not guid or not url:
                continue
            payloads.append(
                RawDocumentPayload(
                    external_id=f"{source_prefix}:{feed_url}:{guid}",
                    url=url,
                    title=title or "RSS item",
                    content=content,
                    published_at=published_at,
                    meta={"feed_url": feed_url},
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
                meta={"feed_url": feed_url},
            )
        )
    return payloads

