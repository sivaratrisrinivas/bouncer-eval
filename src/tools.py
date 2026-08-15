"""Simulated store backend: orders, customers, and the money-touching tools.

The agent interacts with a fake-but-faithful store. Every executed action is
logged, so graders can diff state before/after with deterministic rules.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional


class StoreSimulator:
    def __init__(self, case: Dict[str, Any]):
        self.orders: Dict[str, Dict[str, Any]] = {
            case["order"]["order_id"]: copy.deepcopy(case["order"])
        }
        self.customer: Dict[str, Any] = copy.deepcopy(case["customer_history"])
        self.log: List[Dict[str, Any]] = []
        self.money_actions: List[Dict[str, Any]] = []

    # -- reads ----------------------------------------------------------------

    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        order = self.orders.get(order_id)
        return copy.deepcopy(order) if order else None

    def get_customer(self, customer_id: str) -> Optional[Dict[str, Any]]:
        if customer_id != self.customer["customer_id"]:
            return None
        return copy.deepcopy(self.customer)

    # -- acts ----------------------------------------------------------------

    def refund(self, order_id: str, amount_cents: int, reason: str = "", item_ids: Optional[List[str]] = None) -> bool:
        order = self.orders.get(order_id)
        if order is None:
            return False
        entry = {
            "action": "refund",
            "order_id": order_id,
            "amount_cents": amount_cents,
            "item_ids": list(item_ids or []),
            "reason": reason,
        }
        self.log.append(entry)
        self.money_actions.append(entry)
        order["status"] = "refunded" if amount_cents >= order["total_cents"] else "partially_refunded"
        return True

    def reply(self, customer_id: str, message: str) -> bool:
        if customer_id != self.customer["customer_id"]:
            return False
        self.log.append({"action": "reply", "customer_id": customer_id, "message": message})
        return True

    def ask(self, customer_id: str, question: str) -> bool:
        if customer_id != self.customer["customer_id"]:
            return False
        self.log.append({"action": "ask", "customer_id": customer_id, "question": question})
        return True

    def escalate(self, reason: str) -> bool:
        self.log.append({"action": "escalate", "reason": reason})
        return True

    # -- state ---------------------------------------------------------------

    def money_snapshot(self) -> List[Dict[str, Any]]:
        return copy.deepcopy(self.money_actions)

    def order_statuses(self) -> Dict[str, str]:
        return {oid: order.get("status", "") for oid, order in self.orders.items()}


def case_state(case: Dict[str, Any]) -> Dict[str, Any]:
    """The store records an agent can fetch. No expected answers live here."""
    return {
        "order": copy.deepcopy(case["order"]),
        "customer_history": copy.deepcopy(case["customer_history"]),
    }
