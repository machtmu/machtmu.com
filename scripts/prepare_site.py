#!/usr/bin/env python3
"""Generate display-only media and fingerprint assets after `zensical build`.

Original images, videos, CSVs, PDFs and all download links remain untouched.
The generated site is disposable; .cache/media retains deterministic variants.
"""
from __future__ import annotations

import argparse
import hashlib
import html
from html.parser import HTMLParser
from pathlib import Path
import re
import shutil
from urllib.parse import unquote, urlsplit

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
VERSION = "display-v2"

# Content-fit cutoff (600px): the full logo and six tabs need about 583px
# including gutters, with a little extra room for active-link font widths.
# Keep the native theme's drawer, section
# navigation and JS viewport observer in step with our compact header row.
# Transform only disposable build assets; never edit installed theme sources.
NAVIGATION_MEDIA = {"76.25em": "37.5em", "76.234375em": "37.484375em"}
PORTRAIT_DISPLAY_QUALITY = 96


def portrait_encoding(native: bool):
    # Keep native master-sized copies exactly lossless. Only resized browser
    # copies use high-quality compression, never the retained source assets.
    return {'lossless': native, 'quality': 100 if native else PORTRAIT_DISPLAY_QUALITY}


def immediate_navigation_close(bundle: str):
    # Close the old drawer when navigation occurs, not 125ms afterwards: the
    # delayed theme cleanup otherwise closes a drawer the visitor just opened
    # on the new page. Match only this cleanup, leaving other debounce intact.
    pattern = r'(\.pipe\([\w$]+)\(125\)(\)\.subscribe\(\(\)=>\{[\w$]+\("drawer",!1\),[\w$]+\("search",!1\)\}\))'
    updated, count = re.subn(pattern, r'\g<1>(0)\g<2>', bundle)
    if count != 1:
        raise RuntimeError('Native post-navigation drawer cleanup not found')
    return updated


def navigation_assets(site: Path):
    assets = {}
    styles = sorted((site / "assets/stylesheets").glob("*/main.*.min.css"))
    bundles = sorted((site / "assets/javascripts").glob("bundle.*.min.js"))
    for paths in (styles, bundles):
        if not paths:
            raise RuntimeError("Native navigation assets missing; check theme build layout")
        for path in paths:
            original = path.read_text()
            updated = original
            for old, new in NAVIGATION_MEDIA.items():
                updated = updated.replace(old, new)
            if updated == original:
                raise RuntimeError(f"Native navigation breakpoint not found in {path.name}")
            if path.suffix == '.js':
                updated = immediate_navigation_close(updated)
            digest = hashlib.sha256(updated.encode()).hexdigest()[:12]
            target = path.with_name(f"{path.stem}.nav-{digest}{path.suffix}")
            target.write_text(updated)
            assets["/" + path.relative_to(site).as_posix()] = "/" + target.relative_to(site).as_posix()
    return assets


class Media:
    def __init__(self, site: Path, cache: Path):
        self.site, self.cache = site, cache
        self.memo = {}
        self.output = site / "assets/display"
        self.output.mkdir(parents=True, exist_ok=True)
        cache.mkdir(parents=True, exist_ok=True)

    def variants(self, raw: str, page: Path, logo=False, poster=False, portrait=False):
        parsed = urlsplit(raw)
        if parsed.scheme or parsed.netloc or not parsed.path:
            return None
        source = ((self.site / unquote(parsed.path).lstrip("/")) if parsed.path.startswith("/")
                  else (page.parent / unquote(parsed.path))).resolve()
        if not source.is_relative_to(self.site.resolve()) or not source.is_file():
            return None
        if source.is_relative_to(self.output.resolve()):
            return None
        if source.suffix.lower() not in (".jpg", ".jpeg", ".webp", ".png"):
            return None
        # PNG telemetry remains at full resolution, with the existing theme/viewer.
        if source.suffix.lower() == ".png" and not logo and not poster:
            return None
        if source.stat().st_size < 16000 and not logo:
            return None
        key = (source, logo, poster, portrait)
        if key in self.memo:
            return self.memo[key]
        digest = hashlib.sha256(source.read_bytes() + VERSION.encode() + (b'portrait-responsive-q96-v2' if portrait else b'')).hexdigest()[:16]
        with Image.open(source) as opened:
            if getattr(opened, "is_animated", False):
                return None
            original_width, original_height = opened.size
            if opened.getexif().get(274) in (5, 6, 7, 8):
                original_width, original_height = original_height, original_width
            image = None
            candidates = (320, 480, 640, 960, original_width) if portrait else ((480, 768, 1280) if logo else (480, 960, 1440))
            widths = sorted({min(original_width, w) for w in candidates})
            paths = []
            for width in widths:
                kind = ('-portrait-lossless' if width == original_width else '-portrait-q96') if portrait else ('-logo' if logo else '')
                name = f"{digest}-{width}{kind}.webp"
                cached = self.cache / name
                if not cached.exists():
                    if image is None:
                        image = ImageOps.exif_transpose(opened).convert("RGBA" if "A" in opened.getbands() or "transparency" in opened.info else "RGB")
                    height = max(1, round(original_height * width / original_width))
                    resized = image.resize((width, height), Image.Resampling.LANCZOS) if width != original_width else image
                    encoding = portrait_encoding(width == original_width) if portrait else {'quality': 86, 'lossless': logo}
                    resized.save(cached, "WEBP", **encoding, method=6, exact=True,
                                 icc_profile=opened.info.get("icc_profile", b""))
                target = self.output / name
                if not target.exists():
                    shutil.copyfile(cached, target)
                paths.append((width, "/assets/display/" + name))
        default = next((url for width, url in reversed(paths) if width <= 960), paths[0][1])
        result = (default, ", ".join(f"{url} {width}w" for width, url in paths), original_width, original_height)
        self.memo[key] = result
        return result


class Rewriter(HTMLParser):
    def __init__(self, page: Path, media: Media, assets: dict):
        super().__init__(convert_charrefs=False)
        self.page, self.media, self.assets = page, media, assets
        self.parts = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        original = self.get_starttag_text()
        changed = False
        if tag == "img" and values.get("src") and "data-plot-dark-src" not in values:
            logo = "/sponsors/" in values["src"] or values["src"].startswith("sponsors/")
            # Original opt-ins retain their native delivery unless a studio
            # portrait explicitly requests responsive display copies.
            # Even then, the unchanged native master remains data-original-src.
            portrait = "data-portrait-delivery" in values
            result = (self.media.variants(values["src"], self.page, portrait=True) if portrait
                      else None if "data-display-original" in values else self.media.variants(values["src"], self.page, logo=logo))
            if result:
                src, srcset, width, height = result
                values["data-original-src"] = values["src"]
                values.update(src=src, srcset=srcset, width=str(width), height=str(height))
                values["sizes"] = (values.get("sizes", "100vw") if portrait else
                                   "(max-width: 900px) 60vw, 250px" if logo
                                   else "(max-width: 760px) 92vw, (max-width: 1220px) 70vw, 960px")
                if not portrait and "/assets/images/leads/" in "/" + unquote(urlsplit(values["data-original-src"]).path).lstrip("./"):
                    values["sizes"] = "(max-width: 760px) 45vw, 300px"
                changed = True
        if tag == "video" and values.get("poster"):
            hero = "hero-bg" in values.get("class", "").split()
            if not hero:
                values["preload"] = "none"
                changed = True
            # The hero already has an optimized native-resolution WebP. Keep
            # its detail rather than replacing it with a 960px video thumbnail.
            result = None if hero else self.media.variants(values["poster"], self.page, poster=True)
            if result:
                values["poster"] = result[0]
                for name in ("data-light-poster", "data-dark-poster"):
                    if name in values:
                        values[name] = result[0]
                changed = True
            if "showcase-video" in values.get("class", ""):
                values.update(width="1920", height="1080")
                changed = True
        for name in ("src", "href"):
            raw = values.get(name)
            if not raw:
                continue
            parsed = urlsplit(raw)
            if parsed.scheme or parsed.netloc:
                continue
            source = ((self.media.site / parsed.path.lstrip("/")) if parsed.path.startswith("/")
                      else (self.page.parent / parsed.path)).resolve()
            if not source.is_relative_to(self.media.site):
                continue
            replacement = self.assets.get("/" + source.relative_to(self.media.site).as_posix())
            if replacement:
                values[name] = replacement
                changed = True
        if changed:
            self.parts.append("<" + tag + "".join(" " + key if value is None else f' {key}="{html.escape(value, quote=True)}"'
                                                for key, value in values.items()) + ">")
        else:
            self.parts.append(original)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.parts[-1] = self.parts[-1][:-1] + " />"

    def handle_endtag(self, tag): self.parts.append(f"</{tag}>")
    def handle_data(self, data): self.parts.append(data)
    def handle_entityref(self, name): self.parts.append(f"&{name};")
    def handle_charref(self, name): self.parts.append(f"&#{name};")
    def handle_comment(self, data): self.parts.append(f"<!--{data}-->")
    def handle_decl(self, decl): self.parts.append(f"<!{decl}>")
    def handle_pi(self, data): self.parts.append(f"<?{data}>")


def prepare(site: Path, cache: Path):
    assets = navigation_assets(site)
    for folder in ("css", "js"):
        for path in (site / folder).glob("*.*"):
            if re.search(r"\.[0-9a-f]{12}\.", path.name):
                continue
            digest = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
            target = path.with_name(f"{path.stem}.{digest}{path.suffix}")
            shutil.copyfile(path, target)
            relative = path.relative_to(site).as_posix()
            versioned = target.relative_to(site).as_posix()
            assets[relative] = versioned
            assets["/" + relative] = "/" + versioned
    media = Media(site, cache)
    for page in site.rglob("*.html"):
        rewriter = Rewriter(page, media, assets)
        rewriter.feed(page.read_text())
        rewriter.close()
        page.write_text("".join(rewriter.parts))
    print(f"Prepared {len(media.memo)} display images; original files and download links retained.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=ROOT / "site")
    parser.add_argument("--cache", type=Path, default=ROOT / ".cache/media")
    args = parser.parse_args()
    prepare(args.site.resolve(), args.cache.resolve())
