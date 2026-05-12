#!/usr/bin/env python3
"""Resolve lnkd.in short links to their final destination URLs.

Usage:
    python scripts/resolve_links.py
"""

from __future__ import annotations

import re
import sys
from html import unescape

import requests

LINKS = [
    "https://lnkd.in/dPPpttHg",
    "https://lnkd.in/dWCVfXsA",
    "https://lnkd.in/gtqdw864",
    "https://lnkd.in/gkCpv7NA",
    "https://lnkd.in/gQTuepVf",
    "https://lnkd.in/gnFS4frz",
    "https://lnkd.in/gRPrQrf5",
    "https://lnkd.in/ggYbizNB",
    "https://lnkd.in/gQYCkwS2",
    "https://lnkd.in/gYtZQY53",
    "https://lnkd.in/d89TewuQ",
    "https://lnkd.in/ddn7hfeu",
    "https://lnkd.in/dUyvbSwC",
    "https://lnkd.in/dn83kbwv",
    "https://lnkd.in/d53iPD-U",
    "https://lnkd.in/dtVqDV-g",
    "https://lnkd.in/dt_-2-Uj",
    "https://lnkd.in/dqvnAmSK",
    "https://lnkd.in/gTY4pZgu",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}
TIMEOUT_SEC = 10

# lnkd.in serves an HTML interstitial (no HTTP redirect). The real destination
# lives in an <a> tag flagged with data-tracking-control-name="external_url_click".
_LNKD_EXTERNAL_HREF = re.compile(
    r'data-tracking-control-name="external_url_click"[^>]*href="([^"]+)"',
    re.IGNORECASE,
)


def _extract_lnkd_destination(html: str) -> str | None:
    match = _LNKD_EXTERNAL_HREF.search(html)
    return unescape(match.group(1)) if match else None


def resolve(url: str) -> str:
    try:
        r = requests.get(url, allow_redirects=True, timeout=TIMEOUT_SEC, headers=HEADERS)
    except requests.Timeout:
        return "ERROR: timeout"
    except requests.ConnectionError as e:
        return f"ERROR: connection ({type(e).__name__})"
    except requests.RequestException as e:
        return f"ERROR: {type(e).__name__}: {e}"

    # If the server issued real HTTP redirects, r.url is already the destination.
    if "lnkd.in" not in r.url:
        return r.url

    # Otherwise parse the LinkedIn interstitial.
    dest = _extract_lnkd_destination(r.text)
    if dest:
        return dest
    return f"ERROR: could not parse destination (status {r.status_code})"


def main() -> int:
    width = max(len(u) for u in LINKS)
    for url in LINKS:
        resolved = resolve(url)
        print(f"{url:<{width}}  ->  {resolved}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
