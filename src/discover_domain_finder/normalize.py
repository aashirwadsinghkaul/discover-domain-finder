from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlsplit


class InvalidDomain(ValueError):
    pass


_LABEL = re.compile(r"^(?!-)[a-z0-9-]{1,63}(?<!-)$")


def normalize_domain(raw: str) -> str:
    """Return a lowercase ASCII hostname without a leading www."""
    value = (raw or "").strip().strip("\ufeff")
    if not value:
        raise InvalidDomain("domain is empty")
    candidate = value if "://" in value else f"//{value}"
    try:
        parsed = urlsplit(candidate)
        hostname = parsed.hostname
    except ValueError as exc:
        raise InvalidDomain(f"invalid domain: {value}") from exc
    if not hostname:
        raise InvalidDomain(f"invalid domain: {value}")
    hostname = hostname.rstrip(".").lower()
    if hostname.startswith("www."):
        hostname = hostname[4:]
    try:
        hostname = hostname.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise InvalidDomain(f"invalid international domain: {value}") from exc
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        raise InvalidDomain("IP addresses are not supported")
    if len(hostname) > 253 or "." not in hostname:
        raise InvalidDomain(f"invalid domain: {value}")
    if any(not _LABEL.fullmatch(label) for label in hostname.split(".")):
        raise InvalidDomain(f"invalid domain: {value}")
    return hostname

