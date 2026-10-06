#!/usr/bin/env python3
"""Build hero-only speed-ramped derivatives, leaving the full relight untouched."""
from pathlib import Path
import hashlib
import math
import subprocess
from array import array

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'docs/Seraphina/aug-20-hotfire/seraphina-double-hotfire.mp4'
OUTPUT = ROOT / 'docs/assets/videos'

# Source-video seconds, checked against the source audio and footage.
# The first engine-noise interval lasts ~0.95-5.2s, with tail-off to ~6.8s.
# Relight noise begins ~14.85s. Protect both intervals with normal-speed margins.
# The visible orange flare is not the entire firing, so do not time burns by it.
WAIT_START = 7.0
WAIT_END = 14.7
WAIT_DURATION = 1.5
RAMP_SOURCE_SECONDS = 0.45


def wait_time(source_seconds):
    """Continuous time map with 1x speed at either edge and faster motion inside."""
    span = WAIT_END - WAIT_START
    tau = RAMP_SOURCE_SECONDS
    edge = math.exp(-span / tau)
    ramp_area = 2 * tau * (1 - edge) / (1 + edge)
    slope = (WAIT_DURATION - ramp_area) / (span - ramp_area)
    ease = (1 - slope) / (1 + edge)
    return (slope * source_seconds + ease * tau *
            (1 - math.exp(-source_seconds / tau) +
             math.exp(-(span - source_seconds) / tau) - edge))


def filters(width):
    span = WAIT_END - WAIT_START
    tau = RAMP_SOURCE_SECONDS
    edge = math.exp(-span / tau)
    ramp_area = 2 * tau * (1 - edge) / (1 + edge)
    slope = (WAIT_DURATION - ramp_area) / (span - ramp_area)
    ease = (1 - slope) / (1 + edge)
    clock = (f'({slope:.12f}*T+{ease*tau:.12f}*'
             f'(1-exp(-T/{tau})+exp(-({span}-T)/{tau})-{edge:.12f}))/TB')
    return (
        '[0:v]split=3[first][wait][second];'
        f'[first]trim=end={WAIT_START},setpts=PTS-STARTPTS[a];'
        f'[wait]trim=start={WAIT_START}:end={WAIT_END},'
        f'setpts=PTS-STARTPTS,setpts={clock}[b];'
        f'[second]trim=start={WAIT_END},setpts=PTS-STARTPTS[c];'
        '[a][b][c]concat=n=3:v=1:a=0,'
        f'crop=1920:1036:0:0,scale={width}:-2,fps=30[out]'
    )


def check_quiet_audio():
    """Reject a wait window containing sustained engine-volume source audio."""
    raw = subprocess.check_output([
        'ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', str(SOURCE),
        '-vn', '-ac', '1', '-ar', '16000', '-f', 'f32le', 'pipe:1',
    ])
    samples = array('f')
    samples.frombytes(raw)
    window = 1600  # 100 ms at 16 kHz; tests use the original audio, not a muted edit.
    start = round(WAIT_START * 16000)
    stop = round(WAIT_END * 16000)
    assert len(samples) >= stop, 'Source audio does not cover the ramp interval'
    peak = max(
        20 * math.log10(math.sqrt(sum(value * value for value in samples[i:i+window]) / window) + 1e-10)
        for i in range(start, stop - window + 1, window)
    )
    # Firing windows are roughly -10 to -20 dBFS; this selected quiet gap is below -35.
    assert peak < -30, f'Ramp intersects loud source audio ({peak:.1f} dBFS)'
    print(f'Original audio checked: ramp window {WAIT_START}-{WAIT_END}s, peak {peak:.1f} dBFS.', flush=True)


def main():
    source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    check_quiet_audio()
    assert abs(wait_time(0)) < 1e-9
    assert abs(wait_time(WAIT_END - WAIT_START) - WAIT_DURATION) < 1e-9
    for name, width, quality in (
        ('seraphina-august-relight-hero.mp4', 1280, 24),
        ('seraphina-august-relight-hero-mobile.mp4', 960, 25),
    ):
        subprocess.run([
            'ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(SOURCE),
            '-filter_complex', filters(width), '-map', '[out]', '-an',
            '-c:v', 'libx264', '-preset', 'fast', '-crf', str(quality),
            '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(OUTPUT / name),
        ], check=True)
        print(f'{name}: both firings retained; wait ramped to {WAIT_DURATION}s', flush=True)
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == source_hash
    print('Original relight video unchanged.', flush=True)


if __name__ == '__main__':
    main()
