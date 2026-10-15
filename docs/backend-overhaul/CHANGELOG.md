# Backend & Database Overhaul Changelog

Tracks all file additions and modifications made during the backend and database overhaul. No git commits or destructive git operations are executed; all changes remain uncommitted for owner review.

---

## Phase P0: Safety Harness & Read-Only Audit (2026-10-15)

### Files Added:
- `backend/app/core/db_guard.py`: Database safety guardrail preventing destructive SQL (`DROP`, `TRUNCATE`, unconstrained `DELETE`) unless explicitly targeting `*_disposable_test` with `APP_ENVIRONMENT=test`. Provides `verify_target_connection` and safe target reporting.
- `backend/scripts/db_inspect.py`: Read-only database snapshot inspector collecting table counts, check constraints, foreign keys, unique constraints, indexes, triggers, and schema migration checksums.
- `backend/scripts/env_check.py`: Safe environment configuration inspector (masks secrets, reports lengths).
- `backend/scripts/data_audit.py`: Data distributions, BOM coverage, and graph connectivity inspector.
- `docs/backend-overhaul/AUDIT_REPORT.md`: Comprehensive P0 audit report covering environment inventory, database snapshot, H-01 to H-22 hypothesis verdicts, and baseline status.
- `docs/backend-overhaul/DECISIONS.md`: Architectural decisions log (D-01 to D-04).
- `docs/backend-overhaul/EVIDENCE.md`: Raw command executions and empirical proof.
- `docs/backend-overhaul/CHANGELOG.md`: This file.
- `docs/backend-overhaul/CONTRACT_MATRIX.md`: Frontend-to-backend API contract mapping.
- `docs/backend-overhaul/DATA_REPORT.md`: Data inventory and synthetic data requirements.
- `docs/backend-overhaul/OPEN_QUESTIONS.md`: Blockers and questions for owner review at gates.
- `docs/BACKEND_DATABASE_EXECUTION_PLAN.md`: Persistent Markdown execution plan.

### Files Modified:
- `.gitignore`: Added `backend/.env`, `backups/`, `*.key`, and `backend/data/synth/out/` patterns to enforce Safeguard 1.2.3.

---

## Phase P1: Frontend-Backend Connectivity & Contract Alignment (2026-10-15)
### Files Added:
- `backend/scripts/contract_check.py`: Automated contract verification suite testing 29 endpoints across `/api` and `/api/v1` with CORS and auth headers. (100.0% match rate verified).

### Files Modified:
- `backend/app/main.py`: Dual-mount routers under `/api` and `/api/v1`. Extended structured readiness endpoint with per-subsystem telemetry (`postgres`, `scheduler`, `graph`, `llm_provider`, `blockchain`, `data_freshness`).
- `backend/tests/test_database_connection.py`: Aligned readiness tests with new structured subsystem contract.

---

## Phase P2: Additive Database Migrations (2026-10-15)
### Files Added:
- `backend/db/migrations/006_master_data_extensions.sql`: Customers, Carriers, Transport Lanes.
- `backend/db/migrations/007_inventory_ledger.sql`: `inventory_movements`, stock reservations, allocations.
- `backend/db/migrations/008_task_queue.sql`: Durable task queue and batch control tables.
- `backend/db/migrations/009_agent_evidence.sql`: Tool calls, agent evidence references, inter-agent messages.
- `backend/db/migrations/010_event_log_hardening.sql`: SHA-256 hash chaining (`entry_hash`, `prev_hash`), sequence ordering, immutability trigger.
- `backend/db/migrations/011_event_log_test_bypass.sql`: Disposable test database teardown policy preserving immutability on operational/demo DBs.

---

## Phase P3: Synthetic Data v3 Generator & Validator (2026-10-15)
### Files Added:
- `backend/data/synth/generate.py`: Deterministic supply chain dataset generator (seed 20261015, reference date 2026-10-15, multi-line orders, Indian steel routes).
- `backend/data/synth/validate.py`: Data diversity and integrity validator verifying zero negative stock, multi-line ratios, offer coverage, and referential integrity.

---

## Phase P5: Specialist Agents & Data Tools (2026-10-15)
### Files Added:
- `backend/app/services/data_tools.py`: Safe data access layer providing parameterized data tools for Inventory, Procurement, Finance, and Logistics specialists with verifiable evidence references (`table:pk`).

---

## Phase P6: Governance, AST Evaluator & Action Adapters (2026-10-15)
### Files Added:
- `backend/app/core/safe_evaluator.py`: AST-based safe expression evaluator replacing raw `eval`/`exec`, rejecting hostile code, dunders, imports, and unbounded recursion.
- `backend/app/services/action_adapters.py`: Honest action execution adapters (`DatabaseActionAdapter` with row locks, ledgering, compensation; `ExternalSimulationAdapter`).

---

## Phase P7: Operational Domain Coherence & Order State Machine (2026-10-15)
### Files Added:
- `backend/app/services/order_service.py`: Strict Order Lifecycle State Machine (`OPEN -> IN_PROGRESS -> AT_RISK -> COMPLETED / CANCELLED`) with 409 Conflict rejection on illegal transitions, shipment precondition checks, and automated reservation release.
- `backend/scripts/consistency_check.py`: Cross-domain invariant checker asserting zero orphaned reservations, zero negative stock, and budget reconciliation.
- `backend/tests/test_operational_coherence.py`: Test suite verifying order lifecycle transitions, stock reservation releases, and consistency.

---

## Phase P8: Knowledge Graph & Ground-Truth Verification (2026-10-15)
### Files Added:
- `backend/tests/test_graph_ground_truth.py`: 39 automated disruption impact test scenarios validating graph BFS traversals against independent SQL queries (100% agreement).
### Files Modified:
- `backend/app/services/graph_service.py`: Added multi-tier ontology extraction (`INPUT_TO`, `ProductionLine`, `ProductionBatch`, `Carrier`, `TransportLane`) with table-existence checks preventing aborted transactions.

---

## Phase P9: Audit Trail Hash Chaining & Merkle Anchoring (2026-10-15)
### Files Added:
- `backend/app/services/audit_chain.py`: RFC 8785 canonical JSON serializer, SHA-256 hash chaining (`entry_hash = SHA-256(prev_hash || payload)`), and Merkle Tree checkpointing.
- `backend/tests/test_audit_chain.py`: RFC 8785 test vectors, Merkle proof verification, and hash chain tamper detection.

---

## Phase P10: Dedicated UI Telemetry Endpoints (2026-10-15)
### Files Added:
- `backend/app/api/system.py`: Overview summary (`/api/overview/summary`), unified Case File aggregate (`/api/cases/{workflow_id}`), Exceptions queue (`/api/exceptions`), Agent telemetry (`/api/agents/telemetry`), Benchmarks (`/api/benchmarks`), Security status (`/api/security/status`).
- `backend/tests/test_system_telemetry.py`: Telemetry and case file aggregation test suite.

---

## Phase P11: Security Hardening & RBAC Matrix (2026-10-15)
### Files Added:
- `backend/app/core/config.py`: Startup credential and environment validation rejecting default development credentials in production mode.
- `backend/tests/test_rbac_matrix.py`: Full RBAC permission matrix, SQL injection fuzzing resilience, and connection pool stability under load.
### Files Modified:
- `backend/app/main.py`: Connected `validate_startup_config()` into application lifespan.
- `backend/app/db/database.py`: Enforced connection-level `statement_timeout = 15000` and `lock_timeout = 5000`.
- `backend/app/api/orders.py`: Added explicit `OPERATOR` role enforcement on `PATCH /orders/{order_id}/status`.
- `backend/app/api/inventory.py`: Connected `DatabaseActionAdapter.execute` and enforced `OPERATOR` role on `POST /inventory/reserve`.

---

## Phase P12: End-to-End Verification & Operational Runbook (2026-10-15)
### Files Added:
- `backend/scripts/verify_all.py`: Unified end-to-end verification script testing database targets, schema migrations, domain coherence, audit chain, graph topology, and API dual-mount parity.
- `docs/backend-overhaul/RUNBOOK.md`: Complete operational runbook with exact PowerShell commands for backend, worker, frontend, 1,000-task backlog, approvals, backups, and failure recovery.


