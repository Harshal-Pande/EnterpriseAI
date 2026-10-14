"""Lightweight versioned SQL migration runner.

Usage (from repository root or backend/):
    python backend/db/migrate.py --dry-run
    python backend/db/migrate.py
    python backend/db/migrate.py --database-url-var TEST_DATABASE_URL

Never drops or resets an existing database. Repeated runs skip applied versions.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from connection import connect, get_database_url  # noqa: E402

MIGRATIONS_DIR = _HERE / "migrations"
TRACKING_TABLE = "_schema_migrations"


def list_migration_files() -> list[Path]:
    if not MIGRATIONS_DIR.is_dir():
        return []
    return sorted(p for p in MIGRATIONS_DIR.glob("*.sql") if p.is_file())


def checksum_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ensure_tracking_table(cur) -> None:
    cur.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {TRACKING_TABLE} (
            version TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            checksum TEXT NOT NULL,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    cur.execute(
        f"ALTER TABLE {TRACKING_TABLE} ADD COLUMN IF NOT EXISTS checksum TEXT"
    )


def applied_records(cur) -> dict[str, str]:
    """Return {version: checksum} for applied migrations. Missing checksum → empty string."""
    cur.execute(
        f"SELECT version, COALESCE(checksum, '') FROM {TRACKING_TABLE}"
    )
    return {row[0]: row[1] for row in cur.fetchall()}


def version_of(path: Path) -> str:
    return path.stem


def run(dry_run: bool = False, env_var: str = "DATABASE_URL") -> int:
    files = list_migration_files()
    if not files:
        print(f"No SQL files found in {MIGRATIONS_DIR}")
        return 0

    print(f"Found {len(files)} migration file(s) in {MIGRATIONS_DIR}:")
    for path in files:
        print(f"  - {path.name}")

    url = get_database_url(env_var)
    if dry_run and not url:
        print(
            f"\nDRY-RUN: {env_var} is not set. Listing local files only; "
            "cannot determine which versions are already applied."
        )
        print("Pending (unknown applied set):")
        for path in files:
            print(f"  PENDING  {path.name}")
        return 0

    conn = connect(env_var)
    applied: dict[str, str] = {}
    try:
        if dry_run:
            # Do not CREATE/ALTER tracking tables during dry-run.
            try:
                with conn.cursor() as cur:
                    applied = applied_records(cur)
                conn.rollback()
            except Exception:
                conn.rollback()
                applied = {}
                print(
                    "DRY-RUN: tracking table not present; treating all files as pending."
                )
        else:
            with conn.cursor() as cur:
                ensure_tracking_table(cur)
            conn.commit()
            with conn.cursor() as cur:
                applied = applied_records(cur)
    except Exception:
        conn.rollback()
        conn.close()
        raise

    checksum_errors = []
    pending = []
    skipped = []
    for path in files:
        ver = version_of(path)
        current = checksum_of(path)
        if ver in applied:
            stored = applied[ver]
            if stored and stored != current:
                checksum_errors.append(
                    f"{path.name}: applied checksum {stored} != file checksum {current}"
                )
            skipped.append(path)
        else:
            pending.append(path)

    if checksum_errors:
        print("ERROR: applied migration file(s) have changed on disk:", file=sys.stderr)
        for msg in checksum_errors:
            print(f"  {msg}", file=sys.stderr)
        print(
            "Refusing to skip or re-apply a modified migration. "
            "Add a new numbered SQL file instead of editing an applied one.",
            file=sys.stderr,
        )
        conn.close()
        return 1

    if dry_run:
        print("\nDRY-RUN: no SQL will be executed.")
        for path in skipped:
            print(f"  SKIP     {path.name} (already applied, checksum match)")
        for path in pending:
            print(f"  APPLY    {path.name}  checksum={checksum_of(path)[:12]}…")
        if not pending:
            print("  (nothing pending)")
        conn.close()
        return 0

    try:
        for path in skipped:
            print(f"SKIP  {path.name} (already applied, checksum match)")

        if not pending:
            print("No pending migrations.")
            return 0

        for path in pending:
            sql = path.read_text(encoding="utf-8")
            digest = checksum_of(path)
            print(f"APPLY {path.name} ...")
            try:
                with conn.cursor() as cur:
                    cur.execute(sql)
                    cur.execute(
                        f"INSERT INTO {TRACKING_TABLE} (version, filename, checksum) "
                        f"VALUES (%s, %s, %s)",
                        (version_of(path), path.name, digest),
                    )
                conn.commit()
                print(f"  OK    {path.name} checksum={digest[:12]}…")
            except Exception as exc:  # noqa: BLE001
                conn.rollback()
                print(f"  FAIL  {path.name}: {exc}", file=sys.stderr)
                return 1
        return 0
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply versioned SQL migrations.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List pending migrations without executing SQL.",
    )
    parser.add_argument(
        "--database-url-var",
        default="DATABASE_URL",
        help="Environment variable holding the PostgreSQL URL (default: DATABASE_URL).",
    )
    args = parser.parse_args()
    raise SystemExit(run(dry_run=args.dry_run, env_var=args.database_url_var))


if __name__ == "__main__":
    main()
