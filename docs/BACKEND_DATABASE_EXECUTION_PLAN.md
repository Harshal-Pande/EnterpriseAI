# Enterprise AI Mesh: Backend & Database Execution Plan

**Document Path:** `docs/BACKEND_DATABASE_EXECUTION_PLAN.md`  
**Author:** Antigravity Engineering Agent  
**Last Updated:** 2026-10-15  
**Version:** 1.0.0  
**Status:** In Progress — Phase P0 Complete, Awaiting Gate G1 Approval  

---

## 1. Project Objectives & Scope

The Enterprise AI Mesh frontend redesign is 100% complete across all 14 screens, establishing a fixed integration contract with design tokens, strict role-based views, and a dedicated 7-step Case File architecture. 

The objective of this plan is the complete end-to-end overhaul and verification of the backend (`backend/`), the PostgreSQL database, synthetic data generation, multi-agent orchestration, the knowledge graph, and the tamper-evident audit trail.

### Key Tenets & Mandates
1. **Preservation:** The frontend is treated as a frozen integration contract. Working baseline functionality (300/300 passing tests) and operational database records (`event_log`, `scenario_instances`, `blockchain_anchors`) must never be broken or reduced.
2. **Honesty:** Zero fabricated liveness. Subsystems report truthful states (`live`, `simulated`, `fallback`, `unavailable`). No claims of "Production-Ready" without empirical verification.
3. **Safety First:** Strict refusal of destructive DDL (`DROP`, `TRUNCATE`, unconstrained `DELETE`) enforced by `db_guard.py`. Real operational writes require Gate approvals and pre-migration backups.
4. **Observable & Durable:** Single tasks and ~1,000-task backlogs execute with ACID durability, restart resiliency, and exactly-once state transitions.
5. **Grounded Multi-Agent Orchestration:** Specialist agents perform deterministic domain computations citing evidence references, while LLM recommendations are routed through a 7-key Gemini API pool with OpenRouter fallback.

---

## 2. Findings from the Initial Audit (Phase P0 Baseline)

| Item | Verified Reality | Evidence & Notes |
|---|---|---|
| **Working Tree** | Clean on branch `main` | Zero uncommitted changes at audit start |
| **Test Suite Baseline** | **300 passed in 33.71s** | `pytest backend/tests -q` executed against `enterprise_ai_disposable_test` |
| **Operational DB** | `enterprise_ai_test` | 43 tables, 388 event log rows, 2 blockchain anchors, 62 scenarios, 200 orders |
| **Disposable DB** | `enterprise_ai_disposable_test` | 43 tables, 0 runtime event logs, clean master fixtures |
| **Database Migrations** | 6 applied (001 to 005) | Checksummed by runner; all future migrations must be additive (`006+`) |
| **Gemini API Keys** | **ALL 7 KEYS PRESENT** | `GEMINI_API_KEY_1` to `_7` configured in local environment (len=53) |
| **OpenRouter Fallback** | Configured (len=73) | Present in local environment |
| **LLM Provider Mode** | `LIVE` | Ready for approved live execution |
| **Blockchain Mode** | `SIMULATE_BLOCKCHAIN=true` | Sepolia contract deployed at `0xf7aE6E373be5ad0f9444D230f285e8E620b70b63` |
| **Docker / Neo4j** | Docker daemon inactive | `RelationalGraphEngine` operational as high-availability fallback |
| **Route Alignment** | Frontend calls `/api/...` | Matches FastAPI routes. Zero `/api/v1` in frontend code; aliases will be added for safety |
| **Orders & BOM Data** | 100% single-line orders | 200 orders, 200 lines. Only 6 offers for 4 items. Requires Synthetic Data v3 |

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
- [ ] **Gate G1 Approval:** Present P0 audit findings and phase sequence to owner.

---

### Phase P1: Frontend-Backend Connectivity & Contract Alignment
*Goal: Redesigned frontend connects truthfully in Live mode; "Execute governed pipeline" works against PostgreSQL.*
- [ ] **Task P1.1:** Build `backend/scripts/contract_check.py` to validate 100% of frontend routes against backend API.
- [ ] **Task P1.2:** Mount `/api/v1` aliases in `app/main.py` mirroring `/api` to prevent any prefix divergence.
- [ ] **Task P1.3:** Enhance `/api/health/ready` to return structured per-subsystem objects (`postgres`, `scheduler`, `graph`, `llm_provider`, `blockchain`, `data_freshness`).
- [ ] **Task P1.4:** Standardize API error response format across all routers (`{"error": {"code", "message", "details", "correlation_id"}}`).
- [ ] **Task P1.5:** Validate CORS configuration for both `localhost:5173` and `127.0.0.1:5173`.
- [ ] **Task P1.6:** Execute ONE governed pipeline from frontend / API against PostgreSQL and capture full telemetry trace.

---

### Phase P2: Database Model Gap Analysis & Additive Migrations
*Goal: Additive schema evolution without breaking existing data or checksummed migrations 001-005.*
- [ ] **Task P2.1:** Implement migration `006_master_data_extensions.sql` (Customers, Carriers, Transport Lanes).
- [ ] **Task P2.2:** Implement migration `007_inventory_ledger.sql` (`inventory_movements` transactional ledger, allocations, stock reservations).
- [ ] **Task P2.3:** Implement migration `008_task_queue.sql` (Durable batch and work queue tables for 1,000-task engine).
- [ ] **Task P2.4:** Implement migration `009_agent_evidence.sql` (Tool call logging, evidence references, inter-agent messages).
- [ ] **Task P2.5:** Implement migration `010_event_log_hardening.sql` (Sequential order, `prev_hash`, `entry_hash`, immutable UPDATE/DELETE trigger).
- [ ] **Task P2.6:** Test migrations cleanly on `enterprise_ai_disposable_test` and pass dry-run before Gate G2.

---

### Phase P3: Synthetic Data v3 (Realistic Supply Chain Data)
*Goal: Rich, diverse, domain-consistent Indian steel supply chain data anchored to reference date 2026-10-15.*
- [ ] **Task P3.1:** Build deterministic generator `backend/data/synth/generate.py` with reproducible seed and `manifest.json`.
- [ ] **Task P3.2:** Generate expanded catalog (25-40 SKUs, multi-tier BOM, 60-120 customers with Pareto distribution).
- [ ] **Task P3.3:** Generate ~1,500 to 2,500 realistic orders with multi-line items (1-6 lines per order), correlated pricing, priorities, and deadlines.
- [ ] **Task P3.4:** Generate carrier lanes, freight rates, and 25-40 suppliers with 150-300 offers.
- [ ] **Task P3.5:** Build data diversity validator `backend/data/synth/validate.py` (entropy, distinct tuples, zero negative stock).
- [ ] **Task P3.6:** Load data into `enterprise_ai_disposable_test`, verify original 1,327 seed rows remain completely untouched.

---

### Phase P4: Durable Task Model & 1,000-Task Execution Engine
*Goal: Process single tasks on demand and a 1,000-task backlog with PostgreSQL SKIP LOCKED, restart recovery, and chaos durability.*
- [ ] **Task P4.1:** Implement task queue worker `app/worker.py` utilizing `SELECT ... FOR UPDATE SKIP LOCKED` with lease heartbeats and reaper.
- [ ] **Task P4.2:** Enforce exactly-once transitions and idempotency keys across all tasks and agent phases.
- [ ] **Task P4.3:** Size database connection pool and threadpool execution to guarantee `/api/health` stays responsive under 200+ task bursts.
- [ ] **Task P4.4:** Implement preloaded backlog generator creating ~1,000 diverse tasks mapped to the 15 scenario templates.
- [ ] **Task P4.5:** Implement batch control APIs (create, list, pause, resume, cancel, retry).
- [ ] **Task P4.6:** Execute chaos test (kill worker mid-run via `taskkill /F`, restart, prove 0 lost and 0 duplicate tasks).

---

### Phase P5: Specialist Agents & Grounded Multi-Agent Orchestration
*Goal: Substance-grounded specialist computations, supervisor coordination, and multi-key Gemini LLM pool.*
- [ ] **Task P5.1:** Implement internal data tools layer with parameterized queries returning structured evidence references.
- [ ] **Task P5.2:** Enhance deterministic specialist agent computations:
  - *Inventory Agent:* Net available stock, warehouse allocation, BOM breakdown, days of cover.
  - *Procurement Agent:* Supplier ranking, landed freight cost, reliability weighting, single-source detection.
  - *Finance Agent:* Budget headroom, margin verification, single-action spend approval rules.
  - *Logistics Agent:* Lane transit feasibility, mode alternatives (rail vs road), weather/congestion delay delta.
- [ ] **Task P5.3:** Wire multi-key Gemini API pool (`GEMINI_API_KEY_1` to `_7`) with cyclic rotation and cooldown tracking.
- [ ] **Task P5.4:** Enforce strict Pydantic output contracts and fail-closed handling for malformed or missing evidence.
- [ ] **Task P5.5:** Persist all agent steps, tool calls, and evidence references into `agent_runs` and `event_log`.

---

### Phase P6: Governance, Approvals & Controlled Actions
*Goal: Rule enforcement, exactly-once approvals, and transactional database state mutations with before/after ledgers.*
- [ ] **Task P6.1:** Build safe AST-based condition expression evaluator for `business_rules` (prohibits eval/exec).
- [ ] **Task P6.2:** Enforce strict approval state machine (`PENDING -> APPROVED | REJECTED | EXPIRED`) with 409 conflict on double decision.
- [ ] **Task P6.3:** Implement `DatabaseActionAdapter` with row locks (`SELECT ... FOR UPDATE`), pre-condition checks, and transactional rollback.
- [ ] **Task P6.4:** Implement state-change ledger recording `(action_id, table, pk, column, before, after)`.
- [ ] **Task P6.5:** Implement compensating transaction handlers for reversible actions (stock unreserve, PO cancellation).
- [ ] **Task P6.6:** Run negative test matrix (budget breach without approval, concurrent reserve oversell prevention).

---

### Phase P7: Domain Operational Coherence
*Goal: Unified behavior across orders, inventory, procurement, finance, and logistics.*
- [ ] **Task P7.1:** Implement formal order state machine in `workflow_service.py` (`OPEN -> IN_PROGRESS -> AT_RISK -> COMPLETED`).
- [ ] **Task P7.2:** Transactional inventory reservations with row locks and automatic release on order cancellation.
- [ ] **Task P7.3:** Procurement lifecycle with PO states, goods receipt posting to inventory, and quality hold segregation.
- [ ] **Task P7.4:** Financial reconciliation endpoint and test (`SUM(POs) == committed_spend_inr`).
- [ ] **Task P7.5:** Automated cross-domain consistency checker (`consistency_check.py`).

---

### Phase P8: Knowledge Graph & Multi-Hop Disruption Analysis
*Goal: Connected knowledge graph with real multi-tier paths and verified impact blast radius.*
- [ ] **Task P8.1:** Expand graph ontology beyond 6 entity types (add ProductionLines, Batches, Carriers, Lanes, POs, BOM links).
- [ ] **Task P8.2:** Implement unified graph extractor generating interconnected nodes and edges from PostgreSQL.
- [ ] **Task P8.3:** Implement multi-hop disruption impact algorithm (Supplier -> Raw Material -> Finished Product -> Orders -> Customers -> Revenue at Risk).
- [ ] **Task P8.4:** Ground truth verification test: compare graph impact against independent SQL queries across 30 random disruptions.
- [ ] **Task P8.5:** Maintain honest status reporting (`relational_fallback` vs `neo4j`).

---

### Phase P9: Audit Trail Hardening & Blockchain Anchoring
*Goal: RFC 8785 canonicalization, cryptographic hash chain, and truthful Sepolia verification.*
- [ ] **Task P9.1:** Verify RFC 8785 canonical JSON digest stability.
- [ ] **Task P9.2:** Implement SHA-256 hash chaining (`entry_hash = SHA256(prev_hash || payload)`) with tamper verification endpoint.
- [ ] **Task P9.3:** Implement Merkle tree root calculation for batch checkpoint anchoring.
- [ ] **Task P9.4:** Read-only verification of existing anchored event `EVT-PHASE7-SEP-635CDB7E` against Sepolia contract `0xf7aE6E373be5ad0f9444D230f285e8E620b70b63`.
- [ ] **Task P9.5:** Guarantee `SIMULATE_BLOCKCHAIN=true` prevents accidental ETH expenditure.

---

### Phase P10: Dedicated Endpoints for Redesigned Frontend
*Goal: Full API backing for all UI views without browser-side synthesis.*
- [ ] **Task P10.1:** Implement `/api/cases/{workflow_id}` (7-step Case File aggregate with findings, policy, governance, before/after ledger).
- [ ] **Task P10.2:** Implement `/api/exceptions` (Dedicated queue with severity, blast radius, and ownership).
- [ ] **Task P10.3:** Implement `/api/agents/telemetry` (Live per-agent latency, runs, token counts, and error rates).
- [ ] **Task P10.4:** Implement `/api/benchmarks/metrics` (Completion rate, safe-failure rate, duration percentiles).
- [ ] **Task P10.5:** Implement `/api/security/status` (Read-only security posture, active key counts, auth roles).

---

### Phase P11: Reliability, Security & Pool Hardening
*Goal: Production-grade robustness, statement timeouts, leak tests, and RBAC.*
- [ ] **Task P11.1:** Enforce startup config validation refusing default credentials when `APP_ENVIRONMENT != development`.
- [ ] **Task P11.2:** Configure database `statement_timeout` (5000ms) and `lock_timeout` (3000ms).
- [ ] **Task P11.3:** Connection pool leak test: execute 500 requests and verify pool availability remains 100%.
- [ ] **Task P11.4:** Comprehensive RBAC test suite across Viewer, Operator, Finance, Supply Chain, and Admin roles.
- [ ] **Task P11.5:** Automated log sanitizer tests asserting zero credentials leak into logs or API responses.

---

### Phase P12: End-to-End Verification, Demo Suite & Final Documentation
*Goal: Comprehensive system proof, runbooks, and final acceptance.*
- [ ] **Task P12.1:** Automated verification script `backend/scripts/verify_all.py`.
- [ ] **Task P12.2:** Execute full 4-scenario exception suite on disposable database (Supplier, Budget, Logistics, Combined).
- [ ] **Task P12.3:** Execute 1,000-task backlog test and report throughput, p95 latencies, and outcome distributions.
- [ ] **Task P12.4:** Gate G3 approval before running demo batch on operational database.
- [ ] **Task P12.5:** Update `BACKEND_DOCUMENTATION.md`, `DATABASE_DOCUMENTATION.md`, and generate `docs/backend-overhaul/RUNBOOK.md`.
- [ ] **Task P12.6:** Deliver final report and acceptance matrix.

---

## 4. Safety Controls & Gate Milestones

| Gate | Timing | Purpose | Mandatory Condition |
|---|---|---|---|
| **G1** | Post P0 | Approve P0 audit findings & phase sequence | **ACTIVE — STOP & PRESENT TO OWNER** |
| **G2** | Pre P2/P3 | Apply migrations/synthetic data to operational DB | `pg_dump` backup taken, `--dry-run` passed, tested on disposable DB |
| **G3** | Pre P4/P12 | Run 1,000-task backlog against operational DB | Run on disposable/demo clone first |
| **G4** | Pre P8 | Docker daemon / Neo4j installation | Default to relational fallback unless explicitly requested |
| **G5** | Pre Live LLM | Live provider calls with Gemini multi-key pool | Simulation mode default; live calls gated |
| **G6** | Pre Blockchain | Any Ethereum transaction signing | Default `SIMULATE_BLOCKCHAIN=true`; zero ETH spend |

---

## 5. Cross-Cutting Acceptance Matrix

| # | Acceptance Criterion | Verification Method | Status |
|---|---|---|---|
| 1 | Frontend Live mode works; Execute governed pipeline enabled | `contract_check.py` 100% MATCH + live pipeline run | Pending P1 |
| 2 | Subsystems truthfully report health (including failure states) | `/api/health/ready` probe tests | Pending P1 |
| 3 | Migrations apply cleanly on fresh and existing DB | Forward-only runner check | Pending P2 |
| 4 | Original 1,327 workbook rows and operational records preserved | Checksum comparison to baseline | Pending P3 |
| 5 | Synthetic data deterministic, valid, diverse | `synth/validate.py` output | Pending P3 |
| 6 | Single task and 1,000-task batch complete durably | PostgreSQL SKIP LOCKED queue run | Pending P4 |
| 7 | Crash recovery: zero lost or duplicate work | Chaos kill & restart test | Pending P4 |
| 8 | Agents produce evidence-backed, persisted findings | `agent_runs` table inspections | Pending P5 |
| 9 | Policy engine safe (no eval); LLM cannot override rules | Hostile AST tests + override test | Pending P6 |
| 10 | Approvals and actions exactly-once with before/after ledger | Transactional ledger tests | Pending P6 |
| 11 | Domains coherent; consistency check zero violations | `consistency_check.py` clean | Pending P7 |
| 12 | Graph connected, multi-hop, ground-truth verified | SQL parity test across 30 disruptions | Pending P8 |
| 13 | Audit chain verifies; tamper detected; anchor mode honest | SHA-256 chain verification test | Pending P9 |
| 14 | No secrets in repo, logs, or API responses | Safe regex scanner | PASS (P0) |
| 15 | Test suite preserves 300 passing baseline + new tests | `pytest` summary | PASS (P0: 300/300) |
| 16 | Documentation & runbooks match real operational behavior | Diff review | Pending P12 |
