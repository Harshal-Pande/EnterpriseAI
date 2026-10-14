-- Phase 2 Tasks 8-12: Scheduler, Action Lifecycle, and Decision Indexes.
-- Additive, safely reversible, and forward-compatible migration.

ALTER TABLE scheduler_state 
  ADD COLUMN IF NOT EXISTS locked_by TEXT,
  ADD COLUMN IF NOT EXISTS lock_acquired_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS lease_expires_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS last_status TEXT,
  ADD COLUMN IF NOT EXISTS last_scenario_id UUID,
  ADD COLUMN IF NOT EXISTS total_runs INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS consecutive_failures INTEGER NOT NULL DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_scheduler_state_lease 
  ON scheduler_state (lease_expires_at);

CREATE INDEX IF NOT EXISTS idx_decisions_scenario 
  ON decisions (scenario_id);

CREATE INDEX IF NOT EXISTS idx_approval_requests_status 
  ON approval_requests (status);

CREATE INDEX IF NOT EXISTS idx_action_queue_scenario 
  ON action_queue (scenario_id);
