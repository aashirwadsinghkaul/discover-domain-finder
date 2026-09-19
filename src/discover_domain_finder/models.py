from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Capture:
    timestamp: str
    url: str
    status_code: str = "200"
    mime_type: str = "text/html"
    digest: str = ""

    @property
    def year(self) -> int | None:
        try:
            value = int(self.timestamp[:4])
            return value if 1990 <= value <= 2100 else None
        except (TypeError, ValueError):
            return None


@dataclass(frozen=True)
class URLSignals:
    normalized_url: str
    article_likely: bool
    section_signals: tuple[str, ...] = ()
    date_pattern: bool = False
    wordpress: bool = False
    spam_signals: tuple[str, ...] = ()


@dataclass
class DomainResult:
    domain: str
    score: int = 0
    verdict: str = "LOW"
    data_status: str = "OK"
    captures: int = 0
    unique_urls: int = 0
    likely_articles: int = 0
    article_ratio: float = 0.0
    archive_years: int = 0
    first_year: int | None = None
    last_year: int | None = None
    longest_year_streak: int = 0
    section_signal_urls: int = 0
    wordpress_urls: int = 0
    spam_urls: int = 0
    spam_ratio: float = 0.0
    sample_articles: list[str] = field(default_factory=list)
    error: str = ""

    def as_row(self) -> dict[str, object]:
        return {
            "rank": "",
            "domain": self.domain,
            "score": self.score,
            "verdict": self.verdict,
            "data_status": self.data_status,
            "captures": self.captures,
            "unique_urls": self.unique_urls,
            "likely_articles": self.likely_articles,
            "article_ratio": f"{self.article_ratio:.3f}",
            "archive_years": self.archive_years,
            "first_year": self.first_year or "",
            "last_year": self.last_year or "",
            "longest_year_streak": self.longest_year_streak,
            "section_signal_urls": self.section_signal_urls,
            "wordpress_urls": self.wordpress_urls,
            "spam_urls": self.spam_urls,
            "spam_ratio": f"{self.spam_ratio:.3f}",
            "sample_articles": " | ".join(self.sample_articles),
            "error": self.error,
            "disclaimer": "Heuristic only; does not prove historical Google Discover traffic.",
        }
