import csv
import tempfile
import unittest
from pathlib import Path

from discover_domain_finder.io import read_domains, write_results
from discover_domain_finder.models import DomainResult


class InputOutputTests(unittest.TestCase):
    def test_reads_text_ignores_comments_invalid_and_duplicates(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "domains.txt"
            path.write_text("# note\nExample.com\nhttps://www.example.com/x\nnot-a-domain\nother.org\n", encoding="utf-8")
            domains, warnings = read_domains(path)
        self.assertEqual(domains, ["example.com", "other.org"])
        self.assertEqual(len(warnings), 1)

    def test_reads_csv_detected_and_explicit_columns(self):
        with tempfile.TemporaryDirectory() as directory:
            detected = Path(directory) / "detected.csv"
            detected.write_text("name,Website\nA,https://www.example.com/a\n", encoding="utf-8")
            self.assertEqual(read_domains(detected)[0], ["example.com"])
            explicit = Path(directory) / "explicit.csv"
            explicit.write_text("candidate,note\nother.org,x\n", encoding="utf-8")
            self.assertEqual(read_domains(explicit, "candidate")[0], ["other.org"])

    def test_csv_missing_column_is_clear_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "x.csv"
            path.write_text("a,b\nexample.com,x\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "--column"):
                read_domains(path)

    def test_write_results_ranks_and_includes_disclaimer(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "out.csv"
            write_results(path, [DomainResult("low.com", score=10), DomainResult("high.com", score=80)])
            with path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
        self.assertEqual([row["domain"] for row in rows], ["high.com", "low.com"])
        self.assertEqual(rows[0]["rank"], "1")
        self.assertIn("does not prove", rows[0]["disclaimer"])
        self.assertFalse((path.parent / f".{path.name}.tmp").exists())


if __name__ == "__main__":
    unittest.main()
