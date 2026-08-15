"""Bouncer CLI: run one adapter over the dataset, grade deterministically,
print the summary table, and write the JSON results + Markdown error report.

Usage:
    python -m src.run --model rules  --dataset data/cases.jsonl
    python -m src.run --model cheap  --dataset data/cases.jsonl
    python -m src.run --model strong --dataset data/cases.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List

from .adapters import make_adapter
from .graders import grade_case
from .metrics import aggregate, expected_action_cost
from .schema import load_cases
from .tools import StoreSimulator


def run_one(model: str, dataset: str) -> Dict[str, Any]:
    cases = load_cases(dataset)
    adapter = make_adapter(model)
    graded: List[Dict[str, Any]] = []
    for case in cases:
        store = StoreSimulator(case)
        outcome = adapter.run_case(case, store)
        result = outcome["result"]
        graded.append(grade_case(case, result, store, model=adapter.name, used_reads=outcome["used_reads"]))
    summary = aggregate(graded)
    return {"model": adapter.name, "summary": summary, "results": graded}


def print_summary(summary: Dict[str, Any]) -> None:
    s = summary
    print(f"MODEL                  {s.get('n', 0)} cases")
    print(f"TASK SUCCESS           {s['task_success_rate']}%")
    print(f"UNSAFE ACTIONS         {s['unsafe_action_rate']}%  ({s['unsafe_action_count']})")
    print(f"VALID AUTO ACTIONS     {s['valid_automation_rate']}%  ({s['valid_automation_count']}/{s['expected_act_count']})")
    print(f"MISSED ESCALATIONS     {s['missed_escalation_rate']}%")
    print(f"EXCESS ESCALATIONS     {s['excess_escalation_rate']}%")
    print(f"EXPECTED ACTION COST   ${s['expected_action_cost_usd']} (proxy)")
    print(f"AVG LATENCY            {s['avg_latency_ms']}ms")
    print(f"AVG COST               ${s['avg_cost_usd']}")
    print(f"FAILURE TAGS           {s['failure_tag_counts']}")


def write_report(model: str, run: Dict[str, Any], path: str) -> None:
    results = run["results"]
    s = run["summary"]
    cost = expected_action_cost(results)

    lines = [
        f"# Bouncer report — model `{model}`",
        "",
        f"Dataset: {run.get('_dataset', '')} · {s['n']} cases",
        "",
        "## Headline",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Task success | {s['task_success_rate']}% |",
        f"| Unsafe actions | {s['unsafe_action_rate']}% ({s['unsafe_action_count']}) |",
        f"| Valid automation | {s['valid_automation_rate']}% ({s['valid_automation_count']}/{s['expected_act_count']}) |",
        f"| Missed escalations | {s['missed_escalation_rate']}% |",
        f"| Excess escalations | {s['excess_escalation_rate']}% |",
        f"| Expected Action Cost (proxy) | ${s['expected_action_cost_usd']} |",
        "",
        f"> {cost['note']}",
        "",
        "## Per category",
        "",
        "| Category | n | success | unsafe |",
        "|---|---|---|---|",
    ]
    for cat, stats in s["by_category"].items():
        lines.append(f"| {cat} | {stats['n']} | {stats['success_rate']}% | {stats['unsafe_rate']}% |")

    lines += ["", "## Failure tags", ""]
    if s["failure_tag_counts"]:
        for tag, count in s["failure_tag_counts"].items():
            lines.append(f"- {tag}: {count}")
    else:
        lines.append("- none")

    lines += ["", "## Worst failures", ""]
    bad = [r for r in results if r["unsafe_action"] or r["failure_tags"]]
    bad.sort(key=lambda r: (
        -(int(r["arguments"].get("amount_cents", 0)) if r["unsafe_action"] else 0),
        len(r["failure_tags"]),
    ))
    for r in bad[:12]:
        args = json.dumps(r["arguments"])
        lines.append(
            f"- `{r['case_id']}` [{r['category']}] expected={r['expected_action']} "
            f"got={r['action']} args={args} unsafe={r['unsafe_action']} "
            f"tags={','.join(r['failure_tags']) or 'none'}"
        )
    if not bad:
        lines.append("- none")

    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bouncer", description="Scoped Autonomy Eval runner")
    parser.add_argument("--model", default="rules", choices=["rules", "cheap", "strong", "custom"],
                        help="adapter under test (default: rules)")
    parser.add_argument("--dataset", default="data/cases.jsonl")
    parser.add_argument("--output", default=None, help="results JSON path")
    parser.add_argument("--report", default=None, help="Markdown error report path")
    args = parser.parse_args(argv)

    output = args.output or f"results/{args.model}.json"
    report = args.report or f"results/{args.model}-report.md"

    run = run_one(args.model, args.dataset)
    run["_dataset"] = args.dataset

    with open(output, "w", encoding="utf-8") as fh:
        json.dump(run, fh, indent=2)

    write_report(args.model, run, report)

    print_summary(run["summary"])
    print(f"\nresults -> {output}")
    print(f"report  -> {report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
