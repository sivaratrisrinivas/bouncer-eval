# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Static HTML/CSS/JS frontend + a tiny Python 3 stdlib `http.server` backend that
runs the eval code directly. No npm, no build step, no dependencies, no API
keys. Runs on the repo's existing Python 3.12 stdlib-only ethos.

## Users

- **Primary:** a technical hiring reviewer at Amboras who opens the demo with
  60–120 seconds to spend. They are evaluating both the eval itself and the
  person who built it, so honesty and tightness of the narrative matter as much
  as the results.
- **Secondary:** the author (Srinivas), while iterating on the eval and later
  the hybrid adapter, as a fast way to eyeball a case and its grading.

## Product Purpose

An interactive live demo of the Bouncer eval. A visitor picks one of the 50
graded cases (or skims the built-in highlights), sees the merchant policy,
store state, and customer message the agent was handed, and watches each of the
three agents — the deterministic rules engine, `gpt-oss-120b`, `gemma-4-31b` —
make its decision. Each decision is graded against the same deterministic
grader the eval uses, so the visitor sees exactly what the eval saw.

Success is the visitor leaving in under two minutes with the eval's central
claim in hand: raw LLM autonomy is ~5× less safe on money than the rule
engine, and the stronger model was the worse system — architecture beats model
choice.

## Positioning

The demo is the proof-of-work. A viewer can touch the eval's own machinery — the
rules engine genuinely runs, the LLM decisions are the real recorded runs, and
every verdict is produced by the same deterministic grader — rather than being
shown a slide deck about an eval.

## Operating Context

- Launched from the repo with `python3` only; opens in a browser on localhost.
- The reviewer has no API key and no network dependence for the LLM agents.
- The rules engine runs live against the real case; LLM agents replay their
  recorded per-case decisions from the last full Cerebras run, clearly labeled
  as such.
- Money actions are never executed for real; the simulated store logs them and
  the grader judges them, exactly as the eval does.

## Capabilities and Constraints

- All 50 cases in `data/cases.jsonl`, browsable and filterable by category.
- Three agents viewable: rules (Baseline 0), strong `gpt-oss-120b`, cheap
  `gemma-4-31b`. A fourth (hybrid) is a future possibility once built.
- Deterministic grading only — no LLM judges, matching the eval.
- `results/*.json` and `results/*.md` are gitignored, so the replayed LLM
  decisions must be committed as separate fixture data (e.g. under `data/`),
  not read from `results/` at runtime.
- `python3 -m pytest tests/ -q` must stay green (42 tests).
- No new runtime dependencies may be added to the repo.
- The eval's five actions: ACT / REPLY / ASK / ESCALATE / ABSTAIN. Eight case
  categories: clear_allowed, clear_forbidden, boundary, ambiguous, conflict,
  missing_evidence, previously_actioned, adversarial.

## Brand Commitments

Name: **Bouncer** (what decides whether an agent is let through to touch
money). No other visual or voice commitments are bound.

## Evidence on Hand

- `README.md` — the full eval narrative, metrics definitions, and results table.
- `data/cases.jsonl` — the 50 graded cases.
- `results/strong.json`, `results/cheap.json`, `results/rules.json` — recorded
  per-case decisions and summaries (gitignored; used to seed demo fixtures).
- `results/comparison.md` — the per-category and unsafe-action tables.
- All numbers in the demo must trace to these real runs; nothing is invented.

## Product Principles

1. **The machinery is the message.** The demo runs the eval's real code path —
   rules live, LLM decisions real, grader deterministic. No fake results, no
   theater, no LLM judge.
2. **Two minutes or it's too long.** The narrative must land inside the
   reviewer's attention budget; interactivity serves the story, it does not
   replace it.
3. **Zero friction.** `python3` + open a page. No keys, no installs, no network,
   no build step.
4. **Honesty about provenance.** Replayed LLM decisions are labeled as
   replays; live execution is labeled as live. The eval's known weaknesses are
   shown, not hidden.
5. **Money safety is the hero metric.** The 4-case shared blind spot
   (`refund_011/012/020/021`) is the headline, not a footnote.

## Accessibility & Inclusion

No product-specific accessibility standard is established. The default bar for
web UI applies: keyboard-operable, readable contrast, semantic structure.