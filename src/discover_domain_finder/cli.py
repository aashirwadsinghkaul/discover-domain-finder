from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from . import __version__
from .io import read_domains, write_results
from .models import DomainResult
from .scoring import analyze_domain
from .wayback import WaybackClient, WaybackError


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
    parser.add_argument("--delay", type=float, default=1.0, help="seconds between domains (default: 1.0)")
    parser.add_argument("--timeout", type=float, default=30.0, help="request timeout seconds (default: 30)")
    parser.add_argument("--retries", type=int, default=3, help="retry count for temporary failures (default: 3)")
    parser.add_argument("--max-records", type=int, default=5000, help="maximum CDX records per domain (default: 5000)")
    parser.add_argument("--endpoint", default="https://web.archive.org/cdx/search/cdx", help=argparse.SUPPRESS)
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def run(args: argparse.Namespace, *, client: WaybackClient | None = None) -> int:
    if args.delay < 0 or args.timeout <= 0 or args.retries < 0 or args.max_records <= 0:
        raise ValueError("delay/retries must be non-negative; timeout/max-records must be positive")
    domains, warnings = read_domains(args.input, args.column)
    for warning in warnings:
        print(f"Warning: {warning}", file=sys.stderr)
    if not domains:
        raise ValueError("no valid domains found in input")
    client = client or WaybackClient(
        endpoint=args.endpoint,
        timeout=args.timeout,
        retries=args.retries,
        delay=max(0.25, args.delay),
        max_records=args.max_records,
    )
    results: list[DomainResult] = []
    for index, domain in enumerate(domains, start=1):
        print(f"[{index}/{len(domains)}] Checking {domain} ...", file=sys.stderr)
        try:
            results.append(analyze_domain(domain, client.fetch(domain)))
        except WaybackError as exc:
            results.append(DomainResult(domain=domain, error=str(exc)))
            print(f"  Could not query Wayback: {exc}", file=sys.stderr)
        if index < len(domains) and args.delay:
            time.sleep(args.delay)
    write_results(args.output, results)
    print(f"Saved {len(results)} ranked domain(s) to {Path(args.output).resolve()}")
    print(DISCLAIMER)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        return run(parser.parse_args(argv))
    except (FileNotFoundError, ValueError, OSError) as exc:
        parser.exit(2, f"Error: {exc}\n")

