from tests.helpers import case_by_id

from src.tools import StoreSimulator


def test_refund_logs_and_updates_status():
    store = StoreSimulator(case_by_id("refund_001"))
    assert store.refund("o_001", 2200, "damaged", ["it_1"]) is True
    assert len(store.money_actions) == 1
    assert store.money_actions[0]["amount_cents"] == 2200
    assert store.order_statuses()["o_001"] == "refunded"


def test_partial_refund_status():
    store = StoreSimulator(case_by_id("refund_009"))
    store.refund("o_009", 1800, "damaged", ["it_1"])
    assert store.order_statuses()["o_009"] == "partially_refunded"


def test_refund_unknown_order_fails_without_log():
    store = StoreSimulator(case_by_id("refund_001"))
    assert store.refund("o_nope", 100, "x") is False
    assert store.money_actions == []


def test_reply_ask_escalate_logged_no_money():
    store = StoreSimulator(case_by_id("refund_001"))
    store.reply("c_001", "hi")
    store.ask("c_001", "which?")
    store.escalate("review")
    assert len(store.log) == 3
    assert store.money_actions == []


def test_get_order_returns_snapshot():
    store = StoreSimulator(case_by_id("refund_001"))
    order = store.get_order("o_001")
    assert order["total_cents"] == 2200
    order["total_cents"] = 1
    assert store.get_order("o_001")["total_cents"] == 2200
