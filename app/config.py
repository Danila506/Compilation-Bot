from __future__ import annotations

from pathlib import Path
import json
import tempfile

from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_database_url() -> str:
    temp_db = Path(tempfile.gettempdir()) / "tg_bot" / "app.db"
    return f"sqlite+pysqlite:///{temp_db.as_posix()}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "app/.env"),
        env_file_encoding="utf-8",
    )

    app_name: str = "game-mech-monitor-bot"
    environment: str = "dev"
    database_url: str = _default_database_url()

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    score_send_threshold: float = 1.4
    prefer_2d_only: bool = True
    min_2d_signal_score: float = 1.0
    use_mock_collector: bool = False

    game_profile_name: str = "2D top-down survival"
    game_profile_description: str = "Default profile for survival mechanics discovery."
    game_profile_tags: str = "2d,top-down,survival,zombies"
    game_profile_mechanic_weights: str = ""
    game_profile_negative_keywords: str = ""

    reddit_subreddits: str = "gamedev,indiegames,indiedev"
    reddit_limit_per_subreddit: int = 10
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "game-mech-monitor-bot/0.1 by deadSparkBot"

    steam_app_ids: str = "108600,221100,294100"
    steam_news_count_per_app: int = 5
    steam_historical_max_pages: int = 10
    steam_search_queries: str = "2d top-down survival,zombie survival crafting,inventory management survival"
    steam_search_limit_per_query: int = 10
    enable_steam_search: bool = False
    youtube_channel_ids: str = ""
    youtube_limit_per_channel: int = 10
    rss_feed_urls: str = ""
    rss_limit_per_feed: int = 20
    itch_devlog_feed_urls: str = ""
    itch_limit_per_feed: int = 20
    indiedb_feed_urls: str = ""
    indiedb_limit_per_feed: int = 20
    lookback_days: int = 730
    scheduler_interval_minutes: int = 30
    scheduler_run_on_startup: bool = True
    telegram_polling_drop_pending: bool = True

    def reddit_subreddits_list(self) -> list[str]:
        return [s.strip() for s in self.reddit_subreddits.split(",") if s.strip()]

    def steam_app_ids_list(self) -> list[int]:
        app_ids: list[int] = []
        for raw in self.steam_app_ids.split(","):
            value = raw.strip()
            if not value:
                continue
            if value.isdigit():
                app_ids.append(int(value))
        return app_ids

    def steam_search_queries_list(self) -> list[str]:
        return [s.strip() for s in self.steam_search_queries.split(",") if s.strip()]

    def youtube_channel_ids_list(self) -> list[str]:
        return [s.strip() for s in self.youtube_channel_ids.split(",") if s.strip()]

    def rss_feed_urls_list(self) -> list[str]:
        return [s.strip() for s in self.rss_feed_urls.split(",") if s.strip()]

    def itch_devlog_feed_urls_list(self) -> list[str]:
        return [s.strip() for s in self.itch_devlog_feed_urls.split(",") if s.strip()]

    def indiedb_feed_urls_list(self) -> list[str]:
        return [s.strip() for s in self.indiedb_feed_urls.split(",") if s.strip()]

    def game_profile_tags_list(self) -> list[str]:
        return [s.strip() for s in self.game_profile_tags.split(",") if s.strip()]

    def game_profile_mechanic_weights_dict(self) -> dict[str, float]:
        defaults = {
            "inventory_drag_drop": 1.0,
            "equipment_slots": 0.9,
            "clothing_system": 1.1,
            "backpack_container_storage": 1.0,
            "crafting": 0.8,
            "weapons": 0.6,
            "stealth": 0.9,
            "noise_attracting_enemies": 1.2,
            "disguise_infected": 1.4,
            "ai_reaction_sound_visibility": 1.3,
            "loot_scavenging": 0.8,
        }
        if not self.game_profile_mechanic_weights.strip():
            return defaults
        try:
            parsed = json.loads(self.game_profile_mechanic_weights)
        except json.JSONDecodeError:
            return defaults
        if not isinstance(parsed, dict):
            return defaults
        return {str(k): float(v) for k, v in parsed.items() if isinstance(v, int | float)}

    def game_profile_negative_keywords_list(self) -> list[str]:
        return [s.strip().lower() for s in self.game_profile_negative_keywords.split(",") if s.strip()]


settings = Settings()


def ensure_runtime_dirs() -> None:
    if settings.database_url.startswith("sqlite+pysqlite:///"):
        db_path = settings.database_url.removeprefix("sqlite+pysqlite:///")
        db_dir = Path(db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
