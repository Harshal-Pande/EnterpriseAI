-- Migration 009: Agent Evidence and Inter-Agent Messages
-- Adds structured tool call logging, evidence reference tables,
-- and inter-agent message passing for grounded orchestration.

CREATE TABLE IF NOT EXISTS agent_tool_calls (
  tool_call_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_run_id    UUID NOT NULL REFERENCES agent_runs (agent_run_id),
  scenario_id     UUID REFERENCES scenario_instances (scenario_id),
  tool_name       TEXT NOT NULL,
  tool_version    TEXT NOT NULL DEFAULT 'v1',
  input_params    JSONB NOT NULL DEFAULT '{}'::jsonb,
  output_data     JSONB,
  data_refs       JSONB NOT NULL DEFAULT '[]'::jsonb,  -- [{table, pk, columns}]
  execution_ms    INTEGER,
  status          TEXT NOT NULL DEFAULT 'PENDING',
  error_message   TEXT,
  called_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at    TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'SKIPPED')),
  CHECK (tool_name IN (
    'get_inventory_snapshot', 'get_stock_coverage', 'get_order_details',
    'get_supplier_offers', 'get_supplier_reliability', 'get_bom_requirements',
    'check_budget_headroom', 'get_freight_lanes', 'get_production_schedule',
    'get_policy_rules', 'evaluate_policy', 'create_purchase_order',
    'reserve_inventory', 'release_reservation', 'update_order_status',
    'send_notification', 'anchor_to_blockchain', 'custom'
  ))
);

CREATE INDEX IF NOT EXISTS idx_tool_calls_agent    ON agent_tool_calls (agent_run_id, called_at DESC);
CREATE INDEX IF NOT EXISTS idx_tool_calls_scenario ON agent_tool_calls (scenario_id) WHERE scenario_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_tool_calls_name     ON agent_tool_calls (tool_name, status);

CREATE TABLE IF NOT EXISTS evidence_references (
  evidence_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_run_id    UUID REFERENCES agent_runs (agent_run_id),
  tool_call_id    UUID REFERENCES agent_tool_calls (tool_call_id),
  scenario_id     UUID REFERENCES scenario_instances (scenario_id),
  source_table    TEXT NOT NULL,
  source_pk       TEXT NOT NULL,
  source_columns  TEXT[],
  snapshot_data   JSONB,
  evidence_type   TEXT NOT NULL DEFAULT 'DATA_QUERY',
  citation_label  TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (evidence_type IN (
    'DATA_QUERY', 'POLICY_EVALUATION', 'EXTERNAL_API',
    'CALCULATION', 'HUMAN_INPUT', 'SYSTEM_STATE'
  ))
);

CREATE INDEX IF NOT EXISTS idx_evidence_agent    ON evidence_references (agent_run_id) WHERE agent_run_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_evidence_scenario ON evidence_references (scenario_id) WHERE scenario_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_evidence_table    ON evidence_references (source_table, source_pk);

CREATE TABLE IF NOT EXISTS inter_agent_messages (
  message_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scenario_id       UUID NOT NULL REFERENCES scenario_instances (scenario_id),
  workflow_run_id   UUID NOT NULL,
  from_agent        TEXT NOT NULL,
  to_agent          TEXT NOT NULL,
  message_type      TEXT NOT NULL DEFAULT 'FINDINGS',
  payload           JSONB NOT NULL DEFAULT '{}'::jsonb,
  evidence_refs     JSONB NOT NULL DEFAULT '[]'::jsonb,
  sent_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  acknowledged_at   TIMESTAMPTZ,
  status            TEXT NOT NULL DEFAULT 'SENT',
  CHECK (message_type IN (
    'FINDINGS', 'REQUEST', 'RESPONSE', 'ESCALATION', 'CONTEXT', 'DIRECTIVE'
  )),
  CHECK (status IN ('SENT', 'ACKNOWLEDGED', 'IGNORED', 'FAILED'))
);

CREATE INDEX IF NOT EXISTS idx_inter_agent_scenario ON inter_agent_messages (scenario_id, sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_inter_agent_to        ON inter_agent_messages (to_agent, status);
