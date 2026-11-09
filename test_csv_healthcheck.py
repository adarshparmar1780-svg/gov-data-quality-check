import csv
import tempfile
import unittest
from pathlib import Path

from csv_healthcheck import inspect_csv


class InspectCsvTests(unittest.TestCase):
    def inspect_text(self, text):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "input.csv"
            path.write_text(text, encoding="utf-8", newline="")
            return inspect_csv(path)

    def test_accepts_utf8_bom_before_first_header(self):
        report = self.inspect_text("\ufeffid,name\n1,Ada\n")
        self.assertEqual(report["headers"], ["id", "name"])

    def test_counts_rows_and_blank_cells(self):
        report = self.inspect_text("id,name\n1,Ada\n2,\n")
        self.assertEqual(report["rows"], 2)
        self.assertEqual(report["missing"]["name"], 1)
        self.assertEqual(report["malformed_rows"], [])

    def test_rejects_empty_file_with_clear_error(self):
        with self.assertRaisesRegex(ValueError, "the CSV file is empty"):
            self.inspect_text("")

    def test_counts_duplicate_rows_after_first_occurrence(self):
        report = self.inspect_text("id,name\n1,Ada\n1,Ada\n")
        self.assertEqual(report["duplicate_rows"], 1)

    def test_counts_cells_containing_nul_bytes(self):
        report = self.inspect_text("id,name\n1,A\x00da\n")
        self.assertEqual(report["nul_cells"], 1)

    def test_tracks_start_line_of_multiline_csv_record(self):
        report = self.inspect_text('id,note\n1,"first\nsecond"\n2,ok\n')
        self.assertEqual(report["rows"], 2)
        self.assertEqual(report["malformed_rows"], [])

    def test_rejects_duplicate_headers_after_normalization(self):
        with self.assertRaisesRegex(ValueError, "duplicate column names"):
            self.inspect_text("ID,id\n1,2\n")

    def test_rejects_unclosed_quoted_field(self):
        with self.assertRaises(csv.Error):
            self.inspect_text('id,note\n1,"unfinished\n')


if __name__ == "__main__":
    unittest.main()
