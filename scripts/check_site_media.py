#!/usr/bin/env python3
"""Fail when the built site contains broken or non-web-ready media references."""

from __future__ import annotations

import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


REPO_ROOT = Path(__file__).resolve().parents[1]
SITE_ROOT = REPO_ROOT / "site"
URL_ATTRIBUTES = {
    "href",
    "poster",
    "src",
    "data-dark-poster",
    "data-dark-src",
    "data-light-poster",
    "data-light-src",
    "data-mobile-src",
}
IGNORED_SCHEMES = {"data", "javascript", "mailto", "tel"}


class ReferenceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.references: list[tuple[str, str, str]] = []
        self.video_without_poster: list[str] = []
        self.placeholder_alt: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {name: value for name, value in attrs}

        for name, value in attrs:
            if name in URL_ATTRIBUTES and value:
                self.references.append((tag, name, value))

        if tag == "video" and "poster" not in values:
            self.video_without_poster.append(values.get("aria-label") or values.get("title") or "unlabelled video")

        if tag == "img" and (values.get("alt") or "").strip().lower() == "alt text":
            self.placeholder_alt.append(values.get("src") or "unknown image")


def local_target(page: Path, raw_url: str) -> Path | None:
    parsed = urlsplit(raw_url)
    if parsed.scheme.lower() in IGNORED_SCHEMES or parsed.scheme or parsed.netloc:
        return None
    if raw_url.startswith("#") or not parsed.path:
        return None

    decoded_path = unquote(parsed.path)
    if decoded_path.startswith("/"):
        return SITE_ROOT / decoded_path.lstrip("/")
    return page.parent / decoded_path


def target_exists(target: Path) -> bool:
    if target.is_file():
        return True
    if target.is_dir() and (target / "index.html").is_file():
        return True
    if not target.suffix:
        if target.with_suffix(".html").is_file():
            return True
        if (target / "index.html").is_file():
            return True
    return False


def main() -> int:
    if not SITE_ROOT.is_dir():
        print("site/ does not exist; run 'zensical build --clean' first.", file=sys.stderr)
        return 2

    failures: list[str] = []
    html_files = sorted(SITE_ROOT.rglob("*.html"))

    for page in html_files:
        parser = ReferenceParser()
        parser.feed(page.read_text(encoding="utf-8"))
        page_name = page.relative_to(SITE_ROOT)

        for tag, attribute, raw_url in parser.references:
            target = local_target(page, raw_url)
            if target is None:
                continue
            if target.suffix.lower() == ".mov":
                failures.append(f"{page_name}: {tag}[{attribute}] uses non-web-standard MOV: {raw_url}")
            if not target_exists(target):
                failures.append(f"{page_name}: broken {tag}[{attribute}] reference: {raw_url}")

        for label in parser.video_without_poster:
            failures.append(f"{page_name}: video has no poster image ({label})")
        for source in parser.placeholder_alt:
            failures.append(f"{page_name}: image still uses placeholder alt text ({source})")

    if failures:
        print(f"Built-site media audit failed with {len(failures)} issue(s):", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print(f"Built-site media audit passed across {len(html_files)} HTML pages.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
