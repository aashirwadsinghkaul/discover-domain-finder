import argparse
import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from discover_domain_finder.cli import DISCLAIMER, run
from discover_domain_finder.models import Capture
from discover_domain_finder.wayback import WaybackError


class FakeClient:
    def fetch(self, domain):
        if domain == "broken.example":
            raise WaybackError("offline")
        return [Capture("20210101000000", f"https://{domain}/blog/a-helpful-story")]


class CLITests(unittest.TestCase):
    def test_batch_continues_after_per_domain_api_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "in.txt"
            output = Path(directory) / "out.csv"
            source.write_text("good.example\nbroken.example\n", encoding="utf-8")
            args = argparse.Namespace(input=str(source), output=str(output), column=None, delay=0,
                                      timeout=1, retries=0, max_records=10, workers=2, endpoint="unused")
            self.assertEqual(run(args, client=FakeClient()), 0)
            with output.open(newline="", encoding="utf-8") as handle:
                rows = {row["domain"]: row for row in csv.DictReader(handle)}
        self.assertEqual(rows["broken.example"]["error"], "offline")
        self.assertEqual(rows["broken.example"]["score"], "0")
        self.assertEqual(rows["broken.example"]["verdict"], "ERROR")
        self.assertEqual(rows["good.example"]["likely_articles"], "1")

    def test_invalid_numeric_options(self):
        args = argparse.Namespace(input="missing", output="x", column=None, delay=-1,
                                  timeout=1, retries=0, max_records=10, workers=2, endpoint="unused")
        with self.assertRaisesRegex(ValueError, "non-negative"):
            run(args, client=FakeClient())

    def test_disclaimer_is_explicit(self):
        self.assertIn("do NOT prove", DISCLAIMER)
        self.assertIn("Search Console", DISCLAIMER)

    def test_csv_is_refreshed_after_each_completed_domain(self):
        from discover_domain_finder.io import write_results as real_write

        calls = []

        def recording_write(path, results):
            calls.append(len(results))
            return real_write(path, results)

        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "in.txt"
            output = Path(directory) / "out.csv"
            source.write_text("one.example\ntwo.example\nthree.example\n", encoding="utf-8")
            args = argparse.Namespace(input=str(source), output=str(output), column=None, delay=0,
                                      timeout=1, retries=0, max_records=10, workers=3, endpoint="unused")
            with patch("discover_domain_finder.cli.write_results", side_effect=recording_write):
                run(args, client=FakeClient())
        self.assertEqual(calls, [0, 1, 2, 3])


if __name__ == "__main__":
    unittest.main()
