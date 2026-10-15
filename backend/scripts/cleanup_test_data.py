import os
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(REPO_ROOT / ".env")
load_dotenv(REPO_ROOT / "backend" / ".env")

db_url = os.environ.get("TEST_DATABASE_URL")
if not db_url or "test" not in db_url.lower():
    raise RuntimeError("Target is not a valid test database")

conn = psycopg2.connect(db_url)
with conn.cursor() as cur:
    cur.execute("DELETE FROM inventory_movements WHERE reference_id IN ('ORD-TEST-LIFECYCLE', 'ORD-TEST-RESERVATION-REL') OR notes LIKE '%ORD-TEST%';")
    cur.execute("DELETE FROM stock_reservations WHERE reference_id IN ('ORD-TEST-LIFECYCLE', 'ORD-TEST-RESERVATION-REL');")
    cur.execute("DELETE FROM orders WHERE order_id IN ('ORD-TEST-LIFECYCLE', 'ORD-TEST-RESERVATION-REL');")
    cur.execute("DELETE FROM blockchain_anchors WHERE anchor_id IS NOT NULL;")
    cur.execute("DELETE FROM event_log WHERE event_id IS NOT NULL;")
    conn.commit()
print("Cleanup of test orders, anchors, and event_log complete.")
conn.close()
