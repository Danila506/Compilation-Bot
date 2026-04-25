import asyncio
import logging

from app.config import settings
from app.db.base import Base
from app.db.session import engine, get_session
from app.notifier.telegram_runtime import run_bot_with_scheduler
from app.pipeline.jobs import run_pipeline_once

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


async def async_main() -> None:
    init_db()
    if settings.telegram_bot_token:
        await run_bot_with_scheduler()
        return

    session = get_session()
    try:
        await run_pipeline_once(
            session=session,
            telegram_token=settings.telegram_bot_token,
            telegram_chat_id=settings.telegram_chat_id,
            threshold=settings.score_send_threshold,
            reddit_subreddits=settings.reddit_subreddits_list(),
            reddit_limit_per_subreddit=settings.reddit_limit_per_subreddit,
            reddit_client_id=settings.reddit_client_id,
            reddit_client_secret=settings.reddit_client_secret,
            reddit_user_agent=settings.reddit_user_agent,
            steam_app_ids=settings.steam_app_ids_list(),
            steam_news_count_per_app=settings.steam_news_count_per_app,
            steam_historical_max_pages=settings.steam_historical_max_pages,
            steam_search_queries=settings.steam_search_queries_list(),
            steam_search_limit_per_query=settings.steam_search_limit_per_query,
            youtube_channel_ids=settings.youtube_channel_ids_list(),
            youtube_limit_per_channel=settings.youtube_limit_per_channel,
            rss_feed_urls=settings.rss_feed_urls_list(),
            rss_limit_per_feed=settings.rss_limit_per_feed,
            itch_devlog_feed_urls=settings.itch_devlog_feed_urls_list(),
            itch_limit_per_feed=settings.itch_limit_per_feed,
            indiedb_feed_urls=settings.indiedb_feed_urls_list(),
            indiedb_limit_per_feed=settings.indiedb_limit_per_feed,
            lookback_days=settings.lookback_days,
            prefer_2d_only=settings.prefer_2d_only,
            min_2d_signal_score=settings.min_2d_signal_score,
            use_mock_collector=settings.use_mock_collector,
            game_profile_name=settings.game_profile_name,
            game_profile_description=settings.game_profile_description,
            game_profile_tags=settings.game_profile_tags_list(),
            game_profile_mechanic_weights=settings.game_profile_mechanic_weights_dict(),
            game_profile_negative_keywords=settings.game_profile_negative_keywords_list(),
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    asyncio.run(async_main())
