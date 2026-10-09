#!/usr/bin/env python3
"""Create a full-frame enclosure photo, retaining the untouched Mac original.

The source is archived privately at research/source-media/electronics/IMG_2916.jpg.
No crop, upscaling, retouching or changes to the previous overview.webp are made.
The normal prepare_site.py pipeline supplies responsive browser-sized copies.
"""
import argparse
import hashlib
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
SOURCE_SHA256 = "f98e75a2d845b3d1db02aa7259582a0f6ad86598d962cc049102de3bc3d11dca"
OUTPUT = ROOT / "docs/SPRINT/electronics/enclosure-img-2916.webp"


def build(source: Path):
    if hashlib.sha256(source.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError("Expected the unchanged IMG_2916.jpg source photograph")
    with Image.open(source) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGB")
        image.save(OUTPUT, "WEBP", quality=94, method=6,
                   icc_profile=opened.info.get("icc_profile", b""))
    print(f"{OUTPUT.name}: full-frame {image.width}x{image.height}, {OUTPUT.stat().st_size:,} bytes")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, nargs="?",
                        default=ROOT / "research/source-media/electronics/IMG_2916.jpg")
    build(parser.parse_args().source)
