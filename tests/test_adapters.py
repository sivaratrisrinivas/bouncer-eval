"""Agent-loop mechanics with a stubbed model — no API key needed.

Verifies: tool_call turns, final decision parsing, state execution, and the
permission/parse-failure paths of the LLM adapter.
"""

from tests.helpers import case_by_id

from src.adapters import LLMAdapter, _parse_json
from src.graders import grade_case
from src.schema import validate_result, CaseError
from src.tools import StoreSimulator


class StubLLM(LLMAdapter):
    """Replays canned responses in order, then asserts the loop."""

    def __init__(self, responses):
        super().__init__("stub", profile="cheap")
        self.responses = list(responses)
        self.calls = 0

    def _complete(self, messages):
        self.calls += 1
        resp = self.responses.pop(0)
        return resp, 0.0001


def test_parse_json():
    assert _parse_json('{"action": "ask", "arguments": {}}') == ({"action": "ask", "arguments": {}}, True)
    assert _parse_json('prefix {"action": "ask"} suffix') == ({"action": "ask"}, True)
    assert _parse_json("not json at all") == (None, False)


def test_tool_loop_then_refund():
    case = case_by_id("refund_001")
    store = StoreSimulator(case)
    stub = StubLLM([
        '{"action": "tool_call", "arguments": {"tool": "get_order", "arguments": {"order_id": "o_001"}}}',
        '{"action": "tool_call", "arguments": {"tool": "get_customer", "arguments": {"customer_id": "c_001"}}}',
        '{"action": "act", "arguments": {"tool": "refund", "order_id": "o_001", "amount_cents": 2200, "item_ids": ["it_1"], "reason": "damaged"}}',
    ])
    outcome = stub.run_case(case, store)
    assert stub.calls == 3
    assert outcome["used_reads"] == ["get_order", "get_customer"]
    graded = grade_case(case, validate_result(outcome["result"], case), store, "stub", outcome["used_reads"])
    assert graded["unsafe_action"] is False
    assert graded["failure_tags"] == []
    assert store.money_actions[0]["amount_cents"] == 2200


def test_refund_without_reads_is_unsafe():
    case = case_by_id("refund_001")
    store = StoreSimulator(case)
    stub = StubLLM([
        '{"action": "act", "arguments": {"tool": "refund", "order_id": "o_001", "amount_cents": 2200, "item_ids": ["it_1"], "reason": "damaged"}}',
    ])
    outcome = stub.run_case(case, store)
    assert outcome["used_reads"] == []
    graded = grade_case(case, validate_result(outcome["result"], case), store, "stub", outcome["used_reads"])
    assert graded["evidence_ok"] is False
    assert "MISSING_EVIDENCE" in graded["failure_tags"]


def test_unpermitted_tool_blocked():
    case = case_by_id("refund_014")  # permissions: no refund
    store = StoreSimulator(case)
    stub = StubLLM([
        '{"action": "act", "arguments": {"tool": "refund", "order_id": "o_014", "amount_cents": 1200, "item_ids": ["it_1"]}}',
    ])
    outcome = stub.run_case(case, store)
    result = outcome["result"]
    assert result["parse_error"] is True
    assert result["attempted_action"]["action"] == "act"
    assert store.money_actions == []  # nothing executed


def test_garbage_output_falls_back_to_abstain():
    case = case_by_id("refund_001")
    store = StoreSimulator(case)
    stub = StubLLM(["this is not json"])
    outcome = stub.run_case(case, store)
    assert outcome["result"]["action"] == "abstain"
    assert outcome["result"]["parse_error"] is True
    assert store.money_actions == []
