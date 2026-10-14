# Enterprise AI Mesh Backend

FastAPI application providing PostgreSQL-backed operational APIs, multi-agent workflow orchestration, deterministic policy governance, and persistent scenario scheduling.

---

## Architecture & Capabilities

- **PostgreSQL Connection Foundation**: ThreadedConnectionPool with connection lifecycle management, health probes (`/api/health`, `/api/live`), and safe error handling.
- **Operational Data APIs**: PostgreSQL-backed endpoints querying validated operational tables:
  - `GET /api/orders/`, `GET /api/orders/summary`, `GET /api/orders/{id}`
  - `GET /api/inventory/items`, `GET /api/inventory/summary`
  - `GET /api/suppliers/`, `GET /api/suppliers/{id}`
- **Workflow & Agent Persistence**: State transitions persisted in `scenario_instances` and `agent_runs` (`/api/workflow/`, `/api/agents/`).
- **Persistent Five-Minute Scenario Engine**: Recurring 300-second execution cycle (`/api/scheduler/`):
  - Distributed PostgreSQL lease locking (`scheduler_state`) with stale lock recovery.
  - Active renewal heartbeat to prevent lease expiration during agent execution.
  - Deterministic slot idempotency (`SCHED-<template>-SLOT-<ts>`) and safe handling of concurrent retries.
  - Watchdog recovery of orphaned `QUEUED`/`RUNNING` workflows after worker interruption.
  - Queue capacity limits (`SCHEDULER_MAX_OPEN_SCENARIOS`) with administrative override restricted to `ADMIN`.
- **Policy & Approval Engine**: Server-side deterministic policy evaluation and human-in-the-loop approval workflows (`/api/policies/`, `/api/approvals/`).
- **Controlled Action Execution**: Simulation adapter recording proposals and simulated executions (`/api/actions/`). Note: Physical ERP/warehouse execution is simulated.
- **Cryptographic Audit Log**: Canonical SHA-256 payload hashing and tamper-evident event logging in `event_log` (`/api/audit/`). Note: Polygon blockchain anchoring calculates real state roots and Merkle verification locally.
- **Security & Authorization**: Server-side credential validation with least-privilege role hierarchy (`ADMIN`, `FINANCE_APPROVER`, `SUPPLY_CHAIN_APPROVER`, `OPERATOR`, `VIEWER`). Fails closed in production mode.

---

## Local Setup & Execution

### 1. Requirements
- Python 3.10+
- PostgreSQL 13+

### 2. Environment Configuration
Create a `.env` file in `backend/` (or set environment variables):

```env
DATABASE_URL=postgresql://eas_user:eas_dev_pass@localhost:5432/eas_dev
TEST_DATABASE_URL=postgresql://eas_user:eas_dev_pass@localhost:5432/eas_test
APP_ENVIRONMENT=development
SCHEDULER_ENABLED=false
```

### 3. Migrations & Seed Data
```bash
# Apply schema migrations (001_core, 002_runtime, 003_workflow)
python db/migrate.py

# Load operational seed data (1,327 source rows)
python data/load_seed_data.py

# Verify operational database consistency (119 checks)
python data/validate_seed_data.py --database-url-var DATABASE_URL
```

### 4. Running the API
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

- **Health Probe**: `GET /api/health`
- **Live Readiness Probe**: `GET /api/live`
- **Interactive Documentation**: `http://localhost:8000/docs`

### 5. Running Tests
```bash
# Fast unit & integration tests:
pytest -q

# Specific test suites:
pytest backend/tests/test_scheduler.py -v
pytest backend/tests/test_security.py -v
pytest backend/tests/test_e2e_lifecycle.py -v
```
