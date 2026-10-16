# Baseline Audit Report: Enterprise AI Mesh

**Audit Timestamp:** 2026-10-16 23:45:00 UTC+05:30  
**Environment:** Windows (PowerShell), Python 3.12.2, PostgreSQL 5432 (`enterprise_ai_disposable_test`), Node v22.17.0, npm 11.6.1  
**Git Branch:** `main` (commit clean baseline, all preexisting changes preserved)

---

## 1. Detected Components and Entry Points

### 1.1 Backend Component
- **Root Directory:** `d:\MajorProject\EnterpriseAI\backend`
- **Framework:** FastAPI (`app.main:app`), ASGI server Uvicorn.
- **Entry Points:**
  - `backend/app/main.py`: Lifespan manager (`lifespan`), router mounts for `/api` and `/api/v1`.
  - Routers:
    - `/orders`: `app.api.orders`
    - `/workflow`: `app.api.workflow`
    - `/agents`: `app.api.agents`
    - `/orchestration`: `app.api.orchestration`
    - `/exceptions`: `app.api.exceptions`
    - `/approvals`: `app.api.approvals`
    - `/actions`: `app.api.actions`
    - `/audit`: `app.api.audit`
    - `/policies`: `app.api.policies`
    - `/inventory`: `app.api.inventory`
    - `/suppliers`: `app.api.suppliers`
    - `/scheduler`: `app.api.scheduler`
    - `/system`: `app.api.system`
    - `/health`: `app.api.health`
    - WebSocket: `app.api.ws`

### 1.2 Frontend Component
- **Root Directory:** `d:\MajorProject\EnterpriseAI\frontend`
- **Framework:** React 18, TypeScript, Vite, Tailwind CSS, Lucide icons.
- **Entry Points:**
  - `frontend/src/App.tsx`: Main routing and Shell layout.
  - `frontend/src/pages/OrdersPage.tsx`: Order lifecycle (FIFO queue, running, done).
  - `frontend/src/pages/OrchestrationPage.tsx`: Agent mesh orchestration view.
  - `frontend/src/pages/ExceptionsPage.tsx`: Operational exceptions management.
  - `frontend/src/pages/AuditTrailPage.tsx`: Event log and blockchain verification.
  - `frontend/src/pages/OverviewPage.tsx`: Executive supply chain control room dashboard.
  - `frontend/src/services/apiClient.ts`: Strongly typed REST client for backend endpoints.

### 1.3 Database & Migrations
- **Engine:** PostgreSQL 16 on `localhost:5432`.
- **Database Name:** `enterprise_ai_disposable_test`.
- **Migration Mechanism:** Sequential versioned SQL scripts in `backend/db/migrations/`:
  - `001_operational_schema.sql`: Core master domain data (products, suppliers, warehouses, budgets, inventory, orders, order_lines).
  - `002_runtime_schema.sql`: Scenarios, decisions, action_queue, event_log, approval_requests.
  - `003_workflow_agent_schema.sql`: Agent runs, policy evaluations.
  - `004_scheduler_lifecycle_schema.sql`: Scheduler state and distributed leases.
  - `005_blockchain_anchoring_schema.sql`: Blockchain anchors table.
  - `006_master_data_extensions.sql` to `012_cascade_runtime_foreign_keys.sql`: Hardening, ledger, constraints.
  - `013_order_processing_queue.sql`: `order_processing_queue` (atomic claim with queue_position, status) & `operational_exceptions`.
  - `014_order_queue_lifecycle.sql`: `orders_queued`, `orders_running`, `orders_done`, `agent_decision_logs`, `blockchain_blocks`, `blockchain_tx_queue`.

### 1.4 Orchestration & Agent Framework
- **Primary Governed Orchestrator:** `backend/app/orchestration/governed.py` (`GovernedOrchestrator`).
  - Specialists: `SupervisorAgent`, `InventoryAgent`, `ProcurementAgent`, `FinanceAgent`, `LogisticsAgent`.
  - Deterministic policy gating, approval requirement check, safe action proposal/execution.
- **Secondary / Legacy Graph:** `backend/app/orchestration/graph.py` (`WorkflowGraph`).

---

## 2. Order Queue Implementation & Discovered Duplication Sources

### 2.1 Complete Order Lifecycle Trace (Current State)
1. **Creation:** `POST /api/orders/` (`backend/app/api/orders.py:create_order`) inserts into `orders` and `order_lines`. If `auto_enqueue` is true, inserts into BOTH `order_processing_queue` AND `orders_queued`.
   - **Defect Found (Idempotency):** No `idempotency_key` parameter in `OrderCreateRequest` or uniqueness constraint on orders table. Client retry immediately creates a duplicate order row with a new `order_id` (e.g., `ORD-1250`).
2. **Dual Queue Duplication:** Two independent queues exist simultaneously:
   - `order_processing_queue` (Migration 013) consumed by background runner `order_queue_runner`.
   - `orders_queued` (Migration 014) consumed by `OrderLifecycleService` triggered via UI buttons.
3. **Infinite Auto-Replenishment:** `order_queue_runner` has `is_queue_auto_replenish() == True` by default. Every time an order is processed, `replenish_one_order` synthesizes a new order and appends it to `order_processing_queue`, triggering perpetual order execution.
4. **Synthetic Disconnected Simulation in Lifecycle Service:** `OrderLifecycleService.pop_and_execute_order` hardcodes 5 fake agent responses, fabricates mock transaction hashes `f"0x{_calc_sha256(...)}"`, and writes fake blocks into `blockchain_blocks` table, bypassing `GovernedOrchestrator` and real `blockchain_service.py`.
5. **No Atomic Row Lock in Target Claim:** `pop_and_execute_order` using `target_order_id` does a simple `DELETE FROM orders_queued WHERE order_id = %s` without verifying if the order is already in `orders_running` or `orders_done`.
6. **Exception Infinite Loop:** When an exception is resumed (`exception_service.py:resume_order_from_exception`), the queue item is reset to `QUEUED` without bounded retry tracking, causing the queue runner to immediately re-claim it and hit the identical policy failure.
7. **Stale Claim Recovery Absent:** If a worker crashes while an order is in `PROCESSING`, the record is locked indefinitely with no timeout recovery.

---

## 3. Blockchain Anchoring: Reality vs. Simulation
- **Real Service:** `backend/app/services/blockchain_service.py` (`BlockchainService`, `Web3AuditService`, `CanonicalHasher`).
  - Has RFC 8785 canonical digest calculation, smart contract ABI (`EnterpriseAudit.sol`), transaction submission, receipt polling, and verification.
  - Uses `blockchain_anchors` table.
- **Fake Mock in Lifecycle Queue:** `backend/app/services/lifecycle_queue_service.py` creates local table `blockchain_blocks` and fabricates hashes without any real cryptographic proof or Web3 connection.
- **Defect:** The UI was wired to display the fake `blockchain_blocks` table instead of verifiable audit trail records from `blockchain_anchors` and `event_log`.

---

## 4. Baseline Test & Build Results

### 4.1 Backend Test Results
- **Command:** `python -m pytest backend/tests`
- **Total Tests Collected:** 371
- **Passed:** 369
- **Failed:** 2 (Isolated race condition / state bleed from uncleaned test orders in `test_isolation.py` and scheduler lock contention in `test_scheduler.py`). Both pass when run in isolation.
- **Database Connection Tests:** 10/10 passed (`test_database_connection.py`).
- **Order Queue Runner Tests:** 8/8 passed (`test_order_queue_runner.py`).
- **Order Lifecycle Pipeline Tests:** 7/7 passed (`test_order_lifecycle_pipeline.py`).

### 4.2 Frontend Build Results
- **Command:** `npm run build` in `frontend/`
- **Output:** Built cleanly in 1.21s without TypeScript errors or Vite bundler issues.

---

## 5. Summary of Primary Deficiencies to Address
1. **Unify Queue & Execution:** Retire disconnected synthetic simulation in `lifecycle_queue_service.py` and unify on `GovernedOrchestrator` with durable persistence in `order_processing_queue`.
2. **Idempotency on Order Submission:** Add `idempotency_key` support on `OrderCreateRequest` and enforce unique constraint in `orders` / `order_processing_queue`.
3. **Queue Claiming & Bounded Retries:** Enforce atomic `SELECT FOR UPDATE SKIP LOCKED`, lease heartbeat, stale-claim recovery, and bounded retries (`max_retries = 3`).
4. **Real Agent Integration:** Ensure all 5 specialist agents (`Supervisor`, `Inventory`, `Procurement`, `Finance`, `Logistics`) run through `GovernedOrchestrator` and output structured Pydantic models with durable database persistence.
5. **Truthful Blockchain Anchoring:** Anchor completed orders and exception events using `blockchain_service.py`, distinguishing confirmed EVM testnet transactions from local simulation, eliminating fabricated fake hashes.
6. **Frontend Truthfulness:** Ensure `OrdersPage`, `OrchestrationPage`, and `AuditTrailPage` display authoritative data directly from `orders`, `order_processing_queue`, `agent_runs`, `decisions`, `operational_exceptions`, and `blockchain_anchors`.
