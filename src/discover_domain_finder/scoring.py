from __future__ import annotations

import math

from .classify import classify_url
from .models import Capture, DomainResult


def _longest_streak(years: set[int]) -> int:
    best = current = 0
    previous = None
    for year in sorted(years):
        current = current + 1 if previous is not None and year == previous + 1 else 1
        best = max(best, current)
        previous = year
    return best


def verdict_for(score: int) -> str:
    if score >= 75:
        return "HIGH"
    if score >= 55:
        return "GOOD"
    if score >= 35:
        return "REVIEW"
    return "LOW"


def analyze_domain(domain: str, captures: list[Capture]) -> DomainResult:
    if not captures:
        return DomainResult(domain=domain, verdict="NO_DATA", data_status="NO_DATA")
    unique: dict[str, tuple[object, set[int]]] = {}
    all_years: set[int] = set()
    for capture in captures:
        try:
            signals = classify_url(capture.url)
        except (TypeError, ValueError):
            # The CDX can contain malformed legacy URLs. One bad record should
            # not prevent the rest of a domain from being analyzed.
            continue
        year = capture.year
        if year:
            all_years.add(year)
        if signals.normalized_url not in unique:
            unique[signals.normalized_url] = (signals, set())
        if year:
            unique[signals.normalized_url][1].add(year)

    signals_list = [entry[0] for entry in unique.values()]
    total = len(signals_list)
    articles = [signal for signal in signals_list if signal.article_likely]
    section_count = sum(bool(signal.section_signals) for signal in signals_list)
    wordpress_count = sum(signal.wordpress for signal in signals_list)
    spam_count = sum(bool(signal.spam_signals) for signal in signals_list)
    article_ratio = len(articles) / total if total else 0.0
    spam_ratio = spam_count / total if total else 0.0
    streak = _longest_streak(all_years)

    # 100 points: article evidence 35, scale 15, history 25, publishing tech 10,
    # diversity 10, then up to a 35-point spam penalty.
    article_points = min(25, round(7 * math.log2(len(articles) + 1))) + min(10, round(article_ratio * 10))
    scale_points = min(15, round(3 * math.log2(total + 1)))
    history_points = min(15, len(all_years) * 3) + min(10, streak * 2)
    tech_points = min(10, wordpress_count * 2)
    section_types = {name for signal in signals_list for name in signal.section_signals}
    diversity_points = min(10, len(section_types) * 3)
    spam_penalty = min(35, round(spam_ratio * 50) + min(10, spam_count))
    score = max(0, min(100, article_points + scale_points + history_points + tech_points + diversity_points - spam_penalty))

    return DomainResult(
        domain=domain,
        score=score,
        verdict=verdict_for(score),
        captures=len(captures),
        unique_urls=total,
        likely_articles=len(articles),
        article_ratio=article_ratio,
        archive_years=len(all_years),
        first_year=min(all_years) if all_years else None,
        last_year=max(all_years) if all_years else None,
        longest_year_streak=streak,
        section_signal_urls=section_count,
        wordpress_urls=wordpress_count,
        spam_urls=spam_count,
        spam_ratio=spam_ratio,
        sample_articles=[signal.normalized_url for signal in articles[:5]],
    )
