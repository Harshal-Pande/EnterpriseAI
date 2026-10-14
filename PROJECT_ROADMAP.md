# Enterprise AI Mesh — Roadmap

## PHASE 1 — Frontend Prototype & UX
**Objective**: Build a compelling interactive dashboard to visualize the conceptual system.
**Major tasks**: Dashboard, Analytics, Agent Workflow visualization, Knowledge Graph UI.
**Dependencies**: None
**Current status**: **Completed** (Prototype phase)
**Definition of completion**: Fully navigable UI with simulated data demonstrating the intended user experience.

## PHASE 2 — Production Backend Foundation & Governance Pipeline
**Objective**: Build persistent PostgreSQL-backed operational APIs, multi-agent workflows, deterministic policy evaluation, human-in-the-loop approvals, controlled simulation action execution, and blockchain audit anchoring.
**Major tasks**:
- Database connection pool lifecycle (`init_db_pool`, `get_db`, `close_db_pool`, `/api/health`, `/api/live`).
- Operational REST APIs backed by PostgreSQL (`/api/orders`, `/api/inventory`, `/api/suppliers`).
- Workflow persistence and state transitions (`/api/workflow`).
- Specialist-agent run persistence and findings (`/api/agents`).
- Scenario scheduler with distributed lease locking (`/api/scheduler`).
- Deterministic policy evaluation & approval engine (`/api/policies`, `/api/approvals`).
- Controlled action execution via safe simulation adapter (`/api/actions`).
- Audit logging & canonical SHA-256 blockchain anchoring (`/api/audit`).
- Role-based access control (RBAC), CORS middleware, and API key authentication.
- Centralized typed frontend API client with Demo Mode and Live PostgreSQL Mode switcher.
- Docker Compose and containerization (`docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`).
**Dependencies**: PostgreSQL, FastAPI, React Frontend
**Current status**: **Completed, Hardened & Verified** (165/165 Pytest tests passing, 119/119 DB validation checks passing, Frontend production build passing with 0 errors, Docker Compose configuration verified).
**Definition of completion**: Fully integrated end-to-end lifecycle verified from scenario generation to blockchain digest anchoring with live UI controls.

## PHASE 3 — Persistent Five-Minute Scenario Engine
**Objective**: Implement, complete, and verify the persistent scenario-generation engine for the Enterprise AI Supply Chain Control Room.
**Major tasks**:
- Default 300-second (5-minute) scheduler interval with strict environment precedence (`SCENARIO_SCHEDULER_INTERVAL_SECONDS` > `SCHEDULER_INTERVAL_SECONDS` > 300).
- Safe startup validation rejecting negative, zero, or non-numeric intervals, with fast overrides for automated tests.
- Grounding against PostgreSQL operational tables (`orders`, `inventory`, `suppliers`, `budgets`) to bind genuine entities rather than fabricated placeholders.
- Deterministic template selection via random seed and explicit template filtering.
- Queue concurrency and open-scenario capacity enforcement (`SCHEDULER_MAX_OPEN_SCENARIOS`, default 10) with observable `OPEN_SCENARIOS_LIMIT_REACHED` skip logging.
- Distributed lease locking in PostgreSQL with stale lease recovery, collision prevention, and idempotency key protection.
- Comprehensive audit event logging (`event_log`) for all scheduler lifecycle events (`SCHEDULER_CYCLE_STARTED`, `SCENARIO_GENERATED`, `SCENARIO_GENERATION_SKIPPED`, `SCHEDULER_LEASE_RELEASED`).
- Backend APIs: `GET /api/scheduler/status`, `POST /api/scheduler/trigger` (with `force`, `template_id`, `idempotency_key`, `seed`), `GET /api/scheduler/templates`, `GET /api/scheduler/scenarios`.
- Frontend integration: Overview and Exceptions pages display live scheduler state, 300s interval, queue capacity counter (`active/max`), active leases, and skip feedback.
**Dependencies**: Phase 2 PostgreSQL Backend Foundation & Governance Pipeline (Completed)
**Current status**: **Completed, Hardened & Verified** (171/171 Pytest tests passing, 119/119 DB validation checks passing, Frontend production build passing with 0 errors, Docker Compose configuration verified).
**Definition of completion**: Scenario scheduler runs every 300s, grounds against real PostgreSQL data, enforces open limits, supports idempotent manual triggers, persists all state before processing, and updates frontend truth.

## PHASE 3.5 — Reliability, Security & Audit Remediation
**Objective**: Resolve all confirmed findings from the independent Phase 0–3 audit, add regression tests, verify the existing system, and harden deployment security.
**Major tasks**:
- **FIND-01**: Hardened scheduler force and concurrency safeguards. Lease mutual exclusion is absolute; `force=true` and administrative overrides cannot bypass active leases. Admin overrides require `ADMIN` role with recorded justification and audit event.
- **FIND-02**: Deterministic scheduled idempotency derived from UTC schedule slots (`SCHED-<template>-SLOT-<ts>`) and configured intervals. Manual triggers remain distinguishable.
- **FIND-03**: Orphaned workflow recovery using `FOR UPDATE SKIP LOCKED` for stale `QUEUED`/`RUNNING` scenarios, transitioning to `FAILED` with audit events.
- **FIND-04**: Background scheduler lease renewal heartbeat preventing lease expiration during execution with clean shutdown and ownership loss detection.
- **FIND-05**: Truthful frontend live connectivity: `DemoContext.tsx` checks live probe and operational endpoints, marking offline or degraded states transparently.
- **FIND-06**: Hardened Docker Compose configuration failing closed on missing production credentials and secrets. Root `.env.example` template provided.
- **FIND-07**: Harmonized documentation across READMEs, roadmap, and project references, accurately reflecting PostgreSQL persistence and Phase 0–3.5 capabilities.
- **FIND-08**: Added architectural design target disclaimer to `BenchmarksPage.tsx`.
**Dependencies**: Phase 3 Persistent Five-Minute Scenario Engine (Completed)
**Current status**: **Completed, Hardened & Verified**
**Definition of completion**: Scheduler concurrency and idempotency defects resolved, orphaned recovery active, lease renewal heartbeat running, truthful frontend connectivity, fail-closed Compose security, and clean regression test suite.

## PHASE 4 — Governed Multi-Agent Intelligence and Orchestration
**Objective**: Implement grounded multi-agent coordination with typed contracts, deterministic policy gating, approval thresholds, safe action execution, and dual-mode LLM provider abstraction.
**Major tasks**:
- Small, typed `LLMProvider` abstraction supporting `SIMULATION` and `LIVE` modes with bounded timeouts, retries, and masked credential logging.
- `GovernedOrchestrator` coordinating `InventoryAgent`, conditional `ProcurementAgent`, `FinanceAgent`, `LogisticsAgent`, and `SupervisorAgent`.
- Structured `SupervisorOutput` contract identifying evidence-backed recommendations, operational conflicts, and missing evidence.
- Deterministic policy evaluation and human-approval gating (> 50M INR single-action threshold) preventing unapproved executions.
- Safe action simulation with audit trails in `event_log` and state updates across `scenario_instances`, `decisions`, and `action_queue`.
- Comprehensive `/api/orchestration` endpoints secured with RBAC (`OPERATOR` and `VIEWER` roles).
- Interactive `OrchestrationPage.tsx` React frontend with real backend consumption and retry/resume controls.
**Dependencies**: Phase 2 Backend Foundation & Phase 3 Scenario Engine (Completed)
**Current status**: **Completed, Hardened & Verified** (218/218 backend tests passing, 36/36 orchestration tests passing, 119/119 DB validation checks passing, Frontend build & lint clean).
**Definition of completion**: Orchestration pipeline executes grounded agents, validates typed contracts, gates actions behind deterministic policies, persists state in PostgreSQL, surfaces truth to the UI, and passes all tests.

## PHASE 7 — Real-Time Events & WebSockets
**Objective**: Stream agent workflow progress live to the UI.
**Major tasks**: Configure WebSockets in FastAPI, update React to listen for state changes.
**Dependencies**: Real Multi-Agent Orchestration
**Current status**: **Planned**
**Definition of completion**: UI Activity Stream updates in real-time as agents progress through LangGraph nodes.

## PHASE 8 — Integration, Testing & Benchmarking
**Objective**: Ensure the entire system works cohesively.
**Major tasks**: End-to-end testing, performance metrics, UI polish.
**Dependencies**: All prior phases
**Current status**: **Planned**
**Definition of completion**: All components integrate without critical errors and pass automated tests.

## PHASE 9 — Final Documentation & Deployment
**Objective**: Prepare the project for final presentation/release.
**Major tasks**: Comprehensive READMEs, deployment guides, video demonstrations.
**Dependencies**: Phase 8
**Current status**: **Planned**
**Definition of completion**: Project is fully documented and can be deployed from scratch using provided instructions.
