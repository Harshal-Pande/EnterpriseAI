-- Migration 013: Dedicated Order Processing Queue & Unified Operational Exceptions
-- Additive, safe, idempotent migration supporting:
-- 1. Sequential order queue with atomic claim (SELECT FOR UPDATE SKIP LOCKED)
-- 2. Unified exceptions linked to orders, runs, decisions, approvals, and actions
-- 3. Dedicated scheduler lease for order-queue-runner

-- Table: operational_exceptions
CREATE TABLE IF NOT EXISTS operational_exceptions (
  exception_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id TEXT REFERENCES orders (order_id) ON DELETE SET NULL,
  scenario_id UUID REFERENCES scenario_instances (scenario_id) ON DELETE SET NULL,
  workflow_run_id UUID,
  decision_id UUID REFERENCES decisions (decision_id) ON DELETE SET NULL,
  action_id UUID REFERENCES action_queue (action_id) ON DELETE SET NULL,
  approval_id UUID REFERENCES approval_requests (approval_id) ON DELETE SET NULL,
  severity TEXT NOT NULL DEFAULT 'HIGH' CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
  exception_type TEXT NOT NULL CHECK (exception_type IN (
    'BUDGET_BREACH', 'SUPPLIER_UNAVAILABLE', 'STOCK_SHORTFALL',
    'DELIVERY_DELAY', 'POLICY_VIOLATION', 'QUALITY_SAFETY',
    'AGENT_FAILURE', 'BLOCKCHAIN_FAILURE', 'COMBINED'
  )),
  cause TEXT NOT NULL,
  owner_role TEXT NOT NULL DEFAULT 'OPERATOR',
  status TEXT NOT NULL DEFAULT 'OPEN' CHECK (status IN (
    'OPEN', 'INVESTIGATING', 'PROPOSED', 'AWAITING_APPROVAL',
    'APPROVED', 'RESOLVED', 'REJECTED', 'FAILED'
  )),
  ai_recommendation JSONB NOT NULL DEFAULT '{}'::jsonb,
  proposed_action JSONB,
  resolution_notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  resolved_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_operational_exceptions_status 
  ON operational_exceptions (status, severity, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_operational_exceptions_order 
  ON operational_exceptions (order_id);
CREATE INDEX IF NOT EXISTS idx_operational_exceptions_scenario
  ON operational_exceptions (scenario_id);

-- Table: order_processing_queue
CREATE TABLE IF NOT EXISTS order_processing_queue (
  queue_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id TEXT NOT NULL UNIQUE REFERENCES orders (order_id) ON DELETE CASCADE,
  queue_position INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'QUEUED' CHECK (status IN (
    'QUEUED', 'PROCESSING', 'WAITING_EXCEPTION', 'COMPLETED', 'FAILED', 'CANCELLED'
  )),
  enqueued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  claimed_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  attempt_count INTEGER NOT NULL DEFAULT 0,
  last_error TEXT,
  exception_id UUID REFERENCES operational_exceptions (exception_id) ON DELETE SET NULL,
  origin TEXT NOT NULL DEFAULT 'SYSTEM' CHECK (origin IN (
    'SEED', 'MANUAL', 'REPLENISHMENT', 'SYSTEM'
  )),
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

-- Fast atomic claim index for worker: ordered by stable queue_position
CREATE INDEX IF NOT EXISTS idx_order_queue_claim 
  ON order_processing_queue (queue_position ASC) 
  WHERE status = 'QUEUED';

CREATE INDEX IF NOT EXISTS idx_order_queue_status_pos 
  ON order_processing_queue (status, queue_position);

-- Register order queue runner state in scheduler_state
INSERT INTO scheduler_state (scheduler_name, enabled, interval_seconds)
VALUES ('order-queue-runner', TRUE, 300)
ON CONFLICT (scheduler_name) DO NOTHING;
