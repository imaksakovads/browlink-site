"""IndexNow ping tool — уведомляет поисковики об изменениях на сайте.

Usage:
    python3 ping_indexnow.py --url https://www.ostinkosmo.ru/
    python3 ping_indexnow.py --urls https://example.com/a https://example.com/b
    python3 ping_indexnow.py --sitemap https://www.ostinkosmo.ru/sitemap.xml
    python3 ping_indexnow.py --all        # все URL из sitemap
"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error
import urllib.parse
import ssl
import xml.etree.ElementTree as ET
from typing import Optional
import certifi

INDEXNOW_KEY = "2ea4787e-3231-41fb-b812-744372ff4a32"
BASE_URL = "https://www.ostinkosmo.ru"
INDEXNOW_API = "https://api.indexnow.org/indexnow"
YANDEX_INDEXNOW = "https://yandex.com/indexnow"


def ping_url(key: str, url: str, endpoint: str) -> tuple[bool, str]:
    """Пингует IndexNow-эндпоинт для одного URL."""
    params = urllib.parse.urlencode({"url": url, "key": key})
    full_url = f"{endpoint}?{params}"
    try:
        ctx = ssl.create_default_context(cafile=certifi.where())
        req = urllib.request.Request(full_url, method="GET")
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            body = resp.read().decode()
            if resp.status in (200, 202):
                return True, f"HTTP {resp.status}"
            return False, f"HTTP {resp.status}: {body[:200]}"
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:200]
        return False, f"HTTP {e.code}: {body}"
    except Exception as e:
        return False, str(e)


def extract_urls_from_sitemap(sitemap_url: str) -> list[str]:
    """Извлекает все <loc> из sitemap.xml."""
    try:
        ctx = ssl.create_default_context(cafile=certifi.where())
        req = urllib.request.Request(sitemap_url)
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            tree = ET.parse(resp)
        root = tree.getroot()
        ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        return [url.findtext("ns:loc", "", ns) for url in root.findall("ns:url", ns)]
    except Exception as e:
        print(f"[ERROR] Failed to parse sitemap: {e}", file=sys.stderr)
        return []


def ping_all(key: str, urls: list[str]) -> tuple[int, int]:
    """Пингует все URL через IndexNow (Bing) и Яндекс."""
    total = len(urls)
    ok = 0
    endpoints = [
        ("IndexNow (Bing)", INDEXNOW_API),
        ("Yandex", YANDEX_INDEXNOW),
    ]

    for url in urls:
        for name, endpoint in endpoints:
            success, msg = ping_url(key, url, endpoint)
            status = "OK" if success else "FAIL"
            print(f"[{status}] {name}: {url} → {msg}")
            if success:
                ok += 1
            else:
                pass  # отдельные ошибки не фатальны

    return total, ok


def main() -> None:
    parser = argparse.ArgumentParser(description="IndexNow ping tool")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--url", help="Single URL to ping")
    group.add_argument("--urls", nargs="+", help="Space-separated URLs")
    group.add_argument("--sitemap", help="Read URLs from sitemap.xml")
    group.add_argument("--all", action="store_true", help="All URLs from main sitemap")
    args = parser.parse_args()

    key = os.getenv("INDEXNOW_KEY", INDEXNOW_KEY)

    if args.url:
        urls = [args.url]
    elif args.urls:
        urls = args.urls
    elif args.sitemap:
        urls = extract_urls_from_sitemap(args.sitemap)
    elif args.all:
        urls = extract_urls_from_sitemap(f"{BASE_URL}/sitemap.xml")

    if not urls:
        print("[ERROR] No URLs to ping", file=sys.stderr)
        sys.exit(1)

    print(f"Pinging {len(urls)} URL(s) via IndexNow...")
    total, ok = ping_all(key, urls)
    print(f"\nDone: {ok}/{total} OK")
    sys.exit(0 if ok > 0 else 1)


if __name__ == "__main__":
    main()
