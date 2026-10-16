"""Tests for order queue reconciliation, 100/100 history/queue dataset, and order diversity."""

from __future__ import annotations

import pytest
from scripts.reconcile_order_queue import reconcile_budgets, reconcile_orders_and_queue


@pytest.mark.integration
def test_reconcile_idempotency_and_counts(test_conn):
    """Verify running reconciliation results in exactly 100 queued and 100 completed orders."""
    # First run
    reconcile_budgets(test_conn)
    reconcile_orders_and_queue(test_conn)

    with test_conn.cursor() as cur:
        # Check queue status counts
        cur.execute("SELECT COUNT(*) FROM order_processing_queue WHERE status = 'QUEUED';")
        queued_count = cur.fetchone()[0]
        assert queued_count == 100, f"Expected 100 queued items, got {queued_count}"

        cur.execute("SELECT COUNT(*) FROM order_processing_queue WHERE status = 'COMPLETED';")
        completed_count = cur.fetchone()[0]
        assert completed_count == 100, f"Expected 100 completed items, got {completed_count}"

        # Verify queue positions 1..100 are strictly contiguous and unique
        cur.execute("SELECT queue_position FROM order_processing_queue WHERE status = 'QUEUED' ORDER BY queue_position ASC;")
        positions = [r[0] for r in cur.fetchall()]
        assert positions == list(range(1, 101)), "Queue positions must be contiguous 1..100"

        # Verify no duplicate order_id in queue
        cur.execute("SELECT order_id, COUNT(*) FROM order_processing_queue GROUP BY order_id HAVING COUNT(*) > 1;")
        dupes = cur.fetchall()
        assert len(dupes) == 0, f"Found duplicate queue order_ids: {dupes}"

    # Second run for idempotency
    reconcile_budgets(test_conn)
    reconcile_orders_and_queue(test_conn)

    with test_conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM order_processing_queue WHERE status = 'QUEUED';")
        assert cur.fetchone()[0] == 100
        cur.execute("SELECT COUNT(*) FROM order_processing_queue WHERE status = 'COMPLETED';")
        assert cur.fetchone()[0] == 100


@pytest.mark.integration
def test_order_diversity_and_validity(test_conn):
    """Verify that orders and order lines exhibit genuine enterprise diversity."""
    with test_conn.cursor() as cur:
        # Check distinct customers
        cur.execute("SELECT COUNT(DISTINCT customer_ref) FROM orders;")
        n_cust = cur.fetchone()[0]
        assert n_cust >= 15, f"Expected >= 15 distinct customers, got {n_cust}"

        # Check distinct entities
        cur.execute("SELECT COUNT(DISTINCT entity_id) FROM orders;")
        n_entities = cur.fetchone()[0]
        assert n_entities == 4, f"Expected 4 entities, got {n_entities}"

        # Check distinct priorities
        cur.execute("SELECT COUNT(DISTINCT priority) FROM orders;")
        n_priorities = cur.fetchone()[0]
        assert n_priorities == 4, f"Expected all 4 priorities, got {n_priorities}"

        # Check distinct products in order lines
        cur.execute("SELECT COUNT(DISTINCT product_id) FROM order_lines;")
        n_prods = cur.fetchone()[0]
        assert n_prods >= 4, f"Expected >= 4 distinct products, got {n_prods}"

        # Check multi-line distribution
        cur.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT order_id FROM order_lines GROUP BY order_id HAVING COUNT(*) > 1
            ) multi;
            """
        )
        multi_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(DISTINCT order_id) FROM orders;")
        total_orders = cur.fetchone()[0]
        multi_pct = (multi_count / total_orders) * 100
        assert multi_pct >= 20.0, f"Expected >= 20% multi-line orders, got {multi_pct:.1f}%"

        # Check line arithmetic: qty > 0, unit_price > 0
        cur.execute("SELECT COUNT(*) FROM order_lines WHERE requested_qty <= 0 OR unit_price_inr <= 0;")
        invalid_lines = cur.fetchone()[0]
        assert invalid_lines == 0, "No order lines should have non-positive quantities or prices"

        # Verify referential integrity: every line has an existing order and product
        cur.execute(
            """
            SELECT COUNT(*) FROM order_lines ol
            WHERE NOT EXISTS (SELECT 1 FROM orders o WHERE o.order_id = ol.order_id)
               OR NOT EXISTS (SELECT 1 FROM products p WHERE p.product_id = ol.product_id);
            """
        )
        orphan_lines = cur.fetchone()[0]
        assert orphan_lines == 0, "No orphaned order lines allowed"


@pytest.mark.integration
def test_budget_coherence(test_conn):
    """Verify demo budgets have coherent approved, committed, and available amounts."""
    with test_conn.cursor() as cur:
        cur.execute("SELECT budget_id, approved_limit_inr, committed_spend_inr, available_budget_inr FROM budgets;")
        rows = cur.fetchall()
        assert len(rows) >= 4
        for b_id, approved, committed, available in rows:
            assert approved > 0, f"Budget {b_id} approved limit must be positive"
            assert committed >= 0, f"Budget {b_id} committed spend must be non-negative"
            assert available >= 0, f"Budget {b_id} available budget must be non-negative"
            assert approved == committed + available, f"Budget {b_id} arithmetic mismatch: {approved} != {committed} + {available}"
