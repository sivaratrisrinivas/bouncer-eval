"""Demo payload honesty + local server still serves the console."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen

from demo.server import Handler, build_payload


def _by_id(agents):
    return {a["id"]: a for a in agents}


def test_payload_labels_rules_live_and_llms_replayed():
    payload = build_payload()
    agents = _by_id(payload["agents"])

    assert agents["rules"]["source"] == "live"
    assert "LIVE" in agents["rules"]["source_note"]
    assert agents["strong"]["source"] == "replay"
    assert "REPLAYED" in agents["strong"]["source_note"]
    assert agents["cheap"]["source"] == "replay"
    assert "REPLAYED" in agents["cheap"]["source_note"]

    assert set(payload["results"]) == {"rules", "strong", "cheap"}
    assert payload["n_cases"] == 50
    assert len(payload["cases"]) == 50
    assert len(payload["results"]["rules"]) == 50
    assert len(payload["results"]["strong"]) == 50
    assert len(payload["results"]["cheap"]) == 50


def test_vercel_handler_uses_same_payload_builder():
    root = Path(__file__).resolve().parents[1]
    spec_path = root / "api" / "data.py"
    import importlib.util

    spec = importlib.util.spec_from_file_location("vercel_api_data", spec_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)

    assert issubclass(mod.handler, BaseHTTPRequestHandler)
    assert mod.build_payload is build_payload


def test_vercel_rewrites_map_fonts_and_other_demo_static():
    cfg = json.loads((Path(__file__).resolve().parents[1] / "vercel.json").read_text())
    rewrites = cfg["rewrites"]
    assert any(r["source"] == "/" and r["destination"] == "/demo/index.html" for r in rewrites)
    assert any(
        r["destination"] in ("/demo/:path", "/demo/:path*", "/demo/$1", "/demo/fonts/:path*")
        and (
            "fonts" in r["source"]
            or ":path" in r["source"]
            or r["source"] in ("/:path*", "/((?!api/).*)")
        )
        for r in rewrites
    )


def test_local_server_serves_static_and_api():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = "http://127.0.0.1:%d" % httpd.server_address[1]
    try:
        with urlopen(base + "/") as resp:
            html = resp.read().decode()
            assert resp.status == 200
        assert "Bouncer" in html
        assert 'src="app.js"' in html

        with urlopen(base + "/app.js") as resp:
            js = resp.read().decode()
            assert resp.status == 200
        assert "fetch(\"/api/data\")" in js

        with urlopen(base + "/style.css") as resp:
            css = resp.read().decode()
            assert resp.status == 200
        assert "fonts/archivo-400-500-600.woff2" in css

        for name in (
            "archivo-400-500-600.woff2",
            "spacemono-400.woff2",
            "spacemono-700.woff2",
        ):
            with urlopen(base + "/fonts/" + name) as resp:
                assert resp.status == 200
                assert resp.headers.get_content_type() == "font/woff2"
                assert resp.read()

        with urlopen(base + "/api/data") as resp:
            assert resp.status == 200
            assert resp.headers.get_content_type() == "application/json"
            data = json.load(resp)
        agents = _by_id(data["agents"])
        assert agents["rules"]["source"] == "live"
        assert agents["strong"]["source"] == "replay"
        assert agents["cheap"]["source"] == "replay"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)
