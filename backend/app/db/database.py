"""PostgreSQL database connection foundation for FastAPI application.

Provides connection pooling via psycopg2.pool.ThreadedConnectionPool,
lifespan startup/shutdown management, safe connection acquisition and release,
and readiness check logic. Does not expose credentials to API clients.
"""

from __future__ import annotations

import logging
import threading
from contextlib import contextmanager
from typing import Generator, Optional

from fastapi import HTTPException, status

try:

    from db.connection import get_database_url
except ImportError:
    from backend.db.connection import get_database_url

try:
    import psycopg2
    from psycopg2.extensions import connection as PGConnection
    from psycopg2.pool import PoolError, ThreadedConnectionPool
except ImportError:  # pragma: no cover
    psycopg2 = None
    PGConnection = None
    PoolError = Exception
    ThreadedConnectionPool = None

logger = logging.getLogger("enterpriseai.db")

_pool_lock = threading.Lock()
_pool: Optional[ThreadedConnectionPool] = None


class DatabaseConnectionError(HTTPException):
    """Raised when a database connection cannot be acquired.

    Inherits from HTTPException so FastAPI returns a safe 503 response.
    Never exposes credentials or internal driver details.
    """

    def __init__(self, detail: str = "Database connection unavailable"):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
        )


def init_db_pool(
    database_url: Optional[str] = None,
    minconn: int = 1,
    maxconn: int = 10,
) -> Optional[ThreadedConnectionPool]:
    """Initialize the ThreadedConnectionPool.

    If the database is unreachable or DATABASE_URL is unset, logs a warning
    and leaves the pool uninitialized so application startup is not blocked.
    """
    global _pool
    with _pool_lock:
        if _pool is not None:
            return _pool

        url = database_url or get_database_url("DATABASE_URL")
        if not url:
            logger.warning("DATABASE_URL is not configured; database pool not initialized.")
            return None

        if ThreadedConnectionPool is None:  # pragma: no cover
            logger.error("psycopg2 is not installed; database pool cannot be created.")
            return None

        try:
            pool = ThreadedConnectionPool(minconn, maxconn, dsn=url)
            _pool = pool
            logger.info("PostgreSQL connection pool initialized (min=%d, max=%d).", minconn, maxconn)
            return _pool
        except Exception as exc:
            # Do not crash the application on startup if DB is down; log safe summary without credentials
            logger.warning("Failed to initialize database pool: %s", type(exc).__name__)
            return None


def close_db_pool() -> None:
    """Close all connections in the pool and reset pool state."""
    global _pool
    with _pool_lock:
        if _pool is not None:
            try:
                _pool.closeall()
                logger.info("PostgreSQL connection pool closed.")
            except Exception as exc:  # pragma: no cover
                logger.warning("Error closing database pool: %s", exc)
            finally:
                _pool = None


def get_db_pool() -> Optional[ThreadedConnectionPool]:
    """Return the active connection pool, if initialized."""
    with _pool_lock:
        return _pool


def set_db_pool(pool: Optional[ThreadedConnectionPool]) -> None:
    """Explicitly set or replace the connection pool (primarily for testing)."""
    global _pool
    with _pool_lock:
        _pool = pool


def acquire_connection() -> PGConnection:
    """Acquire a connection from the pool.

    Attempts lazy initialization if pool is not yet created.
    Never returns None; raises DatabaseConnectionError on failure.
    """
    pool = get_db_pool()
    if pool is None:
        pool = init_db_pool()

    if pool is None:
        raise DatabaseConnectionError("Database is not configured or unavailable")

    try:
        conn = pool.getconn()
        if conn is None:  # pragma: no cover
            raise DatabaseConnectionError("Pool returned empty connection")
        if conn.closed:
            pool.putconn(conn, close=True)
            conn = pool.getconn()
        return conn
    except PoolError as exc:
        logger.error("Connection pool exhausted: %s", exc)
        raise DatabaseConnectionError("Database connection pool exhausted") from exc
    except Exception as exc:
        logger.error("Failed to acquire connection: %s", type(exc).__name__)
        raise DatabaseConnectionError("Database connection unavailable") from exc


def release_connection(conn: Optional[PGConnection]) -> None:
    """Safely rollback uncommitted transactions and return connection to pool."""
    if conn is None:
        return

    pool = get_db_pool()
    try:
        if not conn.closed:
            conn.rollback()
    except Exception as exc:  # pragma: no cover
        logger.warning("Error rolling back connection before release: %s", exc)

    if pool is not None:
        try:
            pool.putconn(conn, close=conn.closed)
        except Exception as exc:  # pragma: no cover
            logger.warning("Error returning connection to pool: %s", exc)
            try:
                conn.close()
            except Exception:
                pass
    else:
        try:
            conn.close()
        except Exception:
            pass


@contextmanager
def get_db_connection() -> Generator[PGConnection, None, None]:
    """Context manager for acquiring and safely releasing a connection.

    Guarantees rollback and release even if the enclosed block raises an exception.
    """
    conn = acquire_connection()
    try:
        yield conn
    finally:
        release_connection(conn)


def get_db() -> Generator[PGConnection, None, None]:
    """FastAPI dependency yielding a managed PostgreSQL connection.

    Usage in FastAPI routes:
        @router.get("/example")
        def example_route(conn: PGConnection = Depends(get_db)):
            ...

    Never silently returns None.
    Rolls back any uncommitted work and returns the connection to the pool upon exit.
    """
    with get_db_connection() as conn:
        yield conn


def check_db_readiness() -> tuple[bool, str]:
    """Verify live PostgreSQL connectivity by running a real SELECT 1 query.

    Returns:
        (True, 'connected') if query succeeds.
        (False, 'unavailable') on any error, without exposing sensitive details.
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                row = cur.fetchone()
                if row and row[0] == 1:
                    return True, "connected"
                return False, "unexpected response"
    except Exception as exc:
        logger.debug("Database readiness check failed: %s", exc)
        return False, "unavailable"
