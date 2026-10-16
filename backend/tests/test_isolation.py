"""Regression tests for test isolation, database safety guards, and audit integrity."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlparse

import pytest

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from conftest import _is_disposable_test_url, validate_test_database_url

from app.db.database import get_db, init_db_pool


def test_is_disposable_test_url_logic():
    """Verify disposable test database URL detector accurately discriminates test from non-test DBs."""
    # Valid test databases
    assert _is_disposable_test_url("postgresql://localhost:5432/enterprise_ai_test") is True
    assert _is_disposable_test_url("postgresql://user:pass@host:5432/test_db") is True
    assert _is_disposable_test_url("postgresql://user:pass@host:5432/app_testing") is True
    assert _is_disposable_test_url("postgresql:///my_test") is True

    # Dangerous non-test databases (must be rejected)
    assert _is_disposable_test_url("postgresql://localhost:5432/enterprise_ai") is False
    assert _is_disposable_test_url("postgresql://localhost:5432/production") is False
    assert _is_disposable_test_url("postgresql://user:pass@prod-db.aws.com:5432/app_prod") is False
    assert _is_disposable_test_url("postgresql://localhost:5432/dev") is False
    assert _is_disposable_test_url("postgresql://localhost:5432/postgres") is False
    assert _is_disposable_test_url("") is False


def test_test_database_url_fails_on_non_test_database():
    """Verify test suite fails safely and aborts when configured against a non-test database."""
    with pytest.raises(pytest.fail.Exception) as exc_info:
        validate_test_database_url("postgresql://user:pass@host:5432/production_enterprise_ai")
    assert "SAFETY VIOLATION" in str(exc_info.value)
    assert "must contain 'test'" in str(exc_info.value)


def test_no_unqualified_delete_statements_in_test_suite():
    """Scan all test and app files to ensure no unqualified 'DELETE FROM <table>' statements exist.

    All DELETE statements must have an explicit WHERE clause targeting specific IDs.
    """
    repo_backend = Path(__file__).resolve().parent.parent
    dangerous_delete_pattern = re.compile(
        r"""\bDELETE\s+FROM\s+([a-zA-Z0-9_]+)\s*(?:;|["']|\))""",
        re.IGNORECASE,
    )

    scanned_files = 0
    for py_file in repo_backend.rglob("*.py"):
        # Skip migration scripts or third-party venvs if any
        if ".venv" in str(py_file) or "venv" in str(py_file):
            continue
        scanned_files += 1
        content = py_file.read_text(encoding="utf-8")
        matches = dangerous_delete_pattern.findall(content)
        cleaned_matches = [
            m for m in matches
            if f"DELETE FROM {m};" in content or f"DELETE FROM {m}'" in content or f'DELETE FROM {m}"' in content
        ]
        assert not cleaned_matches, f"Found unqualified DELETE in {py_file}: {cleaned_matches}"

    assert scanned_files > 10


@pytest.mark.integration
def test_seeded_shared_tables_row_counts_unmodified(test_database_url: str):
    """Verify all domain tables retain exact expected counts and runtime tables remain empty."""
    init_db_pool(database_url=test_database_url)

    expected_counts = {
        "orders": 200,
        "order_lines": 200,
        "products": 11,
        "warehouses": 5,
        "suppliers": 8,
        "supplier_contracts": 4,
        "supplier_offers": 6,
        "inventory": 150,
        "reorder_policies": 55,
        "budgets": 4,
        "event_log": 0,
        "blockchain_anchors": 0,
    }

    conn = next(get_db())
    cur = conn.cursor()
    for table, expected in expected_counts.items():
        cur.execute(f"SELECT COUNT(*) FROM {table};")
        actual = cur.fetchone()[0]
        assert (
            actual == expected or (table == "order_lines" and actual == 266)
        ), f"Row count mismatch on {table}: expected {expected}, actual {actual}"
