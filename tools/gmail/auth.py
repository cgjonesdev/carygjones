"""Gmail OAuth helpers — local files, env vars, or Secret Manager."""

from __future__ import annotations

import json
import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES_READONLY = ["https://www.googleapis.com/auth/gmail.readonly"]
SCOPES_COMPOSE = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
]
SCOPES = SCOPES_READONLY
TOOL_DIR = Path(__file__).resolve().parent
CREDENTIALS_FILE = TOOL_DIR / "credentials.json"
TOKEN_FILE = TOOL_DIR / "token.json"


def _is_cloud_runtime() -> bool:
    return bool(os.environ.get("JOB_MODE") == "cloud" or os.environ.get("K_SERVICE"))


def _load_json_env(name: str) -> dict | None:
    raw = os.environ.get(name)
    if not raw:
        return None
    return json.loads(raw)


def _load_client_config() -> dict:
    data = _load_json_env("GMAIL_CREDENTIALS_JSON")
    if data:
        return data
    if CREDENTIALS_FILE.exists():
        return json.loads(CREDENTIALS_FILE.read_text())
    raise FileNotFoundError(
        "Missing Gmail OAuth client config. Set GMAIL_CREDENTIALS_JSON or create "
        f"{CREDENTIALS_FILE}. See tools/gmail/README.md."
    )


def _load_token_data() -> dict | None:
    data = _load_json_env("GMAIL_TOKEN_JSON")
    if data:
        return data
    if TOKEN_FILE.exists():
        return json.loads(TOKEN_FILE.read_text())
    return None


def _save_token_data(creds: Credentials) -> None:
    if _is_cloud_runtime():
        return
    TOKEN_FILE.write_text(creds.to_json())


def get_gmail_service(*, scopes: list[str] | None = None):
    scopes = scopes or SCOPES_READONLY
    creds: Credentials | None = None
    token_data = _load_token_data()
    if token_data:
        creds = Credentials.from_authorized_user_info(token_data, scopes)

    needs_auth = not creds or not creds.valid
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            _save_token_data(creds)
            needs_auth = not creds.valid
        except Exception:
            needs_auth = True

    if needs_auth:
        if _is_cloud_runtime():
            raise RuntimeError(
                "Gmail token missing or expired in Cloud Run. Re-run "
                "tools/gmail/cloud/setup_secrets.sh after local OAuth."
            )
        client_config = _load_client_config()
        flow = InstalledAppFlow.from_client_config(client_config, scopes)
        creds = flow.run_local_server(port=0)
        _save_token_data(creds)

    return build("gmail", "v1", credentials=creds)
