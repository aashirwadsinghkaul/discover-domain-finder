from __future__ import annotations

import csv
import os
from pathlib import Path

from .models import DomainResult
from .normalize import InvalidDomain, normalize_domain


DOMAIN_COLUMNS = ("domain", "hostname", "host", "url", "website", "site")
OUTPUT_FIELDS = list(DomainResult("").as_row().keys())


def read_domains(path: str | Path, column: str | None = None) -> tuple[list[str], list[str]]:
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"input file not found: {source}")
    raw_values: list[str] = []
    if source.suffix.lower() == ".csv":
        with source.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            fields = reader.fieldnames or []
            selected = column
            if selected and selected not in fields:
                raise ValueError(f"CSV column '{selected}' not found; available: {', '.join(fields)}")
            if not selected:
                lookup = {name.strip().lower(): name for name in fields}
                selected = next((lookup[name] for name in DOMAIN_COLUMNS if name in lookup), None)
            if not selected:
                if len(fields) == 1:
                    selected = fields[0]
                else:
                    raise ValueError("could not find a domain column; use --column COLUMN_NAME")
            raw_values.extend((row.get(selected) or "") for row in reader)
    else:
        with source.open(encoding="utf-8-sig") as handle:
            raw_values.extend(line.strip() for line in handle if line.strip() and not line.lstrip().startswith("#"))

    domains: list[str] = []
    warnings: list[str] = []
    seen: set[str] = set()
    for index, value in enumerate(raw_values, start=1):
        try:
            domain = normalize_domain(value)
        except InvalidDomain as exc:
            warnings.append(f"row {index}: {exc}")
            continue
        if domain not in seen:
            seen.add(domain)
            domains.append(domain)
    return domains, warnings


def write_results(path: str | Path, results: list[DomainResult]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(results, key=lambda item: (-item.score, item.domain))
    temporary = destination.with_name(f".{destination.name}.tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        for rank, result in enumerate(ordered, start=1):
            row = result.as_row()
            row["rank"] = rank
            writer.writerow(row)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, destination)
