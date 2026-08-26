from __future__ import annotations

import os
import re
from pathlib import Path
from xml.etree import ElementTree as ET

SITE_URL = os.getenv("SITE_URL", "https://crypto-factory-studios.cryptofactorystudios.workers.dev").rstrip("/")
FRONTEND = Path(__file__).resolve().parents[1] / "frontend"
SEO_PAGES = {
    "index.html": "/",
    "publish-web-game.html": "/publish-web-game.html",
    "publish-html5-game.html": "/publish-html5-game.html",
    "godot-web-hosting.html": "/godot-web-hosting.html",
    "how-to-publish-godot-game-web.html": "/how-to-publish-godot-game-web.html",
    "indie-game-hosting.html": "/indie-game-hosting.html",
    "browser-games.html": "/browser-games.html",
    "creator-platform.html": "/creator-platform.html",
}
FORBIDDEN_SEO_HOSTS = {
    "https://crypto-factory-studios.cesargp9712.workers.dev",
    "https://crypto-factory-studios.onrender.com",
}


def _attr(html: str, tag_pattern: str, attr: str) -> str | None:
    match = re.search(tag_pattern, html, flags=re.IGNORECASE)
    if not match:
        return None
    value = re.search(rf'{attr}=["\']([^"\']+)["\']', match.group(0), flags=re.IGNORECASE)
    return value.group(1) if value else None


def validate_pages() -> None:
    for filename, path in SEO_PAGES.items():
        html = (FRONTEND / filename).read_text(encoding="utf-8")
        expected = f"{SITE_URL}{path}" if path != "/" else f"{SITE_URL}/"
        canonical = _attr(html, r"<link\b[^>]*rel=[\"']canonical[\"'][^>]*>", "href")
        og_url = _attr(html, r"<meta\b[^>]*property=[\"']og:url[\"'][^>]*>", "content")
        assert canonical == expected, f"{filename}: canonical={canonical!r}, expected={expected!r}"
        assert og_url == expected, f"{filename}: og:url={og_url!r}, expected={expected!r}"
        for forbidden in FORBIDDEN_SEO_HOSTS:
            assert forbidden not in html, f"{filename}: forbidden SEO host {forbidden}"


def validate_robots() -> None:
    robots = (FRONTEND / "robots.txt").read_text(encoding="utf-8")
    expected = f"Sitemap: {SITE_URL}/sitemap.xml"
    assert expected in robots, f"robots.txt missing {expected}"
    for forbidden in FORBIDDEN_SEO_HOSTS:
        assert forbidden not in robots, f"robots.txt: forbidden SEO host {forbidden}"


def validate_sitemap() -> None:
    sitemap_path = FRONTEND / "sitemap.xml"
    root = ET.parse(sitemap_path).getroot()
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locs = [node.text.strip() for node in root.findall("sm:url/sm:loc", ns) if node.text]
    expected = {
        f"{SITE_URL}{path}" if path != "/" else f"{SITE_URL}/"
        for path in SEO_PAGES.values()
    }
    assert set(locs) == expected, f"sitemap URLs differ: got={set(locs)!r}, expected={expected!r}"
    assert len(locs) == len(set(locs)), "sitemap contains duplicate URLs"
    for loc in locs:
        assert loc.startswith(f"{SITE_URL}/"), f"sitemap foreign host: {loc}"


def main() -> None:
    validate_pages()
    validate_robots()
    validate_sitemap()
    print(f"SEO canonical host validated: {SITE_URL}")


if __name__ == "__main__":
    main()
