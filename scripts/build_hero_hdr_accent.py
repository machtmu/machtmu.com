#!/usr/bin/env python3
"""Build a colour-preserving hero accent from the existing logo and HDR tile.

The SVG follows the original red pixels, including their edge opacity. The
JPEG reuses the working tile's ISO gain map and ICC profile, changing only its
SDR base colour and updating the MPF image offsets. Requires Pillow/ImageMagick.
"""
from collections import defaultdict
from io import BytesIO
from pathlib import Path
import struct
import subprocess

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
IMG = ROOT / 'docs/img'


def build():
    logo = Image.open(IMG / 'logo-header-dark.png').convert('RGBA')
    paths = defaultdict(list)
    for y in range(logo.height):
        x = 0
        while x < logo.width:
            r, g, b, alpha = logo.getpixel((x, y))
            if not alpha or r <= 1.5 * max(g, b):
                x += 1
                continue
            start = x
            x += 1
            while x < logo.width:
                rr, gg, bb, aa = logo.getpixel((x, y))
                if aa != alpha or rr <= 1.5 * max(gg, bb):
                    break
                x += 1
            paths[alpha].append(f'M{start} {y}h{x-start}v1h{start-x}z')
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {logo.width} {logo.height}">']
    for alpha, parts in sorted(paths.items()):
        svg.append(f'<path fill="white" opacity="{alpha / 255:.6f}" d="{"".join(parts)}"/>')
    svg.append('</svg>')
    (IMG / 'logo-hero-hdr-accent-mask.svg').write_text('\n'.join(svg) + '\n')

    source = (IMG / 'white-7.5x.jpg').read_bytes()
    source_image = Image.open(BytesIO(source))
    primary_size = source_image._getmp()[0xB002][0]['Size']
    gainmap = source[primary_size:]
    # Reuse the known-good ICC, ISO reference, and MPF segments verbatim.
    segments = []
    offset = 2
    while source[offset:offset + 2] != b'\xff\xda':
        assert source[offset] == 0xFF
        length = struct.unpack_from('>H', source, offset + 2)[0]
        if source[offset + 1] == 0xE2:
            segments.append(source[offset:offset + 2 + length])
        offset += 2 + length
    assert len(segments) == 3
    base = subprocess.check_output([
        'magick', '-size', '64x64', 'xc:rgb(217,26,33)',
        '-sampling-factor', '4:4:4', '-quality', '100', 'jpeg:-',
    ])
    primary = bytearray(b'\xff\xd8' + b''.join(segments) + base[2:])
    tiff_start = primary.index(b'MPF\0') + 4
    ifd = tiff_start + struct.unpack_from('>I', primary, tiff_start + 4)[0]
    count = struct.unpack_from('>H', primary, ifd)[0]
    for i in range(count):
        entry = ifd + 2 + i * 12
        if struct.unpack_from('>H', primary, entry)[0] == 0xB002:
            images = tiff_start + struct.unpack_from('>I', primary, entry + 8)[0]
            struct.pack_into('>I', primary, images + 4, len(primary))
            struct.pack_into('>II', primary, images + 20, len(gainmap), len(primary) - tiff_start)
            break
    else:
        raise ValueError('Missing MPF image entries')
    output = bytes(primary) + gainmap
    check = Image.open(BytesIO(output))
    entries = check._getmp()[0xB002]
    assert entries[0]['Size'] == len(primary)
    assert entries[1]['DataOffset'] + tiff_start == len(primary)
    assert check.info['icc_profile'] == source_image.info['icc_profile']
    assert all(abs(a - b) <= 1 for a, b in zip(check.getpixel((32, 32)), (217, 26, 33)))
    check.seek(1)
    assert check.size == (64, 64)
    assert output[len(primary):] == gainmap
    (IMG / 'red-7.5x.jpg').write_bytes(output)
    print(f'Built original-shape red mask and {len(output)}-byte HDR colour tile.')


if __name__ == '__main__':
    build()
