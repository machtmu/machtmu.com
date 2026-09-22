#!/usr/bin/env python3
"""Check public landing-page metadata in a fresh Zensical build."""

import json
from html.parser import HTMLParser
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1] / "site"
BASE = "https://machtmu.com/"


class Page(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.meta = {}
        self.canonicals = []
        self.titles = []
        self.structured = []
        self.capture = None
        self.buffer = ""
        self.feed(path.read_text())

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta":
            key = attrs.get("name", attrs.get("property"))
            self.meta.setdefault(key, []).append(attrs.get("content", ""))
        if tag == "link" and attrs.get("rel") == "canonical":
            self.canonicals.append(attrs["href"])
        if tag == "title" or (tag == "script" and attrs.get("type") == "application/ld+json"):
            self.capture, self.buffer = tag, ""

    def handle_data(self, data):
        if self.capture:
            self.buffer += data

    def handle_endtag(self, tag):
        if tag == self.capture:
            if tag == "title":
                self.titles.append(self.buffer.strip())
            else:
                self.structured.append(json.loads(self.buffer))
            self.capture = None


def main():
    sitemap = ET.parse(ROOT / "sitemap.xml")
    urls = {e.text for e in sitemap.findall(".//{*}loc")}
    titles, descriptions = set(), set()
    for route in ("", "team/", "resources/", "SPRINT/", "Seraphina/"):
        page = Page(ROOT / route / "index.html")
        assert len(page.titles) == 1, route
        title = page.titles[0]
        assert title not in titles and "MACH" in title, route
        titles.add(title)
        assert len(page.meta["description"]) == 1, route
        description = page.meta["description"][0]
        assert description not in descriptions and "Toronto Metropolitan University" in description, route
        descriptions.add(description)
        assert page.meta["og:title"] == page.meta["twitter:title"] == [title], route
        assert page.meta["og:description"] == page.meta["twitter:description"] == [description], route
        assert page.canonicals == [BASE + route], route
        assert BASE + route in urls, route
        assert "noindex" not in ",".join(page.meta.get("robots", [])), route
        if not route:
            assert "Toronto Rocketry" in title
            graph = page.structured[0]["@graph"]
            org = next(node for node in graph if node["@type"] == "Organization")
            assert "Toronto Rocketry" not in org["alternateName"]
            assert "Metropolitan Aerospace & Combustion Hub" in org["alternateName"]
            assert org["description"] == description
            assert org["location"]["address"]["addressLocality"] == "Toronto"
    assert "Sitemap: " + BASE + "sitemap.xml" in (ROOT / "robots.txt").read_text()
    print("SEO checks passed: unique titles/descriptions, social metadata, canonicals, schema and sitemap.")


if __name__ == "__main__":
    main()
