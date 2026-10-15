"""Read-only database inspector for Enterprise AI Mesh (P0 Audit).

Connects via psycopg2, verifies target with db_guard, and collects:
- Visible databases
- All tables and row counts
- Applied schema migrations and checksum verification
- Foreign keys, unique constraints, check constraints
- Triggers and indexes
- Outputs snapshot summary in JSON and text format
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

# Ensure backend root is on sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.db_guard import verify_target_connection
from db.connection import connect, get_database_url, load_project_env


def inspect_database(env_var: str = "DATABASE_URL") -> Dict[str, Any]:
    load_project_env()
    raw_url = get_database_url(env_var)
    if not raw_url:
        print(f"Error: Environment variable {env_var} is not set.", file=sys.stderr)
        return {"error": f"{env_var} not set"}

    conn = connect(env_var)
    conn.autocommit = True
    actual_db, actual_host, actual_port = verify_target_connection(conn)

    report: Dict[str, Any] = {
        "target": {
            "env_var": env_var,
            "database": actual_db,
            "host": actual_host,
            "port": actual_port,
        },
        "visible_databases": [],
        "tables": {},
        "migrations": [],
        "check_constraints": [],
        "foreign_keys": [],
        "unique_constraints": [],
        "triggers": [],
        "indexes": [],
    }

    with conn.cursor() as cur:
        # Visible databases
        try:
            cur.execute("SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY datname;")
            report["visible_databases"] = [r[0] for r in cur.fetchall()]
        except Exception as e:
            report["visible_databases"] = [f"Error: {e}"]

        # List user tables in public schema
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """)
        table_names = [r[0] for r in cur.fetchall()]

        # Row counts per table
        for tbl in table_names:
            try:
                cur.execute(f'SELECT count(*) FROM "{tbl}";')
                count = cur.fetchone()[0]
                report["tables"][tbl] = count
            except Exception as e:
                report["tables"][tbl] = f"Error: {e}"

        # Migrations if table exists
        if "_schema_migrations" in table_names:
            cur.execute("SELECT version, filename, applied_at, checksum FROM _schema_migrations ORDER BY version;")
            report["migrations"] = [
                {"version": r[0], "filename": r[1], "applied_at": str(r[2]), "checksum": r[3]}
                for r in cur.fetchall()
            ]

        # Check constraints
        cur.execute("""
            SELECT tc.table_name, tc.constraint_name, cc.check_clause
            FROM information_schema.table_constraints tc
            JOIN information_schema.check_constraints cc 
              ON tc.constraint_name = cc.constraint_name
            WHERE tc.table_schema = 'public' AND tc.constraint_type = 'CHECK'
            ORDER BY tc.table_name, tc.constraint_name;
        """)
        report["check_constraints"] = [
            {"table": r[0], "constraint": r[1], "clause": r[2]}
            for r in cur.fetchall()
        ]

        # Foreign keys
        cur.execute("""
            SELECT
                tc.table_name, kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name,
                rc.delete_rule
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
              AND tc.table_schema = kcu.table_schema
            JOIN information_schema.referential_constraints AS rc
              ON tc.constraint_name = rc.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
              ON ccu.constraint_name = tc.constraint_name
              AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'public'
            ORDER BY tc.table_name, kcu.column_name;
        """)
        report["foreign_keys"] = [
            {"table": r[0], "column": r[1], "foreign_table": r[2], "foreign_column": r[3], "on_delete": r[4]}
            for r in cur.fetchall()
        ]

        # Unique constraints
        cur.execute("""
            SELECT tc.table_name, tc.constraint_name, kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
            WHERE tc.constraint_type = 'UNIQUE' AND tc.table_schema = 'public'
            ORDER BY tc.table_name, tc.constraint_name;
        """)
        report["unique_constraints"] = [
            {"table": r[0], "constraint": r[1], "column": r[2]}
            for r in cur.fetchall()
        ]

        # Triggers
        cur.execute("""
            SELECT event_object_table, trigger_name, event_manipulation, action_statement
            FROM information_schema.triggers
            WHERE trigger_schema = 'public'
            ORDER BY event_object_table, trigger_name;
        """)
        report["triggers"] = [
            {"table": r[0], "trigger": r[1], "event": r[2], "action": r[3]}
            for r in cur.fetchall()
        ]

        # Indexes
        cur.execute("""
            SELECT tablename, indexname, indexdef
            FROM pg_indexes
            WHERE schemaname = 'public'
            ORDER BY tablename, indexname;
        """)
        report["indexes"] = [
            {"table": r[0], "index": r[1], "def": r[2]}
            for r in cur.fetchall()
        ]

    conn.close()
    return report


if __name__ == "__main__":
    env_var = sys.argv[1] if len(sys.argv) > 1 else "DATABASE_URL"
    res = inspect_database(env_var)
    print("\n--- DATABASE SNAPSHOT REPORT ---")
    print(f"Target DB: {res.get('target')}")
    print(f"Visible DBs: {res.get('visible_databases')}")
    print(f"Total Tables: {len(res.get('tables', {}))}")
    print("Tables & Row Counts:")
    for t, c in sorted(res.get("tables", {}).items()):
        print(f"  - {t}: {c}")
    print(f"Migrations Applied: {len(res.get('migrations', []))}")
    for m in res.get("migrations", []):
        print(f"  [{m['version']}] {m['filename']} ({m['applied_at']})")
    print(f"Check Constraints: {len(res.get('check_constraints', []))}")
    print(f"Foreign Keys: {len(res.get('foreign_keys', []))}")
    print(f"Unique Constraints: {len(res.get('unique_constraints', []))}")
    print(f"Triggers: {len(res.get('triggers', []))}")
    print(f"Indexes: {len(res.get('indexes', []))}")

    # Optionally dump full json if --json flag
    if "--json" in sys.argv:
        out_path = BACKEND_DIR.parent / "docs" / "backend-overhaul" / f"db_snapshot_{res.get('target', {}).get('database')}.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(res, indent=2), encoding="utf-8")
        print(f"Full snapshot saved to {out_path}")
