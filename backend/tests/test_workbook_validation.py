"""End-to-end workbook validation without PostgreSQL."""

from run_validation import validate_all, WORKBOOK_PATH


def test_workbook_validation_has_no_critical_findings():
    import openpyxl

    assert WORKBOOK_PATH.exists()
    wb = openpyxl.load_workbook(str(WORKBOOK_PATH), read_only=True, data_only=True)
    try:
        report = validate_all(wb)
    finally:
        wb.close()

    assert report["mode"] == "workbook_only"
    assert report["database_queried"] is False
    assert report["sheets_inspected"] == 31
    assert report["total_records_inspected"] == 1327
    assert report["count_reconciliation"]["workbook_data_rows"] == 1677
    assert report["summary"]["critical"] == 0
    empty = report["count_reconciliation"]["empty_runtime_sheets"]
    assert len(empty) == 6
    assert all(item["row_count"] == 0 for item in empty)
