"""Check inventory table schema."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from db.connection import load_project_env, connect

load_project_env()
conn = connect("TEST_DATABASE_URL")
with conn.cursor() as cur:
    cur.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'inventory'
        ORDER BY ordinal_position;
    """)
    for r in cur.fetchall():
        print(f"  {r[0]}: {r[1]}")
conn.close()
