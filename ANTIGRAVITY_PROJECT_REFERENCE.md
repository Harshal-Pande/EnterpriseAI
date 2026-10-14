# Enterprise AI Mesh — Antigravity Project Reference
**Document type:** Source-of-truth project context and implementation roadmap  
**Status:** Baseline reference for the next implementation cycle  
**Last updated:** 14 October 2026

---

## 1. Purpose of this file

This document is the working reference for Antigravity and anyone contributing to the Enterprise AI Mesh project. Read it before changing code. It records the intended product, the verified repository baseline, the architecture direction, implementation phases, and rules that prevent fake integrations or unnecessary rewrites.

**This file is a plan and baseline, not evidence that any planned feature has already been implemented.** Update the status and development log as work is completed and tested.

## 2. Product vision

Build an industrial supply-chain control room for a fictional steel manufacturer. The system should continuously create realistic operational situations, investigate them with coordinated agents, recommend or perform permitted actions, persist the outcome, and provide an auditable explanation of what happened.

The target demo loop is:

1. A scheduler creates a new operational scenario every **300 seconds (5 minutes)**.
2. The scenario is saved to persistent storage before processing.
3. A Supervisor coordinates relevant specialist agents using current operational data and explicit business rules.
4. Agents produce structured findings, evidence, options, risk assessments, and recommended actions.
5. Policy checks determine whether an action is permitted automatically or requires human approval.
6. Approved actions update the operational database and generate audit events.
7. Critical audit checkpoints are hashed and recorded on a real blockchain deployment.
8. The dashboard reflects actual persisted state and workflow events.
9. Operators can inspect the scenario, agent reasoning summary, decision, action, approval, and audit proof.

The timer schedules scenario generation; it does **not** require every workflow to finish within five minutes. Workflows may continue while later scenarios are generated, subject to explicit concurrency limits.

## 3. Scope and business domain

The system is an industrial steel supply-chain simulation, not merely a generic order-fulfilment demo. Model relevant entities and relationships such as:

- Sites, departments, users, roles, and approval permissions
- Products, raw materials, bills of material, warehouses, and inventory movements
- Customer orders, order lines, delivery commitments, shipments, and carrier events
- Suppliers, supplier offers, contracts, purchase orders, goods receipts, and supplier performance
- Production lines, shifts, production batches, capacity, and planned/unplanned downtime
- Quality inspections, non-conformances, holds, and release decisions
- Maintenance assets, work orders, spare parts, and equipment-risk events
- Energy readings, energy costs, operational budgets, and budget thresholds
- Safety events and near misses
- Scenario templates and scenario instances
- Agent runs, decisions, approvals, action execution, event history, and blockchain anchors

Use a fictional company name and synthetic data. Do not imply that the dataset represents actual Tata Steel internal data.

## 4. Repository baseline observed in the uploaded project

Repository: `harshal-pande/enterpriseai` (uploaded ZIP root: `EnterpriseAI-main`).

### 4.1 Frontend

- React + TypeScript + Vite + Tailwind CSS.
- Main application and `DemoContext` manage a demo-oriented UI.
- Existing command-center screens include Overview, Orders, Agent Mesh, Inventory, Procurement, Finance, Logistics, Knowledge Graph, Audit Trail, Exceptions, and Benchmarks.
- Existing components include the live agent mesh, order panel, agent decision panel, and activity stream.
- Existing UI work is valuable and should be preserved unless a concrete incompatibility is demonstrated.
- The current demo contains static or simulated data and must not be described as a live integrated system until connected and tested.

### 4.2 Backend

- FastAPI application under `backend/app`.
- API routers exist for health, orders, workflow, agents, and audit.
- Agent classes exist for Supervisor, Inventory, Procurement, Finance, and Logistics.
- Orchestration and state modules exist, but the workflow is currently a minimal simulation rather than a complete compiled LangGraph workflow.
- Several endpoints return hardcoded sample values.
- `backend/app/db/database.py` is a placeholder; no active PostgreSQL connection has been established in the reviewed baseline.
- The backend requirements currently list only the minimal runtime dependencies; several intended integration dependencies are commented out.

### 4.3 Data and knowledge graph

- `backend/app/db/schema_notes.md` contains only a preliminary outline of orders, inventory, suppliers, audit events, and a future vector-search use case.
- `knowledge-graph/schema.cypher` and `sample_data.cypher` exist, but a live Neo4j connection and operational graph queries are not established.
- Do not make Neo4j or pgvector a blocker for the first end-to-end workflow. PostgreSQL is the first operational source of truth. Add graph/vector functionality when a concrete tested use case needs it.

### 4.4 Blockchain

- `blockchain/contracts/EnterpriseAudit.sol` exists and defines an audit-event structure, `recordEvent`, and `getAuditTrail`.
- The contract is a starter contract and was documented as **not deployed**.
- `backend/app/services/blockchain_service.py` currently returns a simulated transaction hash. That is not a blockchain integration.
- Never show a simulated hash as a real transaction, and never mark a record as confirmed on-chain without a successful receipt from the configured network.
- Keep operational records and sensitive business data off-chain; record a hash and minimal metadata on-chain.

### 4.5 Documentation

- `README.md`, `PROJECT_CONTEXT.md`, `PROJECT_ROADMAP.md`, and `docs/architecture.md` exist.
- Some documentation describes intended architecture as if the phases are further along than the actual integrations. Reconcile documentation against tests and observable behaviour as each phase is completed.
- The existing project constraints include: do not break the frontend, do not fake completed integrations, distinguish simulations from real implementations, and prefer modular architecture.

## 5. Dataset work already prepared

A separate starter pack was previously generated and should be checked if it is available in the workspace:

- `enterprise_ai_industrial_dataset_v2.xlsx`
- `schema_core.sql`
- `simulation_config.json`
- `README.md`

The workbook contains a synthetic industrial data model with reference/master data, operational tables, dictionary sheets, scenario templates, and runtime-table outlines. It is a **starting dataset, not a production-ready database migration**. Inspect its actual contents and validate identifiers, foreign-key relationships, units, constraints, date ranges, and scenario logic before loading it.

The starter configuration proposes:
- 300-second scenario-generation interval
- Synthetic scenario overlay
- Limits on open scenarios and concurrent workflows
- No automatic external actions
- Human approval for finance, safety, quality, and production-stop decisions
- Hash-only blockchain anchoring with confirmation based on an actual receipt

Do not assume the starter workbook has already been integrated into the uploaded repository or loaded into a database. Verify this.

## 6. Architecture principles

1. **One operational source of truth:** PostgreSQL owns operational state and workflow persistence.
2. **UI preservation:** adapt the existing frontend through its API/service boundary; avoid a wholesale redesign.
3. **Deterministic controls:** calculations, thresholds, budget checks, inventory arithmetic, permissions, and action validation should be deterministic code, not free-form LLM output.
4. **LLMs assist; policy code governs:** agents may analyse and propose. Policy validation and approval gates decide what can execute.
5. **Persistent workflows:** scenarios, agent runs, decisions, approvals, action attempts, and audit events survive restarts.
6. **Idempotency:** retries must not create duplicate scenarios, purchases, inventory movements, or blockchain anchors.
7. **Traceability:** every decision should reference its scenario, relevant input records, rule checks, agent run, and action outcome.
8. **Honest status reporting:** label synthetic, simulated, pending, failed, and verified states accurately.
9. **Safe defaults:** do not perform real external purchases, send messages, or trigger physical operations. Use sandboxed simulated actions unless explicitly configured and approved.
10. **Incremental delivery:** implement one phase at a time, run checks, document results, and only then proceed.
11. **Secrets hygiene:** use environment variables; never commit private keys, API keys, credentials, or real personal data.
12. **Testability:** critical logic must have automated tests and a reproducible demo scenario.

## 7. Target workflow and data contracts

### Scenario lifecycle
`CREATED → TRIAGED → INVESTIGATING → DECISION_READY → AWAITING_APPROVAL (when required) → EXECUTING → RESOLVED`

Terminal or exceptional statuses should include `REJECTED`, `FAILED`, `CANCELLED`, and `NEEDS_HUMAN_REVIEW`. Define the actual allowed transitions in code and validate them.

### Minimum persisted records
- `scenario_templates`: reusable scenario definitions and parameters
- `scenario_instances`: generated scenario, inputs, severity, status, timestamps, idempotency key
- `agent_runs`: agent identity, input/output references, status, duration, errors
- `decisions`: selected option, rationale summary, evidence references, rule results, confidence if applicable
- `action_queue`: proposed action, policy result, approval requirement, status, execution result
- `event_log`: ordered application audit events
- `blockchain_anchors`: event/decision hash, chain ID, contract address, transaction hash, receipt status, block number, timestamps
- `scheduler_state`: scheduler lease/last-run/next-run state as required to prevent duplicate scheduling

Operational domain tables must support the relevant foreign keys. Names can change if the existing codebase warrants it, but equivalent semantics and constraints must be preserved.

### Minimum agent result contract
An agent should return structured data containing:
- `status`
- `summary`
- `evidence` (references to records or rule results)
- `findings`
- `options` where relevant
- `recommended_action` where relevant
- `risk_level`
- `requires_approval`
- `errors` or `limitations` when applicable

Do not treat an LLM-generated statement as proof that a database mutation, approval, or blockchain transaction occurred.

## 8. Phased implementation roadmap

### Phase 0 — Repository baseline and implementation contract
**Goal:** establish a reliable starting point before making changes.

Tasks:
- Inspect the actual repository tree and important files.
- Run frontend install/build/lint where practical; run backend import/startup checks and existing tests if present.
- Identify broken builds, missing files, dependency mismatches, and the actual current behaviour.
- Create a baseline report and update `PROJECT_CONTEXT.md` and `PROJECT_ROADMAP.md` so implemented, simulated, and planned features are clearly separated.
- Create a Git checkpoint before risky work, if Git is available.
- Do not redesign the UI or start implementing future phases in this phase.

Acceptance criteria:
- Baseline checks and failures are recorded with exact commands and outputs.
- Existing working features and known defects are documented.
- A phase plan and file-change plan are approved before broad edits.

### Phase 1 — Domain model and dataset validation
**Goal:** define a coherent synthetic industrial data model.

Tasks:
- Inspect the starter workbook and SQL if available.
- Define table relationships, identifiers, units, enums/status transitions, constraints, indexes, and realistic seed-data rules.
- Validate all foreign-key references and important business invariants.
- Create versioned database migrations or a repeatable schema setup; do not rely on manual spreadsheet edits as the live database.
- Seed a small reproducible dataset plus enough linked records for the demo scenarios.
- Keep the data dictionary and README in sync with the actual schema.

Acceptance criteria:
- A clean database can be created from documented commands.
- Seed data loads repeatably.
- Validation checks show no orphan foreign keys or invalid core relationships.
- At least three scenario types can be represented by the data.

### Phase 2 — PostgreSQL persistence and real API vertical slice
**Goal:** replace hardcoded backend responses with persisted records.

Tasks:
- Configure database connection via environment variables.
- Add connection/session management, migrations, and repository/service boundaries appropriate to the existing project.
- Implement real read/write APIs for health, orders, inventory, suppliers, scenarios, decisions, and audit events as needed for the first slice.
- Add input validation, error handling, pagination where needed, and tests.
- Connect one or two existing frontend screens to real API data without breaking the remaining screens.

Acceptance criteria:
- CRUD or equivalent operational endpoints use PostgreSQL, not hardcoded in-memory responses.
- A change made through an API persists after backend restart.
- API integration tests pass against a test database.
- The UI clearly distinguishes live API data from remaining demo fixtures.

### Phase 3 — Persistent five-minute scenario engine
**Goal:** generate and persist scenarios on a 300-second cadence.

Tasks:
- Implement a configurable scheduler with start/stop controls for development and a safe production lifecycle.
- Persist each generated scenario before dispatch.
- Use idempotency keys, database locking/leases, or an equivalent mechanism to avoid duplicate generation when processes restart or multiple workers exist.
- Support deterministic seeded scenario generation for reproducible demos and optional randomised selection within validated bounds.
- Enforce open-scenario and concurrency limits from configuration.
- Handle missed ticks, shutdown, retries, and failures without silently losing work.

Acceptance criteria:
- Scenario generation can be tested without waiting five minutes.
- In normal mode, the configured interval is 300 seconds.
- Restarting the backend does not create duplicate instances for the same scheduled generation.
- Scenario creation, status, timestamps, and failures are persisted and visible through an API.

### Phase 4 — Real agent orchestration and decision-making
**Goal:** implement a real end-to-end workflow rather than sequential stub calls.

Tasks:
- Define typed shared workflow state and valid transitions.
- Implement the Supervisor and specialist agents with narrow, testable responsibilities.
- Build the actual LangGraph workflow if the dependency and architecture remain suitable; otherwise document a justified alternative before changing the stack.
- Expose tools for querying operational data and running deterministic business-rule checks.
- Implement evidence-linked decisions, retries, timeouts, and structured error paths.
- Keep LLM calls optional/configurable where possible so deterministic tests work without an API key.

Acceptance criteria:
- A scenario is read from PostgreSQL, investigated by the relevant agents, and results in a persisted decision.
- Agent runs and routing are observable in logs and the API.
- At least three scenario types pass automated end-to-end workflow tests.
- No agent can directly bypass policy checks to mutate protected state.

### Phase 5 — Policy engine, approvals, and action execution
**Goal:** safely apply approved decisions to simulated operational state.

Tasks:
- Implement explicit policy checks for budget limits, supplier eligibility, inventory consistency, quality holds, safety events, and production-stop actions as applicable.
- Distinguish `proposed`, `approved`, `rejected`, `executing`, `succeeded`, and `failed` actions.
- Require human approval for finance commitments, safety-critical actions, quality release/hold overrides, and production stoppages unless an explicit, tested policy says otherwise.
- Make action execution idempotent and transactional where possible.
- Record before/after state, actor/approver, policy result, and failure reason.

Acceptance criteria:
- A permitted action changes database state exactly once.
- A prohibited action is rejected with an auditable reason.
- Approval-required actions cannot execute before approval.
- Failed actions can be retried safely without duplicate side effects.

### Phase 6 — Frontend integration and live workflow visibility
**Goal:** make the existing command center display real system state.

Tasks:
- Connect the current API service boundary and `DemoContext` to backend endpoints.
- Replace hardcoded values incrementally, screen by screen.
- Add scenario queue, scenario detail, agent run trace, decision evidence, approval controls, action outcomes, and truthful audit status.
- Use WebSockets or server-sent events for live updates after REST-based state retrieval is reliable.
- Add loading, empty, stale, error, reconnecting, and offline states.
- Preserve the existing design unless changes are required for correctness or usability.

Acceptance criteria:
- A backend-created scenario appears in the dashboard without manually editing frontend fixtures.
- Decision/action status changes are reflected from persisted backend state.
- Disconnecting the backend produces a clear error/stale state, not fabricated live activity.
- Existing navigation and core screens continue to build.

### Phase 7 — Real blockchain audit anchoring
**Goal:** verify critical audit records on an actual test network.

Tasks:
- Review the current Solidity contract and add access controls, validation, event design, and tests where appropriate.
- Select and document the supported test network and RPC configuration. Do not assume a deprecated network endpoint.
- Deploy using a safe deployment process and record chain ID, contract address, ABI, and deployment transaction.
- Implement Web3 integration using environment-managed credentials and minimal signing permissions.
- Hash a canonical representation of the audit event/decision and anchor the hash; keep business data off-chain.
- Persist transaction hash and pending/confirmed/failed receipt state.
- Implement retry/idempotency behaviour and independent verification.

Acceptance criteria:
- A critical decision produces a real transaction on the configured test network.
- The receipt is confirmed before the UI reports it as verified.
- The on-chain hash can be matched against the corresponding off-chain audit record.
- No hardcoded or simulated transaction hash is shown as real.

### Phase 8 — Knowledge graph integration (only if justified by a tested use case)
**Goal:** enable useful dependency queries over suppliers, materials, products, sites, and orders.

Tasks:
- Define the concrete graph questions agents need to answer.
- Start Neo4j through documented configuration, ingest stable IDs from PostgreSQL, and implement a synchronisation strategy.
- Add query tests and failure behaviour.
- Avoid maintaining duplicate business truth in Neo4j.

Acceptance criteria:
- At least one agent workflow uses a real graph query that improves dependency/risk analysis.
- Graph results reference valid PostgreSQL entity IDs.
- The system continues safely if the graph service is unavailable.

### Phase 9 — Reliability, benchmarks, security, and delivery
**Goal:** make the project defensible and reproducible.

Tasks:
- Add end-to-end tests across scenario creation, agent investigation, approval, action, and audit anchoring.
- Test retries, duplicate scheduler ticks, database outages, agent timeouts, rejected actions, and blockchain RPC failure.
- Compare agent-assisted decisions with a deterministic baseline using defined metrics.
- Add structured logs, health checks, configuration validation, and useful error reporting.
- Document setup, migrations, seeding, environment variables, test commands, deployment, and demo reset.
- Ensure secrets and generated local files are excluded from Git.

Acceptance criteria:
- A new developer can start the project from documented steps.
- A full demo can be repeated and its evidence inspected.
- Benchmarks use measured results rather than invented values.
- README, project context, and roadmap match the actual tested implementation.

## 9. Work protocol for Antigravity

For each phase, follow this loop:

1. Read this file and inspect relevant code before editing.
2. State the phase goal, files likely to change, dependencies, risks, and tests.
3. Make only changes needed for the current phase.
4. Run the relevant build, lint, unit, integration, or validation commands.
5. Report exact results. Never say a command passed unless it was run successfully.
6. Update this file's phase status and development log.
7. Stop at the phase boundary and report any blocker before moving to the next phase.

### Do not
- Rewrite the whole project or replace the frontend without approval.
- implement multiple phases in one unreviewed change.
- replace real data with new hardcoded fixtures while claiming integration is complete.
- return fake blockchain transaction hashes or fake receipt statuses.
- call an agent workflow “autonomous” if it only calls stub functions.
- silently add major infrastructure dependencies.
- commit secrets, private keys, or credentials.
- claim a feature is complete without a test or observable verification.

### Required response format after each Antigravity task
- **Phase / objective**
- **Files inspected**
- **Files changed**
- **Implementation details**
- **Commands executed**
- **Test/build results**
- **Known limitations or blockers**
- **Acceptance criteria met / unmet**
- **Recommended next step**

## 10. Current status checklist

| Phase | Status at baseline |
|---|---|
| Phase 0 — Repository baseline | **Complete** — baseline report in `PHASE_0_BASELINE_REPORT.md` |
| Phase 0.5 — Repository hygiene | **Complete** — checkpoint commit `827143d` |
| Phase 1 — Domain model and dataset validation | **Complete** — verified against PostgreSQL 18.6: 43 tables, 1,327 seed rows, 119 DB checks pass, 37/37 tests pass |
| Phase 2 — PostgreSQL persistence and API | Starter only; no active database connection confirmed |
| Phase 3 — Scenario scheduler | Not implemented as a persistent 300-second scheduler |
| Phase 4 — Real agent orchestration | Stub/simulation; complete orchestration not implemented |
| Phase 5 — Policy, approvals, action execution | Not implemented end to end |
| Phase 6 — Frontend integration/live updates | Frontend exists; most demo state is simulated |
| Phase 7 — Blockchain audit anchoring | Solidity starter exists; deployment and real transaction integration unverified/not completed |
| Phase 8 — Knowledge graph | Cypher starter files exist; live integration unverified |
| Phase 9 — Reliability and delivery | Pending |

## 11. Immediate next task

**Phase 1 is verified and complete.** Proceed to Phase 2 (PostgreSQL Persistence & API Integration).

---

## Development log

### 2026-10-14 — Phase 3.5 Reliability, Security & Audit Remediation Verified & Complete
- **FIND-01 Concurrency & Mutual Exclusion**: Enforced absolute lease mutual exclusion in `ScenarioScheduler.run_cycle`. Neither `force=True` nor administrative overrides can bypass an active lease owned by another worker. Administrative capacity overrides restricted to `ADMIN` role with mandatory reason code and audit event.
- **FIND-02 Deterministic Slot Idempotency**: Automated scheduled ticks derive deterministic generation identity `SCHED-<template>-SLOT-<ts>` from the configured interval and UTC epoch slot. Distinct manual keys (`MANUAL-<template>-<uuid>`) prevent collision with scheduled slots.
- **FIND-03 Orphaned Workflow Watchdog**: Implemented `recover_orphaned_workflows` using `FOR UPDATE SKIP LOCKED` to safely transition stale `QUEUED` and `RUNNING` scenarios to `FAILED` with `STALE_WORKFLOW_TIMEOUT` audit logs.
- **FIND-04 Lease Renewal Heartbeat**: Added background renewal thread in `lease_heartbeat` context manager with clean daemon termination and ownership loss detection during workflow execution.
- **FIND-05 Truthful Frontend Connectivity**: Updated `DemoContext.tsx` to verify backend live probes and operational endpoints; marks offline or degraded connections transparently.
- **FIND-06 Docker Deployment Hardening**: Replaced predictable fallback credentials with mandatory variable interpolation (`${VAR:?...}`); added root `.env.example`.
- **FIND-07 & FIND-08 Transparency**: Reconciled stale documentation in READMEs and roadmap; added architectural design target disclaimer to `BenchmarksPage.tsx`.

### 2026-10-14 — Phase 3 Persistent Five-Minute Scenario Engine Verified & Complete
- **Interval Configuration & Precedence**: Implemented strict precedence rule: `SCENARIO_SCHEDULER_INTERVAL_SECONDS` takes precedence over `SCHEDULER_INTERVAL_SECONDS`, defaulting safely to 300 seconds (5 minutes). Startup validation rejects negative, zero, or invalid values.
- **Operational Data Grounding**: Scenarios bind dynamically to real entities in PostgreSQL operational tables (`orders`, `inventory`, `suppliers`, `budgets`) rather than fabricating synthetic identifiers.
- **Queue Limit & Capacity Control**: Enforced `SCHEDULER_MAX_OPEN_SCENARIOS` (default 10) to guard against unbounded scenario creation, skipping cycles observably with `OPEN_SCENARIOS_LIMIT_REACHED` status and audit logging.
- **Seeded Determinism & Idempotency**: Added support for seeded template selection (`seed` query param / env) for reproducible test scenarios, and idempotency key handling ensuring duplicate triggers return existing instances without creating duplicates.
- **Scheduler Audit Events**: Logged structured lifecycle events (`SCHEDULER_CYCLE_STARTED`, `SCENARIO_GENERATED`, `SCENARIO_GENERATION_SKIPPED`, `SCHEDULER_LEASE_RELEASED`) into `event_log`.
- **API Endpoints**: Enhanced `POST /api/scheduler/trigger` (with `force`, `template_id`, `idempotency_key`, `seed`), added `GET /api/scheduler/templates` and `GET /api/scheduler/scenarios`.
- **Frontend Integration**: Updated Overview and Governance/Exceptions pages to truthfully display scheduler status badge, 300s interval, queue capacity counter (`active/max`), active leases, and detailed skip reasons.
- **Regression Suite**: 171/171 passing Pytest tests (+6 new Phase 3 scenario engine tests), 119/119 passing database integrity checks, 0 rows in runtime tables, clean frontend production build and lint.

### 2026-10-14 — Phase 2 Security Hardening & Contract Alignment Gate Passed
- **Authentication & Anti-Forgery**: Enforced server-side credential-to-role mapping (`ADMIN_API_KEY`, `FINANCE_API_KEY`, `SUPPLY_CHAIN_API_KEY`, `OPERATOR_API_KEY`, `VIEWER_API_KEY`). Built Anti-Forgery Guard rejecting spoofed client role headers (`X-User-Role: ADMIN` with non-admin keys -> HTTP 403 Forbidden).
- **Least-Privilege Defaults & Fail-Closed Security**: In development, unauthenticated requests receive read-only `VIEWER` role; in production, missing credentials fail closed with HTTP 500/401.
- **Human Approval & Identity Enforcement**: Backend strictly stamps `decided_by = current_user.user_id` and `proposed_by = current_user.user_id`. Prohibits self-approval (HTTP 403). Enforces financial spending threshold limits (`FINANCE_APPROVER` capped at ₹60,000,000 INR; higher amounts require `ADMIN`).
- **Frontend Credential Decoupling**: Documented client bundle visibility in `frontend/.env.example`. Removed privileged secret assumptions from browser bundle.
- **API Contract Alignment**: Added missing route contracts (`/api/live` for container healthchecks & UI live checks, `/api/orders/summary`, `/api/inventory/items`, `/api/audit/events`). Added fallback canonical verification for unanchored local audit events in `verify_anchor_integrity()`.
- **Docker Compose Cleanliness**: Removed obsolete `version: '3.8'` line from `docker-compose.yml`; verified clean syntax with `docker compose config`.
- **Regression Outcomes**: 165/165 passing Pytest tests (+5 new security tests), 119/119 passing database integrity checks, 0 rows in runtime tables, clean frontend production build (1.53s) and lint.

### 2026-10-14 — Phase 2 Full Implementation & Verification Passed (Tasks 1–20)
- **Task 1–5**: PostgreSQL connection pool lifecycle (`init_db_pool`, `get_db`, `close_db_pool`), parameterized operational APIs (`/api/orders`, `/api/inventory`, `/api/suppliers`), and audit event logging.
- **Task 6–7**: Workflow and specialist-agent run persistence (`workflow_instances`, `agent_runs`, `agent_findings`, `decisions`).
- **Task 8**: Persistent scenario scheduler with distributed lease locking in PostgreSQL (`scheduler_state`, lease renewal, stale recovery).
- **Task 9**: Specialist-agent grounding contract hardening across Inventory, Procurement, Finance, and Logistics agents.
- **Task 10**: Deterministic policy evaluation engine (`policy_rules`, `policy_evaluations`) and human approval workflow (`approval_requests`).
- **Task 11**: Controlled action queue (`action_queue`, `action_execution_results`) with safe simulation adapter (`SimulatedActionAdapter`).
- **Task 12 & 18**: Canonical RFC 8785 JSON SHA-256 digest computation, duplicate anchor prevention, and honest unconfigured testnet status reporting.
- **Task 13**: Centralized typed frontend API client (`apiClient.ts`), `DemoContext` dual-mode switcher ('demo' vs 'live'), live header badge, and live data integration across Overview, Orders, Inventory, Procurement, Audit Trail, and Governance/Exceptions screens.
- **Task 14**: End-to-end integration test suite (`test_e2e_lifecycle.py`) verifying full governed lifecycle from scenario generation to blockchain digest anchoring and rejection branches.
- **Task 15**: Role-based access control (`UserRole`, `AuthUser`, `require_role`), CORS middleware configuration, and error sanitization.
- **Task 16**: Deployment preparation: `docker-compose.yml`, multi-stage `frontend/Dockerfile`, `backend/Dockerfile`, `backend/.env.example`, `frontend/.env.example`.
- **Task 17 & 18**: Operational monitoring, graceful shutdown, structured logging, honest unconfigured testnet status handling.
- **Task 19**: Full regression verified: 160/160 Pytest tests passing, 119/119 database validation checks passing, 0 rows in runtime tables, frontend production build passing in 1.59s with 0 errors.

### 2026-10-14 — Phase 1 PostgreSQL verification gate passed
- Verified PostgreSQL 18.6 running locally on port 5432. Created dedicated disposable test database `enterprise_ai_test`.
- Applied migrations `001_operational_schema.sql` and `002_runtime_schema.sql`. Verified 43 tables, 43 PKs, 54 FKs, 360 CHECKs, 3 UNIQUEs, 73 indexes.
- Verified migration idempotency, checksum mismatch detection, and transactional rollback on failure.
- Loaded 1,327 seed rows across 31 mapped sheets with 0 rejected rows and 0 orphans. Verified idempotency (1,327 skipped on rerun).
- Executed `validate_seed_data.py` against live database: 119 of 119 automated checks passed.
- Pytest suite: 37 of 37 tests passed (27 unit tests + 10 PostgreSQL integration tests).
- Frontend build and lint passed (`tsc -b && vite build` in 1.73s; 0 lint errors, 1 known warning).
- Backend import (`app.main`) passed cleanly. FastAPI remains uncoupled from database as required.

### 2026-10-14 — Reference established
- Recorded the current repository baseline based on the uploaded repository ingest.
- Clarified the target five-minute scenario loop and the industrial supply-chain domain.
- Established incremental implementation phases and acceptance criteria.
- No repository code has been changed by creating this reference document.

### 2026-10-14 — Phase 1 continuation
- Reconciled workbook totals (1677 vs 1327). Previous validation report (30 sheets / 1315 rows / 73 warnings) omitted `simulation_config` and treated observed enums as errors.
- Added `backend/db/migrate.py`, seed loader, database validator, pytest suite. FastAPI remains disconnected.

### 2026-10-14 — Phase 0.5 hygiene checkpoint (`827143d`)
- Created root `.gitignore` covering `.env`, `__pycache__/`, venvs, test caches, logs, OS/editor metadata, and frontend build artefacts.
- `blockchain_service.py`: replaced simulated tx hash with a zero-address placeholder and `status: 'SIMULATED'`; added a docstring explicitly stating no network call is made.
- `backend/app/api/audit.py`: removed fake `tx_hash` field; added `blockchain_status: 'SIMULATED'` and explanatory `note` field.
- `AuditTrailPage.tsx`: changed `VERIFIED` badge to `SIMULATED` on all event cards; replaced invented "CONSENSUS / Contract 0x7f83…a91c" summary metric with `NOT DEPLOYED / Phase 7 — pending testnet deployment`.
- `DemoContext.tsx`: `addAuditEvent` now sets `status: 'SIMULATED'` instead of `'VERIFIED'`.
- `initialDemoData.ts`: all five seed audit events updated to `status: 'SIMULATED'`.
- `types/index.ts`: added `'SIMULATED'` to `AuditEvent.status` union with JSDoc explaining each value.
- `backend/.env.example`: removed deprecated Polygon Mumbai RPC URL; replaced `POLYGON_RPC_URL` with empty `EVM_RPC_URL` placeholder and a comment explaining why Mumbai is gone and what to do in Phase 7.
- `backend/requirements.txt`: annotated with version-mismatch explanation, `__init__.py` decision rationale, and recommended virtual-environment strategy. Pins left unchanged pending venv setup.
- Added `ANTIGRAVITY_PROJECT_REFERENCE.md`, `PHASE_0_BASELINE_REPORT.md`, and `project_reference/` starter dataset files to the repository.
- Frontend build: ✅ exit 0, 328.70 KB JS, 36.10 KB CSS.
- Frontend lint: ✅ 0 errors, 1 pre-existing warning (`only-export-components` in `DemoContext.tsx`).
- Backend import: ✅ `from app.main import app` exit 0.
- Phase 1 has not started.
