# Phase 1 Implementation Plan
**Generated from:** live workbook inspection + full repo read  
**Workbook:** `project_reference/enterprise_ai_industrial_dataset_v2.xlsx`  
**Date:** 2026-10-14  

---

## Part A — Workbook Findings

### A.1 Sheet inventory (40 sheets total)

| Sheet | Row count | Category | Load group |
|-------|-----------|----------|------------|
| README | 8 | Metadata | skip |
| ref_entities | 4 | Reference | 1 – reference |
| ref_departments | 11 | Reference | 1 – reference |
| ref_products | 11 | Reference + materials | 1 – reference |
| ref_warehouses | 5 | Reference | 1 – reference |
| ref_suppliers | 8 | Reference | 1 – reference |
| ref_supplier_offers | 6 | Reference | 1 – reference |
| ref_roles | 7 | Reference | 1 – reference |
| ref_users | 30 | Reference | 1 – reference |
| ref_production_lines | 5 | Reference | 1 – reference |
| ref_budgets | 4 | Reference | 1 – reference |
| ref_supplier_contracts | 4 | Reference | 1 – reference |
| ref_shifts | 4 | Reference | 1 – reference |
| ref_reorder_policies | 55 | Reference | 2 – operational config |
| bill_of_materials | 5 | Reference | 2 – operational config |
| business_rules | 10 | Reference | 2 – operational config |
| inventory | 150 | Operational transaction | 3 – transactional |
| orders | 200 | Operational transaction | 3 – transactional |
| order_lines | 200 | Operational transaction | 3 – transactional |
| production_batches | 60 | Operational transaction | 3 – transactional |
| shipments | 120 | Operational transaction | 3 – transactional |
| purchase_orders | 3 | Operational transaction | 3 – transactional |
| goods_receipts | 2 | Operational transaction | 3 – transactional |
| quality_events | 40 | Operational transaction | 3 – transactional |
| maintenance_assets | 35 | Operational transaction | 3 – transactional |
| maintenance_work_orders | 50 | Operational transaction | 3 – transactional |
| energy_readings | 240 | Operational transaction | 3 – transactional |
| safety_events | 25 | Operational transaction | 3 – transactional |
| carrier_events | 2 | Operational transaction | 3 – transactional |
| feed_health | 4 | Operational monitoring | 3 – transactional |
| scenario_templates | 15 | Runtime | 4 – runtime seed |
| scenario_instances | 0 | Runtime (empty – schema only) | 4 – runtime |
| agent_runs | 0 | Runtime (empty – schema only) | 4 – runtime |
| decisions | 0 | Runtime (empty – schema only) | 4 – runtime |
| action_queue | 0 | Runtime (empty – schema only) | 4 – runtime |
| event_log | 0 | Runtime (empty – schema only) | 4 – runtime |
| blockchain_anchors | 0 | Runtime (empty – schema only) | 4 – runtime |
| simulation_config | 12 | Config reference | 4 – runtime seed |
| data_dictionary | 37 | Metadata | skip |
| column_dictionary | 305 | Metadata | skip |

**Total data rows:** 1,677 (of which 0 are in the six empty runtime sheets)

### A.2 Full-cross-sheet FK validation results

All 18 FK relationships checked programmatically. **Zero orphan references found anywhere.** The dataset is referentially clean.

| Relationship | Result |
|---|---|
| order_lines.order_id → orders | ✅ 0 orphans |
| shipments.order_id → orders | ✅ 0 orphans |
| shipments.carrier_supplier_id → ref_suppliers | ✅ 0 orphans |
| production_batches.production_line_id → ref_production_lines | ✅ 0 orphans |
| quality_events.batch_id → production_batches | ✅ 0 orphans |
| inventory.warehouse_id → ref_warehouses | ✅ 0 orphans |
| inventory.item_id → ref_products | ✅ 0 orphans |
| ref_users.role_id → ref_roles | ✅ 0 orphans |
| ref_supplier_contracts.supplier_id → ref_suppliers | ✅ 0 orphans |
| purchase_orders.supplier_id → ref_suppliers | ✅ 0 orphans |
| maintenance_work_orders.asset_id → maintenance_assets | ✅ 0 orphans |
| energy_readings.production_line_id → ref_production_lines | ✅ 0 orphans |
| maintenance_assets.production_line_id → ref_production_lines | ✅ 0 orphans |
| ref_reorder_policies.item_id → ref_products | ✅ 0 orphans |
| ref_reorder_policies.warehouse_id → ref_warehouses | ✅ 0 orphans |
| ref_budgets.entity_id → ref_entities | ✅ 0 orphans |
| safety_events.entity_id → ref_entities | ✅ 0 orphans |
| carrier_events.shipment_id → shipments | ✅ 0 orphans |

### A.3 Data quality findings

#### Confirmed defects

| ID | Sheet | Issue | Severity | Resolution |
|----|-------|-------|----------|------------|
| DQ-01 | scenario_templates | Column `linked_reference_id` stores severity values (`HIGH`, `CRITICAL`, `MEDIUM`, `LOW`) in all 15 rows. This is the workbook's missing `severity` column; the column was mislabelled. `schema_core.sql` has a separate `severity` column. | **HIGH** | During import: rename `linked_reference_id` → `severity` and populate `linked_reference_id` with `NULL` for all rows (no genuine linked_reference_id data exists in this sheet). |
| DQ-02 | scenario_templates | `enabled` column is absent from the workbook but required `NOT NULL DEFAULT true` in `schema_core.sql`. | MEDIUM | During import: default all rows to `enabled = true`. |
| DQ-03 | goods_receipts | Only 2 rows. GRN-002 has `accepted_qty = 0` with `inspection_status = QUALITY_HOLD`. `accepted_qty < received_qty` is valid here (quality hold), but `accepted_qty = 0` when `received_qty = 1000` means 100% rejection. This is a deliberate scenario fixture, not an error. | INFO | Document as intentional scenario seed. |
| DQ-04 | purchase_orders | Only 3 rows. Sparse enough that FK checks may miss coverage edge cases at runtime. | LOW | Acceptable for Phase 1 seed; more POs generated by Phase 3 workflows. |
| DQ-05 | carrier_events | Only 2 rows for 120 shipments. | LOW | Acceptable — carrier events are generated at runtime. |

#### Potential issues (not confirmed defects)

| ID | Sheet | Observation |
|----|-------|-------------|
| DQ-P1 | production_batches | BATCH-7001 has `actual_output_qty_mt = 288` vs `planned = 2310` (12.5% yield). This is an extreme underperformance and likely a scenario-injection fixture for EQUIPMENT_FAILURE_RISK / QUALITY_HOLD scenarios. |
| DQ-P2 | inventory | All 150 rows have `stock_signal = NORMAL`. No `LOW_STOCK` or `CRITICAL` signals exist in the seed. Agents will need to compute signals dynamically against reorder policies. |
| DQ-P3 | orders | No `COMPLETED` or `CANCELLED` status — all 200 orders are `OPEN`/`IN_PROGRESS`/`AT_RISK`. Intentional for demo (everything is active and interesting). |
| DQ-P4 | shipments | No `DELIVERED` or `COMPLETED` status — all planned, in-transit or at-risk. Same reasoning as orders. |
| DQ-P5 | ref_users | 30 users assigned to 7 roles across 4 entities. No email/password fields — not a defect; RBAC is Phase 5. |

### A.4 Key enum values discovered

These must match SQL CHECK constraints exactly.

| Table | Column | Observed values |
|-------|--------|-----------------|
| orders | status | OPEN, IN_PROGRESS, AT_RISK |
| orders | priority | LOW, MEDIUM, HIGH, CRITICAL |
| shipments | status | PLANNED, IN_TRANSIT, AT_RISK |
| shipments | transport_mode | RAIL, ROAD_RAIL |
| production_batches | status | PLANNED, IN_PROGRESS, COMPLETED |
| quality_events | status | OPEN, IN_REVIEW, RELEASED |
| quality_events | severity | LOW, MEDIUM, HIGH, CRITICAL |
| maintenance_assets | health_status | NORMAL, WARNING, CRITICAL |
| maintenance_work_orders | status | OPEN, SCHEDULED, IN_PROGRESS, COMPLETED |
| safety_events | event_type | NEAR_MISS, UNSAFE_CONDITION, EQUIPMENT_GUARD_ALERT, PPE_NONCOMPLIANCE |
| safety_events | severity | HIGH (and by extension LOW/MEDIUM/CRITICAL must be allowed) |
| ref_suppliers | risk_band | LOW, MEDIUM, HIGH |
| ref_suppliers | status | ACTIVE |
| ref_production_lines | status | RUNNING (STOPPED, MAINTENANCE required for scenarios) |
| inventory | stock_signal | NORMAL (LOW_STOCK, CRITICAL, OUT_OF_STOCK required) |
| purchase_orders | status | DRAFT, APPROVED, IN_TRANSIT |
| scenario_templates | domain | Inventory, Procurement, Finance, Logistics, Quality, Maintenance, Energy, Safety |
| scenario_templates | scenario_type | 15 distinct types (see full list in section A.5) |

### A.5 Scenario types (15 templates)

1. INVENTORY_SHORTAGE
2. SUPPLIER_UNAVAILABLE
3. BUDGET_BREACH
4. DELIVERY_DELAY
5. QUALITY_HOLD
6. EQUIPMENT_FAILURE_RISK
7. SAFETY_NEAR_MISS
8. ENERGY_COST_SPIKE
9. RAW_MATERIAL_QUALITY
10. CAPACITY_CONFLICT
11. SPARE_PART_SHORTAGE
12. SUPPLIER_RECERTIFICATION
13. DATA_STALENESS
14. NORMAL_OPERATIONS
15. COMPOUND_EXCEPTION

### A.6 Schema discrepancy: workbook vs schema_core.sql

`schema_core.sql` defines only the 7 runtime tables (`scenario_templates`, `scenario_instances`, `agent_runs`, `decisions`, `action_queue`, `event_log`, `blockchain_anchors`) plus `scheduler_state`. It has **zero operational domain tables**. All 29 operational/reference sheets must produce new SQL tables.

`scenario_templates` in `schema_core.sql` has columns that differ from the workbook:

| schema_core.sql column | Workbook column | Resolution |
|---|---|---|
| scenario_template_id | scenario_template_id | match |
| scenario_type | scenario_type | match |
| domain | domain | match |
| description | description | match |
| **severity** | *absent* (mislabelled as `linked_reference_id`) | import: read col[4] as severity |
| **linked_reference_id** | linked_reference_id (stores severity) | import: set to NULL |
| base_record_id | base_record_id | match |
| injection_method | injection_method | match |
| agents_involved | agents_involved | match |
| expected_response | expected_response | match |
| guardrail | guardrail | match |
| **enabled** | *absent* | import: default TRUE |

---

## Part B — Design Decisions

### B.1 Migration tool: raw SQL scripts (not Alembic)

**Decision:** Use versioned raw SQL files (`backend/db/migrations/`) run by a simple Python runner script (`backend/db/apply_migrations.py`). Do not introduce Alembic.

**Rationale:** Alembic requires SQLAlchemy ORM models to be aligned with tables, and Phase 1 does not yet introduce SQLAlchemy (that is Phase 2). A lightweight runner keeps the dependency footprint minimal (only `psycopg2-binary`, which is already system-installed). The migration files are idempotent (`CREATE TABLE IF NOT EXISTS`, `INSERT ... ON CONFLICT DO NOTHING`) so they can be re-run safely.

### B.2 Single migration file for Phase 1

**Decision:** Two migration files: `001_operational_schema.sql` (all domain tables) and `002_runtime_schema.sql` (replaces/extends `schema_core.sql` content).

**Rationale:** Splitting operational from runtime keeps concerns separate and allows Phase 2 to add ORM on top of `001` without touching the runtime tables. `002` is essentially the `schema_core.sql` content with the `scenario_templates` column fix applied.

### B.3 Products and materials in one table

**Decision:** Keep `ref_products` as a single `products` table with a `product_category` column (`Finished Steel`, `Raw Material`, `Flux`, `Consumable`, `Utility`). Do not split into `products` + `materials`.

**Rationale:** The workbook uses one sheet with `product_id` values prefixed `PRD-` and `MAT-`. All 18 FK checks (`inventory.item_id`, `bom.input_item_id`, `bom.output_product_id`, `ref_reorder_policies.item_id`) point to this single table. Splitting would require a polymorphic FK pattern with no benefit at this stage.

### B.4 Customers are not a first-class table in Phase 1

**Decision:** `orders` table stores `customer_ref` as a plain `TEXT` column, not a FK to a `customers` table.

**Rationale:** The workbook has no `ref_customers` sheet. The `orders` sheet has `customer_ref` values like `CUST-036` with no corresponding reference table. Creating an empty placeholder table with no data would add FK complexity with no benefit. A `customers` table is added in Phase 2 when real customer data can be defined.

### B.5 `ref_products` maps to `products` (not `items` or `materials`)

The SQL table is named `products`. Column `product_id` is the PK. No rename needed.

### B.6 Timestamp conventions

All `timestamptz` columns. The workbook stores timestamps as ISO 8601 strings without timezone offset; during import these are interpreted as UTC and loaded with explicit `AT TIME ZONE 'UTC'` casting. This is documented in the import script.

### B.7 Monetary precision

`NUMERIC(18,2)` for all INR amounts. The workbook stores integer INR values; the extra decimal places handle any decimal values the scenario engine may produce.

### B.8 Import pipeline: Python script (not dbt, not pandas)

**Decision:** A single Python script `backend/data/load_seed_data.py` reads the workbook with `openpyxl`, applies all documented transformations, and inserts via `psycopg2` parameterised queries. No additional data-pipeline dependency.

**Rationale:** openpyxl is already installed. psycopg2 is already system-installed. This keeps Phase 1 to zero new dependencies beyond what already exists.

### B.9 `business_rules` loaded as a lookup table

The 10 rows in the `business_rules` sheet are loaded into a `business_rules` table. They are read-only reference data for the policy engine (Phase 5); loading them now completes the reference layer.

### B.10 `feed_health`, `simulation_config` as operational tables

`feed_health` maps to a `feed_health` table (4 rows). `simulation_config` maps to a `simulation_config` table (12 rows). These are needed by the scheduler (Phase 3) and are cheap to load now.

---

## Part C — PostgreSQL Schema Entity List

### C.1 Reference / master tables (Group 1)

| SQL table name | Source sheet | PK | Row count |
|---|---|---|---|
| `entities` | ref_entities | entity_id TEXT | 4 |
| `departments` | ref_departments | department_id TEXT | 11 |
| `products` | ref_products | product_id TEXT | 11 |
| `warehouses` | ref_warehouses | warehouse_id TEXT | 5 |
| `suppliers` | ref_suppliers | supplier_id TEXT | 8 |
| `supplier_offers` | ref_supplier_offers | offer_id TEXT | 6 |
| `roles` | ref_roles | role_id TEXT | 7 |
| `users` | ref_users | user_id TEXT | 30 |
| `production_lines` | ref_production_lines | production_line_id TEXT | 5 |
| `budgets` | ref_budgets | budget_id TEXT | 4 |
| `supplier_contracts` | ref_supplier_contracts | contract_id TEXT | 4 |
| `shifts` | ref_shifts | shift_id TEXT | 4 |

### C.2 Operational configuration tables (Group 2)

| SQL table name | Source sheet | PK | Row count |
|---|---|---|---|
| `reorder_policies` | ref_reorder_policies | policy_id TEXT | 55 |
| `bill_of_materials` | bill_of_materials | bom_line_id TEXT | 5 |
| `business_rules` | business_rules | rule_id TEXT | 10 |

### C.3 Operational transaction tables (Group 3)

| SQL table name | Source sheet | PK | Row count |
|---|---|---|---|
| `inventory` | inventory | inventory_id TEXT | 150 |
| `orders` | orders | order_id TEXT | 200 |
| `order_lines` | order_lines | order_line_id TEXT | 200 |
| `production_batches` | production_batches | batch_id TEXT | 60 |
| `shipments` | shipments | shipment_id TEXT | 120 |
| `purchase_orders` | purchase_orders | po_id TEXT | 3 |
| `goods_receipts` | goods_receipts | grn_id TEXT | 2 |
| `quality_events` | quality_events | quality_event_id TEXT | 40 |
| `maintenance_assets` | maintenance_assets | asset_id TEXT | 35 |
| `maintenance_work_orders` | maintenance_work_orders | work_order_id TEXT | 50 |
| `energy_readings` | energy_readings | reading_id TEXT | 240 |
| `safety_events` | safety_events | safety_event_id TEXT | 25 |
| `carrier_events` | carrier_events | carrier_event_id TEXT | 2 |
| `feed_health` | feed_health | feed_id TEXT | 4 |

### C.4 Runtime workflow tables (Group 4 — from schema_core.sql with DQ-01/02 fixes)

| SQL table name | Source | PK | Notes |
|---|---|---|---|
| `scenario_templates` | scenario_templates sheet + schema_core.sql | scenario_template_id TEXT | DQ-01 fix: split mislabelled linked_reference_id into severity + NULL linked_reference_id |
| `scenario_instances` | schema_core.sql (empty) | scenario_id UUID | Generated at runtime by scheduler |
| `agent_runs` | schema_core.sql (empty) | agent_run_id UUID | Populated by Phase 4 |
| `decisions` | schema_core.sql (empty) | decision_id UUID | Populated by Phase 4 |
| `action_queue` | schema_core.sql (empty) | action_id UUID | Populated by Phase 5 |
| `event_log` | schema_core.sql (empty) | event_id UUID | Populated by Phase 4+ |
| `blockchain_anchors` | schema_core.sql (empty) | anchor_id UUID | Populated by Phase 7 |
| `scheduler_state` | schema_core.sql (seed row) | scheduler_name TEXT | Pre-seeded with 300s interval |
| `simulation_config` | simulation_config sheet | config_key TEXT | 12 key-value config rows |

**Total tables: 32** (12 reference + 3 config + 14 transaction + 3 runtime seed-data + 6 runtime empty + scheduler_state + simulation_config)

---

## Part D — Column Mapping Decisions

### D.1 Transformations applied at import time

| Sheet | Workbook column | SQL column | Transformation |
|---|---|---|---|
| scenario_templates | `linked_reference_id` (col[4]) | `severity` | Rename: values HIGH/CRITICAL/MEDIUM/LOW map directly |
| scenario_templates | `linked_reference_id` (col[4]) | `linked_reference_id` | Set to NULL for all 15 rows (no real value present) |
| scenario_templates | *(absent)* | `enabled` | Default TRUE for all rows |
| All sheets with datetime strings | string timestamps | `TIMESTAMPTZ` | `datetime.fromisoformat(val).replace(tzinfo=timezone.utc)` |
| ref_supplier_contracts | `effective_from`, `effective_to` | `DATE` | `date.fromisoformat(val)` |
| ref_supplier_offers | `effective_from`, `effective_to` | `DATE` | `date.fromisoformat(val)` |
| All monetary columns `*_inr` | `INTEGER` | `NUMERIC(18,2)` | Direct cast; no precision loss since source is integer |
| ref_production_lines | `utilisation_pct` | `NUMERIC(5,4)` | Value is 0–1 fraction (e.g. 0.93); store as-is |
| maintenance_assets | `failure_risk_score` | `NUMERIC(5,4)` | Same — 0–1 fraction |

### D.2 Columns present in schema_core.sql but absent in workbook runtime sheets

The 6 empty runtime sheets (scenario_instances, agent_runs, decisions, action_queue, event_log, blockchain_anchors) exist only as column-name headers in the workbook. The actual SQL columns follow `schema_core.sql` exactly, which is the authoritative definition. Minor naming differences:

| Workbook column name | SQL column name | Note |
|---|---|---|
| `input_overlay_json` | `input_overlay` (JSONB) | Strip `_json` suffix; stored as JSONB |
| `output_json` | `output` (JSONB) | Strip suffix |
| `evidence_refs_json` | `evidence_refs` (JSONB) | Strip suffix |
| `policy_checks_json` | `policy_checks` (JSONB) | Strip suffix |
| `payload_json` | `payload` (JSONB) | Strip suffix |
| `result_json` | `result` (JSONB) | Strip suffix |
| `input_refs_json` | `input_refs` (JSONB) | Strip suffix |

The SQL definition takes precedence; the `_json` suffix in the workbook header is documentary.

---

## Part E — Numbered Implementation Steps

- [ ] 1. **Install Phase 1 Python dependencies and add `__init__.py` files**

  Add `psycopg2-binary==2.9.9` and `pytest==8.3.2` + `httpx==0.27.0` to `backend/requirements.txt` (uncomment psycopg2, add pytest/httpx). Create empty `__init__.py` in all 7 backend package directories (`app/`, `app/agents/`, `app/api/`, `app/db/`, `app/models/`, `app/orchestration/`, `app/services/`). Create `backend/data/__init__.py`.

  Files: `backend/requirements.txt`, 8× `__init__.py` files

  Verify: `python -c "import psycopg2; import pytest; print('ok')"` exits 0. `python -c "from app.main import app"` run from `backend/` exits 0.

- [ ] 2. **Create `.env` from `.env.example` and document DB connection variables**

  Copy `backend/.env.example` to `backend/.env` (not committed). Add `DATABASE_URL=postgresql://eas_user:eas_dev_pass@localhost:5432/eas_dev` and `TEST_DATABASE_URL=postgresql://eas_user:eas_dev_pass@localhost:5432/eas_test`. Ensure `.env` is in `.gitignore` (root `.gitignore` already exists from Phase 0.5).

  Files: `backend/.env` (not committed), `backend/.env.example` (update placeholders)

  Verify: `cat backend/.env.example` shows the new DB variable names. `backend/.env` is listed in `git status` as untracked/ignored.

- [ ] 3. **Create the migration runner script**

  Create `backend/db/apply_migrations.py`. The script:
  - reads `DATABASE_URL` from environment (via `python-dotenv` or direct `os.environ`)
  - scans `backend/db/migrations/` for `*.sql` files in alphabetical order
  - tracks applied migrations in a `_migrations` table (`migration_name TEXT PRIMARY KEY, applied_at TIMESTAMPTZ`)
  - skips already-applied files
  - prints each migration name before applying
  - exits non-zero on error

  Also create `backend/db/migrations/` directory with a `.gitkeep`.

  Files: `backend/db/apply_migrations.py`, `backend/db/migrations/.gitkeep`

  Verify: `python backend/db/apply_migrations.py --dry-run` (add a `--dry-run` flag that lists pending migrations without executing) exits 0 and prints "No database URL configured" or similar when `DATABASE_URL` is unset.

- [ ] 4. **Write migration 001: operational domain schema**

  Create `backend/db/migrations/001_operational_schema.sql`.

  Tables to create (all `IF NOT EXISTS`, all with `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()` and `updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()` where appropriate):

  **Group 1 — Reference:**
  - `entities(entity_id TEXT PK, entity_name TEXT NOT NULL, entity_type TEXT NOT NULL, country TEXT, status TEXT NOT NULL DEFAULT 'ACTIVE')`
  - `departments(department_id TEXT PK, department_name TEXT NOT NULL)`
  - `products(product_id TEXT PK, product_name TEXT NOT NULL, product_category TEXT NOT NULL, base_uom TEXT NOT NULL, reference_unit_cost_inr NUMERIC(18,2), status TEXT NOT NULL DEFAULT 'ACTIVE')`
  - `warehouses(warehouse_id TEXT PK, warehouse_name TEXT NOT NULL, entity_id TEXT NOT NULL REFERENCES entities, location_label TEXT, capacity_units NUMERIC(18,2), warehouse_type TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'ACTIVE')`
  - `suppliers(supplier_id TEXT PK, supplier_name TEXT NOT NULL, supplier_category TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'ACTIVE', risk_band TEXT NOT NULL DEFAULT 'LOW', historical_on_time_rate NUMERIC(5,4), default_lead_time_hours INTEGER)`
  - `supplier_offers(offer_id TEXT PK, supplier_id TEXT NOT NULL REFERENCES suppliers, item_id TEXT NOT NULL REFERENCES products, unit_price_inr NUMERIC(18,2) NOT NULL, price_uom TEXT NOT NULL, lead_time_hours INTEGER, max_available_qty NUMERIC(18,2), on_time_rate NUMERIC(5,4), effective_from DATE, effective_to DATE, offer_status TEXT NOT NULL DEFAULT 'ACTIVE')`
  - `roles(role_id TEXT PK, role_name TEXT NOT NULL, permissions_summary TEXT)`
  - `users(user_id TEXT PK, display_name TEXT NOT NULL, role_id TEXT NOT NULL REFERENCES roles, entity_id TEXT NOT NULL REFERENCES entities, status TEXT NOT NULL DEFAULT 'ACTIVE')`
  - `production_lines(production_line_id TEXT PK, line_name TEXT NOT NULL, entity_id TEXT NOT NULL REFERENCES entities, process_stage TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'RUNNING', utilisation_pct NUMERIC(5,4), daily_capacity_mt NUMERIC(18,2))`
  - `budgets(budget_id TEXT PK, entity_id TEXT NOT NULL REFERENCES entities, cost_center TEXT NOT NULL, period TEXT NOT NULL, currency TEXT NOT NULL DEFAULT 'INR', approved_limit_inr NUMERIC(18,2) NOT NULL, committed_spend_inr NUMERIC(18,2) NOT NULL DEFAULT 0, available_budget_inr NUMERIC(18,2) NOT NULL, single_action_approval_threshold_inr NUMERIC(18,2), status TEXT NOT NULL DEFAULT 'ACTIVE')`
  - `supplier_contracts(contract_id TEXT PK, supplier_id TEXT NOT NULL REFERENCES suppliers, contract_category TEXT NOT NULL, effective_from DATE, effective_to DATE, contract_limit_inr NUMERIC(18,2), currency TEXT NOT NULL DEFAULT 'INR', status TEXT NOT NULL DEFAULT 'ACTIVE', owner_department TEXT)`
  - `shifts(shift_id TEXT PK, entity_id TEXT NOT NULL REFERENCES entities, start_local TEXT NOT NULL, end_local TEXT NOT NULL, duration_hours INTEGER, status TEXT NOT NULL DEFAULT 'ACTIVE')`

  **Group 2 — Operational config:**
  - `reorder_policies(policy_id TEXT PK, item_id TEXT NOT NULL REFERENCES products, warehouse_id TEXT NOT NULL REFERENCES warehouses, reorder_point_qty NUMERIC(18,2) NOT NULL, safety_stock_qty NUMERIC(18,2) NOT NULL, target_stock_qty NUMERIC(18,2), status TEXT NOT NULL DEFAULT 'ACTIVE', UNIQUE(item_id, warehouse_id))`
  - `bill_of_materials(bom_line_id TEXT PK, output_product_id TEXT NOT NULL REFERENCES products, input_item_id TEXT NOT NULL REFERENCES products, quantity_per_output_unit NUMERIC(10,4) NOT NULL, consumption_uom TEXT NOT NULL, version_status TEXT NOT NULL DEFAULT 'STANDARD')`
  - `business_rules(rule_id TEXT PK, domain TEXT NOT NULL, condition_expression TEXT NOT NULL, failure_action TEXT NOT NULL, severity TEXT NOT NULL, automation_mode TEXT NOT NULL, enabled BOOLEAN NOT NULL DEFAULT TRUE)`

  **Group 3 — Transactions:**
  - `inventory(inventory_id TEXT PK, item_id TEXT NOT NULL REFERENCES products, warehouse_id TEXT NOT NULL REFERENCES warehouses, on_hand_qty NUMERIC(18,2) NOT NULL DEFAULT 0, reserved_qty NUMERIC(18,2) NOT NULL DEFAULT 0, available_qty NUMERIC(18,2) NOT NULL DEFAULT 0, uom TEXT NOT NULL, as_of_timestamp TIMESTAMPTZ, stock_signal TEXT NOT NULL DEFAULT 'NORMAL', updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW())`
  - `orders(order_id TEXT PK, customer_ref TEXT NOT NULL, entity_id TEXT NOT NULL REFERENCES entities, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), required_delivery_at TIMESTAMPTZ, status TEXT NOT NULL DEFAULT 'OPEN', priority TEXT NOT NULL DEFAULT 'MEDIUM', currency TEXT NOT NULL DEFAULT 'INR', external_reference TEXT, CHECK(status IN ('OPEN','IN_PROGRESS','AT_RISK','COMPLETED','CANCELLED')))`
  - `order_lines(order_line_id TEXT PK, order_id TEXT NOT NULL REFERENCES orders, product_id TEXT NOT NULL REFERENCES products, requested_qty NUMERIC(18,2) NOT NULL, unit_price_inr NUMERIC(18,2), uom TEXT NOT NULL)`
  - `production_batches(batch_id TEXT PK, production_line_id TEXT NOT NULL REFERENCES production_lines, output_product_id TEXT NOT NULL REFERENCES products, planned_output_qty_mt NUMERIC(18,2), actual_output_qty_mt NUMERIC(18,2), planned_start TIMESTAMPTZ, planned_end TIMESTAMPTZ, status TEXT NOT NULL DEFAULT 'PLANNED', risk_flag TEXT NOT NULL DEFAULT 'NORMAL', CHECK(status IN ('PLANNED','IN_PROGRESS','COMPLETED','CANCELLED')))`
  - `shipments(shipment_id TEXT PK, order_id TEXT NOT NULL REFERENCES orders, origin_warehouse_id TEXT REFERENCES warehouses, destination_warehouse_id TEXT REFERENCES warehouses, carrier_supplier_id TEXT REFERENCES suppliers, planned_dispatch_at TIMESTAMPTZ, estimated_arrival_at TIMESTAMPTZ, status TEXT NOT NULL DEFAULT 'PLANNED', transport_mode TEXT, risk_flag TEXT NOT NULL DEFAULT 'NORMAL', CHECK(status IN ('PLANNED','IN_TRANSIT','AT_RISK','DELIVERED','CANCELLED')))`
  - `purchase_orders(po_id TEXT PK, supplier_id TEXT NOT NULL REFERENCES suppliers, item_id TEXT NOT NULL REFERENCES products, quantity NUMERIC(18,2) NOT NULL, unit_cost_inr NUMERIC(18,2) NOT NULL, total_cost_inr NUMERIC(18,2), currency TEXT NOT NULL DEFAULT 'INR', created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), status TEXT NOT NULL DEFAULT 'DRAFT', budget_id TEXT REFERENCES budgets, CHECK(status IN ('DRAFT','APPROVED','IN_TRANSIT','RECEIVED','CANCELLED')))`
  - `goods_receipts(grn_id TEXT PK, po_id TEXT NOT NULL REFERENCES purchase_orders, supplier_id TEXT NOT NULL REFERENCES suppliers, item_id TEXT NOT NULL REFERENCES products, received_qty NUMERIC(18,2) NOT NULL, accepted_qty NUMERIC(18,2) NOT NULL DEFAULT 0, received_at TIMESTAMPTZ, inspection_status TEXT NOT NULL DEFAULT 'PENDING', quality_certificate_ref TEXT)`
  - `quality_events(quality_event_id TEXT PK, batch_id TEXT NOT NULL REFERENCES production_batches, product_id TEXT NOT NULL REFERENCES products, detected_at TIMESTAMPTZ, defect_code TEXT NOT NULL, severity TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'OPEN', recommended_control TEXT, CHECK(status IN ('OPEN','IN_REVIEW','RELEASED','REJECTED')))`
  - `maintenance_assets(asset_id TEXT PK, production_line_id TEXT NOT NULL REFERENCES production_lines, asset_name TEXT NOT NULL, last_signal_at TIMESTAMPTZ, failure_risk_score NUMERIC(5,4), health_status TEXT NOT NULL DEFAULT 'NORMAL', next_maintenance_due TIMESTAMPTZ, recommended_action TEXT, CHECK(health_status IN ('NORMAL','WARNING','CRITICAL')))`
  - `maintenance_work_orders(work_order_id TEXT PK, asset_id TEXT NOT NULL REFERENCES maintenance_assets, work_type TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'OPEN', created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), scheduled_for TIMESTAMPTZ, priority TEXT NOT NULL DEFAULT 'MEDIUM', assigned_team_or_vendor TEXT, CHECK(status IN ('OPEN','SCHEDULED','IN_PROGRESS','COMPLETED','CANCELLED')))`
  - `energy_readings(reading_id TEXT PK, entity_id TEXT NOT NULL REFERENCES entities, production_line_id TEXT NOT NULL REFERENCES production_lines, reading_at TIMESTAMPTZ NOT NULL, energy_kwh NUMERIC(18,2) NOT NULL, unit_rate_inr NUMERIC(10,4), signal TEXT NOT NULL DEFAULT 'NORMAL', currency TEXT NOT NULL DEFAULT 'INR')`
  - `safety_events(safety_event_id TEXT PK, entity_id TEXT NOT NULL REFERENCES entities, occurred_at TIMESTAMPTZ NOT NULL, event_type TEXT NOT NULL, severity TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'OPEN', description TEXT)`
  - `carrier_events(carrier_event_id TEXT PK, shipment_id TEXT NOT NULL REFERENCES shipments, event_timestamp TIMESTAMPTZ NOT NULL, event_type TEXT NOT NULL, description TEXT, source_supplier_id TEXT REFERENCES suppliers)`
  - `feed_health(feed_id TEXT PK, source_name TEXT NOT NULL, last_success_at TIMESTAMPTZ, consecutive_failures INTEGER NOT NULL DEFAULT 0, health_status TEXT NOT NULL DEFAULT 'HEALTHY', max_age_seconds INTEGER, updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW())`

  **Indexes** (on every meaningful FK and common query column):
  ```sql
  CREATE INDEX IF NOT EXISTS idx_inventory_item ON inventory(item_id);
  CREATE INDEX IF NOT EXISTS idx_inventory_warehouse ON inventory(warehouse_id);
  CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status, created_at);
  CREATE INDEX IF NOT EXISTS idx_order_lines_order ON order_lines(order_id);
  CREATE INDEX IF NOT EXISTS idx_order_lines_product ON order_lines(product_id);
  CREATE INDEX IF NOT EXISTS idx_shipments_order ON shipments(order_id);
  CREATE INDEX IF NOT EXISTS idx_shipments_status ON shipments(status);
  CREATE INDEX IF NOT EXISTS idx_production_batches_line ON production_batches(production_line_id);
  CREATE INDEX IF NOT EXISTS idx_production_batches_status ON production_batches(status);
  CREATE INDEX IF NOT EXISTS idx_quality_events_batch ON quality_events(batch_id);
  CREATE INDEX IF NOT EXISTS idx_maintenance_assets_line ON maintenance_assets(production_line_id);
  CREATE INDEX IF NOT EXISTS idx_maintenance_wo_asset ON maintenance_work_orders(asset_id);
  CREATE INDEX IF NOT EXISTS idx_energy_readings_line_time ON energy_readings(production_line_id, reading_at);
  CREATE INDEX IF NOT EXISTS idx_safety_events_entity ON safety_events(entity_id, occurred_at);
  CREATE INDEX IF NOT EXISTS idx_purchase_orders_supplier ON purchase_orders(supplier_id);
  ```

  Files: `backend/db/migrations/001_operational_schema.sql`

  Verify: Apply to a local PostgreSQL instance (`python backend/db/apply_migrations.py`). `psql -c "\dt"` lists all 26 new tables. Zero errors.

- [ ] 5. **Write migration 002: runtime workflow schema**

  Create `backend/db/migrations/002_runtime_schema.sql`. This is `schema_core.sql` content with the DQ-01/DQ-02 fixes applied:

  - `scenario_templates` column definition: add `severity TEXT NOT NULL` and `enabled BOOLEAN NOT NULL DEFAULT TRUE`; `linked_reference_id` stays as-is (nullable TEXT)
  - `simulation_config(config_key TEXT PK, config_value TEXT NOT NULL, description TEXT)` — new table for the 12 config rows
  - All other tables from `schema_core.sql` transcribed verbatim with `IF NOT EXISTS` added where missing.
  - Seed row for `scheduler_state` via `INSERT ... ON CONFLICT DO NOTHING`.

  Files: `backend/db/migrations/002_runtime_schema.sql`

  Verify: Same apply run as step 4. `psql -c "\dt"` shows `scenario_templates`, `scenario_instances`, `agent_runs`, `decisions`, `action_queue`, `event_log`, `blockchain_anchors`, `scheduler_state`, `simulation_config`. Zero errors.

- [ ] 6. **Write the seed data loader**

  Create `backend/data/load_seed_data.py`. The script:

  1. Opens the workbook read-only via openpyxl.
  2. Loads each sheet in dependency order (reference → config → transactions → runtime-seed).
  3. Applies all documented transformations (DQ-01 severity rename, DQ-02 enabled default, timestamp UTC casting, NUMERIC casting).
  4. Inserts via `psycopg2` using `executemany` with parameterised queries (`INSERT ... ON CONFLICT (pk) DO NOTHING` for idempotency).
  5. Logs row counts inserted vs skipped per table.
  6. Commits once per load group (not per row).
  7. Exits non-zero on psycopg2 errors; prints the failing row for debugging.

  Load order:
  ```
  Group 1:  entities, departments, products, warehouses, suppliers,
            roles, users, production_lines, budgets, supplier_contracts,
            shifts, supplier_offers
  Group 2:  reorder_policies, bill_of_materials, business_rules
  Group 3:  inventory, orders, order_lines, production_batches,
            shipments, purchase_orders, goods_receipts, quality_events,
            maintenance_assets, maintenance_work_orders, energy_readings,
            safety_events, carrier_events, feed_health
  Group 4:  scenario_templates (with DQ-01/02 transforms), simulation_config
  ```

  Note: the 6 empty runtime sheets (scenario_instances, agent_runs, etc.) are skipped — they have 0 data rows.

  Files: `backend/data/load_seed_data.py`

  Verify: `python backend/data/load_seed_data.py` with a configured `DATABASE_URL` completes with exit 0. Running it a second time produces "0 inserted, N skipped" for every table (idempotency). Final row counts match workbook: entities=4, departments=11, products=11, warehouses=5, suppliers=8, supplier_offers=6, roles=7, users=30, production_lines=5, budgets=4, supplier_contracts=4, shifts=4, reorder_policies=55, bom=5, business_rules=10, inventory=150, orders=200, order_lines=200, production_batches=60, shipments=120, purchase_orders=3, goods_receipts=2, quality_events=40, maintenance_assets=35, maintenance_work_orders=50, energy_readings=240, safety_events=25, carrier_events=2, feed_health=4, scenario_templates=15, simulation_config=12.

- [ ] 7. **Write the machine-readable data validation report**

  Create `backend/data/validate_seed_data.py`. The script:

  1. Connects to the database (reads `DATABASE_URL` from env).
  2. Checks row counts per table match expected counts.
  3. Checks FK integrity: runs `SELECT COUNT(*) FROM child WHERE fk_col NOT IN (SELECT pk FROM parent)` for each FK relationship listed in section A.2.
  4. Checks enum values: runs `SELECT DISTINCT status FROM orders` etc. and verifies all values are in the expected set.
  5. Checks: no negative `on_hand_qty`, `reserved_qty`, or `available_qty` in inventory.
  6. Checks: `available_qty = on_hand_qty - reserved_qty` for every inventory row (arithmetic consistency).
  7. Checks: `total_cost_inr = quantity * unit_cost_inr` for purchase_orders (within 1 INR rounding tolerance).
  8. Outputs a JSON report to `backend/data/validation_report.json` with structure:
     ```json
     {
       "run_at": "...",
       "pass": true/false,
       "checks": [
         { "check_id": "ROW_COUNT_entities", "status": "PASS", "expected": 4, "actual": 4 },
         ...
       ]
     }
     ```
  9. Prints human-readable summary to stdout.
  10. Exits 0 if all checks pass, 1 if any check fails.

  Files: `backend/data/validate_seed_data.py`, `backend/data/validation_report.json` (generated)

  Verify: `python backend/data/validate_seed_data.py` exits 0 with `"pass": true` when seed data is loaded. `"pass": false` when run against an empty database.

- [ ] 8. **Write the Phase 1 data audit document**

  Create `PHASE_1_DATA_AUDIT.md` in the repository root. It must document:
  - All 40 sheet names with row counts (table from A.1 above)
  - Full FK validation results (table from A.2)
  - Data quality findings (tables from A.3 and A.4)
  - Enum values per table (A.4)
  - Scenario types (A.5)
  - Schema discrepancy resolution (A.6)
  - All transformations applied (D.1, D.2)
  - Final table list (C.1–C.4)
  - Commands to reproduce the inspection: `python backend/data/inspect_workbook.py`
  - Commands to apply schema and load seed: see step 10

  Files: `PHASE_1_DATA_AUDIT.md`

  Verify: File exists, is non-empty, references actual data found by the inspection script.

- [ ] 9. **Write pytest test suite**

  Create `backend/tests/` directory with `__init__.py`. Write the following test files:

  **`backend/tests/test_migrations.py`** — Tests that the migration runner works in isolation:
  - Test: `_migrations` table is created on first run.
  - Test: running migrations twice does not raise errors (idempotency).
  - Test: `apply_migrations.py --dry-run` lists pending migrations without executing.

  **`backend/tests/test_seed_data.py`** — Tests row counts and FK integrity after loading seed:
  - For each of the 31 populated tables: assert `SELECT COUNT(*) FROM table` equals expected count.
  - Assert all FK checks return 0 orphan rows.

  **`backend/tests/test_validation_report.py`** — Tests the validation script output:
  - Assert the JSON output file is valid JSON.
  - Assert `pass = true` after a clean load.
  - Assert the `checks` array contains at least one entry per FK relationship.

  **`backend/tests/test_schema_constraints.py`** — Tests SQL CHECK constraints:
  - Assert inserting `status='INVALID_STATUS'` into orders raises `psycopg2.errors.CheckViolation`.
  - Assert inserting a shipment with a non-existent `order_id` raises `ForeignKeyViolation`.
  - Assert inserting inventory with `available_qty` that is negative does NOT raise an error (no CHECK constraint on this — the CHECK is a business validation, not a DB constraint). This documents the deliberate choice.

  All tests use a `TEST_DATABASE_URL` fixture (separate test database). Tests requiring a live DB are marked `@pytest.mark.integration` and skipped by default with `pytest -m "not integration"`.

  Files: `backend/tests/__init__.py`, `backend/tests/conftest.py`, `backend/tests/test_migrations.py`, `backend/tests/test_seed_data.py`, `backend/tests/test_validation_report.py`, `backend/tests/test_schema_constraints.py`

  Verify: `python -m pytest backend/tests/ -m "not integration" -v` exits 0 (unit tests only). `python -m pytest backend/tests/ -m integration -v` with `TEST_DATABASE_URL` set runs all tests and exits 0.

- [ ] 10. **Update schema_notes.md and backend README**

  Replace the outdated 4-table sketch in `backend/app/db/schema_notes.md` with a pointer to the new migration files and the audit document. Update `backend/README.md` with the Phase 1 setup commands:

  ```bash
  # Setup Phase 1 database (requires PostgreSQL running locally)
  export DATABASE_URL=postgresql://eas_user:eas_dev_pass@localhost:5432/eas_dev

  # Apply schema migrations
  python backend/db/apply_migrations.py

  # Load seed data
  python backend/data/load_seed_data.py

  # Validate seed data
  python backend/data/validate_seed_data.py

  # Run tests (unit only, no DB required)
  python -m pytest backend/tests/ -m "not integration" -v

  # Run integration tests (requires TEST_DATABASE_URL)
  export TEST_DATABASE_URL=postgresql://eas_user:eas_dev_pass@localhost:5432/eas_test
  python -m pytest backend/tests/ -m integration -v
  ```

  Files: `backend/app/db/schema_notes.md`, `backend/README.md`

  Verify: File contents are updated. `python -m pytest backend/tests/ -m "not integration"` still exits 0.

- [ ] 11. **Update ANTIGRAVITY_PROJECT_REFERENCE.md phase status**

  In the status checklist table, change Phase 1 from "Starter workbook/schema prepared separately; repository integration unverified" to "In progress — schema defined, seed loaded, validation passing". Add a development log entry recording what was done, commands run, and acceptance criteria met/unmet.

  Files: `ANTIGRAVITY_PROJECT_REFERENCE.md`

  Verify: File is updated. `git diff --stat` shows only the status entry changed.

- [ ] 12. **Git checkpoint commit**

  Stage and commit all Phase 1 files:
  - `backend/requirements.txt`
  - `backend/db/apply_migrations.py`
  - `backend/db/migrations/001_operational_schema.sql`
  - `backend/db/migrations/002_runtime_schema.sql`
  - `backend/data/inspect_workbook.py` (already created in this step)
  - `backend/data/load_seed_data.py`
  - `backend/data/validate_seed_data.py`
  - `backend/data/workbook_inspection.json`
  - `backend/tests/__init__.py`
  - `backend/tests/conftest.py`
  - `backend/tests/test_migrations.py`
  - `backend/tests/test_seed_data.py`
  - `backend/tests/test_validation_report.py`
  - `backend/tests/test_schema_constraints.py`
  - `PHASE_1_DATA_AUDIT.md`
  - `ANTIGRAVITY_PROJECT_REFERENCE.md`
  - `backend/app/db/schema_notes.md`
  - `backend/README.md`
  - All `__init__.py` files

  Do NOT commit: `backend/.env`, `backend/data/validation_report.json` (generated artefact — add to `.gitignore`).

  Commit message: `feat(phase1): operational schema, seed loader, validation, and data audit`

  Verify: `git log --oneline -1` shows the new commit. `git status` shows clean working tree. `git show --stat HEAD` lists all expected files.

---

## Part F — Ambiguous Decisions and Resolutions

| # | Ambiguity | Resolution |
|---|-----------|------------|
| F-1 | `scenario_templates.linked_reference_id` in the workbook stores severity values. Should the import re-use the misnamed column or rename it? | **Rename to `severity` during import.** `linked_reference_id` stays in the schema (matches `schema_core.sql`) but is set to NULL for all 15 seed rows. This is the least-surprise approach and aligns with the SQL schema. |
| F-2 | Should `customers` be a FK table or a `TEXT` field? | **TEXT field for Phase 1.** No ref_customers sheet exists. A `customers` table is deferred to Phase 2 when real customer records are defined. A TODO comment is added to the `orders` table definition. |
| F-3 | `available_qty = on_hand_qty - reserved_qty` in the inventory — should this be a generated column or a CHECK constraint? | **No DB constraint for Phase 1.** The relationship is validated in `validate_seed_data.py`. Adding a `GENERATED ALWAYS AS` column requires PostgreSQL 12+ and complicates the import (cannot insert the column). The validation script catches mismatches; a DB constraint can be added in Phase 2 when the ORM layer manages inserts. |
| F-4 | Should `utilisation_pct` and `failure_risk_score` (0–1 fractions) have a CHECK `value BETWEEN 0 AND 1`? | **Yes — add CHECK constraints.** These are well-bounded physical quantities. The constraint is `CHECK (utilisation_pct BETWEEN 0 AND 1)` and `CHECK (failure_risk_score BETWEEN 0 AND 1)`. |
| F-5 | `data_dictionary` and `column_dictionary` sheets — import or skip? | **Skip.** They are documentation artefacts, not operational data. Their content is superseded by the SQL schema comments and this audit document. |
| F-6 | `ref_supplier_offers.lead_time_hours = 1800` (75 days for iron ore) — is this a data error? | **Not an error.** 1800 hours = 75 days for bulk iron ore ocean freight from overseas supplier is plausible. Document as unusual-but-valid in the audit. No correction applied. |
| F-7 | `orders` has only 3 statuses (OPEN, IN_PROGRESS, AT_RISK). Should the CHECK constraint be strict or allow more? | **Allow more in the CHECK.** Add COMPLETED and CANCELLED to the constraint so Phase 3/4 workflows can complete/cancel orders without a migration. The seed data only uses 3 values. |
| F-8 | Should `schema_core.sql` in `project_reference/` be kept, replaced, or superseded? | **Keep as-is; supersede.** The authoritative schema for Phase 1 is the new migration files. `schema_core.sql` is preserved unchanged as the original starter reference (per guardrail 11). A comment at the top of `002_runtime_schema.sql` notes it supersedes `schema_core.sql`. |

---

## Part G — Test Strategy Summary

| Test file | What it covers | Requires DB |
|---|---|---|
| `test_migrations.py` | Migration runner idempotency, dry-run mode, `_migrations` table creation | Integration only |
| `test_seed_data.py` | Row counts match workbook; all 18 FK relationships return 0 orphans | Integration only |
| `test_validation_report.py` | JSON output is valid; `pass=true` after clean load | Integration only |
| `test_schema_constraints.py` | CHECK violations raise correct psycopg2 errors; FK violations raise ForeignKeyViolation | Integration only |

All integration tests use a separate `TEST_DATABASE_URL` and are isolated behind `@pytest.mark.integration`. Running `pytest -m "not integration"` exercises import-level checks only (imports of migration runner, loader, validator modules).

---

## Part H — Documentation Strategy

| Document | Action |
|---|---|
| `PHASE_1_DATA_AUDIT.md` | **Create new** — primary human-readable audit output |
| `backend/data/workbook_inspection.json` | **Already created** — machine-readable inspection results |
| `backend/data/validation_report.json` | **Generated by script** — machine-readable validation results |
| `backend/app/db/schema_notes.md` | **Replace** — outdated 4-table sketch → pointer to migration files |
| `backend/README.md` | **Update** — add Phase 1 setup commands |
| `ANTIGRAVITY_PROJECT_REFERENCE.md` | **Update status** — phase 1 in-progress; dev log entry |
| `project_reference/schema_core.sql` | **Leave untouched** — original starter, preserved per guardrail 11 |

---

## Part I — Git Commit Plan

| Commit | Content | Message |
|---|---|---|
| 1 (this phase) | All Phase 1 files listed in step 12 | `feat(phase1): operational schema, seed loader, validation, and data audit` |

Single commit for Phase 1 to keep the checkpoint atomic. The commit should pass `python -c "from app.main import app"` and `python -m pytest backend/tests/ -m "not integration"` from `backend/`.
