"""Workbook validator unit tests (no PostgreSQL)."""

from datetime import date

from validators import (
    check_arithmetic_identity,
    check_date_order,
    check_date_range,
    check_no_duplicate_ids,
    check_no_nulls,
    check_numeric_range,
    check_product_identity,
    check_quantity_lte,
    check_referential_integrity,
    check_required_columns,
    check_valid_status,
    _is_null,
    _to_float,
)


def test_required_columns_missing():
    errors = check_required_columns("orders", ["order_id"], ["order_id", "status"])
    assert len(errors) == 1
    assert errors[0].severity == "CRITICAL"


def test_duplicate_ids():
    records = [{"id": "A"}, {"id": "B"}, {"id": "A"}]
    errors = check_no_duplicate_ids("t", records, "id")
    assert len(errors) == 1
    assert errors[0].row == 3


def test_null_and_blank_strings():
    assert _is_null(None)
    assert _is_null("")
    assert _is_null("  ")
    errors = check_no_nulls("t", [{"id": "x", "name": "  "}], ["id", "name"])
    assert len(errors) == 1


def test_numeric_range_and_invalid_type():
    records = [{"qty": 5}, {"qty": -1}, {"qty": "nope"}]
    errors = check_numeric_range("t", records, "qty", 0, 10)
    assert len(errors) == 2


def test_valid_status_unknown_value():
    errors = check_valid_status("t", [{"s": "OPEN"}, {"s": "WEIRD"}], "s", {"OPEN"})
    assert len(errors) == 1


def test_referential_integrity_orphan():
    errors = check_referential_integrity(
        "child", [{"fk": "X"}], "fk", {"A", "B"}
    )
    assert errors[0].severity == "CRITICAL"


def test_referential_integrity_null_skipped():
    errors = check_referential_integrity("child", [{"fk": None}], "fk", {"A"})
    assert errors == []


def test_inventory_arithmetic():
    ok = [{"on": 10, "res": 3, "av": 7}]
    bad = [{"on": 10, "res": 3, "av": 8}]
    assert check_arithmetic_identity("inv", ok, "on", "res", "av") == []
    assert check_arithmetic_identity("inv", bad, "on", "res", "av")


def test_po_product_identity():
    ok = [{"q": 2, "u": 5, "t": 10}]
    bad = [{"q": 2, "u": 5, "t": 9}]
    assert check_product_identity("po", ok, "q", "u", "t", tolerance=1.0) == []
    assert check_product_identity("po", bad, "q", "u", "t", tolerance=0)


def test_quantity_lte_and_date_order():
    assert check_quantity_lte("g", [{"a": 0, "r": 1000}], "a", "r") == []
    assert check_quantity_lte("g", [{"a": 5, "r": 4}], "a", "r")
    records = [
        {"start": "2026-01-02", "end": "2026-01-01"},
        {"start": "2026-01-01", "end": "2026-01-02"},
    ]
    errors = check_date_order("t", records, "start", "end")
    assert len(errors) == 1


def test_date_range_unparseable():
    errors = check_date_range(
        "t", [{"d": "not-a-date"}], "d", date(2025, 1, 1), date(2028, 12, 31)
    )
    assert errors


def test_to_float_rejects_bool():
    assert _to_float(True) is None
    assert _to_float("3.5") == 3.5
