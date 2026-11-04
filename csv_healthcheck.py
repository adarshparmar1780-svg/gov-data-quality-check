#!/usr/bin/env python3
"""Report basic structural issues in a CSV without changing the file."""

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path


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
            key = tuple(cell.strip() for cell in row)
            if key in seen_rows:
                duplicate_rows += 1
            else:
                seen_rows.add(key)

    return {
        "headers": headers,
        "rows": row_count,
        "missing": missing,
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
    has_findings = report["duplicate_rows"] or report["malformed_rows"] or nonempty_missing
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
            "blank_or_absent_cells": dict(report["missing"]),
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

    if has_findings:
        print("Review the flagged rows and source documentation; these checks do not prove the data is incorrect.")
        return 1
    print("No configured structural issues detected. This is not a validation of the data's meaning or accuracy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

