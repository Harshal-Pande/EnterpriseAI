#!/bin/sh
set -e

export PYTHONPATH="${PYTHONPATH:-.}"

# Run schema migrations if database is reachable
echo "=== Running PostgreSQL Migrations ==="
python db/migrate.py || echo "[WARN] Migration check failed; continuing to app startup..."

# Seed initial industrial dataset if table is empty
echo "=== Checking & Seeding Operational Data ==="
python data/load_seed_data.py || echo "[WARN] Data seed check failed; continuing to app startup..."

PORT="${PORT:-8000}"
echo "=== Starting Enterprise AI Backend on port ${PORT} ==="
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT}"
