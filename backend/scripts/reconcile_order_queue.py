"""Reconcile development order processing queue, historical completed orders, and demo budgets.

Usage:
    python backend/scripts/reconcile_order_queue.py
    python backend/scripts/reconcile_order_queue.py --database-url-var TEST_DATABASE_URL

Idempotent:
- Reconciles exactly 100 historical orders with status 'COMPLETED' (capped processed history).
- Reconciles exactly 100 pending orders with status 'QUEUED' in order_processing_queue (positions 1..100).
- Updates/ensures rich diversity across products, lines, quantities, customers, and entities.
- Idempotently raises demonstration budgets while maintaining budget arithmetic.
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_BACKEND = _HERE.parent
for p in (_BACKEND, _BACKEND / "db", _BACKEND / "data"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from connection import connect, get_database_url

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("reconcile_order_queue")

CUSTOMERS = [
    "Tata Motors Commercial",
    "Mahindra & Mahindra Automotive",
    "Larsen & Toubro Heavy Eng",
    "Bharat Forge Precision",
    "JSW Infrastructure Projects",
    "BHEL Power Equipment",
    "Godrej Aerospace Division",
    "Maruti Suzuki India",
    "Ashok Leyland Fleet",
    "Jindal Steel & Power",
    "Adani Ports & SEZ",
    "Tata Steel BSL Fabricators",
    "Steel Authority of India Ltd",
    "Sundram Fasteners",
    "Thermax Industrial Boilers",
    "Siemens Energy India",
    "Alstom Transport India",
    "Hyundai Motor India",
    "Kirloskar Oil Engines",
    "Caterpillar India Mining",
]

PRODUCTS_SPEC = [
    ("PRD-HRC", "Hot Rolled Coil", "MT", Decimal("72000.00")),
    ("PRD-CRC", "Cold Rolled Coil", "MT", Decimal("84500.00")),
    ("PRD-REB", "Rebar", "MT", Decimal("61000.00")),
    ("PRD-PLT", "Steel Plate", "MT", Decimal("79000.00")),
]

ENTITIES = ["EAS-HQ", "EAS-EAST", "EAS-WEST", "EAS-PORT"]
PRIORITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


def reconcile_budgets(conn) -> None:
    """Idempotently raise demonstration budgets to allow ordinary scenarios to succeed."""
    with conn.cursor() as cur:
        # BUD-PROC-2026-10: Procurement budget
        # Approved limit: 50 Cr, Committed: 10 Cr, Available: 40 Cr, Threshold: 2.5 Cr
        cur.execute(
            """
            UPDATE budgets
            SET approved_limit_inr = 500000000.00,
                committed_spend_inr = 100000000.00,
                available_budget_inr = 400000000.00,
                single_action_approval_threshold_inr = 25000000.00,
                status = 'ACTIVE',
                updated_at = NOW()
            WHERE budget_id = 'BUD-PROC-2026-10';
            """
        )
        # BUD-OPS-2026-10: Operations budget
        cur.execute(
            """
            UPDATE budgets
            SET approved_limit_inr = 500000000.00,
                committed_spend_inr = 150000000.00,
                available_budget_inr = 350000000.00,
                single_action_approval_threshold_inr = 50000000.00,
                status = 'ACTIVE',
                updated_at = NOW()
            WHERE budget_id = 'BUD-OPS-2026-10';
            """
        )
        conn.commit()
    logger.info("Budgets successfully updated to demo operational limits.")


def reconcile_orders_and_queue(conn) -> None:
    """Ensure exactly 100 completed history orders and 100 queued pending orders."""
    now = datetime.now(timezone.utc)
    rng = random.Random(42)  # Deterministic seed for reproducibility

    with conn.cursor() as cur:
        # Fetch all existing orders in order_id order
        cur.execute("SELECT order_id, customer_ref, entity_id, status, priority FROM orders ORDER BY order_id;")
        orders = cur.fetchall()
        total_orders = len(orders)
        logger.info("Found %d existing orders in database.", total_orders)

        if total_orders < 200:
            logger.warning("Fewer than 200 orders found (%d). Reconciling available orders.", total_orders)

        # Split: First 100 orders -> Pending queue (ORD-1042 to ORD-1141)
        # Remaining orders (up to 100) -> Historical completed orders (ORD-1142 to ORD-1241)
        queued_orders = orders[:100]
        completed_orders = orders[100:200]
        reconciled_ids = [o[0] for o in queued_orders] + [o[0] for o in completed_orders]

        # Clean up any extraneous queue entries and transient test orders from past test runs
        cur.execute(
            """
            DELETE FROM order_processing_queue
            WHERE NOT (order_id = ANY(%s));
            """,
            (reconciled_ids,),
        )
        cur.execute(
            """
            DELETE FROM order_lines
            WHERE order_id NOT IN (SELECT order_id FROM order_processing_queue)
              AND order_id ~ '^ORD-[0-9]+$'
              AND CAST(SUBSTRING(order_id FROM 5) AS INTEGER) > 1241;
            """
        )
        cur.execute(
            """
            DELETE FROM orders
            WHERE order_id NOT IN (SELECT order_id FROM order_processing_queue)
              AND order_id ~ '^ORD-[0-9]+$'
              AND CAST(SUBSTRING(order_id FROM 5) AS INTEGER) > 1241;
            """
        )

        logger.info("Assigning %d orders to QUEUED queue and %d orders to COMPLETED history.", len(queued_orders), len(completed_orders))

        # 1. Reconcile Completed Orders (History)
        for idx, (ord_id, cust_ref, ent_id, status, priority) in enumerate(completed_orders):
            completed_time = now - timedelta(hours=idx + 1)
            # Update order status in orders table to COMPLETED
            cur.execute(
                """
                UPDATE orders
                SET status = 'COMPLETED',
                    updated_at = %s
                WHERE order_id = %s;
                """,
                (completed_time, ord_id),
            )
            # Maintain cross-domain consistency: completed orders must have DELIVERED shipments
            cur.execute(
                """
                UPDATE shipments
                SET status = 'DELIVERED', updated_at = %s
                WHERE order_id = %s AND status NOT IN ('DELIVERED', 'CANCELLED');
                """,
                (completed_time, ord_id),
            )
            # Insert or update in order_processing_queue as COMPLETED
            cur.execute(
                """
                INSERT INTO order_processing_queue (
                    order_id, queue_position, status, enqueued_at, claimed_at, completed_at, attempt_count, origin
                )
                VALUES (%s, 0, 'COMPLETED', %s, %s, %s, 1, 'SEED')
                ON CONFLICT (order_id) DO UPDATE
                SET status = 'COMPLETED',
                    queue_position = 0,
                    completed_at = EXCLUDED.completed_at;
                """,
                (ord_id, completed_time - timedelta(minutes=15), completed_time - timedelta(minutes=10), completed_time),
            )

        # 2. Reconcile Queued Orders (Queue positions 1 to 100)
        for idx, (ord_id, cust_ref, ent_id, status, priority) in enumerate(queued_orders):
            pos = idx + 1
            enq_time = now - timedelta(minutes=(100 - idx) * 2)

            # Preserve ORD-1042's operational status 'AT_RISK' as required by tests and exception demo
            order_table_status = "AT_RISK" if ord_id == "ORD-1042" else ("IN_PROGRESS" if ord_id == "ORD-1043" else "OPEN")

            cur.execute(
                """
                UPDATE orders
                SET status = %s,
                    updated_at = %s
                WHERE order_id = %s;
                """,
                (order_table_status, enq_time, ord_id),
            )

            # Insert or update in order_processing_queue as QUEUED
            cur.execute(
                """
                INSERT INTO order_processing_queue (
                    order_id, queue_position, status, enqueued_at, attempt_count, origin
                )
                VALUES (%s, %s, 'QUEUED', %s, 0, 'SEED')
                ON CONFLICT (order_id) DO UPDATE
                SET queue_position = EXCLUDED.queue_position,
                    status = 'QUEUED',
                    enqueued_at = EXCLUDED.enqueued_at;
                """,
                (ord_id, pos, enq_time),
            )

        # 3. Enhance diversity and add multi-line items deterministically
        # Ensure customer names, entities, and varied order lines
        for idx, (ord_id, _, orig_ent, _, _) in enumerate(queued_orders + completed_orders):
            cust = "CUST-036" if ord_id == "ORD-1042" else CUSTOMERS[idx % len(CUSTOMERS)]
            ent = orig_ent if ord_id == "ORD-1042" else ENTITIES[idx % len(ENTITIES)]
            cur.execute("UPDATE orders SET customer_ref = %s, entity_id = %s WHERE order_id = %s;", (cust, ent, ord_id))

            # Check existing order lines
            cur.execute("SELECT order_line_id FROM order_lines WHERE order_id = %s;", (ord_id,))
            lines = cur.fetchall()

            # Ensure primary line uses one of the products deterministically
            prod = PRODUCTS_SPEC[idx % len(PRODUCTS_SPEC)]
            qty = Decimal(str(rng.randint(15, 120)))
            unit_price = prod[3]

            if lines:
                first_line_id = lines[0][0]
                # Keep ORD-1042's original product/qty intact for test_get_single_order_with_lines
                if ord_id != "ORD-1042":
                    cur.execute(
                        """
                        UPDATE order_lines
                        SET product_id = %s, requested_qty = %s, unit_price_inr = %s, uom = %s
                        WHERE order_line_id = %s;
                        """,
                        (prod[0], qty, unit_price, prod[2], first_line_id),
                    )
            else:
                # Insert line if missing
                line_id = f"LN-{ord_id}-01"
                cur.execute(
                    """
                    INSERT INTO order_lines (order_line_id, order_id, product_id, requested_qty, unit_price_inr, uom)
                    VALUES (%s, %s, %s, %s, %s, %s);
                    """,
                    (line_id, ord_id, prod[0], qty, unit_price, prod[2]),
                )

            # For 35% of orders (excluding ORD-1042), ensure a second line exists for multi-line diversity
            if ord_id != "ORD-1042" and idx % 3 == 0:
                second_prod = PRODUCTS_SPEC[(idx + 1) % len(PRODUCTS_SPEC)]
                second_qty = Decimal(str(rng.randint(10, 80)))
                second_line_id = f"LN-{ord_id}-02"
                cur.execute(
                    """
                    INSERT INTO order_lines (order_line_id, order_id, product_id, requested_qty, unit_price_inr, uom)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (order_line_id) DO UPDATE
                    SET product_id = EXCLUDED.product_id,
                        requested_qty = EXCLUDED.requested_qty,
                        unit_price_inr = EXCLUDED.unit_price_inr;
                    """,
                    (second_line_id, ord_id, second_prod[0], second_qty, second_prod[3], second_prod[2]),
                )

        # 4. Create initial demo exceptions if not already present
        demo_exceptions = [
            (
                "ORD-1042",
                "HIGH",
                "BUDGET_BREACH",
                "Single order purchase cost ₹17.38 Cr exceeds delegated approval threshold limit ₹2.50 Cr.",
                "FINANCE",
                "OPEN",
                {
                    "recommended_action": "REQUEST_FINANCE_APPROVAL",
                    "rationale": "High-volume strategic automotive requisition exceeding delegated limit requires VP Finance sign-off.",
                    "estimated_cost_inr": 173800000.0,
                    "risk_level": "MEDIUM",
                },
            ),
            (
                "ORD-1044",
                "CRITICAL",
                "SUPPLIER_UNAVAILABLE",
                "Primary Bokaro steel mill reported 15 MT slab inventory stockout.",
                "PROCUREMENT",
                "AWAITING_APPROVAL",
                {
                    "recommended_action": "REROUTE_SUPPLIER",
                    "rationale": "Secondary supplier SUP-002 possesses matching Grade A inventory available for immediate dispatch.",
                    "target_supplier_id": "SUP-002",
                    "risk_level": "HIGH",
                },
            ),
            (
                "ORD-1045",
                "MEDIUM",
                "DELIVERY_DELAY",
                "Freight corridor weather bottleneck adds 36 hours beyond promised customer SLA.",
                "LOGISTICS",
                "PROPOSED",
                {
                    "recommended_action": "EXPEDITE_FREIGHT",
                    "rationale": "Priority dedicated green corridor rail freight can recover 24 hours.",
                    "estimated_delay_recovery_hours": 24,
                    "risk_level": "LOW",
                },
            ),
        ]

        for exc_ord_id, sev, exc_type, cause_text, owner, exc_status, rec in demo_exceptions:
            cur.execute(
                "SELECT exception_id FROM operational_exceptions WHERE order_id = %s;",
                (exc_ord_id,),
            )
            if not cur.fetchone():
                cur.execute(
                    """
                    INSERT INTO operational_exceptions (
                        order_id, severity, exception_type, cause, owner_role, status, ai_recommendation
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb);
                    """,
                    (exc_ord_id, sev, exc_type, cause_text, owner, exc_status, json.dumps(rec)),
                )

        conn.commit()
    logger.info("Successfully reconciled orders, lines, queue, and demo exceptions.")


def main():
    parser = argparse.ArgumentParser(description="Reconcile order queue and demo dataset")
    parser.add_argument("--database-url-var", default="DATABASE_URL", help="Environment variable for database connection")
    args = parser.parse_args()

    url = get_database_url(args.database_url_var)
    if not url:
        logger.error("Database connection URL not set for %s", args.database_url_var)
        sys.exit(1)

    conn = connect(args.database_url_var)
    try:
        reconcile_budgets(conn)
        reconcile_orders_and_queue(conn)
        logger.info("Reconciliation completed successfully.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
