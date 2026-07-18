"""Minimal read-only HTTP helpers for live AccountPulse connectors."""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


class HttpClientError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def request_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    query: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
    timeout: float = 20,
) -> Any:
    if query:
        url = f"{url}?{urllib.parse.urlencode(query)}"
    data = None
    req_headers = {"Accept": "application/json", **(headers or {})}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(
        url, data=data, method=method, headers=req_headers
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        if exc.code == 404:
            raise HttpClientError(
                "account_not_found",
                f"HTTP 404 for {url}",
            ) from exc
        raise HttpClientError(
            "upstream_unavailable",
            f"HTTP {exc.code}: {detail[:300]}",
        ) from exc
    except urllib.error.URLError as exc:
        raise HttpClientError(
            "upstream_unavailable",
            f"Network error: {exc.reason}",
        ) from exc


def basic_auth_header(username: str, password: str) -> str:
    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode(
        "ascii"
    )
    return f"Basic {token}"
