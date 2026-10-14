# Enterprise AI Mesh Backend

Starter FastAPI application plus Phase 1 PostgreSQL schema and seed tooling.

The HTTP API still returns **hardcoded** responses. Phase 1 does **not** connect FastAPI to PostgreSQL.

## Stack
- FastAPI (mock business API + live DB readiness check)
- PostgreSQL connection foundation (ThreadedConnectionPool, `get_db` dependency)
- PostgreSQL schema + seed scripts (Phase 1)
- LangGraph, Neo4j, Web3 (planned; not implemented)

## Running the API
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

- **Liveness probe:** `GET /api/health` -> `200 OK` (independent of database)
- **Readiness probe:** `GET /api/ready` or `GET /api/health/ready` -> executes `SELECT 1` (returns `200 OK` if connected, `503 Service Unavailable` if unavailable)
- **Business endpoints:** (e.g. `/api/orders/`, `/api/audit/`) remain mock-backed in Task 1.

## Phase 1 — schema and seed

The single migration entry point is `backend/db/migrate.py`. `apply_migrations.py` is a thin wrapper that calls the same `main()`.

### 1. Create local databases (once)

PostgreSQL 13+ (tested target: PostgreSQL 18). Use a superuser shell (`psql -U postgres`):

```sql
CREATE USER eas_user WITH PASSWORD 'eas_dev_pass';
CREATE DATABASE eas_dev OWNER eas_user;
CREATE DATABASE eas_test OWNER eas_user;
```

Copy `backend/.env.example` to `backend/.env` and set:

```
DATABASE_URL=postgresql://eas_user:eas_dev_pass@localhost:5432/eas_dev
TEST_DATABASE_URL=postgresql://eas_user:eas_dev_pass@localhost:5432/eas_test
```

Never commit `.env`. Integration tests skip unless the test database name contains `test`.

### 2. Workbook validation (no PostgreSQL)

```bash
python backend/data/inspect_workbook.py
python backend/data/run_validation.py
```

Writes `backend/data/workbook_inspection.json` and `backend/data/workbook_validation_report.json`. Mode is `workbook_only`; `database_queried` is false.

### 3. Apply migrations

```bash
python backend/db/migrate.py --dry-run
python backend/db/migrate.py
```

Dry-run does not CREATE tracking tables or apply SQL. Applied files are tracked in `_schema_migrations` with a SHA-256 checksum. Editing an already-applied file fails instead of being skipped silently.

### 4. Load seed data

```bash
python backend/data/load_seed_data.py --dry-run
python backend/data/load_seed_data.py
```

Uses `column_mappings.py`. Existing rows are skipped (`ON CONFLICT DO NOTHING`), never updated. One transaction per run; any rejected row rolls the run back.

### 5. Database validation (requires a real connection)

```bash
python backend/data/validate_seed_data.py
```

Writes `backend/data/validation_report.json` only after querying PostgreSQL (`database_queried: true`).

### 6. Tests

```bash
python -m pytest backend/tests -c backend/pytest.ini -m "not integration" -v
python -m pytest backend/tests -c backend/pytest.ini -m integration -v
```
