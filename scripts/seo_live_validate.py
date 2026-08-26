from __future__ import annotations

import re
import time
import urllib.request
from xml.etree import ElementTree as ET

from seo_config import FORBIDDEN_SEO_HOSTS, SEO_PAGES, SITE_URL


def fetch(path: str) -> tuple[int, str, str]:
    request = urllib.request.Request(
        SITE_URL + path,
        headers={"User-Agent": "CFS-SEO-production-validator/1.0"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.status, response.headers.get("Content-Type", ""), response.read().decode("utf-8")


def expected_url(path: str) -> str:
    return SITE_URL + ("/" if path == "/" else path)


def extract(html: str, pattern: str, attribute: str) -> str | None:
    tag = re.search(pattern, html, flags=re.IGNORECASE)
    if not tag:
        return None
    value = re.search(rf'{attribute}=["\']([^"\']+)["\']', tag.group(0), flags=re.IGNORECASE)
    return value.group(1) if value else None


def wait_for_frontend() -> None:
    expected = expected_url("/")
    last_error = "not checked"
    for attempt in range(1, 37):
        try:
            status, content_type, html = fetch("/")
            canonical = extract(html, r"<link\b[^>]*rel=[\"']canonical[\"'][^>]*>", "href")
            if status == 200 and "text/html" in content_type.lower() and canonical == expected:
                print(f"frontend ready on attempt {attempt}: {expected}")
                return
            last_error = f"status={status} content_type={content_type!r} canonical={canonical!r}"
        except Exception as exc:
            last_error = repr(exc)
        print(f"frontend not ready on attempt {attempt}: {last_error}")
        time.sleep(10)
    raise AssertionError(f"canonical frontend did not become ready: {last_error}")


def validate_pages() -> None:
    for path in SEO_PAGES.values():
        status, content_type, html = fetch(path)
        expected = expected_url(path)
        assert status == 200, (path, status)
        assert "text/html" in content_type.lower(), (path, content_type)
        canonical = extract(html, r"<link\b[^>]*rel=[\"']canonical[\"'][^>]*>", "href")
        og_url = extract(html, r"<meta\b[^>]*property=[\"']og:url[\"'][^>]*>", "content")
        assert canonical == expected, (path, canonical, expected)
        assert og_url == expected, (path, og_url, expected)
        assert not any(host in html for host in FORBIDDEN_SEO_HOSTS), f"{path}: obsolete SEO host found"
        print(f"page ok: {expected}")


def validate_robots() -> None:
    status, _, robots = fetch("/robots.txt")
    assert status == 200, status
    assert "Sitemap: " + SITE_URL + "/sitemap.xml" in robots, robots
    assert not any(host in robots for host in FORBIDDEN_SEO_HOSTS), "robots contains obsolete SEO host"
    print("robots.txt ok")


def validate_sitemap() -> None:
    status, _, xml = fetch("/sitemap.xml")
    assert status == 200, status
    root = ET.fromstring(xml)
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locs = [node.text.strip() for node in root.findall("sm:url/sm:loc", ns) if node.text]
    expected = {expected_url(path) for path in SEO_PAGES.values()}
    assert set(locs) == expected, (set(locs), expected)
    assert len(locs) == len(set(locs)), "duplicate sitemap URLs"
    assert not any(host in xml for host in FORBIDDEN_SEO_HOSTS), "sitemap contains obsolete SEO host"
    print("sitemap.xml ok")


def main() -> None:
    wait_for_frontend()
    validate_pages()
    validate_robots()
    validate_sitemap()
    print(f"LIVE SEO VERIFIED: {SITE_URL}")


if __name__ == "__main__":
    main()
