from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from app.analyzer.normalize import clean_text
from app.analyzer.rule_analyzer import RuleAnalyzer
from app.collector.base import Collector, RawDocumentPayload
from app.collector.itch import ItchCollector
from app.collector.indiedb import IndieDBCollector
from app.collector.reddit import RedditCollector
from app.collector.rss import RssCollector
from app.collector.steam import SteamCollector
from app.collector.steam_search import SteamSearchCollector
from app.collector.youtube import YouTubeCollector
from app.dedup.canonical import canonicalize_url
from app.dedup.fingerprints import content_hash, tiny_simhash
from app.notifier.telegram_bot import TelegramNotifier
from app.scorer.rule_scorer import RuleScorer
from app.storage.repositories import DedupRepo, DocumentRepo, ProfileRepo, ScoreRepo, SentRepo, SourceRepo

log = logging.getLogger(__name__)


class MockCollector(Collector):
    source_type = "mock"
    source_name = "Mock Devlog Source"

    async def collect(self) -> list[RawDocumentPayload]:
        return [
            RawDocumentPayload(
                external_id="mock-1",
                url="https://example.com/devlog-1?utm_source=test",
                title="Devlog: noise attracting enemies and stealth update",
                content=(
                    "We changed AI reaction to sound and visibility. "
                    "Added drag and drop inventory with equipment slots."
                ),
                author="demo",
                published_at=datetime.now(timezone.utc),
            )
        ]


async def run_pipeline_once(
    session,
    telegram_token: str,
    telegram_chat_id: str,
    threshold: float,
    reddit_subreddits: list[str],
    reddit_limit_per_subreddit: int,
    reddit_client_id: str,
    reddit_client_secret: str,
    reddit_user_agent: str,
    steam_app_ids: list[int],
    steam_news_count_per_app: int,
    steam_historical_max_pages: int,
    steam_search_queries: list[str],
    steam_search_limit_per_query: int,
    youtube_channel_ids: list[str],
    youtube_limit_per_channel: int,
    rss_feed_urls: list[str],
    rss_limit_per_feed: int,
    itch_devlog_feed_urls: list[str],
    itch_limit_per_feed: int,
    indiedb_feed_urls: list[str],
    indiedb_limit_per_feed: int,
    lookback_days: int,
    prefer_2d_only: bool,
    min_2d_signal_score: float,
    use_mock_collector: bool = False,
    game_profile_name: str = "2D top-down survival",
    game_profile_description: str = "Default profile for survival mechanics discovery.",
    game_profile_tags: list[str] | None = None,
    game_profile_mechanic_weights: dict | None = None,
    game_profile_negative_keywords: list[str] | None = None,
):
    collectors: list[Collector] = []
    if reddit_subreddits:
        collectors.append(
            RedditCollector(
                subreddits=reddit_subreddits,
                limit_per_subreddit=reddit_limit_per_subreddit,
                client_id=reddit_client_id,
                client_secret=reddit_client_secret,
                user_agent=reddit_user_agent,
            )
        )
    if steam_app_ids:
        collectors.append(
            SteamCollector(
                app_ids=steam_app_ids,
                news_count_per_app=steam_news_count_per_app,
                lookback_days=lookback_days,
                historical_max_pages=steam_historical_max_pages,
            )
        )
    if steam_search_queries:
        collectors.append(
            SteamSearchCollector(
                queries=steam_search_queries,
                limit_per_query=steam_search_limit_per_query,
            )
        )
    if youtube_channel_ids:
        collectors.append(
            YouTubeCollector(
                channel_ids=youtube_channel_ids,
                limit_per_channel=youtube_limit_per_channel,
            )
        )
    if rss_feed_urls:
        collectors.append(
            RssCollector(
                feed_urls=rss_feed_urls,
                limit_per_feed=rss_limit_per_feed,
            )
        )
    if itch_devlog_feed_urls:
        collectors.append(
            ItchCollector(
                feed_urls=itch_devlog_feed_urls,
                limit_per_feed=itch_limit_per_feed,
            )
        )
    if indiedb_feed_urls:
        collectors.append(
            IndieDBCollector(
                feed_urls=indiedb_feed_urls,
                limit_per_feed=indiedb_limit_per_feed,
            )
        )
    if use_mock_collector:
        collectors.append(MockCollector())

    analyzer = RuleAnalyzer()
    scorer = RuleScorer(
        threshold=threshold,
        prefer_2d_only=prefer_2d_only,
        min_2d_signal_score=min_2d_signal_score,
    )
    notifier = TelegramNotifier(token=telegram_token, chat_id=telegram_chat_id)

    source_repo = SourceRepo(session)
    doc_repo = DocumentRepo(session)
    profile_repo = ProfileRepo(session)
    dedup_repo = DedupRepo(session)
    score_repo = ScoreRepo(session)
    sent_repo = SentRepo(session)

    profile = profile_repo.get_default_profile(
        name=game_profile_name,
        description=game_profile_description,
        tags=game_profile_tags or [],
        mechanic_weights=game_profile_mechanic_weights or {},
        negative_keywords=game_profile_negative_keywords or [],
    )
    profile_text = " ".join(
        [
            profile.name or "",
            profile.description or "",
            " ".join(profile.tags_json or []),
            " ".join((profile.mechanic_weights_json or {}).keys()),
        ]
    )
    cutoff_dt = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=max(1, lookback_days))
    total_collected = 0
    total_new_raw = 0
    total_dedup_skipped = 0
    total_relevant = 0
    total_sent = 0

    for collector in collectors:
        source = source_repo.get_or_create(collector.source_type, collector.source_name)
        collector_payloads = await collector.collect()
        total_collected += len(collector_payloads)
        log.info(
            "Collector=%s type=%s collected=%s",
            collector.source_name,
            collector.source_type,
            len(collector_payloads),
        )
        for payload in collector_payloads:
            if payload.published_at:
                payload_dt = payload.published_at.astimezone(timezone.utc).replace(tzinfo=None)
                if payload_dt < cutoff_dt:
                    continue
            if doc_repo.raw_exists(source.id, payload.external_id):
                continue

            raw_row = doc_repo.insert_raw(source.id, payload)
            total_new_raw += 1
            text_clean = clean_text(payload.content)
            normalized_row = doc_repo.insert_normalized(
                raw_id=raw_row.id,
                canonical_url=canonicalize_url(payload.url),
                title_clean=clean_text(payload.title),
                text_clean=text_clean,
                lang="en",
                tokens_count=len(text_clean.split()),
                content_hash=content_hash(f"{payload.title} {payload.content}"),
                simhash=tiny_simhash(f"{payload.title} {payload.content}"),
            )

            dedup_key = normalized_row.content_hash
            existing = dedup_repo.find_by_key(dedup_key)
            if existing:
                dedup_repo.add(normalized_row.id, dedup_key, existing.document_id, "content_hash")
                total_dedup_skipped += 1
                continue
            dedup_repo.add(normalized_row.id, dedup_key, None, "content_hash")

            meta = payload.meta or {}
            meta_text = " ".join(
                str(v)
                for k, v in meta.items()
                if v is not None and k not in {"query", "search_query"}
            )
            features = analyzer.analyze(payload.title, f"{payload.content} {meta_text}")
            score = scorer.score(
                features,
                {
                    "mechanic_weights": profile.mechanic_weights_json,
                    "profile_text": profile_text,
                    "negative_keywords": (profile.negative_filters_json or {}).get("keywords", []),
                },
            )
            score_repo.insert(normalized_row.id, profile.id, score.total, score.breakdown, score.is_relevant)

            if not score.is_relevant:
                continue
            total_relevant += 1
            duplicate = dedup_repo.find_by_canonical_url(normalized_row.canonical_url, normalized_row.id)
            if duplicate:
                dedup_repo.add(normalized_row.id, f"url:{normalized_row.canonical_url}", duplicate.id, "canonical_url")
                total_dedup_skipped += 1
                continue
            duplicate = dedup_repo.find_near_simhash(normalized_row.simhash, normalized_row.id)
            if duplicate:
                dedup_repo.add(normalized_row.id, f"simhash:{normalized_row.simhash}", duplicate.id, "simhash")
                total_dedup_skipped += 1
                continue
            if sent_repo.was_sent(telegram_chat_id or "default", normalized_row.id):
                continue

            message_id = await notifier.send_finding(
                title=payload.title,
                url=payload.url,
                score=score.total,
                mechanics=[
                    {
                        "key": m.key,
                        "evidence": m.evidence,
                        "introduced": m.introduced,
                        "confidence": m.confidence,
                    }
                    for m in features.mechanics
                ],
                document_id=normalized_row.id,
            )
            sent_repo.mark_sent(telegram_chat_id or "default", normalized_row.id, message_id)
            total_sent += 1
            log.info("Sent finding doc_id=%s message_id=%s", normalized_row.id, message_id)

    log.info("Collected documents total=%s", total_collected)
    return {
        "total_collected": total_collected,
        "total_new_raw": total_new_raw,
        "total_dedup_skipped": total_dedup_skipped,
        "total_relevant": total_relevant,
        "total_sent": total_sent,
    }
