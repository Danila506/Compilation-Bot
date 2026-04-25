# Game Mechanics Monitor Bot

Practical architecture scaffold for a Telegram bot that tracks game mechanics from external sources.

## Current Status

This repository contains:
- package layout for collector / analyzer / scorer / storage / notifier
- SQLAlchemy models for core entities
- lightweight pipeline orchestration
- starter collectors and analyzer interfaces

## Run

1. Install dependencies:

```powershell
pip install -e .
```

2. Set environment variables:

```powershell
$env:TELEGRAM_BOT_TOKEN="your-token"
$env:TELEGRAM_CHAT_ID="123456789"
$env:PREFER_2D_ONLY="true"
$env:MIN_2D_SIGNAL_SCORE="1.0"
$env:GAME_PROFILE_NAME="2D top-down survival"
$env:GAME_PROFILE_TAGS="2d,top-down,survival,zombies"
$env:GAME_PROFILE_MECHANIC_WEIGHTS='{"inventory_drag_drop":1.0,"equipment_slots":0.9,"crafting":0.8}'
$env:GAME_PROFILE_NEGATIVE_KEYWORDS="battle royale,match-3"
$env:REDDIT_SUBREDDITS="gamedev,indiegames,indiedev"
$env:REDDIT_LIMIT_PER_SUBREDDIT="10"
$env:REDDIT_CLIENT_ID=""
$env:REDDIT_CLIENT_SECRET=""
$env:REDDIT_USER_AGENT="game-mech-monitor-bot/0.1 by deadSparkBot"
$env:STEAM_APP_IDS="108600,221100,294100"
$env:STEAM_NEWS_COUNT_PER_APP="5"
$env:STEAM_HISTORICAL_MAX_PAGES="10"
$env:STEAM_SEARCH_QUERIES="2d top-down survival,zombie survival crafting,inventory management survival"
$env:STEAM_SEARCH_LIMIT_PER_QUERY="10"
$env:YOUTUBE_CHANNEL_IDS="UC_x5XG1OV2P6uZZ5FSM9Ttw"
$env:YOUTUBE_LIMIT_PER_CHANNEL="10"
$env:RSS_FEED_URLS="https://www.gamedeveloper.com/rss.xml"
$env:RSS_LIMIT_PER_FEED="20"
$env:ITCH_DEVLOG_FEED_URLS=""
$env:ITCH_LIMIT_PER_FEED="20"
$env:INDIEDB_FEED_URLS=""
$env:INDIEDB_LIMIT_PER_FEED="20"
$env:LOOKBACK_DAYS="730"
$env:SCHEDULER_INTERVAL_MINUTES="30"
$env:SCHEDULER_RUN_ON_STARTUP="true"
$env:USE_MOCK_COLLECTOR="false"
```

3. Start bot polling + scheduler:

```powershell
python -m app.main
```

## Deploy to Render

This bot is configured as a Render Free Web Service. The web process exposes `/health` for Render and starts Telegram polling plus APScheduler in the background.

1. Push this repository to GitHub/GitLab/Bitbucket.
2. In Render, create a new Blueprint from the repository. Render will read `render.yaml`.
3. Fill secret values when prompted:
   - `TELEGRAM_BOT_TOKEN`
      - `TELEGRAM_CHAT_ID`
      - `DATABASE_URL`
      - optional `REDDIT_CLIENT_ID`
      - optional `REDDIT_CLIENT_SECRET`
4. Deploy.

Use an external PostgreSQL database for `DATABASE_URL` on Render Free. SQLite in `/tmp/app.db` is ephemeral: collected items, feedback, dedup, and sent-item history can be lost on redeploys/restarts, which can make the bot send old findings again.

PostgreSQL URL examples:

```text
postgresql://user:password@host:5432/dbname
postgresql+psycopg://user:password@host:5432/dbname
```

The app normalizes `postgres://` / `postgresql://` to `postgresql+psycopg://` automatically and adds `sslmode=require` for hosted Postgres providers such as Supabase.

For Supabase, use a URI from Project Settings -> Database -> Connection string. If the password contains special characters such as `@`, `#`, `%`, `:` or `/`, URL-encode it before placing it in `DATABASE_URL`.

### Keep Render Free awake

This repository includes `.github/workflows/render-keepalive.yml`, which pings the deployed `/health` endpoint every 10 minutes.

After the first Render deploy:

1. Copy the Render service URL and append `/health`.
2. In GitHub, open repository Settings -> Secrets and variables -> Actions.
3. Add a repository secret named `RENDER_HEALTH_URL`.
4. Set it to a value like `https://your-service-name.onrender.com/health`.
5. Open Actions -> Render Keepalive -> Run workflow once to verify it works.

This reduces Render Free spin-downs, but it does not make the service production-grade. Render can still restart free services, and `/tmp/app.db` remains temporary.

### Telegram polling conflict

If Render logs show `TelegramConflictError: terminated by other getUpdates request`, the same `TELEGRAM_BOT_TOKEN` is running in another process. Stop every other copy of the bot before leaving Render enabled:

- local `python -m app.main` or `python -m app.web`
- another Render service created from the same repo
- an old deployment/provider using the same token

Telegram polling supports only one active consumer per bot token.

### Dashboard

Open `/dashboard` on the deployed Render URL to inspect collected findings, score breakdowns, feedback, sources, and raw text.

Example:

```text
https://your-service-name.onrender.com/dashboard
```

## Telegram commands

- `/sources` - monitored sources and collected item counts
- `/top` - top relevant findings for last 24 hours
- `/today` - findings scored today (UTC day)
- `/status` - last run status and counters
- `/feedback <doc_id> relevant|miss [note]` - save relevance feedback
- `/set_interval N` - update scheduler interval in minutes (1..1440)
- `/run` - manual pipeline run now

## Next Steps

- add real source APIs in collectors
- connect PostgreSQL and Alembic migrations
- add scheduler/background workers
- improve NLP and semantic deduplication
