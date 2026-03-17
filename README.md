# zip2telegraph-bot

Telegram group bot that accepts ZIP uploads from group administrators, extracts
image files, publishes them through your existing Nginx static site, and
creates a Telegraph page that references those public image URLs.

## What this starter package includes

- Python 3.11+ project scaffold built on `aiogram`
- `SQLite` persistence for rate-limit events and task history
- Per-group serial job queue
- ZIP validation, natural file ordering, and temp directory cleanup
- Local static image publishing + Telegraph page client
- Docker and `docker compose` deployment artifacts
- Unit tests for core rules

## Important platform constraint

Telegram's current Bot API documentation says bots can download files only up to
`20 MB` when using the public Bot API. Telegram's documentation for a local Bot
API server says self-hosting removes that download limit.

This means:

- With the public Bot API, your practical ZIP input limit is `20 MB`
- To support your requested `1 GB` ZIP uploads, you need a self-hosted local
  Bot API server and must point `TELEGRAM_API_BASE` at it

The app keeps your requested `1 GB` business limit, but it also enforces the
effective transport limit from your Telegram API mode.

## Layout

```text
src/zip2telegraph_bot/
  app.py
  config.py
  db.py
  errors.py
  logging.py
  models.py
  queue.py
  services/
  utils/
docs/
  architecture.md
tests/
```

## Quick start

1. Create a bot with `@BotFather`
2. Copy one of these templates to `.env`
   - `.env.public-bot-api.example`
   - `.env.local-bot-api.example`
3. Fill `BOT_TOKEN`
4. Optionally set `TELEGRAPH_ACCESS_TOKEN`
5. Set `PUBLIC_IMAGE_BASE_URL` to the URL served by your existing Nginx
6. Choose public Bot API mode or local Bot API mode
7. Run with Docker or local Python

### Docker

Public Bot API mode:

```bash
Copy-Item .env.public-bot-api.example .env
docker compose up --build
```

Local Bot API mode for large ZIP files:

1. Set `USE_LOCAL_TELEGRAM_BOT_API=true` in `.env`
2. Fill `TELEGRAM_API_ID` and `TELEGRAM_API_HASH`
3. Run:

```bash
Copy-Item .env.local-bot-api.example .env
docker compose -f docker-compose.yml -f docker-compose.local-bot-api.yml up --build
```

### Local Python

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
python -m zip2telegraph_bot
```

## Bot behavior

- Only `group` and `supergroup` chats are processed
- Only chat admins can trigger processing
- A ZIP document message triggers processing automatically
- Non-image files inside the ZIP are ignored
- Any invalid image or limit violation fails the whole task
- Each group is processed serially
- Rate limiting defaults:
  - per chat: 1 call / 5 minutes
  - per admin user: 3 calls / hour

## Operations notes

- Mount `./data` to persist SQLite
- Mount `./tmp` for temp files if you want visibility into disk usage
- Mount `./public-images` and serve it through your existing Nginx
- Mount `./telegram-bot-api-data` if you use the local Bot API server
- The bot removes task temp directories after completion
- On startup, the bot removes stale temp directories left by previous crashes

Docker bind mounts can be customized from `.env` with:

- `HOST_DATA_DIR`
- `HOST_TMP_DIR`
- `HOST_PUBLIC_IMAGE_DIR`
- `HOST_TELEGRAM_BOT_API_DATA_DIR`

In Docker mode, the bot container always uses fixed internal paths:

- `DATA_DIR=/app/data`
- `TMP_DIR=/app/tmp`
- `PUBLIC_IMAGE_DIR=/app/public-images`

So changing those three values in `.env` will not break Docker bind mounts.

## Static image hosting

This project no longer relies on `https://telegra.ph/upload`.

Instead:

- The bot copies task images into `PUBLIC_IMAGE_DIR`
- Your existing Nginx serves that directory as static files
- `createPage` uses `PUBLIC_IMAGE_BASE_URL/...` URLs in each `img src`

You need a publicly reachable host name or IP for `PUBLIC_IMAGE_BASE_URL`.

## Run tests

```bash
pytest
```

## Generate TELEGRAPH_ACCESS_TOKEN

You can generate a Telegraph account token directly with:

```bash
python scripts/create_telegraph_account.py
```

Optional arguments:

```bash
python scripts/create_telegraph_account.py --short-name zip2telegraph --author-name zip2telegraph-bot
```

The script prints:

```text
TELEGRAPH_ACCESS_TOKEN=...
TELEGRAPH_AUTH_URL=...
```

Place `TELEGRAPH_ACCESS_TOKEN` into your VPS `.env`.

`TELEGRAPH_AUTH_URL` is the account management URL returned by Telegraph. Keep
it for your records if you want to manage that Telegraph account later.

## GitHub Actions deployment

The repository now includes a production-oriented CI/CD workflow in
`.github/workflows/ci.yml`:

- Every push and pull request runs tests and a Docker build check
- Pushes to `main` also trigger deployment to your VPS
- Manual deployment is available through `workflow_dispatch`

Required GitHub Actions secrets for VPS deployment:

- `VPS_HOST`: VPS public IP or domain
- `VPS_USER`: deployment user on the VPS
- `VPS_SSH_KEY`: private SSH key used by GitHub Actions

Recommended GitHub Actions secrets:

- `VPS_PORT`: SSH port, defaults to `22`
- `VPS_HOST_FINGERPRINT`: SSH host fingerprint for host verification
- `VPS_APP_DIR`: dedicated deploy directory, defaults to `/opt/zip2telegraph-bot`

Important:

- `VPS_APP_DIR` must be a dedicated application directory
- The deployment workflow clears everything inside that directory except `data/`
  , `tmp/`, `telegram-bot-api-data/`, and `.env` before extracting the new
  release
- Runtime configuration is not taken from GitHub Actions secrets
- You must upload the production `.env` file manually to `VPS_APP_DIR/.env`
  before the first deployment
- If `.env` contains `USE_LOCAL_TELEGRAM_BOT_API=true`, the deploy workflow
  automatically starts the additional local `telegram-bot-api` service
- In local Bot API mode, `.env` must also contain `TELEGRAM_API_ID` and
  `TELEGRAM_API_HASH`

Suggested first-time upload:

```bash
scp .env deploy@your-vps-host:/opt/zip2telegraph-bot/.env
```

See `docs/deployment-vps.md` for the full VPS setup and GitHub configuration
process. For local Bot API mode details, see `docs/local-bot-api.md`. For the
Nginx static image configuration, see `docs/nginx-static-images.md`.
