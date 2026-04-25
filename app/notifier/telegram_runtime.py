from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import BotCommand
from aiogram.types import Message
from aiogram.exceptions import TelegramNetworkError, TelegramAPIError

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
except ImportError:  # pragma: no cover
    AsyncIOScheduler = None  # type: ignore[assignment]

from app.config import settings
from app.db.session import get_session
from app.pipeline.jobs import run_pipeline_once
from app.storage.repositories import FeedbackRepo, ReadRepo

log = logging.getLogger(__name__)

router = Router()
PIPELINE_JOB_ID = "pipeline_job"

runtime_state: dict = {
    "last_started_at": None,
    "last_finished_at": None,
    "last_status": "never",
    "last_error": "",
    "last_stats": {},
    "interval_minutes": settings.scheduler_interval_minutes,
}
scheduler_instance = None


async def safe_answer(message: Message, text: str) -> None:
    try:
        await message.answer(text)
    except (TelegramNetworkError, TelegramAPIError) as exc:
        log.warning("Failed to answer user message: %s", exc)


async def run_pipeline_job() -> None:
    runtime_state["last_started_at"] = datetime.now(timezone.utc).isoformat()
    runtime_state["last_status"] = "running"
    runtime_state["last_error"] = ""

    session = get_session()
    try:
        stats = await run_pipeline_once(
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
            steam_search_queries=settings.steam_search_queries_list() if settings.enable_steam_search else [],
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
        runtime_state["last_stats"] = stats or {}
        runtime_state["last_status"] = "ok"
    except Exception:
        session.rollback()
        log.exception("Pipeline job failed")
        runtime_state["last_status"] = "error"
        runtime_state["last_error"] = "pipeline exception (see logs)"
    finally:
        session.close()
        runtime_state["last_finished_at"] = datetime.now(timezone.utc).isoformat()


def _format_findings(items: list[dict], title: str) -> str:
    if not items:
        return f"{title}\nNo findings yet."
    lines = [title]
    for i, row in enumerate(items, 1):
        lines.append(
            f"{i}. ID={row['doc_id']} [{row['source']}] score={row['score']:.2f}\n"
            f"{row['title']}\n"
            f"{row['url']}"
        )
    return "\n\n".join(lines)


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await safe_answer(
        message,
        "Game mechanics monitor bot is running.\n"
        "Commands: /sources, /top, /today, /status, /feedback, /set_interval N, /run"
    )


@router.message(Command("sources"))
async def cmd_sources(message: Message) -> None:
    session = get_session()
    try:
        rows = ReadRepo(session).list_sources_overview()
    finally:
        session.close()

    if not rows:
        await safe_answer(message, "Sources are not initialized yet.")
        return

    lines = ["Sources:"]
    for row in rows:
        lines.append(f"- {row['name']} ({row['type']}): {row['items']} items")
    await safe_answer(message, "\n".join(lines))


@router.message(Command("top"))
async def cmd_top(message: Message) -> None:
    session = get_session()
    try:
        items = ReadRepo(session).top_findings_last_hours(hours=24, limit=10)
    finally:
        session.close()
    await safe_answer(message, _format_findings(items, "Top findings (last 24h):"))


@router.message(Command("today"))
async def cmd_today(message: Message) -> None:
    session = get_session()
    try:
        items = ReadRepo(session).findings_today(limit=20)
    finally:
        session.close()
    await safe_answer(message, _format_findings(items, "Today's findings (UTC day):"))


@router.message(Command("run"))
async def cmd_run(message: Message) -> None:
    await safe_answer(message, "Running pipeline now...")
    await run_pipeline_job()
    await safe_answer(message, "Pipeline run completed.")


@router.message(Command("status"))
async def cmd_status(message: Message) -> None:
    stats = runtime_state.get("last_stats") or {}
    text = (
        "Status:\n"
        f"- state: {runtime_state.get('last_status')}\n"
        f"- interval_min: {runtime_state.get('interval_minutes')}\n"
        f"- last_started_utc: {runtime_state.get('last_started_at')}\n"
        f"- last_finished_utc: {runtime_state.get('last_finished_at')}\n"
        f"- collected: {stats.get('total_collected', 0)}\n"
        f"- new_raw: {stats.get('total_new_raw', 0)}\n"
        f"- dedup_skipped: {stats.get('total_dedup_skipped', 0)}\n"
        f"- relevant: {stats.get('total_relevant', 0)}\n"
        f"- sent: {stats.get('total_sent', 0)}"
    )
    if runtime_state.get("last_error"):
        text += f"\n- error: {runtime_state['last_error']}"
    await safe_answer(message, text)


@router.message(Command("feedback"))
async def cmd_feedback(message: Message) -> None:
    parts = (message.text or "").split(maxsplit=3)
    if len(parts) < 3 or not parts[1].isdigit():
        await safe_answer(message, "Usage: /feedback <doc_id> relevant|miss [note]")
        return

    value_aliases = {
        "relevant": "relevant",
        "yes": "relevant",
        "+": "relevant",
        "miss": "miss",
        "no": "miss",
        "-": "miss",
    }
    value = value_aliases.get(parts[2].lower())
    if value is None:
        await safe_answer(message, "Feedback must be one of: relevant, miss")
        return

    chat_id = str(message.chat.id) if message.chat else "unknown"
    note = parts[3] if len(parts) > 3 else ""
    session = get_session()
    try:
        FeedbackRepo(session).add(chat_id=chat_id, document_id=int(parts[1]), value=value, note=note)
        session.commit()
    except Exception:
        session.rollback()
        log.exception("Failed to save feedback")
        await safe_answer(message, "Failed to save feedback.")
        return
    finally:
        session.close()

    await safe_answer(message, f"Feedback saved: doc_id={parts[1]} value={value}")


@router.message(Command("set_interval"))
async def cmd_set_interval(message: Message) -> None:
    global scheduler_instance
    parts = (message.text or "").split()
    if len(parts) != 2 or not parts[1].isdigit():
        await safe_answer(message, "Usage: /set_interval <minutes>. Example: /set_interval 15")
        return

    minutes = int(parts[1])
    if minutes < 1 or minutes > 1440:
        await safe_answer(message, "Interval must be between 1 and 1440 minutes.")
        return

    if scheduler_instance is None:
        await safe_answer(message, "Scheduler is not ready yet.")
        return

    scheduler_instance.reschedule_job(
        job_id=PIPELINE_JOB_ID,
        trigger="interval",
        minutes=minutes,
    )
    runtime_state["interval_minutes"] = minutes
    await safe_answer(message, f"Pipeline interval updated: every {minutes} minute(s).")


async def register_bot_commands(bot: Bot) -> None:
    try:
        await bot.set_my_commands(
            [
                BotCommand(command="start", description="Show bot help"),
                BotCommand(command="sources", description="List sources and collected counts"),
                BotCommand(command="top", description="Top relevant findings for last 24h"),
                BotCommand(command="today", description="Findings scored today"),
                BotCommand(command="status", description="Show scheduler and last run status"),
                BotCommand(command="feedback", description="Mark a finding as relevant or miss"),
                BotCommand(command="set_interval", description="Set scheduler interval in minutes"),
                BotCommand(command="run", description="Run pipeline now"),
            ]
        )
    except (TelegramNetworkError, TelegramAPIError) as exc:
        log.warning("Failed to register bot commands: %s", exc)


async def run_bot_with_scheduler() -> None:
    global scheduler_instance
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required for bot polling mode")
    if AsyncIOScheduler is None:
        raise RuntimeError(
            "APScheduler is not installed. Run: pip install -e . (or pip install apscheduler)"
        )

    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher()
    dp.include_router(router)
    await register_bot_commands(bot)

    scheduler = AsyncIOScheduler()
    scheduler_instance = scheduler
    interval_minutes = max(1, settings.scheduler_interval_minutes)
    runtime_state["interval_minutes"] = interval_minutes
    scheduler.add_job(run_pipeline_job, "interval", id=PIPELINE_JOB_ID, minutes=interval_minutes)
    scheduler.start()
    log.info("Scheduler started. Interval=%s min", settings.scheduler_interval_minutes)

    if settings.scheduler_run_on_startup:
        asyncio.create_task(run_pipeline_job())

    try:
        while True:
            try:
                await dp.start_polling(bot, drop_pending_updates=settings.telegram_polling_drop_pending)
                break
            except (TelegramNetworkError, TelegramAPIError) as exc:
                log.warning("Polling network error, retrying in 10s: %s", exc)
                await asyncio.sleep(10)
    finally:
        scheduler.shutdown(wait=False)
        scheduler_instance = None
        await bot.session.close()
