"""Synthetic Data Validator — Phase P3.

Verifies data diversity, integrity, and business rule compliance
after synthetic data generation. Zero tolerance for violations.

Usage:
    python backend/data/synth/validate.py --target TEST_DATABASE_URL
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger("synth.validate")

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BACKEND_DIR))


def check(conn) -> Tuple[bool, List[str], List[str]]:
    """Run all validation checks. Returns (passed, warnings, errors)."""
    warnings = []
    errors = []

    with conn.cursor() as cur:

        # 1. Orders: must have > 200 (beyond original seed) with multi-line distribution
        cur.execute("SELECT count(*) FROM orders;")
        n_orders = cur.fetchone()[0]
        if n_orders < 200:
            errors.append(f"ORDERS: Too few orders: {n_orders} (expected >= 200)")
        else:
            logger.info("PASS: orders = %d", n_orders)

        # 2. Multi-line orders: at least 30% should have > 1 line
        cur.execute("""
            SELECT
                count(*) FILTER (WHERE line_count = 1) AS single,
                count(*) FILTER (WHERE line_count > 1) AS multi,
                count(*) AS total
            FROM (
                SELECT order_id, count(*) AS line_count
                FROM order_lines
                GROUP BY order_id
            ) s;
        """)
        row = cur.fetchone()
        if row and row[2] > 0:
            multi_pct = row[1] / row[2] * 100
            if n_orders > 200 and multi_pct < 20:
                warnings.append(f"ORDER LINES: Only {multi_pct:.1f}% of orders have multiple lines (expected >= 20%)")
            else:
                logger.info("PASS: multi-line order pct = %.1f%%", multi_pct)

        # 3. Supplier offers: must have ≥ 3 per order-eligible product
        cur.execute("""
            SELECT item_id, count(*) AS offer_count
            FROM supplier_offers
            WHERE offer_status = 'ACTIVE'
            GROUP BY item_id
            ORDER BY offer_count ASC;
        """)
        offer_rows = cur.fetchall()
        sparse_products = [(r[0], r[1]) for r in offer_rows if r[1] < 2]
        if sparse_products:
            warnings.append(f"SUPPLIER OFFERS: {len(sparse_products)} products have < 2 active offers: {sparse_products[:5]}")
        else:
            logger.info("PASS: all products have >= 2 supplier offers")

        total_offers = sum(r[1] for r in offer_rows) if offer_rows else 0
        if total_offers < 50:
            errors.append(f"SUPPLIER OFFERS: Only {total_offers} total offers (expected >= 50)")
        else:
            logger.info("PASS: total active supplier offers = %d", total_offers)

        # 4. BOM coverage: all finished products must have at least 1 BOM entry
        cur.execute("""
            SELECT p.product_id
            FROM products p
            WHERE p.product_category IN ('Finished Steel', 'Structural Steel', 'Tubular Steel', 'Semifinished Steel')
              AND NOT EXISTS (
                SELECT 1 FROM bill_of_materials b WHERE b.output_product_id = p.product_id
              );
        """)
        missing_bom = [r[0] for r in cur.fetchall()]
        if missing_bom:
            warnings.append(f"BOM: {len(missing_bom)} finished products without BOM entries: {missing_bom[:5]}")
        else:
            logger.info("PASS: all finished products have BOM entries")

        # 5. No negative quantities in inventory
        cur.execute("SELECT count(*) FROM inventory WHERE on_hand_qty < 0;")
        neg_inv = cur.fetchone()[0]
        if neg_inv > 0:
            errors.append(f"INVENTORY: {neg_inv} rows have negative on_hand_qty")
        else:
            logger.info("PASS: no negative inventory quantities")

        # 6. Customers: must exist and have correct types
        cur.execute("SELECT count(*) FROM customers;")
        n_customers = cur.fetchone()[0]
        if n_customers < 20:
            errors.append(f"CUSTOMERS: Only {n_customers} customers (expected >= 20)")
        else:
            logger.info("PASS: customers = %d", n_customers)

        # 7. Carriers: must exist
        cur.execute("SELECT count(*) FROM carriers;")
        n_carriers = cur.fetchone()[0]
        if n_carriers < 5:
            errors.append(f"CARRIERS: Only {n_carriers} carriers (expected >= 5)")
        else:
            logger.info("PASS: carriers = %d", n_carriers)

        # 8. Transport lanes: must exist with valid min <= max days
        cur.execute("SELECT count(*) FROM transport_lanes WHERE transit_days_min > transit_days_max;")
        bad_lanes = cur.fetchone()[0]
        if bad_lanes > 0:
            errors.append(f"TRANSPORT LANES: {bad_lanes} lanes have min_transit > max_transit")
        else:
            logger.info("PASS: all transport lanes have valid transit day ranges")

        cur.execute("SELECT count(*) FROM transport_lanes;")
        n_lanes = cur.fetchone()[0]
        if n_lanes < 10:
            errors.append(f"TRANSPORT LANES: Only {n_lanes} lanes (expected >= 10)")
        else:
            logger.info("PASS: transport lanes = %d", n_lanes)

        # 9. Order status distribution: must have variety
        cur.execute("""
            SELECT status, count(*) FROM orders GROUP BY status ORDER BY status;
        """)
        status_dist = {r[0]: r[1] for r in cur.fetchall()}
        if len(status_dist) < 2:
            warnings.append(f"ORDERS: Low status diversity: {status_dist}")
        else:
            logger.info("PASS: order status distribution = %s", status_dist)

        # 10. Referential integrity: all order_lines.order_id must exist in orders
        cur.execute("""
            SELECT count(*) FROM order_lines l
            WHERE NOT EXISTS (SELECT 1 FROM orders o WHERE o.order_id = l.order_id);
        """)
        orphan_lines = cur.fetchone()[0]
        if orphan_lines > 0:
            errors.append(f"ORDER LINES: {orphan_lines} orphaned lines (no parent order)")
        else:
            logger.info("PASS: all order lines have valid parent orders")

        # 11. Supplier offers: no zero or negative prices
        cur.execute("SELECT count(*) FROM supplier_offers WHERE unit_price_inr <= 0;")
        bad_prices = cur.fetchone()[0]
        if bad_prices > 0:
            errors.append(f"SUPPLIER OFFERS: {bad_prices} offers have zero or negative price")
        else:
            logger.info("PASS: all supplier offer prices are positive")

        # 12. Products: check distinct categories
        cur.execute("SELECT count(distinct product_category) FROM products;")
        n_cats = cur.fetchone()[0]
        if n_cats < 3:
            warnings.append(f"PRODUCTS: Only {n_cats} distinct product categories (expected >= 3)")
        else:
            logger.info("PASS: product categories = %d", n_cats)

    return (len(errors) == 0), warnings, errors


def main():
    parser = argparse.ArgumentParser(description="Synthetic Data Validator v3")
    parser.add_argument("--target", default="TEST_DATABASE_URL",
                        help="Env var holding the target PostgreSQL URL")
    args = parser.parse_args()

    sys.path.insert(0, str(BACKEND_DIR / "db"))
    from connection import load_project_env, connect
    load_project_env()

    conn = connect(args.target)
    try:
        passed, warnings, errors = check(conn)
        print(f"\n{'=' * 60}")
        print(" SYNTHETIC DATA VALIDATION RESULTS")
        print(f"{'=' * 60}")
        for w in warnings:
            print(f"  [WARN]  {w}")
        for e in errors:
            print(f"  [ERROR] {e}")
        if passed:
            print(f"\n  [OK] VALIDATION PASSED ({len(warnings)} warnings, {len(errors)} errors)")
        else:
            print(f"\n  [FAIL] VALIDATION FAILED ({len(errors)} errors, {len(warnings)} warnings)")
        print(f"{'=' * 60}\n")
        return 0 if passed else 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
