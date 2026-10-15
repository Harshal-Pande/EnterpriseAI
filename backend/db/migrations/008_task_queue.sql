-- Migration 008: Durable Task Queue (Phase P4)
-- Implements a PostgreSQL-backed task queue using SELECT ... FOR UPDATE SKIP LOCKED
-- for exactly-once, crash-safe processing of up to 1,000+ concurrent tasks.

CREATE TABLE IF NOT EXISTS task_queue (
  task_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  task_type         TEXT NOT NULL,
  priority          INTEGER NOT NULL DEFAULT 5 CHECK (priority BETWEEN 1 AND 10),
  payload           JSONB NOT NULL DEFAULT '{}'::jsonb,
  idempotency_key   TEXT NOT NULL UNIQUE,
  status            TEXT NOT NULL DEFAULT 'PENDING',
  scenario_id       UUID REFERENCES scenario_instances (scenario_id),
  workflow_run_id   UUID,
  assigned_worker   TEXT,
  lease_expires_at  TIMESTAMPTZ,
  attempt_count     INTEGER NOT NULL DEFAULT 0,
  max_attempts      INTEGER NOT NULL DEFAULT 3,
  last_error        TEXT,
  result            JSONB,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  started_at        TIMESTAMPTZ,
  completed_at      TIMESTAMPTZ,
  scheduled_for     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  parent_task_id    UUID REFERENCES task_queue (task_id),
  tags              TEXT[],
  CHECK (status IN (
    'PENDING', 'CLAIMED', 'RUNNING', 'COMPLETED', 'FAILED',
    'CANCELLED', 'RETRYING', 'DEAD_LETTER', 'PAUSED'
  )),
  CHECK (task_type IN (
    'ORCHESTRATION', 'SCENARIO_RUN', 'AGENT_RUN', 'DATA_SYNC',
    'BLOCKCHAIN_ANCHOR', 'NOTIFICATION', 'CLEANUP', 'BATCH_LOAD', 'HEALTH_CHECK'
  ))
);

-- Primary work-claim index: workers claim PENDING tasks ordered by priority+time
CREATE INDEX IF NOT EXISTS idx_task_queue_claim
  ON task_queue (priority DESC, scheduled_for ASC, status)
  WHERE status IN ('PENDING', 'RETRYING');

-- Lease expiry recovery index: reaper finds abandoned CLAIMED/RUNNING tasks
CREATE INDEX IF NOT EXISTS idx_task_queue_lease
  ON task_queue (lease_expires_at)
  WHERE status IN ('CLAIMED', 'RUNNING');

-- Scenario grouping index
CREATE INDEX IF NOT EXISTS idx_task_queue_scenario
  ON task_queue (scenario_id)
  WHERE scenario_id IS NOT NULL;

-- Type + status for batch control queries
CREATE INDEX IF NOT EXISTS idx_task_queue_type_status
  ON task_queue (task_type, status, created_at DESC);

-- Parent-child task relationships
CREATE INDEX IF NOT EXISTS idx_task_queue_parent
  ON task_queue (parent_task_id)
  WHERE parent_task_id IS NOT NULL;

-- Worker heartbeat table: track running workers for health monitoring
CREATE TABLE IF NOT EXISTS task_workers (
  worker_id         TEXT PRIMARY KEY,
  worker_pid        INTEGER,
  worker_host       TEXT NOT NULL DEFAULT 'localhost',
  started_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_heartbeat_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  tasks_claimed     INTEGER NOT NULL DEFAULT 0,
  tasks_completed   INTEGER NOT NULL DEFAULT 0,
  tasks_failed      INTEGER NOT NULL DEFAULT 0,
  status            TEXT NOT NULL DEFAULT 'RUNNING',
  metadata          JSONB NOT NULL DEFAULT '{}'::jsonb,
  CHECK (status IN ('RUNNING', 'IDLE', 'STOPPING', 'STOPPED', 'CRASHED'))
);

CREATE INDEX IF NOT EXISTS idx_task_workers_heartbeat
  ON task_workers (last_heartbeat_at)
  WHERE status IN ('RUNNING', 'IDLE');

-- Task batches: group tasks for coordinated batch operations
CREATE TABLE IF NOT EXISTS task_batches (
  batch_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  batch_name        TEXT NOT NULL,
  batch_type        TEXT NOT NULL DEFAULT 'GENERIC',
  total_tasks       INTEGER NOT NULL DEFAULT 0,
  pending_count     INTEGER NOT NULL DEFAULT 0,
  running_count     INTEGER NOT NULL DEFAULT 0,
  completed_count   INTEGER NOT NULL DEFAULT 0,
  failed_count      INTEGER NOT NULL DEFAULT 0,
  cancelled_count   INTEGER NOT NULL DEFAULT 0,
  status            TEXT NOT NULL DEFAULT 'ACTIVE',
  created_by        TEXT NOT NULL DEFAULT 'SYSTEM',
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at      TIMESTAMPTZ,
  metadata          JSONB NOT NULL DEFAULT '{}'::jsonb,
  CHECK (status IN ('ACTIVE', 'PAUSED', 'COMPLETED', 'CANCELLED', 'FAILED'))
);

-- Add batch FK to task_queue
ALTER TABLE task_queue ADD COLUMN IF NOT EXISTS batch_id UUID REFERENCES task_batches (batch_id);
CREATE INDEX IF NOT EXISTS idx_task_queue_batch ON task_queue (batch_id) WHERE batch_id IS NOT NULL;

-- Function: auto-update task_queue.updated_at on any row change
CREATE OR REPLACE FUNCTION fn_task_queue_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_task_queue_updated_at ON task_queue;
CREATE TRIGGER trg_task_queue_updated_at
  BEFORE UPDATE ON task_queue
  FOR EACH ROW EXECUTE FUNCTION fn_task_queue_updated_at();
