"""Shared fixtures: minimal valid cases built from the real dataset."""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.schema import load_cases  # noqa: E402

DATA = os.path.join(os.path.dirname(__file__), "..", "data", "cases.jsonl")


def cases():
    return load_cases(DATA)


def case_by_id(case_id: str):
    for c in cases():
        if c["id"] == case_id:
            return c
    raise KeyError(case_id)


def canonical_policy():
    from src.policy import POLICIES
    return POLICIES["canonical_damage"]["text"]
