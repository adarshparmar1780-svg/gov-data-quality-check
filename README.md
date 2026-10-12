# Government CSV Data Quality Check

A read-only Python command-line tool for spotting basic structural problems in a CSV: blank cells, duplicate rows, and rows whose field count differs from the header. It reports possible issues for a person to review; it does not determine whether the data is true or false.

## Run

Requires Python 3.10 or newer. No packages or network access are needed.

```powershell
py .\csv_healthcheck.py .\sample_data\all_india_rainfall_1901_1906.csv
py .\csv_healthcheck.py .\sample_data\demo_with_issues.csv
```

The first file is a six-row excerpt from an India Meteorological Department rainfall dataset listed on the Government of India's Open Government Data platform. See [SOURCES.md](SOURCES.md) for attribution, license, and limits. The second file is synthetic and intentionally includes examples of the findings this tool reports.

## What it checks

- Empty or duplicate header names
- Blank cells per column
- Repeated rows
- Rows with too few or too many fields
- CSV quoting and file-reading errors

It does not check numeric ranges, units, statistical outliers, whether a value is factually correct, or whether a dataset is up to date. Do not treat a warning as evidence of misconduct or a reason to reject the source.

AI-assisted initial draft. Review and understand the code and data sources before presenting this project as your work.
