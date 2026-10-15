# Enterprise AI Mesh — Operational Runbook

This runbook provides exact, copy-pasteable PowerShell commands for operating, verifying, and recovering the Enterprise AI Mesh backend, database, and autonomous agent orchestration stack.

---

## 1. Prerequisites & Environment Setup

Verify Python 3.11+, PostgreSQL 13+, and Node.js are available:

```powershell
# Navigate to repository root
cd D:\MajorProject\EnterpriseAI

# Confirm Python version
python --version

# Confirm PostgreSQL service is running
Get-Service -Name postgresql*
```

---

## 2. Starting the Application Stack

### Step 2.1: Start the FastAPI Backend

Run the server on `127.0.0.1:8000`. Dual-mounted under `/api` and `/api/v1` for 100% frontend contract parity:

```powershell
cd D:\MajorProject\EnterpriseAI\backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Verify backend health:
```powershell
curl.exe -s http://127.0.0.1:8000/api/health/ready
```

### Step 2.2: Start the Background Task Worker (Phase P4)

Run the autonomous worker process to claim and execute queue tasks:

```powershell
cd D:\MajorProject\EnterpriseAI\backend
python -m app.worker
```

### Step 2.3: Start the Redesigned Frontend

```powershell
cd D:\MajorProject\EnterpriseAI\frontend
npm run dev
```

Open your browser to `http://localhost:5173`. The system health badge will indicate **LIVE** mode.

---

## 3. Preloaded 1,000-Task Backlog Management

### Create and Enqueue Backlog

Generate and enqueue ~1,000 diverse tasks across all 15 scenario templates:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/tasks/batches/generate?batch_name=DEMO-RUN-01" `
  -H "X-API-Key: dev-operator-key"
```

### Inspect Batch Progress and Queue Stats

```powershell
# Get queue counters (pending, running, completed, failed)
curl.exe -s "http://127.0.0.1:8000/api/tasks/stats" -H "X-API-Key: dev-viewer-key"

# List batch status and completion percentage
curl.exe -s "http://127.0.0.1:8000/api/tasks/batches/" -H "X-API-Key: dev-viewer-key"
```

---

## 4. Single Scenario Execution & Human Approval Flow

### Step 4.1: Trigger Governed Multi-Agent Orchestration

Execute a governed pipeline for order `ORD-1042`:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/orchestration/execute?order_id=ORD-1042&template_id=TPL-010&severity=HIGH" `
  -H "X-API-Key: dev-operator-key"
```

### Step 4.2: Decide Pending Approval (Exactly-Once)

List pending approvals:
```powershell
curl.exe -s "http://127.0.0.1:8000/api/approvals/?status=PENDING" -H "X-API-Key: dev-viewer-key"
```

Authorize an approval request:
```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/approvals/<APPROVAL_UUID>/decision" `
  -H "Content-Type: application/json" `
  -H "X-API-Key: dev-finance-key" `
  -d '{"decision": "APPROVED", "reason": "Authorized within departmental quarterly budget limit"}'
```

---

## 5. Verification & Consistency Audit

Run the unified end-to-end verification script against the disposable database:

```powershell
python backend/scripts/verify_all.py --disposable
```

Run cross-domain consistency checks (orders, reservations, inventory, budgets):

```powershell
python backend/scripts/consistency_check.py
```

Run cryptographic audit chain verification:

```powershell
curl.exe -s "http://127.0.0.1:8000/api/audit/chain/verify" -H "X-API-Key: dev-viewer-key"
```

Run test suite:

```powershell
pytest backend/tests -q
```

---

## 6. Database Disaster Recovery & Backups

### Take a Logical Backup (Before Applying Migrations to Operational DB)

```powershell
# Create backups directory if not present
mkdir -Force backups

# Perform compressed custom-format pg_dump
pg_dump --format=custom --file=backups\enterprise_ai_backup_$(Get-Date -Format 'yyyyMMdd_HHmm').dump `
  -h localhost -p 5432 -U postgres enterprise_ai_test
```

### Restore Database from Backup

```powershell
pg_restore --clean --if-exists -h localhost -p 5432 -U postgres `
  -d enterprise_ai_disposable_test backups\latest.dump
```

---

## 7. Subsystem Troubleshooting & Failure Recovery

| Subsystem State | Cause | Remediation Procedure |
|---|---|---|
| **PostgreSQL `unavailable`** | Service stopped or port 5432 blocked | Run `Start-Service postgresql*` and verify connectivity via `backend/scripts/db_inspect.py`. |
| **Worker `unavailable`** | Process died or `ENABLE_TASK_WORKER=false` | Restart worker via `python -m app.worker`. On restart, the automated reaper claims expired leases. |
| **Graph `fallback`** | Neo4j Bolt port 7687 offline | System automatically uses `RelationalGraphEngine` over PostgreSQL CTEs. Zero downtime. |
| **LLM Provider `simulation`** | Live keys not configured | Safe deterministic fallback generates grounded recommendations citing database rows. |
| **Blockchain `simulated`** | `SIMULATE_BLOCKCHAIN=true` | Batch Merkle checkpoints verify cryptographic integrity locally. |
