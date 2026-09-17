#!/usr/bin/env python3
"""Re-authorize Gmail OAuth with compose scope and upload-ready token.json."""

from __future__ import annotations

from auth import SCOPES_COMPOSE, get_gmail_service


def main() -> int:
    service = get_gmail_service(scopes=SCOPES_COMPOSE)
    profile = service.users().getProfile(userId="me").execute()
    email = profile.get("emailAddress", "?")
    print(f"Authorized Gmail compose access for {email}.")
    print("Next: cd tools/gmail && ./cloud/setup_secrets.sh")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
