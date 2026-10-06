#!/usr/bin/env python3
"""Build efficient high-resolution hero artwork and matching HDR masks.

Downsample the genuine 7349px source once to 2048px for the 420 CSS-pixel hero.
That preserves ample resolution at DPR 3/4 without decoding three oversized
textures on phones. Keep alpha, neutral lettering and the red accent faithful,
with no tracing, upscaling, sharpening or retouching. Small navigation-logo
assets and the original logo remain untouched.
"""
from pathlib import Path

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
IMG = ROOT / 'docs/img'
DISPLAY_WIDTH = 2048


def build():
    original = Image.open(IMG / 'logo1-dark.png').convert('RGBA')
    size = (DISPLAY_WIDTH, round(original.height * DISPLAY_WIDTH / original.width))
    assert DISPLAY_WIDTH <= original.width
    logo = original.resize(size, Image.Resampling.LANCZOS)
    display = IMG / 'logo-hero-dark.png'
    logo.save(display, optimize=True, compress_level=9)
    print(f'{display.name}: {logo.width} x {logo.height}; {display.stat().st_size:,} bytes; source downsampled once.')
    # Format-only delivery optimization: retain every decoded RGBA pixel,
    # including transparent RGB, at the same native resolution and geometry.
    delivery = IMG / 'logo-hero-dark.webp'
    logo.save(delivery, 'WEBP', lossless=True, quality=100, method=6, exact=True)
    with Image.open(delivery) as decoded:
        assert decoded.convert('RGBA').tobytes() == logo.tobytes()
    print(f'{delivery.name}: {delivery.stat().st_size:,} bytes; pixel-identical lossless delivery.')
    red, green, blue, alpha = logo.split()
    colour_difference = ImageChops.lighter(
        ImageChops.difference(red, green), ImageChops.difference(red, blue),
    )
    neutral = colour_difference.point(lambda value: 255 if value == 0 else 0)
    white_alpha = ImageChops.multiply(alpha, neutral)
    red_alpha = ImageChops.multiply(alpha, ImageChops.invert(neutral))
    assert ImageChops.difference(ImageChops.add(white_alpha, red_alpha), alpha).getbbox() is None
    for name, channel in (
        ('logo-hero-hdr-mask.png', white_alpha),
        ('logo-hero-hdr-accent-mask.png', red_alpha),
    ):
        output = IMG / name
        mask = Image.merge('LA', (Image.new('L', logo.size, 255), channel))
        mask.save(output, optimize=True, compress_level=9)
        print(f'{name}: {logo.width} x {logo.height}; {output.stat().st_size:,} bytes; matching display alpha retained.')


if __name__ == '__main__':
    build()
