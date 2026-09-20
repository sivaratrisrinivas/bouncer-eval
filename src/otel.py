"""OpenTelemetry-compatible tracing for one live Bouncer path.

Stdlib only. No collector, no API keys. When tracing is off (the default),
`start_span` is a no-op so the Vercel demo and deterministic grading stay
unchanged. Enable with `BOUNCER_OTEL_FILE` (explicit path) or `BOUNCER_OTEL=1`
(defaults the path to docs/traces/demo-api-data.otlp.json). Finished spans
are written as OTLP JSON (the same shape an OTLP/HTTP JSON exporter would
POST). Each `flush()` is one trace snapshot: it writes the current buffer
and then clears it.

Usage:
    python3 -m src.otel
    BOUNCER_OTEL_FILE=docs/traces/demo-api-data.otlp.json python3 demo/server.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

# OTLP span.kind enum (opentelemetry.proto.trace.v1.Span.SpanKind)
SPAN_KIND_INTERNAL = 1
SPAN_KIND_SERVER = 2

# OTLP status.code enum (Status.StatusCode). 1 = OK, 2 = ERROR.
STATUS_UNSET = 0
STATUS_OK = 1
STATUS_ERROR = 2

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRACE_PATH = ROOT / "docs" / "traces" / "demo-api-data.otlp.json"

_current: ContextVar[Optional["Span"]] = ContextVar("bouncer_otel_span", default=None)


def _hex_id(n_bytes: int) -> str:
    return os.urandom(n_bytes).hex()


def _any_value(value: Any) -> Dict[str, Any]:
    if isinstance(value, bool):
        return {"boolValue": value}
    if isinstance(value, int):
        return {"intValue": str(value)}
    if isinstance(value, float):
        return {"doubleValue": value}
    return {"stringValue": str(value)}


def _otlp_attributes(attrs: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [{"key": key, "value": _any_value(value)} for key, value in attrs.items()]


class NullSpan:
    """Returned when tracing is off. Attribute writes are ignored."""

    def set_attribute(self, key: str, value: Any) -> "NullSpan":
        return self


class Span:
    def __init__(
        self,
        name: str,
        *,
        trace_id: str,
        span_id: str,
        parent_span_id: str,
        kind: int,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.name = name
        self.trace_id = trace_id
        self.span_id = span_id
        self.parent_span_id = parent_span_id
        self.kind = kind
        self.attributes: Dict[str, Any] = dict(attributes or {})
        self.start_time_unix_nano = time.time_ns()
        self.end_time_unix_nano = 0
        self.status_code = STATUS_UNSET
        self.status_message = ""

    def set_attribute(self, key: str, value: Any) -> "Span":
        self.attributes[key] = value
        return self

    def end(self, status_code: int = STATUS_OK, status_message: str = "") -> None:
        if self.end_time_unix_nano == 0:
            self.end_time_unix_nano = time.time_ns()
        self.status_code = status_code
        self.status_message = status_message

    def to_otlp(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "traceId": self.trace_id,
            "spanId": self.span_id,
            "name": self.name,
            "kind": self.kind,
            "startTimeUnixNano": str(self.start_time_unix_nano),
            "endTimeUnixNano": str(self.end_time_unix_nano),
            "attributes": _otlp_attributes(self.attributes),
            "status": {"code": self.status_code},
        }
        if self.parent_span_id:
            payload["parentSpanId"] = self.parent_span_id
        if self.status_message:
            payload["status"]["message"] = self.status_message
        return payload


class Tracer:
    def __init__(self) -> None:
        self.enabled = False
        self.file_path: Optional[Path] = None
        self.service_name = "bouncer-eval"
        self.scope_name = "bouncer.demo"
        self.scope_version = "0.1"
        self._spans: List[Span] = []
        self._lock = threading.Lock()

    def configure(
        self,
        file_path: Optional[str | os.PathLike[str]] = None,
        enabled: Optional[bool] = None,
    ) -> None:
        path = file_path if file_path is not None else os.environ.get("BOUNCER_OTEL_FILE")
        env_flag = os.environ.get("BOUNCER_OTEL", "").strip().lower()
        env_on = env_flag in ("1", "true", "yes", "on")
        self.file_path = Path(path) if path else None
        if enabled is not None:
            self.enabled = enabled
        else:
            self.enabled = bool(self.file_path) or env_on
        if self.enabled and self.file_path is None:
            self.file_path = DEFAULT_TRACE_PATH

    def reset(self) -> None:
        with self._lock:
            self._spans.clear()
        self.enabled = False
        self.file_path = None

    def record(self, span: Span) -> None:
        with self._lock:
            self._spans.append(span)

    def spans(self) -> List[Span]:
        with self._lock:
            return list(self._spans)

    def export_otlp(self) -> Dict[str, Any]:
        return self._otlp_doc(self.spans())

    def _otlp_doc(self, spans: List[Span]) -> Dict[str, Any]:
        return {
            "resourceSpans": [
                {
                    "resource": {
                        "attributes": _otlp_attributes(
                            {
                                "service.name": self.service_name,
                                "telemetry.sdk.language": "python",
                                "telemetry.sdk.name": "bouncer-stdlib-otel",
                                "telemetry.sdk.version": self.scope_version,
                            }
                        )
                    },
                    "scopeSpans": [
                        {
                            "scope": {
                                "name": self.scope_name,
                                "version": self.scope_version,
                            },
                            "spans": [s.to_otlp() for s in spans],
                        }
                    ],
                }
            ]
        }

    def flush(self) -> Optional[Path]:
        """Write the current buffer as one OTLP JSON snapshot, then clear it.

        One call is one `resourceSpans` document (typically one GET /api/data
        trace). Clearing keeps a long-running `demo/server.py` from growing
        without bound or merging multiple traceIds into a single file.
        """
        if not self.enabled or self.file_path is None:
            return None
        path = self.file_path
        with self._lock:
            snapshot = list(self._spans)
            self._spans.clear()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self._otlp_doc(snapshot), indent=2) + "\n", encoding="utf-8")
        return path


_tracer = Tracer()
_tracer.configure()


def configure(
    file_path: Optional[str | os.PathLike[str]] = None,
    enabled: Optional[bool] = None,
) -> None:
    _tracer.configure(file_path=file_path, enabled=enabled)


def reset() -> None:
    _tracer.reset()
    token = _current.set(None)
    _current.reset(token)


def flush() -> Optional[Path]:
    return _tracer.flush()


def exported_spans() -> List[Span]:
    return _tracer.spans()


@contextmanager
def start_span(
    name: str,
    *,
    kind: int = SPAN_KIND_INTERNAL,
    attributes: Optional[Dict[str, Any]] = None,
) -> Iterator[NullSpan | Span]:
    if not _tracer.enabled:
        yield NullSpan()
        return

    parent = _current.get()
    if parent is None:
        trace_id = _hex_id(16)
        parent_span_id = ""
    else:
        trace_id = parent.trace_id
        parent_span_id = parent.span_id

    span = Span(
        name,
        trace_id=trace_id,
        span_id=_hex_id(8),
        parent_span_id=parent_span_id,
        kind=kind,
        attributes=attributes,
    )
    token = _current.set(span)
    try:
        yield span
    except Exception as exc:
        span.end(STATUS_ERROR, type(exc).__name__)
        _tracer.record(span)
        raise
    else:
        span.end(STATUS_OK)
        _tracer.record(span)
    finally:
        _current.reset(token)


def _capture_via_http(host: str, port: int) -> None:
    """Hit a real GET /api/data on an ephemeral demo server."""
    import threading
    from http.server import ThreadingHTTPServer
    from urllib.request import urlopen

    from demo.server import Handler

    httpd = ThreadingHTTPServer((host, port), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    assigned = httpd.server_address[1]
    try:
        url = f"http://{host}:{assigned}/api/data"
        with urlopen(url) as resp:
            status = resp.status
            raw = resp.read().decode()
        if status != 200:
            raise SystemExit(f"GET {url} returned {status}")
        payload = json.loads(raw)
        print(f"GET {url} -> {status}  n_cases={payload.get('n_cases')}")
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="bouncer-otel",
        description="Capture one live GET /api/data as an OTLP JSON trace.",
    )
    parser.add_argument(
        "--out",
        default=str(DEFAULT_TRACE_PATH),
        help="OTLP JSON path (default: docs/traces/demo-api-data.otlp.json)",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0, help="0 = ephemeral port")
    args = parser.parse_args(argv)

    os.chdir(ROOT)
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    reset()
    configure(file_path=args.out, enabled=True)
    _capture_via_http(args.host, args.port)
    path = Path(args.out)
    # Handler.flush() already wrote one snapshot and cleared the buffer.
    if not path.exists():
        flush()
    names: List[str] = []
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        names = [s["name"] for s in data["resourceSpans"][0]["scopeSpans"][0]["spans"]]
    print(f"spans ({len(names)}): {names}")
    print(f"trace -> {path}")
    return 0


if __name__ == "__main__":
    # `python -m src.otel` loads this file as __main__, while demo.server
    # imports src.otel. Re-dispatch so both share one tracer.
    from src.otel import main as _package_main
    sys.exit(_package_main())
