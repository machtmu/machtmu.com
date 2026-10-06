#!/usr/bin/env python3
"""Create approved web crops from the untouched full-resolution film scans.

Run after placing the original at the path below. Uses ImageMagick for the
normal website asset pipeline, without upscaling, sharpening or retouching.
"""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'docs/Seraphina/aug-20-hotfire'
PHOTOS = [
    ('team-at-test-stand-full.jpg', 'seraphina-relight-team.webp', 157, 630, 640),
    ('team-celebration-full.jpg', 'seraphina-relight-celebration.webp', 145, 545, 704),
]


def build_photo(source_name, output_name, source_x, source_y, source_width):
    source = FOLDER / 'team-photos' / source_name
    output = FOLDER / output_name
    width, height = map(int, subprocess.check_output([
        'identify', '-format', '%w %h', str(source),
    ], text=True).split())
    # Coordinates use the old 982 x 1280 upload scale. The standing frame
    # centers the group rather than the test stand, without cutting off faces.
    x, y = round(width * source_x / 982), round(height * source_y / 1280)
    crop_width = round(width * source_width / 982)
    crop_height = round(crop_width * 9 / 16)
    subprocess.run([
        'magick', str(source), '-auto-orient', '-crop',
        f'{crop_width}x{crop_height}+{x}+{y}', '+repage',
        '-quality', '94', '-define', 'webp:method=6', str(output),
    ], check=True)
    print(f'{output_name}: {crop_width} x {crop_height}, {output.stat().st_size:,} bytes; original untouched.')


def build_mobile_intro_photo():
    """Keep the full group, with genuine ground beneath the mobile overlay."""
    source = FOLDER / 'team-photos' / 'team-at-test-stand-full.jpg'
    output = FOLDER / 'seraphina-relight-team-portrait.webp'
    width, height = map(int, subprocess.check_output([
        'identify', '-format', '%w %h', str(source),
    ], text=True).split())
    # Same horizontally centered group as the landscape frame. Include the
    # source scan's real grass below them, not generated or repeated imagery.
    x, y = round(width * 157 / 982), round(height * 433 / 1280)
    crop_width, crop_height = round(width * 640 / 982), round(height * 840 / 1280)
    assert x + crop_width <= width and y + crop_height <= height
    assert crop_width >= 1200
    subprocess.run([
        'magick', str(source), '-auto-orient', '-crop',
        f'{crop_width}x{crop_height}+{x}+{y}', '+repage', '-resize', '1200x',
        '-quality', '94', '-define', 'webp:method=6', str(output),
    ], check=True)
    print(f'{output.name}: native portrait crop, 1200 px wide, {output.stat().st_size:,} bytes; original untouched.')


def build_tighter_intro_photos():
    """Intro-only crops center the people without changing shared card photos."""
    source = FOLDER / 'team-photos' / 'team-at-test-stand-full.jpg'
    width, height = map(int, subprocess.check_output([
        'identify', '-format', '%w %h', str(source),
    ], text=True).split())
    assert (width, height) == (3859, 5028), 'Review framing if the source scan changes.'
    for name, x, y, crop_width, crop_height, display_width in (
        ('seraphina-relight-team-intro.webp', 807, 2650, 2140, 1204, 2140),
        ('seraphina-relight-team-intro-portrait.webp', 807, 1900, 2140, 3100, 1200),
    ):
        assert x + crop_width <= width and y + crop_height <= height
        assert display_width <= crop_width
        output = FOLDER / name
        subprocess.run([
            'magick', str(source), '-auto-orient', '-crop',
            f'{crop_width}x{crop_height}+{x}+{y}', '+repage',
            '-resize', f'{display_width}x', '-quality', '94',
            '-define', 'webp:method=6', str(output),
        ], check=True)
        print(f'{name}: tighter native group crop, {output.stat().st_size:,} bytes; shared photos untouched.')


if __name__ == '__main__':
    for photo in PHOTOS:
        build_photo(*photo)
    build_mobile_intro_photo()
    build_tighter_intro_photos()
