"""Migration runner tests."""

import os
from pathlib import Path

import pytest

from migrate import checksum_of, list_migration_files, run, version_of

BACKEND_DIR = Path(__file__).resolve().parent.parent


def test_migration_files_are_ordered():
    files = list_migration_files()
    names = [p.name for p in files]
    assert names[0] == "001_operational_schema.sql"
    assert names[1] == "002_runtime_schema.sql"
    assert names == sorted(names)
    assert version_of(files[0]) == "001_operational_schema"


def test_dry_run_without_database_url(monkeypatch, capsys):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    # Ensure connection helper does not pick up a leftover .env value for this test
    monkeypatch.setenv("DATABASE_URL", "")
    code = run(dry_run=True, env_var="DATABASE_URL_UNSET_FOR_TEST")
    captured = capsys.readouterr()
    assert code == 0
    assert "001_operational_schema.sql" in captured.out
    assert "DRY-RUN" in captured.out


def test_migration_checksums_are_stable_and_distinct():
    files = list_migration_files()
    digests = [checksum_of(p) for p in files]
    assert len(digests) == len(set(digests))
    assert all(len(d) == 64 for d in digests)
    assert checksum_of(files[0]) == checksum_of(files[0])


def test_apply_without_database_url_fails(monkeypatch):
    monkeypatch.delenv("DATABASE_URL_UNSET_FOR_TEST", raising=False)
    with pytest.raises(SystemExit) as exc:
        run(dry_run=False, env_var="DATABASE_URL_UNSET_FOR_TEST")
    assert exc.value.code == 2


@pytest.mark.integration
def test_migrations_apply_twice(test_database_url, monkeypatch):
    monkeypatch.setenv("TEST_DATABASE_URL", test_database_url)
    assert run(dry_run=True, env_var="TEST_DATABASE_URL") == 0
    assert run(dry_run=False, env_var="TEST_DATABASE_URL") == 0
    assert run(dry_run=False, env_var="TEST_DATABASE_URL") == 0

    import psycopg2

    conn = psycopg2.connect(test_database_url)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT version FROM _schema_migrations ORDER BY version")
            versions = [row[0] for row in cur.fetchall()]
            assert "001_operational_schema" in versions
            assert "002_runtime_schema" in versions
            cur.execute(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = 'orders'"
            )
            assert cur.fetchone()[0] == 1
    finally:
        conn.close()
    # silence unused import if flake8 in editor
    assert os.environ.get("TEST_DATABASE_URL")
