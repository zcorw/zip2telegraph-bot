from __future__ import annotations

import argparse
import json
import sys
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DEFAULT_API_URL = "https://api.telegra.ph/createAccount"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a Telegraph account and print TELEGRAPH_ACCESS_TOKEN."
    )
    parser.add_argument(
        "--short-name",
        default="zip2telegraph",
        help="Telegraph short_name, default: zip2telegraph",
    )
    parser.add_argument(
        "--author-name",
        default="zip2telegraph-bot",
        help="Telegraph author_name, default: zip2telegraph-bot",
    )
    parser.add_argument(
        "--author-url",
        default="",
        help="Optional Telegraph author_url",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    payload = {
        "short_name": args.short_name,
        "author_name": args.author_name,
    }
    if args.author_url:
        payload["author_url"] = args.author_url

    request = Request(
        DEFAULT_API_URL,
        data=urlencode(payload).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
    except Exception as exc:
        print(f"Failed to create Telegraph account: {exc}", file=sys.stderr)
        return 1

    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        print(f"Invalid response from Telegraph: {exc}", file=sys.stderr)
        print(body, file=sys.stderr)
        return 1

    if not data.get("ok"):
        error = data.get("error", "UNKNOWN_ERROR")
        print(f"Telegraph API error: {error}", file=sys.stderr)
        return 1

    result = data.get("result", {})
    access_token = result.get("access_token")
    auth_url = result.get("auth_url")

    if not access_token:
        print("Telegraph response did not include access_token", file=sys.stderr)
        print(body, file=sys.stderr)
        return 1

    print("Created Telegraph account successfully.")
    print(f"TELEGRAPH_ACCESS_TOKEN={access_token}")
    if auth_url:
        print(f"TELEGRAPH_AUTH_URL={auth_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
