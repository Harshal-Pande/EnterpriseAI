"""Validate loaded PostgreSQL seed data against workbook mappings.

Requires DATABASE_URL (or --database-url-var). Does not claim success unless
a real database query ran.

Workbook-only validation remains: python backend/data/run_validation.py

Usage:
    python backend/data/validate_seed_data.py
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_BACKEND = _HERE.parent
for path in (_HERE, _BACKEND, _BACKEND / "db"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from column_mappings import (  # noqa: E402
    EMPTY_RUNTIME_SHEETS,
    EXPECTED_SOURCE_ROW_COUNTS,
    FK_SPECS,
    MAPPED_IMPORT_ROWS,
    METADATA_EXCLUDED_ROWS,
    SHEET_MAPPINGS,
    TOTAL_WORKBOOK_ROWS,
    dest_primary_key,
)
from connection import connect  # noqa: E402

OUTPUT_PATH = _HERE / "validation_report.json"

RUNTIME_EMPTY_TABLES = [
    "scenario_instances",
    "agent_runs",
    "agent_findings",
    "decisions",
    "action_queue",
    "policy_evaluations",
    "approval_requests",
    "action_execution_results",
    "event_log",
    "blockchain_anchors",
]


def _check(check_id: str, status: str, **extra) -> dict:
    row = {"check_id": check_id, "status": status}
    row.update(extra)
    return row


def validate(conn) -> dict:
    checks = []
    with conn.cursor() as cur:
        for sheet_name, mapping in SHEET_MAPPINGS.items():
            table = mapping.dest_table
            expected = EXPECTED_SOURCE_ROW_COUNTS[sheet_name]
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            actual = cur.fetchone()[0]
            ok = actual == expected
            checks.append(_check(
                f"ROW_COUNT_{table}",
                "PASS" if ok else "FAIL",
                sheet=sheet_name,
                table=table,
                expected=expected,
                actual=actual,
                source_rows=expected,
                imported_rows=actual,
                excluded_rows=0,
                rejected_rows=max(0, expected - actual) if actual < expected else 0,
            ))

        cur.execute("SELECT COUNT(*) FROM scheduler_state")
        sched = cur.fetchone()[0]
        checks.append(_check(
            "ROW_COUNT_scheduler_state",
            "PASS" if sched == 1 else "FAIL",
            table="scheduler_state",
            expected=1,
            actual=sched,
            note="SQL seed row, not a workbook sheet",
        ))

        for table in RUNTIME_EMPTY_TABLES:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            actual = cur.fetchone()[0]
            checks.append(_check(
                f"EMPTY_RUNTIME_{table}",
                "PASS" if actual == 0 else "FAIL",
                table=table,
                expected=0,
                actual=actual,
                note="Runtime table; workbook sheet is header-only or schema-only",
            ))

        for sheet_name, mapping in SHEET_MAPPINGS.items():
            table = mapping.dest_table
            pk = dest_primary_key(mapping)
            cur.execute(
                f"SELECT COUNT(*) FROM (SELECT {pk} FROM {table} GROUP BY {pk} HAVING COUNT(*) > 1) d"
            )
            dupes = cur.fetchone()[0]
            checks.append(_check(
                f"PK_UNIQUE_{table}",
                "PASS" if dupes == 0 else "FAIL",
                table=table,
                duplicate_keys=dupes,
            ))

        for spec in FK_SPECS:
            child = SHEET_MAPPINGS[spec.child_sheet]
            parent = SHEET_MAPPINGS[spec.parent_sheet]
            child_col = spec.fk_col
            for col in child.columns:
                if col.source_col == spec.fk_col:
                    child_col = col.dest_col
                    break
            sql = (
                f"SELECT COUNT(*) FROM {child.dest_table} c "
                f"WHERE c.{child_col} IS NOT NULL "
                f"AND NOT EXISTS (SELECT 1 FROM {parent.dest_table} p "
                f"WHERE p.{spec.parent_pk} = c.{child_col})"
            )
            cur.execute(sql)
            orphans = cur.fetchone()[0]
            checks.append(_check(
                f"FK_{child.dest_table}_{child_col}",
                "PASS" if orphans == 0 else "FAIL",
                child_table=child.dest_table,
                parent_table=parent.dest_table,
                orphans=orphans,
            ))

        cur.execute(
            """
            SELECT COUNT(*) FROM inventory
            WHERE on_hand_qty < 0 OR reserved_qty < 0 OR available_qty < 0
               OR ABS(available_qty - (on_hand_qty - reserved_qty)) > 0.01
            """
        )
        inv_bad = cur.fetchone()[0]
        checks.append(_check(
            "INVENTORY_ARITHMETIC",
            "PASS" if inv_bad == 0 else "FAIL",
            mismatched_rows=inv_bad,
        ))

        cur.execute(
            """
            SELECT COUNT(*) FROM purchase_orders
            WHERE ABS(total_cost_inr - (quantity * unit_cost_inr)) > 1
            """
        )
        po_bad = cur.fetchone()[0]
        checks.append(_check(
            "PO_TOTAL_ARITHMETIC",
            "PASS" if po_bad == 0 else "FAIL",
            mismatched_rows=po_bad,
        ))

        cur.execute(
            """
            SELECT COUNT(*) FROM budgets
            WHERE ABS(available_budget_inr - (approved_limit_inr - committed_spend_inr)) > 0.01
            """
        )
        bud_bad = cur.fetchone()[0]
        checks.append(_check(
            "BUDGET_ARITHMETIC",
            "PASS" if bud_bad == 0 else "FAIL",
            mismatched_rows=bud_bad,
        ))

        cur.execute(
            """
            SELECT COUNT(*) FROM goods_receipts
            WHERE accepted_qty > received_qty
            """
        )
        grn_bad = cur.fetchone()[0]
        checks.append(_check(
            "GRN_ACCEPTED_LTE_RECEIVED",
            "PASS" if grn_bad == 0 else "FAIL",
            mismatched_rows=grn_bad,
        ))

        cur.execute(
            """
            SELECT COUNT(*) FROM scenario_templates
            WHERE linked_reference_id IS NOT NULL
            """
        )
        linked = cur.fetchone()[0]
        checks.append(_check(
            "DQ01_LINKED_REFERENCE_NULL",
            "PASS" if linked == 0 else "FAIL",
            non_null_linked_reference_id=linked,
            note="Workbook linked_reference_id stored severity; import must set FK column NULL",
        ))

        cur.execute(
            """
            SELECT COUNT(*) FROM scenario_templates
            WHERE enabled IS NOT TRUE
            """
        )
        disabled = cur.fetchone()[0]
        checks.append(_check(
            "DQ02_ENABLED_TRUE",
            "PASS" if disabled == 0 else "FAIL",
            not_enabled=disabled,
        ))

        cur.execute("SELECT DISTINCT severity FROM scenario_templates")
        severities = {row[0] for row in cur.fetchall()}
        allowed = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        checks.append(_check(
            "DQ01_SEVERITY_VALUES",
            "PASS" if severities <= allowed and severities else "FAIL",
            values=sorted(severities),
        ))

    failed = [c for c in checks if c["status"] == "FAIL"]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "database",
        "database_queried": True,
        "pass": len(failed) == 0,
        "failed_count": len(failed),
        "check_count": len(checks),
        "count_reconciliation": {
            "workbook_data_rows": TOTAL_WORKBOOK_ROWS,
            "mapped_import_rows": MAPPED_IMPORT_ROWS,
            "metadata_excluded_rows": METADATA_EXCLUDED_ROWS,
            "empty_runtime_workbook_sheets": list(EMPTY_RUNTIME_SHEETS),
            "note": (
                "1677 = all 40 sheets. 1327 = 31 mapped import sheets. "
                "350 = README (8) + data_dictionary (37) + column_dictionary (305). "
                "Six runtime workbook sheets contribute 0 rows but still have tables."
            ),
        },
        "checks": checks,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate PostgreSQL seed data.")
    parser.add_argument("--database-url-var", default="DATABASE_URL")
    parser.add_argument("--output", default=str(OUTPUT_PATH))
    args = parser.parse_args()

    conn = connect(args.database_url_var)
    try:
        report = validate(conn)
    finally:
        conn.close()

    out = Path(args.output)
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    print(f"Database validation report written to: {out}")
    print(f"  database_queried : {report['database_queried']}")
    print(f"  checks           : {report['check_count']}")
    print(f"  failed           : {report['failed_count']}")
    print(f"  pass             : {report['pass']}")
    for check in report["checks"]:
        if check["status"] != "PASS":
            print(f"  FAIL {check['check_id']}: {check}")

    sys.exit(0 if report["pass"] else 1)


if __name__ == "__main__":
    main()
