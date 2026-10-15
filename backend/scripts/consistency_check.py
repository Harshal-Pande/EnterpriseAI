"""Cross-Domain Consistency Checker (Phase 7).

Performs read-only validation across Inventory, Procurement, Logistics, Orders, and Finance.
Can be executed as a standalone CLI script or imported by FastAPI system endpoints.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def run_consistency_checks(conn) -> Dict[str, Any]:
    """Execute integrity checks across operational domains and return structured report."""
    violations: List[Dict[str, Any]] = []

    with conn.cursor() as cur:
        # 1. Inventory: Reserved > On Hand
        cur.execute("""
            SELECT inventory_id, item_id, warehouse_id, on_hand_qty, reserved_qty
            FROM inventory
            WHERE reserved_qty > on_hand_qty;
        """)
        for r in cur.fetchall():
            violations.append({
                "domain": "INVENTORY",
                "code": "INV_RESERVED_EXCEEDS_ON_HAND",
                "entity": f"inventory:{r[0]}",
                "details": f"Item {r[1]} in warehouse {r[2]} has reserved ({r[4]}) > on_hand ({r[3]}).",
            })

        # 2. Inventory: Arithmetic mismatch available != on_hand - reserved
        cur.execute("""
            SELECT inventory_id, item_id, warehouse_id, on_hand_qty, reserved_qty, available_qty
            FROM inventory
            WHERE ABS(available_qty - (on_hand_qty - reserved_qty)) > 0.01;
        """)
        for r in cur.fetchall():
            violations.append({
                "domain": "INVENTORY",
                "code": "INV_AVAILABLE_ARITHMETIC_MISMATCH",
                "entity": f"inventory:{r[0]}",
                "details": f"Item {r[1]} in warehouse {r[2]} has available={r[5]} != on_hand({r[3]}) - reserved({r[4]}).",
            })

        # 3. Orders: Order lines referencing non-existent product
        cur.execute("""
            SELECT ol.order_line_id, ol.order_id, ol.product_id
            FROM order_lines ol
            LEFT JOIN products p ON ol.product_id = p.product_id
            WHERE p.product_id IS NULL;
        """)
        for r in cur.fetchall():
            violations.append({
                "domain": "ORDERS",
                "code": "ORD_ORPHAN_PRODUCT_LINE",
                "entity": f"order_lines:{r[0]}",
                "details": f"Order line {r[0]} for order {r[1]} references unknown product '{r[2]}'.",
            })

        # 4. Orders: COMPLETED order with undelivered/in-transit shipments
        cur.execute("""
            SELECT o.order_id, s.shipment_id, s.status
            FROM orders o
            JOIN shipments s ON o.order_id = s.order_id
            WHERE o.status = 'COMPLETED' AND s.status NOT IN ('DELIVERED', 'CANCELLED');
        """)
        for r in cur.fetchall():
            violations.append({
                "domain": "LOGISTICS_ORDERS",
                "code": "ORD_COMPLETED_WITH_PENDING_SHIPMENT",
                "entity": f"orders:{r[0]}",
                "details": f"Order {r[0]} is COMPLETED but shipment {r[1]} is in status '{r[2]}'.",
            })

        # 5. Finance: Budget available arithmetic reconciliation
        cur.execute("""
            SELECT
                b.budget_id,
                b.cost_center,
                b.approved_limit_inr,
                b.committed_spend_inr,
                b.available_budget_inr
            FROM budgets b
            WHERE ABS(b.available_budget_inr - (b.approved_limit_inr - b.committed_spend_inr)) > 0.01;
        """)
        for r in cur.fetchall():
            violations.append({
                "domain": "FINANCE",
                "code": "FIN_BUDGET_ARITHMETIC_MISMATCH",
                "entity": f"budgets:{r[0]}",
                "details": f"Budget {r[0]} ({r[1]}): available {r[4]:,.2f} != limit({r[2]:,.2f}) - committed({r[3]:,.2f}).",
            })

        # 6. Negative inventory balances
        cur.execute("""
            SELECT inventory_id, item_id, on_hand_qty, available_qty
            FROM inventory
            WHERE on_hand_qty < 0 OR available_qty < 0 OR reserved_qty < 0;
        """)
        for r in cur.fetchall():
            violations.append({
                "domain": "INVENTORY",
                "code": "INV_NEGATIVE_STOCK",
                "entity": f"inventory:{r[0]}",
                "details": f"Item {r[1]} has negative inventory balances: on_hand={r[2]}, avail={r[3]}.",
            })

    status_str = "HEALTHY" if not violations else "VIOLATIONS_FOUND"
    return {
        "status": status_str,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "violations_count": len(violations),
        "violations": violations,
    }


def main():
    parser = argparse.ArgumentParser(description="Run cross-domain consistency checks.")
    parser.add_argument(
        "--env-var",
        default="DATABASE_URL",
        help="Environment variable for database connection (default: DATABASE_URL)",
    )
    args = parser.parse_args()

    from db.connection import connect

    conn = connect(args.env_var)
    try:
        report = run_consistency_checks(conn)
        print(json.dumps(report, indent=2))
        if report["violations_count"] > 0:
            print(f"\nFAILED: {report['violations_count']} domain consistency violations found.", file=sys.stderr)
            sys.exit(1)
        else:
            print("\nPASSED: Zero cross-domain consistency violations detected.", file=sys.stderr)
            sys.exit(0)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
