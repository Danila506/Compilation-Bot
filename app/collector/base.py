from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class RawDocumentPayload:
    external_id: str
    url: str
    title: str
    content: str = ""
    author: str | None = None
    published_at: datetime | None = None
    meta: dict = field(default_factory=dict)


class Collector:
    source_type: str = "unknown"
    source_name: str = "unknown"

    async def collect(self) -> list[RawDocumentPayload]:
        return []

