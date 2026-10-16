# Local Order Pipeline Implementation Plan
## Order Processing Pipeline, FIFO Queue, Agent Decisions, Blockchain Queue, Live Exceptions, and Dashboard Integration

**Repository Path:** `d:\MajorProject\EnterpriseAI`  
**Date:** 2026-10-16  
**Status:** In Progress / Active Execution  

---

## 1. Baseline Findings & Root Cause Analysis

### 1.1 Root Cause of Repeated Processing & Stale Status
1. **Uncoordinated Background Triggering:**
   - The legacy `scheduler.py` continually polled and spawned scenario instances for orders `ORD-1243` and `ORD-1244` without updating their lifecycle state in PostgreSQL.
   - `OrchestrationPage.tsx` was querying `/api/scheduler/scenarios`, which was populated with multiple identical scenario runs stuck in `Pending`.
2. **Missing State Partitioning (Queued vs. Running vs. Done):**
   - The application previously tracked orders only in the general `orders` and `order_processing_queue` tables.
   - Completed orders remained in `order_processing_queue` with status `'COMPLETED'`, but the frontend lacked strict separation, causing ambiguous queries and re-runs.
3. **Disconnected Agent Decision Persistence:**
   - The multi-agent orchestrator was executing, but individual agent decision records (findings, rationale, confidence score, risk) were not stored in a queryable, dedicated decision table linked to the blockchain queue.
4. **Disconnected Blockchain Queue:**
   - Blockchain anchoring was decoupled from agent decisions; transactions were not generated directly from the agent decision log.
5. **Dashboard Usability Gap:**
   - `OverviewPage.tsx` was purely read-only metrics with no operational shortcut or interactive controls to trigger or monitor order execution.

---

## 2. Architectural Design & Component Reuse

### 2.1 Reused Components (No Redundant Rebuilds)
- **FastAPI Backend:** Reused existing API routers in `backend/app/api/orders.py`, `backend/app/api/orchestration.py`, `backend/app/api/exceptions.py`.
- **Database Connection:** Reused `app.db.database` (`get_db`, `get_db_connection`) and PostgreSQL connection pooling.
- **Governed Multi-Agent Orchestrator:** Reused `app.orchestration.governed.GovernedOrchestrator` and specialist agents (`SupervisorAgent`, `InventoryAgent`, `ProcurementAgent`, `FinanceAgent`, `LogisticsAgent`).
- **Operational Exceptions:** Reused `operational_exceptions` schema and lifecycle services.
- **Blockchain Infrastructure:** Reused canonical JSON hashing (RFC 8785 style) and EVM transaction structures in `app.services.blockchain_service.py`.
- **Frontend Architecture:** Reused Vite + React + Tailwind + Lucide icons + `apiClient.ts` without introducing competing libraries.

### 2.2 Schema Extensions (Migration 014)
- **`orders_queued`:** Dedicated FIFO queue table with `queue_position` ordering. Orders waiting to be processed.
- **`orders_running`:** Active execution table tracking orders currently claimed and being evaluated by the AI agent mesh, with live per-agent states (`supervisor`, `inventory`, `procurement`, `finance`, `logistics`).
- **`orders_done`:** Immutable archival table for terminally processed orders (`COMPLETED`), recording final consensus decision, execution duration (ms), blockchain block number, and transaction hash.
- **`agent_decision_logs`:** Dedicated decision log table recording decisions taken by each specialist agent with structured evidence and confidence scores.
- **`blockchain_tx_queue` & `blockchain_blocks`:** Queue of decision transactions mined into consecutive blockchain blocks with block hashes, previous hash, and Merkle root.

---

## 3. Detailed Implementation Tasks

### Phase 1: Order Lifecycle & FIFO Processing
- [x] Create forward-only migration `014_order_queue_lifecycle.sql`.
- [x] Apply migration 014 to PostgreSQL database.
- [x] Implement `OrderLifecycleService.pop_and_execute_order()` with atomic claim (`FOR UPDATE SKIP LOCKED`), moving from `orders_queued` -> `orders_running` -> `orders_done`.
- [x] Ensure completed orders are deleted from `orders_running` and never re-queued.
- [x] Disable automatic synthetic order generation by default in normal local operation.

### Phase 2: Backend REST Endpoints
- [x] Expose `GET /api/orders/lifecycle/queued`
- [x] Expose `GET /api/orders/lifecycle/running`
- [x] Expose `GET /api/orders/lifecycle/done`
- [x] Expose `GET /api/orders/lifecycle/decisions`
- [x] Expose `GET /api/orders/lifecycle/blockchain/blocks`
- [x] Expose `POST /api/orders/lifecycle/run-next` (FIFO pop and execute)
- [x] Expose `POST /api/orders/lifecycle/run-order/{order_id}`

### Phase 3: Agent Orchestration & Decision Logging
- [x] Execute 5-agent mesh on claimed order.
- [x] Write individual decisions to `agent_decision_logs`.
- [x] Record structured evidence records, rationale, confidence, and risk level.
- [x] Enqueue decisions into `blockchain_tx_queue`.
- [x] Mine transactions into `blockchain_blocks`.

### Phase 4: Live Exceptions
- [x] Controlled exception scenarios (`SUPPLIER_UNAVAILABLE`, `BUDGET_BREACH`, `DELIVERY_DELAY`, `STOCK_SHORTFALL`).
- [x] When exception is encountered, order transitions to `EXCEPTION` status in `orders_running` and writes to `operational_exceptions`.
- [x] Live exception badge and cause displayed immediately in UI.

### Phase 5: Frontend Operational Experience
- [x] Add typed methods in `frontend/src/services/apiClient.ts`.
- [x] Update `OrdersPage.tsx` with 3 distinct tabs (FIFO Queue, Active Running, Processed History) and direct "Run Now" actions.
- [x] Update `OrchestrationPage.tsx` with real execution history, real agent decision logs from the database, and blockchain block inspection.
- [x] Update `OverviewPage.tsx` (Dashboard) with prominent Orchestration Shortcut card and live queue metrics.
- [x] Verify frontend build passes with 0 TypeScript/lint errors (`npm run build`).

### Phase 6: Automated Testing & Verification
- [ ] Implement automated integration test suite in `backend/tests/test_order_lifecycle_pipeline.py`.
- [ ] Verify FIFO ordering test.
- [ ] Verify duplicate prevention and idempotency test.
- [ ] Verify clean completion vs exception handling test.
- [ ] Verify blockchain block and transaction generation test.
- [ ] Perform local end-to-end multi-order execution scenario.
- [ ] Compile final delivery report `progressMD/LOCAL_ORDER_PIPELINE_IMPLEMENTATION_REPORT.md`.
