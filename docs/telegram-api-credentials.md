# How to Apply for TELEGRAM_API_ID and TELEGRAM_API_HASH

This document explains how to obtain `TELEGRAM_API_ID` and
`TELEGRAM_API_HASH` for local `telegram-bot-api` deployment.

## What these credentials are

These values are not the same as `BOT_TOKEN`.

- `BOT_TOKEN`: identifies your bot, issued by `@BotFather`
- `TELEGRAM_API_ID` and `TELEGRAM_API_HASH`: identify your Telegram developer
  application, issued from `my.telegram.org`

You only need `TELEGRAM_API_ID` and `TELEGRAM_API_HASH` when you run a local
`telegram-bot-api` server.

## Official entry point

Open:

`https://my.telegram.org`

Then go to:

`API development tools`

Official reference:

- `https://core.telegram.org/api/obtaining_api_id`

## Before you start

Prepare these items:

- A Telegram account with a phone number that can log in successfully
- A stable application name
- A short application identifier
- A URL, such as your GitHub repository URL
- A short description of your use case

Important:

- Telegram's official documentation says the phone number used for login must
  belong to an active Telegram account
- Telegram's official documentation also says there can currently be only one
  `api_id` linked to each phone number

## Suggested form values for this project

Use values close to these:

```text
App title: Zip2Telegraph Bot Infra
Short name: zip2telegraphinfra
URL: https://github.com/<your-account>/zip2telegraph-bot
Platform: Desktop
Description: Self-hosted infrastructure for a private Telegram bot that processes ZIP image archives and publishes Telegraph pages. Used to run the official local telegram-bot-api server for large file handling. No spam, no mass messaging, no scraping.
```

## Field-by-field guidance

### App title

Use a neutral name that describes your infrastructure or service.

Recommended:

- `Zip2Telegraph Bot Infra`
- `Zip2Telegraph Service`

Avoid:

- Names that pretend to be official Telegram products
- Names containing `Telegram` unless you understand Telegram's naming rules

### Short name

This is a simple identifier for the application.

Recommended style:

- lower-case letters and digits
- no spaces
- short but readable

Example:

- `zip2telegraphinfra`

### URL

Use any stable project URL you control.

Recommended:

- GitHub repository URL
- Project homepage
- VPS domain if you have one

Example:

- `https://github.com/<your-account>/zip2telegraph-bot`

### Platform

For this project, `Desktop` is a practical choice.

The local `telegram-bot-api` server runs on your VPS, but this field is mainly
descriptive. What matters is that the application is a legitimate developer app
for your infrastructure.

### Description

Keep it short, factual, and non-suspicious.

Good description:

```text
Self-hosted infrastructure for a private Telegram bot that processes ZIP image archives and publishes Telegraph pages. Used to run the official local telegram-bot-api server for large file handling. No spam, no mass messaging, no scraping.
```

## Step-by-step application process

1. Open `https://my.telegram.org`
2. Sign in with the phone number of your Telegram account
3. Enter the login code sent by Telegram
4. Open `API development tools`
5. Fill the application form using the suggested values above
6. Submit the form
7. Copy the generated `api_id`
8. Copy the generated `api_hash`

After successful creation, place them into your VPS `.env` file:

```env
USE_LOCAL_TELEGRAM_BOT_API=true
TELEGRAM_API_ID=123456
TELEGRAM_API_HASH=replace-with-your-real-value
```

## Important notes

- `api_hash` is sensitive and should be treated like a secret
- Do not commit `TELEGRAM_API_ID` and `TELEGRAM_API_HASH` to Git
- Do not put these values into GitHub Actions if you are following this
  repository's current minimal-secrets deployment model
- Store them only in the VPS-side `.env`

## Telegram policy note

Telegram's API Terms say:

- your application title must not contain `Telegram` unless it is prefixed by
  `Unofficial`
- you must not use Telegram's logo

Official reference:

- `https://core.telegram.org/api/terms`

## Related project documents

- `docs/local-bot-api.md`
- `docs/deployment-vps.md`
