import unittest

from discover_domain_finder.models import Capture
from discover_domain_finder.scoring import analyze_domain, verdict_for


class ScoringTests(unittest.TestCase):
    def test_strong_continuous_publisher_scores_above_thin_site(self):
        strong = [
            Capture(f"{year}0101000000", f"https://example.com/blog/{year}/01/story-{year}-{i}")
            for year in range(2016, 2024)
            for i in range(5)
        ]
        thin = [Capture("20200101000000", "https://thin.example/about")]
        strong_result = analyze_domain("example.com", strong)
        thin_result = analyze_domain("thin.example", thin)
        self.assertGreaterEqual(strong_result.score, 75)
        self.assertEqual(strong_result.verdict, "HIGH")
        self.assertGreater(strong_result.score, thin_result.score)
        self.assertEqual(strong_result.longest_year_streak, 8)

    def test_deduplicates_canonical_urls_but_keeps_capture_count(self):
        captures = [
            Capture("20200101000000", "http://www.example.com/blog/same-story?utm_source=a"),
            Capture("20210101000000", "http://example.com/blog/same-story/"),
        ]
        result = analyze_domain("example.com", captures)
        self.assertEqual(result.captures, 2)
        self.assertEqual(result.unique_urls, 1)
        self.assertEqual(result.archive_years, 2)

    def test_spam_penalty_reduces_score_and_empty_is_low(self):
        clean = [Capture("20200101000000", f"https://x.com/news/helpful-story-{i}") for i in range(20)]
        spam = [Capture("20200101000000", f"https://x.com/news/casino-poker-viagra-{i}") for i in range(20)]
        self.assertGreater(analyze_domain("x.com", clean).score, analyze_domain("x.com", spam).score)
        empty = analyze_domain("empty.com", [])
        self.assertEqual((empty.score, empty.verdict, empty.data_status), (0, "NO_DATA", "NO_DATA"))

    def test_verdict_boundaries(self):
        self.assertEqual([verdict_for(x) for x in (0, 34, 35, 54, 55, 74, 75, 100)],
                         ["LOW", "LOW", "REVIEW", "REVIEW", "GOOD", "GOOD", "HIGH", "HIGH"])

    def test_malformed_archive_url_does_not_break_domain(self):
        captures = [
            Capture("20200101000000", "https://example.com:bad/blog/broken"),
            Capture("20210101000000", "https://example.com/blog/good-story"),
        ]
        result = analyze_domain("example.com", captures)
        self.assertEqual(result.captures, 2)
        self.assertEqual(result.unique_urls, 1)


if __name__ == "__main__":
    unittest.main()
