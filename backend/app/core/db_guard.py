"""Database safety harness and target database guard for Enterprise AI Mesh.

Enforces Safeguard 1.1:
1. Target check: Prints ONLY database name, host, and port (never secrets or full DSN).
2. Prevents destructive SQL (DROP, TRUNCATE, DELETE without tagged WHERE, ALTER DROP COLUMN)
   unless explicitly targeting a database matching *_disposable_test with APP_ENVIRONMENT=test.
3. Distinguishes operational/demo databases from disposable test databases.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger("enterpriseai.db_guard")

# Regex patterns for destructive statements
DESTRUCTIVE_PATTERNS = [
    (re.compile(r"\bDROP\s+DATABASE\b", re.IGNORECASE), "DROP DATABASE"),
    (re.compile(r"\bDROP\s+SCHEMA\b", re.IGNORECASE), "DROP SCHEMA"),
    (re.compile(r"\bDROP\s+TABLE\b", re.IGNORECASE), "DROP TABLE"),
    (re.compile(r"\bTRUNCATE\b", re.IGNORECASE), "TRUNCATE"),
    (re.compile(r"\bALTER\s+TABLE\b.*\bDROP\s+COLUMN\b", re.IGNORECASE), "ALTER TABLE DROP COLUMN"),
]

DELETE_PATTERN = re.compile(r"\bDELETE\s+FROM\b", re.IGNORECASE)
WHERE_PATTERN = re.compile(r"\bWHERE\b", re.IGNORECASE)


class DatabaseGuardViolation(RuntimeError):
    """Raised when an operation violates database safety safeguards."""
    pass


def parse_safe_target_info(dsn_or_url: str) -> Dict[str, Any]:
    """Parse DSN or postgres URL and return ONLY safe fields (host, port, dbname).
    
    Never returns user, password, or full URL.
    """
    if not dsn_or_url:
        return {"host": None, "port": None, "dbname": None}
    
    if "://" in dsn_or_url:
        parsed = urlparse(dsn_or_url)
        return {
            "host": parsed.hostname or "localhost",
            "port": parsed.port or 5432,
            "dbname": (parsed.path or "/").lstrip("/") or None,
        }
    
    info: Dict[str, Any] = {"host": "localhost", "port": 5432, "dbname": None}
    for part in dsn_or_url.split():
        if "=" in part:
            k, v = part.split("=", 1)
            k = k.strip().lower()
            v = v.strip().strip("'").strip('"')
            if k in ("host", "hostaddr"):
                info["host"] = v
            elif k == "port":
                try:
                    info["port"] = int(v)
                except ValueError:
                    info["port"] = 5432
            elif k in ("dbname", "database"):
                info["dbname"] = v
    return info


def format_safe_target(info: Dict[str, Any]) -> str:
    """Format safe connection info for logging/display."""
    return f"database='{info.get('dbname')}' host='{info.get('host')}' port={info.get('port')}"


def is_disposable_test_db(dbname: Optional[str]) -> bool:
    """Check if the database is explicitly a disposable test database."""
    if not dbname:
        return False
    name = dbname.strip().lower()
    return name.endswith("_disposable_test") or name == "enterprise_ai_disposable_test"


def check_sql_safety(sql: str, dbname: Optional[str] = None, app_env: Optional[str] = None) -> None:
    """Validate that SQL does not contain forbidden destructive commands.
    
    Allowed only if dbname matches *_disposable_test AND APP_ENVIRONMENT=test.
    """
    env = (app_env or os.environ.get("APP_ENVIRONMENT", "")).strip().lower()
    is_safe_test_target = is_disposable_test_db(dbname) and env == "test"

    for pattern, name in DESTRUCTIVE_PATTERNS:
        if pattern.search(sql):
            if not is_safe_test_target:
                raise DatabaseGuardViolation(
                    f"GUARD REFUSAL: Destructive SQL '{name}' is forbidden against database '{dbname}' "
                    f"in environment '{env}'. Destructive SQL is permitted ONLY against *_disposable_test with APP_ENVIRONMENT=test."
                )

    if DELETE_PATTERN.search(sql) and not WHERE_PATTERN.search(sql):
        if not is_safe_test_target:
            raise DatabaseGuardViolation(
                f"GUARD REFUSAL: Unconstrained 'DELETE FROM' without WHERE is forbidden against database '{dbname}' "
                f"in environment '{env}'."
            )


def verify_target_connection(
    conn: Any,
    expected_dbname: Optional[str] = None,
    require_disposable: bool = False,
) -> Tuple[str, str, int]:
    """Execute a target check on an active psycopg2 connection.
    
    Queries `current_database()`, `inet_server_addr()`, `inet_server_port()`.
    Prints safe details and raises DatabaseGuardViolation if safety rules fail.
    """
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT current_database(), coalesce(inet_server_addr()::text, 'local'), coalesce(inet_server_port(), 5432)"
        )
        row = cursor.fetchone()
        actual_db, actual_host, actual_port = row[0], row[1], row[2]
    finally:
        cursor.close()

    safe_summary = f"TARGET CHECK: database='{actual_db}' host='{actual_host}' port={actual_port}"
    print(safe_summary)
    logger.info(safe_summary)

    if expected_dbname and actual_db.lower() != expected_dbname.lower():
        raise DatabaseGuardViolation(
            f"GUARD REFUSAL: Target database mismatch. Expected '{expected_dbname}', but connected to '{actual_db}'."
        )

    if require_disposable and not is_disposable_test_db(actual_db):
        raise DatabaseGuardViolation(
            f"GUARD REFUSAL: Operation requires a disposable test database (*_disposable_test), "
            f"but connected to '{actual_db}'."
        )

    return str(actual_db), str(actual_host), int(actual_port)
