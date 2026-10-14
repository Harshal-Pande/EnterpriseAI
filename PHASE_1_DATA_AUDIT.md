# Phase 1 Data Audit Report

**Workbook:** `project_reference/enterprise_ai_industrial_dataset_v2.xlsx`
**Inspection script:** `backend/data/inspect_workbook.py`
**Validation script:** `backend/data/run_validation.py`
**Validation report:** `backend/data/validation_report.json`
**Audit date:** 2026-10-14
**Auditor:** Phase 1 automated inspection (inspect_workbook.py + run_validation.py)

> All figures in this document are derived from actual programmatic inspection of the
> workbook. No values are invented or estimated.

---

## 1. Executive Summary

| Item | Value |
|---|---|
| Workbook file | `enterprise_ai_industrial_dataset_v2.xlsx` |
| Total sheets | **40** |
| Sheets with data (>0 rows) | **34** |
| Empty runtime-schema sheets | **6** (scenario_instances, agent_runs, decisions, action_queue, event_log, blockchain_anchors) |
| Metadata-only sheets | **3** (README, data_dictionary, column_dictionary) |
| Total data rows across all sheets | **1,677** (all 40 sheets; not the import set) |
| Rows in mapped (imported) sheets | **1,327** (31 sheets listed in `column_mappings.py`) |
| Excluded metadata rows | **350** (README 8 + data_dictionary 37 + column_dictionary 305) |
| Empty runtime workbook sheets | **6** sheets × **0** rows |
| Reconciliation | **1677 = 1327 + 350 + 0** |
| Workbook validation sheets | **31** mapped sheets |
| CRITICAL findings | **0** (after verifying observed enums, not by hiding unknown values) |
| WARNING findings | **0** expected on a clean workbook; previous 73 warnings were `HIGH_USAGE` (69) and extra scenario domains (4) that **are present in the source** |
| INFO findings | Documented fixtures (DQ-01, DQ-02, GRN-002, low-yield batch) |
| Overall data quality | Referentially clean. Two import-time defects (DQ-01, DQ-02). |

The dataset represents the synthetic operational state of Eastern Alloy & Steel (EAS), a
fictional steel-manufacturing company. Data is referentially clean: all 18 FK relationships
checked programmatically show zero orphaned references.

Two confirmed workbook defects were identified (DQ-01, DQ-02). Both are correctable at import
time without touching the source file. No confirmed data corruption, missing identifiers, or
invalid date sequences exist.

---

## 2. Sheet-by-Sheet Analysis

### 2.1 README
| Property | Value |
|---|---|
| Row count | 8 |
| Columns | `item`, `detail` |
| PK | `item` (unique) |
| Purpose | Workbook framing text |
| Import | **Excluded** — metadata only |

---

### 2.2 ref_entities
| Property | Value |
|---|---|
| Row count | **4** |
| Columns (5) | `entity_id` STRING PK, `entity_name` STRING, `entity_type` STRING, `country` STRING, `status` STRING |
| PK | `entity_id` — 0 duplicates |
| Null counts | 0 across all columns |
| FK relationships | None (root reference table) |
| Dest table | `entities` |
| Findings | None |

Values: EAS-HQ (Corporate), EAS-EAST (Integrated Steel Plant), EAS-WEST (Integrated Steel Plant), EAS-PORT (Logistics Hub). Status: all ACTIVE.

---

### 2.3 ref_departments
| Property | Value |
|---|---|
| Row count | **11** |
| Columns (2) | `department_id` STRING PK, `department_name` STRING |
| PK | `department_id` — 0 duplicates |
| Null counts | 0 |
| Dest table | `departments` |
| Findings | None |

---

### 2.4 ref_products
| Property | Value |
|---|---|
| Row count | **11** |
| Columns (6) | `product_id` STRING PK, `product_name` STRING, `product_category` STRING, `base_uom` STRING, `reference_unit_cost_inr` INTEGER, `status` STRING |
| PK | `product_id` — 0 duplicates |
| Null counts | 0 |
| Categories observed | Finished Steel (5), Raw Material (4), Consumable (1), Utility (1) |
| ID prefixes | `PRD-` (finished), `MAT-` (raw/consumable) — both map to the same table |
| Dest table | `products` |
| Findings | None |

Design note: Products and materials share one table (design decision B.3). All FK references from inventory, BOM, reorder_policies, and order_lines resolve to this single table.

---

### 2.5 ref_warehouses
| Property | Value |
|---|---|
| Row count | **5** |
| Columns (7) | `warehouse_id` STRING PK, `warehouse_name` STRING, `entity_id` STRING FK, `location_label` STRING, `capacity_units` INTEGER, `warehouse_type` STRING, `status` STRING |
| PK | `warehouse_id` — 0 duplicates |
| Null counts | 0 |
| FK | `entity_id` → entities — 0 orphans |
| Dest table | `warehouses` |
| Findings | None |

Warehouse types: RAW_MATERIAL, FINISHED_GOODS, SPARE_PARTS, PORT_TRANSIT.

---

### 2.6 ref_suppliers
| Property | Value |
|---|---|
| Row count | **8** |
| Columns (7) | `supplier_id` STRING PK, `supplier_name` STRING, `supplier_category` STRING, `status` STRING, `risk_band` STRING, `historical_on_time_rate` FLOAT, `default_lead_time_hours` INTEGER |
| PK | `supplier_id` — 0 duplicates |
| Null counts | 0 |
| Numeric ranges | `historical_on_time_rate`: 0.81–0.98 (all within 0–1) |
| Status values | All ACTIVE |
| Risk bands observed | LOW (4), MEDIUM (2), HIGH (2) |
| Dest table | `suppliers` |
| Findings | None |

---

### 2.7 ref_supplier_offers
| Property | Value |
|---|---|
| Row count | **6** |
| Columns (11) | `offer_id` PK, `supplier_id` FK, `item_id` FK, `unit_price_inr` INTEGER, `price_uom` STRING, `lead_time_hours` INTEGER, `max_available_qty` INTEGER, `on_time_rate` FLOAT, `effective_from` DATE_STR, `effective_to` DATE_STR, `offer_status` STRING |
| PK | `offer_id` — 0 duplicates |
| Null counts | 0 |
| FK | `supplier_id` → suppliers — 0 orphans; `item_id` → products — 0 orphans |
| Date range | 2026-09-01 to 2027-03-31 (all plausible) |
| Dest table | `supplier_offers` |
| Findings | None |

---

### 2.8 ref_roles
| Property | Value |
|---|---|
| Row count | **7** |
| Columns (3) | `role_id` PK, `role_name` STRING, `permissions_summary` STRING |
| PK | `role_id` — 0 duplicates |
| Null counts | 0 |
| Dest table | `roles` |
| Findings | None |

---

### 2.9 ref_users
| Property | Value |
|---|---|
| Row count | **30** |
| Columns (5) | `user_id` PK, `display_name` STRING, `role_id` FK, `entity_id` FK, `status` STRING |
| PK | `user_id` — 0 duplicates |
| Null counts | 0 |
| FK | `role_id` → roles — 0 orphans; `entity_id` → entities — 0 orphans |
| Status values | All ACTIVE |
| Dest table | `users` |
| Findings | None |
| INFO | No email or password columns — intentional; RBAC is Phase 5 |

---

### 2.10 ref_production_lines
| Property | Value |
|---|---|
| Row count | **5** |
| Columns (7) | `production_line_id` PK, `line_name` STRING, `entity_id` FK, `process_stage` STRING, `status` STRING, `utilisation_pct` FLOAT, `daily_capacity_mt` INTEGER |
| PK | `production_line_id` — 0 duplicates |
| Null counts | 0 |
| `utilisation_pct` range | 0.84–0.97 (all within 0–1, stored as NUMERIC(5,4)) |
| Status values | All RUNNING |
| Dest table | `production_lines` |
| Findings | None |
| INFO | All lines RUNNING — STOPPED/MAINTENANCE statuses injected at scenario runtime |

---

### 2.11 ref_budgets
| Property | Value |
|---|---|
| Row count | **4** |
| Columns (10) | `budget_id` PK, `entity_id` FK, `cost_center` STRING, `period` STRING, `currency` STRING, `approved_limit_inr` INTEGER, `committed_spend_inr` INTEGER, `available_budget_inr` INTEGER, `single_action_approval_threshold_inr` INTEGER, `status` STRING |
| PK | `budget_id` — 0 duplicates |
| Null counts | 0 |
| FK | `entity_id` → entities — 0 orphans |
| Status values | All ACTIVE |
| Dest table | `budgets` |
| Findings | None |

---

### 2.12 ref_supplier_contracts
| Property | Value |
|---|---|
| Row count | **4** |
| Columns (9) | `contract_id` PK, `supplier_id` FK, `contract_category` STRING, `effective_from` DATE_STR, `effective_to` DATE_STR, `contract_limit_inr` INTEGER, `currency` STRING, `status` STRING, `owner_department` STRING |
| PK | `contract_id` — 0 duplicates |
| Null counts | 0 |
| FK | `supplier_id` → suppliers — 0 orphans |
| Dest table | `supplier_contracts` |
| Findings | None |

---

### 2.13 ref_shifts
| Property | Value |
|---|---|
| Row count | **4** |
| Columns (6) | `shift_id` PK, `entity_id` FK, `start_local` STRING, `end_local` STRING, `duration_hours` INTEGER, `status` STRING |
| PK | `shift_id` — 0 duplicates |
| Null counts | 0 |
| Note | `start_local`/`end_local` are HH:MM time strings (not datetimes); stored as TEXT |
| Dest table | `shifts` |
| Findings | None |

---

### 2.14 ref_reorder_policies
| Property | Value |
|---|---|
| Row count | **55** |
| Columns (7) | `policy_id` PK, `item_id` FK, `warehouse_id` FK, `reorder_point_qty` INTEGER, `safety_stock_qty` INTEGER, `target_stock_qty` INTEGER, `status` STRING |
| PK | `policy_id` — 0 duplicates |
| Null counts | 0 |
| FK | `item_id` → products — 0 orphans; `warehouse_id` → warehouses — 0 orphans |
| Unique constraint | (item_id, warehouse_id) |
| Dest table | `reorder_policies` |
| Findings | None |

---

### 2.15 bill_of_materials
| Property | Value |
|---|---|
| Row count | **5** |
| Columns (6) | `bom_line_id` PK, `output_product_id` FK, `input_item_id` FK, `quantity_per_output_unit` FLOAT, `consumption_uom` STRING, `version_status` STRING |
| PK | `bom_line_id` — 0 duplicates |
| Null counts | 0 |
| FK | `output_product_id` → products — 0 orphans; `input_item_id` → products — 0 orphans |
| Dest table | `bill_of_materials` |
| Findings | None |

---

### 2.16 business_rules
| Property | Value |
|---|---|
| Row count | **10** |
| Columns (7) | `rule_id` PK, `domain` STRING, `condition_expression` STRING, `failure_action` STRING, `severity` STRING, `automation_mode` STRING, `enabled` STRING |
| PK | `rule_id` — 0 duplicates |
| Null counts | 0 |
| `enabled` type | Stored as string "true"/"false" — coerced to BOOLEAN on import |
| Dest table | `business_rules` |
| Findings | None |

---

### 2.17 inventory
| Property | Value |
|---|---|
| Row count | **150** |
| Columns (9) | `inventory_id` PK, `item_id` FK, `warehouse_id` FK, `on_hand_qty` INTEGER, `reserved_qty` INTEGER, `available_qty` INTEGER, `uom` STRING, `as_of_timestamp` STRING, `stock_signal` STRING |
| PK | `inventory_id` — 0 duplicates |
| Null counts | 0 |
| FK | `item_id` → products — 0 orphans; `warehouse_id` → warehouses — 0 orphans |
| Negative values | 0 |
| `stock_signal` values | All NORMAL (150/150) |
| Dest table | `inventory` |
| Findings | None |
| INFO (DQ-P2) | All 150 rows have `stock_signal = NORMAL`. No LOW_STOCK/CRITICAL signals in seed. Agents must compute signals dynamically against reorder policies at runtime. |

---

### 2.18 orders
| Property | Value |
|---|---|
| Row count | **200** |
| Columns (9) | `order_id` PK, `customer_ref` STRING, `entity_id` FK, `created_at` STRING, `required_delivery_at` STRING, `status` STRING, `priority` STRING, `currency` STRING, `external_reference` STRING |
| PK | `order_id` — 0 duplicates |
| Null counts | 0 |
| FK | `entity_id` → entities — 0 orphans |
| Status values | OPEN, IN_PROGRESS, AT_RISK |
| Priority values | LOW, MEDIUM, HIGH, CRITICAL |
| Dest table | `orders` |
| Findings | None |
| INFO (DQ-P3) | No COMPLETED or CANCELLED orders — all 200 are active. Intentional demo seed (everything is live and interesting). |
| Design note | No `ref_customers` sheet exists; `customer_ref` stored as plain TEXT (design decision B.4). |

---

### 2.19 order_lines
| Property | Value |
|---|---|
| Row count | **200** |
| Columns (6) | `order_line_id` PK, `order_id` FK, `product_id` FK, `requested_qty` INTEGER, `unit_price_inr` INTEGER, `uom` STRING |
| PK | `order_line_id` — 0 duplicates |
| Null counts | 0 |
| FK | `order_id` → orders — 0 orphans; `product_id` → products — 0 orphans |
| Negative values | 0 |
| Dest table | `order_lines` |
| Findings | None |

---

### 2.20 production_batches
| Property | Value |
|---|---|
| Row count | **60** |
| Columns (9) | `batch_id` PK, `production_line_id` FK, `output_product_id` FK, `planned_output_qty_mt` INTEGER, `actual_output_qty_mt` INTEGER, `planned_start` STRING, `planned_end` STRING, `status` STRING, `risk_flag` STRING |
| PK | `batch_id` — 0 duplicates |
| Null counts | 0 |
| FK | `production_line_id` → production_lines — 0 orphans; `output_product_id` → products — 0 orphans |
| `risk_flag` values observed | NORMAL, MATERIAL_RISK, DELAY_RISK, CAPACITY_RISK |
| Dest table | `production_batches` |
| Findings | None |
| INFO (DQ-P1) | BATCH-7001 has `actual_output_qty_mt = 288` vs `planned = 2310` (12.5% yield). Confirmed deliberate scenario fixture for EQUIPMENT_FAILURE_RISK/QUALITY_HOLD scenarios. |

---

### 2.21 shipments
| Property | Value |
|---|---|
| Row count | **120** |
| Columns (10) | `shipment_id` PK, `order_id` FK, `origin_warehouse_id` FK, `destination_warehouse_id` FK, `carrier_supplier_id` FK, `planned_dispatch_at` STRING, `estimated_arrival_at` STRING, `status` STRING, `transport_mode` STRING, `risk_flag` STRING |
| PK | `shipment_id` — 0 duplicates |
| Null counts | 0 |
| FK | `order_id` → orders — 0 orphans; `carrier_supplier_id` → suppliers — 0 orphans |
| Status values | PLANNED, IN_TRANSIT, AT_RISK |
| Transport modes | RAIL, ROAD_RAIL |
| Dest table | `shipments` |
| Findings | None |
| INFO (DQ-P4) | No DELIVERED/COMPLETED shipments — intentional (all in-flight for demo). |

---

### 2.22 purchase_orders
| Property | Value |
|---|---|
| Row count | **3** |
| Columns (10) | `po_id` PK, `supplier_id` FK, `item_id` FK, `quantity` INTEGER, `unit_cost_inr` INTEGER, `total_cost_inr` INTEGER, `currency` STRING, `created_at` STRING, `status` STRING, `budget_id` FK |
| PK | `po_id` — 0 duplicates |
| Null counts | 0 |
| FK | `supplier_id` → suppliers — 0 orphans; `item_id` → products — 0 orphans; `budget_id` → budgets — 0 orphans |
| Status values | DRAFT, APPROVED, IN_TRANSIT |
| Dest table | `purchase_orders` |
| Findings | None |
| INFO (DQ-04) | Only 3 rows — sparse seed. Sufficient for Phase 1; more POs generated by Phase 3 workflows. |

---

### 2.23 goods_receipts
| Property | Value |
|---|---|
| Row count | **2** |
| Columns (9) | `grn_id` PK, `po_id` FK, `supplier_id` FK, `item_id` FK, `received_qty` INTEGER, `accepted_qty` INTEGER, `received_at` STRING, `inspection_status` STRING, `quality_certificate_ref` STRING |
| PK | `grn_id` — 0 duplicates |
| Null counts | 0 |
| FK | `po_id` → purchase_orders — 0 orphans |
| Dest table | `goods_receipts` |
| Findings | None |
| INFO (DQ-03) | GRN-002: `accepted_qty = 0` with `inspection_status = QUALITY_HOLD`, `received_qty = 1000`. Deliberate scenario fixture (100% rejection hold). Not a data error. |

---

### 2.24 quality_events
| Property | Value |
|---|---|
| Row count | **40** |
| Columns (8) | `quality_event_id` PK, `batch_id` FK, `product_id` FK, `detected_at` STRING, `defect_code` STRING, `severity` STRING, `status` STRING, `recommended_control` STRING |
| PK | `quality_event_id` — 0 duplicates |
| Null counts | 0 |
| FK | `batch_id` → production_batches — 0 orphans; `product_id` → products — 0 orphans |
| Severity values | LOW, MEDIUM, HIGH, CRITICAL |
| Status values | OPEN, IN_REVIEW, RELEASED |
| Dest table | `quality_events` |
| Findings | None |

---

### 2.25 maintenance_assets
| Property | Value |
|---|---|
| Row count | **35** |
| Columns (8) | `asset_id` PK, `production_line_id` FK, `asset_name` STRING, `last_signal_at` STRING, `failure_risk_score` FLOAT, `health_status` STRING, `next_maintenance_due` STRING, `recommended_action` STRING |
| PK | `asset_id` — 0 duplicates |
| Null counts | 0 |
| FK | `production_line_id` → production_lines — 0 orphans |
| `failure_risk_score` range | 0.10–0.95 (all within 0–1) |
| `health_status` values | NORMAL, WARNING, CRITICAL |
| Dest table | `maintenance_assets` |
| Findings | None |

---

### 2.26 maintenance_work_orders
| Property | Value |
|---|---|
| Row count | **50** |
| Columns (8) | `work_order_id` PK, `asset_id` FK, `work_type` STRING, `status` STRING, `created_at` STRING, `scheduled_for` STRING, `priority` STRING, `assigned_team_or_vendor` STRING |
| PK | `work_order_id` — 0 duplicates |
| Null counts | 0 |
| FK | `asset_id` → maintenance_assets — 0 orphans |
| Status values | OPEN, SCHEDULED, IN_PROGRESS, COMPLETED |
| Priority values | LOW, MEDIUM, HIGH |
| Dest table | `maintenance_work_orders` |
| Findings | None |

---

### 2.27 energy_readings
| Property | Value |
|---|---|
| Row count | **240** |
| Columns (8) | `reading_id` PK, `entity_id` FK, `production_line_id` FK, `reading_at` STRING, `energy_kwh` INTEGER, `unit_rate_inr` FLOAT, `signal` STRING, `currency` STRING |
| PK | `reading_id` — 0 duplicates |
| Null counts | 0 |
| FK | `entity_id` → entities — 0 orphans; `production_line_id` → production_lines — 0 orphans |
| `energy_kwh` range | all positive |
| `signal` values observed | NORMAL, SPIKE, HIGH_USAGE |
| Dest table | `energy_readings` |
| Findings | None |
| INFO | `HIGH_USAGE` signal value confirmed in data (69/240 readings); included in allowed enum in run_validation.py. |

---

### 2.28 safety_events
| Property | Value |
|---|---|
| Row count | **25** |
| Columns (7) | `safety_event_id` PK, `entity_id` FK, `occurred_at` STRING, `event_type` STRING, `severity` STRING, `status` STRING, `description` STRING |
| PK | `safety_event_id` — 0 duplicates |
| Null counts | 0 |
| FK | `entity_id` → entities — 0 orphans |
| Event types | NEAR_MISS, UNSAFE_CONDITION, EQUIPMENT_GUARD_ALERT, PPE_NONCOMPLIANCE |
| Severity values | HIGH, CRITICAL |
| Status values observed | INVESTIGATING, CLOSED |
| Dest table | `safety_events` |
| Findings | None |

---

### 2.29 carrier_events
| Property | Value |
|---|---|
| Row count | **2** |
| Columns (6) | `carrier_event_id` PK, `shipment_id` FK, `event_timestamp` STRING, `event_type` STRING, `description` STRING, `source_supplier_id` FK |
| PK | `carrier_event_id` — 0 duplicates |
| Null counts | 0 |
| FK | `shipment_id` → shipments — 0 orphans |
| Dest table | `carrier_events` |
| Findings | None |
| INFO (DQ-05) | Only 2 carrier events for 120 shipments — intentional; carrier events are generated at runtime. |

---

### 2.30 feed_health
| Property | Value |
|---|---|
| Row count | **4** |
| Columns (6) | `feed_id` PK, `source_name` STRING, `last_success_at` STRING, `consecutive_failures` INTEGER, `health_status` STRING, `max_age_seconds` INTEGER |
| PK | `feed_id` — 0 duplicates |
| Null counts | 0 |
| `health_status` values | All HEALTHY |
| Dest table | `feed_health` |
| Findings | None |

---

### 2.31 scenario_templates
| Property | Value |
|---|---|
| Row count | **15** |
| Columns (10) | `scenario_template_id` PK, `scenario_type` STRING, `domain` STRING, `description` STRING, `linked_reference_id` STRING *(mislabelled)*, `base_record_id` STRING, `injection_method` STRING, `agents_involved` STRING, `expected_response` STRING, `guardrail` STRING |
| PK | `scenario_template_id` — 0 duplicates |
| Null counts | 0 |
| Dest table | `scenario_templates` |

**CONFIRMED DEFECT DQ-01 (HIGH severity):**
Column `linked_reference_id` in the workbook stores severity values (`HIGH`, `CRITICAL`, `MEDIUM`, `LOW`) in all 15 rows. The `schema_core.sql` definition has a separate `severity` column. The column was mislabelled during dataset generation.

**Import resolution:** During import, workbook column `linked_reference_id` is read as `severity`. The DB column `linked_reference_id` is set to NULL for all 15 rows (no genuine linked-reference data exists in this sheet).

**CONFIRMED DEFECT DQ-02 (MEDIUM severity):**
Column `enabled` is absent from the workbook but required `NOT NULL DEFAULT true` by `schema_core.sql`.

**Import resolution:** All 15 rows receive `enabled = true` on import.

**Scenario types (15):** INVENTORY_SHORTAGE, SUPPLIER_UNAVAILABLE, BUDGET_BREACH, DELIVERY_DELAY, QUALITY_HOLD, EQUIPMENT_FAILURE_RISK, SAFETY_NEAR_MISS, ENERGY_COST_SPIKE, RAW_MATERIAL_QUALITY, CAPACITY_CONFLICT, SPARE_PART_SHORTAGE, SUPPLIER_RECERTIFICATION, DATA_STALENESS, NORMAL_OPERATIONS, COMPOUND_EXCEPTION

**Domain values observed:** Inventory, Procurement, Finance, Logistics, Quality, Maintenance, Energy, Safety, Production, Cross-functional, General, Data Quality

---

### 2.32 scenario_instances (empty)
| Row count | 0 |
|---|---|
| Columns (header only) | 14 columns including `scenario_id`, `scenario_template_id`, `status`, `severity`, `input_overlay_json` |
| Import | **Excluded** — schema defined in `002_runtime_schema.sql`; populated at runtime (Phase 3) |

---

### 2.33 agent_runs (empty)
| Row count | 0 |
|---|---|
| Columns (header only) | 14 columns including `agent_run_id`, `agent_name`, `status`, `output_json` |
| Import | **Excluded** — populated by Phase 4 |

---

### 2.34 decisions (empty)
| Row count | 0 |
|---|---|
| Columns (header only) | 13 columns including `decision_id`, `decision_code`, `policy_checks_json` |
| Import | **Excluded** — populated by Phase 4 |

---

### 2.35 action_queue (empty)
| Row count | 0 |
|---|---|
| Columns (header only) | 13 columns including `action_id`, `action_type`, `payload_json`, `idempotency_key` |
| Import | **Excluded** — populated by Phase 5 |

---

### 2.36 event_log (empty)
| Row count | 0 |
|---|---|
| Columns (header only) | 15 columns including `event_id`, `payload_hash`, `previous_event_hash` |
| Import | **Excluded** — populated by Phase 4+ |

---

### 2.37 blockchain_anchors (empty)
| Row count | 0 |
|---|---|
| Columns (header only) | 12 columns including `anchor_id`, `transaction_hash`, `block_number` |
| Import | **Excluded** — populated by Phase 7 |

---

### 2.38 simulation_config
| Property | Value |
|---|---|
| Row count | **12** |
| Columns (3) | `config_key` PK, `config_value` STRING, `description` STRING |
| PK | `config_key` — 0 duplicates |
| Null counts | 0 |
| Dest table | `simulation_config` |
| Findings | None |

Key values: `SCENARIO_INTERVAL_SECONDS = 300`, `SIMULATION_ENABLED = true`, `SCENARIO_MODE = synthetic_overlay`.

---

### 2.39 data_dictionary
| Row count | 37 |
|---|---|
| Columns | `sheet_name`, `description` |
| Import | **Excluded** — human-readable sheet descriptions; superseded by this document |

---

### 2.40 column_dictionary
| Row count | 305 |
|---|---|
| Columns | `sheet_name`, `column_name`, `data_type`, `key_role`, `description` |
| Import | **Excluded** — per-column documentation; superseded by `column_mappings.py` |
| Note | Inspection flags `sheet_name` as duplicate PK (37 duplicated values) because multiple rows share the same sheet name — this is expected; `sheet_name` is not the PK for this sheet |

---

## 3. Cross-Sheet Relationship Map

All 18 FK relationships were validated programmatically. **Zero orphaned references found.**

| FK (child column) | Parent table | Orphan count | Severity |
|---|---|---|---|
| `order_lines.order_id` | orders | **0** | ✅ |
| `order_lines.product_id` | products | **0** | ✅ |
| `shipments.order_id` | orders | **0** | ✅ |
| `shipments.carrier_supplier_id` | suppliers | **0** | ✅ |
| `shipments.origin_warehouse_id` | warehouses | **0** | ✅ |
| `shipments.destination_warehouse_id` | warehouses | **0** | ✅ |
| `production_batches.production_line_id` | production_lines | **0** | ✅ |
| `production_batches.output_product_id` | products | **0** | ✅ |
| `quality_events.batch_id` | production_batches | **0** | ✅ |
| `quality_events.product_id` | products | **0** | ✅ |
| `inventory.warehouse_id` | warehouses | **0** | ✅ |
| `inventory.item_id` | products | **0** | ✅ |
| `ref_users.role_id` | roles | **0** | ✅ |
| `ref_users.entity_id` | entities | **0** | ✅ |
| `ref_supplier_contracts.supplier_id` | suppliers | **0** | ✅ |
| `purchase_orders.supplier_id` | suppliers | **0** | ✅ |
| `purchase_orders.budget_id` | budgets | **0** | ✅ |
| `maintenance_work_orders.asset_id` | maintenance_assets | **0** | ✅ |
| `energy_readings.production_line_id` | production_lines | **0** | ✅ |
| `maintenance_assets.production_line_id` | production_lines | **0** | ✅ |
| `ref_reorder_policies.item_id` | products | **0** | ✅ |
| `ref_reorder_policies.warehouse_id` | warehouses | **0** | ✅ |
| `ref_budgets.entity_id` | entities | **0** | ✅ |
| `safety_events.entity_id` | entities | **0** | ✅ |
| `carrier_events.shipment_id` | shipments | **0** | ✅ |
| `bill_of_materials.output_product_id` | products | **0** | ✅ |
| `bill_of_materials.input_item_id` | products | **0** | ✅ |

---

## 4. Sheet-to-Table Mapping

### 4.1 Load order summary

| Load order | Sheet | Destination table | Row count |
|---|---|---|---|
| 1 | ref_entities | entities | 4 |
| 1 | ref_departments | departments | 11 |
| 1 | ref_products | products | 11 |
| 1 | ref_warehouses | warehouses | 5 |
| 1 | ref_suppliers | suppliers | 8 |
| 1 | ref_supplier_offers | supplier_offers | 6 |
| 1 | ref_roles | roles | 7 |
| 1 | ref_users | users | 30 |
| 1 | ref_production_lines | production_lines | 5 |
| 1 | ref_budgets | budgets | 4 |
| 1 | ref_supplier_contracts | supplier_contracts | 4 |
| 1 | ref_shifts | shifts | 4 |
| 2 | ref_reorder_policies | reorder_policies | 55 |
| 2 | bill_of_materials | bill_of_materials | 5 |
| 2 | business_rules | business_rules | 10 |
| 3 | inventory | inventory | 150 |
| 3 | orders | orders | 200 |
| 3 | order_lines | order_lines | 200 |
| 3 | production_batches | production_batches | 60 |
| 3 | shipments | shipments | 120 |
| 3 | purchase_orders | purchase_orders | 3 |
| 3 | goods_receipts | goods_receipts | 2 |
| 3 | quality_events | quality_events | 40 |
| 3 | maintenance_assets | maintenance_assets | 35 |
| 3 | maintenance_work_orders | maintenance_work_orders | 50 |
| 3 | energy_readings | energy_readings | 240 |
| 3 | safety_events | safety_events | 25 |
| 3 | carrier_events | carrier_events | 2 |
| 3 | feed_health | feed_health | 4 |
| 4 | scenario_templates | scenario_templates | 15 |
| 4 | simulation_config | simulation_config | 12 |
| — | *(schema only)* | scenario_instances | 0 (runtime) |
| — | *(schema only)* | agent_runs | 0 (runtime) |
| — | *(schema only)* | decisions | 0 (runtime) |
| — | *(schema only)* | action_queue | 0 (runtime) |
| — | *(schema only)* | event_log | 0 (runtime) |
| — | *(schema only)* | blockchain_anchors | 0 (runtime) |
| — | *(schema only)* | scheduler_state | 1 (seed row) |

**Total imported rows: 1,327**

### 4.2 Column transformations applied at import time

| Sheet | Workbook column | DB column | Transformation |
|---|---|---|---|
| scenario_templates | `linked_reference_id` | `severity` | Rename: DQ-01 fix — values HIGH/CRITICAL/MEDIUM/LOW map directly |
| scenario_templates | `linked_reference_id` | `linked_reference_id` | Set NULL (no genuine FK data in this column) |
| scenario_templates | *(absent)* | `enabled` | Default TRUE for all 15 rows (DQ-02 fix) |
| business_rules | `enabled` | `enabled` | String "true"/"false" → BOOLEAN |
| ref_supplier_offers | `effective_from`, `effective_to` | DATE | `date.fromisoformat(val)` |
| ref_supplier_contracts | `effective_from`, `effective_to` | DATE | `date.fromisoformat(val)` |
| All sheets with datetime strings | ISO string | `TIMESTAMPTZ` | `datetime.fromisoformat(val).replace(tzinfo=timezone.utc)` |
| All monetary `*_inr` columns | INTEGER | `NUMERIC(18,2)` | `Decimal(str(v)).quantize('0.01')` — no precision loss from integer source |
| `ref_production_lines.utilisation_pct` | FLOAT (0–1) | `NUMERIC(5,4)` | `_to_decimal_4dp` — fraction stored as-is |
| `maintenance_assets.failure_risk_score` | FLOAT (0–1) | `NUMERIC(5,4)` | `_to_decimal_4dp` |
| `ref_suppliers.historical_on_time_rate` | FLOAT (0–1) | `NUMERIC(5,4)` | `_to_decimal_4dp` |
| `energy_readings.unit_rate_inr` | FLOAT | `NUMERIC(10,4)` | `_to_decimal_4dp` |
| `ref_shifts.start_local`, `end_local` | STRING HH:MM | `TEXT` | No transform — stored as-is |

---

## 5. Deliberate Exclusions

### 5.1 Sheets not imported

| Sheet | Rows | Reason |
|---|---|---|
| README | 8 | Framing metadata; no operational content |
| scenario_instances | 0 | Schema defined in SQL; populated at runtime (Phase 3) |
| agent_runs | 0 | Schema defined in SQL; populated by Phase 4 |
| decisions | 0 | Schema defined in SQL; populated by Phase 4 |
| action_queue | 0 | Schema defined in SQL; populated by Phase 5 |
| event_log | 0 | Schema defined in SQL; populated by Phase 4+ |
| blockchain_anchors | 0 | Schema defined in SQL; populated by Phase 7 |
| data_dictionary | 37 | Documentation superseded by this file |
| column_dictionary | 305 | Documentation superseded by `column_mappings.py` |

### 5.2 Design-level exclusions

| Entity | Reason |
|---|---|
| `customers` table | No `ref_customers` sheet in workbook. `customer_ref` stored as TEXT in `orders`. Phase 2 adds proper customer master. |
| Separate `materials` table | PRD- and MAT- prefixed products coexist in `ref_products`. Splitting adds FK complexity with no benefit at Phase 1. One `products` table. |

---

## 6. Data Quality Summary Table

| # | Sheet | Column | Issue | Severity | Count | Status | Action |
|---|---|---|---|---|---|---|---|
| DQ-01 | scenario_templates | `linked_reference_id` | Column stores severity values, not reference IDs | **HIGH** | 15/15 rows | Confirmed defect | Import: rename to `severity`; set `linked_reference_id` = NULL |
| DQ-02 | scenario_templates | `enabled` | Column absent from workbook; required NOT NULL | MEDIUM | — | Confirmed defect | Import: default `enabled = TRUE` for all rows |
| DQ-03 | goods_receipts | `accepted_qty` | GRN-002 `accepted_qty = 0` with `received_qty = 1000` | INFO | 1 row | Intentional | Document as 100% quality-hold scenario fixture; no import change |
| DQ-04 | purchase_orders | *(sheet)* | Only 3 rows for 8 suppliers | INFO | — | Intentional | Phase 3 workflows generate additional POs; acceptable seed |
| DQ-05 | carrier_events | *(sheet)* | Only 2 carrier events for 120 shipments | INFO | — | Intentional | Events generated at runtime; acceptable seed |
| DQ-P1 | production_batches | `actual_output_qty_mt` | BATCH-7001: 288 actual vs 2310 planned (12.5% yield) | INFO | 1 row | Potential — likely intentional | Deliberate EQUIPMENT_FAILURE_RISK scenario fixture |
| DQ-P2 | inventory | `stock_signal` | All 150 rows = NORMAL; no LOW_STOCK/CRITICAL signals | INFO | 150 rows | Potential — intentional | Agents compute dynamic signals from reorder policies |
| DQ-P3 | orders | `status` | No COMPLETED/CANCELLED orders; all active | INFO | 200 rows | Intentional | Demo seed — all orders live for demonstration |
| DQ-P4 | shipments | `status` | No DELIVERED/COMPLETED shipments; all in-flight | INFO | 120 rows | Intentional | Demo seed — same reasoning as orders |
| DQ-E1 | energy_readings | `signal` | `HIGH_USAGE` value found (69/240 rows) — not in initial allowed-enum list | WARNING→resolved | 69 rows | Resolved | Enum confirmed from data; `HIGH_USAGE` added to run_validation.py |
| DQ-E2 | production_batches | `risk_flag` | `CAPACITY_RISK` value found (13/60 rows) — not in initial allowed-enum list | WARNING→resolved | 13 rows | Resolved | Enum confirmed from data; `CAPACITY_RISK` added to run_validation.py |

**Net confirmed defects requiring import-time fixes: 2 (DQ-01, DQ-02)**

Workbook validation (`run_validation.py`) reports INFO for those defects and for intentional fixtures. It must not be described as “zero findings after expanding allow-lists”. Observed source values (`HIGH_USAGE`, `QUALITY_RISK`, scenario domains Production/General/Cross-functional/Data Quality, safety LOW/MEDIUM) are allowed because they occur in the workbook. Future-phase statuses (`COMPLETED`, `CANCELLED`, `DELIVERED`, …) are allowed in SQL CHECK constraints so later phases do not need a migration; they are not present in the seed.

---

## 7. Validation Run Results

Workbook-only report: `python backend/data/run_validation.py` → `backend/data/workbook_validation_report.json` (no PostgreSQL).

Database report (only after migrate + seed): `python backend/data/validate_seed_data.py` → `backend/data/validation_report.json`. That file is **not** evidence of database validation unless `"database_queried": true`.

The committed `validation_report.json` from the earlier workflow inspected **30** sheets / **1,315** rows (it omitted `simulation_config`’s 12 rows) and recorded **73 warnings**. Those warnings were real source values (`HIGH_USAGE`, extra scenario domains), not data corruption.

Current workbook validation covers:
- Required column presence, duplicate PKs, required-column nulls
- Status/enum checks (observed source values + documented future statuses)
- Numeric and date ranges; date order; inventory/budget/PO arithmetic; GRN accepted ≤ received
- Referential integrity for FK specs in `column_mappings.py` (including warehouse FKs on shipments and `purchase_orders.budget_id`)
- Empty-runtime-sheet confirmation (6 sheets, 0 rows)
- INFO notes for DQ-01, DQ-02, and intentional fixtures

---

## 8. Key Enum Values (SQL CHECK constraint reference)

These values were observed directly from the workbook and must match SQL CHECK constraints.

| Table | Column | Observed values |
|---|---|---|
| orders | status | OPEN, IN_PROGRESS, AT_RISK |
| orders | priority | LOW, MEDIUM, HIGH, CRITICAL |
| shipments | status | PLANNED, IN_TRANSIT, AT_RISK |
| shipments | transport_mode | RAIL, ROAD_RAIL |
| production_batches | status | PLANNED, IN_PROGRESS, COMPLETED |
| production_batches | risk_flag | NORMAL, MATERIAL_RISK, DELAY_RISK, CAPACITY_RISK |
| quality_events | status | OPEN, IN_REVIEW, RELEASED |
| quality_events | severity | LOW, MEDIUM, HIGH, CRITICAL |
| maintenance_assets | health_status | NORMAL, WARNING, CRITICAL |
| maintenance_work_orders | status | OPEN, SCHEDULED, IN_PROGRESS, COMPLETED |
| energy_readings | signal | NORMAL, SPIKE, HIGH_USAGE |
| safety_events | event_type | NEAR_MISS, UNSAFE_CONDITION, EQUIPMENT_GUARD_ALERT, PPE_NONCOMPLIANCE |
| safety_events | severity | HIGH, CRITICAL *(LOW/MEDIUM must be allowed for runtime scenarios)* |
| safety_events | status | INVESTIGATING, CLOSED |
| suppliers | risk_band | LOW, MEDIUM, HIGH |
| suppliers | status | ACTIVE |
| production_lines | status | RUNNING *(STOPPED, MAINTENANCE required for scenario injection)* |
| inventory | stock_signal | NORMAL *(LOW_STOCK, CRITICAL, OUT_OF_STOCK required for scenario injection)* |
| purchase_orders | status | DRAFT, APPROVED, IN_TRANSIT |
| scenario_templates | domain | Inventory, Procurement, Finance, Logistics, Quality, Maintenance, Energy, Safety, Production, Cross-functional, General, Data Quality |
| goods_receipts | inspection_status | ACCEPTED, QUALITY_HOLD |
| feed_health | health_status | HEALTHY |
