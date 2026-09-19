from __future__ import annotations

import argparse
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from . import __version__
from .io import read_domains, write_results
from .models import DomainResult
from .scoring import analyze_domain
from .wayback import FetchResult, WaybackClient, WaybackError


DISCLAIMER = (
    "Scores are historical-content heuristics. They do NOT prove historical Google Discover traffic. "
    "Confirmed Discover performance requires legitimate access to the domain's Google Search Console property."
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="discover-domain-finder",
        description="Rank domains using historical publishing signals in the Wayback Machine.",
        epilog=DISCLAIMER,
    )
    parser.add_argument("input", help="domains.txt or CSV file")
    parser.add_argument("-o", "--output", default="ranked_domains.csv", help="output CSV (default: ranked_domains.csv)")
    parser.add_argument("--column", help="domain column name for CSV input")
    parser.add_argument("--workers", type=int, default=4, help="domains scanned concurrently (default: 4)")
    parser.add_argument("--delay", type=float, default=0.25, help="minimum seconds between Wayback requests (default: 0.25)")
    parser.add_argument("--timeout", type=float, default=30.0, help="request timeout seconds (default: 30)")
    parser.add_argument("--retries", type=int, default=3, help="retry count for temporary failures (default: 3)")
    parser.add_argument("--max-records", type=int, default=5000, help="maximum CDX records per domain (default: 5000)")
    parser.add_argument("--endpoint", default="https://web.archive.org/cdx/search/cdx", help=argparse.SUPPRESS)
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def _scan_domain(domain: str, client: WaybackClient) -> DomainResult:
    try:
        fetched = client.fetch(domain)
        # Keeping list-returning fake/custom clients compatible is useful for
        # integrations written against V1.
        if isinstance(fetched, FetchResult):
            result = analyze_domain(domain, fetched.captures)
            if fetched.warnings:
                result.data_status = "PARTIAL"
                result.error = "Partial Wayback data: " + "; ".join(fetched.warnings)
            return result
        return analyze_domain(domain, fetched)
    except WaybackError as exc:
        return DomainResult(domain=domain, verdict="ERROR", data_status="ERROR", error=str(exc))


def run(args: argparse.Namespace, *, client: WaybackClient | None = None) -> int:
    workers = getattr(args, "workers", 4)
    if args.delay < 0 or args.timeout <= 0 or args.retries < 0 or args.max_records <= 0 or workers <= 0:
        raise ValueError("delay/retries must be non-negative; timeout/max-records/workers must be positive")
    domains, warnings = read_domains(args.input, args.column)
    for warning in warnings:
        print(f"Warning: {warning}", file=sys.stderr)
    if not domains:
        raise ValueError("no valid domains found in input")
    client = client or WaybackClient(
        endpoint=args.endpoint,
        timeout=args.timeout,
        retries=args.retries,
        delay=args.delay,
        max_records=args.max_records,
    )
    results: list[DomainResult] = []
    write_results(args.output, results)
    print(f"Scanning {len(domains)} domain(s) with {workers} workers. CSV updates after every result.", file=sys.stderr)
    with ThreadPoolExecutor(max_workers=min(workers, len(domains))) as executor:
        futures = {executor.submit(_scan_domain, domain, client): domain for domain in domains}
        for completed, future in enumerate(as_completed(futures), start=1):
            result = future.result()
            results.append(result)
            write_results(args.output, results)
            detail = f"score={result.score} verdict={result.verdict} urls={result.unique_urls}"
            if result.error:
                detail += f" error={result.error}"
            print(f"[{completed}/{len(domains)}] {result.domain} -> {detail}", file=sys.stderr, flush=True)
    print(f"Saved {len(results)} ranked domain(s) to {Path(args.output).resolve()}")
    print(DISCLAIMER)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        return run(parser.parse_args(argv))
    except (FileNotFoundError, ValueError, OSError) as exc:
        parser.exit(2, f"Error: {exc}\n")
