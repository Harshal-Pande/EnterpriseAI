-- Phase 1 operational / domain schema.
-- Derived from project_reference/enterprise_ai_industrial_dataset_v2.xlsx
-- and backend/data/column_mappings.py. Does not invent unsupported entities.
--
-- Deliberate exclusions:
--   * customers table — no ref_customers sheet; orders.customer_ref is TEXT.
--   * materials table — PRD- and MAT- rows share products.
--   * departments.owner FK from supplier_contracts.owner_department — values
--     are labels (PROCUREMENT/LOGISTICS/MAINTENANCE), not department_id.
--   * README, data_dictionary, column_dictionary — documentation only.

CREATE TABLE IF NOT EXISTS entities (
  entity_id TEXT PRIMARY KEY,
  entity_name TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  country TEXT,
  status TEXT NOT NULL DEFAULT 'ACTIVE',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (status IN ('ACTIVE', 'INACTIVE'))
);

CREATE TABLE IF NOT EXISTS departments (
  department_id TEXT PRIMARY KEY,
  department_name TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS products (
  product_id TEXT PRIMARY KEY,
  product_name TEXT NOT NULL,
  product_category TEXT NOT NULL,
  base_uom TEXT NOT NULL,
  reference_unit_cost_inr NUMERIC(18, 2),
  status TEXT NOT NULL DEFAULT 'ACTIVE',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (status IN ('ACTIVE', 'INACTIVE', 'OBSOLETE'))
);

CREATE TABLE IF NOT EXISTS roles (
  role_id TEXT PRIMARY KEY,
  role_name TEXT NOT NULL,
  permissions_summary TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS suppliers (
  supplier_id TEXT PRIMARY KEY,
  supplier_name TEXT NOT NULL,
  supplier_category TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'ACTIVE',
  risk_band TEXT NOT NULL DEFAULT 'LOW',
  historical_on_time_rate NUMERIC(5, 4),
  default_lead_time_hours INTEGER,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (status IN ('ACTIVE', 'INACTIVE', 'SUSPENDED')),
  CHECK (risk_band IN ('LOW', 'MEDIUM', 'HIGH')),
  CHECK (historical_on_time_rate IS NULL OR historical_on_time_rate BETWEEN 0 AND 1)
);

CREATE TABLE IF NOT EXISTS warehouses (
  warehouse_id TEXT PRIMARY KEY,
  warehouse_name TEXT NOT NULL,
  entity_id TEXT NOT NULL REFERENCES entities (entity_id),
  location_label TEXT,
  capacity_units NUMERIC(18, 2),
  warehouse_type TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'ACTIVE',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (status IN ('ACTIVE', 'INACTIVE', 'MAINTENANCE'))
);

CREATE TABLE IF NOT EXISTS users (
  user_id TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  role_id TEXT NOT NULL REFERENCES roles (role_id),
  entity_id TEXT NOT NULL REFERENCES entities (entity_id),
  status TEXT NOT NULL DEFAULT 'ACTIVE',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (status IN ('ACTIVE', 'INACTIVE', 'SUSPENDED'))
);

CREATE TABLE IF NOT EXISTS production_lines (
  production_line_id TEXT PRIMARY KEY,
  line_name TEXT NOT NULL,
  entity_id TEXT NOT NULL REFERENCES entities (entity_id),
  process_stage TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'RUNNING',
  utilisation_pct NUMERIC(5, 4),
  daily_capacity_mt NUMERIC(18, 2),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (status IN ('RUNNING', 'STOPPED', 'MAINTENANCE', 'IDLE')),
  CHECK (utilisation_pct IS NULL OR utilisation_pct BETWEEN 0 AND 1)
);

CREATE TABLE IF NOT EXISTS budgets (
  budget_id TEXT PRIMARY KEY,
  entity_id TEXT NOT NULL REFERENCES entities (entity_id),
  cost_center TEXT NOT NULL,
  period TEXT NOT NULL,
  currency TEXT NOT NULL DEFAULT 'INR',
  approved_limit_inr NUMERIC(18, 2) NOT NULL,
  committed_spend_inr NUMERIC(18, 2) NOT NULL DEFAULT 0,
  available_budget_inr NUMERIC(18, 2) NOT NULL,
  single_action_approval_threshold_inr NUMERIC(18, 2),
  status TEXT NOT NULL DEFAULT 'ACTIVE',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (status IN ('ACTIVE', 'INACTIVE', 'CLOSED'))
);

CREATE TABLE IF NOT EXISTS supplier_contracts (
  contract_id TEXT PRIMARY KEY,
  supplier_id TEXT NOT NULL REFERENCES suppliers (supplier_id),
  contract_category TEXT NOT NULL,
  effective_from DATE,
  effective_to DATE,
  contract_limit_inr NUMERIC(18, 2),
  currency TEXT NOT NULL DEFAULT 'INR',
  status TEXT NOT NULL DEFAULT 'ACTIVE',
  owner_department TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (status IN ('ACTIVE', 'EXPIRED', 'TERMINATED'))
);

CREATE TABLE IF NOT EXISTS shifts (
  shift_id TEXT PRIMARY KEY,
  entity_id TEXT NOT NULL REFERENCES entities (entity_id),
  start_local TEXT NOT NULL,
  end_local TEXT NOT NULL,
  duration_hours INTEGER,
  status TEXT NOT NULL DEFAULT 'ACTIVE',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (status IN ('ACTIVE', 'INACTIVE'))
);

CREATE TABLE IF NOT EXISTS supplier_offers (
  offer_id TEXT PRIMARY KEY,
  supplier_id TEXT NOT NULL REFERENCES suppliers (supplier_id),
  item_id TEXT NOT NULL REFERENCES products (product_id),
  unit_price_inr NUMERIC(18, 2) NOT NULL,
  price_uom TEXT NOT NULL,
  lead_time_hours INTEGER,
  max_available_qty NUMERIC(18, 2),
  on_time_rate NUMERIC(5, 4),
  effective_from DATE,
  effective_to DATE,
  offer_status TEXT NOT NULL DEFAULT 'ACTIVE',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (offer_status IN ('ACTIVE', 'EXPIRED', 'WITHDRAWN')),
  CHECK (on_time_rate IS NULL OR on_time_rate BETWEEN 0 AND 1)
);

CREATE TABLE IF NOT EXISTS reorder_policies (
  policy_id TEXT PRIMARY KEY,
  item_id TEXT NOT NULL REFERENCES products (product_id),
  warehouse_id TEXT NOT NULL REFERENCES warehouses (warehouse_id),
  reorder_point_qty NUMERIC(18, 2) NOT NULL,
  safety_stock_qty NUMERIC(18, 2) NOT NULL,
  target_stock_qty NUMERIC(18, 2),
  status TEXT NOT NULL DEFAULT 'ACTIVE',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (item_id, warehouse_id),
  CHECK (status IN ('ACTIVE', 'INACTIVE'))
);

CREATE TABLE IF NOT EXISTS bill_of_materials (
  bom_line_id TEXT PRIMARY KEY,
  output_product_id TEXT NOT NULL REFERENCES products (product_id),
  input_item_id TEXT NOT NULL REFERENCES products (product_id),
  quantity_per_output_unit NUMERIC(10, 4) NOT NULL,
  consumption_uom TEXT NOT NULL,
  version_status TEXT NOT NULL DEFAULT 'STANDARD',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS business_rules (
  rule_id TEXT PRIMARY KEY,
  domain TEXT NOT NULL,
  condition_expression TEXT NOT NULL,
  failure_action TEXT NOT NULL,
  severity TEXT NOT NULL,
  automation_mode TEXT NOT NULL,
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL'))
);

CREATE TABLE IF NOT EXISTS inventory (
  inventory_id TEXT PRIMARY KEY,
  item_id TEXT NOT NULL REFERENCES products (product_id),
  warehouse_id TEXT NOT NULL REFERENCES warehouses (warehouse_id),
  on_hand_qty NUMERIC(18, 2) NOT NULL DEFAULT 0,
  reserved_qty NUMERIC(18, 2) NOT NULL DEFAULT 0,
  available_qty NUMERIC(18, 2) NOT NULL DEFAULT 0,
  uom TEXT NOT NULL,
  as_of_timestamp TIMESTAMPTZ,
  stock_signal TEXT NOT NULL DEFAULT 'NORMAL',
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (stock_signal IN ('NORMAL', 'LOW_STOCK', 'CRITICAL', 'OUT_OF_STOCK', 'EXCESS'))
);

-- customer_ref is TEXT (no ref_customers sheet in Phase 1).
CREATE TABLE IF NOT EXISTS orders (
  order_id TEXT PRIMARY KEY,
  customer_ref TEXT NOT NULL,
  entity_id TEXT NOT NULL REFERENCES entities (entity_id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  required_delivery_at TIMESTAMPTZ,
  status TEXT NOT NULL DEFAULT 'OPEN',
  priority TEXT NOT NULL DEFAULT 'MEDIUM',
  currency TEXT NOT NULL DEFAULT 'INR',
  external_reference TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (status IN ('OPEN', 'IN_PROGRESS', 'AT_RISK', 'COMPLETED', 'CANCELLED')),
  CHECK (priority IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL'))
);

CREATE TABLE IF NOT EXISTS order_lines (
  order_line_id TEXT PRIMARY KEY,
  order_id TEXT NOT NULL REFERENCES orders (order_id),
  product_id TEXT NOT NULL REFERENCES products (product_id),
  requested_qty NUMERIC(18, 2) NOT NULL,
  unit_price_inr NUMERIC(18, 2),
  uom TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS production_batches (
  batch_id TEXT PRIMARY KEY,
  production_line_id TEXT NOT NULL REFERENCES production_lines (production_line_id),
  output_product_id TEXT NOT NULL REFERENCES products (product_id),
  planned_output_qty_mt NUMERIC(18, 2),
  actual_output_qty_mt NUMERIC(18, 2),
  planned_start TIMESTAMPTZ,
  planned_end TIMESTAMPTZ,
  status TEXT NOT NULL DEFAULT 'PLANNED',
  risk_flag TEXT NOT NULL DEFAULT 'NORMAL',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (status IN ('PLANNED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')),
  CHECK (risk_flag IN ('NORMAL', 'MATERIAL_RISK', 'DELAY_RISK', 'CAPACITY_RISK', 'QUALITY_RISK'))
);

CREATE TABLE IF NOT EXISTS purchase_orders (
  po_id TEXT PRIMARY KEY,
  supplier_id TEXT NOT NULL REFERENCES suppliers (supplier_id),
  item_id TEXT NOT NULL REFERENCES products (product_id),
  quantity NUMERIC(18, 2) NOT NULL,
  unit_cost_inr NUMERIC(18, 2) NOT NULL,
  total_cost_inr NUMERIC(18, 2),
  currency TEXT NOT NULL DEFAULT 'INR',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  status TEXT NOT NULL DEFAULT 'DRAFT',
  budget_id TEXT REFERENCES budgets (budget_id),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (status IN ('DRAFT', 'APPROVED', 'IN_TRANSIT', 'RECEIVED', 'CANCELLED'))
);

CREATE TABLE IF NOT EXISTS goods_receipts (
  grn_id TEXT PRIMARY KEY,
  po_id TEXT NOT NULL REFERENCES purchase_orders (po_id),
  supplier_id TEXT NOT NULL REFERENCES suppliers (supplier_id),
  item_id TEXT NOT NULL REFERENCES products (product_id),
  received_qty NUMERIC(18, 2) NOT NULL,
  accepted_qty NUMERIC(18, 2) NOT NULL DEFAULT 0,
  received_at TIMESTAMPTZ,
  inspection_status TEXT NOT NULL DEFAULT 'PENDING',
  quality_certificate_ref TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (inspection_status IN ('PENDING', 'ACCEPTED', 'QUALITY_HOLD', 'REJECTED'))
);

CREATE TABLE IF NOT EXISTS shipments (
  shipment_id TEXT PRIMARY KEY,
  order_id TEXT NOT NULL REFERENCES orders (order_id),
  origin_warehouse_id TEXT REFERENCES warehouses (warehouse_id),
  destination_warehouse_id TEXT REFERENCES warehouses (warehouse_id),
  carrier_supplier_id TEXT REFERENCES suppliers (supplier_id),
  planned_dispatch_at TIMESTAMPTZ,
  estimated_arrival_at TIMESTAMPTZ,
  status TEXT NOT NULL DEFAULT 'PLANNED',
  transport_mode TEXT,
  risk_flag TEXT NOT NULL DEFAULT 'NORMAL',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (status IN ('PLANNED', 'IN_TRANSIT', 'AT_RISK', 'DELIVERED', 'CANCELLED')),
  CHECK (transport_mode IS NULL OR transport_mode IN ('RAIL', 'ROAD', 'ROAD_RAIL', 'SEA', 'AIR')),
  CHECK (risk_flag IN ('NORMAL', 'DELAY_RISK', 'AT_RISK'))
);

CREATE TABLE IF NOT EXISTS carrier_events (
  carrier_event_id TEXT PRIMARY KEY,
  shipment_id TEXT NOT NULL REFERENCES shipments (shipment_id),
  event_timestamp TIMESTAMPTZ NOT NULL,
  event_type TEXT NOT NULL,
  description TEXT,
  source_supplier_id TEXT REFERENCES suppliers (supplier_id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS quality_events (
  quality_event_id TEXT PRIMARY KEY,
  batch_id TEXT NOT NULL REFERENCES production_batches (batch_id),
  product_id TEXT NOT NULL REFERENCES products (product_id),
  detected_at TIMESTAMPTZ,
  defect_code TEXT NOT NULL,
  severity TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'OPEN',
  recommended_control TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
  CHECK (status IN ('OPEN', 'IN_REVIEW', 'RELEASED', 'REJECTED'))
);

CREATE TABLE IF NOT EXISTS maintenance_assets (
  asset_id TEXT PRIMARY KEY,
  production_line_id TEXT NOT NULL REFERENCES production_lines (production_line_id),
  asset_name TEXT NOT NULL,
  last_signal_at TIMESTAMPTZ,
  failure_risk_score NUMERIC(5, 4),
  health_status TEXT NOT NULL DEFAULT 'NORMAL',
  next_maintenance_due TIMESTAMPTZ,
  recommended_action TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (health_status IN ('NORMAL', 'WARNING', 'CRITICAL')),
  CHECK (failure_risk_score IS NULL OR failure_risk_score BETWEEN 0 AND 1)
);

CREATE TABLE IF NOT EXISTS maintenance_work_orders (
  work_order_id TEXT PRIMARY KEY,
  asset_id TEXT NOT NULL REFERENCES maintenance_assets (asset_id),
  work_type TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'OPEN',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  scheduled_for TIMESTAMPTZ,
  priority TEXT NOT NULL DEFAULT 'MEDIUM',
  assigned_team_or_vendor TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (status IN ('OPEN', 'SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')),
  CHECK (priority IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL'))
);

CREATE TABLE IF NOT EXISTS energy_readings (
  reading_id TEXT PRIMARY KEY,
  entity_id TEXT NOT NULL REFERENCES entities (entity_id),
  production_line_id TEXT NOT NULL REFERENCES production_lines (production_line_id),
  reading_at TIMESTAMPTZ NOT NULL,
  energy_kwh NUMERIC(18, 2) NOT NULL,
  unit_rate_inr NUMERIC(10, 4),
  signal TEXT NOT NULL DEFAULT 'NORMAL',
  currency TEXT NOT NULL DEFAULT 'INR',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (signal IN ('NORMAL', 'SPIKE', 'HIGH_USAGE', 'LOW', 'OFFLINE', 'ALERT'))
);

CREATE TABLE IF NOT EXISTS safety_events (
  safety_event_id TEXT PRIMARY KEY,
  entity_id TEXT NOT NULL REFERENCES entities (entity_id),
  occurred_at TIMESTAMPTZ NOT NULL,
  event_type TEXT NOT NULL,
  severity TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'OPEN',
  description TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
  CHECK (status IN ('OPEN', 'INVESTIGATING', 'CLOSED', 'ESCALATED'))
);

CREATE TABLE IF NOT EXISTS feed_health (
  feed_id TEXT PRIMARY KEY,
  source_name TEXT NOT NULL,
  last_success_at TIMESTAMPTZ,
  consecutive_failures INTEGER NOT NULL DEFAULT 0,
  health_status TEXT NOT NULL DEFAULT 'HEALTHY',
  max_age_seconds INTEGER,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (health_status IN ('HEALTHY', 'DEGRADED', 'OFFLINE', 'UNKNOWN'))
);

CREATE INDEX IF NOT EXISTS idx_inventory_item ON inventory (item_id);
CREATE INDEX IF NOT EXISTS idx_inventory_warehouse ON inventory (warehouse_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders (status, created_at);
CREATE INDEX IF NOT EXISTS idx_order_lines_order ON order_lines (order_id);
CREATE INDEX IF NOT EXISTS idx_order_lines_product ON order_lines (product_id);
CREATE INDEX IF NOT EXISTS idx_shipments_order ON shipments (order_id);
CREATE INDEX IF NOT EXISTS idx_shipments_status ON shipments (status);
CREATE INDEX IF NOT EXISTS idx_production_batches_line ON production_batches (production_line_id);
CREATE INDEX IF NOT EXISTS idx_production_batches_status ON production_batches (status);
CREATE INDEX IF NOT EXISTS idx_quality_events_batch ON quality_events (batch_id);
CREATE INDEX IF NOT EXISTS idx_maintenance_assets_line ON maintenance_assets (production_line_id);
CREATE INDEX IF NOT EXISTS idx_maintenance_wo_asset ON maintenance_work_orders (asset_id);
CREATE INDEX IF NOT EXISTS idx_energy_readings_line_time ON energy_readings (production_line_id, reading_at);
CREATE INDEX IF NOT EXISTS idx_safety_events_entity ON safety_events (entity_id, occurred_at);
CREATE INDEX IF NOT EXISTS idx_purchase_orders_supplier ON purchase_orders (supplier_id);
CREATE INDEX IF NOT EXISTS idx_warehouses_entity ON warehouses (entity_id);
CREATE INDEX IF NOT EXISTS idx_users_role ON users (role_id);
CREATE INDEX IF NOT EXISTS idx_supplier_offers_supplier ON supplier_offers (supplier_id);
CREATE INDEX IF NOT EXISTS idx_carrier_events_shipment ON carrier_events (shipment_id);
