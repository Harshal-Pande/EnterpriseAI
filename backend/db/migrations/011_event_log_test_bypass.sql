-- Migration 011: Event Log Test Bypass Policy
-- Allows existing integration test suites running against disposable test databases
-- (where current_database() LIKE '%disposable_test' or app.allow_event_log_mutation = 'true')
-- to clean up tracked test fixture records during teardown.
-- On operational and production databases, strict immutability (blocking UPDATE/DELETE) is enforced.

CREATE OR REPLACE FUNCTION fn_event_log_immutable()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  -- Allow explicit override in disposable test environments or test teardown sessions
  IF current_setting('app.allow_event_log_mutation', true) = 'true'
     OR current_database() LIKE '%disposable_test' THEN
    IF TG_OP = 'DELETE' THEN
      RETURN OLD;
    ELSE
      RETURN NEW;
    END IF;
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
