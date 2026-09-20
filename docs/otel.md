# OpenTelemetry on GET /api/data

Bouncer stays stdlib-only. There is no Langfuse cloud sink and no OTLP
collector to configure. The live demo path — `GET /api/data`, used by both
`demo/server.py` and the Vercel function `api/data.py` — records
OpenTelemetry spans and can dump them as OTLP JSON.

Tracing is **off** unless an export path is set. The Vercel demo and
deterministic grading do not change.

## Capture one real local request

From the repo root:

```bash
python3 -m src.otel
```

That starts the demo handler on an ephemeral port, issues `GET /api/data`
(rules engine live, LLM agents replayed), and writes:

```
docs/traces/demo-api-data.otlp.json
```

An example from a local run is committed at that path.

To attach the same exporter to the long-running demo server:

```bash
BOUNCER_OTEL_FILE=docs/traces/demo-api-data.otlp.json python3 demo/server.py
# then: curl -s http://127.0.0.1:8765/api/data > /dev/null
```

`BOUNCER_OTEL=1` enables tracing and defaults the file to the path above.

## Spans

One request produces a single trace. Meaningful steps:

| Span | What it is |
|---|---|
| `GET /api/data` | Server span for the HTTP handler |
| `demo.build_payload` | Assemble the console payload |
| `demo.load_cases` | Read `data/cases.jsonl` |
| `demo.load_policies` | Structured merchant policies |
| `demo.rules_live` | Live rules-engine eval |
| `eval.run_one` | `src.run.run_one("rules")` |
| `eval.load_cases` | Dataset load inside the eval |
| `eval.make_adapter` | Rules adapter |
| `eval.run_and_grade` | Per-case simulate + deterministic grade |
| `eval.aggregate` | Headline metrics |
| `demo.replay_strong` | Replay `data/replay/strong.json` |
| `demo.replay_cheap` | Replay `data/replay/cheap.json` |
| `demo.assemble` | Final JSON object |

The file is OTLP JSON (`resourceSpans` / `scopeSpans` / `spans`), so a
collector that accepts OTLP/HTTP JSON can ingest it later. No SDK and no
remote endpoint are required.

## Optional SDK extra

If you already have `opentelemetry-sdk` installed, you do not need it for
this path. The stdlib file exporter is the supported way to prove traces
exist without cloud secrets. Do not add the SDK as a runtime dependency of
the demo or the eval — that would break the stdlib-only Vercel deploy.
