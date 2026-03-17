from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from zip2telegraph_bot.errors import UserVisibleError


logger = logging.getLogger(__name__)


class TelegraphClient:
    def __init__(
        self,
        api_url: str,
        short_name: str,
        author_name: str,
        author_url: str | None,
        access_token: str | None,
    ) -> None:
        self._api_url = api_url.rstrip("/")
        self._short_name = short_name
        self._author_name = author_name
        self._author_url = author_url
        self._access_token = access_token
        self._http = httpx.AsyncClient(timeout=120)

    async def close(self) -> None:
        await self._http.aclose()

    async def ensure_account(self) -> None:
        if self._access_token:
            return

        payload = {
            "short_name": self._short_name,
            "author_name": self._author_name,
        }
        if self._author_url:
            payload["author_url"] = self._author_url

        response = await self._http.post(f"{self._api_url}/createAccount", data=payload)
        result = self._extract_result(response, "ERR_TELEGRAPH_ACCOUNT")
        self._access_token = result["access_token"]
        logger.warning("telegraph access token created; persist TELEGRAPH_ACCESS_TOKEN=%s", self._access_token)

    async def create_page(self, title: str, image_urls: list[str]) -> str:
        await self.ensure_account()
        content = self._build_content(title, image_urls)
        content_json = json.dumps(content, ensure_ascii=False, separators=(",", ":"))
        if len(content_json.encode("utf-8")) > 64 * 1024:
            raise UserVisibleError("ERR_PAGE_CONTENT_TOO_LARGE", "页面内容超过 Telegraph 64KB 限制")

        payload = {
            "access_token": self._access_token,
            "title": title,
            "author_name": self._author_name,
            "content": content_json,
            "return_content": "false",
        }
        if self._author_url:
            payload["author_url"] = self._author_url

        response = await self._http.post(f"{self._api_url}/createPage", data=payload)
        result = self._extract_result(response, "ERR_PAGE_CREATE_FAILED")
        url = result.get("url")
        if not url:
            raise UserVisibleError("ERR_PAGE_CREATE_FAILED", "Telegraph 页面返回缺少 URL")
        return str(url)

    def _build_content(self, title: str, image_urls: list[str]) -> list[dict[str, Any]]:
        content: list[dict[str, Any]] = [{"tag": "h3", "children": [title]}]
        for image_url in image_urls:
            content.append({"tag": "p", "children": [{"tag": "img", "attrs": {"src": image_url}}]})
        return content

    def _extract_result(self, response: httpx.Response, error_code: str) -> dict[str, Any]:
        if response.status_code >= 400:
            raise UserVisibleError(error_code, f"Telegraph API HTTP {response.status_code}")

        payload = response.json()
        if not payload.get("ok"):
            error_message = payload.get("error", "UNKNOWN_ERROR")
            raise UserVisibleError(error_code, f"Telegraph API 错误: {error_message}")
        result = payload.get("result")
        if not isinstance(result, dict):
            raise UserVisibleError(error_code, "Telegraph API 返回格式异常")
        return result
