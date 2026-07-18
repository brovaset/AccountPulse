"""Read-only Gmail client for AccountPulse communication signals."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

from tools._http import HttpClientError, request_json

DEFAULT_QUERY_MAP = {
    "acc_001": "northwind OR budget OR renewal",
    "333055649511": "northwind OR budget OR renewal",
    "acc_002": "brightleaf",
    "332906103502": "brightleaf",
    "acc_003": "harbor",
    "333057467115": "harbor",
}

_CONCERNED = ("budget", "frustrated", "concern", "urgent", "delay", "risk", "cancel")
_POSITIVE = ("thanks", "great", "happy", "love", "appreciate", "excellent")


class GmailClientError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def gmail_enabled() -> bool:
    provider = os.getenv("COMMUNICATION_PROVIDER", "auto").strip().lower()
    has_token = bool(
        os.getenv("GMAIL_ACCESS_TOKEN", "").strip()
        or os.getenv("GMAIL_REFRESH_TOKEN", "").strip()
    )
    if provider == "mock":
        return False
    if provider == "gmail":
        return True
    return has_token


def _query_map() -> dict[str, str]:
    raw = os.getenv("GMAIL_QUERY_MAP", "").strip()
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return {str(k): str(v) for k, v in parsed.items()}
        except json.JSONDecodeError:
            pass
    return dict(DEFAULT_QUERY_MAP)


def _refresh_access_token() -> str:
    refresh = os.getenv("GMAIL_REFRESH_TOKEN", "").strip()
    client_id = os.getenv("GMAIL_CLIENT_ID", "").strip()
    client_secret = os.getenv("GMAIL_CLIENT_SECRET", "").strip()
    if not (refresh and client_id and client_secret):
        raise GmailClientError(
            "communication_unavailable",
            "Gmail token expired/missing; set GMAIL_ACCESS_TOKEN or "
            "GMAIL_REFRESH_TOKEN + GMAIL_CLIENT_ID/SECRET",
        )
    body = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh,
            "grant_type": "refresh_token",
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=body,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise GmailClientError(
            "communication_unavailable",
            f"Gmail token refresh failed: HTTP {exc.code}: {detail[:200]}",
        ) from exc
    access = (payload.get("access_token") or "").strip()
    if not access:
        raise GmailClientError(
            "communication_unavailable",
            "Gmail token refresh returned no access_token",
        )
    os.environ["GMAIL_ACCESS_TOKEN"] = access
    return access


def _token() -> str:
    token = os.getenv("GMAIL_ACCESS_TOKEN", "").strip()
    if token:
        return token
    return _refresh_access_token()


def _request(path: str, *, query: dict[str, str] | None = None) -> Any:
    url = f"https://gmail.googleapis.com/gmail/v1/users/me{path}"
    try:
        return request_json(
            "GET",
            url,
            headers={"Authorization": f"Bearer {_token()}"},
            query=query,
        )
    except HttpClientError as exc:
        # Retry once after refresh on auth failures.
        if "401" in exc.message or "403" in exc.message:
            try:
                access = _refresh_access_token()
                return request_json(
                    "GET",
                    url,
                    headers={"Authorization": f"Bearer {access}"},
                    query=query,
                )
            except (HttpClientError, GmailClientError):
                pass
        code = (
            "account_not_found"
            if exc.code == "account_not_found"
            else "communication_unavailable"
        )
        raise GmailClientError(code, exc.message) from exc


def _message_datetime(payload: dict[str, Any]) -> datetime | None:
    headers = {
        (h.get("name") or "").lower(): h.get("value") or ""
        for h in ((payload.get("payload") or {}).get("headers") or [])
    }
    date_header = headers.get("date")
    if date_header:
        try:
            return parsedate_to_datetime(date_header).astimezone(timezone.utc)
        except (TypeError, ValueError, IndexError):
            pass
    internal = payload.get("internalDate")
    if internal:
        try:
            return datetime.fromtimestamp(int(internal) / 1000, tz=timezone.utc)
        except (TypeError, ValueError):
            return None
    return None


def _snippet_sentiment(texts: list[str]) -> tuple[str, float]:
    blob = " ".join(texts).lower()
    if any(w in blob for w in _CONCERNED):
        return "concerned", -0.4
    if any(w in blob for w in _POSITIVE):
        return "positive", 0.4
    return "neutral", 0.0


def fetch_gmail_communication_account(account_id: str) -> dict[str, Any]:
    """Fetch recent Gmail threads matching the account query map."""

    term = _query_map().get(account_id, account_id)
    # Keep query simple and read-only; avoid inventing mailbox contents.
    query = os.getenv(
        "GMAIL_SEARCH_TEMPLATE",
        'newer_than:30d ({term})',
    ).format(term=term)

    listing = _request(
        "/messages",
        query={"q": query, "maxResults": "20"},
    )
    message_refs = listing.get("messages") or []
    if not message_refs:
        raise GmailClientError(
            "account_not_found",
            f"No Gmail messages matched query for account {account_id}",
        )

    snippets: list[str] = []
    subjects: list[str] = []
    datetimes: list[datetime] = []
    for ref in message_refs[:10]:
        mid = ref.get("id")
        if not mid:
            continue
        msg = _request(
            f"/messages/{mid}",
            query={"format": "full"},
        )
        snippet = (msg.get("snippet") or "").strip()
        if snippet:
            snippets.append(snippet)
        headers = {
            (h.get("name") or "").lower(): h.get("value") or ""
            for h in ((msg.get("payload") or {}).get("headers") or [])
        }
        subject = headers.get("subject")
        if subject:
            subjects.append(subject)
        dt = _message_datetime(msg)
        if dt:
            datetimes.append(dt)

    now = datetime.now(timezone.utc)
    last_dt = max(datetimes) if datetimes else None
    days_since = (now - last_dt).days if last_dt else 30
    sentiment, score = _snippet_sentiment(snippets + subjects)
    follow_up = any(
        re.search(r"\b(follow[- ]?up|can you|please reply|waiting)\b", t, re.I)
        for t in snippets + subjects
    )
    trend = "declining" if days_since >= 14 or sentiment == "concerned" else "stable"

    summary = snippets[0] if snippets else (subjects[0] if subjects else "")
    return {
        "account_id": account_id,
        "last_meaningful_contact_date": (
            last_dt.date().isoformat() if last_dt else None
        ),
        "days_since_last_meaningful_contact": days_since,
        "recent_email_count_30d": len(message_refs),
        "recent_meeting_count_30d": 0,
        "sentiment": sentiment,
        "sentiment_score": score,
        "communication_trend": trend,
        "recent_summary": summary[:400],
        "no_meaningful_contact_over_14_days": days_since >= 14,
        "customer_requested_follow_up": follow_up,
        "data_source": "gmail",
        "gmail_query": query,
    }
