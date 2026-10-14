"""
column_mappings.py — Authoritative workbook-to-database column mappings.

This is the single source of truth for how every workbook column maps to a
PostgreSQL table column in the Phase 1 schema.  Import logic in load_seed_data.py
reads these mappings rather than hard-coding column names there.

Column names are the EXACT header strings found in the workbook (verified from
workbook_inspection.json).  Destination column names match 001_operational_schema.sql.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Dataclass definitions
# ---------------------------------------------------------------------------

@dataclass
class ColumnMapping:
    source_col: str           # exact header in workbook
    dest_col: str             # destination table column name
    dest_type: str            # 'str','int','float','date','datetime','bool','decimal'
    required: bool = True     # False = nullable
    transform: Optional[Callable[[Any], Any]] = None  # coercion/cleaning function
    description: str = ""


@dataclass
class SheetMapping:
    sheet_name: str           # exact sheet name in workbook
    dest_table: str           # destination PostgreSQL table name
    primary_key_col: str      # source column name for the PK
    columns: List[ColumnMapping] = field(default_factory=list)
    required_for_fk: bool = False   # True = must be loaded before FK-dependent sheets
    load_order: int = 0             # lower = loaded first
    extra_dest_values: Dict[str, Any] = field(default_factory=dict)
    # Constant destination values applied at import (not present as source columns).


# ---------------------------------------------------------------------------
# Shared transform functions (pure, no side-effects)
# ---------------------------------------------------------------------------

def _strip(v: Any) -> Optional[str]:
    """Strip surrounding whitespace; treat blank strings as null."""
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None


def _to_bool_str(v: Any) -> bool:
    """Convert 'true'/'false' string or actual bool to Python bool."""
    if v is None:
        return True  # default enabled
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    return s not in ("false", "0", "no", "n")


def _parse_date(v: Any) -> Optional[date]:
    """Coerce workbook date-string or date/datetime object to Python date."""
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _parse_datetime(v: Any) -> Optional[datetime]:
    """Coerce workbook datetime-string to timezone-aware UTC datetime."""
    if v is None:
        return None
    if isinstance(v, datetime):
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)
    if isinstance(v, date):
        return datetime(v.year, v.month, v.day, tzinfo=timezone.utc)
    s = str(v).strip()
    for fmt in (
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _to_int(v: Any) -> Optional[int]:
    """Cast integer-like values; reject booleans and non-numeric strings."""
    if v is None or v == "":
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    try:
        return int(float(str(v).strip()))
    except (TypeError, ValueError):
        return None


def _to_decimal(v: Any) -> Optional[float]:
    """Cast integer/float/string to float (stored as NUMERIC in PostgreSQL)."""
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _severity_from_linked_ref(v: Any) -> Optional[str]:
    """DQ-01 fix: workbook linked_reference_id column actually stores severity values."""
    if v is None:
        return None
    s = str(v).strip().upper()
    if s in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
        return s
    return None


# ---------------------------------------------------------------------------
# Sheet Mappings
# ---------------------------------------------------------------------------

SHEET_MAPPINGS: Dict[str, SheetMapping] = {

    # =========================================================================
    # GROUP 1 — Reference / master tables  (load_order 1)
    # =========================================================================

    "ref_entities": SheetMapping(
        sheet_name="ref_entities",
        dest_table="entities",
        primary_key_col="entity_id",
        required_for_fk=True,
        load_order=1,
        columns=[
            ColumnMapping("entity_id",   "entity_id",   "str",  True,  _strip),
            ColumnMapping("entity_name", "entity_name", "str",  True,  _strip),
            ColumnMapping("entity_type", "entity_type", "str",  True,  _strip),
            ColumnMapping("country",     "country",     "str",  False, _strip),
            ColumnMapping("status",      "status",      "str",  True,  _strip),
        ],
    ),

    "ref_departments": SheetMapping(
        sheet_name="ref_departments",
        dest_table="departments",
        primary_key_col="department_id",
        required_for_fk=True,
        load_order=1,
        columns=[
            ColumnMapping("department_id",   "department_id",   "str", True,  _strip),
            ColumnMapping("department_name", "department_name", "str", True,  _strip),
        ],
    ),

    "ref_products": SheetMapping(
        sheet_name="ref_products",
        dest_table="products",
        primary_key_col="product_id",
        required_for_fk=True,
        load_order=1,
        columns=[
            ColumnMapping("product_id",               "product_id",               "str",     True,  _strip),
            ColumnMapping("product_name",             "product_name",             "str",     True,  _strip),
            ColumnMapping("product_category",         "product_category",         "str",     True,  _strip),
            ColumnMapping("base_uom",                 "base_uom",                 "str",     True,  _strip),
            ColumnMapping("reference_unit_cost_inr",  "reference_unit_cost_inr",  "decimal", False, _to_decimal,
                          "INR unit cost stored as NUMERIC(18,2)"),
            ColumnMapping("status",                   "status",                   "str",     True,  _strip),
        ],
    ),

    "ref_warehouses": SheetMapping(
        sheet_name="ref_warehouses",
        dest_table="warehouses",
        primary_key_col="warehouse_id",
        required_for_fk=True,
        load_order=1,
        columns=[
            ColumnMapping("warehouse_id",   "warehouse_id",   "str",     True,  _strip),
            ColumnMapping("warehouse_name", "warehouse_name", "str",     True,  _strip),
            ColumnMapping("entity_id",      "entity_id",      "str",     True,  _strip,      "FK → entities"),
            ColumnMapping("location_label", "location_label", "str",     False, _strip),
            ColumnMapping("capacity_units", "capacity_units", "decimal", False, _to_decimal),
            ColumnMapping("warehouse_type", "warehouse_type", "str",     True,  _strip),
            ColumnMapping("status",         "status",         "str",     True,  _strip),
        ],
    ),

    "ref_suppliers": SheetMapping(
        sheet_name="ref_suppliers",
        dest_table="suppliers",
        primary_key_col="supplier_id",
        required_for_fk=True,
        load_order=1,
        columns=[
            ColumnMapping("supplier_id",              "supplier_id",              "str",     True,  _strip),
            ColumnMapping("supplier_name",            "supplier_name",            "str",     True,  _strip),
            ColumnMapping("supplier_category",        "supplier_category",        "str",     True,  _strip),
            ColumnMapping("status",                   "status",                   "str",     True,  _strip),
            ColumnMapping("risk_band",                "risk_band",                "str",     True,  _strip),
            ColumnMapping("historical_on_time_rate",  "historical_on_time_rate",  "float",   False, _to_decimal,
                          "0–1 fraction"),
            ColumnMapping("default_lead_time_hours",  "default_lead_time_hours",  "int",     False, _to_int),
        ],
    ),

    "ref_supplier_offers": SheetMapping(
        sheet_name="ref_supplier_offers",
        dest_table="supplier_offers",
        primary_key_col="offer_id",
        required_for_fk=False,
        load_order=1,
        columns=[
            ColumnMapping("offer_id",          "offer_id",          "str",      True,  _strip),
            ColumnMapping("supplier_id",        "supplier_id",       "str",      True,  _strip,       "FK → suppliers"),
            ColumnMapping("item_id",            "item_id",           "str",      True,  _strip,       "FK → products"),
            ColumnMapping("unit_price_inr",     "unit_price_inr",    "decimal",  True,  _to_decimal),
            ColumnMapping("price_uom",          "price_uom",         "str",      True,  _strip),
            ColumnMapping("lead_time_hours",    "lead_time_hours",   "int",      False, _to_int),
            ColumnMapping("max_available_qty",  "max_available_qty", "decimal",  False, _to_decimal),
            ColumnMapping("on_time_rate",       "on_time_rate",      "float",    False, _to_decimal,  "0–1 fraction"),
            ColumnMapping("effective_from",     "effective_from",    "date",     False, _parse_date),
            ColumnMapping("effective_to",       "effective_to",      "date",     False, _parse_date),
            ColumnMapping("offer_status",       "offer_status",      "str",      True,  _strip),
        ],
    ),

    "ref_roles": SheetMapping(
        sheet_name="ref_roles",
        dest_table="roles",
        primary_key_col="role_id",
        required_for_fk=True,
        load_order=1,
        columns=[
            ColumnMapping("role_id",            "role_id",            "str", True,  _strip),
            ColumnMapping("role_name",          "role_name",          "str", True,  _strip),
            ColumnMapping("permissions_summary","permissions_summary","str", False, _strip),
        ],
    ),

    "ref_users": SheetMapping(
        sheet_name="ref_users",
        dest_table="users",
        primary_key_col="user_id",
        required_for_fk=False,
        load_order=1,
        columns=[
            ColumnMapping("user_id",      "user_id",      "str", True,  _strip),
            ColumnMapping("display_name", "display_name", "str", True,  _strip),
            ColumnMapping("role_id",      "role_id",      "str", True,  _strip, "FK → roles"),
            ColumnMapping("entity_id",    "entity_id",    "str", True,  _strip, "FK → entities"),
            ColumnMapping("status",       "status",       "str", True,  _strip),
        ],
    ),

    "ref_production_lines": SheetMapping(
        sheet_name="ref_production_lines",
        dest_table="production_lines",
        primary_key_col="production_line_id",
        required_for_fk=True,
        load_order=1,
        columns=[
            ColumnMapping("production_line_id", "production_line_id", "str",     True,  _strip),
            ColumnMapping("line_name",           "line_name",          "str",     True,  _strip),
            ColumnMapping("entity_id",           "entity_id",          "str",     True,  _strip,      "FK → entities"),
            ColumnMapping("process_stage",       "process_stage",      "str",     True,  _strip),
            ColumnMapping("status",              "status",             "str",     True,  _strip),
            ColumnMapping("utilisation_pct",     "utilisation_pct",    "float",   False, _to_decimal, "0–1 fraction"),
            ColumnMapping("daily_capacity_mt",   "daily_capacity_mt",  "decimal", False, _to_decimal),
        ],
    ),

    "ref_budgets": SheetMapping(
        sheet_name="ref_budgets",
        dest_table="budgets",
        primary_key_col="budget_id",
        required_for_fk=False,
        load_order=1,
        columns=[
            ColumnMapping("budget_id",                          "budget_id",                          "str",     True,  _strip),
            ColumnMapping("entity_id",                          "entity_id",                          "str",     True,  _strip,      "FK → entities"),
            ColumnMapping("cost_center",                        "cost_center",                        "str",     True,  _strip),
            ColumnMapping("period",                             "period",                             "str",     True,  _strip),
            ColumnMapping("currency",                           "currency",                           "str",     True,  _strip),
            ColumnMapping("approved_limit_inr",                 "approved_limit_inr",                 "decimal", True,  _to_decimal),
            ColumnMapping("committed_spend_inr",                "committed_spend_inr",                "decimal", True,  _to_decimal),
            ColumnMapping("available_budget_inr",               "available_budget_inr",               "decimal", True,  _to_decimal),
            ColumnMapping("single_action_approval_threshold_inr","single_action_approval_threshold_inr","decimal",False, _to_decimal),
            ColumnMapping("status",                             "status",                             "str",     True,  _strip),
        ],
    ),

    "ref_supplier_contracts": SheetMapping(
        sheet_name="ref_supplier_contracts",
        dest_table="supplier_contracts",
        primary_key_col="contract_id",
        required_for_fk=False,
        load_order=1,
        columns=[
            ColumnMapping("contract_id",        "contract_id",        "str",     True,  _strip),
            ColumnMapping("supplier_id",         "supplier_id",        "str",     True,  _strip,      "FK → suppliers"),
            ColumnMapping("contract_category",   "contract_category",  "str",     True,  _strip),
            ColumnMapping("effective_from",      "effective_from",     "date",    False, _parse_date),
            ColumnMapping("effective_to",        "effective_to",       "date",    False, _parse_date),
            ColumnMapping("contract_limit_inr",  "contract_limit_inr", "decimal", False, _to_decimal),
            ColumnMapping("currency",            "currency",           "str",     True,  _strip),
            ColumnMapping("status",              "status",             "str",     True,  _strip),
            ColumnMapping("owner_department",    "owner_department",   "str",     False, _strip),
        ],
    ),

    "ref_shifts": SheetMapping(
        sheet_name="ref_shifts",
        dest_table="shifts",
        primary_key_col="shift_id",
        required_for_fk=False,
        load_order=1,
        columns=[
            ColumnMapping("shift_id",        "shift_id",        "str", True,  _strip),
            ColumnMapping("entity_id",        "entity_id",       "str", True,  _strip,  "FK → entities"),
            ColumnMapping("start_local",      "start_local",     "str", True,  _strip,  "Local 24-h time string e.g. '06:00'"),
            ColumnMapping("end_local",        "end_local",       "str", True,  _strip),
            ColumnMapping("duration_hours",   "duration_hours",  "int", False, _to_int),
            ColumnMapping("status",           "status",          "str", True,  _strip),
        ],
    ),

    # =========================================================================
    # GROUP 2 — Operational configuration tables  (load_order 2)
    # =========================================================================

    "ref_reorder_policies": SheetMapping(
        sheet_name="ref_reorder_policies",
        dest_table="reorder_policies",
        primary_key_col="policy_id",
        required_for_fk=False,
        load_order=2,
        columns=[
            ColumnMapping("policy_id",          "policy_id",          "str",     True,  _strip),
            ColumnMapping("item_id",             "item_id",            "str",     True,  _strip,      "FK → products"),
            ColumnMapping("warehouse_id",        "warehouse_id",       "str",     True,  _strip,      "FK → warehouses"),
            ColumnMapping("reorder_point_qty",   "reorder_point_qty",  "decimal", True,  _to_decimal),
            ColumnMapping("safety_stock_qty",    "safety_stock_qty",   "decimal", True,  _to_decimal),
            ColumnMapping("target_stock_qty",    "target_stock_qty",   "decimal", False, _to_decimal),
            ColumnMapping("status",              "status",             "str",     True,  _strip),
        ],
    ),

    "bill_of_materials": SheetMapping(
        sheet_name="bill_of_materials",
        dest_table="bill_of_materials",
        primary_key_col="bom_line_id",
        required_for_fk=False,
        load_order=2,
        columns=[
            ColumnMapping("bom_line_id",               "bom_line_id",               "str",   True,  _strip),
            ColumnMapping("output_product_id",          "output_product_id",          "str",   True,  _strip, "FK → products"),
            ColumnMapping("input_item_id",              "input_item_id",              "str",   True,  _strip, "FK → products"),
            ColumnMapping("quantity_per_output_unit",   "quantity_per_output_unit",   "float", True,  _to_decimal),
            ColumnMapping("consumption_uom",            "consumption_uom",            "str",   True,  _strip),
            ColumnMapping("version_status",             "version_status",             "str",   True,  _strip),
        ],
    ),

    "business_rules": SheetMapping(
        sheet_name="business_rules",
        dest_table="business_rules",
        primary_key_col="rule_id",
        required_for_fk=False,
        load_order=2,
        columns=[
            ColumnMapping("rule_id",              "rule_id",              "str",  True,  _strip),
            ColumnMapping("domain",               "domain",               "str",  True,  _strip),
            ColumnMapping("condition_expression", "condition_expression", "str",  True,  _strip),
            ColumnMapping("failure_action",       "failure_action",       "str",  True,  _strip),
            ColumnMapping("severity",             "severity",             "str",  True,  _strip),
            ColumnMapping("automation_mode",      "automation_mode",      "str",  True,  _strip),
            ColumnMapping("enabled",              "enabled",              "bool", True,  _to_bool_str,
                          "Workbook stores 'true'/'false' strings; convert to bool"),
        ],
    ),

    # =========================================================================
    # GROUP 3 — Operational transaction tables  (load_order 3)
    # =========================================================================

    "inventory": SheetMapping(
        sheet_name="inventory",
        dest_table="inventory",
        primary_key_col="inventory_id",
        required_for_fk=False,
        load_order=3,
        columns=[
            ColumnMapping("inventory_id",   "inventory_id",   "str",      True,  _strip),
            ColumnMapping("item_id",         "item_id",        "str",      True,  _strip,      "FK → products"),
            ColumnMapping("warehouse_id",    "warehouse_id",   "str",      True,  _strip,      "FK → warehouses"),
            ColumnMapping("on_hand_qty",     "on_hand_qty",    "decimal",  True,  _to_decimal),
            ColumnMapping("reserved_qty",    "reserved_qty",   "decimal",  True,  _to_decimal),
            ColumnMapping("available_qty",   "available_qty",  "decimal",  True,  _to_decimal),
            ColumnMapping("uom",             "uom",            "str",      True,  _strip),
            ColumnMapping("as_of_timestamp", "as_of_timestamp","datetime", False, _parse_datetime,
                          "Workbook stores ISO 8601 string without TZ; treated as UTC"),
            ColumnMapping("stock_signal",    "stock_signal",   "str",      True,  _strip),
        ],
    ),

    "orders": SheetMapping(
        sheet_name="orders",
        dest_table="orders",
        primary_key_col="order_id",
        required_for_fk=True,
        load_order=3,
        columns=[
            ColumnMapping("order_id",              "order_id",              "str",      True,  _strip),
            ColumnMapping("customer_ref",           "customer_ref",          "str",      True,  _strip,
                          "No ref_customers table in Phase 1; stored as plain TEXT"),
            ColumnMapping("entity_id",              "entity_id",             "str",      True,  _strip,      "FK → entities"),
            ColumnMapping("created_at",             "created_at",            "datetime", False, _parse_datetime),
            ColumnMapping("required_delivery_at",   "required_delivery_at",  "datetime", False, _parse_datetime),
            ColumnMapping("status",                 "status",                "str",      True,  _strip),
            ColumnMapping("priority",               "priority",              "str",      True,  _strip),
            ColumnMapping("currency",               "currency",              "str",      True,  _strip),
            ColumnMapping("external_reference",     "external_reference",    "str",      False, _strip),
        ],
    ),

    "order_lines": SheetMapping(
        sheet_name="order_lines",
        dest_table="order_lines",
        primary_key_col="order_line_id",
        required_for_fk=False,
        load_order=3,
        columns=[
            ColumnMapping("order_line_id",  "order_line_id",  "str",     True,  _strip),
            ColumnMapping("order_id",        "order_id",       "str",     True,  _strip,      "FK → orders"),
            ColumnMapping("product_id",      "product_id",     "str",     True,  _strip,      "FK → products"),
            ColumnMapping("requested_qty",   "requested_qty",  "decimal", True,  _to_decimal),
            ColumnMapping("unit_price_inr",  "unit_price_inr", "decimal", False, _to_decimal),
            ColumnMapping("uom",             "uom",            "str",     True,  _strip),
        ],
    ),

    "production_batches": SheetMapping(
        sheet_name="production_batches",
        dest_table="production_batches",
        primary_key_col="batch_id",
        required_for_fk=True,
        load_order=3,
        columns=[
            ColumnMapping("batch_id",                "batch_id",                "str",      True,  _strip),
            ColumnMapping("production_line_id",       "production_line_id",      "str",      True,  _strip, "FK → production_lines"),
            ColumnMapping("output_product_id",        "output_product_id",       "str",      True,  _strip, "FK → products"),
            ColumnMapping("planned_output_qty_mt",    "planned_output_qty_mt",   "decimal",  False, _to_decimal),
            ColumnMapping("actual_output_qty_mt",     "actual_output_qty_mt",    "decimal",  False, _to_decimal),
            ColumnMapping("planned_start",            "planned_start",           "datetime", False, _parse_datetime),
            ColumnMapping("planned_end",              "planned_end",             "datetime", False, _parse_datetime),
            ColumnMapping("status",                   "status",                  "str",      True,  _strip),
            ColumnMapping("risk_flag",                "risk_flag",               "str",      True,  _strip),
        ],
    ),

    "shipments": SheetMapping(
        sheet_name="shipments",
        dest_table="shipments",
        primary_key_col="shipment_id",
        required_for_fk=True,
        load_order=3,
        columns=[
            ColumnMapping("shipment_id",             "shipment_id",             "str",      True,  _strip),
            ColumnMapping("order_id",                 "order_id",                "str",      True,  _strip,      "FK → orders"),
            ColumnMapping("origin_warehouse_id",      "origin_warehouse_id",     "str",      False, _strip,      "FK → warehouses (nullable)"),
            ColumnMapping("destination_warehouse_id", "destination_warehouse_id","str",      False, _strip,      "FK → warehouses (nullable)"),
            ColumnMapping("carrier_supplier_id",      "carrier_supplier_id",     "str",      False, _strip,      "FK → suppliers (nullable)"),
            ColumnMapping("planned_dispatch_at",      "planned_dispatch_at",     "datetime", False, _parse_datetime),
            ColumnMapping("estimated_arrival_at",     "estimated_arrival_at",    "datetime", False, _parse_datetime),
            ColumnMapping("status",                   "status",                  "str",      True,  _strip),
            ColumnMapping("transport_mode",           "transport_mode",          "str",      False, _strip),
            ColumnMapping("risk_flag",                "risk_flag",               "str",      True,  _strip),
        ],
    ),

    "purchase_orders": SheetMapping(
        sheet_name="purchase_orders",
        dest_table="purchase_orders",
        primary_key_col="po_id",
        required_for_fk=True,
        load_order=3,
        columns=[
            ColumnMapping("po_id",          "po_id",          "str",     True,  _strip),
            ColumnMapping("supplier_id",     "supplier_id",    "str",     True,  _strip,      "FK → suppliers"),
            ColumnMapping("item_id",         "item_id",        "str",     True,  _strip,      "FK → products"),
            ColumnMapping("quantity",        "quantity",       "decimal", True,  _to_decimal),
            ColumnMapping("unit_cost_inr",   "unit_cost_inr",  "decimal", True,  _to_decimal),
            ColumnMapping("total_cost_inr",  "total_cost_inr", "decimal", False, _to_decimal),
            ColumnMapping("currency",        "currency",       "str",     True,  _strip),
            ColumnMapping("created_at",      "created_at",     "datetime",False, _parse_datetime),
            ColumnMapping("status",          "status",         "str",     True,  _strip),
            ColumnMapping("budget_id",       "budget_id",      "str",     False, _strip,      "FK → budgets (nullable)"),
        ],
    ),

    "goods_receipts": SheetMapping(
        sheet_name="goods_receipts",
        dest_table="goods_receipts",
        primary_key_col="grn_id",
        required_for_fk=False,
        load_order=3,
        columns=[
            ColumnMapping("grn_id",                   "grn_id",                   "str",     True,  _strip),
            ColumnMapping("po_id",                     "po_id",                    "str",     True,  _strip,      "FK → purchase_orders"),
            ColumnMapping("supplier_id",               "supplier_id",              "str",     True,  _strip,      "FK → suppliers"),
            ColumnMapping("item_id",                   "item_id",                  "str",     True,  _strip,      "FK → products"),
            ColumnMapping("received_qty",              "received_qty",             "decimal", True,  _to_decimal),
            ColumnMapping("accepted_qty",              "accepted_qty",             "decimal", True,  _to_decimal),
            ColumnMapping("received_at",               "received_at",              "datetime",False, _parse_datetime),
            ColumnMapping("inspection_status",         "inspection_status",        "str",     True,  _strip),
            ColumnMapping("quality_certificate_ref",   "quality_certificate_ref",  "str",     False, _strip),
        ],
    ),

    "quality_events": SheetMapping(
        sheet_name="quality_events",
        dest_table="quality_events",
        primary_key_col="quality_event_id",
        required_for_fk=False,
        load_order=3,
        columns=[
            ColumnMapping("quality_event_id",   "quality_event_id",  "str",      True,  _strip),
            ColumnMapping("batch_id",            "batch_id",          "str",      True,  _strip,      "FK → production_batches"),
            ColumnMapping("product_id",          "product_id",        "str",      True,  _strip,      "FK → products"),
            ColumnMapping("detected_at",         "detected_at",       "datetime", False, _parse_datetime),
            ColumnMapping("defect_code",         "defect_code",       "str",      True,  _strip),
            ColumnMapping("severity",            "severity",          "str",      True,  _strip),
            ColumnMapping("status",              "status",            "str",      True,  _strip),
            ColumnMapping("recommended_control", "recommended_control","str",     False, _strip),
        ],
    ),

    "maintenance_assets": SheetMapping(
        sheet_name="maintenance_assets",
        dest_table="maintenance_assets",
        primary_key_col="asset_id",
        required_for_fk=True,
        load_order=3,
        columns=[
            ColumnMapping("asset_id",              "asset_id",              "str",      True,  _strip),
            ColumnMapping("production_line_id",     "production_line_id",    "str",      True,  _strip, "FK → production_lines"),
            ColumnMapping("asset_name",             "asset_name",            "str",      True,  _strip),
            ColumnMapping("last_signal_at",         "last_signal_at",        "datetime", False, _parse_datetime),
            ColumnMapping("failure_risk_score",     "failure_risk_score",    "float",    False, _to_decimal, "0–1 fraction"),
            ColumnMapping("health_status",          "health_status",         "str",      True,  _strip),
            ColumnMapping("next_maintenance_due",   "next_maintenance_due",  "datetime", False, _parse_datetime),
            ColumnMapping("recommended_action",     "recommended_action",    "str",      False, _strip),
        ],
    ),

    "maintenance_work_orders": SheetMapping(
        sheet_name="maintenance_work_orders",
        dest_table="maintenance_work_orders",
        primary_key_col="work_order_id",
        required_for_fk=False,
        load_order=3,
        columns=[
            ColumnMapping("work_order_id",          "work_order_id",          "str",      True,  _strip),
            ColumnMapping("asset_id",                "asset_id",               "str",      True,  _strip,      "FK → maintenance_assets"),
            ColumnMapping("work_type",               "work_type",              "str",      True,  _strip),
            ColumnMapping("status",                  "status",                 "str",      True,  _strip),
            ColumnMapping("created_at",              "created_at",             "datetime", False, _parse_datetime),
            ColumnMapping("scheduled_for",           "scheduled_for",          "datetime", False, _parse_datetime),
            ColumnMapping("priority",                "priority",               "str",      True,  _strip),
            ColumnMapping("assigned_team_or_vendor", "assigned_team_or_vendor","str",      False, _strip),
        ],
    ),

    "energy_readings": SheetMapping(
        sheet_name="energy_readings",
        dest_table="energy_readings",
        primary_key_col="reading_id",
        required_for_fk=False,
        load_order=3,
        columns=[
            ColumnMapping("reading_id",         "reading_id",         "str",      True,  _strip),
            ColumnMapping("entity_id",           "entity_id",          "str",      True,  _strip,      "FK → entities"),
            ColumnMapping("production_line_id",  "production_line_id", "str",      True,  _strip,      "FK → production_lines"),
            ColumnMapping("reading_at",          "reading_at",         "datetime", True,  _parse_datetime),
            ColumnMapping("energy_kwh",          "energy_kwh",         "decimal",  True,  _to_decimal),
            ColumnMapping("unit_rate_inr",       "unit_rate_inr",      "decimal",  False, _to_decimal),
            ColumnMapping("signal",              "signal",             "str",      True,  _strip,
                          "Observed values include SPIKE and NORMAL; import as-is"),
            ColumnMapping("currency",            "currency",           "str",      True,  _strip),
        ],
    ),

    "safety_events": SheetMapping(
        sheet_name="safety_events",
        dest_table="safety_events",
        primary_key_col="safety_event_id",
        required_for_fk=False,
        load_order=3,
        columns=[
            ColumnMapping("safety_event_id", "safety_event_id", "str",      True,  _strip),
            ColumnMapping("entity_id",        "entity_id",       "str",      True,  _strip,      "FK → entities"),
            ColumnMapping("occurred_at",      "occurred_at",     "datetime", True,  _parse_datetime),
            ColumnMapping("event_type",       "event_type",      "str",      True,  _strip),
            ColumnMapping("severity",         "severity",        "str",      True,  _strip),
            ColumnMapping("status",           "status",          "str",      True,  _strip),
            ColumnMapping("description",      "description",     "str",      False, _strip),
        ],
    ),

    "carrier_events": SheetMapping(
        sheet_name="carrier_events",
        dest_table="carrier_events",
        primary_key_col="carrier_event_id",
        required_for_fk=False,
        load_order=3,
        columns=[
            ColumnMapping("carrier_event_id",  "carrier_event_id",  "str",      True,  _strip),
            ColumnMapping("shipment_id",         "shipment_id",       "str",      True,  _strip,      "FK → shipments"),
            ColumnMapping("event_timestamp",     "event_timestamp",   "datetime", True,  _parse_datetime),
            ColumnMapping("event_type",          "event_type",        "str",      True,  _strip),
            ColumnMapping("description",         "description",       "str",      False, _strip),
            ColumnMapping("source_supplier_id",  "source_supplier_id","str",      False, _strip,      "FK → suppliers (nullable)"),
        ],
    ),

    "feed_health": SheetMapping(
        sheet_name="feed_health",
        dest_table="feed_health",
        primary_key_col="feed_id",
        required_for_fk=False,
        load_order=3,
        columns=[
            ColumnMapping("feed_id",              "feed_id",              "str", True,  _strip),
            ColumnMapping("source_name",           "source_name",          "str", True,  _strip),
            ColumnMapping("last_success_at",       "last_success_at",      "datetime", False, _parse_datetime),
            ColumnMapping("consecutive_failures",  "consecutive_failures", "int", True,  _to_int),
            ColumnMapping("health_status",         "health_status",        "str", True,  _strip),
            ColumnMapping("max_age_seconds",       "max_age_seconds",      "int", False, _to_int),
        ],
    ),

    # =========================================================================
    # GROUP 4 — Runtime seed tables  (load_order 4)
    # =========================================================================

    "scenario_templates": SheetMapping(
        sheet_name="scenario_templates",
        dest_table="scenario_templates",
        primary_key_col="scenario_template_id",
        required_for_fk=False,
        load_order=4,
        extra_dest_values={"linked_reference_id": None, "enabled": True},
        columns=[
            ColumnMapping("scenario_template_id", "scenario_template_id", "str", True,  _strip),
            ColumnMapping("scenario_type",         "scenario_type",        "str", True,  _strip),
            ColumnMapping("domain",                "domain",               "str", True,  _strip),
            ColumnMapping("description",           "description",          "str", True,  _strip),
            # DQ-01: workbook column 'linked_reference_id' actually stores severity values.
            # During import: read this column → write to 'severity'; set linked_reference_id = NULL.
            ColumnMapping(
                "linked_reference_id",  # source (col[4]) — stores severity in workbook
                "severity",             # destination column
                "str",
                True,
                _severity_from_linked_ref,
                "DQ-01 fix: col stores severity (HIGH/CRITICAL/MEDIUM/LOW); mapped to severity. "
                "linked_reference_id set to NULL for all rows.",
            ),
            ColumnMapping("base_record_id",    "base_record_id",    "str", False, _strip),
            ColumnMapping("injection_method",  "injection_method",  "str", True,  _strip),
            ColumnMapping("agents_involved",   "agents_involved",   "str", True,  _strip),
            ColumnMapping("expected_response", "expected_response", "str", True,  _strip),
            ColumnMapping("guardrail",         "guardrail",         "str", True,  _strip),
            # DQ-02: 'enabled' column absent from workbook; defaulted to True at import time.
            # No source_col mapping; the loader sets enabled=True unconditionally.
        ],
    ),

    "simulation_config": SheetMapping(
        sheet_name="simulation_config",
        dest_table="simulation_config",
        primary_key_col="config_key",
        required_for_fk=False,
        load_order=4,
        columns=[
            ColumnMapping("config_key",   "config_key",   "str", True,  _strip),
            ColumnMapping("config_value", "config_value", "str", True,  _strip),
            ColumnMapping("description",  "description",  "str", False, _strip),
        ],
    ),
}


# ---------------------------------------------------------------------------
# Sheets deliberately NOT imported (with justification)
# ---------------------------------------------------------------------------

EXCLUDED_SHEETS: Dict[str, str] = {
    "README": (
        "Workbook metadata only (8 rows of purpose/framing text). "
        "No operational data; not a candidate for any database table."
    ),
    "data_dictionary": (
        "Sheet-level descriptions for documentation purposes. "
        "Equivalent content is in this file and PHASE_1_DATA_AUDIT.md."
    ),
    "column_dictionary": (
        "Column-level data dictionary (305 rows). Documentation artefact. "
        "Authoritative mapping is this file (column_mappings.py)."
    ),
    "scenario_instances": (
        "Header-only, 0 data rows. This table is populated at runtime by the "
        "Phase 3 scheduler; the SQL schema is defined in 002_runtime_schema.sql."
    ),
    "agent_runs": (
        "Header-only, 0 data rows. Populated at runtime by Phase 4 agents."
    ),
    "decisions": (
        "Header-only, 0 data rows. Populated at runtime by Phase 4 supervisor agent."
    ),
    "action_queue": (
        "Header-only, 0 data rows. Populated at runtime by Phase 5 action engine."
    ),
    "event_log": (
        "Header-only, 0 data rows. Populated at runtime by Phase 4+ audit subsystem."
    ),
    "blockchain_anchors": (
        "Header-only, 0 data rows. Populated at runtime by Phase 7 blockchain module."
    ),
}


# Import order is the authority for FK-safe loading (masters before dependents).
LOAD_SEQUENCE: List[str] = [
    "ref_entities",
    "ref_departments",
    "ref_products",
    "ref_roles",
    "ref_suppliers",
    "ref_warehouses",
    "ref_users",
    "ref_production_lines",
    "ref_budgets",
    "ref_supplier_contracts",
    "ref_shifts",
    "ref_supplier_offers",
    "ref_reorder_policies",
    "bill_of_materials",
    "business_rules",
    "inventory",
    "orders",
    "order_lines",
    "production_batches",
    "purchase_orders",
    "goods_receipts",
    "maintenance_assets",
    "maintenance_work_orders",
    "shipments",
    "carrier_events",
    "quality_events",
    "energy_readings",
    "safety_events",
    "feed_health",
    "scenario_templates",
    "simulation_config",
]


EXPECTED_SOURCE_ROW_COUNTS: Dict[str, int] = {
    "ref_entities": 4,
    "ref_departments": 11,
    "ref_products": 11,
    "ref_warehouses": 5,
    "ref_suppliers": 8,
    "ref_supplier_offers": 6,
    "ref_roles": 7,
    "ref_users": 30,
    "ref_production_lines": 5,
    "ref_budgets": 4,
    "ref_supplier_contracts": 4,
    "ref_shifts": 4,
    "ref_reorder_policies": 55,
    "bill_of_materials": 5,
    "business_rules": 10,
    "inventory": 150,
    "orders": 200,
    "order_lines": 200,
    "production_batches": 60,
    "shipments": 120,
    "purchase_orders": 3,
    "goods_receipts": 2,
    "quality_events": 40,
    "maintenance_assets": 35,
    "maintenance_work_orders": 50,
    "energy_readings": 240,
    "safety_events": 25,
    "carrier_events": 2,
    "feed_health": 4,
    "scenario_templates": 15,
    "simulation_config": 12,
}


# Status allowlists used by workbook validation and SQL CHECK constraints.
# - Values present in the v2 workbook are included because they occur in source data
#   (e.g. energy_readings.signal HIGH_USAGE, scenario_templates.domain Production).
# - Additional values (COMPLETED, CANCELLED, DELIVERED, STOPPED, …) are forward-
#   compatible statuses for later phases. They do not hide current warnings: they
#   are unused in the seed. Unknown tokens still fail validation.
STATUS_ALLOWLISTS: Dict[Tuple[str, str], Set[str]] = {
    ("ref_entities", "status"): {"ACTIVE", "INACTIVE"},
    ("ref_products", "status"): {"ACTIVE", "INACTIVE", "OBSOLETE"},
    ("ref_warehouses", "status"): {"ACTIVE", "INACTIVE", "MAINTENANCE"},
    ("ref_suppliers", "status"): {"ACTIVE", "INACTIVE", "SUSPENDED"},
    ("ref_suppliers", "risk_band"): {"LOW", "MEDIUM", "HIGH"},
    ("ref_supplier_offers", "offer_status"): {"ACTIVE", "EXPIRED", "WITHDRAWN"},
    ("ref_users", "status"): {"ACTIVE", "INACTIVE", "SUSPENDED"},
    ("ref_production_lines", "status"): {"RUNNING", "STOPPED", "MAINTENANCE", "IDLE"},
    ("ref_budgets", "status"): {"ACTIVE", "INACTIVE", "CLOSED"},
    ("ref_supplier_contracts", "status"): {"ACTIVE", "EXPIRED", "TERMINATED"},
    ("ref_shifts", "status"): {"ACTIVE", "INACTIVE"},
    ("ref_reorder_policies", "status"): {"ACTIVE", "INACTIVE"},
    ("inventory", "stock_signal"): {"NORMAL", "LOW_STOCK", "CRITICAL", "OUT_OF_STOCK", "EXCESS"},
    ("orders", "status"): {"OPEN", "IN_PROGRESS", "AT_RISK", "COMPLETED", "CANCELLED"},
    ("orders", "priority"): {"LOW", "MEDIUM", "HIGH", "CRITICAL"},
    ("production_batches", "status"): {"PLANNED", "IN_PROGRESS", "COMPLETED", "CANCELLED"},
    ("production_batches", "risk_flag"): {
        "NORMAL", "MATERIAL_RISK", "DELAY_RISK", "CAPACITY_RISK", "QUALITY_RISK",
    },
    ("shipments", "status"): {"PLANNED", "IN_TRANSIT", "AT_RISK", "DELIVERED", "CANCELLED"},
    ("shipments", "transport_mode"): {"RAIL", "ROAD", "ROAD_RAIL", "SEA", "AIR"},
    ("shipments", "risk_flag"): {"NORMAL", "DELAY_RISK", "AT_RISK"},
    ("purchase_orders", "status"): {"DRAFT", "APPROVED", "IN_TRANSIT", "RECEIVED", "CANCELLED"},
    ("goods_receipts", "inspection_status"): {"PENDING", "ACCEPTED", "QUALITY_HOLD", "REJECTED"},
    ("quality_events", "severity"): {"LOW", "MEDIUM", "HIGH", "CRITICAL"},
    ("quality_events", "status"): {"OPEN", "IN_REVIEW", "RELEASED", "REJECTED"},
    ("maintenance_assets", "health_status"): {"NORMAL", "WARNING", "CRITICAL"},
    ("maintenance_work_orders", "status"): {"OPEN", "SCHEDULED", "IN_PROGRESS", "COMPLETED", "CANCELLED"},
    ("maintenance_work_orders", "priority"): {"LOW", "MEDIUM", "HIGH", "CRITICAL"},
    ("energy_readings", "signal"): {"NORMAL", "SPIKE", "HIGH_USAGE", "LOW", "OFFLINE", "ALERT"},
    ("safety_events", "event_type"): {
        "NEAR_MISS", "UNSAFE_CONDITION", "EQUIPMENT_GUARD_ALERT",
        "PPE_NONCOMPLIANCE", "INCIDENT", "FIRE", "SPILL",
    },
    ("safety_events", "severity"): {"LOW", "MEDIUM", "HIGH", "CRITICAL"},
    ("safety_events", "status"): {"OPEN", "INVESTIGATING", "CLOSED", "ESCALATED"},
    ("business_rules", "severity"): {"LOW", "MEDIUM", "HIGH", "CRITICAL"},
    ("feed_health", "health_status"): {"HEALTHY", "DEGRADED", "OFFLINE", "UNKNOWN"},
    ("scenario_templates", "domain"): {
        "Inventory", "Procurement", "Finance", "Logistics", "Quality",
        "Maintenance", "Energy", "Safety", "Production", "Cross-functional",
        "General", "Data Quality",
    },
    # DQ-01: workbook column is mislabelled; values are severities.
    ("scenario_templates", "linked_reference_id"): {"LOW", "MEDIUM", "HIGH", "CRITICAL"},
}


@dataclass(frozen=True)
class ForeignKeySpec:
    child_sheet: str
    fk_col: str
    parent_sheet: str
    parent_pk: str


FK_SPECS: List[ForeignKeySpec] = [
    ForeignKeySpec("ref_warehouses", "entity_id", "ref_entities", "entity_id"),
    ForeignKeySpec("ref_users", "role_id", "ref_roles", "role_id"),
    ForeignKeySpec("ref_users", "entity_id", "ref_entities", "entity_id"),
    ForeignKeySpec("ref_production_lines", "entity_id", "ref_entities", "entity_id"),
    ForeignKeySpec("ref_budgets", "entity_id", "ref_entities", "entity_id"),
    ForeignKeySpec("ref_supplier_contracts", "supplier_id", "ref_suppliers", "supplier_id"),
    ForeignKeySpec("ref_shifts", "entity_id", "ref_entities", "entity_id"),
    ForeignKeySpec("ref_supplier_offers", "supplier_id", "ref_suppliers", "supplier_id"),
    ForeignKeySpec("ref_supplier_offers", "item_id", "ref_products", "product_id"),
    ForeignKeySpec("ref_reorder_policies", "item_id", "ref_products", "product_id"),
    ForeignKeySpec("ref_reorder_policies", "warehouse_id", "ref_warehouses", "warehouse_id"),
    ForeignKeySpec("bill_of_materials", "output_product_id", "ref_products", "product_id"),
    ForeignKeySpec("bill_of_materials", "input_item_id", "ref_products", "product_id"),
    ForeignKeySpec("inventory", "item_id", "ref_products", "product_id"),
    ForeignKeySpec("inventory", "warehouse_id", "ref_warehouses", "warehouse_id"),
    ForeignKeySpec("orders", "entity_id", "ref_entities", "entity_id"),
    ForeignKeySpec("order_lines", "order_id", "orders", "order_id"),
    ForeignKeySpec("order_lines", "product_id", "ref_products", "product_id"),
    ForeignKeySpec("production_batches", "production_line_id", "ref_production_lines", "production_line_id"),
    ForeignKeySpec("production_batches", "output_product_id", "ref_products", "product_id"),
    ForeignKeySpec("shipments", "order_id", "orders", "order_id"),
    ForeignKeySpec("shipments", "origin_warehouse_id", "ref_warehouses", "warehouse_id"),
    ForeignKeySpec("shipments", "destination_warehouse_id", "ref_warehouses", "warehouse_id"),
    ForeignKeySpec("shipments", "carrier_supplier_id", "ref_suppliers", "supplier_id"),
    ForeignKeySpec("purchase_orders", "supplier_id", "ref_suppliers", "supplier_id"),
    ForeignKeySpec("purchase_orders", "item_id", "ref_products", "product_id"),
    ForeignKeySpec("purchase_orders", "budget_id", "ref_budgets", "budget_id"),
    ForeignKeySpec("goods_receipts", "po_id", "purchase_orders", "po_id"),
    ForeignKeySpec("goods_receipts", "supplier_id", "ref_suppliers", "supplier_id"),
    ForeignKeySpec("goods_receipts", "item_id", "ref_products", "product_id"),
    ForeignKeySpec("quality_events", "batch_id", "production_batches", "batch_id"),
    ForeignKeySpec("quality_events", "product_id", "ref_products", "product_id"),
    ForeignKeySpec("maintenance_assets", "production_line_id", "ref_production_lines", "production_line_id"),
    ForeignKeySpec("maintenance_work_orders", "asset_id", "maintenance_assets", "asset_id"),
    ForeignKeySpec("energy_readings", "entity_id", "ref_entities", "entity_id"),
    ForeignKeySpec("energy_readings", "production_line_id", "ref_production_lines", "production_line_id"),
    ForeignKeySpec("safety_events", "entity_id", "ref_entities", "entity_id"),
    ForeignKeySpec("carrier_events", "shipment_id", "shipments", "shipment_id"),
    ForeignKeySpec("carrier_events", "source_supplier_id", "ref_suppliers", "supplier_id"),
]


TOTAL_WORKBOOK_ROWS = 1677
MAPPED_IMPORT_ROWS = sum(EXPECTED_SOURCE_ROW_COUNTS.values())  # 1327
METADATA_EXCLUDED_ROWS = 8 + 37 + 305  # README + data_dictionary + column_dictionary
EMPTY_RUNTIME_SHEETS = (
    "scenario_instances",
    "agent_runs",
    "decisions",
    "action_queue",
    "event_log",
    "blockchain_anchors",
)


def dest_primary_key(mapping: SheetMapping) -> str:
    """Return the destination PK column for a sheet mapping."""
    for col in mapping.columns:
        if col.source_col == mapping.primary_key_col:
            return col.dest_col
    return mapping.primary_key_col


def convert_record(mapping: SheetMapping, record: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Apply column mappings and transforms to one source row.

    Returns (dest_row, None) on success, or (None, reason) on rejection.
    Does not fabricate missing values.
    """
    dest: Dict[str, Any] = {}
    for col in mapping.columns:
        raw = record.get(col.source_col)
        if col.transform is not None:
            value = col.transform(raw)
        else:
            value = raw
            if isinstance(value, str):
                value = value.strip() or None
        if col.required and value is None:
            return None, f"missing required source column '{col.source_col}'"
        dest[col.dest_col] = value
    dest.update(mapping.extra_dest_values)
    return dest, None
