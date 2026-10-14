"""Shared pytest fixtures.

Integration tests run only when TEST_DATABASE_URL points at a disposable
database whose name contains 'test'. They never target a generic development DB.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent
for extra in (BACKEND_DIR, BACKEND_DIR / "data", BACKEND_DIR / "db"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

from connection import get_database_url, load_project_env  # noqa: E402

load_project_env()

WORKBOOK_PATH = REPO_ROOT / "project_reference" / "enterprise_ai_industrial_dataset_v2.xlsx"


def _is_disposable_test_url(url: str) -> bool:
    dbname = (urlparse(url).path or "").lstrip("/").lower()
    return "test" in dbname


@pytest.fixture(scope="session")
def workbook_path() -> Path:
    return WORKBOOK_PATH


def validate_test_database_url(url: str | None) -> str:
    """Validate that the database URL is explicitly a disposable test database."""
    if not url:
        pytest.skip("TEST_DATABASE_URL is not set; skipping PostgreSQL integration tests")
    if not _is_disposable_test_url(url):
        pytest.fail(
            "SAFETY VIOLATION: TEST_DATABASE_URL database name must contain 'test' so tests cannot "
            f"run against non-test database '{urlparse(url).path}'"
        )
    return url


@pytest.fixture(scope="session")
def test_database_url() -> str:
    url = get_database_url("TEST_DATABASE_URL") or os.environ.get("TEST_DATABASE_URL")
    return validate_test_database_url(url)


@pytest.fixture
def test_conn(test_database_url):
    import psycopg2

    conn = psycopg2.connect(test_database_url)
    conn.autocommit = False
    try:
        yield conn
    finally:
        conn.close()
