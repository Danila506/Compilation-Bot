from __future__ import annotations

import asyncio
import logging
import os

from aiohttp import web

from app.config import settings
from app.db.base import Base
from app.db.session import engine
from app.notifier.telegram_runtime import run_bot_with_scheduler, runtime_state

log = logging.getLogger(__name__)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


async def bot_context(app: web.Application):
    init_db()
    bot_task: asyncio.Task | None = None

    if settings.telegram_bot_token:
        bot_task = asyncio.create_task(run_bot_with_scheduler())
        log.info("Telegram polling task started")
    else:
        log.warning("TELEGRAM_BOT_TOKEN is not set; web service started without bot polling")

    try:
        yield
    finally:
        if bot_task is not None:
            bot_task.cancel()
            try:
                await bot_task
            except asyncio.CancelledError:
                pass


async def root(request: web.Request) -> web.Response:
    return web.json_response({
        "name": settings.app_name,
        "status": "ok",
        "bot_enabled": bool(settings.telegram_bot_token),
    })


async def health(request: web.Request) -> web.Response:
    return web.json_response({
        "status": "ok",
        "bot_enabled": bool(settings.telegram_bot_token),
        "pipeline_status": runtime_state.get("last_status"),
        "last_started_at": runtime_state.get("last_started_at"),
        "last_finished_at": runtime_state.get("last_finished_at"),
    })


def create_app() -> web.Application:
    app = web.Application()
    app.cleanup_ctx.append(bot_context)
    app.router.add_get("/", root)
    app.router.add_get("/health", health)
    return app


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    port = int(os.environ.get("PORT", "10000"))
    web.run_app(create_app(), host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
