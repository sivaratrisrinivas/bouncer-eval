"""OpenTelemetry file exporter on the live GET /api/data path."""

from __future__ import annotations

import json
import subprocess
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen

from demo.server import Handler, build_payload
from src.otel import (
    SPAN_KIND_SERVER,
    configure,
    exported_spans,
    flush,
    reset,
    start_span,
)


def setup_function(_function):
    reset()


def teardown_function(_function):
    reset()


def test_start_span_is_noop_when_disabled(tmp_path):
    out = tmp_path / "trace.json"
    with start_span("should-not-record"):
        pass
    assert exported_spans() == []
    assert flush() is None
    assert not out.exists()


def test_build_payload_emits_named_eval_and_replay_spans(tmp_path):
    out = tmp_path / "trace.json"
    configure(file_path=out, enabled=True)
    payload = build_payload()
    path = flush()

    assert path == out
    assert payload["n_cases"] == 50
    assert payload["agents"][0]["source"] == "live"
    assert payload["agents"][1]["source"] == "replay"
    assert exported_spans() == []

    data = json.loads(out.read_text(encoding="utf-8"))
    spans = data["resourceSpans"][0]["scopeSpans"][0]["spans"]
    names = {s["name"] for s in spans}
    for expected in (
        "demo.build_payload",
        "demo.load_cases",
        "demo.load_policies",
        "demo.rules_live",
        "eval.run_one",
        "eval.load_cases",
        "eval.make_adapter",
        "eval.run_and_grade",
        "eval.aggregate",
        "demo.replay_strong",
        "demo.replay_cheap",
        "demo.assemble",
    ):
        assert expected in names
    assert len({s["traceId"] for s in spans}) == 1


def test_http_get_writes_server_span_and_otlp_file(tmp_path):
    out = tmp_path / "demo-api-data.otlp.json"
    configure(file_path=out, enabled=True)

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = "http://127.0.0.1:%d" % httpd.server_address[1]
    try:
        with urlopen(base + "/api/data") as resp:
            assert resp.status == 200
            data = json.load(resp)
        assert data["n_cases"] == 50
        assert data["agents"][0]["source"] == "live"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)

    assert out.exists()
    otlp = json.loads(out.read_text(encoding="utf-8"))
    resource = otlp["resourceSpans"][0]["resource"]["attributes"]
    service = next(a["value"]["stringValue"] for a in resource if a["key"] == "service.name")
    assert service == "bouncer-eval"

    spans = otlp["resourceSpans"][0]["scopeSpans"][0]["spans"]
    by_name = {s["name"]: s for s in spans}
    assert "GET /api/data" in by_name
    root = by_name["GET /api/data"]
    assert root["kind"] == SPAN_KIND_SERVER
    assert "parentSpanId" not in root
    assert root["status"]["code"] == 1
    children = [s for s in spans if s.get("parentSpanId") == root["spanId"]]
    assert any(s["name"] == "demo.build_payload" for s in children)


def test_payload_unchanged_when_tracing_is_on(tmp_path):
    cold = build_payload()
    configure(file_path=tmp_path / "trace.json", enabled=True)
    hot = build_payload()
    assert hot["n_cases"] == cold["n_cases"]
    assert {a["id"]: a["source"] for a in hot["agents"]} == {
        a["id"]: a["source"] for a in cold["agents"]
    }
    assert hot["results"]["rules"].keys() == cold["results"]["rules"].keys()
    assert hot["agents"][0]["summary"] == cold["agents"][0]["summary"]


def test_committed_example_trace_is_otlp_json():
    path = Path(__file__).resolve().parents[1] / "docs" / "traces" / "demo-api-data.otlp.json"
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    spans = data["resourceSpans"][0]["scopeSpans"][0]["spans"]
    names = {s["name"] for s in spans}
    assert "GET /api/data" in names
    assert "demo.rules_live" in names
    assert "eval.run_and_grade" in names
    assert "demo.replay_strong" in names


def test_python_m_src_otel_captures_real_http_trace(tmp_path):
    out = tmp_path / "cli.otlp.json"
    root = Path(__file__).resolve().parents[1]
    subprocess.check_call(
        [sys.executable, "-m", "src.otel", "--out", str(out)],
        cwd=root,
    )
    data = json.loads(out.read_text(encoding="utf-8"))
    names = {s["name"] for s in data["resourceSpans"][0]["scopeSpans"][0]["spans"]}
    assert "GET /api/data" in names
    assert "eval.run_one" in names
    assert len(names) >= 13


def test_flush_clears_buffer_so_snapshots_do_not_merge(tmp_path):
    out = tmp_path / "trace.json"
    configure(file_path=out, enabled=True)
    with start_span("first"):
        pass
    flush()
    assert exported_spans() == []
    first_ids = {
        s["traceId"]
        for s in json.loads(out.read_text(encoding="utf-8"))["resourceSpans"][0]["scopeSpans"][0]["spans"]
    }
    with start_span("second"):
        pass
    flush()
    assert exported_spans() == []
    spans = json.loads(out.read_text(encoding="utf-8"))["resourceSpans"][0]["scopeSpans"][0]["spans"]
    names = [s["name"] for s in spans]
    assert names == ["second"]
    assert {s["traceId"] for s in spans} != first_ids


def test_http_flush_on_error_exports_error_span(tmp_path, monkeypatch):
    out = tmp_path / "error.otlp.json"
    configure(file_path=out, enabled=True)

    def boom():
        raise RuntimeError("payload failed")

    monkeypatch.setattr("demo.server.build_payload", boom)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = "http://127.0.0.1:%d" % httpd.server_address[1]
    try:
        try:
            urlopen(base + "/api/data")
        except Exception:
            pass
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)

    spans = json.loads(out.read_text(encoding="utf-8"))["resourceSpans"][0]["scopeSpans"][0]["spans"]
    by_name = {s["name"]: s for s in spans}
    assert "GET /api/data" in by_name
    assert by_name["GET /api/data"]["status"]["code"] == 2
    assert by_name["GET /api/data"]["status"].get("message") == "RuntimeError"
