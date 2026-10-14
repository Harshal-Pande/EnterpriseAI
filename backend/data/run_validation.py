"""
run_validation.py — Extended validation runner for the Enterprise AI Industrial Dataset.

Reads every mapped sheet from the workbook, applies validator rules, and writes
backend/data/validation_report.json with actual row counts and findings.

Usage:
    python backend/data/run_validation.py
"""

import json
import sys
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

try:
    import openpyxl
except ImportError:
    print("ERROR: openpyxl not installed.  Run: pip install openpyxl==3.1.2")
    sys.exit(1)

from validators import (
    ValidationError,
    check_date_range,
    check_no_duplicate_ids,
    check_no_nulls,
    check_numeric_range,
    check_referential_integrity,
    check_required_columns,
    check_valid_status,
)

WORKBOOK_PATH = (
    Path(__file__).parent.parent.parent
    / "project_reference"
    / "enterprise_ai_industrial_dataset_v2.xlsx"
)
OUTPUT_PATH = Path(__file__).parent / "validation_report.json"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def sheet_to_records(ws) -> tuple[list[str], list[dict]]:
    """Return (columns, records) from an openpyxl worksheet (values_only)."""
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return [], []
    headers = [str(h) if h is not None else f"COL_{i}" for i, h in enumerate(rows[0])]
    records = []
    for row in rows[1:]:
        rec = {}
        for i, val in enumerate(row):
            col = headers[i] if i < len(headers) else f"COL_{i}"
            rec[col] = val
        records.append(rec)
    return headers, records


def build_ref_set(records: list[dict], col: str) -> set:
    """Collect non-null values from a column into a set."""
    return {str(r[col]).strip() for r in records if r.get(col) is not None}


def errors_to_findings(errors: list[ValidationError]) -> list[dict]:
    """Aggregate ValidationError list into compact findings grouped by rule+column."""
    grouped: dict = defaultdict(lambda: {"rule": "", "severity": "", "column": "", "count": 0, "examples": []})
    for e in errors:
        key = (e.rule, e.column, e.severity)
        g = grouped[key]
        g["rule"] = e.rule
        g["severity"] = e.severity
        g["column"] = e.column
        g["count"] += 1
        if len(g["examples"]) < 5:
            g["examples"].append(str(e.value))
    return list(grouped.values())


# ---------------------------------------------------------------------------
# Validation rules per sheet
# ---------------------------------------------------------------------------

def validate_all(wb) -> dict:
    """Run all validations and return a structured results dict."""
    all_errors: list[ValidationError] = []
    sheet_results: list[dict] = []

    # ---- Load reference sets first (needed for FK checks) ----
    entities_ws   = wb["ref_entities"]
    products_ws   = wb["ref_products"]
    warehouses_ws = wb["ref_warehouses"]
    suppliers_ws  = wb["ref_suppliers"]
    roles_ws      = wb["ref_roles"]
    prod_lines_ws = wb["ref_production_lines"]
    orders_ws     = wb["orders"]
    batches_ws    = wb["production_batches"]
    assets_ws     = wb["maintenance_assets"]
    shipments_ws  = wb["shipments"]
    po_ws         = wb["purchase_orders"]

    _, ent_records   = sheet_to_records(entities_ws)
    _, prod_records  = sheet_to_records(products_ws)
    _, wh_records    = sheet_to_records(warehouses_ws)
    _, sup_records   = sheet_to_records(suppliers_ws)
    _, role_records  = sheet_to_records(roles_ws)
    _, pl_records    = sheet_to_records(prod_lines_ws)
    _, ord_records   = sheet_to_records(orders_ws)
    _, bat_records   = sheet_to_records(batches_ws)
    _, ast_records   = sheet_to_records(assets_ws)
    _, shp_records   = sheet_to_records(shipments_ws)
    _, po_records    = sheet_to_records(po_ws)

    entity_ids    = build_ref_set(ent_records,  "entity_id")
    product_ids   = build_ref_set(prod_records, "product_id")
    warehouse_ids = build_ref_set(wh_records,   "warehouse_id")
    supplier_ids  = build_ref_set(sup_records,  "supplier_id")
    role_ids      = build_ref_set(role_records, "role_id")
    pl_ids        = build_ref_set(pl_records,   "production_line_id")
    order_ids     = build_ref_set(ord_records,  "order_id")
    batch_ids     = build_ref_set(bat_records,  "batch_id")
    asset_ids     = build_ref_set(ast_records,  "asset_id")
    shipment_ids  = build_ref_set(shp_records,  "shipment_id")
    po_ids        = build_ref_set(po_records,   "po_id")

    # Date bounds: the workbook scenario is set in Oct 2026
    MIN_DATE = date(2025, 1, 1)
    MAX_DATE = date(2028, 12, 31)

    # -----------------------------------------------------------------------
    # Sheet-by-sheet validation blocks
    # -----------------------------------------------------------------------

    def run_sheet(sheet_name: str, errs: list[ValidationError]):
        ws = wb[sheet_name]
        cols, recs = sheet_to_records(ws)
        findings = errors_to_findings(errs)
        all_errors.extend(errs)
        sheet_results.append({
            "sheet_name": sheet_name,
            "row_count": len(recs),
            "column_count": len(cols),
            "columns": cols,
            "findings": findings,
        })

    # --- ref_entities ---
    _, r = sheet_to_records(wb["ref_entities"])
    errs = []
    errs += check_required_columns("ref_entities", list(r[0].keys()) if r else [],
                                   ["entity_id", "entity_name", "entity_type", "status"])
    errs += check_no_duplicate_ids("ref_entities", r, "entity_id")
    errs += check_no_nulls("ref_entities", r, ["entity_id", "entity_name", "entity_type", "status"])
    errs += check_valid_status("ref_entities", r, "status", {"ACTIVE", "INACTIVE"})
    run_sheet("ref_entities", errs)

    # --- ref_departments ---
    _, r = sheet_to_records(wb["ref_departments"])
    errs = []
    errs += check_required_columns("ref_departments", list(r[0].keys()) if r else [],
                                   ["department_id", "department_name"])
    errs += check_no_duplicate_ids("ref_departments", r, "department_id")
    errs += check_no_nulls("ref_departments", r, ["department_id", "department_name"])
    run_sheet("ref_departments", errs)

    # --- ref_products ---
    _, r = sheet_to_records(wb["ref_products"])
    errs = []
    errs += check_required_columns("ref_products", list(r[0].keys()) if r else [],
                                   ["product_id", "product_name", "product_category", "base_uom", "status"])
    errs += check_no_duplicate_ids("ref_products", r, "product_id")
    errs += check_no_nulls("ref_products", r, ["product_id", "product_name", "product_category", "base_uom", "status"])
    errs += check_valid_status("ref_products", r, "status", {"ACTIVE", "INACTIVE", "OBSOLETE"})
    errs += check_numeric_range("ref_products", r, "reference_unit_cost_inr", 0, 10_000_000)
    run_sheet("ref_products", errs)

    # --- ref_warehouses ---
    _, r = sheet_to_records(wb["ref_warehouses"])
    errs = []
    errs += check_required_columns("ref_warehouses", list(r[0].keys()) if r else [],
                                   ["warehouse_id", "warehouse_name", "entity_id", "warehouse_type", "status"])
    errs += check_no_duplicate_ids("ref_warehouses", r, "warehouse_id")
    errs += check_no_nulls("ref_warehouses", r, ["warehouse_id", "warehouse_name", "entity_id"])
    errs += check_referential_integrity("ref_warehouses", r, "entity_id", entity_ids)
    errs += check_valid_status("ref_warehouses", r, "status", {"ACTIVE", "INACTIVE", "MAINTENANCE"})
    errs += check_numeric_range("ref_warehouses", r, "capacity_units", 0, 1_000_000)
    run_sheet("ref_warehouses", errs)

    # --- ref_suppliers ---
    _, r = sheet_to_records(wb["ref_suppliers"])
    errs = []
    errs += check_required_columns("ref_suppliers", list(r[0].keys()) if r else [],
                                   ["supplier_id", "supplier_name", "supplier_category", "status", "risk_band"])
    errs += check_no_duplicate_ids("ref_suppliers", r, "supplier_id")
    errs += check_no_nulls("ref_suppliers", r, ["supplier_id", "supplier_name", "status", "risk_band"])
    errs += check_valid_status("ref_suppliers", r, "status", {"ACTIVE", "INACTIVE", "SUSPENDED"})
    errs += check_valid_status("ref_suppliers", r, "risk_band", {"LOW", "MEDIUM", "HIGH"})
    errs += check_numeric_range("ref_suppliers", r, "historical_on_time_rate", 0.0, 1.0)
    errs += check_numeric_range("ref_suppliers", r, "default_lead_time_hours", 0, 8760)
    run_sheet("ref_suppliers", errs)

    # --- ref_supplier_offers ---
    _, r = sheet_to_records(wb["ref_supplier_offers"])
    errs = []
    errs += check_required_columns("ref_supplier_offers", list(r[0].keys()) if r else [],
                                   ["offer_id", "supplier_id", "item_id", "unit_price_inr", "offer_status"])
    errs += check_no_duplicate_ids("ref_supplier_offers", r, "offer_id")
    errs += check_no_nulls("ref_supplier_offers", r, ["offer_id", "supplier_id", "item_id"])
    errs += check_referential_integrity("ref_supplier_offers", r, "supplier_id", supplier_ids)
    errs += check_referential_integrity("ref_supplier_offers", r, "item_id", product_ids)
    errs += check_numeric_range("ref_supplier_offers", r, "unit_price_inr", 0, 10_000_000)
    errs += check_numeric_range("ref_supplier_offers", r, "on_time_rate", 0.0, 1.0)
    errs += check_date_range("ref_supplier_offers", r, "effective_from", MIN_DATE, MAX_DATE)
    errs += check_date_range("ref_supplier_offers", r, "effective_to", MIN_DATE, MAX_DATE)
    errs += check_valid_status("ref_supplier_offers", r, "offer_status", {"ACTIVE", "EXPIRED", "WITHDRAWN"})
    run_sheet("ref_supplier_offers", errs)

    # --- ref_roles ---
    _, r = sheet_to_records(wb["ref_roles"])
    errs = []
    errs += check_required_columns("ref_roles", list(r[0].keys()) if r else [],
                                   ["role_id", "role_name"])
    errs += check_no_duplicate_ids("ref_roles", r, "role_id")
    errs += check_no_nulls("ref_roles", r, ["role_id", "role_name"])
    run_sheet("ref_roles", errs)

    # --- ref_users ---
    _, r = sheet_to_records(wb["ref_users"])
    errs = []
    errs += check_required_columns("ref_users", list(r[0].keys()) if r else [],
                                   ["user_id", "display_name", "role_id", "entity_id", "status"])
    errs += check_no_duplicate_ids("ref_users", r, "user_id")
    errs += check_no_nulls("ref_users", r, ["user_id", "display_name", "role_id", "entity_id", "status"])
    errs += check_referential_integrity("ref_users", r, "role_id", role_ids)
    errs += check_referential_integrity("ref_users", r, "entity_id", entity_ids)
    errs += check_valid_status("ref_users", r, "status", {"ACTIVE", "INACTIVE", "SUSPENDED"})
    run_sheet("ref_users", errs)

    # --- ref_production_lines ---
    _, r = sheet_to_records(wb["ref_production_lines"])
    errs = []
    errs += check_required_columns("ref_production_lines", list(r[0].keys()) if r else [],
                                   ["production_line_id", "line_name", "entity_id", "status"])
    errs += check_no_duplicate_ids("ref_production_lines", r, "production_line_id")
    errs += check_no_nulls("ref_production_lines", r, ["production_line_id", "line_name", "entity_id"])
    errs += check_referential_integrity("ref_production_lines", r, "entity_id", entity_ids)
    errs += check_valid_status("ref_production_lines", r, "status",
                               {"RUNNING", "STOPPED", "MAINTENANCE", "IDLE"})
    errs += check_numeric_range("ref_production_lines", r, "utilisation_pct", 0.0, 1.0)
    errs += check_numeric_range("ref_production_lines", r, "daily_capacity_mt", 0, 50_000)
    run_sheet("ref_production_lines", errs)

    # --- ref_budgets ---
    _, r = sheet_to_records(wb["ref_budgets"])
    errs = []
    errs += check_required_columns("ref_budgets", list(r[0].keys()) if r else [],
                                   ["budget_id", "entity_id", "approved_limit_inr", "status"])
    errs += check_no_duplicate_ids("ref_budgets", r, "budget_id")
    errs += check_no_nulls("ref_budgets", r, ["budget_id", "entity_id", "approved_limit_inr"])
    errs += check_referential_integrity("ref_budgets", r, "entity_id", entity_ids)
    errs += check_numeric_range("ref_budgets", r, "approved_limit_inr", 0, 10_000_000_000)
    errs += check_numeric_range("ref_budgets", r, "committed_spend_inr", 0, 10_000_000_000)
    errs += check_numeric_range("ref_budgets", r, "available_budget_inr", 0, 10_000_000_000)
    run_sheet("ref_budgets", errs)

    # --- ref_supplier_contracts ---
    _, r = sheet_to_records(wb["ref_supplier_contracts"])
    errs = []
    errs += check_required_columns("ref_supplier_contracts", list(r[0].keys()) if r else [],
                                   ["contract_id", "supplier_id", "status"])
    errs += check_no_duplicate_ids("ref_supplier_contracts", r, "contract_id")
    errs += check_no_nulls("ref_supplier_contracts", r, ["contract_id", "supplier_id"])
    errs += check_referential_integrity("ref_supplier_contracts", r, "supplier_id", supplier_ids)
    errs += check_date_range("ref_supplier_contracts", r, "effective_from", MIN_DATE, MAX_DATE)
    errs += check_date_range("ref_supplier_contracts", r, "effective_to", MIN_DATE, MAX_DATE)
    errs += check_valid_status("ref_supplier_contracts", r, "status", {"ACTIVE", "EXPIRED", "TERMINATED"})
    run_sheet("ref_supplier_contracts", errs)

    # --- ref_shifts ---
    _, r = sheet_to_records(wb["ref_shifts"])
    errs = []
    errs += check_required_columns("ref_shifts", list(r[0].keys()) if r else [],
                                   ["shift_id", "entity_id", "start_local", "end_local", "status"])
    errs += check_no_duplicate_ids("ref_shifts", r, "shift_id")
    errs += check_no_nulls("ref_shifts", r, ["shift_id", "entity_id", "start_local", "end_local"])
    errs += check_referential_integrity("ref_shifts", r, "entity_id", entity_ids)
    errs += check_numeric_range("ref_shifts", r, "duration_hours", 1, 24)
    run_sheet("ref_shifts", errs)

    # --- ref_reorder_policies ---
    _, r = sheet_to_records(wb["ref_reorder_policies"])
    errs = []
    errs += check_required_columns("ref_reorder_policies", list(r[0].keys()) if r else [],
                                   ["policy_id", "item_id", "warehouse_id", "reorder_point_qty", "safety_stock_qty"])
    errs += check_no_duplicate_ids("ref_reorder_policies", r, "policy_id")
    errs += check_no_nulls("ref_reorder_policies", r, ["policy_id", "item_id", "warehouse_id"])
    errs += check_referential_integrity("ref_reorder_policies", r, "item_id", product_ids)
    errs += check_referential_integrity("ref_reorder_policies", r, "warehouse_id", warehouse_ids)
    errs += check_numeric_range("ref_reorder_policies", r, "reorder_point_qty", 0, 1_000_000)
    errs += check_numeric_range("ref_reorder_policies", r, "safety_stock_qty", 0, 1_000_000)
    run_sheet("ref_reorder_policies", errs)

    # --- bill_of_materials ---
    _, r = sheet_to_records(wb["bill_of_materials"])
    errs = []
    errs += check_required_columns("bill_of_materials", list(r[0].keys()) if r else [],
                                   ["bom_line_id", "output_product_id", "input_item_id",
                                    "quantity_per_output_unit", "consumption_uom"])
    errs += check_no_duplicate_ids("bill_of_materials", r, "bom_line_id")
    errs += check_no_nulls("bill_of_materials", r,
                           ["bom_line_id", "output_product_id", "input_item_id", "quantity_per_output_unit"])
    errs += check_referential_integrity("bill_of_materials", r, "output_product_id", product_ids)
    errs += check_referential_integrity("bill_of_materials", r, "input_item_id", product_ids)
    errs += check_numeric_range("bill_of_materials", r, "quantity_per_output_unit", 0.0001, 1000)
    run_sheet("bill_of_materials", errs)

    # --- business_rules ---
    _, r = sheet_to_records(wb["business_rules"])
    errs = []
    errs += check_required_columns("business_rules", list(r[0].keys()) if r else [],
                                   ["rule_id", "domain", "condition_expression", "failure_action", "severity"])
    errs += check_no_duplicate_ids("business_rules", r, "rule_id")
    errs += check_no_nulls("business_rules", r,
                           ["rule_id", "domain", "condition_expression", "severity"])
    errs += check_valid_status("business_rules", r, "severity",
                               {"LOW", "MEDIUM", "HIGH", "CRITICAL"})
    run_sheet("business_rules", errs)

    # --- inventory ---
    _, r = sheet_to_records(wb["inventory"])
    errs = []
    errs += check_required_columns("inventory", list(r[0].keys()) if r else [],
                                   ["inventory_id", "item_id", "warehouse_id",
                                    "on_hand_qty", "uom", "stock_signal"])
    errs += check_no_duplicate_ids("inventory", r, "inventory_id")
    errs += check_no_nulls("inventory", r, ["inventory_id", "item_id", "warehouse_id", "on_hand_qty", "uom"])
    errs += check_referential_integrity("inventory", r, "item_id", product_ids)
    errs += check_referential_integrity("inventory", r, "warehouse_id", warehouse_ids)
    errs += check_numeric_range("inventory", r, "on_hand_qty", 0, 10_000_000)
    errs += check_numeric_range("inventory", r, "reserved_qty", 0, 10_000_000)
    errs += check_numeric_range("inventory", r, "available_qty", 0, 10_000_000)
    errs += check_valid_status("inventory", r, "stock_signal",
                               {"NORMAL", "LOW_STOCK", "CRITICAL", "OUT_OF_STOCK", "EXCESS"})
    run_sheet("inventory", errs)

    # --- orders ---
    _, r = sheet_to_records(wb["orders"])
    errs = []
    errs += check_required_columns("orders", list(r[0].keys()) if r else [],
                                   ["order_id", "customer_ref", "entity_id", "status", "priority"])
    errs += check_no_duplicate_ids("orders", r, "order_id")
    errs += check_no_nulls("orders", r, ["order_id", "customer_ref", "entity_id", "status"])
    errs += check_referential_integrity("orders", r, "entity_id", entity_ids)
    errs += check_valid_status("orders", r, "status",
                               {"OPEN", "IN_PROGRESS", "AT_RISK", "COMPLETED", "CANCELLED"})
    errs += check_valid_status("orders", r, "priority",
                               {"LOW", "MEDIUM", "HIGH", "CRITICAL"})
    errs += check_date_range("orders", r, "created_at", MIN_DATE, MAX_DATE)
    errs += check_date_range("orders", r, "required_delivery_at", MIN_DATE, MAX_DATE)
    run_sheet("orders", errs)

    # --- order_lines ---
    _, r = sheet_to_records(wb["order_lines"])
    errs = []
    errs += check_required_columns("order_lines", list(r[0].keys()) if r else [],
                                   ["order_line_id", "order_id", "product_id", "requested_qty", "uom"])
    errs += check_no_duplicate_ids("order_lines", r, "order_line_id")
    errs += check_no_nulls("order_lines", r, ["order_line_id", "order_id", "product_id", "requested_qty"])
    errs += check_referential_integrity("order_lines", r, "order_id", order_ids)
    errs += check_referential_integrity("order_lines", r, "product_id", product_ids)
    errs += check_numeric_range("order_lines", r, "requested_qty", 0.001, 1_000_000)
    errs += check_numeric_range("order_lines", r, "unit_price_inr", 0, 100_000_000)
    run_sheet("order_lines", errs)

    # --- production_batches ---
    _, r = sheet_to_records(wb["production_batches"])
    errs = []
    errs += check_required_columns("production_batches", list(r[0].keys()) if r else [],
                                   ["batch_id", "production_line_id", "output_product_id", "status"])
    errs += check_no_duplicate_ids("production_batches", r, "batch_id")
    errs += check_no_nulls("production_batches", r,
                           ["batch_id", "production_line_id", "output_product_id", "status"])
    errs += check_referential_integrity("production_batches", r, "production_line_id", pl_ids)
    errs += check_referential_integrity("production_batches", r, "output_product_id", product_ids)
    errs += check_numeric_range("production_batches", r, "planned_output_qty_mt", 0, 100_000)
    errs += check_numeric_range("production_batches", r, "actual_output_qty_mt", 0, 100_000)
    errs += check_valid_status("production_batches", r, "status",
                               {"PLANNED", "IN_PROGRESS", "COMPLETED", "CANCELLED"})
    errs += check_date_range("production_batches", r, "planned_start", MIN_DATE, MAX_DATE)
    errs += check_date_range("production_batches", r, "planned_end", MIN_DATE, MAX_DATE)
    run_sheet("production_batches", errs)

    # --- shipments ---
    _, r = sheet_to_records(wb["shipments"])
    errs = []
    errs += check_required_columns("shipments", list(r[0].keys()) if r else [],
                                   ["shipment_id", "order_id", "carrier_supplier_id", "status"])
    errs += check_no_duplicate_ids("shipments", r, "shipment_id")
    errs += check_no_nulls("shipments", r, ["shipment_id", "order_id", "status"])
    errs += check_referential_integrity("shipments", r, "order_id", order_ids)
    errs += check_referential_integrity("shipments", r, "carrier_supplier_id", supplier_ids)
    errs += check_valid_status("shipments", r, "status",
                               {"PLANNED", "IN_TRANSIT", "AT_RISK", "DELIVERED", "CANCELLED"})
    errs += check_valid_status("shipments", r, "transport_mode", {"RAIL", "ROAD", "ROAD_RAIL", "SEA", "AIR"})
    errs += check_date_range("shipments", r, "planned_dispatch_at", MIN_DATE, MAX_DATE)
    errs += check_date_range("shipments", r, "estimated_arrival_at", MIN_DATE, MAX_DATE)
    run_sheet("shipments", errs)

    # --- purchase_orders ---
    _, r = sheet_to_records(wb["purchase_orders"])
    errs = []
    errs += check_required_columns("purchase_orders", list(r[0].keys()) if r else [],
                                   ["po_id", "supplier_id", "item_id", "quantity", "unit_cost_inr", "status"])
    errs += check_no_duplicate_ids("purchase_orders", r, "po_id")
    errs += check_no_nulls("purchase_orders", r, ["po_id", "supplier_id", "item_id", "quantity"])
    errs += check_referential_integrity("purchase_orders", r, "supplier_id", supplier_ids)
    errs += check_referential_integrity("purchase_orders", r, "item_id", product_ids)
    errs += check_numeric_range("purchase_orders", r, "quantity", 0.001, 10_000_000)
    errs += check_numeric_range("purchase_orders", r, "unit_cost_inr", 0, 10_000_000)
    errs += check_valid_status("purchase_orders", r, "status",
                               {"DRAFT", "APPROVED", "IN_TRANSIT", "RECEIVED", "CANCELLED"})
    run_sheet("purchase_orders", errs)

    # --- goods_receipts ---
    _, r = sheet_to_records(wb["goods_receipts"])
    errs = []
    errs += check_required_columns("goods_receipts", list(r[0].keys()) if r else [],
                                   ["grn_id", "po_id", "supplier_id", "item_id", "received_qty"])
    errs += check_no_duplicate_ids("goods_receipts", r, "grn_id")
    errs += check_no_nulls("goods_receipts", r, ["grn_id", "po_id", "supplier_id", "item_id", "received_qty"])
    errs += check_referential_integrity("goods_receipts", r, "po_id", po_ids)
    errs += check_referential_integrity("goods_receipts", r, "supplier_id", supplier_ids)
    errs += check_referential_integrity("goods_receipts", r, "item_id", product_ids)
    errs += check_numeric_range("goods_receipts", r, "received_qty", 0, 1_000_000)
    errs += check_numeric_range("goods_receipts", r, "accepted_qty", 0, 1_000_000)
    errs += check_valid_status("goods_receipts", r, "inspection_status",
                               {"PENDING", "ACCEPTED", "QUALITY_HOLD", "REJECTED"})
    run_sheet("goods_receipts", errs)

    # --- quality_events ---
    _, r = sheet_to_records(wb["quality_events"])
    errs = []
    errs += check_required_columns("quality_events", list(r[0].keys()) if r else [],
                                   ["quality_event_id", "batch_id", "product_id", "defect_code", "severity", "status"])
    errs += check_no_duplicate_ids("quality_events", r, "quality_event_id")
    errs += check_no_nulls("quality_events", r,
                           ["quality_event_id", "batch_id", "product_id", "severity", "status"])
    errs += check_referential_integrity("quality_events", r, "batch_id", batch_ids)
    errs += check_referential_integrity("quality_events", r, "product_id", product_ids)
    errs += check_valid_status("quality_events", r, "severity",
                               {"LOW", "MEDIUM", "HIGH", "CRITICAL"})
    errs += check_valid_status("quality_events", r, "status",
                               {"OPEN", "IN_REVIEW", "RELEASED", "REJECTED"})
    errs += check_date_range("quality_events", r, "detected_at", MIN_DATE, MAX_DATE)
    run_sheet("quality_events", errs)

    # --- maintenance_assets ---
    _, r = sheet_to_records(wb["maintenance_assets"])
    errs = []
    errs += check_required_columns("maintenance_assets", list(r[0].keys()) if r else [],
                                   ["asset_id", "production_line_id", "asset_name", "health_status"])
    errs += check_no_duplicate_ids("maintenance_assets", r, "asset_id")
    errs += check_no_nulls("maintenance_assets", r,
                           ["asset_id", "production_line_id", "asset_name", "health_status"])
    errs += check_referential_integrity("maintenance_assets", r, "production_line_id", pl_ids)
    errs += check_valid_status("maintenance_assets", r, "health_status",
                               {"NORMAL", "WARNING", "CRITICAL"})
    errs += check_numeric_range("maintenance_assets", r, "failure_risk_score", 0.0, 1.0)
    errs += check_date_range("maintenance_assets", r, "next_maintenance_due", MIN_DATE, MAX_DATE)
    run_sheet("maintenance_assets", errs)

    # --- maintenance_work_orders ---
    _, r = sheet_to_records(wb["maintenance_work_orders"])
    errs = []
    errs += check_required_columns("maintenance_work_orders", list(r[0].keys()) if r else [],
                                   ["work_order_id", "asset_id", "work_type", "status", "priority"])
    errs += check_no_duplicate_ids("maintenance_work_orders", r, "work_order_id")
    errs += check_no_nulls("maintenance_work_orders", r,
                           ["work_order_id", "asset_id", "work_type", "status"])
    errs += check_referential_integrity("maintenance_work_orders", r, "asset_id", asset_ids)
    errs += check_valid_status("maintenance_work_orders", r, "status",
                               {"OPEN", "SCHEDULED", "IN_PROGRESS", "COMPLETED", "CANCELLED"})
    errs += check_valid_status("maintenance_work_orders", r, "priority",
                               {"LOW", "MEDIUM", "HIGH", "CRITICAL"})
    errs += check_date_range("maintenance_work_orders", r, "scheduled_for", MIN_DATE, MAX_DATE)
    run_sheet("maintenance_work_orders", errs)

    # --- energy_readings ---
    _, r = sheet_to_records(wb["energy_readings"])
    errs = []
    errs += check_required_columns("energy_readings", list(r[0].keys()) if r else [],
                                   ["reading_id", "entity_id", "production_line_id",
                                    "reading_at", "energy_kwh", "signal"])
    errs += check_no_duplicate_ids("energy_readings", r, "reading_id")
    errs += check_no_nulls("energy_readings", r,
                           ["reading_id", "entity_id", "production_line_id", "energy_kwh"])
    errs += check_referential_integrity("energy_readings", r, "entity_id", entity_ids)
    errs += check_referential_integrity("energy_readings", r, "production_line_id", pl_ids)
    errs += check_numeric_range("energy_readings", r, "energy_kwh", 0, 1_000_000)
    errs += check_numeric_range("energy_readings", r, "unit_rate_inr", 0, 100)
    errs += check_valid_status("energy_readings", r, "signal",
                               {"NORMAL", "SPIKE", "LOW", "OFFLINE", "ALERT"})
    errs += check_date_range("energy_readings", r, "reading_at", MIN_DATE, MAX_DATE)
    run_sheet("energy_readings", errs)

    # --- safety_events ---
    _, r = sheet_to_records(wb["safety_events"])
    errs = []
    errs += check_required_columns("safety_events", list(r[0].keys()) if r else [],
                                   ["safety_event_id", "entity_id", "occurred_at",
                                    "event_type", "severity", "status"])
    errs += check_no_duplicate_ids("safety_events", r, "safety_event_id")
    errs += check_no_nulls("safety_events", r,
                           ["safety_event_id", "entity_id", "occurred_at", "event_type", "severity"])
    errs += check_referential_integrity("safety_events", r, "entity_id", entity_ids)
    errs += check_valid_status("safety_events", r, "event_type",
                               {"NEAR_MISS", "UNSAFE_CONDITION", "EQUIPMENT_GUARD_ALERT",
                                "PPE_NONCOMPLIANCE", "INCIDENT", "FIRE", "SPILL"})
    errs += check_valid_status("safety_events", r, "severity",
                               {"LOW", "MEDIUM", "HIGH", "CRITICAL"})
    errs += check_valid_status("safety_events", r, "status",
                               {"OPEN", "INVESTIGATING", "CLOSED", "ESCALATED"})
    errs += check_date_range("safety_events", r, "occurred_at", MIN_DATE, MAX_DATE)
    run_sheet("safety_events", errs)

    # --- carrier_events ---
    _, r = sheet_to_records(wb["carrier_events"])
    errs = []
    errs += check_required_columns("carrier_events", list(r[0].keys()) if r else [],
                                   ["carrier_event_id", "shipment_id", "event_timestamp", "event_type"])
    errs += check_no_duplicate_ids("carrier_events", r, "carrier_event_id")
    errs += check_no_nulls("carrier_events", r,
                           ["carrier_event_id", "shipment_id", "event_timestamp", "event_type"])
    errs += check_referential_integrity("carrier_events", r, "shipment_id", shipment_ids)
    errs += check_referential_integrity("carrier_events", r, "source_supplier_id", supplier_ids)
    errs += check_date_range("carrier_events", r, "event_timestamp", MIN_DATE, MAX_DATE)
    run_sheet("carrier_events", errs)

    # --- feed_health ---
    _, r = sheet_to_records(wb["feed_health"])
    errs = []
    errs += check_required_columns("feed_health", list(r[0].keys()) if r else [],
                                   ["feed_id", "source_name", "health_status"])
    errs += check_no_duplicate_ids("feed_health", r, "feed_id")
    errs += check_no_nulls("feed_health", r, ["feed_id", "source_name", "health_status"])
    errs += check_valid_status("feed_health", r, "health_status",
                               {"HEALTHY", "DEGRADED", "OFFLINE", "UNKNOWN"})
    errs += check_numeric_range("feed_health", r, "consecutive_failures", 0, 1000)
    run_sheet("feed_health", errs)

    # --- business_rules handled above; skip scenario_templates (DQ-01 noted separately)
    # --- scenario_templates ---
    _, r = sheet_to_records(wb["scenario_templates"])
    errs = []
    errs += check_required_columns("scenario_templates", list(r[0].keys()) if r else [],
                                   ["scenario_template_id", "scenario_type", "domain",
                                    "description", "injection_method"])
    errs += check_no_duplicate_ids("scenario_templates", r, "scenario_template_id")
    errs += check_no_nulls("scenario_templates", r,
                           ["scenario_template_id", "scenario_type", "domain", "description"])
    errs += check_valid_status("scenario_templates", r, "domain",
                               {"Inventory", "Procurement", "Finance", "Logistics",
                                "Quality", "Maintenance", "Energy", "Safety"})
    # DQ-01: linked_reference_id column actually stores severity values
    errs += check_valid_status("scenario_templates", r, "linked_reference_id",
                               {"LOW", "MEDIUM", "HIGH", "CRITICAL"})
    run_sheet("scenario_templates", errs)

    # ---- Summarise ----
    total_records = sum(s["row_count"] for s in sheet_results)
    summary = {"critical": 0, "warning": 0, "info": 0}
    for e in all_errors:
        key = e.severity.lower()
        if key in summary:
            summary[key] += 1

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "workbook_path": str(WORKBOOK_PATH),
        "sheets_inspected": len(sheet_results),
        "total_records_inspected": total_records,
        "summary": summary,
        "sheets": sheet_results,
        "errors": [],
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    if not WORKBOOK_PATH.exists():
        print(f"ERROR: Workbook not found at {WORKBOOK_PATH}")
        sys.exit(1)

    print(f"Opening workbook: {WORKBOOK_PATH}")
    wb = openpyxl.load_workbook(str(WORKBOOK_PATH), read_only=True, data_only=True)

    print("Running validation rules …")
    report = validate_all(wb)
    wb.close()

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"\nValidation report written to: {OUTPUT_PATH}")
    print(f"  Sheets inspected  : {report['sheets_inspected']}")
    print(f"  Records inspected : {report['total_records_inspected']}")
    print(f"  CRITICAL findings : {report['summary']['critical']}")
    print(f"  WARNING  findings : {report['summary']['warning']}")
    print(f"  INFO     findings : {report['summary']['info']}")

    for s in report["sheets"]:
        if s["findings"]:
            print(f"\n  [{s['sheet_name']}] {s['row_count']} rows — {len(s['findings'])} finding group(s)")
            for f in s["findings"]:
                print(f"    {f['severity']:8s} | {f['rule']:30s} | col={f['column']:30s} | count={f['count']}")


if __name__ == "__main__":
    main()
