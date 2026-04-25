from __future__ import annotations

from datetime import datetime
from email.utils import parsedate_to_datetime
import logging
from xml.etree import ElementTree as ET

import httpx

from app.collector.base import Collector, RawDocumentPayload

log = logging.getLogger(__name__)


class YouTubeCollector(Collector):
    source_type = "youtube"
    source_name = "YouTube RSS"

    def __init__(self, channel_ids: list[str], limit_per_channel: int = 10):
        self.channel_ids = channel_ids
        self.limit_per_channel = limit_per_channel

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            try:
                return parsedate_to_datetime(value)
            except Exception:  # noqa: BLE001
                return None

    async def collect(self) -> list[RawDocumentPayload]:
        if not self.channel_ids:
            return []

        payloads: list[RawDocumentPayload] = []
        ns = {"atom": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
        headers = {"User-Agent": "game-mech-monitor-bot/0.1"}

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, headers=headers) as client:
            for channel_id in self.channel_ids:
                feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
                try:
                    resp = await client.get(feed_url)
                    resp.raise_for_status()
                except Exception as exc:  # noqa: BLE001
                    log.warning("YouTube RSS fetch failed for channel_id=%s: %s", channel_id, exc)
                    continue

                try:
                    root = ET.fromstring(resp.text)
                except Exception as exc:  # noqa: BLE001
                    log.warning("YouTube RSS parse failed for channel_id=%s: %s", channel_id, exc)
                    continue

                entries = root.findall("atom:entry", ns)[: max(1, self.limit_per_channel)]
                for entry in entries:
                    video_id = entry.findtext("yt:videoId", default="", namespaces=ns)
                    link_el = entry.find("atom:link", ns)
                    href = link_el.attrib.get("href", "") if link_el is not None else ""
                    title = entry.findtext("atom:title", default="", namespaces=ns).strip()
                    author = entry.findtext("atom:author/atom:name", default="", namespaces=ns)
                    published_at = self._parse_datetime(
                        entry.findtext("atom:published", default="", namespaces=ns)
                    )

                    if not video_id and not href:
                        continue
                    payloads.append(
                        RawDocumentPayload(
                            external_id=f"{channel_id}:{video_id or href}",
                            url=href or f"https://www.youtube.com/watch?v={video_id}",
                            title=title or f"YouTube video {video_id}",
                            content="",
                            author=author or None,
                            published_at=published_at,
                            meta={"channel_id": channel_id, "video_id": video_id},
                        )
                    )
        return payloads
