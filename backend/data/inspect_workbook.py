"""
Workbook inspection script for Enterprise AI Industrial Dataset v2.
Outputs JSON results to backend/data/workbook_inspection.json
and prints human-readable summary to stdout.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict, Counter
import datetime

try:
    import openpyxl
except ImportError:
    print("ERROR: openpyxl not installed. Run: pip install openpyxl==3.1.2")
    sys.exit(1)

WORKBOOK_PATH = Path(__file__).parent.parent.parent / "project_reference" / "enterprise_ai_industrial_dataset_v2.xlsx"
OUTPUT_PATH = Path(__file__).parent / "workbook_inspection.json"

SAMPLE_ROWS = 3
TYPE_SAMPLE_ROWS = 20


def infer_type(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "float"
    if isinstance(value, datetime.datetime):
        return "datetime"
    if isinstance(value, datetime.date):
        return "date"
    if isinstance(value, str):
        stripped = value.strip()
        if stripped == "":
            return "empty_string"
        # Try numeric
        try:
            int(stripped)
            return "integer_str"
        except ValueError:
            pass
        try:
            float(stripped)
            return "float_str"
        except ValueError:
            pass
        # Try date-like
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
            try:
                datetime.datetime.strptime(stripped, fmt)
                return "date_str"
            except ValueError:
                pass
        return "string"
    return type(value).__name__


def inspect_sheet(ws):
    """Return a dict of inspection results for a single worksheet."""
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return {
            "row_count": 0,
            "columns": [],
            "data_types": {},
            "null_counts": {},
            "sample_rows": [],
            "duplicate_pk_count": 0,
            "duplicate_pk_values": [],
            "negative_numeric_count": 0,
            "out_of_range_pct_count": 0,
            "warnings": ["Sheet is empty"]
        }

    header = rows[0]
    data_rows = rows[1:]
    col_names = [str(h) if h is not None else f"COL_{i}" for i, h in enumerate(header)]
    num_cols = len(col_names)
    row_count = len(data_rows)

    # Infer types from first TYPE_SAMPLE_ROWS data rows
    type_votes = defaultdict(Counter)
    null_counts = defaultdict(int)
    negative_numeric = 0
    out_of_range_pct = 0

    for row in data_rows:
        for i, val in enumerate(row):
            col = col_names[i] if i < num_cols else f"COL_{i}"
            t = infer_type(val)
            if t in ("null", "empty_string"):
                null_counts[col] += 1
            else:
                type_votes[col][t] += 1
            # Check negatives
            if isinstance(val, (int, float)) and not isinstance(val, bool) and val < 0:
                negative_numeric += 1
            # Check out-of-range percentages - column name heuristic
            col_lower = col.lower()
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                if any(kw in col_lower for kw in ["pct", "percent", "rate", "efficiency", "utilization",
                                                    "score", "rating", "quality"]):
                    if val > 100 or val < 0:
                        out_of_range_pct += 1

    # Dominant type per column
    data_types = {}
    for col in col_names:
        if col in type_votes and type_votes[col]:
            data_types[col] = type_votes[col].most_common(1)[0][0]
        else:
            data_types[col] = "null"

    # Sample rows (first 3 data rows)
    sample_rows = []
    for row in data_rows[:SAMPLE_ROWS]:
        sample = {}
        for i, val in enumerate(row):
            col = col_names[i] if i < num_cols else f"COL_{i}"
            if isinstance(val, (datetime.datetime, datetime.date)):
                sample[col] = str(val)
            else:
                sample[col] = val
        sample_rows.append(sample)

    # Duplicate check on first column (candidate PK)
    pk_col = col_names[0] if col_names else None
    pk_values = []
    for row in data_rows:
        if row:
            pk_values.append(row[0])

    pk_non_null = [v for v in pk_values if v is not None]
    pk_counter = Counter(pk_non_null)
    dupes = {str(k): v for k, v in pk_counter.items() if v > 1}
    duplicate_pk_count = len(dupes)
    duplicate_pk_values = list(dupes.keys())[:10]  # show up to 10

    warnings = []
    if duplicate_pk_count > 0:
        warnings.append(f"Duplicate values in first column ({pk_col}): {duplicate_pk_count} duplicated values")
    if negative_numeric > 0:
        warnings.append(f"Negative numeric values found: {negative_numeric} occurrences")
    if out_of_range_pct > 0:
        warnings.append(f"Out-of-range percentage values (>100 or <0): {out_of_range_pct} occurrences")

    # Check null rate for each column - warn if > 50%
    for col, nc in null_counts.items():
        rate = nc / row_count if row_count > 0 else 0
        if rate > 0.5:
            warnings.append(f"Column '{col}' has high null rate: {nc}/{row_count} ({rate:.0%})")

    return {
        "row_count": row_count,
        "columns": col_names,
        "data_types": data_types,
        "null_counts": dict(null_counts),
        "sample_rows": sample_rows,
        "duplicate_pk_column": pk_col,
        "duplicate_pk_count": duplicate_pk_count,
        "duplicate_pk_values": duplicate_pk_values,
        "negative_numeric_count": negative_numeric,
        "out_of_range_pct_count": out_of_range_pct,
        "warnings": warnings
    }


def main():
    print(f"Opening workbook: {WORKBOOK_PATH}")
    if not WORKBOOK_PATH.exists():
        print(f"ERROR: Workbook not found at {WORKBOOK_PATH}")
        sys.exit(1)

    wb = openpyxl.load_workbook(str(WORKBOOK_PATH), read_only=True, data_only=True)
    sheet_names = wb.sheetnames
    print(f"Sheets found ({len(sheet_names)}): {sheet_names}\n")

    results = {
        "workbook_path": str(WORKBOOK_PATH),
        "sheet_count": len(sheet_names),
        "sheet_names": sheet_names,
        "sheets": {}
    }

    for sheet_name in sheet_names:
        print(f"--- Sheet: {sheet_name} ---")
        ws = wb[sheet_name]
        info = inspect_sheet(ws)
        results["sheets"][sheet_name] = info

        print(f"  Rows (excl. header): {info['row_count']}")
        print(f"  Columns ({len(info['columns'])}): {info['columns'][:10]}{'...' if len(info['columns']) > 10 else ''}")
        print(f"  Data types: {dict(list(info['data_types'].items())[:6])}{'...' if len(info['data_types']) > 6 else ''}")

        if info.get("null_counts"):
            top_nulls = sorted(info["null_counts"].items(), key=lambda x: -x[1])[:5]
            print(f"  Top null counts: {top_nulls}")

        print(f"  Duplicate PK ({info.get('duplicate_pk_column')}): {info['duplicate_pk_count']}")
        print(f"  Negative numerics: {info['negative_numeric_count']}")
        print(f"  Out-of-range pct values: {info['out_of_range_pct_count']}")

        if info["warnings"]:
            for w in info["warnings"]:
                print(f"  WARNING: {w}")

        if info["sample_rows"]:
            print(f"  Sample row 1: {dict(list(info['sample_rows'][0].items())[:5])}")
        print()

    wb.close()

    # Write JSON output
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\nInspection results written to: {OUTPUT_PATH}")
    print(f"Total sheets: {len(sheet_names)}")
    total_rows = sum(info["row_count"] for info in results["sheets"].values())
    print(f"Total data rows across all sheets: {total_rows}")


if __name__ == "__main__":
    main()
