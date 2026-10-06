#!/usr/bin/env python3
"""Create Aqua's Safari-safe dark wordmark without changing its symbol."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LETTERING = {"#274978": "#a7cdff", "#505050": "#bdbdbd"}


def dark_artwork(original):
    # These are the opaque colors produced by the previous filter in Chromium.
    # Explicit fills also work in WebKit's external SVG image renderer.
    for source, target in LETTERING.items():
        old = f"fill:{source};"
        assert original.count(old) == 1, f"Unexpected Aqua artwork: {source}"
        original = original.replace(old, f"fill:{target};")
    return original


if __name__ == "__main__":
    source = ROOT / "docs/sponsors/aqua-environment-logo.svg"
    target = source.with_name("aqua-environment-logo-dark-v2.svg")
    target.write_text(dark_artwork(source.read_text()))
    print(f"Prepared {target.name}: original symbol and paths preserved")
