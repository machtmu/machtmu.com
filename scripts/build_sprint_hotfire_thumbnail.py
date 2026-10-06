#!/usr/bin/env python3
"""Extract the requested 00:02 source frame without changing the SPRINT video."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'docs/SPRINT/sept-13-hotfire'


def build():
    source = FOLDER / 'sept-14-hotfire.mp4'
    output = FOLDER / 'sept-14-hotfire-2s.webp'
    subprocess.run([
        'ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', str(source),
        '-ss', '00:00:02.000', '-frames:v', '1', '-an', '-c:v', 'libwebp',
        '-quality', '94', '-compression_level', '6', '-y', str(output),
    ], check=True)
    print(f'{output.name}: requested 00:02 source frame; {output.stat().st_size:,} bytes; video untouched.')


if __name__ == '__main__':
    build()
