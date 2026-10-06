#!/usr/bin/env python3
"""Encode approved native studio portraits for exact, lossless web delivery."""
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
PORTRAITS = ROOT / 'docs/assets/images/leads'


def build():
    before = after = 0
    for source in sorted(PORTRAITS.glob('*-studio.png')):
        destination = source.with_suffix('.webp')
        with Image.open(source) as image:
            original = image.convert('RGBA')
            original.save(destination, 'WEBP', lossless=True, quality=100,
                          method=6, exact=True)
            with Image.open(destination) as delivery:
                assert delivery.size == original.size
                assert delivery.convert('RGBA').tobytes() == original.tobytes()
        before += source.stat().st_size
        after += destination.stat().st_size
        print(f'{destination.name}: {destination.stat().st_size:,} bytes; '
              'native resolution and decoded RGBA unchanged.', flush=True)
    print(f'Portrait delivery: {before:,} -> {after:,} bytes '
          f'({100 * (1 - after / before):.1f}% smaller).', flush=True)


if __name__ == '__main__':
    build()
