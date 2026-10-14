-- Phase 1 runtime / workflow schema.
-- Supersedes project_reference/schema_core.sql for application use.
-- The original starter file is preserved unchanged.
--
-- Empty workbook sheets (headers only, 0 rows) still receive tables:
--   scenario_instances, agent_runs, decisions, action_queue,
--   event_log, blockchain_anchors.
-- Additional tables justified by the Phase 1/4/5 design (no seed rows):
--   agent_findings, policy_evaluations, approval_requests, action_execution_results.
-- scheduler_state is seeded with a 300s interval; the scheduler itself is Phase 3.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS scenario_templates (
  scenario_template_id TEXT PRIMARY KEY,
  scenario_type TEXT NOT NULL,
  domain TEXT NOT NULL,
  description TEXT NOT NULL,
  severity TEXT NOT NULL,
  linked_reference_id TEXT,
  base_record_id TEXT,
  injection_method TEXT NOT NULL,
  agents_involved TEXT NOT NULL,
  expected_response TEXT NOT NULL,
  guardrail TEXT NOT NULL,
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL'))
);

CREATE TABLE IF NOT EXISTS simulation_config (
  config_key TEXT PRIMARY KEY,
  config_value TEXT NOT NULL,
  description TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS scenario_instances (
  scenario_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scenario_template_id TEXT NOT NULL REFERENCES scenario_templates (scenario_template_id),
  scheduled_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  status TEXT NOT NULL DEFAULT 'QUEUED',
  severity TEXT NOT NULL,
  linked_order_id TEXT,
  linked_batch_id TEXT,
  input_overlay JSONB NOT NULL DEFAULT '{}'::jsonb,
  workflow_run_id UUID,
  resolved_at TIMESTAMPTZ,
  resolution_summary TEXT,
  idempotency_key TEXT NOT NULL UNIQUE,
  data_mode TEXT NOT NULL DEFAULT 'SYNTHETIC',
  CHECK (status IN (
    'QUEUED', 'CREATED', 'TRIAGED', 'INVESTIGATING', 'DECISION_READY',
    'RUNNING', 'WAITING_APPROVAL', 'AWAITING_APPROVAL', 'EXECUTING',
    'RESOLVED', 'REJECTED', 'FAILED', 'FAILED_SAFE', 'CANCELLED', 'NEEDS_HUMAN_REVIEW'
  )),
  CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL'))
);

CREATE INDEX IF NOT EXISTS idx_scenario_queue ON scenario_instances (status, scheduled_at);

CREATE TABLE IF NOT EXISTS agent_runs (
  agent_run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scenario_id UUID NOT NULL REFERENCES scenario_instances (scenario_id),
  workflow_run_id UUID NOT NULL,
  agent_name TEXT NOT NULL,
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  status TEXT NOT NULL,
  input_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
  output JSONB,
  evidence_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
  error_code TEXT,
  model_provider TEXT,
  model_name TEXT,
  prompt_version TEXT,
  CHECK (status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'SKIPPED'))
);

CREATE INDEX IF NOT EXISTS idx_agent_runs_scenario ON agent_runs (scenario_id, started_at);

CREATE TABLE IF NOT EXISTS agent_findings (
  finding_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_run_id UUID NOT NULL REFERENCES agent_runs (agent_run_id),
  scenario_id UUID REFERENCES scenario_instances (scenario_id),
  finding_code TEXT NOT NULL,
  severity TEXT NOT NULL,
  summary TEXT NOT NULL,
  evidence_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL'))
);

CREATE INDEX IF NOT EXISTS idx_agent_findings_run ON agent_findings (agent_run_id);

CREATE TABLE IF NOT EXISTS decisions (
  decision_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scenario_id UUID NOT NULL REFERENCES scenario_instances (scenario_id),
  workflow_run_id UUID NOT NULL,
  decision_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  supervisor_summary TEXT NOT NULL,
  decision_code TEXT NOT NULL,
  recommended_action JSONB NOT NULL,
  policy_checks JSONB NOT NULL DEFAULT '[]'::jsonb,
  human_approval_required BOOLEAN NOT NULL DEFAULT FALSE,
  approval_status TEXT NOT NULL DEFAULT 'NOT_REQUIRED',
  evidence_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
  audit_event_id UUID,
  blockchain_anchor_status TEXT NOT NULL DEFAULT 'NOT_SUBMITTED',
  CHECK (approval_status IN ('NOT_REQUIRED', 'PENDING', 'APPROVED', 'REJECTED')),
  CHECK (blockchain_anchor_status IN ('NOT_SUBMITTED', 'PENDING', 'CONFIRMED', 'FAILED', 'NOT_REQUIRED'))
);

CREATE TABLE IF NOT EXISTS action_queue (
  action_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scenario_id UUID NOT NULL REFERENCES scenario_instances (scenario_id),
  decision_id UUID NOT NULL REFERENCES decisions (decision_id),
  action_type TEXT NOT NULL,
  target_entity_id TEXT,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  status TEXT NOT NULL DEFAULT 'PROPOSED',
  requires_approval BOOLEAN NOT NULL DEFAULT FALSE,
  approved_by TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  executed_at TIMESTAMPTZ,
  result JSONB,
  idempotency_key TEXT NOT NULL UNIQUE,
  CHECK (status IN ('PROPOSED', 'APPROVED', 'REJECTED', 'EXECUTING', 'SUCCEEDED', 'FAILED', 'CANCELLED'))
);

CREATE INDEX IF NOT EXISTS idx_action_queue_status ON action_queue (status, created_at);

CREATE TABLE IF NOT EXISTS policy_evaluations (
  policy_eval_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  decision_id UUID REFERENCES decisions (decision_id),
  action_id UUID REFERENCES action_queue (action_id),
  rule_id TEXT REFERENCES business_rules (rule_id),
  result TEXT NOT NULL,
  details JSONB NOT NULL DEFAULT '{}'::jsonb,
  evaluated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (result IN ('PASS', 'FAIL', 'SKIP', 'NEEDS_APPROVAL'))
);

CREATE INDEX IF NOT EXISTS idx_policy_evaluations_decision ON policy_evaluations (decision_id);

CREATE TABLE IF NOT EXISTS approval_requests (
  approval_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  action_id UUID REFERENCES action_queue (action_id),
  decision_id UUID REFERENCES decisions (decision_id),
  scenario_id UUID REFERENCES scenario_instances (scenario_id),
  requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  required_domain TEXT,
  status TEXT NOT NULL DEFAULT 'PENDING',
  decided_by TEXT,
  decided_at TIMESTAMPTZ,
  reason TEXT,
  CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED', 'CANCELLED', 'EXPIRED'))
);

CREATE TABLE IF NOT EXISTS action_execution_results (
  execution_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  action_id UUID NOT NULL REFERENCES action_queue (action_id),
  attempted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  status TEXT NOT NULL,
  result JSONB,
  error_message TEXT,
  CHECK (status IN ('SUCCEEDED', 'FAILED', 'SKIPPED', 'ROLLED_BACK'))
);

CREATE INDEX IF NOT EXISTS idx_action_execution_action ON action_execution_results (action_id);

CREATE TABLE IF NOT EXISTS event_log (
  event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  event_type TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  scenario_id UUID REFERENCES scenario_instances (scenario_id),
  workflow_run_id UUID,
  actor_type TEXT NOT NULL,
  actor_id TEXT NOT NULL,
  status TEXT NOT NULL,
  reason_code TEXT,
  evidence_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
  payload_hash TEXT NOT NULL,
  previous_event_hash TEXT,
  source_channel TEXT NOT NULL DEFAULT 'SYSTEM'
);

CREATE INDEX IF NOT EXISTS idx_event_log_entity_time ON event_log (entity_type, entity_id, event_timestamp);
CREATE INDEX IF NOT EXISTS idx_event_log_scenario ON event_log (scenario_id, event_timestamp);

CREATE TABLE IF NOT EXISTS blockchain_anchors (
  anchor_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id_or_batch_id TEXT NOT NULL,
  payload_hash TEXT NOT NULL,
  chain_name TEXT NOT NULL,
  chain_id BIGINT NOT NULL,
  contract_address TEXT NOT NULL,
  transaction_hash TEXT,
  block_number BIGINT,
  anchored_at TIMESTAMPTZ,
  confirmation_status TEXT NOT NULL DEFAULT 'NOT_SUBMITTED',
  verification_status TEXT NOT NULL DEFAULT 'NOT_VERIFIED',
  error_message TEXT,
  CHECK (confirmation_status IN ('NOT_SUBMITTED', 'PENDING', 'CONFIRMED', 'FAILED')),
  CHECK (verification_status IN ('NOT_VERIFIED', 'MATCHED', 'MISMATCH', 'FAILED'))
);

CREATE TABLE IF NOT EXISTS scheduler_state (
  scheduler_name TEXT PRIMARY KEY,
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  interval_seconds INTEGER NOT NULL DEFAULT 300 CHECK (interval_seconds >= 60),
  last_scheduled_at TIMESTAMPTZ,
  next_scheduled_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO scheduler_state (scheduler_name, enabled, interval_seconds)
VALUES ('scenario-generator', TRUE, 300)
ON CONFLICT (scheduler_name) DO NOTHING;
