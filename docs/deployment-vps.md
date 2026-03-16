# VPS Deployment Guide

This document describes the production deployment flow implemented by
`.github/workflows/ci.yml`.

## What the workflow does

1. Runs tests on GitHub Actions
2. Verifies the Docker image builds successfully
3. On push to `main`, uploads a release archive to the VPS
4. Recreates the app directory contents except `data/`, `tmp/`, and `.env`
5. Reuses the existing manually uploaded `.env`
6. Chooses single-service or dual-service compose based on `.env`

## Deployment assumptions

- VPS OS: modern Linux distribution such as Ubuntu 22.04 or 24.04
- Runtime: Docker Engine with Docker Compose plugin installed
- Deployment branch: `main`
- App directory: dedicated directory, recommended `/opt/zip2telegraph-bot`
- Persistence: SQLite database and temp files stored under `data/` and `tmp/`
- Optional local Bot API persistence stored under `telegram-bot-api-data/`

## Step 1: Prepare the VPS

Create or choose a Linux server with SSH access.

Install Docker and the Docker Compose plugin. On Ubuntu:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Create a dedicated deploy user if you do not want to use `root`:

```bash
sudo adduser deploy
sudo usermod -aG docker deploy
```

Create the app directory:

```bash
sudo mkdir -p /opt/zip2telegraph-bot
sudo chown -R deploy:deploy /opt/zip2telegraph-bot
```

Important:

- Use a dedicated `VPS_APP_DIR`
- The deployment workflow deletes all existing files in that directory except
  `data/`, `tmp/`, `telegram-bot-api-data/`, and `.env`

## Step 2: Create an SSH key for GitHub Actions

On your local machine:

```bash
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ./github-actions-deploy
```

This creates:

- `github-actions-deploy`: private key
- `github-actions-deploy.pub`: public key

Append the public key to the deploy user's `authorized_keys` on the VPS:

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
cat github-actions-deploy.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

If you created a separate deploy user, do this as that user.

## Step 3: Collect the SSH host fingerprint

Recommended:

```bash
ssh-keyscan -H your-vps-host
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub -E sha256
```

Use the `SHA256:...` fingerprint value as `VPS_HOST_FINGERPRINT` in GitHub
secrets. This enables host verification in the workflow.

## Step 4: Configure GitHub repository secrets

In GitHub, open:

`Settings -> Secrets and variables -> Actions`

Add these required secrets:

- `VPS_HOST`: example `203.0.113.10`
- `VPS_USER`: example `deploy`
- `VPS_SSH_KEY`: contents of the private key file `github-actions-deploy`

Add these recommended secrets:

- `VPS_PORT`: default `22`
- `VPS_HOST_FINGERPRINT`: SSH host fingerprint such as `SHA256:...`
- `VPS_APP_DIR`: recommended `/opt/zip2telegraph-bot`

Runtime variables are intentionally not stored in GitHub Actions secrets in this
deployment model. They live only in the VPS-side `.env` file.

## Step 5: Optional GitHub Environment configuration

The workflow uses the `production` environment for the deploy job.

You can create it in:

`Settings -> Environments -> New environment`

Recommended options:

- Require manual approval before deployment
- Restrict deployment to protected branches
- Scope production-only secrets to this environment if desired

If you use environment-scoped secrets, create them under the `production`
environment instead of repository-wide secrets.

## Step 6: Upload the production .env file manually

Create a production `.env` file locally. Start from `.env.example` and fill the
runtime values you actually need.

At minimum:

- `BOT_TOKEN`

Recommended:

- `TELEGRAPH_ACCESS_TOKEN`
- `TIMEZONE`
- `LOG_LEVEL`

If you need ZIP support above `20 MB`, also configure:

- `USE_LOCAL_TELEGRAM_BOT_API=true`
- `TELEGRAM_API_ID`
- `TELEGRAM_API_HASH`

Upload the file to the VPS app directory before the first deploy:

```bash
scp .env deploy@your-vps-host:/opt/zip2telegraph-bot/.env
```

Verify it exists on the server:

```bash
ssh deploy@your-vps-host
ls -la /opt/zip2telegraph-bot/.env
```

The deploy workflow will fail if `.env` is missing.

### How to generate TELEGRAPH_ACCESS_TOKEN

You can generate a Telegraph account token locally before uploading `.env`:

```bash
python scripts/create_telegraph_account.py
```

Or with explicit account metadata:

```bash
python scripts/create_telegraph_account.py --short-name zip2telegraph --author-name zip2telegraph-bot
```

The script prints:

```text
TELEGRAPH_ACCESS_TOKEN=...
TELEGRAPH_AUTH_URL=...
```

Use `TELEGRAPH_ACCESS_TOKEN` in your VPS `.env`.

Keep `TELEGRAPH_AUTH_URL` somewhere safe if you want to manage that Telegraph
account later. It is not required in `.env`.

## Step 7: First deployment

Make sure your default branch is `main`, or update the workflow if you deploy
from a different branch.

Then push to `main`:

```bash
git push origin main
```

GitHub Actions will:

1. Run tests
2. Build the Docker image
3. Upload the release to the VPS
4. Reuse the existing `.env`
5. If `USE_LOCAL_TELEGRAM_BOT_API=true`, start both the bot and local
   `telegram-bot-api` service
6. Otherwise, start only the bot service

## Step 8: Verify the deployment on the VPS

SSH into the server and check the container:

```bash
cd /opt/zip2telegraph-bot
docker compose ps
docker compose logs -f
```

Check that:

- The bot container is `Up`
- The `telegram-bot-api` container is also `Up` if local mode is enabled
- The application can read `.env`
- `data/app.db` is created after activity
- No startup error is logged for `BOT_TOKEN`

## Step 9: Subsequent updates

Every push to `main` will redeploy automatically.

Manual redeploy is also available from:

`Actions -> CI/CD -> Run workflow`

Use manual runs when:

- You rotated secrets
- You updated the VPS-side `.env`
- You changed the VPS runtime manually
- You want to redeploy the current `main` commit without making a new commit

## Operational notes

- `data/` and `tmp/` are preserved across deployments
- `.env` is preserved across deployments
- `telegram-bot-api-data/` is preserved if local mode is enabled
- Other files under `VPS_APP_DIR` are replaced on each deployment
- The workflow builds the image on the VPS, so the VPS must have enough CPU,
  RAM, and disk for Docker builds
- `docker image prune -f` runs after deployment to limit image buildup

## Important Telegram limitation

With the public Telegram Bot API, bots can only download files up to `20 MB`.

If you need your requested `1 GB` ZIP support, you must:

1. Enable local Bot API mode in `.env`
2. Set `USE_LOCAL_TELEGRAM_BOT_API=true`
3. Set `TELEGRAM_API_ID`
4. Set `TELEGRAM_API_HASH`

Without that, the app will still run, but the effective ZIP input limit will be
`20 MB`.

For the full local mode procedure, see `docs/local-bot-api.md`.
