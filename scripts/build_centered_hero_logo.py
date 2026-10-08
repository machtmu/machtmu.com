"""Pad the native hero artwork and HDR layers without changing their pixels."""
import base64
from pathlib import Path

IMAGES = Path(__file__).resolve().parents[1] / 'docs/img'
# The MACH letters span x=0..1625; the orbit extends to x=2048.
# Extra space at the left puts the lettering at the canvas midpoint.
VIEWBOX = '-423 0 2471 636'


def build():
    for source, target, media_type in (
        ('logo-hero-dark.webp', 'logo-hero-word-centered.svg', 'image/webp'),
        ('logo-hero-hdr-mask.png', 'logo-hero-word-centered-hdr-mask.svg', 'image/png'),
        ('logo-hero-hdr-accent-mask.png', 'logo-hero-word-centered-hdr-accent-mask.svg', 'image/png'),
    ):
        encoded = base64.b64encode((IMAGES / source).read_bytes()).decode('ascii')
        (IMAGES / target).write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" width="2471" height="636" viewBox="{VIEWBOX}">'
            f'<image width="2048" height="636" href="data:{media_type};base64,{encoded}"/></svg>\n'
        )


if __name__ == '__main__':
    build()
