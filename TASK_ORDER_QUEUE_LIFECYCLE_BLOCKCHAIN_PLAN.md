# Enterprise AI Mesh: Order Queue Lifecycle, Agent Decisions, and Blockchain Synchronization

## Instructions & Verification Breakdown

This document tracks the step-by-step implementation, verification, and legitimacy criteria as requested by the user.

---

### Step 1: Database Architecture (Migration 014)
- [ ] Create `backend/db/migrations/014_order_queue_lifecycle.sql` with:
  1. `orders_queued`: Dedicated FIFO queue table of orders awaiting execution.
  2. `orders_running`: Dedicated active execution table tracking live running orders, current stage, and per-agent status.
  3. `orders_done`: Dedicated append-only archive of completed orders with outcome, decision summary, duration, and blockchain linkage.
  4. `agent_decision_logs`: Log of each individual agent's decision (supervisor, inventory, procurement, finance, logistics) with rationale, risk level, confidence, and timestamp.
  5. `blockchain_blocks` and `blockchain_tx_queue`: Queue where agent decisions are received and deployed into blockchain blocks and transactions.
  6. Populate initial `orders_queued` from pending orders and seed `orders_done` from existing completed orders.
- [ ] Apply migration 014 to PostgreSQL database.

---

### Step 2: Backend Order Lifecycle & Execution Service
- [ ] Implement `backend/app/services/lifecycle_queue_service.py`:
  - `pop_next_queued_order()`: FIFO pop that atomically removes order from `orders_queued` and inserts into `orders_running`.
  - `update_running_order_progress()`: Updates live execution phase and agent status in `orders_running`.
  - `record_agent_decision()`: Records decisions taken by each specialist agent into `agent_decision_logs` and enqueues into `blockchain_tx_queue`.
  - `complete_running_order()`: Removes order from `orders_running` and appends to `orders_done`. Guarantees orders never run twice.
  - `mark_running_order_exception()`: Marks order with LIVE exception, records in `operational_exceptions`, and updates running table.
  - `process_blockchain_tx_queue()`: Mines queued decisions into consecutive blockchain blocks with block hash, previous hash, merkle root, and transaction hashes.
- [ ] Expose REST APIs in `backend/app/api/orders.py` and `backend/app/api/orchestration.py`:
  - `GET /api/orders/lifecycle/queued`
  - `GET /api/orders/lifecycle/running`
  - `GET /api/orders/lifecycle/done`
  - `GET /api/orders/lifecycle/decisions/{order_id}`
  - `GET /api/orders/lifecycle/blockchain/blocks`
  - `POST /api/orders/lifecycle/run-next` (FIFO pop and execute)
  - `POST /api/orders/lifecycle/run-order/{order_id}`

---

### Step 3: Frontend Views & Realtime Integration
- [ ] Update `frontend/src/services/apiClient.ts` with typed methods for lifecycle queued, running, done, decisions, blockchain blocks, and run-next.
- [ ] Update `frontend/src/pages/OrdersPage.tsx`:
  - Three distinct tabs: **Queued (FIFO)**, **Running (Live)**, and **Done (History)**.
  - Show real data dynamically moving between these tables without duplication.
- [ ] Update `frontend/src/pages/OrchestrationPage.tsx`:
  - Display current running order with dynamic live agent states.
  - Show agent decision log and blockchain block generation.
  - Link directly to live exceptions when triggered.
- [ ] Update `frontend/src/pages/OverviewPage.tsx` (Dashboard):
  - Add **Orchestration Shortcut** card allowing the user to trigger next order execution, view live running status, and jump directly to active execution or exceptions.
- [ ] Update `frontend/src/pages/AuditTrailPage.tsx`:
  - Show the live blockchain blocks generated from the agent decision logs.

---

### Step 4: Verification & Local Testing
- [ ] Verify database schema and test execution flow:
  1. Trigger FIFO order pop.
  2. Confirm order moves from `orders_queued` to `orders_running`.
  3. Confirm agent decisions are saved in `agent_decision_logs`.
  4. Confirm blockchain block is generated and linked.
  5. Confirm order is removed from `orders_running` and recorded in `orders_done`.
  6. Confirm order is NEVER run again.
  7. Confirm dashboard shortcut functions seamlessly.
- [ ] Build frontend (`npm run build`) with 0 errors.
- [ ] Verify live running application and provide direct access URLs.

---

### Step 5: Final Delivery Report
- [ ] Produce detailed delivery report documenting all changed files, architectural improvements, and verification evidence.
