from __future__ import annotations

from datetime import datetime, timezone
import logging

import httpx

from app.collector.base import Collector, RawDocumentPayload

log = logging.getLogger(__name__)


class RedditCollector(Collector):
    source_type = "reddit"
    source_name = "Reddit"

    def __init__(
        self,
        subreddits: list[str],
        limit_per_subreddit: int = 10,
        client_id: str = "",
        client_secret: str = "",
        user_agent: str = "game-mech-monitor-bot/0.1 (+https://example.local)",
    ):
        self.subreddits = subreddits
        self.limit_per_subreddit = limit_per_subreddit
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_agent = user_agent

    async def _oauth_token(self, client: httpx.AsyncClient) -> str:
        if not self.client_id or not self.client_secret:
            return ""
        response = await client.post(
            "https://www.reddit.com/api/v1/access_token",
            auth=(self.client_id, self.client_secret),
            data={"grant_type": "client_credentials"},
            headers={"User-Agent": self.user_agent},
        )
        response.raise_for_status()
        return response.json().get("access_token", "")

    async def collect(self) -> list[RawDocumentPayload]:
        if not self.subreddits:
            return []

        payloads: list[RawDocumentPayload] = []
        headers = {"User-Agent": self.user_agent}

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, headers=headers) as client:
            access_token = ""
            if self.client_id and self.client_secret:
                try:
                    access_token = await self._oauth_token(client)
                except Exception as exc:  # noqa: BLE001
                    log.warning("Reddit OAuth token request failed, fallback to public endpoint: %s", exc)

            for subreddit in self.subreddits:
                if access_token:
                    url = f"https://oauth.reddit.com/r/{subreddit}/new?limit={self.limit_per_subreddit}"
                    request_headers = {"Authorization": f"Bearer {access_token}"}
                else:
                    url = f"https://www.reddit.com/r/{subreddit}/new.json?limit={self.limit_per_subreddit}"
                    request_headers = {}
                try:
                    response = await client.get(url, headers=request_headers)
                    response.raise_for_status()
                    data = response.json()
                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code == 403:
                        log.info("Reddit blocked r/%s with 403, skipping", subreddit)
                    else:
                        log.warning("Reddit fetch failed for r/%s: %s", subreddit, exc)
                    continue
                except Exception as exc:  # noqa: BLE001
                    log.warning("Reddit fetch failed for r/%s: %s", subreddit, exc)
                    continue

                children = data.get("data", {}).get("children", [])
                for item in children:
                    post = item.get("data", {})
                    post_id = post.get("id")
                    if not post_id:
                        continue

                    created_utc = post.get("created_utc")
                    published_at = None
                    if isinstance(created_utc, (int, float)):
                        published_at = datetime.fromtimestamp(created_utc, tz=timezone.utc)

                    permalink = post.get("permalink", "")
                    full_url = f"https://www.reddit.com{permalink}" if permalink else post.get("url", "")
                    title = post.get("title", "").strip()
                    selftext = post.get("selftext", "") or ""

                    payloads.append(
                        RawDocumentPayload(
                            external_id=f"{subreddit}:{post_id}",
                            url=full_url,
                            title=title or f"r/{subreddit} post {post_id}",
                            content=selftext,
                            author=post.get("author"),
                            published_at=published_at,
                            meta={
                                "subreddit": subreddit,
                                "score": post.get("score"),
                                "num_comments": post.get("num_comments"),
                                "link_flair_text": post.get("link_flair_text"),
                            },
                        )
                    )
        return payloads
