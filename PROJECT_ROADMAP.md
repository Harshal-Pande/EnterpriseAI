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
