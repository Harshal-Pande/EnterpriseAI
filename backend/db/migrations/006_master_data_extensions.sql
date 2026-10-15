-- Migration 006: Master Data Extensions
-- Adds: customers, carriers, transport_lanes tables
-- Additive only — existing tables are not modified.
-- Safe to re-run (all CREATE TABLE IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS customers (
  customer_id   TEXT PRIMARY KEY,
  customer_name TEXT NOT NULL,
  customer_type TEXT NOT NULL DEFAULT 'B2B',
  city          TEXT,
  state         TEXT,
  country       TEXT NOT NULL DEFAULT 'IN',
  credit_limit_inr NUMERIC(18, 2),
  payment_terms_days INTEGER NOT NULL DEFAULT 30,
  tier          TEXT NOT NULL DEFAULT 'STANDARD',
  status        TEXT NOT NULL DEFAULT 'ACTIVE',
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (customer_type IN ('B2B', 'B2C', 'INTERNAL', 'EXPORT')),
  CHECK (tier IN ('STANDARD', 'PREFERRED', 'STRATEGIC', 'SUSPENDED')),
  CHECK (status IN ('ACTIVE', 'INACTIVE', 'SUSPENDED'))
);

CREATE INDEX IF NOT EXISTS idx_customers_status ON customers (status);
CREATE INDEX IF NOT EXISTS idx_customers_tier   ON customers (tier);

CREATE TABLE IF NOT EXISTS carriers (
  carrier_id        TEXT PRIMARY KEY,
  carrier_name      TEXT NOT NULL,
  carrier_type      TEXT NOT NULL DEFAULT 'ROAD',
  service_zones     TEXT[],
  max_load_mt       NUMERIC(10, 2),
  avg_transit_days  NUMERIC(5, 2),
  on_time_rate      NUMERIC(5, 4),
  cost_per_km_inr   NUMERIC(10, 4),
  status            TEXT NOT NULL DEFAULT 'ACTIVE',
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (carrier_type IN ('ROAD', 'RAIL', 'SEA', 'AIR', 'MULTIMODAL')),
  CHECK (status IN ('ACTIVE', 'INACTIVE', 'SUSPENDED')),
  CHECK (on_time_rate IS NULL OR on_time_rate BETWEEN 0 AND 1)
);

CREATE INDEX IF NOT EXISTS idx_carriers_type   ON carriers (carrier_type);
CREATE INDEX IF NOT EXISTS idx_carriers_status ON carriers (status);

CREATE TABLE IF NOT EXISTS transport_lanes (
  lane_id           TEXT PRIMARY KEY,
  origin_city       TEXT NOT NULL,
  origin_state      TEXT,
  dest_city         TEXT NOT NULL,
  dest_state        TEXT,
  carrier_id        TEXT NOT NULL REFERENCES carriers (carrier_id),
  mode              TEXT NOT NULL DEFAULT 'ROAD',
  distance_km       NUMERIC(10, 2),
  transit_days_min  INTEGER NOT NULL DEFAULT 1,
  transit_days_max  INTEGER NOT NULL DEFAULT 5,
  freight_rate_inr_per_mt NUMERIC(10, 4),
  status            TEXT NOT NULL DEFAULT 'ACTIVE',
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (mode IN ('ROAD', 'RAIL', 'SEA', 'AIR', 'MULTIMODAL')),
  CHECK (status IN ('ACTIVE', 'INACTIVE', 'SEASONAL')),
  CHECK (transit_days_min <= transit_days_max)
);

CREATE INDEX IF NOT EXISTS idx_lanes_carrier ON transport_lanes (carrier_id);
CREATE INDEX IF NOT EXISTS idx_lanes_origin  ON transport_lanes (origin_city);
CREATE INDEX IF NOT EXISTS idx_lanes_dest    ON transport_lanes (dest_city);

-- Add customer FK to orders if customers table is now present and column exists
-- Use a safe DO block so re-runs are idempotent
DO $$
BEGIN
  -- Add customer_id column to orders if not present
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'orders' AND column_name = 'customer_id'
  ) THEN
    ALTER TABLE orders ADD COLUMN customer_id TEXT REFERENCES customers (customer_id);
  END IF;
END;
$$;
