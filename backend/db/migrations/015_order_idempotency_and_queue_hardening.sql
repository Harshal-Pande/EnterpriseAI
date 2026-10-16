-- Migration 015: Order Submission Idempotency & Queue Hardening
-- Ensures:
-- 1. Orders table supports unique client idempotency keys to prevent duplicate creation on client retry.
-- 2. Unique constraint on orders_done to ensure completed orders cannot have duplicate records.
-- 3. Stale claim index and max_attempts on order_processing_queue.

-- 1. Add idempotency_key to orders table
ALTER TABLE orders 
  ADD COLUMN IF NOT EXISTS idempotency_key TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_idempotency_key 
  ON orders (idempotency_key) 
  WHERE idempotency_key IS NOT NULL;

-- 2. Add idempotency_key to order_processing_queue
ALTER TABLE order_processing_queue 
  ADD COLUMN IF NOT EXISTS idempotency_key TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_order_proc_queue_idempotency 
  ON order_processing_queue (idempotency_key) 
  WHERE idempotency_key IS NOT NULL;

-- 3. Add max_attempts to order_processing_queue if not exists
ALTER TABLE order_processing_queue 
  ADD COLUMN IF NOT EXISTS max_attempts INTEGER NOT NULL DEFAULT 3;

-- 4. Index for efficient stale claim identification
CREATE INDEX IF NOT EXISTS idx_order_proc_queue_stale_claim 
  ON order_processing_queue (status, claimed_at) 
  WHERE status = 'PROCESSING';

-- 5. Enforce unique order_id on orders_done if table exists
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'orders_done') THEN
    -- Remove any potential duplicates before applying index
    DELETE FROM orders_done a USING (
      SELECT MIN(ctid) as min_ctid, order_id 
      FROM orders_done 
      GROUP BY order_id HAVING COUNT(*) > 1
    ) b 
    WHERE a.order_id = b.order_id AND a.ctid <> b.min_ctid;

    CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_done_unique_order 
      ON orders_done (order_id);
  END IF;
END $$;
