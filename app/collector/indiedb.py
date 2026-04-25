from __future__ import annotations

import logging
from urllib.parse import urlparse

import httpx

from app.collector.base import Collector, RawDocumentPayload
from app.collector.page_enricher import fetch_page_info
from app.collector.rss_parser import parse_feed_items

log = logging.getLogger(__name__)


class IndieDBCollector(Collector):
    source_type = "indiedb"
    source_name = "IndieDB Feeds"

    def __init__(self, feed_urls: list[str], limit_per_feed: int = 20):
        self.feed_urls = feed_urls
        self.limit_per_feed = limit_per_feed

    async def collect(self) -> list[RawDocumentPayload]:
        if not self.feed_urls:
            return []

        payloads: list[RawDocumentPayload] = []
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "application/rss+xml, application/xml, text/xml;q=0.9, */*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, headers=headers) as client:
            for feed_url in self.feed_urls:
                try:
                    host = urlparse(feed_url).scheme + "://" + urlparse(feed_url).netloc
                    request_headers = {
                        **headers,
                        "Referer": host + "/",
                    }
                    resp = await client.get(feed_url, headers=request_headers)
                    if resp.status_code == 403:
                        # Retry once with a different UA, some IndieDB edges are strict.
                        request_headers["User-Agent"] = "Mozilla/5.0 (compatible; IndieDBFeedBot/1.0)"
                        resp = await client.get(feed_url, headers=request_headers)
                    resp.raise_for_status()
                    items = parse_feed_items(feed_url, resp.text, self.limit_per_feed, "indiedb")
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
                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code == 403:
                        log.info("IndieDB blocked feed %s (403), skipping", feed_url)
                    else:
                        log.warning("IndieDB feed failed for %s: %s", feed_url, exc)
                except Exception as exc:  # noqa: BLE001
                    log.warning("IndieDB feed failed for %s: %s", feed_url, exc)
                    continue

        return payloads
