import unittest

from discover_domain_finder.normalize import InvalidDomain, normalize_domain


class NormalizeDomainTests(unittest.TestCase):
    def test_normalizes_url_case_www_port_and_path(self):
        self.assertEqual(normalize_domain(" HTTPS://WWW.Example.COM:443/blog?q=1 "), "example.com")

    def test_normalizes_unicode_idn(self):
        self.assertEqual(normalize_domain("https://münich.example"), "xn--mnich-kva.example")

    def test_removes_trailing_dot(self):
        self.assertEqual(normalize_domain("Example.com."), "example.com")

    def test_rejects_empty_single_label_ip_and_bad_label(self):
        for value in ("", "localhost", "127.0.0.1", "bad_label.com", "-bad.com"):
            with self.subTest(value=value), self.assertRaises(InvalidDomain):
                normalize_domain(value)


if __name__ == "__main__":
    unittest.main()

