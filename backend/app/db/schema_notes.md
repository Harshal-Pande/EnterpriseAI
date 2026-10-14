# Database schema notes (Phase 1)

The outdated 4-table sketch has been replaced. Authoritative schema is:

- `backend/db/migrations/001_operational_schema.sql` — domain/reference/transaction tables from the workbook
- `backend/db/migrations/002_runtime_schema.sql` — workflow tables (supersedes `project_reference/schema_core.sql` for application use; the starter file is kept unchanged)
- `backend/data/column_mappings.py` — workbook column → SQL column mappings
- `PHASE_1_DATA_AUDIT.md` and `docs/DATA_DICTIONARY.md` — relationships, units, exclusions

`backend/app/db/database.py` is still a placeholder. FastAPI is **not** connected to PostgreSQL in Phase 1.
