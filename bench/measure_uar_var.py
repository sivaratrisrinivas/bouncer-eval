#!/usr/bin/env python3
"""GS-T4: Unsafe Action Rate and Valid Automation Rate per model.

Closest harness: src/run.py (run_one). Run from a clean checkout:

    python bench/measure_uar_var.py

Writes bench/results/uar_var.json and prints a markdown table.
"""
from __future__ import annotations

import json
import os
import platform
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from src.adapters import LLMAdapter, make_adapter  # noqa: E402
from src.graders import grade_case  # noqa: E402
from src.metrics import aggregate  # noqa: E402
from src.run import run_one  # noqa: E402
from src.schema import load_cases  # noqa: E402
from src.tools import StoreSimulator  # noqa: E402

DATASET = "data/cases.jsonl"
OUT_PATH = ROOT / "bench" / "results" / "uar_var.json"
DEFAULT_SMALL = "llama3.1-8b"
DEFAULT_MID = "llama-3.3-70b"
REPLAY_PATHS = {
    "cheap": ROOT / "data" / "replay" / "cheap.json",
    "strong": ROOT / "data" / "replay" / "strong.json",
}
REPLAY_DATE = "2026-08-16"
REPLAY_HARDWARE = (
    "Cerebras public endpoint; original runner hardware was not stored in the fixture"
)


def env(*names: str, default: str = "") -> str:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return default


def get_api_key() -> str:
    return env("BOUNCER_API_KEY", "BOUNCER_API_KEY", "CEREBRAS_API_KEY", "OPENAI_API_KEY")


def get_base_url() -> str:
    return env(
        "BOUNCER_BASE_URL",
        "BOUNCER_BASE_URL",
        default="https://api.openai.com/v1",
    ).rstrip("/")


def get_hardware() -> Dict[str, Any]:
    cpu = ""
    try:
        with open("/proc/cpuinfo", encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("model name"):
                    cpu = line.split(":", 1)[1].strip()
                    break
    except OSError:
        cpu = platform.processor() or "unknown"
    return {
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "cpu": cpu or (platform.processor() or "unknown"),
        "cpus": os.cpu_count(),
    }


def hw_label(hw: Dict[str, Any]) -> str:
    return f"{hw['system']} {hw['machine']}, {hw['cpus']} CPUs, {hw['cpu']}"


def probe(model: str, key: str, endpoint: str) -> Tuple[bool, str]:
    if not key:
        return False, (
            "missing API key (BOUNCER_API_KEY, CEREBRAS_API_KEY, or OPENAI_API_KEY)"
        )
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 4,
        "temperature": 0,
    }
    req = urllib.request.Request(
        f"{endpoint}/chat/completions",
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode())
        if not body.get("choices"):
            return False, f"empty choices from {endpoint} model={model}"
        return True, "ok"
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        return False, f"HTTP {exc.code} calling {endpoint} model={model}: {detail}"
    except urllib.error.URLError as exc:
        return False, f"URL error calling {endpoint} model={model}: {exc.reason}"
    except (TimeoutError, json.JSONDecodeError, OSError) as exc:
        return False, f"{type(exc).__name__} calling {endpoint} model={model}: {exc}"


def run_adapter(adapter: Any, dataset: str) -> Dict[str, Any]:
    cases = load_cases(dataset)
    graded: List[Dict[str, Any]] = []
    for case in cases:
        store = StoreSimulator(case)
        outcome = adapter.run_case(case, store)
        graded.append(
            grade_case(
                case,
                outcome["result"],
                store,
                model=adapter.name,
                used_reads=outcome["used_reads"],
            )
        )
    summary = aggregate(graded)
    return {"model": adapter.name, "summary": summary, "results": graded}


def rates_from_summary(summary: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "n": summary["n"],
        "task_success_rate": summary["task_success_rate"],
        "unsafe_action_rate": summary["unsafe_action_rate"],
        "unsafe_action_count": summary["unsafe_action_count"],
        "valid_automation_rate": summary["valid_automation_rate"],
        "valid_automation_count": summary["valid_automation_count"],
        "expected_act_count": summary["expected_act_count"],
    }


def rates_from_replay(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload["results"]
    if isinstance(rows, dict):
        rows = list(rows.values())
    return {
        "model": payload.get("model"),
        "summary": aggregate(rows),
        "n_records": len(rows),
    }


def row_failed(slot: str, model: str, error: str, today: str, hw: str, n: int) -> Dict[str, Any]:
    return {
        "slot": slot,
        "model": model,
        "status": "failed",
        "source": "none",
        "error": error,
        "date": today,
        "dataset_size": n,
        "hardware": hw,
        "unsafe_action_rate": None,
        "valid_automation_rate": None,
        "unsafe_action_count": None,
        "valid_automation_count": None,
        "expected_act_count": None,
        "task_success_rate": None,
    }


def row_ok(
    slot: str,
    model: str,
    source: str,
    rates: Dict[str, Any],
    date: str,
    hw: str,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    row = {
        "slot": slot,
        "model": model,
        "status": "ok",
        "source": source,
        "error": None,
        "date": date,
        "dataset_size": rates["n"],
        "hardware": hw,
        "task_success_rate": rates["task_success_rate"],
        "unsafe_action_rate": rates["unsafe_action_rate"],
        "unsafe_action_count": rates["unsafe_action_count"],
        "valid_automation_rate": rates["valid_automation_rate"],
        "valid_automation_count": rates["valid_automation_count"],
        "expected_act_count": rates["expected_act_count"],
    }
    if extra:
        row.update(extra)
    return row


def measure_live(
    slot: str,
    model_name: str,
    adapter: Any,
    today: str,
    hw: str,
    n: int,
    key: str,
    endpoint: str,
) -> Dict[str, Any]:
    ok, err = probe(model_name, key, endpoint)
    if not ok:
        return row_failed(slot, model_name, err, today, hw, n)
    run = run_adapter(adapter, DATASET)
    return row_ok(slot, run["model"], "live", rates_from_summary(run["summary"]), today, hw)


def measure_cheap_or_strong(
    slot: str,
    today: str,
    hw: str,
    n: int,
    key: str,
    endpoint: str,
) -> Dict[str, Any]:
    adapter = make_adapter(slot)
    live = measure_live(slot, adapter.model, adapter, today, hw, n, key, endpoint)
    if live["status"] == "ok":
        return live
    replay = rates_from_replay(REPLAY_PATHS[slot])
    return row_ok(
        slot,
        replay["model"],
        "replay_fixture",
        rates_from_summary(replay["summary"]),
        REPLAY_DATE,
        REPLAY_HARDWARE,
        extra={
            "live_attempt": {
                "ok": False,
                "error": live["error"],
                "probed_model": adapter.model,
            },
            "replay_path": str(REPLAY_PATHS[slot].relative_to(ROOT)),
            "replay_records": replay["n_records"],
        },
    )


def print_table(rows: List[Dict[str, Any]]) -> None:
    print("| Slot | Model | Source | UAR | VAR | n | Date | Hardware |")
    print("|---|---|---|---|---|---|---|---|")
    for row in rows:
        if row["status"] != "ok":
            uar = "failed"
            var = row["error"]
        else:
            uar = (
                f"{row['unsafe_action_rate']}% "
                f"({row['unsafe_action_count']}/{row['dataset_size']})"
            )
            var = (
                f"{row['valid_automation_rate']}% "
                f"({row['valid_automation_count']}/{row['expected_act_count']})"
            )
        hw = row["hardware"]
        if len(hw) > 80:
            hw = hw[:77] + "..."
        print(
            f"| {row['slot']} | {row['model']} | {row['source']} | {uar} | {var} | "
            f"{row['dataset_size']} | {row['date']} | {hw} |"
        )


def main() -> int:
    today = datetime.now(timezone.utc).date().isoformat()
    hw = get_hardware()
    label = hw_label(hw)
    n = len(load_cases(DATASET))
    key = get_api_key()
    endpoint = get_base_url()
    if key:
        os.environ.setdefault("BOUNCER_API_KEY", key)
    os.environ.setdefault("BOUNCER_BASE_URL", endpoint)

    rows: List[Dict[str, Any]] = []
    rules = run_one("rules", DATASET)
    rows.append(
        row_ok(
            "rules",
            rules["model"],
            "live",
            rates_from_summary(rules["summary"]),
            today,
            label,
        )
    )
    rows.append(measure_cheap_or_strong("cheap", today, label, n, key, endpoint))
    rows.append(measure_cheap_or_strong("strong", today, label, n, key, endpoint))

    extras = [
        ("small", env("BOUNCER_SMALL_MODEL", "BOUNCER_SMALL_MODEL", default=DEFAULT_SMALL)),
        ("mid", env("BOUNCER_MID_MODEL", "BOUNCER_MID_MODEL", default=DEFAULT_MID)),
    ]
    for slot, model_name in extras:
        adapter = LLMAdapter(
            model_name,
            profile="strong",
            api_key=key or None,
            base_url=endpoint,
        )
        rows.append(measure_live(slot, model_name, adapter, today, label, n, key, endpoint))

    payload = {
        "measurement": "gs-t4-uar-var",
        "date": today,
        "dataset": DATASET,
        "dataset_size": n,
        "hardware": hw,
        "command": "python bench/measure_uar_var.py",
        "endpoint": endpoint,
        "api_key_present": bool(key),
        "models": rows,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print_table(rows)
    print(f"\nwrote {OUT_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
