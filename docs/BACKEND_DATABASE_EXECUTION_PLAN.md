# Enterprise AI Mesh: Backend & Database Execution Plan

**Document Path:** `docs/BACKEND_DATABASE_EXECUTION_PLAN.md`  
**Author:** Antigravity Engineering Agent  
**Last Updated:** 2026-10-15  
**Version:** 1.0.0  
**Status:** Completed — All Phases P0 through P12 Implemented & Verified (330/330 Passing Tests)  

---

## 1. Project Objectives & Scope

The Enterprise AI Mesh frontend redesign is 100% complete across all 14 screens, establishing a fixed integration contract with design tokens, strict role-based views, and a dedicated 7-step Case File architecture. 

The objective of this plan was the complete end-to-end overhaul and verification of the backend (`backend/`), the PostgreSQL database, synthetic data generation, multi-agent orchestration, the knowledge graph, and the tamper-evident audit trail.

### Key Tenets & Mandates
1. **Preservation:** The frontend is treated as a frozen integration contract. Working baseline functionality (300/300 passing tests) and operational database records (`event_log`, `scenario_instances`, `blockchain_anchors`) have been preserved, expanding to 330 passing tests.
2. **Honesty:** Zero fabricated liveness. Subsystems report truthful states (`live`, `simulated`, `fallback`, `unavailable`). No unproven claims.
3. **Safety First:** Strict refusal of destructive DDL (`DROP`, `TRUNCATE`, unconstrained `DELETE`) enforced by `db_guard.py`. Real operational writes protected by Gate safeguards and pre-migration backups.
4. **Observable & Durable:** Single tasks and ~1,000-task backlogs execute with ACID durability, restart resiliency, and exactly-once state transitions.
5. **Grounded Multi-Agent Orchestration:** Specialist agents perform deterministic domain computations citing evidence references, while LLM recommendations are routed through a 7-key Gemini API pool with OpenRouter fallback.

---

## 2. Findings from the Initial Audit (Phase P0 Baseline)

| Item | Verified Reality | Evidence & Notes |
|---|---|---|
| **Working Tree** | Clean on branch `main` | Zero uncommitted changes at audit start |
| **Test Suite Baseline** | **300 passed in 33.71s** | `pytest backend/tests -q` executed against `enterprise_ai_disposable_test` |
| **Current Test Suite** | **330 passed in 44.45s** | Zero failures, zero skips across all 12 phases |
| **Operational DB** | `enterprise_ai_test` | 43 tables, 388 event log rows, 2 blockchain anchors, 62 scenarios, 200 orders (Preserved) |
| **Disposable DB** | `enterprise_ai_disposable_test` | Migrations 001-012 applied, verified clean |
| **Database Migrations** | 12 migrations applied | 001 to 012 applied forward-only and checksummed |
| **Gemini API Keys** | **ALL 7 KEYS PRESENT** | `GEMINI_API_KEY_1` to `_7` configured in local environment (len=53) |
| **OpenRouter Fallback** | Configured (len=73) | Present in local environment |
| **LLM Provider Mode** | `LIVE` | Ready for approved live execution |
| **Blockchain Mode** | `SIMULATE_BLOCKCHAIN=true` | Sepolia contract deployed at `0xf7aE6E373be5ad0f9444D230f285e8E620b70b63` |
| **Docker / Neo4j** | Docker daemon inactive | `RelationalGraphEngine` operational as high-availability fallback |
| **Route Alignment** | Dual-mounted (`/api` & `/api/v1`) | 100.0% match rate across 29 frontend endpoints |

---

## 3. Overall Phases & Task Breakdown

### Phase P0: Safety Harness & Read-Only Audit
- [x] **Task P0.1:** Verify git status, environment tools (`pg_dump`, Python 3.12, Node 22).
- [x] **Task P0.2:** Create safety harness `backend/app/core/db_guard.py` (target check, destructive DDL refusal).
- [x] **Task P0.3:** Create read-only database snapshot script `backend/scripts/db_inspect.py` and capture baseline snapshots.
- [x] **Task P0.4:** Safely inspect environment configuration and verify Gemini API key pool (`backend/scripts/env_check.py`).
- [x] **Task P0.5:** Run workbook validation (`run_validation.py`) and capture data distributions (`data_audit.py`).
- [x] **Task P0.6:** Audit code and evaluate hypotheses H-01 through H-22 with empirical evidence.
- [x] **Task P0.7:** Create documentation hub (`docs/backend-overhaul/` and execution plan).
- [x] **Gate G1 Approval:** Present P0 audit findings and phase sequence to owner (Confirmed: Proceed with backend overhaul).

---

### Phase P1: Frontend-Backend Connectivity & Contract Alignment
- [x] **Task P1.1:** Build `backend/scripts/contract_check.py` to validate 100% of frontend routes against backend API (100% match rate across 29 endpoints).
- [x] **Task P1.2:** Mount `/api/v1` aliases in `app/main.py` mirroring `/api` to prevent any prefix divergence.
- [x] **Task P1.3:** Enhance `/api/health/ready` to return structured per-subsystem objects (`postgres`, `scheduler`, `graph`, `llm_provider`, `blockchain`, `data_freshness`).
- [x] **Task P1.4:** Standardize API error response format across all routers (`{"error": {"code", "message", "details", "correlation_id"}}`).
- [x] **Task P1.5:** Validate CORS configuration for both `localhost:5173` and `127.0.0.1:5173`.
- [x] **Task P1.6:** Execute ONE governed pipeline from frontend / API against PostgreSQL and capture full telemetry trace (Completed: Workflow `ea66645e-1f55-4f42-b0c2-230428121351`).

---

### Phase P2: Database Model Gap Analysis & Additive Migrations
- [x] **Task P2.1:** Implement migration `006_master_data_extensions.sql` (Customers, Carriers, Transport Lanes).
- [x] **Task P2.2:** Implement migration `007_inventory_ledger.sql` (`inventory_movements` transactional ledger, allocations, stock reservations).
- [x] **Task P2.3:** Implement migration `008_task_queue.sql` (Durable batch and work queue tables for 1,000-task engine).
- [x] **Task P2.4:** Implement migration `009_agent_evidence.sql` (Tool call logging, evidence references, inter-agent messages).
- [x] **Task P2.5:** Implement migration `010_event_log_hardening.sql` (Sequential order, `prev_hash`, `entry_hash`, immutable UPDATE/DELETE trigger).
- [x] **Task P2.6:** Test migrations cleanly on `enterprise_ai_disposable_test` (Migrations 006-012 applied and checksum-verified).

---

### Phase P3: Synthetic Data v3 (Realistic Supply Chain Data)
- [x] **Task P3.1:** Build deterministic generator `backend/data/synth/generate.py` with reproducible seed and `manifest.json`.
- [x] **Task P3.2:** Generate expanded catalog (26 SKUs, multi-tier BOM, 60 customers with Pareto distribution).
- [x] **Task P3.3:** Generate 1,510 realistic orders with multi-line items (55.4% multi-line), correlated pricing, priorities, and deadlines.
- [x] **Task P3.4:** Generate carrier lanes (133 lanes, 10 carriers) and 32 suppliers with 77 offers.
- [x] **Task P3.5:** Build data diversity validator `backend/data/synth/validate.py` (validated with zero errors).
- [x] **Task P3.6:** Maintain original 1,327 seed rows completely untouched.

---

### Phase P4: Durable Task Model & 1,000-Task Execution Engine
- [x] **Task P4.1:** Implement task queue worker `app/worker.py` utilizing `SELECT ... FOR UPDATE SKIP LOCKED` with lease heartbeats and reaper.
- [x] **Task P4.2:** Enforce exactly-once transitions and idempotency keys across all tasks and agent phases.
- [x] **Task P4.3:** Size database connection pool and threadpool execution to guarantee `/api/health` stays responsive under load.
- [x] **Task P4.4:** Implement preloaded backlog generator creating ~1,000 diverse tasks mapped to the 15 scenario templates.
- [x] **Task P4.5:** Implement batch control APIs (`app/api/tasks.py`: create, list, pause, resume, cancel, retry).
- [x] **Task P4.6:** Validate restart recovery and automated lease expiry reaper.

---

### Phase P5: Specialist Agents & Grounded Multi-Agent Orchestration
- [x] **Task P5.1:** Implement internal data tools layer with parameterized queries returning structured evidence references (`table:pk`).
- [x] **Task P5.2:** Enhance deterministic specialist agent computations across Inventory, Procurement, Finance, and Logistics.
- [x] **Task P5.3:** Support multi-key Gemini API pool (`GEMINI_API_KEY_1` to `_7`) with cyclic rotation and cooldown tracking.
- [x] **Task P5.4:** Enforce strict Pydantic output contracts and fail-closed handling for malformed or missing evidence.
- [x] **Task P5.5:** Persist all agent steps, tool calls, and evidence references into `agent_runs` and `event_log`.

---

### Phase P6: Governance, Approvals & Controlled Actions
- [x] **Task P6.1:** Build safe AST-based condition expression evaluator for `business_rules` (prohibiting eval/exec).
- [x] **Task P6.2:** Enforce strict approval state machine (`PENDING -> APPROVED | REJECTED | EXPIRED`) with 409 conflict on double decision.
- [x] **Task P6.3:** Implement `DatabaseActionAdapter` with row locks (`SELECT ... FOR UPDATE`), pre-condition checks, and transactional rollback.
- [x] **Task P6.4:** Implement state-change ledger recording before/after changes.
- [x] **Task P6.5:** Implement compensating transaction handlers for reversible actions (stock unreserve, PO cancellation).
- [x] **Task P6.6:** Run negative test matrix (budget breach without approval, concurrent reserve oversell prevention).

---

### Phase P7: Domain Operational Coherence
- [x] **Task P7.1:** Implement formal order state machine in `order_service.py` (`OPEN -> IN_PROGRESS -> AT_RISK -> COMPLETED / CANCELLED`).
- [x] **Task P7.2:** Transactional inventory reservations with row locks and automatic release on order cancellation.
- [x] **Task P7.3:** Procurement lifecycle with PO states, goods receipt posting to inventory, and quality hold segregation.
- [x] **Task P7.4:** Financial reconciliation endpoint and test (`SUM(POs) == committed_spend_inr`).
- [x] **Task P7.5:** Automated cross-domain consistency checker (`consistency_check.py`).

---

### Phase P8: Knowledge Graph & Multi-Hop Disruption Analysis
- [x] **Task P8.1:** Expand graph ontology beyond 6 entity types (add ProductionLines, Batches, Carriers, Lanes, POs, BOM links).
- [x] **Task P8.2:** Implement unified graph extractor generating interconnected nodes and edges from PostgreSQL.
- [x] **Task P8.3:** Implement multi-hop disruption impact algorithm (Supplier -> Raw Material -> Finished Product -> Orders -> Customers -> Revenue at Risk).
- [x] **Task P8.4:** Ground truth verification test: compare graph impact against independent SQL queries across 39 disruption scenarios (100% agreement).
- [x] **Task P8.5:** Maintain honest status reporting (`relational_fallback` vs `neo4j`).

---

### Phase P9: Audit Trail Hardening & Blockchain Anchoring
- [x] **Task P9.1:** Verify RFC 8785 canonical JSON digest stability.
- [x] **Task P9.2:** Implement SHA-256 hash chaining (`entry_hash = SHA256(prev_hash || payload)`) with tamper verification endpoint.
- [x] **Task P9.3:** Implement Merkle tree root calculation for batch checkpoint anchoring.
- [x] **Task P9.4:** Read-only verification of existing anchored event `EVT-PHASE7-SEP-635CDB7E` against Sepolia contract `0xf7aE6E373be5ad0f9444D230f285e8E620b70b63`.
- [x] **Task P9.5:** Guarantee `SIMULATE_BLOCKCHAIN=true` prevents accidental ETH expenditure.

---

### Phase P10: Dedicated Endpoints for Redesigned Frontend
- [x] **Task P10.1:** Implement `/api/cases/{workflow_id}` (7-step Case File aggregate with findings, policy, governance, before/after ledger).
- [x] **Task P10.2:** Implement `/api/exceptions` (Dedicated queue with severity, blast radius, and ownership).
- [x] **Task P10.3:** Implement `/api/agents/telemetry` (Live per-agent latency, runs, token counts, and error rates).
- [x] **Task P10.4:** Implement `/api/benchmarks` (Completion rate, safe-failure rate, duration percentiles).
- [x] **Task P10.5:** Implement `/api/security/status` (Read-only security posture, active key counts, auth roles).

---

### Phase P11: Reliability, Security & Pool Hardening
- [x] **Task P11.1:** Enforce startup config validation refusing default credentials when `APP_ENVIRONMENT != development`.
- [x] **Task P11.2:** Configure database `statement_timeout` (15000ms) and `lock_timeout` (5000ms).
- [x] **Task P11.3:** Connection pool leak test: execute 50 requests and verify pool availability remains 100%.
- [x] **Task P11.4:** Comprehensive RBAC test suite across Viewer, Operator, Finance, Supply Chain, and Admin roles.
- [x] **Task P11.5:** Automated SQL injection fuzzing test asserting zero queries execute injected commands.

---

### Phase P12: End-to-End Verification, Demo Suite & Final Documentation
- [x] **Task P12.1:** Automated verification script `backend/scripts/verify_all.py` (100% PASS).
- [x] **Task P12.2:** Execute full test suite against disposable database (330/330 passing tests).
- [x] **Task P12.3:** Provide complete operational runbook `docs/backend-overhaul/RUNBOOK.md` with PowerShell commands.
- [x] **Task P12.4:** Gate G3 approval documented before running demo batch on operational database.
- [x] **Task P12.5:** Update `CHANGELOG.md` and `EVIDENCE.md`.

---

## 4. Cross-Cutting Acceptance Matrix

| # | Acceptance Criterion | Verification Method | Status | Evidence Reference |
|---|---|---|---|---|
| 1 | Frontend Live mode works; Execute governed pipeline enabled | `contract_check.py` 100% MATCH + live pipeline run | **PASS** | `backend/scripts/contract_check.py` (29/29 endpoints) |
| 2 | Subsystems truthfully report health (including failure states) | `/api/health/ready` probe tests | **PASS** | `backend/tests/test_database_connection.py` |
| 3 | Migrations apply cleanly on fresh and existing DB | Forward-only runner check | **PASS** | Migrations 001-012 applied to disposable DB |
| 4 | Original 1,327 workbook rows and operational records preserved | Checksum comparison to baseline | **PASS** | `test_seed_data.py`, `test_isolation.py` (200 orders, 0 data lost) |
| 5 | Synthetic data deterministic, valid, diverse | `synth/validate.py` output | **PASS** | `backend/data/synth/validate.py` (zero errors) |
| 6 | Single task and 1,000-task batch complete durably | PostgreSQL SKIP LOCKED queue run | **PASS** | `backend/app/worker.py`, `app/api/tasks.py` |
| 7 | Crash recovery: zero lost or duplicate work | Chaos kill & restart test | **PASS** | Idempotency keys + reaper recovery |
| 8 | Agents produce evidence-backed, persisted findings | `agent_runs` table inspections | **PASS** | `backend/app/services/data_tools.py` |
| 9 | Policy engine safe (no eval); LLM cannot override rules | Hostile AST tests + override test | **PASS** | `backend/tests/test_safe_evaluator.py` |
| 10 | Approvals and actions exactly-once with before/after ledger | Transactional ledger tests | **PASS** | `backend/app/services/action_adapters.py` |
| 11 | Domains coherent; consistency check zero violations | `consistency_check.py` clean | **PASS** | `backend/scripts/consistency_check.py` (zero violations) |
| 12 | Graph connected, multi-hop, ground-truth verified | SQL parity test across 39 disruptions | **PASS** | `backend/tests/test_graph_ground_truth.py` (100% agreement) |
| 13 | Audit chain verifies; tamper detected; anchor mode honest | SHA-256 chain verification test | **PASS** | `backend/tests/test_audit_chain.py` |
| 14 | No secrets in repo, logs, or API responses | Safe regex scanner | **PASS** | Secrets audit & sanitizer tests |
| 15 | Test suite preserves 300 passing baseline + new tests | `pytest` summary | **PASS** | **330 passed in 44.45s** |
| 16 | Documentation & runbooks match real operational behavior | Diff review | **PASS** | `docs/backend-overhaul/RUNBOOK.md` |
