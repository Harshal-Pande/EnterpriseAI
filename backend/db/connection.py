"""PostgreSQL connection helpers for Phase 1 migration and seed scripts.

Does not connect the FastAPI application. FastAPI remains on mock endpoints
until Phase 2.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent


def load_env_file(path: Path) -> None:
    """Load KEY=VALUE lines into os.environ without overwriting existing vars."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def load_project_env() -> None:
    load_env_file(BACKEND_DIR / ".env")
    load_env_file(REPO_ROOT / ".env")


def get_database_url(env_var: str = "DATABASE_URL") -> Optional[str]:
    load_project_env()
    url = os.environ.get(env_var)
    if url:
        url = url.strip()
    return url or None


def connect(env_var: str = "DATABASE_URL"):
    """Open a psycopg2 connection. Raises SystemExit with a clear message on failure."""
    try:
        import psycopg2
        from psycopg2.extensions import connection as PGConnection
    except ImportError:
        print(
            "ERROR: psycopg2 is not installed. "
            "Install backend dependencies with: pip install -r backend/requirements.txt",
            file=sys.stderr,
        )
        raise SystemExit(2)

    url = get_database_url(env_var)
    if not url:
        print(
            f"ERROR: {env_var} is not set. "
            "Copy backend/.env.example to backend/.env and set the connection string. "
            "Do not commit backend/.env.",
            file=sys.stderr,
        )
        raise SystemExit(2)

    try:
        conn: PGConnection = psycopg2.connect(url)
        conn.autocommit = False
        return conn
    except Exception as exc:  # noqa: BLE001 — surface driver errors clearly
        parsed = urlparse(url)
        host = parsed.hostname or "?"
        port = parsed.port or 5432
        dbname = (parsed.path or "/").lstrip("/") or "?"
        print(
            f"ERROR: PostgreSQL is unavailable using {env_var} "
            f"(host={host} port={port} db={dbname}): {exc}",
            file=sys.stderr,
        )
        raise SystemExit(2)
