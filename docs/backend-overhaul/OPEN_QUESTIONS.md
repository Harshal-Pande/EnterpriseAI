# Open Questions & Gate Triggers Log

This file tracks questions, blocked decisions, and safety approvals requiring owner sign-off.

---

## Active Gate Approvals

### Gate G1: Phase P0 Audit Presentation & Phase Sequence Approval
* **Status:** PENDING OWNER APPROVAL
* **Summary:**
  - P0 audit is complete with zero database mutations and zero git commits.
  - Operational DB `enterprise_ai_test` (43 tables, 388 event log rows, 2 blockchain anchors) and Disposable DB `enterprise_ai_disposable_test` (300/300 passing tests) are verified.
  - All 7 Gemini API keys are configured and ready for cyclic rotation.
  - Proposed Phase Sequence:
    - **P1:** Frontend-Backend Connectivity & Contract Alignment (Owner's top priority).
    - **P2:** Additive Database Models (Migrations 006+).
    - **P3:** Synthetic Data v3 (Deterministic supply chain expansion).
    - **P4:** Durable Task Queue & 1,000-Task Engine.
    - **P5:** Agents & Grounded Orchestration (Using Gemini API key pool).
    - **P6:** Governance, Approvals & Controlled Actions.
    - **P7:** Domain Operational Coherence.
    - **P8:** Knowledge Graph & Multi-Hop Impact Analysis.
    - **P9:** Audit Trail Hardening & Blockchain Anchoring.
    - **P10:** UI-Facing Aggregate Endpoints (Case File, Exceptions, Benchmarks).
    - **P11:** Reliability, Security & Pool Hardening.
    - **P12:** End-to-End Verification, Demo Suite & Final Documentation.
* **Risk:** None. P0 performed only read-only inspections and safety harness creation.
* **Action Required:** Owner approval to proceed to Phase P1.

---

### Gate G2: Operational Database Migrations & Data Loading
* **Status:** UPCOMING (Phase P2 / P3)
* **Rule:** Before any migration or synthetic data load into `enterprise_ai_test`:
  1. Take full logical backup via `pg_dump` into `backups/`.
  2. Run migration runner with `--dry-run`.
  3. Validate completely on `enterprise_ai_disposable_test`.
  4. Obtain explicit owner confirmation.

### Gate G3: 1,000-Task Backlog Execution Target
* **Status:** UPCOMING (Phase P4 / P12)
* **Rule:** Recommend executing the 1,000-task backlog on a clone/copy of the operational database (`enterprise_ai_demo`) to preserve original historical state.

### Gate G4: Docker Daemon / Neo4j Service
* **Status:** DEFERRED (Phase P8)
* **Context:** Docker daemon is currently inactive. System operates safely with `RelationalGraphEngine`. Owner may choose whether to start Docker for Neo4j testing or keep relational fallback.

### Gate G5: Live LLM Calls & Key Pool Rotation
* **Status:** CONFIGURED & READY FOR APPROVAL
* **Context:** All 7 Gemini API keys (`GEMINI_API_KEY_1` to `_7`) are present in environment. Batch runs will default to deterministic simulation; live validation calls require explicit owner confirmation.

### Gate G6: Blockchain On-Chain Transactions
* **Status:** LOCKED
* **Rule:** `SIMULATE_BLOCKCHAIN=true` remains active. Zero testnet ETH will be spent.
