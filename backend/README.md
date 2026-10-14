# Enterprise AI Mesh Backend

Starter FastAPI application plus Phase 1 PostgreSQL schema and seed tooling.

The HTTP API still returns **hardcoded** responses. Phase 1 does **not** connect FastAPI to PostgreSQL.

## Stack
- FastAPI (mock API)
- PostgreSQL schema + seed scripts (Phase 1)
- LangGraph, Neo4j, Web3 (planned; not implemented)

## Running the mock API
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Phase 1 — schema and seed

Requires a local PostgreSQL instance. Copy `.env.example` to `.env` (never commit `.env`).

```bash
# from repository root
python backend/data/inspect_workbook.py
python backend/data/run_validation.py

python backend/db/migrate.py --dry-run
python backend/db/migrate.py
python backend/data/load_seed_data.py --dry-run
python backend/data/load_seed_data.py
python backend/data/validate_seed_data.py

# unit tests (no database)
python -m pytest backend/tests -m "not integration" -v

# integration tests (requires TEST_DATABASE_URL whose database name contains "test")
python -m pytest backend/tests -m integration -v
```

You can run the same Python commands from `backend/` if that directory is the working directory.

Workbook-only validation never needs PostgreSQL. Database validation (`validate_seed_data.py`) fails clearly if `DATABASE_URL` is missing or the server is down, and it will not report success unless a real query ran.
