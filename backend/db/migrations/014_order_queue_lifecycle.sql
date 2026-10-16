-- Migration 014: Order Queue Lifecycle, Agent Decisions, and Blockchain Synchronization
-- Adds dedicated FIFO queue table, active running table, done archive, agent decision log,
-- and blockchain blocks/transaction queue.

-- 1. Table: orders_queued (FIFO Queue)
CREATE TABLE IF NOT EXISTS orders_queued (
  queue_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id TEXT NOT NULL UNIQUE REFERENCES orders(order_id) ON DELETE CASCADE,
  customer_name TEXT,
  product_code TEXT,
  quantity_tons NUMERIC,
  priority TEXT DEFAULT 'MEDIUM',
  enqueued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  queue_position INTEGER NOT NULL,
  scenario_type TEXT DEFAULT 'NORMAL'
);

CREATE INDEX IF NOT EXISTS idx_orders_queued_pos 
  ON orders_queued (queue_position ASC);

-- 2. Table: orders_running (Currently Executing by AI Agent Mesh)
CREATE TABLE IF NOT EXISTS orders_running (
  running_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id TEXT NOT NULL UNIQUE REFERENCES orders(order_id) ON DELETE CASCADE,
  customer_name TEXT,
  product_code TEXT,
  quantity_tons NUMERIC,
  priority TEXT DEFAULT 'MEDIUM',
  scenario_type TEXT DEFAULT 'NORMAL',
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  current_stage TEXT NOT NULL DEFAULT 'INITIALIZED',
  status TEXT NOT NULL DEFAULT 'RUNNING' CHECK (status IN ('RUNNING', 'WAITING_APPROVAL', 'EXCEPTION', 'COMPLETING')),
  agent_states JSONB NOT NULL DEFAULT '{}'::jsonb,
  last_error TEXT,
  last_updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. Table: orders_done (Completed/Processed Orders History - Never Re-run)
CREATE TABLE IF NOT EXISTS orders_done (
  done_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id TEXT NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
  customer_name TEXT,
  product_code TEXT,
  quantity_tons NUMERIC,
  priority TEXT,
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  outcome_status TEXT NOT NULL DEFAULT 'COMPLETED',
  final_decision TEXT,
  duration_ms INTEGER DEFAULT 0,
  blockchain_tx_hash TEXT,
  blockchain_block_number BIGINT,
  decisions_summary JSONB NOT NULL DEFAULT '[]'::jsonb,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_orders_done_completed 
  ON orders_done (completed_at DESC);

-- 4. Table: agent_decision_logs (Decisions taken by each specialist agent)
CREATE TABLE IF NOT EXISTS agent_decision_logs (
  decision_log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id TEXT NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
  workflow_run_id TEXT,
  agent_name TEXT NOT NULL,
  decision_type TEXT NOT NULL,
  finding TEXT NOT NULL,
  rationale TEXT,
  risk_level TEXT NOT NULL DEFAULT 'LOW',
  confidence_score NUMERIC(4,3) DEFAULT 0.950,
  evidence_records JSONB NOT NULL DEFAULT '[]'::jsonb,
  anchored_to_blockchain BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_decisions_order 
  ON agent_decision_logs (order_id, created_at DESC);

-- 5. Table: blockchain_tx_queue (Queue of decision transactions to be deployed)
CREATE TABLE IF NOT EXISTS blockchain_tx_queue (
  queue_tx_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  decision_log_id UUID REFERENCES agent_decision_logs(decision_log_id) ON DELETE SET NULL,
  order_id TEXT NOT NULL,
  tx_type TEXT NOT NULL DEFAULT 'AGENT_DECISION',
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  payload_hash TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'QUEUED' CHECK (status IN ('QUEUED', 'MINED', 'FAILED')),
  block_number BIGINT,
  tx_hash TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  mined_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_bchain_tx_queue_status 
  ON blockchain_tx_queue (status, created_at ASC);

-- 6. Table: blockchain_blocks (Blocks containing mined transactions)
CREATE TABLE IF NOT EXISTS blockchain_blocks (
  block_number BIGINT PRIMARY KEY,
  block_hash TEXT NOT NULL UNIQUE,
  previous_block_hash TEXT NOT NULL,
  merkle_root TEXT NOT NULL,
  transaction_count INTEGER NOT NULL DEFAULT 0,
  transactions JSONB NOT NULL DEFAULT '[]'::jsonb,
  validator TEXT NOT NULL DEFAULT 'EnterpriseAI-Consensus',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Seed Genesis Block if empty
INSERT INTO blockchain_blocks (
  block_number, block_hash, previous_block_hash, merkle_root, transaction_count, transactions, validator
) VALUES (
  0,
  '0x0000000000000000000000000000000000000000000000000000000000000000',
  '0x0000000000000000000000000000000000000000000000000000000000000000',
  '0x0000000000000000000000000000000000000000000000000000000000000000',
  0,
  '[]'::jsonb,
  'EnterpriseAI-Genesis'
) ON CONFLICT (block_number) DO NOTHING;

-- Initial Seed: Populate orders_queued from pending orders (order_processing_queue)
INSERT INTO orders_queued (order_id, customer_name, product_code, quantity_tons, priority, queue_position, scenario_type)
SELECT 
  o.order_id,
  c.customer_name,
  COALESCE(ol.product_id, 'PRD-HRC'),
  COALESCE(ol.requested_qty, 50.0),
  o.priority,
  q.queue_position,
  'NORMAL'
FROM order_processing_queue q
JOIN orders o ON o.order_id = q.order_id
LEFT JOIN customers c ON c.customer_id = o.customer_id
LEFT JOIN LATERAL (
  SELECT product_id, SUM(requested_qty) AS requested_qty 
  FROM order_lines 
  WHERE order_id = o.order_id 
  GROUP BY product_id 
  LIMIT 1
) ol ON true
WHERE q.status = 'QUEUED'
ORDER BY q.queue_position ASC
ON CONFLICT (order_id) DO NOTHING;

-- Initial Seed: Populate orders_done from completed orders
INSERT INTO orders_done (order_id, customer_name, product_code, quantity_tons, priority, outcome_status, final_decision, completed_at)
SELECT 
  o.order_id,
  c.customer_name,
  COALESCE(ol.product_id, 'PRD-HRC'),
  COALESCE(ol.requested_qty, 50.0),
  o.priority,
  'COMPLETED',
  'Fulfilled successfully via governed multi-agent consensus',
  COALESCE(q.completed_at, o.updated_at, NOW())
FROM orders o
JOIN order_processing_queue q ON q.order_id = o.order_id
LEFT JOIN customers c ON c.customer_id = o.customer_id
LEFT JOIN LATERAL (
  SELECT product_id, SUM(requested_qty) AS requested_qty 
  FROM order_lines 
  WHERE order_id = o.order_id 
  GROUP BY product_id 
  LIMIT 1
) ol ON true
WHERE q.status = 'COMPLETED'
ON CONFLICT DO NOTHING;
