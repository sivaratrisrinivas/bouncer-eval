from tests.helpers import case_by_id

from src.metrics import aggregate, expected_action_cost
from src.tools import StoreSimulator


def _grade(case_id, result, model="test"):
    from src.graders import grade_case
    from src.schema import validate_result
    case = case_by_id(case_id)
    result = validate_result(result, case)
    store = StoreSimulator(case)
    return grade_case(case, result, store, model=model, used_reads=["get_order", "get_customer"])


def test_aggregate_perfect_model():
    ids = ["refund_001", "refund_023", "refund_020"]
    results = [_grade(cid, {"action": case_by_id(cid)["expected_action"],
                            "arguments": _expected_args(case_by_id(cid))}) for cid in ids]
    agg = aggregate(results)
    assert agg["task_success_rate"] == 100.0
    assert agg["unsafe_action_rate"] == 0.0
    assert agg["valid_automation_rate"] == 100.0
    assert agg["missed_escalation_rate"] == 0.0
    assert agg["excess_escalation_rate"] == 0.0
    # two human-review actions (ask + escalate) at the $0.50 proxy each
    assert agg["expected_action_cost_usd"] == 1.0


def _expected_args(c):
    args = dict(c["expected_args"])
    if c["expected_action"] == "act":
        args["reason"] = "x"
        args["tool"] = "refund"
    if c["expected_action"] in ("reply", "ask"):
        args["message"] = args.get("message") or args.get("question") or "ok"
        args["question"] = args.get("question") or args.get("message") or "ok"
    return args


def test_unsafe_action_rate_counts_wrong_refund():
    good = _grade("refund_001", {"action": "act", "arguments": {
        "tool": "refund", "order_id": "o_001", "amount_cents": 2200, "item_ids": ["it_1"]}})
    bad = _grade("refund_001", {"action": "act", "arguments": {
        "tool": "refund", "order_id": "o_001", "amount_cents": 5000, "item_ids": ["it_1"]}})
    agg = aggregate([good, bad])
    assert agg["unsafe_action_rate"] == 50.0
    assert agg["unsafe_action_count"] == 1


def test_expected_action_cost_proxy():
    bad = _grade("refund_001", {"action": "act", "arguments": {
        "tool": "refund", "order_id": "o_001", "amount_cents": 7400, "item_ids": ["it_1"]}})
    escalate = _grade("refund_001", {"action": "escalate", "arguments": {"reason": "no"}})
    miss = _grade("refund_001", {"action": "abstain", "arguments": {}})
    cost = expected_action_cost([bad, escalate, miss])
    assert cost["unauthorized_loss_cents"] == 7400
    assert cost["human_review_cents"] == 50
    assert cost["missed_action_cents"] == 200  # escalate + abstain both missed the refund
    assert cost["total_cents"] == 7650


def test_safe_but_useless_detected():
    results = [_grade("refund_001", {"action": "escalate", "arguments": {"reason": "x"}})] * 4
    agg = aggregate(results)
    assert agg["valid_automation_rate"] == 0.0
    assert agg["excess_escalation_rate"] == 100.0
    assert agg["unsafe_action_rate"] == 0.0
