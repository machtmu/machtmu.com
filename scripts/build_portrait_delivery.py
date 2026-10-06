#!/usr/bin/env python3
"""Encode approved native studio portraits for exact, lossless web delivery."""
import argparse
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
PORTRAITS = ROOT / 'docs/assets/images/leads'


def build(source=None, destination=None):
    before = after = 0
    sources = [source] if source else sorted(PORTRAITS.glob('*-studio.png'))
    for source in sources:
        target = destination or source.with_suffix('.webp')
        with Image.open(source) as image:
            original = image.convert('RGBA')
            original.save(target, 'WEBP', lossless=True, quality=100,
                          method=6, exact=True)
            with Image.open(target) as delivery:
                assert delivery.size == original.size
                assert delivery.convert('RGBA').tobytes() == original.tobytes()
        before += source.stat().st_size
        after += target.stat().st_size
        print(f'{target.name}: {target.stat().st_size:,} bytes; '
              'native resolution and decoded RGBA unchanged.', flush=True)
    print(f'Portrait delivery: {before:,} -> {after:,} bytes '
          f'({100 * (1 - after / before):.1f}% smaller).', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path,
                        help='An approved, retained PNG master outside the published docs.')
    parser.add_argument('--destination', type=Path,
                        help='A new native lossless WebP delivery file; requires --source.')
    args = parser.parse_args()
    if bool(args.source) != bool(args.destination):
        parser.error('--source and --destination must be supplied together')
    if args.destination and args.destination.exists():
        parser.error('Explicit destinations must be new versioned files')
    build(args.source, args.destination)
