# Architecture

## Scope

This project is a Telegram group bot that:

1. Accepts ZIP uploads from group administrators
2. Validates and extracts image files
3. Uploads images to Telegraph-hosted URLs
4. Creates a Telegraph page with title `zip_name - YYYY-MM-DD`
5. Replies with the page URL or a structured failure reason

## Confirmed product rules

- Trigger: sending a ZIP document in a group
- Authorization: only group administrators
- Response: direct page URL on success, detailed error on failure
- Supported payload: images only, non-image files ignored
- Ordering: natural filename sort
- Failure mode: fail the whole task on any invalid content or limit breach
- Concurrency: per-group serial execution
- Rate limits:
  - per group: 1 request / 5 minutes
  - per admin user: 3 requests / hour
- Storage: SQLite
- Deployment: Docker
- Restart behavior: in-flight jobs fail; user retries by resending

## Modules

### `app.py`

Bootstraps config, logging, DB, external clients, and polling.

### `services/admins.py`

Checks whether a message sender is an admin in the current group.

### `services/rate_limit.py`

Applies group and user limits using timestamped SQLite events.

### `queue.py`

Maintains one async queue per chat and a worker task for each active chat.

### `services/zip_processor.py`

Validates the archive, prevents zip-slip extraction, enforces size limits,
normalizes images where needed, and outputs ordered image files.

### `services/telegraph.py`

Encapsulates Telegraph account creation, image upload, and page creation.

### `db.py`

Creates schema and persists task history plus rate-limit events.

## Data model

### `tasks`

- `id`
- `chat_id`
- `user_id`
- `file_name`
- `status`
- `page_url`
- `error_code`
- `error_message`
- `created_at`
- `started_at`
- `finished_at`

### `rate_limit_events`

- `scope`
- `scope_id`
- `created_at`

## Failure model

User-visible failures are normalized into stable codes, for example:

- `ERR_NOT_GROUP`
- `ERR_NOT_ADMIN`
- `ERR_UNSUPPORTED_FILE`
- `ERR_RATE_LIMITED`
- `ERR_ZIP_TOO_LARGE`
- `ERR_EMPTY_ZIP`
- `ERR_INVALID_IMAGE`
- `ERR_IMAGE_TOO_LARGE`
- `ERR_EXTRACTED_SIZE_EXCEEDED`
- `ERR_PAGE_CONTENT_TOO_LARGE`
- `ERR_PAGE_CREATE_FAILED`
- `ERR_TASK_TIMEOUT`

## Reliability notes

- Temp data is isolated per task directory
- Temp directories are deleted after completion
- Startup performs stale temp cleanup
- Each chat has exactly one active worker
- Rate-limit cleanup prunes old records opportunistically

## Constraints that matter

### Telegram file download size

Per the current Telegram Bot API docs, the public Bot API only supports file
downloads up to `20 MB`. Per the same docs, switching to a self-hosted local
Bot API server removes that download limit.

For this project:

- default deployment is simple and uses the public Bot API
- `1 GB` ZIP support is only feasible when `TELEGRAM_API_BASE` points to a
  local Bot API server

### Telegraph page content size

Per the current Telegraph API docs, `createPage` accepts content up to `64 KB`.
This project therefore validates the serialized page node payload size before
calling `createPage`.

### Telegraph image upload

The official Telegraph API docs define page creation and `img src` content, but
do not document a first-party image upload API on the same page. This scaffold
uses a dedicated `upload_image` client method pointed at `TELEGRAPH_UPLOAD_URL`
so the implementation can be swapped without touching queueing or ZIP logic.
