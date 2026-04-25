from __future__ import annotations

import logging

import httpx

from app.collector.base import Collector, RawDocumentPayload
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
                    payloads.extend(parse_feed_items(feed_url, resp.text, self.limit_per_feed, "rss"))
                except Exception as exc:  # noqa: BLE001
                    log.warning("RSS parse failed for %s: %s", feed_url, exc)
                    continue

        return payloads
