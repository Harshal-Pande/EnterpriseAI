# Implementation Plan: Enterprise AI Mesh

**Plan Version:** 1.0.0  
**Status:** In Execution  
**Current Phase:** Phase 2 (Reproduce and Repair Repeated Order Processing)  

---

## 1. Architecture Overviews

### 1.1 Current-State Architecture Diagram
```
[Client / UI: OrdersPage / OrchestrationPage]
        │
        ├─────────────────────────────┬────────────────────────────┐
        ▼                             ▼                            ▼
POST /api/orders              POST /lifecycle/run-next      GET /queue/status
 (Dual Enqueue)                (Disconnected Mock Runner)   (order_queue_runner)
        │                             │                            │
 ┌──────┴───────────────┐             │ (bypasses agents)          │ (bypasses UI)
 ▼                      ▼             ▼                            ▼
orders_queued   order_proc_queue   orders_running          GovernedOrchestrator
(Migration 14)  (Migration 13)    (Fake blocks/txs)        (real 5 agents)
```

### 1.2 Target-State Architecture Diagram
```
[Client / UI Control Room]
        │
        ▼ (with Idempotency-Key header)
[FastAPI Orders API (/api/orders)]
        │
        ▼ (Transaction: orders + order_lines + audit event)
[PostgreSQL Database: orders & order_processing_queue]
        │
        ▼ (Atomic Claim: SELECT ... FOR UPDATE SKIP LOCKED)
[Authoritative Queue Runner (OrderQueueRunner)]
        │
        ▼ (Correlation ID, Typed State, Bounded Retries)
[GovernedOrchestrator]
   ├── 1. Inventory Agent (Stock reservation & shortage checks)
   ├── 2. Procurement Agent (Supplier selection & SLA validation)
   ├── 3. Finance Agent (Budget check & credit approval)
   ├── 4. Logistics Agent (Corridor routing & freight risk)
   └── 5. Supervisor Agent (Reconciliation, policy gating, decision synthesis)
        │
        ├── [Policy Passed] ───────────────► Propose & Execute Action in action_queue
        └── [Policy Breach / Approval Gate] ─► Create operational_exceptions record
        │
        ▼ (Durable State Persistence: status = COMPLETED or WAITING_EXCEPTION)
[order_processing_queue & event_log]
        │
        ▼ (Independent Anchoring Queue - Decoupled Asynchronous Job)
[BlockchainService / blockchain_anchors]
        ├── Canonical RFC 8785 Digest (SHA-256)
        ├── EVM Transaction Broadcast (Sepolia RPC or Local Verified Simulation)
        └── Receipt Confirmation & On-Chain State Verification
```

---

## 2. Prioritized Implementation Phases

### Phase 2: Reproduce and Repair Repeated Order Processing (CRITICAL)
- **Defects Addressed:**
  1. Lack of idempotency key on order submission allows duplicate order generation upon client retry.
  2. Race conditions in queue claiming when multiple requests/workers target the same order.
  3. Processing completed or running orders.
  4. Infinite auto-replenishment cycle generating synthetic orders continuously.
  5. Lack of bounded retries leading to infinite exception loops on policy denials.
- **Target Modules:**
  - `backend/app/models/order.py`: Add `idempotency_key` to `OrderCreateRequest` and response.
  - `backend/app/api/orders.py`: Deduplicate order submission via `idempotency_key`, ensure transactional consistency.
  - `backend/app/services/order_queue_runner.py`: Disable infinite auto-replenish in runtime defaults, implement atomic claim guards, add stale claim recovery.
  - `backend/db/migrations/015_order_idempotency_and_queue_hardening.sql`: Add `idempotency_key` column and unique constraint on `orders`.
- **Acceptance Criteria & Verification:**
  - Regression tests proving that duplicate submissions with identical idempotency keys return the existing order.
  - Concurrent worker claim tests ensuring only 1 worker claims a pending item.
  - Tests ensuring completed orders cannot be claimed or re-run.

### Phase 3: Persistent Queue and Lifecycle Hardening
- **Target Modules:**
  - `backend/app/services/order_queue_runner.py`
  - `backend/app/services/lifecycle_queue_service.py`
- **Actions:**
  - Unify queue lifecycle state transitions: `QUEUED` -> `PROCESSING` -> `COMPLETED` or `WAITING_EXCEPTION`.
  - Add explicit stale claim recovery: any order in `PROCESSING` whose claim is older than `CLAIM_TIMEOUT` (300s) is safely reclaimed or failed.
  - Add bounded attempt counter (`max_attempts = 3`).

### Phase 4 & 5: Actual Agent Orchestration Integration
- **Target Modules:**
  - `backend/app/orchestration/governed.py`
  - `backend/app/services/order_queue_runner.py`
  - `backend/app/services/lifecycle_queue_service.py`
- **Actions:**
  - Ensure all order execution calls the real `GovernedOrchestrator` running all 5 agents (`Supervisor`, `Inventory`, `Procurement`, `Finance`, `Logistics`).
  - Eliminate all hardcoded fake agent decision text in `lifecycle_queue_service.py`.
  - Persist real agent runs in `agent_runs` table, supervisor decisions in `decisions` table.
  - Separate agent recommendations from authorized policy decisions and executed business actions.

### Phase 6: Exceptions, Retries, and Recovery
- **Target Modules:**
  - `backend/app/services/exception_service.py`
  - `backend/app/api/exceptions.py`
- **Actions:**
  - Capture stable exception identifier, linked order, severity, cause, proposed action.
  - Ensure `resume_order_from_exception` checks retry count and does not retry non-retryable policy rejections.
  - Connect operator resolution to real action execution in `action_service.py`.

### Phase 7: Independent Blockchain Audit Anchoring
- **Target Modules:**
  - `backend/app/services/blockchain_service.py`
  - `backend/app/api/audit.py`
- **Actions:**
  - Ensure blockchain anchoring runs independently from order processing queue.
  - Eliminate fake block generation (`0x` + hash) in local tables.
  - Write anchor jobs to `blockchain_anchors` table.
  - Implement real receipt polling, distinguishing confirmed transactions from simulation.

### Phase 8: Frontend Truthful Control Room Integration
- **Target Modules:**
  - `frontend/src/pages/OrdersPage.tsx`
  - `frontend/src/pages/OrchestrationPage.tsx`
  - `frontend/src/pages/AuditTrailPage.tsx`
  - `frontend/src/pages/ExceptionsPage.tsx`
  - `frontend/src/pages/OverviewPage.tsx`
  - `frontend/src/services/apiClient.ts`
- **Actions:**
  - Ensure UI displays authoritative data from `order_processing_queue`, `operational_exceptions`, and `blockchain_anchors`.
  - Remove fake block tables from display.
  - Guard UI buttons against duplicate clicks.

### Phase 9: Verification, End-to-End Testing, and Handoff
- Run the full test suite, verify end-to-end order processing, document test results in `TEST_AND_VERIFICATION_REPORT.md` and complete `FINAL_IMPLEMENTATION_REPORT.md`.
