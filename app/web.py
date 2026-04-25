from __future__ import annotations

import asyncio
import logging
import os
import sys
import traceback

from aiohttp import web

from app.config import settings
from app.dashboard import DASHBOARD_HTML
from app.db.base import Base
from app.db.session import engine, get_session
from app.notifier.telegram_runtime import run_bot_with_scheduler, runtime_state
from app.storage.repositories import ReadRepo

log = logging.getLogger(__name__)


def init_db() -> None:
    log.info("Initializing database")
    Base.metadata.create_all(bind=engine)
    log.info("Database initialized")


async def bot_context(app: web.Application):
    try:
        init_db()
        app["db_ready"] = True
    except Exception as exc:  # noqa: BLE001
        app["db_ready"] = False
        runtime_state["last_status"] = "error"
        runtime_state["last_error"] = f"database init failed: {exc}"
        log.exception("Database initialization failed")
        yield
        return

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
        "db_ready": bool(request.app.get("db_ready", False)),
    })


async def health(request: web.Request) -> web.Response:
    return web.json_response({
        "status": "ok",
        "bot_enabled": bool(settings.telegram_bot_token),
        "db_ready": bool(request.app.get("db_ready", False)),
        "pipeline_status": runtime_state.get("last_status"),
        "last_started_at": runtime_state.get("last_started_at"),
        "last_finished_at": runtime_state.get("last_finished_at"),
        "last_error": runtime_state.get("last_error"),
    })


async def dashboard(request: web.Request) -> web.Response:
    return web.Response(text=DASHBOARD_HTML, content_type="text/html")


async def dashboard_api(request: web.Request) -> web.Response:
    session = get_session()
    try:
        repo = ReadRepo(session)
        payload = {
            "summary": repo.dashboard_summary(),
            "findings": repo.dashboard_findings(),
            "runtime": {
                "pipeline_status": runtime_state.get("last_status"),
                "last_started_at": runtime_state.get("last_started_at"),
                "last_finished_at": runtime_state.get("last_finished_at"),
                "last_error": runtime_state.get("last_error"),
            },
        }
    finally:
        session.close()
    return web.json_response(payload)


def create_app() -> web.Application:
    app = web.Application()
    app.cleanup_ctx.append(bot_context)
    app.router.add_get("/", root)
    app.router.add_get("/health", health)
    app.router.add_get("/dashboard", dashboard)
    app.router.add_get("/api/dashboard", dashboard_api)
    return app


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    port = int(os.environ.get("PORT", "10000"))
    log.info(
        "Starting web service on port=%s env=%s database_url_set=%s telegram_token_set=%s",
        port,
        settings.environment,
        bool(settings.database_url),
        bool(settings.telegram_bot_token),
    )
    web.run_app(create_app(), host="0.0.0.0", port=port)


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001
        traceback.print_exc(file=sys.stderr)
        raise
