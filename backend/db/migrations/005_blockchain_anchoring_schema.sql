-- Phase 7: Real Blockchain Audit Anchoring Schema Hardening.
-- Adds columns for receipt verification, confirmed timestamp, gas metrics, and indexes.

ALTER TABLE blockchain_anchors 
  ADD COLUMN IF NOT EXISTS confirmed_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS receipt_status INTEGER,
  ADD COLUMN IF NOT EXISTS gas_used BIGINT,
  ADD COLUMN IF NOT EXISTS retry_count INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS explorer_url TEXT;

CREATE INDEX IF NOT EXISTS idx_blockchain_anchors_event_id 
  ON blockchain_anchors (event_id_or_batch_id);

CREATE INDEX IF NOT EXISTS idx_blockchain_anchors_payload_hash 
  ON blockchain_anchors (payload_hash);

CREATE INDEX IF NOT EXISTS idx_blockchain_anchors_tx_hash 
  ON blockchain_anchors (transaction_hash);

CREATE INDEX IF NOT EXISTS idx_blockchain_anchors_confirmation 
  ON blockchain_anchors (confirmation_status);
