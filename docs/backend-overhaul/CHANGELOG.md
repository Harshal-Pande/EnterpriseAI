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
