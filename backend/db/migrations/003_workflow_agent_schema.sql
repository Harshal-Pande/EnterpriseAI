-- Phase 2 Tasks 6 & 7: Workflow and Agent-Run persistence schema additions.
-- Additive, safely reversible, and forward-compatible migration.

ALTER TABLE scenario_instances 
  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

ALTER TABLE agent_runs 
  ADD COLUMN IF NOT EXISTS error_message TEXT;

CREATE INDEX IF NOT EXISTS idx_scenario_instances_updated_at 
  ON scenario_instances (updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_scenario_instances_workflow_run 
  ON scenario_instances (workflow_run_id);

CREATE INDEX IF NOT EXISTS idx_scenario_instances_order 
  ON scenario_instances (linked_order_id);

CREATE INDEX IF NOT EXISTS idx_agent_runs_workflow 
  ON agent_runs (workflow_run_id, started_at);

CREATE INDEX IF NOT EXISTS idx_agent_runs_name_status 
  ON agent_runs (agent_name, status);
