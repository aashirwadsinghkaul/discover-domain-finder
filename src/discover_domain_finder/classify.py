from __future__ import annotations

import re
from urllib.parse import parse_qsl, unquote, urlsplit, urlunsplit

from .models import URLSignals


SECTION_PATTERNS = {
    "blog": re.compile(r"(?:^|/)(?:blog|blogs)(?:/|$)", re.I),
    "news": re.compile(r"(?:^|/)(?:news|latest-news)(?:/|$)", re.I),
    "articles": re.compile(r"(?:^|/)(?:article|articles)(?:/|$)", re.I),
    "guides": re.compile(r"(?:^|/)(?:guide|guides|how-to)(?:/|$)", re.I),
    "resources": re.compile(r"(?:^|/)(?:resource|resources)(?:/|$)", re.I),
    "insights": re.compile(r"(?:^|/)(?:insight|insights|stories)(?:/|$)", re.I),
}
DATE_PATH = re.compile(r"/(?:19|20)\d{2}/(?:0?[1-9]|1[0-2])(?:/(?:0?[1-9]|[12]\d|3[01]))?(?:/|$)")
WORDPRESS = re.compile(r"/(?:wp-content|wp-includes|wp-json)(?:/|$)|[?&]p=\d+(?:&|$)", re.I)
SPAM_PATTERNS = {
    "adult": re.compile(r"(?:casino|poker|porn|xxx|escort)", re.I),
    "pharma": re.compile(r"(?:viagra|cialis|pharmacy|levitra)", re.I),
    "payday": re.compile(r"(?:payday[-_ ]?loan|quick[-_ ]?loan)", re.I),
    "crypto": re.compile(r"(?:crypto[-_ ]?giveaway|bitcoin[-_ ]?bonus)", re.I),
    "hack": re.compile(r"(?:crack|keygen|warez)", re.I),
}
NON_ARTICLE_EXTENSIONS = re.compile(
    r"\.(?:jpg|jpeg|png|gif|webp|svg|ico|css|js|xml|json|pdf|zip|mp3|mp4|woff2?|ttf)(?:$|\?)",
    re.I,
)
UTILITY_PATH = re.compile(r"/(?:tag|category|author|page|feed|search|login|cart|checkout)(?:/|$)", re.I)
UTILITY_SLUGS = {
    "about", "about-us", "a-propos", "contact", "contact-us", "faq",
    "legal", "legal-notice", "mentions-legales", "privacy", "privacy-policy",
    "terms", "terms-and-conditions", "conditions-generales", "sitemap",
}


def canonicalize_url(url: str) -> str:
    value = unquote((url or "").strip())
    parsed = urlsplit(value)
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    # HTTP and HTTPS copies are the same historical page for ranking purposes.
    # Accessing ``port`` can raise for malformed archived URLs; let the caller
    # discard those records instead of producing a misleading canonical URL.
    port_number = parsed.port
    port = f":{port_number}" if port_number and port_number not in (80, 443) else ""
    path = re.sub(r"/{2,}", "/", parsed.path or "/")
    if path != "/":
        path = path.rstrip("/")
    query = "&".join(
        f"{key}={value}" for key, value in sorted(parse_qsl(parsed.query, keep_blank_values=True))
        if not key.lower().startswith("utm_") and key.lower() not in {"fbclid", "gclid"}
    )
    return urlunsplit(("https", host + port, path, query, ""))


def classify_url(url: str) -> URLSignals:
    normalized = canonicalize_url(url)
    parsed = urlsplit(normalized)
    target = f"{parsed.path}?{parsed.query}" if parsed.query else parsed.path
    sections = tuple(name for name, pattern in SECTION_PATTERNS.items() if pattern.search(parsed.path))
    date_pattern = bool(DATE_PATH.search(parsed.path))
    wordpress = bool(WORDPRESS.search(target))
    spam = tuple(name for name, pattern in SPAM_PATTERNS.items() if pattern.search(target))
    segments = [part for part in parsed.path.split("/") if part]
    final_slug = segments[-1].lower() if segments else ""
    slug_words = [word for word in re.split(r"[-_]", final_slug) if word]
    # Three-word slugs are a useful weak article signal. Two-word service,
    # portfolio and About pages caused too many false positives in V1.
    slug_like = len(slug_words) >= 3 and len(final_slug) >= 12
    excluded = bool(
        NON_ARTICLE_EXTENSIONS.search(target)
        or UTILITY_PATH.search(parsed.path)
        or final_slug in UTILITY_SLUGS
    )
    article_likely = not excluded and bool(sections or date_pattern or slug_like or re.search(r"[?&]p=\d+", target))
    return URLSignals(normalized, article_likely, sections, date_pattern, wordpress, spam)
