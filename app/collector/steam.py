from __future__ import annotations

from datetime import datetime, timezone
import logging
import time

import httpx

from app.collector.base import Collector, RawDocumentPayload

log = logging.getLogger(__name__)


class SteamCollector(Collector):
    source_type = "steam"
    source_name = "Steam News API"

    def __init__(
        self,
        app_ids: list[int],
        news_count_per_app: int = 5,
        lookback_days: int = 730,
        historical_max_pages: int = 10,
    ):
        self.app_ids = app_ids
        self.news_count_per_app = news_count_per_app
        self.lookback_days = max(1, lookback_days)
        self.historical_max_pages = max(1, historical_max_pages)

    async def collect(self) -> list[RawDocumentPayload]:
        if not self.app_ids:
            return []

        payloads: list[RawDocumentPayload] = []
        now_ts = int(time.time())
        cutoff_ts = now_ts - (self.lookback_days * 24 * 60 * 60)
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            for app_id in self.app_ids:
                enddate = now_ts
                for _ in range(self.historical_max_pages):
                    url = (
                        "https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/"
                        f"?appid={app_id}&count={max(20, self.news_count_per_app)}"
                        f"&maxlength=12000&format=json&enddate={enddate}"
                    )
                    try:
                        response = await client.get(url)
                        response.raise_for_status()
                        data = response.json()
                    except Exception as exc:  # noqa: BLE001
                        log.warning("Steam fetch failed for appid=%s: %s", app_id, exc)
                        break

                    items = data.get("appnews", {}).get("newsitems", [])
                    if not items:
                        break

                    oldest_ts = enddate
                    reached_cutoff = False
                    for item in items:
                        gid = item.get("gid")
                        if not gid:
                            continue

                        ts = item.get("date")
                        if not isinstance(ts, (int, float)):
                            continue
                        ts_int = int(ts)
                        oldest_ts = min(oldest_ts, ts_int)
                        if ts_int < cutoff_ts:
                            reached_cutoff = True
                            continue

                        published_at = datetime.fromtimestamp(ts_int, tz=timezone.utc)
                        title = (item.get("title") or "").strip()
                        content = item.get("contents") or ""
                        item_url = item.get("url") or f"https://store.steampowered.com/news/app/{app_id}"

                        payloads.append(
                            RawDocumentPayload(
                                external_id=f"{app_id}:{gid}",
                                url=item_url,
                                title=title or f"Steam app {app_id} update",
                                content=content,
                                author=item.get("author"),
                                published_at=published_at,
                                meta={
                                    "appid": app_id,
                                    "feedlabel": item.get("feedlabel"),
                                    "feedname": item.get("feedname"),
                                    "tags": item.get("tags", []),
                                },
                            )
                        )

                    if reached_cutoff or oldest_ts >= enddate:
                        break
                    enddate = oldest_ts - 1
        return payloads
