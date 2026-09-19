from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .models import Capture


class WaybackError(RuntimeError):
    pass


@dataclass
class WaybackClient:
    endpoint: str = "https://web.archive.org/cdx/search/cdx"
    timeout: float = 30.0
    retries: int = 3
    delay: float = 1.0
    max_records: int = 5000
    user_agent: str = "DiscoverDomainFinder/1.0 (+https://github.com/)"
    opener: Callable = urlopen
    sleeper: Callable[[float], None] = time.sleep

    def fetch(self, domain: str) -> list[Capture]:
        params = {
            "url": f"{domain}/*",
            "output": "json",
            "fl": "timestamp,original,statuscode,mimetype,digest",
            "filter": ["statuscode:200", "mimetype:text/html"],
            # Collapse identical content, not URLs: changed pages across years
            # remain available for the archive continuity estimate.
            "collapse": "digest",
            "limit": str(self.max_records),
        }
        query = urlencode(params, doseq=True)
        request = Request(f"{self.endpoint}?{query}", headers={"User-Agent": self.user_agent, "Accept": "application/json"})
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            if attempt:
                backoff = self.delay * (2 ** (attempt - 1)) + random.uniform(0, self.delay * 0.1)
                self.sleeper(backoff)
            try:
                with self.opener(request, timeout=self.timeout) as response:
                    payload = response.read()
                return self._parse(payload)
            except HTTPError as exc:
                last_error = exc
                if exc.code not in {429, 500, 502, 503, 504}:
                    break
            except (URLError, TimeoutError, OSError, json.JSONDecodeError, ValueError) as exc:
                last_error = exc
        detail = f"HTTP {last_error.code}" if isinstance(last_error, HTTPError) else str(last_error)
        raise WaybackError(f"Wayback request failed after {self.retries + 1} attempt(s): {detail}")

    @staticmethod
    def _parse(payload: bytes | str) -> list[Capture]:
        data = json.loads(payload)
        if not isinstance(data, list) or not data:
            return []
        header = data[0]
        if not isinstance(header, list) or not {"timestamp", "original"}.issubset(header):
            raise ValueError("unexpected Wayback response format")
        positions = {name: index for index, name in enumerate(header)}
        captures: list[Capture] = []
        for row in data[1:]:
            if not isinstance(row, list) or len(row) < len(header):
                continue
            captures.append(Capture(
                timestamp=row[positions["timestamp"]],
                url=row[positions["original"]],
                status_code=row[positions["statuscode"]] if "statuscode" in positions else "200",
                mime_type=row[positions["mimetype"]] if "mimetype" in positions else "text/html",
            ))
        return captures
