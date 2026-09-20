"""Vercel adapter for GET /api/data.

Same payload as demo/server.py: rules run live via src.run.run_one("rules");
LLM agents replay data/replay/*.json. Stdlib only. No API keys.

GET /api/data is instrumented with OpenTelemetry-compatible spans. Export is
off unless BOUNCER_OTEL_FILE is set, so the Vercel demo is unchanged.
"""

from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from demo.server import build_payload  # noqa: E402
from src.otel import SPAN_KIND_SERVER, flush, start_span  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 (Vercel / stdlib API)
        try:
            with start_span(
                "GET /api/data",
                kind=SPAN_KIND_SERVER,
                attributes={"http.request.method": "GET", "http.route": "/api/data"},
            ):
                body = json.dumps(build_payload()).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)
        finally:
            flush()

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))
