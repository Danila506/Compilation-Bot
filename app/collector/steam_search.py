from __future__ import annotations

from html import unescape
import logging
import re

import httpx

from app.collector.base import Collector, RawDocumentPayload

log = logging.getLogger(__name__)


class SteamSearchCollector(Collector):
    source_type = "steam_search"
    source_name = "Steam Store Search"

    def __init__(self, queries: list[str], limit_per_query: int = 10):
        self.queries = queries
        self.limit_per_query = limit_per_query

    async def collect(self) -> list[RawDocumentPayload]:
        if not self.queries:
            return []

        payloads: list[RawDocumentPayload] = []
        headers = {"User-Agent": "game-mech-monitor-bot/0.1"}
        app_link_re = re.compile(
            r'href="https://store\.steampowered\.com/app/(\d+)/[^"]*".*?<span class="title">([^<]+)</span>',
            re.IGNORECASE | re.DOTALL,
        )

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, headers=headers) as client:
            for query in self.queries:
                params = {
                    "query": query,
                    "start": 0,
                    "count": max(1, self.limit_per_query),
                    "dynamic_data": "",
                    "sort_by": "_ASC",
                    "supportedlang": "english",
                    "infinite": 1,
                }
                url = "https://store.steampowered.com/search/results/"
                try:
                    resp = await client.get(url, params=params)
                    resp.raise_for_status()
                    data = resp.json()
                except Exception as exc:  # noqa: BLE001
                    log.warning("Steam search failed for query=%s: %s", query, exc)
                    continue

                html = data.get("results_html", "")
                if not html:
                    continue

                found = app_link_re.findall(html)
                for app_id, raw_title in found[: max(1, self.limit_per_query)]:
                    title = unescape(raw_title.strip())
                    app_url = f"https://store.steampowered.com/app/{app_id}/"
                    payloads.append(
                        RawDocumentPayload(
                            external_id=f"steam_search:{query}:{app_id}",
                            url=app_url,
                            title=title or f"Steam app {app_id}",
                            content=f"Steam search match for query: {query}",
                            meta={"query": query, "appid": int(app_id)},
                        )
                    )
        return payloads

