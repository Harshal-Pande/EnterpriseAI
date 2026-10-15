-- Migration 012: Cascade Runtime Foreign Keys
-- Configures ON DELETE CASCADE on runtime telemetry tables:
-- agent_tool_calls, evidence_references, inter_agent_messages, task_queue.
-- Ensures that when test scenarios or completed workflows are purged,
-- dependent telemetry records are cleaned up cleanly without foreign key violations.

DO $$
BEGIN
  -- 1. agent_tool_calls -> agent_runs
  IF EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE constraint_name = 'agent_tool_calls_agent_run_id_fkey'
  ) THEN
    ALTER TABLE agent_tool_calls DROP CONSTRAINT agent_tool_calls_agent_run_id_fkey;
  END IF;
  ALTER TABLE agent_tool_calls
    ADD CONSTRAINT agent_tool_calls_agent_run_id_fkey
    FOREIGN KEY (agent_run_id) REFERENCES agent_runs (agent_run_id) ON DELETE CASCADE;

  -- 2. agent_tool_calls -> scenario_instances
  IF EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE constraint_name = 'agent_tool_calls_scenario_id_fkey'
  ) THEN
    ALTER TABLE agent_tool_calls DROP CONSTRAINT agent_tool_calls_scenario_id_fkey;
  END IF;
  ALTER TABLE agent_tool_calls
    ADD CONSTRAINT agent_tool_calls_scenario_id_fkey
    FOREIGN KEY (scenario_id) REFERENCES scenario_instances (scenario_id) ON DELETE CASCADE;

  -- 3. evidence_references -> agent_runs
  IF EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE constraint_name = 'evidence_references_agent_run_id_fkey'
  ) THEN
    ALTER TABLE evidence_references DROP CONSTRAINT evidence_references_agent_run_id_fkey;
  END IF;
  ALTER TABLE evidence_references
    ADD CONSTRAINT evidence_references_agent_run_id_fkey
    FOREIGN KEY (agent_run_id) REFERENCES agent_runs (agent_run_id) ON DELETE CASCADE;

  -- 4. evidence_references -> agent_tool_calls
  IF EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE constraint_name = 'evidence_references_tool_call_id_fkey'
  ) THEN
    ALTER TABLE evidence_references DROP CONSTRAINT evidence_references_tool_call_id_fkey;
  END IF;
  ALTER TABLE evidence_references
    ADD CONSTRAINT evidence_references_tool_call_id_fkey
    FOREIGN KEY (tool_call_id) REFERENCES agent_tool_calls (tool_call_id) ON DELETE CASCADE;

  -- 5. evidence_references -> scenario_instances
  IF EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE constraint_name = 'evidence_references_scenario_id_fkey'
  ) THEN
    ALTER TABLE evidence_references DROP CONSTRAINT evidence_references_scenario_id_fkey;
  END IF;
  ALTER TABLE evidence_references
    ADD CONSTRAINT evidence_references_scenario_id_fkey
    FOREIGN KEY (scenario_id) REFERENCES scenario_instances (scenario_id) ON DELETE CASCADE;

  -- 6. inter_agent_messages -> scenario_instances
  IF EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE constraint_name = 'inter_agent_messages_scenario_id_fkey'
  ) THEN
    ALTER TABLE inter_agent_messages DROP CONSTRAINT inter_agent_messages_scenario_id_fkey;
  END IF;
  ALTER TABLE inter_agent_messages
    ADD CONSTRAINT inter_agent_messages_scenario_id_fkey
    FOREIGN KEY (scenario_id) REFERENCES scenario_instances (scenario_id) ON DELETE CASCADE;

  -- 7. task_queue -> scenario_instances
  IF EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE constraint_name = 'task_queue_scenario_id_fkey'
  ) THEN
    ALTER TABLE task_queue DROP CONSTRAINT task_queue_scenario_id_fkey;
  END IF;
  ALTER TABLE task_queue
    ADD CONSTRAINT task_queue_scenario_id_fkey
    FOREIGN KEY (scenario_id) REFERENCES scenario_instances (scenario_id) ON DELETE CASCADE;
END;
$$;
