"""
validators.py — Standalone validation library for the Enterprise AI Industrial Dataset.

No database dependency. All functions accept raw Python dicts (rows from openpyxl)
and return lists of ValidationError instances.
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, List, Optional, Set


@dataclass
class ValidationError:
    sheet: str
    row: int          # 1-indexed; 0 = sheet-level finding
    column: str
    value: Any
    rule: str
    severity: str     # 'CRITICAL', 'WARNING', 'INFO'
    message: str


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _to_date(value: Any) -> Optional[date]:
    """Coerce a value to date; return None on failure."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y",
                    "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M"):
            try:
                return datetime.strptime(stripped, fmt).date()
            except ValueError:
                continue
    return None


def _to_float(value: Any) -> Optional[float]:
    """Coerce a value to float; return None on failure."""
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _is_null(value: Any) -> bool:
    """Return True for None or empty/whitespace string."""
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


# ---------------------------------------------------------------------------
# Public validation functions
# ---------------------------------------------------------------------------

def check_required_columns(
    sheet_name: str,
    actual_columns: List[str],
    required_cols: List[str],
) -> List[ValidationError]:
    """Verify that all required column names are present in the sheet header."""
    errors: List[ValidationError] = []
    actual_set = set(actual_columns)
    for col in required_cols:
        if col not in actual_set:
            errors.append(ValidationError(
                sheet=sheet_name,
                row=0,
                column=col,
                value=None,
                rule="required_column_present",
                severity="CRITICAL",
                message=f"Required column '{col}' is missing from sheet '{sheet_name}'.",
            ))
    return errors


def check_no_duplicate_ids(
    sheet_name: str,
    records: List[dict],
    id_col: str,
) -> List[ValidationError]:
    """Detect duplicate values in a candidate primary-key column."""
    errors: List[ValidationError] = []
    if not records:
        return errors

    seen: dict = {}
    for idx, record in enumerate(records, start=1):
        value = record.get(id_col)
        if _is_null(value):
            continue
        key = str(value).strip()
        if key in seen:
            errors.append(ValidationError(
                sheet=sheet_name,
                row=idx,
                column=id_col,
                value=value,
                rule="no_duplicate_ids",
                severity="CRITICAL",
                message=(
                    f"Duplicate identifier '{key}' in column '{id_col}' "
                    f"(first seen at row {seen[key]})."
                ),
            ))
        else:
            seen[key] = idx
    return errors


def check_no_nulls(
    sheet_name: str,
    records: List[dict],
    required_cols: List[str],
) -> List[ValidationError]:
    """Report rows where any column in required_cols is null or empty."""
    errors: List[ValidationError] = []
    if not records:
        return errors

    for idx, record in enumerate(records, start=1):
        for col in required_cols:
            value = record.get(col)
            if _is_null(value):
                errors.append(ValidationError(
                    sheet=sheet_name,
                    row=idx,
                    column=col,
                    value=value,
                    rule="no_nulls",
                    severity="WARNING",
                    message=f"Null or empty value in required column '{col}' at row {idx}.",
                ))
    return errors


def check_date_range(
    sheet_name: str,
    records: List[dict],
    date_col: str,
    min_date: date,
    max_date: date,
) -> List[ValidationError]:
    """Flag rows where a date column falls outside [min_date, max_date]."""
    errors: List[ValidationError] = []
    if not records:
        return errors

    for idx, record in enumerate(records, start=1):
        raw = record.get(date_col)
        if _is_null(raw):
            continue  # nulls reported by check_no_nulls if mandatory
        coerced = _to_date(raw)
        if coerced is None:
            errors.append(ValidationError(
                sheet=sheet_name,
                row=idx,
                column=date_col,
                value=raw,
                rule="date_range",
                severity="WARNING",
                message=(
                    f"Cannot parse '{raw}' in column '{date_col}' as a date at row {idx}."
                ),
            ))
            continue
        if coerced < min_date or coerced > max_date:
            errors.append(ValidationError(
                sheet=sheet_name,
                row=idx,
                column=date_col,
                value=str(coerced),
                rule="date_range",
                severity="WARNING",
                message=(
                    f"Date {coerced} in column '{date_col}' at row {idx} "
                    f"is outside expected range [{min_date}, {max_date}]."
                ),
            ))
    return errors


def check_numeric_range(
    sheet_name: str,
    records: List[dict],
    col: str,
    min_val: float,
    max_val: float,
) -> List[ValidationError]:
    """Flag rows where a numeric column is outside [min_val, max_val]."""
    errors: List[ValidationError] = []
    if not records:
        return errors

    for idx, record in enumerate(records, start=1):
        raw = record.get(col)
        if _is_null(raw):
            continue
        num = _to_float(raw)
        if num is None:
            errors.append(ValidationError(
                sheet=sheet_name,
                row=idx,
                column=col,
                value=raw,
                rule="numeric_range",
                severity="WARNING",
                message=(
                    f"Cannot coerce '{raw}' in column '{col}' to a number at row {idx}."
                ),
            ))
            continue
        if num < min_val or num > max_val:
            errors.append(ValidationError(
                sheet=sheet_name,
                row=idx,
                column=col,
                value=num,
                rule="numeric_range",
                severity="WARNING",
                message=(
                    f"Value {num} in column '{col}' at row {idx} "
                    f"is outside expected range [{min_val}, {max_val}]."
                ),
            ))
    return errors


def check_valid_status(
    sheet_name: str,
    records: List[dict],
    col: str,
    allowed_values: Set[str],
) -> List[ValidationError]:
    """Flag rows where a status/enum column contains an unrecognised value."""
    errors: List[ValidationError] = []
    if not records:
        return errors

    for idx, record in enumerate(records, start=1):
        raw = record.get(col)
        if _is_null(raw):
            continue  # null handled by check_no_nulls if mandatory
        value_str = str(raw).strip()
        if value_str not in allowed_values:
            errors.append(ValidationError(
                sheet=sheet_name,
                row=idx,
                column=col,
                value=raw,
                rule="valid_status",
                severity="WARNING",
                message=(
                    f"Unexpected value '{value_str}' in column '{col}' at row {idx}. "
                    f"Allowed: {sorted(allowed_values)}."
                ),
            ))
    return errors


def check_referential_integrity(
    sheet_name: str,
    records: List[dict],
    fk_col: str,
    reference_set: Set[Any],
) -> List[ValidationError]:
    """Flag rows where a foreign-key column references a value not in reference_set."""
    errors: List[ValidationError] = []
    if not records:
        return errors

    # Normalise reference_set to strings for consistent comparison
    ref_str = {str(v).strip() for v in reference_set if v is not None}

    for idx, record in enumerate(records, start=1):
        raw = record.get(fk_col)
        if _is_null(raw):
            continue  # nulls handled elsewhere
        key = str(raw).strip()
        if key not in ref_str:
            errors.append(ValidationError(
                sheet=sheet_name,
                row=idx,
                column=fk_col,
                value=raw,
                rule="referential_integrity",
                severity="CRITICAL",
                message=(
                    f"Orphaned FK value '{key}' in column '{fk_col}' at row {idx}: "
                    f"not found in reference set."
                ),
            ))
    return errors
