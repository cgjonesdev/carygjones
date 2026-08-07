#!/usr/bin/env python3
"""Local-only HTTP helper: admin UI on localhost can trigger GCS → repo sync."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
SYNC_SCRIPT = REPO_ROOT / "tools" / "gmail" / "sync_gcs_inbox.py"
DEFAULT_PORT = int(os.environ.get("LOCAL_SYNC_PORT", "8765"))
ALLOWED_ORIGINS = {
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://localhost:8765",
    "http://127.0.0.1:8765",
}


def _cors_origin(handler: BaseHTTPRequestHandler) -> str:
    origin = handler.headers.get("Origin", "")
    if origin in ALLOWED_ORIGINS:
        return origin
    host = handler.headers.get("Host", "")
    if host.startswith("localhost:") or host.startswith("127.0.0.1:"):
        return origin or f"http://{host.split(':')[0]}:{host.split(':')[-1]}"
    return "http://localhost:8080"


class SyncHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write(f"[local-sync] {self.address_string()} {fmt % args}\n")

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", _cors_origin(self))
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", _cors_origin(self))
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
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
        self._send_json(404, {"error": "Not found"})

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

        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length).decode() if length else "{}"
        try:
            body = json.loads(raw) if raw.strip() else {}
        except json.JSONDecodeError:
            self._send_json(400, {"error": "Invalid JSON body"})
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
            build = subprocess.run(
                [sys.executable, str(REPO_ROOT / "scripts" / "build_admin_data.py")],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                check=False,
            )
            rebuild_out = (build.stdout or build.stderr or "").strip()
            if build.returncode != 0:
                self._send_json(
                    500,
                    {
                        "error": "build_admin_data.py failed",
                        "sync_stdout": proc.stdout.strip(),
                        "stderr": build.stderr.strip(),
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
    print("  Use admin → Pull from GCS when serving website on localhost:8080")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
