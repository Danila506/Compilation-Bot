from __future__ import annotations

import logging

import httpx

from app.collector.base import Collector, RawDocumentPayload
from app.collector.page_enricher import fetch_page_info
from app.collector.rss_parser import parse_feed_items

log = logging.getLogger(__name__)


class RssCollector(Collector):
    source_type = "rss"
    source_name = "RSS/News"

    def __init__(self, feed_urls: list[str], limit_per_feed: int = 20):
        self.feed_urls = feed_urls
        self.limit_per_feed = limit_per_feed

    async def collect(self) -> list[RawDocumentPayload]:
        if not self.feed_urls:
            return []

        payloads: list[RawDocumentPayload] = []
        headers = {"User-Agent": "game-mech-monitor-bot/0.1"}

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, headers=headers) as client:
            for feed_url in self.feed_urls:
                try:
                    resp = await client.get(feed_url)
                    resp.raise_for_status()
                except Exception as exc:  # noqa: BLE001
                    log.warning("RSS fetch failed for %s: %s", feed_url, exc)
                    continue

                try:
                    items = parse_feed_items(feed_url, resp.text, self.limit_per_feed, "rss")
                    for item in items:
                        try:
                            page = await fetch_page_info(client, item.url)
                        except Exception:
                            page = {}
                        if page:
                            item.content = " ".join(
                                value for value in [item.content, page.get("text", "")] if value
                            )[:12000]
                            item.meta["image_url"] = item.meta.get("image_url") or page.get("image_url", "")
                        payloads.append(item)
                except Exception as exc:  # noqa: BLE001
                    log.warning("RSS parse failed for %s: %s", feed_url, exc)
                    continue

        return payloads
