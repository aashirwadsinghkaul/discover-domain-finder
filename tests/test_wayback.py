import json
import unittest
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit

from discover_domain_finder.wayback import WaybackClient, WaybackError


FIXTURE = Path(__file__).parent / "fixtures" / "cdx_publisher.json"


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self):
        return self.payload


class WaybackTests(unittest.TestCase):
    def test_parses_fixture_and_builds_filtered_query(self):
        requests = []

        def opener(request, timeout):
            requests.append((request, timeout))
            return FakeResponse(FIXTURE.read_bytes())

        captures = WaybackClient(opener=opener, sleeper=lambda _: None).fetch("example.com")
        self.assertEqual(len(captures), 5)
        self.assertEqual(captures[0].year, 2018)
        query = parse_qs(urlsplit(requests[0][0].full_url).query)
        self.assertEqual(query["url"], ["example.com/*"])
        self.assertEqual(query["filter"], ["statuscode:200", "mimetype:text/html"])
        self.assertEqual(query["collapse"], ["digest"])

    def test_retries_transient_error_then_succeeds(self):
        attempts = []
        sleeps = []

        def opener(request, timeout):
            attempts.append(1)
            if len(attempts) < 3:
                raise URLError("temporary")
            return FakeResponse(b'[["timestamp","original"],["20200101","https://x.com/blog/story"]]')

        client = WaybackClient(retries=2, delay=0, opener=opener, sleeper=sleeps.append)
        self.assertEqual(len(client.fetch("x.com")), 1)
        self.assertEqual(len(attempts), 3)
        self.assertEqual(len(sleeps), 2)

    def test_non_retryable_http_error_stops(self):
        attempts = []

        def opener(request, timeout):
            attempts.append(1)
            raise HTTPError(request.full_url, 403, "Forbidden", {}, None)

        with self.assertRaisesRegex(WaybackError, "HTTP 403"):
            WaybackClient(retries=5, opener=opener, sleeper=lambda _: None).fetch("x.com")
        self.assertEqual(len(attempts), 1)

    def test_bad_json_and_bad_shape_become_wayback_error(self):
        for payload in (b"not-json", json.dumps([["wrong"]]).encode()):
            with self.subTest(payload=payload):
                client = WaybackClient(retries=0, opener=lambda *_args, **_kwargs: FakeResponse(payload))
                with self.assertRaises(WaybackError):
                    client.fetch("x.com")

    def test_empty_response_is_valid(self):
        client = WaybackClient(opener=lambda *_args, **_kwargs: FakeResponse(b"[]"))
        self.assertEqual(client.fetch("x.com"), [])


if __name__ == "__main__":
    unittest.main()
