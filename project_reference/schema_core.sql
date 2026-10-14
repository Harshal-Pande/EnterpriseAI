-- Enterprise AI Supply Chain Control Room — PostgreSQL starter schema
-- Fictional synthetic dataset. Review before production use.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS scenario_templates (
  scenario_template_id text PRIMARY KEY, scenario_type text NOT NULL,
  domain text NOT NULL, description text NOT NULL, severity text NOT NULL,
  linked_reference_id text, base_record_id text, injection_method text NOT NULL,
  agents_involved text NOT NULL, expected_response text NOT NULL, guardrail text NOT NULL,
  enabled boolean NOT NULL DEFAULT true
);
CREATE TABLE IF NOT EXISTS scenario_instances (
  scenario_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  scenario_template_id text NOT NULL REFERENCES scenario_templates(scenario_template_id),
  scheduled_at timestamptz NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
  status text NOT NULL DEFAULT 'QUEUED', severity text NOT NULL,
  linked_order_id text, linked_batch_id text, input_overlay jsonb NOT NULL DEFAULT '{}'::jsonb,
  workflow_run_id uuid, resolved_at timestamptz, resolution_summary text,
  idempotency_key text NOT NULL UNIQUE, data_mode text NOT NULL DEFAULT 'SYNTHETIC',
  CHECK (status IN ('QUEUED','RUNNING','WAITING_APPROVAL','RESOLVED','FAILED_SAFE','CANCELLED'))
);
CREATE INDEX IF NOT EXISTS idx_scenario_queue ON scenario_instances(status, scheduled_at);
CREATE TABLE IF NOT EXISTS agent_runs (
  agent_run_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  scenario_id uuid NOT NULL REFERENCES scenario_instances(scenario_id),
  workflow_run_id uuid NOT NULL, agent_name text NOT NULL,
  started_at timestamptz NOT NULL DEFAULT now(), completed_at timestamptz,
  status text NOT NULL, input_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
  output jsonb, evidence_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
  error_code text, model_provider text, model_name text, prompt_version text
);
CREATE INDEX IF NOT EXISTS idx_agent_runs_scenario ON agent_runs(scenario_id, started_at);
CREATE TABLE IF NOT EXISTS decisions (
  decision_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  scenario_id uuid NOT NULL REFERENCES scenario_instances(scenario_id),
  workflow_run_id uuid NOT NULL, decision_at timestamptz NOT NULL DEFAULT now(),
  supervisor_summary text NOT NULL, decision_code text NOT NULL,
  recommended_action jsonb NOT NULL, policy_checks jsonb NOT NULL DEFAULT '[]'::jsonb,
  human_approval_required boolean NOT NULL DEFAULT false,
  approval_status text NOT NULL DEFAULT 'NOT_REQUIRED',
  evidence_refs jsonb NOT NULL DEFAULT '[]'::jsonb, audit_event_id uuid,
  blockchain_anchor_status text NOT NULL DEFAULT 'NOT_SUBMITTED'
);
CREATE TABLE IF NOT EXISTS action_queue (
  action_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  scenario_id uuid NOT NULL REFERENCES scenario_instances(scenario_id),
  decision_id uuid NOT NULL REFERENCES decisions(decision_id),
  action_type text NOT NULL, target_entity_id text,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb, status text NOT NULL DEFAULT 'PROPOSED',
  requires_approval boolean NOT NULL DEFAULT false, approved_by text,
  created_at timestamptz NOT NULL DEFAULT now(), executed_at timestamptz,
  result jsonb, idempotency_key text NOT NULL UNIQUE
);
CREATE INDEX IF NOT EXISTS idx_action_queue_status ON action_queue(status, created_at);
CREATE TABLE IF NOT EXISTS event_log (
  event_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  event_timestamp timestamptz NOT NULL DEFAULT now(), event_type text NOT NULL,
  entity_type text NOT NULL, entity_id text NOT NULL, scenario_id uuid REFERENCES scenario_instances(scenario_id),
  workflow_run_id uuid, actor_type text NOT NULL, actor_id text NOT NULL,
  status text NOT NULL, reason_code text, evidence_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
  payload_hash text NOT NULL, previous_event_hash text, source_channel text NOT NULL DEFAULT 'SYSTEM'
);
CREATE INDEX IF NOT EXISTS idx_event_log_entity_time ON event_log(entity_type, entity_id, event_timestamp);
CREATE TABLE IF NOT EXISTS blockchain_anchors (
  anchor_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id_or_batch_id text NOT NULL, payload_hash text NOT NULL,
  chain_name text NOT NULL, chain_id bigint NOT NULL, contract_address text NOT NULL,
  transaction_hash text, block_number bigint, anchored_at timestamptz,
  confirmation_status text NOT NULL DEFAULT 'NOT_SUBMITTED',
  verification_status text NOT NULL DEFAULT 'NOT_VERIFIED', error_message text
);
CREATE TABLE IF NOT EXISTS scheduler_state (
  scheduler_name text PRIMARY KEY, enabled boolean NOT NULL DEFAULT true,
  interval_seconds integer NOT NULL DEFAULT 300 CHECK (interval_seconds >= 60),
  last_scheduled_at timestamptz, next_scheduled_at timestamptz,
  updated_at timestamptz NOT NULL DEFAULT now()
);
INSERT INTO scheduler_state(scheduler_name,enabled,interval_seconds)
VALUES ('scenario-generator',true,300) ON CONFLICT (scheduler_name) DO NOTHING;
