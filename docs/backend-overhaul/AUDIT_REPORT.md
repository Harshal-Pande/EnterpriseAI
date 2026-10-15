# Phase P0: Initial Audit Report

**Date:** 2026-10-15  
**Inspector:** Antigravity Engineering Agent  
**Repository Root:** `D:\MajorProject\EnterpriseAI`  
**Operational Database:** `enterprise_ai_test` (PostgreSQL 18, port 5432)  
**Disposable Test Database:** `enterprise_ai_disposable_test` (PostgreSQL 18, port 5432)  
**Baseline Test Suite:** 300 passed in 33.71s (`pytest backend/tests -q`)  
**Git Working Tree:** Clean, branch `main` (`origin/main`)  

---

## 1. Environment & Infrastructure Inventory

| Component | Target / Value | Status | Evidence / Verification |
|---|---|---|---|
| **Python** | 3.12.2 | PASS | `python --version` |
| **Node.js** | v22.17.0 (npm 11.6.1) | PASS | `node -v`, `npm -v` |
| **PostgreSQL** | 18 (Client & Server) | PASS | Reachable at localhost:5432 |
| **pg_dump** | `C:\Program Files\PostgreSQL\18\bin\pg_dump.exe` | LOCATED | Verified on system disk |
| **Docker Daemon** | Installed (v29.8.2), Daemon not running | INACTIVE | Relational graph fallback active |
| **FastAPI** | 0.116.1 | PASS | Uvicorn server running on 127.0.0.1:8000 |
| **Psycopg2** | 2.9.13 (psycopg2-binary) | PASS | Threaded connection pool operational |
| **Pydantic** | 2.11.7 | PASS | Validated models |
| **Web3.py** | 6.20.4 | PASS | Installed, simulation mode active |
| **Neo4j Driver** | 5.28.6 | PASS | Driver installed; relational fallback active |
| **Pandas / Openpyxl** | 3.0.6 / 3.1.5 | PASS | Installed and functional |

### Environment Variables & Credentials Verification

| Variable | Configured State | Notes |
|---|---|---|
| `APP_ENVIRONMENT` | `development` | Development mode |
| `DATABASE_URL` | `postgresql://.../enterprise_ai_test` | Operational/Demo database (holds real event logs, scenario instances, anchors) |
| `TEST_DATABASE_URL` | `postgresql://.../enterprise_ai_disposable_test` | Isolated disposable database for all tests |
| `GEMINI_API_KEY_1` to `_7` | **ALL 7 KEYS CONFIGURED** (len=53) | Full cyclic multi-key pool present in local environment |
| `OPENROUTER_API_KEY` | CONFIGURED (len=73) | Fallback provider key present |
| `LLM_PROVIDER_MODE` | `LIVE` | Ready for approved live verification |
| `SIMULATE_BLOCKCHAIN` | `true` | Preserves testnet ETH, strictly safe |
| `CONTRACT_ADDRESS` | `0xf7aE6E373be5ad0f9444D230f285e8E620b70b63` | Real Sepolia deployed anchor contract |
| `OPERATOR_API_KEY` | CONFIGURED (len=53) | Default dev operator key matches UI header |
| `ADMIN_API_KEY` | CONFIGURED (len=53) | Present |
| `VIEWER_API_KEY` | CONFIGURED (len=53) | Present |

---

## 2. Baseline Database Snapshot (Verified via db_inspect.py)

### Target: `enterprise_ai_test` (Operational / Demo Database)
- **Total User Tables:** 43
- **Total Migrations Applied:** 6 (`001_operational_schema`, `002_runtime_schema`, `003_blockchain_anchoring`, `003_workflow_agent_schema`, `004_scheduler_lifecycle_schema`, `005_blockchain_anchoring_schema`)
- **Check Constraints:** 364
- **Foreign Keys:** 54
- **Unique Constraints:** 4
- **Indexes:** 86
- **Triggers:** 0

#### Operational Row Counts (Critical Baseline Snapshot):
| Table | Row Count | Operational Significance |
|---|---|---|
| `event_log` | **388** | Existing audit event log; MUST BE PRESERVED |
| `blockchain_anchors` | **2** | Historical anchor records (incl. EVT-PHASE7-SEP-635CDB7E) |
| `scenario_instances` | **62** | Seeded and executed scenario instances |
| `agent_runs` | **315** | Historical agent execution telemetry |
| `decisions` | **62** | Supervisor decisions |
| `policy_evaluations` | **64** | Policy outcomes |
| `orders` | **200** | Initial industrial order dataset |
| `order_lines` | **200** | Exactly 1 line per order |
| `inventory` | **150** | Stock across 5 warehouses |
| `products` | **11** | Master product catalog |
| `suppliers` | **8** | Master suppliers |
| `supplier_offers` | **6** | Offers covering 4 distinct items |
| `supplier_contracts` | **4** | Active contracts |
| `bill_of_materials` | **5** | 5 BOM lines |
| `warehouses` | **5** | 5 regional distribution centers |
| `budgets` | **4** | Departmental budgets |
| `action_queue` | **8** | Governed action proposals |
| `action_execution_results` | **8** | Executed action records |
| `production_batches` | **60** | Batch manufacturing records |
| `production_lines` | **5** | Hot strip mill, blast furnace, etc. |
| `shipments` | **120** | Freight shipment records |
| `business_rules` | **10** | Deterministic guardrails |
| `scenario_templates` | **15** | 15 exception templates |
| `simulation_config` | **12** | Seed configs |

### Target: `enterprise_ai_disposable_test` (Disposable Test Database)
- **Total User Tables:** 43
- **Total Migrations Applied:** 5 (Fresh baseline matching migrations 001-005)
- **Row Counts:** 0 operational runtime records (`event_log`=0, `scenario_instances`=0, `agent_runs`=0, `blockchain_anchors`=0). Contains only master data fixtures (200 orders, 150 inventory, 11 products, 8 suppliers).
- **All 300 tests pass against this target in 33.71s.**

---

## 3. Systematic Verification of Hypotheses (H-01 to H-22)

| ID | Hypothesis | Audit Verdict | Empirical Evidence & Assessment |
|---|---|---|---|
| **H-01** | Route prefix mismatch (`/api/v1` vs `/api`) | **CONFIRMED IN DOCS, NOT AN ISSUE IN ACTUAL CODE** | The frontend documentation mentioned `/api/v1`, but `frontend/src/services/apiClient.ts` calls `/api/...` directly. The backend router in `app/main.py` is mounted at `/api/...`. Zero calls to `/api/v1` exist in the frontend source code. In P1, we will also mount `/api/v1` aliases to guarantee 100% backward/forward compatibility. |
| **H-02** | Health check semantics & CORS | **PARTIAL** | Backend has `/api/health`, `/api/live`, `/api/health/live`, `/api/ready`, `/api/health/ready`. `DemoContext.tsx` calls `apiClient.checkLive()` which hits `/api/live` (returns 200). CORS currently whitelists `localhost:5173` and `127.0.0.1:5173`. However, `/api/health/ready` only returns a boolean database status rather than the full structured subsystem diagnostics (`state`, `latency_ms`, `data_freshness`). |
| **H-03** | Auth header alignment | **NOT AN ISSUE** | `apiClient.ts` sends `X-API-Key` with default `dev-operator-key` (or localStorage `ent_api_key`). `backend/app/core/security.py` parses `X-API-Key` and authenticates `dev-operator-key` as `UserRole.OPERATOR`. |
| **H-04** | Route shadowing (parameter vs literal) | **NOT AN ISSUE IN CODE** | Inspected `orders.py` (`/summary` declared line 158, `/{order_id}` declared line 187). Inspected `orchestration.py` (`/providers` line 144, `/{workflow_id}` line 177). Literal routes precede path parameter routes. |
| **H-05** | HTTP verb mismatch for audit verify | **NOT AN ISSUE IN CODE** | `frontend/src/services/apiClient.ts` calls `POST /api/audit/verify/{event_id}` with JSON body. `backend/app/api/audit.py` declares `@router.post("/verify/{event_id}")`. Both match. In P1, we will also support GET with query parameter. |
| **H-06** | Missing endpoints for redesigned UI | **CONFIRMED** | `BenchmarksPage.tsx` currently computes telemetry in the frontend; `ExceptionsPage.tsx` derives from `liveApprovals`; no standalone `/api/benchmarks/metrics`, `/api/cases/{workflow_id}`, or `/api/exceptions` endpoint exists. These will be cleanly delivered in P10. |
| **H-07** | Status vocabulary drift | **CONFIRMED** | DB constraints on `action_queue.status` (`PROPOSED`, `APPROVED`, `EXECUTED`, `FAILED`), Pydantic models in `apiClient.ts` allow `SUCCEEDED` / `COMPLETED`, and `scenario_instances` has `RESOLVED` vs UI `completed`. Unified enum mapping module is required in P1/P2. |
| **H-08** | Two orchestration implementations | **CONFIRMED & RESOLVED** | `backend/app/orchestration/governed.py` (`GovernedOrchestrator`) is the active implementation imported by `app/api/orchestration.py`. `app/orchestration/graph.py` is dead/divergent code. `governed.py` will be maintained as canonical. |
| **H-09** | Sync DB calls in async server | **CONFIRMED** | Endpoints in `orders.py`, `inventory.py`, `orchestration.py` use `def` (FastAPI runs in threadpool) but database connection acquisition lacks per-statement and lock timeouts. Under high concurrency (1,000 tasks) pool exhaustion is possible. Fixed in P4/P11. |
| **H-10** | In-memory event bus and tickets | **CONFIRMED** | `events.py` uses process-local `asyncio.Queue` and local ticket store. If workers run as separate processes, WebSockets will not receive worker events without a database-backed event stream. Addressed in P4. |
| **H-11** | Policy engine evaluates Python expressions via eval | **NOT AN ISSUE (DISPROVED)** | `backend/app/services/policy_service.py` does NOT use `eval()` or `exec()`. It evaluates conditions using deterministic structured logic (`available_qty >= quantity`, etc.). No code injection vulnerability exists, but AST validation will be added for dynamic expressions in P6. |
| **H-12** | Default credentials check | **CONFIRMED** | Default credentials (`dev-admin-key`, `dev-operator-key`) are active. Startup check in `main.py` needs to enforce non-dev safety. Addressed in P11. |
| **H-13** | Wrong contract address default | **CONFIRMED & RESOLVED** | Project notes deployed Sepolia contract is `0xf7aE6E373be5ad0f9444D230f285e8E620b70b63`. In `backend/.env`, `CONTRACT_ADDRESS` is already set to `0xf7aE6E373be5ad0f9444D230f285e8E620b70b63` (len=42). |
| **H-14** | Table count mismatch (33 vs 43) | **CONFIRMED & EXPLAINED** | 33 tables was an earlier documentation snapshot. The database snapshot contains 43 tables due to migrations `003_blockchain_anchoring`, `003_workflow_agent_schema`, `004_scheduler_lifecycle_schema`, `005_blockchain_anchoring_schema` (added `_schema_migrations`, `action_execution_results`, `action_queue`, `agent_findings`, `agent_runs`, `approval_requests`, `decisions`, `policy_evaluations`, `scenario_instances`, `scheduler_state`). |
| **H-15** | Event log immutability & chaining | **CONFIRMED** | `event_log` has `payload_hash` and `previous_event_hash` columns, but lacks a database trigger blocking `UPDATE`/`DELETE`, and existing rows have NULL previous hashes. Additive hardening with genesis trigger needed in P2. |
| **H-16** | Anchoring scope & Merkle trees | **CONFIRMED** | Individual event anchoring is implemented; batch Merkle tree root anchoring is documented but not implemented. Addressed in P9. |
| **H-17** | Concurrency & duplicate execution | **CONFIRMED** | Approval transitions lack `SELECT ... FOR UPDATE` conditional guards; concurrent `reserve` could oversell without row-level locks. Addressed in P4/P6. |
| **H-18** | Data too thin for complex scenarios | **CONFIRMED (EMPIRICAL)** | Exactly 200 orders with exactly 1 line per order. Only 6 supplier offers covering 4 items. Only 5 BOM lines. Only 4 budgets. Synthetic data v3 in P3 is required. |
| **H-19** | Missing customer, carrier, route masters & inventory ledger | **CONFIRMED** | Customer is only a free text `customer_ref`; carrier is free text; inventory only has point-in-time `on_hand_qty` without a transaction ledger (`inventory_movements`). Additive schema in P2 required. |
| **H-20** | Knowledge graph disconnected / isolated | **CONFIRMED** | Graph extractor has hardcoded `LIMIT` queries (LIMIT 10 warehouses, 15 suppliers, 20 products), producing isolated subgraphs without multi-tier BOM or carrier links. Fixed in P8. |
| **H-21** | Temporal incoherence | **NOT AN ISSUE (DISPROVED)** | Orders `created_at` ranges from 2026-10-10 to 2026-10-14, and shipments range to 2026-10-16. This aligns cleanly with current project reference date (15 October 2026). In P3, reference date anchoring will keep open orders active. |
| **H-22** | Tests mocked vs live database | **CONFIRMED** | Unit tests mock LLM providers and HTTP calls. Database integration tests write to `enterprise_ai_disposable_test`. Real browser-to-backend integration requires contract check script in P1. |

---

## 4. End-to-End Baseline Status Table

| Feature / Subsystem | Current State | Evidence | Operational Status |
|---|---|---|---|
| **Backend Connectivity** | 200 OK | `/api/health`, `/api/live` responding | **LIVE** |
| **Relational Database** | 43 tables, 1,327 seed records | `enterprise_ai_test` snapshot | **LIVE** |
| **Disposable Test DB** | 43 tables, 0 runtime records | `enterprise_ai_disposable_test` snapshot | **LIVE** |
| **Unit Test Suite** | 300 tests passing | `pytest backend/tests -q` (33.71s) | **PASS** |
| **LLM Provider Pool** | 7 Gemini keys configured | `env_check.py` (lengths verified) | **READY (Gate G5)** |
| **Blockchain Anchoring** | Sepolia contract deployed | Read-only verification active; simulation on | **SIMULATED / READ-ONLY** |
| **Knowledge Graph** | RelationalGraphEngine | PostgreSQL extraction active (Docker offline) | **RELATIONAL FALLBACK** |
| **Task Queue / Backlog** | In-process scheduler | Periodic scenario injection active; 1k batch not yet built | **PARTIAL** |
| **Controlled Actions** | DatabaseActionAdapter | DB state mutations supported | **PARTIAL** |
| **Frontend Live Mode** | Redesigned UI live probe | Connects to `/api/live` on port 8000 | **LIVE** |

---

## 5. Risk Assessment & Gate Triggers
1. **Gate G1:** Present audit findings and execution plan for approval before applying any migrations or loading data.
2. **Gate G2:** Logical backup with `pg_dump` and dry-run before any operational database migration.
3. **Gate G3:** Run 1,000-task backlog against disposable test copy before running on operational DB.
4. **Gate G4:** Docker daemon is stopped; keep RelationalGraphEngine as default fallback until Neo4j container is approved.
5. **Gate G5:** All 7 Gemini keys are configured; mock providers for testing, run live calls only with approval.
6. **Gate G6:** No Ethereum transactions to be signed; `SIMULATE_BLOCKCHAIN=true` must remain active.
