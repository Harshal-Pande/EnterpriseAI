# Phase 1 data dictionary

Source workbook: `project_reference/enterprise_ai_industrial_dataset_v2.xlsx`  
Mappings: `backend/data/column_mappings.py`  
SQL: `backend/db/migrations/001_operational_schema.sql`, `002_runtime_schema.sql`

Units: quantities in source UOM (`MT`, `EA`, etc.); monetary amounts in INR stored as `NUMERIC(18,2)`; utilisation, on-time rate, and failure risk as 0–1 fractions (`NUMERIC(5,4)`); timestamps stored as `TIMESTAMPTZ` interpreted as UTC.

## Count reconciliation

| Total | Meaning |
|---|---|
| **1,677** | Every data row in all **40** workbook sheets, including metadata and empty runtime templates (0 extra rows). |
| **1,327** | Rows in the **31 mapped import sheets**. |
| **350** | Excluded metadata: README (8) + data_dictionary (37) + column_dictionary (305). |
| **0** | Six runtime workbook sheets (`scenario_instances`, `agent_runs`, `decisions`, `action_queue`, `event_log`, `blockchain_anchors`) — headers only. |

`1677 = 1327 + 350 + 0`. These totals are not interchangeable.

## Imported tables

| Table | Source sheet | PK | Rows | Notes |
|---|---|---|---|---|
| entities | ref_entities | entity_id | 4 | Root org units |
| departments | ref_departments | department_id | 11 | No inbound FKs in seed |
| products | ref_products | product_id | 11 | PRD- and MAT- in one table |
| warehouses | ref_warehouses | warehouse_id | 5 | FK entity_id |
| suppliers | ref_suppliers | supplier_id | 8 | |
| supplier_offers | ref_supplier_offers | offer_id | 6 | FK supplier, product |
| roles | ref_roles | role_id | 7 | |
| users | ref_users | user_id | 30 | FK role, entity; no passwords |
| production_lines | ref_production_lines | production_line_id | 5 | utilisation_pct 0–1 |
| budgets | ref_budgets | budget_id | 4 | available = approved − committed |
| supplier_contracts | ref_supplier_contracts | contract_id | 4 | owner_department is a label, not department_id |
| shifts | ref_shifts | shift_id | 4 | start_local/end_local are HH:MM TEXT |
| reorder_policies | ref_reorder_policies | policy_id | 55 | UNIQUE(item_id, warehouse_id) |
| bill_of_materials | bill_of_materials | bom_line_id | 5 | |
| business_rules | business_rules | rule_id | 10 | enabled coerced from string |
| inventory | inventory | inventory_id | 150 | available = on_hand − reserved (validated, not a DB CHECK) |
| orders | orders | order_id | 200 | customer_ref TEXT (no customers table) |
| order_lines | order_lines | order_line_id | 200 | |
| production_batches | production_batches | batch_id | 60 | |
| shipments | shipments | shipment_id | 120 | |
| purchase_orders | purchase_orders | po_id | 3 | total = qty × unit cost |
| goods_receipts | goods_receipts | grn_id | 2 | GRN-002 100% quality hold is intentional |
| quality_events | quality_events | quality_event_id | 40 | |
| maintenance_assets | maintenance_assets | asset_id | 35 | failure_risk_score 0–1 |
| maintenance_work_orders | maintenance_work_orders | work_order_id | 50 | |
| energy_readings | energy_readings | reading_id | 240 | signal includes HIGH_USAGE |
| safety_events | safety_events | safety_event_id | 25 | |
| carrier_events | carrier_events | carrier_event_id | 2 | Sparse by design |
| feed_health | feed_health | feed_id | 4 | |
| scenario_templates | scenario_templates | scenario_template_id | 15 | DQ-01/02 transforms |
| simulation_config | simulation_config | config_key | 12 | |

## Runtime tables (schema only in Phase 1)

scenario_instances, agent_runs, agent_findings, decisions, action_queue, policy_evaluations, approval_requests, action_execution_results, event_log, blockchain_anchors, scheduler_state (one SQL seed row).

Workbook JSON headers such as `input_overlay_json` map to JSONB columns without the `_json` suffix (`schema_core.sql` is authoritative for those names).

## Transformations

| Source | Destination | Rule |
|---|---|---|
| scenario_templates.linked_reference_id | severity | **DQ-01:** the column exists in the workbook but stores severity tokens (HIGH/CRITICAL/MEDIUM/LOW), not a foreign key. Values are copied to `severity`. |
| (same column) | linked_reference_id | Set NULL for all 15 rows. No genuine linked-reference IDs exist; nothing is invented. |
| enabled (column absent) | enabled | **DQ-02:** workbook has no `enabled` column. Import defaults TRUE. |
| ISO timestamps without offset | TIMESTAMPTZ | Treated as UTC |
| `*_inr` integers | NUMERIC(18,2) | Direct cast |
| business_rules.enabled | BOOLEAN | `"true"`/`"false"` strings |

## Deliberate exclusions

- No `customers` table (no sheet).
- No separate `materials` table.
- Metadata sheets not imported.
- Empty runtime sheets not treated as business records.
