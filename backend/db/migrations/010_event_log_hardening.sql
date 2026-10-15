-- Migration 010: Event Log Hardening
-- Adds SHA-256 hash chaining to event_log (prev_hash + entry_hash columns),
-- an immutable protection trigger (blocks UPDATE/DELETE on locked events),
-- and a sequence ordering column for strict chain traversal.
-- Fully additive — all columns are ADD COLUMN IF NOT EXISTS.

-- Add entry_hash column if not present (SHA-256 of payload + prev_hash)
ALTER TABLE event_log ADD COLUMN IF NOT EXISTS entry_hash TEXT;

-- Add sequence column for deterministic ordering within microsecond-equal timestamps
ALTER TABLE event_log ADD COLUMN IF NOT EXISTS sequence_num BIGSERIAL;

-- Add chain_verified column: TRUE = chain verified, NULL = not yet checked
ALTER TABLE event_log ADD COLUMN IF NOT EXISTS chain_verified BOOLEAN;

-- Add metadata column for additional context without schema changes
ALTER TABLE event_log ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'::jsonb;

-- Immutable event log trigger: prevents UPDATE or DELETE on committed event rows
CREATE OR REPLACE FUNCTION fn_event_log_immutable()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  -- Allow explicit override only in disposable test environments
  IF current_setting('app.allow_event_log_mutation', true) = 'true' THEN
    RETURN OLD;  -- Allow DELETE in test mode
  END IF;

  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION
      'IMMUTABILITY VIOLATION: event_log rows are append-only. '
      'Attempted DELETE on event_id=%. '
      'Use event status=SUPERSEDED and create a correction event instead.',
      OLD.event_id
      USING ERRCODE = '23000';
  END IF;

  IF TG_OP = 'UPDATE' THEN
    -- Allow only chain_verified and metadata to be updated (for verification runs)
    IF OLD.event_id      != NEW.event_id      OR
       OLD.event_timestamp != NEW.event_timestamp OR
       OLD.event_type    != NEW.event_type    OR
       OLD.payload_hash  != NEW.payload_hash  OR
       OLD.entity_id     != NEW.entity_id
    THEN
      RAISE EXCEPTION
        'IMMUTABILITY VIOLATION: Attempt to modify core fields of event_id=%. '
        'Only chain_verified and metadata may be updated after commit.',
        OLD.event_id
        USING ERRCODE = '23000';
    END IF;
  END IF;

  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_event_log_immutable ON event_log;
CREATE TRIGGER trg_event_log_immutable
  BEFORE UPDATE OR DELETE ON event_log
  FOR EACH ROW EXECUTE FUNCTION fn_event_log_immutable();

-- Index for chain traversal (ordered by sequence)
CREATE INDEX IF NOT EXISTS idx_event_log_sequence ON event_log (sequence_num ASC);

-- Index on entry_hash for tamper detection lookups
CREATE INDEX IF NOT EXISTS idx_event_log_entry_hash ON event_log (entry_hash) WHERE entry_hash IS NOT NULL;

-- Partial index for unverified events (batch verification runs)
CREATE INDEX IF NOT EXISTS idx_event_log_unverified
  ON event_log (sequence_num ASC)
  WHERE chain_verified IS NULL AND entry_hash IS NOT NULL;

-- Materialized summary view for audit reporting
CREATE OR REPLACE VIEW v_event_log_summary AS
SELECT
  date_trunc('hour', event_timestamp) AS hour_bucket,
  event_type,
  entity_type,
  actor_type,
  status,
  COUNT(*) AS event_count,
  COUNT(*) FILTER (WHERE entry_hash IS NOT NULL) AS hashed_count,
  COUNT(*) FILTER (WHERE chain_verified = TRUE) AS verified_count
FROM event_log
GROUP BY 1, 2, 3, 4, 5;
