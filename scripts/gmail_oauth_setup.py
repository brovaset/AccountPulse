#!/usr/bin/env python3
"""Desktop OAuth helper to obtain a Gmail read-only refresh token for AccountPulse.

Prerequisites:
1. Google Cloud project with Gmail API enabled
2. OAuth client type "Desktop app"
3. .env contains:
   GMAIL_CLIENT_ID=...
   GMAIL_CLIENT_SECRET=...

This script opens a browser, listens on localhost:8085, then writes
GMAIL_REFRESH_TOKEN / GMAIL_ACCESS_TOKEN into .env.
"""

from __future__ import annotations

import json
import os
import threading
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
REDIRECT_URI = "http://localhost:8085/"
SCOPE = "https://www.googleapis.com/auth/gmail.readonly"


def _update_env(values: dict[str, str]) -> None:
    lines: list[str] = []
    if ENV_PATH.exists():
        lines = ENV_PATH.read_text().splitlines()
    keys = set(values)
    seen: set[str] = set()
    out: list[str] = []
    for line in lines:
        if "=" in line and not line.lstrip().startswith("#"):
            key = line.split("=", 1)[0].strip()
            if key in values:
                out.append(f"{key}={values[key]}")
                seen.add(key)
                continue
        out.append(line)
    for key, value in values.items():
        if key not in seen:
            out.append(f"{key}={value}")
    ENV_PATH.write_text("\n".join(out) + "\n")


def _post_form(url: str, data: dict[str, str]) -> dict:
    body = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    load_dotenv(ENV_PATH)
    client_id = os.getenv("GMAIL_CLIENT_ID", "").strip()
    client_secret = os.getenv("GMAIL_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        print(
            "Add these to .env first:\n"
            "  GMAIL_CLIENT_ID=...apps.googleusercontent.com\n"
            "  GMAIL_CLIENT_SECRET=...\n\n"
            "Create them in Google Cloud → APIs & Services → Credentials\n"
            "→ Create OAuth client ID → Desktop app.\n"
            "Enable Gmail API for the project."
        )
        return 1

    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(
        {
            "client_id": client_id,
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "scope": SCOPE,
            "access_type": "offline",
            "prompt": "consent",
        }
    )

    result: dict[str, str] = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urllib.parse.urlparse(self.path)
            qs = urllib.parse.parse_qs(parsed.query)
            if "code" in qs:
                result["code"] = qs["code"][0]
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(
                    b"<html><body><h2>AccountPulse Gmail auth complete.</h2>"
                    b"You can close this tab.</body></html>"
                )
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Missing code")

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

    server = HTTPServer(("127.0.0.1", 8085), Handler)
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()

    print("Opening Google consent screen…")
    print(auth_url)
    webbrowser.open(auth_url)
    thread.join(timeout=180)
    server.server_close()

    if "code" not in result:
        print("Timed out waiting for OAuth redirect on http://localhost:8085/")
        return 1

    try:
        token_payload = _post_form(
            "https://oauth2.googleapis.com/token",
            {
                "code": result["code"],
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        print(f"Token exchange failed: HTTP {exc.code}: {detail[:300]}")
        return 1

    access = token_payload.get("access_token", "")
    refresh = token_payload.get("refresh_token", "")
    if not access:
        print("No access_token in Google response:", token_payload)
        return 1

    updates = {
        "COMMUNICATION_PROVIDER": "gmail",
        "GMAIL_ACCESS_TOKEN": access,
    }
    if refresh:
        updates["GMAIL_REFRESH_TOKEN"] = refresh
    else:
        print(
            "Warning: no refresh_token returned. "
            "Revoke prior app access and re-run with prompt=consent if needed."
        )

    _update_env(updates)
    print("Wrote GMAIL_ACCESS_TOKEN to .env", end="")
    if refresh:
        print(" and GMAIL_REFRESH_TOKEN")
    else:
        print()
    print(
        "Smoke test:\n"
        'python -c "from dotenv import load_dotenv; load_dotenv(); '
        "from tools.communications import fetch_communication_activity; "
        'print(fetch_communication_activity(\'acc_001\'))"'
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
