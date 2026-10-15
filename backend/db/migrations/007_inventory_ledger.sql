-- Migration 007: Inventory Ledger
-- Adds transactional inventory_movements ledger, stock_reservations, and
-- allocation tracking tables. Additive — existing inventory table is unchanged.

CREATE TABLE IF NOT EXISTS inventory_movements (
  movement_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id        TEXT NOT NULL REFERENCES products (product_id),
  warehouse_id      TEXT NOT NULL REFERENCES warehouses (warehouse_id),
  movement_type     TEXT NOT NULL,
  quantity_mt       NUMERIC(18, 4) NOT NULL,
  unit_cost_inr     NUMERIC(18, 4),
  total_cost_inr    NUMERIC(18, 4),
  reference_type    TEXT,                -- 'PO', 'ORDER', 'ADJUSTMENT', 'TRANSFER'
  reference_id      TEXT,               -- FK-like soft reference (PO ID, order ID, etc.)
  scenario_id       UUID REFERENCES scenario_instances (scenario_id),
  actor_id          TEXT NOT NULL DEFAULT 'SYSTEM',
  movement_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  notes             TEXT,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (movement_type IN (
    'RECEIPT', 'ISSUE', 'TRANSFER_IN', 'TRANSFER_OUT',
    'ADJUSTMENT_POSITIVE', 'ADJUSTMENT_NEGATIVE',
    'RESERVATION', 'RESERVATION_RELEASE', 'SCRAP', 'RETURN'
  )),
  CHECK (reference_type IS NULL OR reference_type IN ('PO', 'ORDER', 'TRANSFER', 'ADJUSTMENT', 'SCENARIO'))
);

CREATE INDEX IF NOT EXISTS idx_inv_movements_product   ON inventory_movements (product_id, movement_at DESC);
CREATE INDEX IF NOT EXISTS idx_inv_movements_warehouse ON inventory_movements (warehouse_id, movement_at DESC);
CREATE INDEX IF NOT EXISTS idx_inv_movements_ref       ON inventory_movements (reference_type, reference_id);
CREATE INDEX IF NOT EXISTS idx_inv_movements_scenario  ON inventory_movements (scenario_id) WHERE scenario_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS stock_reservations (
  reservation_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id        TEXT NOT NULL REFERENCES products (product_id),
  warehouse_id      TEXT NOT NULL REFERENCES warehouses (warehouse_id),
  reserved_qty_mt   NUMERIC(18, 4) NOT NULL CHECK (reserved_qty_mt > 0),
  reference_type    TEXT NOT NULL,
  reference_id      TEXT NOT NULL,
  reserved_by       TEXT NOT NULL DEFAULT 'SYSTEM',
  reserved_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at        TIMESTAMPTZ,
  status            TEXT NOT NULL DEFAULT 'ACTIVE',
  released_at       TIMESTAMPTZ,
  release_reason    TEXT,
  scenario_id       UUID REFERENCES scenario_instances (scenario_id),
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (status IN ('ACTIVE', 'RELEASED', 'EXPIRED', 'CONSUMED')),
  CHECK (reference_type IN ('ORDER', 'SCENARIO', 'MANUAL', 'PO'))
);

CREATE INDEX IF NOT EXISTS idx_stock_reservations_product   ON stock_reservations (product_id, status);
CREATE INDEX IF NOT EXISTS idx_stock_reservations_warehouse ON stock_reservations (warehouse_id, status);
CREATE INDEX IF NOT EXISTS idx_stock_reservations_ref       ON stock_reservations (reference_type, reference_id);
CREATE INDEX IF NOT EXISTS idx_stock_reservations_expires   ON stock_reservations (expires_at) WHERE status = 'ACTIVE';

-- View: net available stock per product + warehouse (on_hand minus active reservations)
CREATE OR REPLACE VIEW v_net_available_stock AS
SELECT
  i.item_id AS product_id,
  i.warehouse_id,
  i.on_hand_qty AS gross_on_hand_mt,
  COALESCE(SUM(r.reserved_qty_mt) FILTER (WHERE r.status = 'ACTIVE'), 0) AS reserved_mt,
  i.on_hand_qty - COALESCE(SUM(r.reserved_qty_mt) FILTER (WHERE r.status = 'ACTIVE'), 0) AS net_available_mt,
  i.available_qty AS existing_available_qty,
  i.stock_signal
FROM inventory i
LEFT JOIN stock_reservations r
  ON r.product_id = i.item_id AND r.warehouse_id = i.warehouse_id
GROUP BY i.item_id, i.warehouse_id, i.on_hand_qty, i.available_qty, i.stock_signal;

