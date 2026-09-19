# Discover Domain Finder

Discover Domain Finder ranks expired-domain candidates using historical publishing evidence from the Internet Archive's Wayback Machine.

It accepts a plain text or CSV list, finds archived HTML URLs, and looks for signals such as:

- `/blog/`, `/news/`, `/articles/`, `/guides/`, `/resources/`, and `/insights/` sections
- year/month article URL patterns and descriptive slugs
- WordPress traces
- number of likely article URLs
- archive year coverage and consecutive-year continuity
- common spam URL terms (adult, pharma, payday loan, crypto giveaway, and warez terms)

The output is a ranked CSV with an explainable 0–100 score and one of four verdicts: `HIGH`, `GOOD`, `REVIEW`, or `LOW`.

> **Important:** This is a historical-content heuristic. A high score does **not** prove that a domain received traffic from Google Discover. Confirmed historical Discover performance requires legitimate access to that domain's Google Search Console property. Do not buy a domain from this score alone; also check trademarks, backlinks, penalties, current indexing, and archive snapshots manually.

## Quick start on a Mac

You need Python 3.10 or newer. Check it by opening Terminal and running:

```bash
python3 --version
```

Then open Terminal in this project folder and run these commands one at a time:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install .
discover-domain-finder sample_domains.txt --output ranked_domains.csv
```

When it finishes, open `ranked_domains.csv` in Numbers, Excel, or Google Sheets. On future runs, open the project folder and run:

```bash
source .venv/bin/activate
discover-domain-finder domains.txt
```

The program uses no third-party runtime libraries.

## Prepare input

### Text file

Create `domains.txt`, one domain or URL per line. Blank lines and lines beginning with `#` are ignored.

```text
example.com
https://www.example.org/some/path
# a note
another-example.net
```

`www`, letter case, URL paths, and duplicates are normalized automatically.

### CSV file

The program automatically recognizes columns named `domain`, `hostname`, `host`, `url`, `website`, or `site` (case-insensitive):

```csv
domain,note
example.com,auction list
example.org,shortlist
```

For a differently named column, specify it:

```bash
discover-domain-finder candidates.csv --column candidate_domain --output results.csv
```

Invalid input rows are reported as warnings and skipped. Duplicate domains are checked once.

## Useful options

```bash
discover-domain-finder domains.txt \
  --output ranked_domains.csv \
  --delay 1.5 \
  --timeout 30 \
  --retries 3 \
  --max-records 5000
```

| Option | Meaning |
| --- | --- |
| `-o`, `--output` | Output CSV path |
| `--column` | Domain column for CSV input |
| `--delay` | Pause between domains; keep this polite to the free archive service |
| `--timeout` | Seconds before a request times out |
| `--retries` | Retries for rate limits and temporary server/network errors |
| `--max-records` | Maximum archive rows requested per domain |

For all options:

```bash
discover-domain-finder --help
```

## Reading the CSV

The most useful columns are:

- `score` and `verdict`: overall heuristic rank
- `likely_articles` and `article_ratio`: estimated publishing depth
- `archive_years`, `first_year`, `last_year`, and `longest_year_streak`: history and continuity
- `section_signal_urls` and `wordpress_urls`: publishing-platform evidence
- `spam_urls` and `spam_ratio`: URL-level warning signals that lower the score
- `sample_articles`: up to five URLs for manual archive review
- `error`: a per-domain failure message; one failed request does not stop the batch

The score intentionally combines several weak signals rather than treating any single URL pattern as proof. Broad, continuous publishing history raises the score. Spam-heavy archives reduce it. Thresholds are currently:

| Score | Verdict | Interpretation |
| --- | --- | --- |
| 75–100 | `HIGH` | Strong historical publishing evidence; manually verify |
| 55–74 | `GOOD` | Meaningful evidence; worth deeper review |
| 35–54 | `REVIEW` | Mixed or limited evidence |
| 0–34 | `LOW` | Thin evidence or substantial warning signals |

## Wayback limitations

The Wayback Machine is a free external service. Coverage can be incomplete, the CDX API can be temporarily unavailable or rate-limited, and archived URLs can include old redirects or hacked content. The tool therefore:

- requests only historical HTML records with successful status codes
- collapses identical content while retaining changed captures across years
- retries temporary failures with exponential backoff
- waits between domains
- deduplicates canonical page URLs
- records per-domain failures in the CSV and continues

For large lists, use a larger `--delay` and run in smaller batches.

## Development and tests

The automated suite uses mocks and a local CDX fixture. It never needs live Wayback access.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
python3 -m unittest discover -s tests -v
```

The tests cover domain normalization, international domains, URL/content classification, canonical deduplication, scoring and verdict boundaries, text/CSV input, ranking output, malformed archive data, retries, HTTP errors, empty responses, and batch continuation after API errors.

## Responsible use

Respect Internet Archive availability and terms, use conservative request rates, and inspect candidate domains yourself. Only use Search Console data for properties you are legitimately authorized to access.

## License

MIT

