import unittest

from discover_domain_finder.classify import canonicalize_url, classify_url


class ClassificationTests(unittest.TestCase):
    def test_section_date_and_slug_are_article(self):
        signal = classify_url("https://www.EXAMPLE.com/blog/2021/09/a-useful-story/?utm_source=x#top")
        self.assertTrue(signal.article_likely)
        self.assertTrue(signal.date_pattern)
        self.assertIn("blog", signal.section_signals)
        self.assertEqual(signal.normalized_url, "https://example.com/blog/2021/09/a-useful-story")

    def test_wordpress_query(self):
        signal = classify_url("http://example.com/?p=123")
        self.assertTrue(signal.wordpress)
        self.assertTrue(signal.article_likely)

    def test_assets_and_taxonomy_are_not_articles(self):
        for url in (
            "https://x.com/blog/image.jpg", "https://x.com/category/news/", "https://x.com/feed/",
            "https://x.com/a-propos", "https://x.com/about-us", "https://x.com/contact",
            "https://x.com/concept-art",
        ):
            with self.subTest(url=url):
                self.assertFalse(classify_url(url).article_likely)

    def test_spam_signals(self):
        signal = classify_url("https://example.com/news/best-online-casino-bonus")
        self.assertIn("adult", signal.spam_signals)

    def test_canonicalization_sorts_query_and_removes_tracking(self):
        value = canonicalize_url("https://www.example.com/a//b/?z=2&utm_medium=x&a=1")
        self.assertEqual(value, "https://example.com/a/b?a=1&z=2")


if __name__ == "__main__":
    unittest.main()
