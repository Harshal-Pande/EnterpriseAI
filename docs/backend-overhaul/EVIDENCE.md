# Phase P0 Evidence Log

This document records the exact commands run, outputs observed, and empirical evidence collected during Phase P0.

---

## 1. Baseline Test Suite Run
* **Command:** `pytest backend/tests -q`
* **Target Database:** `enterprise_ai_disposable_test` (verified via `db_guard`)
* **Result:** `300 passed in 33.71s`
* **Log:** `file:///C:/Users/Harshal Pande/.gemini/antigravity-ide/brain/4f50c3c5-4c73-4e3b-9758-2a85348a7d2a/.system_generated/tasks/task-699.log`
* **Finding:** 100% of the 300 unit and integration tests pass cleanly.

---

## 2. Operational Database Inspection
* **Command:** `python backend/scripts/db_inspect.py DATABASE_URL --json`
* **Output:**
  ```text
  TARGET CHECK: database='enterprise_ai_test' host='::1/128' port=5432
  Visible DBs: ['enterprise_ai_disposable_test', 'enterprise_ai_test', 'postgres']
  Total Tables: 43
  Row counts: event_log=388, blockchain_anchors=2, scenario_instances=62, agent_runs=315, orders=200, order_lines=200
  Migrations Applied: 6 (001 to 005)
  Check Constraints: 364
  Foreign Keys: 54
  Unique Constraints: 4
  Indexes: 86
  Triggers: 0
  ```
* **Snapshot File:** `docs/backend-overhaul/db_snapshot_enterprise_ai_test.json`

---

## 3. Disposable Test Database Inspection
* **Command:** `python backend/scripts/db_inspect.py TEST_DATABASE_URL --json`
* **Output:**
  ```text
  TARGET CHECK: database='enterprise_ai_disposable_test' host='::1/128' port=5432
  Visible DBs: ['enterprise_ai_disposable_test', 'enterprise_ai_test', 'postgres']
  Total Tables: 43
  Row counts: event_log=0, blockchain_anchors=0, scenario_instances=0, agent_runs=0
  Migrations Applied: 5
  ```
* **Snapshot File:** `docs/backend-overhaul/db_snapshot_enterprise_ai_disposable_test.json`

---

## 4. Environment & Secrets Scan
* **Command:** `python backend/scripts/env_check.py`
* **Output:**
  ```text
  APP_ENVIRONMENT: SET: development
  DATABASE_URL: SET: db='enterprise_ai_test' host='localhost' port=5432
  TEST_DATABASE_URL: SET: db='enterprise_ai_disposable_test' host='localhost' port=5432
  GEMINI_API_KEY_1 through _7: ALL 7 KEYS SET (length=53)
  OPENROUTER_API_KEY: SET (length=73)
  LLM_PROVIDER_MODE: SET: LIVE
  SIMULATE_BLOCKCHAIN: SET: true
  CONTRACT_ADDRESS: SET (length=42)
  OPERATOR_API_KEY: SET (length=53)
  ADMIN_API_KEY: SET (length=53)
  VIEWER_API_KEY: SET (length=53)
  ```

---

## 5. Workbook & Seed Data Validation
* **Command:** `python backend/data/run_validation.py`
* **Result:** `31 sheets inspected, 1327 mapped records, 0 CRITICAL findings, 0 WARNING findings.`
* **Data Metrics from `data_audit.py`:**
  - Lines per order distribution: Exactly `[(1, 200)]` (100% single-line orders).
  - Supplier offers: 6 offers covering 4 distinct items.
  - Bill of materials: 5 lines.
  - Orders `created_at` range: 2026-10-10 to 2026-10-14.
