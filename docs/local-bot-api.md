# Local Telegram Bot API Mode

This project supports two Telegram access modes:

- Public Bot API mode: the bot connects to Telegram's hosted Bot API service
- Local Bot API mode: the bot connects to a self-hosted `telegram-bot-api`
  server running beside the bot container

## When you need local mode

Use local mode when you want ZIP support above `20 MB`.

With the public Bot API, Telegram currently limits bot file downloads to
`20 MB`. A local Bot API server removes that download limit.

Local mode changes only the Telegram file transport path. It does not replace
the static image hosting requirement. You still need your existing Nginx to
serve `PUBLIC_IMAGE_DIR` at `PUBLIC_IMAGE_BASE_URL`.

## What this repository provides

The repository includes:

- `docker-compose.local-bot-api.yml`
- `Dockerfile.telegram-bot-api`

Together they run the official `telegram-bot-api` server from source in a
second container and automatically point the bot at it.

## Required .env values

Add these values to your `.env`:

```env
USE_LOCAL_TELEGRAM_BOT_API=true
TELEGRAM_API_ID=123456
TELEGRAM_API_HASH=replace-me
```

You can obtain `TELEGRAM_API_ID` and `TELEGRAM_API_HASH` from
`https://my.telegram.org`.

For the full application process and suggested form values, see
`docs/telegram-api-credentials.md`.

You do not need to set `TELEGRAM_API_BASE` manually in Docker local mode. The
compose override file injects:

```env
TELEGRAM_API_BASE=http://telegram-bot-api:8081
TELEGRAM_LOCAL_MODE=true
```

## Local run command

```bash
docker compose -f docker-compose.yml -f docker-compose.local-bot-api.yml up -d --build
```

## VPS deployment behavior

The GitHub Actions deployment workflow checks the VPS-side `.env` file.

If it finds:

```env
USE_LOCAL_TELEGRAM_BOT_API=true
```

it automatically deploys with both compose files:

```bash
docker compose -f docker-compose.yml -f docker-compose.local-bot-api.yml up -d --build --remove-orphans
```

Otherwise it uses the single-service deployment:

```bash
docker compose up -d --build --remove-orphans
```

## First switch from public mode to local mode

Before the first time you switch an existing bot from Telegram's hosted Bot API
to your own local Bot API server, call `logOut` on the hosted API for that bot.

Example:

```bash
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/logOut"
```

After that, start the local Bot API deployment.

## Persistent data

The local Bot API server stores data under:

```text
./telegram-bot-api-data
```

Keep that directory persisted on the VPS if you use local mode.
