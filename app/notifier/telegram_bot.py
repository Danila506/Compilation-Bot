import logging
import asyncio

from aiogram import Bot
from aiogram.exceptions import TelegramNetworkError

from app.notifier.formatter import format_alert

log = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id

    async def send_finding(
        self,
        title: str,
        url: str,
        score: float,
        mechanics: list[dict],
        document_id: int | None = None,
    ) -> str:
        text = format_alert(title, url, score, mechanics, document_id=document_id)
        if not self.token or not self.chat_id:
            log.info("Telegram credentials are missing. Dry-run alert:\n%s", text)
            return "dry_run"

        bot = Bot(token=self.token)
        try:
            attempts = 3
            for attempt in range(1, attempts + 1):
                try:
                    response = await bot.send_message(
                        chat_id=self.chat_id,
                        text=text,
                        request_timeout=120,
                    )
                    return str(response.message_id)
                except TelegramNetworkError as exc:
                    if attempt == attempts:
                        log.exception("Telegram network error after %s attempts: %s", attempts, exc)
                        return "network_error"
                    await asyncio.sleep(attempt * 2)
                except Exception as exc:  # noqa: BLE001
                    log.exception("Telegram send failed: %s", exc)
                    return "send_error"
        finally:
            await bot.session.close()
