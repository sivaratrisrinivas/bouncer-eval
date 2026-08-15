"""Bouncer demo server: a localhost operator console for the eval.

Serves the static console (demo/) and one API endpoint, /api/data, which
assembles everything the console needs:

  - cases      : the full 50-case dataset (data/cases.jsonl)
  - policies   : the structured merchant policies, so the console can draw the
                 real money boundary (ceiling, evidence, exclusions)
  - agents     : metadata + summaries for the three agents
  - results    : per-case graded records, keyed by agent id then case id
  - source     : how each agent's decisions were produced

Honesty contract (product principle #4): the rules engine RUNS LIVE in this
server on every /api/data request via src.run.run_one("rules"). The two LLM
agents REPLAY their recorded per-case decisions from data/replay/*.json
(committed fixtures of the last full Cerebras run — results/ is gitignored).
The console labels each slot LIVE or REPLAYED accordingly.

Stdlib only. No API keys. Money actions are never executed for real; the
grader judges them exactly as the eval does.

Usage:
    python3 demo/server.py            # http://127.0.0.1:8765
    python3 demo/server.py --port 9000
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.run import run_one  # noqa: E402  (repo root on sys.path)
from src.schema import CATEGORIES, EXPECTED_ACTIONS, TOOLS  # noqa: E402

REPLAY_DIR = ROOT / "data" / "replay"
CASES_PATH = ROOT / "data" / "cases.jsonl"
STATIC_DIR = ROOT / "demo"

REPLAY_MODELS = {"strong": "gpt-oss-120b", "cheap": "gemma-4-31b"}

MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".woff2": "font/woff2",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
}


def _policies() -> Dict[str, Any]:
    from src.policy import POLICIES
    return {
        pid: {
            "ceiling_cents": p["ceiling_cents"],
            "max_auto_refunds_60d": p["max_auto_refunds_60d"],
            "refund_scope": p["refund_scope"],
            "evidence_required": p["evidence_required"],
            "excluded_categories": p["excluded_categories"],
            "return_window_days": p["return_window_days"],
        }
        for pid, p in POLICIES.items()
    }


def _cases() -> list[Dict[str, Any]]:
    from src.schema import load_cases
    return load_cases(str(CASES_PATH))


def _replay(agent: str) -> Dict[str, Any]:
    path = REPLAY_DIR / f"{agent}.json"
    if not path.exists():
        raise FileNotFoundError(f"missing replay fixture {path} (run the eval first, then regenerate data/replay)")
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    return {"model": data["model"], "summary": data["summary"], "results": data["results"]}


def _rules_live() -> Dict[str, Any]:
    run = run_one("rules", str(CASES_PATH))
    return {
        "model": run["model"],
        "summary": run["summary"],
        "results": {r["case_id"]: r for r in run["results"]},
    }


def build_payload() -> Dict[str, Any]:
    rules = _rules_live()
    strong = _replay("strong")
    cheap = _replay("cheap")

    agents = [
        {
            "id": "rules",
            "model": rules["model"],
            "label": "Rules",
            "sub": "Baseline 0 — deterministic engine",
            "source": "live",
            "source_note": "RUN LIVE — the policy engine executed these decisions in this server.",
            "summary": rules["summary"],
        },
        {
            "id": "strong",
            "model": strong["model"],
            "label": "gpt-oss-120b",
            "sub": "strong LLM · direct autonomy",
            "source": "replay",
            "source_note": "REPLAYED — recorded Cerebras run, committed in data/replay.",
            "summary": strong["summary"],
        },
        {
            "id": "cheap",
            "model": cheap["model"],
            "label": "gemma-4-31b",
            "sub": "cheap LLM · direct autonomy",
            "source": "replay",
            "source_note": "REPLAYED — recorded Cerebras run, committed in data/replay.",
            "summary": cheap["summary"],
        },
    ]

    return {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "n_cases": len(_cases()),
        "cases": _cases(),
        "policies": _policies(),
        "catalog": {
            "categories": CATEGORIES,
            "expected_actions": EXPECTED_ACTIONS,
            "tools": TOOLS,
        },
        "agents": agents,
        "results": {
            "rules": rules["results"],
            "strong": strong["results"],
            "cheap": cheap["results"],
        },
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "BouncerDemo/0.1"

    def do_GET(self) -> None:  # noqa: N802 (stdlib API)
        if self.path == "/api/data":
            self._send_json(build_payload())
            return
        if self.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        self._serve_static(self.path)

    def _serve_static(self, path: str) -> None:
        rel = path.lstrip("/") or "index.html"
        target = (STATIC_DIR / rel).resolve()
        if not target.is_relative_to(STATIC_DIR.resolve()) or not target.exists() or target.is_dir():
            self.send_error(404, "not found")
            return
        content = target.read_bytes()
        ext = target.suffix.lower()
        self.send_response(200)
        self.send_header("Content-Type", MIME.get(ext, "application/octet-stream"))
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def _send_json(self, payload: Any) -> None:
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", MIME[".json"])
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bouncer-demo", description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args(argv)

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Bouncer operator console -> http://{args.host}:{args.port}")
    print(f"cases: {CASES_PATH}  replay: {REPLAY_DIR}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())