#!/usr/bin/env python3
"""Local-only HTTP helper: admin UI on localhost can sync GCS and save application settings."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
CLOUD_RUN = REPO_ROOT / "tools" / "cloud_run"
SYNC_SCRIPT = REPO_ROOT / "tools" / "gmail" / "sync_gcs_inbox.py"
BUILD_SCRIPT = REPO_ROOT / "scripts" / "build_admin_data.py"
DEFAULT_PORT = int(os.environ.get("LOCAL_SYNC_PORT", "8765"))
ALLOWED_ORIGINS = {
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://localhost:8765",
    "http://127.0.0.1:8765",
}
APP_PATH_RE = re.compile(r"^/api/applications/([^/]+)/?$")


def _cloud_run_imports():
    if str(CLOUD_RUN) not in sys.path:
        sys.path.insert(0, str(CLOUD_RUN))
    from app_settings import apply_settings_update, settings_from_meta

    return apply_settings_update, settings_from_meta


def _cors_origin(handler: BaseHTTPRequestHandler) -> str:
    origin = handler.headers.get("Origin", "")
    if origin in ALLOWED_ORIGINS:
        return origin
    host = handler.headers.get("Host", "")
    if host.startswith("localhost:") or host.startswith("127.0.0.1:"):
        return origin or f"http://{host.split(':')[0]}:{host.split(':')[-1]}"
    return "http://localhost:8080"


def load_local_meta(slug: str) -> dict | None:
    path = REPO_ROOT / "applications" / slug / "meta.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_local_meta(slug: str, meta: dict) -> None:
    app_dir = REPO_ROOT / "applications" / slug
    app_dir.mkdir(parents=True, exist_ok=True)
    path = app_dir / "meta.json"
    path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")


def upload_meta_to_gcs(slug: str, meta: dict) -> bool:
    if not os.environ.get("GCS_BUCKET", "").strip():
        return False
    try:
        if str(CLOUD_RUN) not in sys.path:
            sys.path.insert(0, str(CLOUD_RUN))
        import gcs_apps

        gcs_apps.save_app_meta(slug, meta)
        return True
    except Exception as exc:
        sys.stderr.write(f"[local-sync] GCS upload skipped: {exc}\n")
        return False


def rebuild_admin_data() -> tuple[bool, str]:
    proc = subprocess.run(
        [sys.executable, str(BUILD_SCRIPT)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    output = (proc.stdout or proc.stderr or "").strip()
    return proc.returncode == 0, output


def application_response(slug: str, meta: dict) -> dict:
    apply_settings_update, settings_from_meta = _cloud_run_imports()
    _ = apply_settings_update
    settings = settings_from_meta(meta)
    return {
        "slug": slug,
        "company": meta.get("company"),
        "role": meta.get("role"),
        "location": meta.get("location"),
        "match_score": meta.get("match_score"),
        "status": meta.get("status"),
        "updated": meta.get("updated"),
        "apply_url": meta.get("apply_url"),
        "apply_method": meta.get("apply_method"),
        "gmail_draft_id": meta.get("gmail_draft_id"),
        "interview_url": meta.get("interview_url"),
        "settings": settings,
    }


class SyncHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write(f"[local-sync] {self.address_string()} {fmt % args}\n")

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", _cors_origin(self))
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Admin-Key")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length).decode() if length else "{}"
        try:
            return json.loads(raw) if raw.strip() else {}
        except json.JSONDecodeError as exc:
            raise ValueError("Invalid JSON body") from exc

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", _cors_origin(self))
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Admin-Key")
        self.end_headers()

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/health":
            bucket = os.environ.get("GCS_BUCKET", "")
            self._send_json(
                200,
                {
                    "status": "ok",
                    "gcs_bucket": bucket or None,
                    "repo": str(REPO_ROOT),
                },
            )
            return

        match = APP_PATH_RE.match(path)
        if match:
            slug = match.group(1)
            meta = load_local_meta(slug)
            if not meta:
                self._send_json(404, {"detail": "Application not found"})
                return
            self._send_json(200, application_response(slug, meta))
            return

        self._send_json(404, {"error": "Not found"})

    def do_PATCH(self) -> None:
        path = urlparse(self.path).path
        match = APP_PATH_RE.match(path)
        if not match:
            self._send_json(404, {"error": "Not found"})
            return

        slug = match.group(1)
        meta = load_local_meta(slug)
        if not meta:
            self._send_json(404, {"detail": "Application not found"})
            return

        try:
            body = self._read_json_body()
        except ValueError as exc:
            self._send_json(400, {"detail": str(exc)})
            return

        apply_settings_update, _ = _cloud_run_imports()
        try:
            updated = apply_settings_update(meta, body)
        except ValueError as exc:
            self._send_json(400, {"detail": str(exc)})
            return

        save_local_meta(slug, updated)
        uploaded = upload_meta_to_gcs(slug, updated)
        ok, rebuild_out = rebuild_admin_data()
        if not ok:
            self._send_json(
                500,
                {
                    "detail": "Saved meta.json but build_admin_data.py failed",
                    "stderr": rebuild_out,
                },
            )
            return

        payload = application_response(slug, updated)
        payload["saved_to_gcs"] = uploaded
        if rebuild_out:
            payload["rebuild_stdout"] = rebuild_out
        self._send_json(200, payload)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path != "/api/sync":
            self._send_json(404, {"error": "Not found"})
            return

        if not os.environ.get("GCS_BUCKET", "").strip():
            self._send_json(
                400,
                {
                    "error": "Set GCS_BUCKET before starting the sync server.",
                    "hint": "GCS_BUCKET=cgjonesdev-recruiter-inbox python scripts/local_sync_server.py",
                },
            )
            return

        try:
            body = self._read_json_body()
        except ValueError as exc:
            self._send_json(400, {"error": str(exc)})
            return

        applications = body.get("applications", True)
        inbox = body.get("inbox", True)
        rebuild = body.get("rebuild_admin_data", True)

        cmd = [sys.executable, str(SYNC_SCRIPT)]
        if inbox and applications:
            cmd.append("--all")
        elif applications:
            cmd.append("--applications")

        try:
            proc = subprocess.run(
                cmd,
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError as exc:
            self._send_json(500, {"error": str(exc)})
            return

        if proc.returncode != 0:
            self._send_json(
                500,
                {
                    "error": "sync_gcs_inbox.py failed",
                    "stderr": proc.stderr.strip(),
                    "stdout": proc.stdout.strip(),
                },
            )
            return

        rebuild_out = ""
        if rebuild:
            ok, rebuild_out = rebuild_admin_data()
            if not ok:
                self._send_json(
                    500,
                    {
                        "error": "build_admin_data.py failed",
                        "sync_stdout": proc.stdout.strip(),
                        "stderr": rebuild_out,
                    },
                )
                return

        self._send_json(
            200,
            {
                "status": "ok",
                "sync_stdout": proc.stdout.strip(),
                "rebuild_stdout": rebuild_out,
            },
        )


def main() -> int:
    port = DEFAULT_PORT
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    server = ThreadingHTTPServer(("127.0.0.1", port), SyncHandler)
    bucket = os.environ.get("GCS_BUCKET", "")
    print(f"Local GCS sync server on http://127.0.0.1:{port}")
    print(f"  Repo:   {REPO_ROOT}")
    print(f"  Bucket: {bucket or '(set GCS_BUCKET)'}")
    print("  Admin UI: Pull from GCS + save application settings on localhost")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
