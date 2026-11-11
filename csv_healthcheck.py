#!/usr/bin/env python3
"""Report basic structural issues in a CSV without changing the file."""

import argparse
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

FORMULA_PREFIXES = ("=", "@", "\t", "\r", "\n", "＝", "＠")
NUMERIC_VALUE_RE = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?\Z")


def _may_be_spreadsheet_formula(value):
    candidate = value.lstrip(" \u00a0")
    if not candidate:
        return False
    if candidate[0] in FORMULA_PREFIXES:
        return True
    if candidate[0] in ("+", "-", "＋", "－"):
        return not NUMERIC_VALUE_RE.fullmatch(candidate)
    return False


def inspect_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        rows = csv.reader(source, strict=True)
        try:
            headers = next(rows)
        except StopIteration as exc:
            raise ValueError("the CSV file is empty") from exc

        normalized_headers = [header.strip().casefold() for header in headers]
        if not headers or any(not header for header in normalized_headers):
            raise ValueError("the header row contains an empty column name")
        if len(set(normalized_headers)) != len(normalized_headers):
            raise ValueError("the header row contains duplicate column names")

        missing = Counter()
        nul_cells = 0
        nul_locations = []
        formula_locations = [(1, header) for header in headers if _may_be_spreadsheet_formula(header)]
        seen_rows = set()
        duplicate_rows = 0
        malformed_rows = []
        row_count = 0

        previous_line = rows.line_num
        while True:
            try:
                row = next(rows)
            except StopIteration:
                break
            line_number = previous_line + 1
            previous_line = rows.line_num
            row_count += 1
            if len(row) != len(headers):
                malformed_rows.append((line_number, len(row)))
            for index, header in enumerate(headers):
                if index >= len(row) or not row[index].strip():
                    missing[header] += 1
            for index, cell in enumerate(row):
                column = headers[index] if index < len(headers) else f"field {index + 1}"
                if "\x00" in cell:
                    nul_locations.append((line_number, column))
                if _may_be_spreadsheet_formula(cell):
                    formula_locations.append((line_number, column))
            nul_cells = len(nul_locations)
            key = tuple(cell.strip() for cell in row)
            if key in seen_rows:
                duplicate_rows += 1
            else:
                seen_rows.add(key)

    return {
        "headers": headers,
        "rows": row_count,
        "missing": missing,
        "nul_cells": nul_cells,
        "nul_locations": nul_locations,
        "formula_cells": len(formula_locations),
        "formula_locations": formula_locations,
        "duplicate_rows": duplicate_rows,
        "malformed_rows": malformed_rows,
    }


def main():
    parser = argparse.ArgumentParser(description="Check CSV structure, blank cells, and repeated rows.")
    parser.add_argument("csv_file", type=Path, help="CSV file to inspect (read-only)")
    parser.add_argument("--json", action="store_true", dest="json_output", help="print a machine-readable JSON report")
    args = parser.parse_args()

    try:
        report = inspect_csv(args.csv_file)
    except (OSError, UnicodeError, csv.Error, ValueError) as exc:
        print(f"Could not inspect CSV: {exc}", file=sys.stderr)
        return 2

    nonempty_missing = [(name, count) for name, count in report["missing"].items() if count]
    has_findings = (report["duplicate_rows"] or report["malformed_rows"] or nonempty_missing or report["nul_cells"] or report["formula_cells"])
    if args.json_output:
        print(json.dumps({
            "file": str(args.csv_file),
            "headers": report["headers"],
            "data_rows": report["rows"],
            "duplicate_rows": report["duplicate_rows"],
            "malformed_rows": [
                {"line": line, "field_count": fields, "expected_field_count": len(report["headers"])}
                for line, fields in report["malformed_rows"]
            ],
            "possible_spreadsheet_formula_cells": report["formula_cells"],
            "possible_spreadsheet_formula_locations": [
                {"line": line, "column": column} for line, column in report["formula_locations"]
            ],
            "blank_or_absent_cells": dict(report["missing"]),
            "cells_with_nul_bytes": report["nul_cells"],
            "nul_cell_locations": [
                {"line": line, "column": column} for line, column in report["nul_locations"]
            ],
        }, indent=2))
        return 1 if has_findings else 0

    print(f"CSV data quality report: {args.csv_file}")
    print(f"Data rows: {report['rows']}")
    print(f"Columns: {len(report['headers'])}")
    print(f"Repeated rows after the first occurrence: {report['duplicate_rows']}")
    print(f"Rows with a different field count than the header: {len(report['malformed_rows'])}")
    if report["malformed_rows"]:
        for line_number, field_count in report["malformed_rows"]:
            print(f"  Line {line_number}: {field_count} fields; expected {len(report['headers'])}")

    if nonempty_missing:
        print("Blank or absent cells:")
        for name, count in nonempty_missing:
            print(f"  {name}: {count}")
    else:
        print("Blank or absent cells: none detected")

    print("Cells containing NUL bytes: {}".format(report["nul_cells"]))
    for line, column in report["nul_locations"]:
        print(f"  Line {line}, column {column}")
    print("Possible spreadsheet formula cells: {}".format(report["formula_cells"]))
    for line, column in report["formula_locations"]:
        print(f"  Line {line}, column {column}")
    if has_findings:
        print("Review the flagged rows and source documentation; these checks do not prove the data is incorrect.")
        return 1
    print("No configured structural issues detected. This is not a validation of the data's meaning or accuracy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

