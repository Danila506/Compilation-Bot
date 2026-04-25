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

    async def _app_details(self, client: httpx.AsyncClient, app_id: str) -> dict:
        resp = await client.get(
            "https://store.steampowered.com/api/appdetails",
            params={"appids": app_id, "filters": "basic,genres,categories"},
        )
        resp.raise_for_status()
        data = resp.json().get(str(app_id), {})
        if not data.get("success"):
            return {}
        return data.get("data", {}) or {}

    @staticmethod
    def _looks_2d_relevant(details: dict) -> bool:
        text = " ".join(
            [
                str(details.get("name") or ""),
                str(details.get("short_description") or ""),
                " ".join(g.get("description", "") for g in details.get("genres", []) if isinstance(g, dict)),
                " ".join(c.get("description", "") for c in details.get("categories", []) if isinstance(c, dict)),
            ]
        ).lower()
        positive = ["2d", "top-down", "top down", "isometric", "pixel", "survival", "craft", "zombie"]
        negative = ["hero shooter", "pvp", "moba", "vr", "sports", "racing"]
        return any(marker in text for marker in positive) and not any(marker in text for marker in negative)

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
                    try:
                        details = await self._app_details(client, app_id)
                    except Exception as exc:  # noqa: BLE001
                        log.warning("Steam appdetails failed for appid=%s: %s", app_id, exc)
                        continue
                    if not self._looks_2d_relevant(details):
                        continue
                    content = " ".join(
                        value
                        for value in [
                            details.get("name", ""),
                            details.get("short_description", ""),
                            " ".join(
                                g.get("description", "") for g in details.get("genres", []) if isinstance(g, dict)
                            ),
                            " ".join(
                                c.get("description", "") for c in details.get("categories", []) if isinstance(c, dict)
                            ),
                        ]
                        if value
                    )
                    payloads.append(
                        RawDocumentPayload(
                            external_id=f"steam_search:{query}:{app_id}",
                            url=app_url,
                            title=title or details.get("name") or f"Steam app {app_id}",
                            content=content,
                            meta={
                                "query": query,
                                "appid": int(app_id),
                                "image_url": details.get("header_image", ""),
                            },
                        )
                    )
        return payloads
