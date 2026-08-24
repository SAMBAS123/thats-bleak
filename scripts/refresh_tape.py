#!/usr/bin/env python3
"""Refresh tape.json from Have I Been Pwned + Google News RSS.

One hourly GitHub Action. If a source fails, keep the previous slice.
Does not download dumps or game footage.
"""

from __future__ import annotations

import json
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TAPE_PATH = ROOT / "tape.json"

UA = "BLEAK-tape/0.1 (+https://sambas123.github.io/thats-bleak; public leak blotter)"

TOKEN = None

HIBP_URL = "https://haveibeenpwned.com/api/v3/breaches"
HIBP_PAGE = "https://haveibeenpwned.com/PwnedWebsites"

NEWS_QUERY = (
    'CyberLeek OR "GTA 6 leak" OR "GTA VI leak" OR "data breach" OR "data leak" when:7d'
)

RECORD = [
    {
        "label": "CyberLeek token first traded, footage three days later",
        "value": "Aug 15 → 18",
        "period": "2026 · Solana",
        "source": "Bitquery",
        "url": "https://bitquery.io/investigations/cyberleek-gta6-leak-coin",
    },
    {
        "label": "Take-Two subpoenas to ID the GTA 6 leaker",
        "value": "MS / Discord / X",
        "period": "week of 2026-08-23",
        "source": "BeInCrypto",
        "url": "https://beincrypto.com/gta-vi-cyberleek-meme-coin-rally/",
    },
    {
        "label": "CareCloud patient records stolen",
        "value": "3.7M",
        "period": "confirmed 2026-08",
        "source": "TechCrunch",
        "url": "https://techcrunch.com/2026/08/19/carecloud-confirms-3-7m-patients-had-their-medical-records-stolen-in-a-data-breach/",
    },
    {
        "label": "Exact Sciences on HIBP",
        "value": "10.8M",
        "period": "breach date 2026-07-15",
        "source": "Have I Been Pwned",
        "url": "https://haveibeenpwned.com/PwnedWebsites#ExactSciences",
    },
    {
        "label": "Infostealer Elasticsearch dump",
        "value": "24B records",
        "period": "Jun 2026 · mixed sites",
        "source": "Cybernews",
        "url": "https://cybernews.com/security/24-billion-credentials-data-leak/",
    },
    {
        "label": "Roblox logins listed for sale (alleged, infostealer-class)",
        "value": "50M",
        "period": "Mar 2026 · not a confirmed Roblox hack",
        "source": "Cybernews / Brinztech",
        "url": "https://cybernews.com/security/millions-login-records-allegedly-stolen-from-roblox/",
    },
]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_dt(raw: str | None) -> datetime | None:
    if not raw:
        return None
    raw = raw.strip().replace("Z", "+00:00")
    if "T" not in raw:
        raw = raw + "+00:00"
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def load_prev() -> dict:
    if not TAPE_PATH.exists():
        return {}
    try:
        return json.loads(TAPE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def fetch(url: str, timeout: int = 30) -> bytes:
    ctx = ssl.create_default_context()
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "application/json, application/rss+xml, application/xml, text/xml, */*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        return resp.read()


def pull_catalog() -> dict:
    rows = json.loads(fetch(HIBP_URL))
    if not isinstance(rows, list):
        raise ValueError("HIBP did not return a list")
    now = utc_now()
    cut7 = now - timedelta(days=7)
    cut30 = now - timedelta(days=30)
    dated_2026 = [b for b in rows if str(b.get("BreachDate") or "").startswith("2026")]
    added = []
    for b in rows:
        dt = parse_dt(b.get("AddedDate"))
        if dt:
            added.append((dt, b))
    added.sort(key=lambda x: x[0], reverse=True)
    latest = []
    for dt, b in added[:8]:
        name = b.get("Name") or ""
        latest.append(
            {
                "name": name,
                "title": b.get("Title") or name,
                "added": iso(dt),
                "breach_date": b.get("BreachDate") or "",
                "pwn_count": int(b.get("PwnCount") or 0),
                "url": HIBP_PAGE + "#" + urllib.parse.quote(name),
            }
        )
    pwn_2026 = sum(int(b.get("PwnCount") or 0) for b in dated_2026)
    return {
        "source": HIBP_PAGE,
        "api": HIBP_URL,
        "catalog_total": len(rows),
        "breaches_2026": len(dated_2026),
        "pwn_2026": pwn_2026,
        "added_2026": sum(1 for dt, _ in added if dt.year == 2026),
        "added_7d": sum(1 for dt, _ in added if dt >= cut7),
        "added_30d": sum(1 for dt, _ in added if dt >= cut30),
        "latest": latest,
    }


def parse_rss_date(raw: str | None) -> str | None:
    if not raw:
        return None
    raw = raw.strip()
    for fmt in (
        "%a, %d %b %Y %H:%M:%S %Z",
        "%a, %d %b %Y %H:%M:%S %z",
    ):
        try:
            return iso(datetime.strptime(raw, fmt))
        except ValueError:
            continue
    return raw


def pull_news() -> dict:
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(
        {
            "q": NEWS_QUERY,
            "hl": "en-US",
            "gl": "US",
            "ceid": "US:en",
        }
    )
    xml = fetch(url)
    root = ET.fromstring(xml)
    seen: set[str] = set()
    items: list[dict] = []
    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        if not title or title.lower() in seen:
            continue
        seen.add(title.lower())
        outlet = ""
        if " - " in title:
            title, outlet = title.rsplit(" - ", 1)
        items.append(
            {
                "title": title.strip(),
                "outlet": outlet.strip(),
                "url": link,
                "published": parse_rss_date(item.findtext("pubDate")),
            }
        )
        if len(items) >= 8:
            break
    return {
        "query": NEWS_QUERY,
        "source": "Google News RSS",
        "hits_7d": len(root.findall("./channel/item")),
        "latest": items,
    }


def merge(prev: dict, catalog: dict | None, news: dict | None, errors: list[str]) -> dict:
    prev_c = prev.get("catalog") if isinstance(prev.get("catalog"), dict) else {}
    prev_n = prev.get("news") if isinstance(prev.get("news"), dict) else {}
    token = TOKEN if TOKEN else prev.get("token")
    return {
        "as_of": iso(utc_now()),
        "token": token if token else None,
        "catalog": catalog or prev_c,
        "news": news or prev_n,
        "record": RECORD,
        "errors": errors,
    }


def write_tape(tape: dict) -> None:
    tmp = TAPE_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(tape, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(TAPE_PATH)


def main() -> int:
    prev = load_prev()
    errors: list[str] = []
    catalog = news = None

    try:
        catalog = pull_catalog()
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError) as exc:
        errors.append(f"hibp: {exc}")

    try:
        news = pull_news()
    except (urllib.error.URLError, TimeoutError, ET.ParseError, OSError) as exc:
        errors.append(f"news: {exc}")

    if catalog is None and news is None and not prev:
        print("refresh failed with no prior tape", file=sys.stderr)
        for line in errors:
            print(line, file=sys.stderr)
        return 1

    tape = merge(prev, catalog, news, errors)
    write_tape(tape)
    c = tape.get("catalog") or {}
    n = tape.get("news") or {}
    print(
        f"ok pwn_2026={c.get('pwn_2026')} breaches_2026={c.get('breaches_2026')} "
        f"added_7d={c.get('added_7d')} news_7d={n.get('hits_7d')} errors={len(errors)}"
    )
    for line in errors:
        print(line, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
