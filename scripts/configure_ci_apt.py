#!/usr/bin/env python3
"""Use official HTTPS Ubuntu archives on disposable GitHub-hosted runners.

The runner's HTTP Azure mirror has stalled browser dependency installation.
Only Ubuntu archive URLs are changed; signing keys and third-party repos stay
untouched. This is not a workstation setup script.
"""
from __future__ import annotations

import os
from pathlib import Path
import re


APT_LIMITS = '''Acquire::http::Timeout "20";
Acquire::https::Timeout "20";
Acquire::Retries "2";
Acquire::Languages "none";
'''


def official_https_sources(text: str) -> str:
    text = re.sub(
        r'mirror\+file:/etc/apt/apt-mirrors\.txt/?(?=\s|$)',
        'https://archive.ubuntu.com/ubuntu/', text)
    return re.sub(
        r'https?://(azure\.archive|archive|security)\.ubuntu\.com/ubuntu/?(?=\s|$)',
        lambda match: ('https://security.ubuntu.com/ubuntu/'
                       if match.group(1) == 'security'
                       else 'https://archive.ubuntu.com/ubuntu/'), text)


def configure(apt: Path) -> int:
    changed = 0
    for relative in ('sources.list.d/ubuntu.sources', 'sources.list', 'apt-mirrors.txt'):
        path = apt / relative
        if not path.is_file():
            continue
        original = path.read_text()
        updated = official_https_sources(original)
        if updated != original:
            path.write_text(updated)
            changed += 1
    (apt / 'apt.conf.d/99-mach-ci-network').write_text(APT_LIMITS)
    return changed


if __name__ == '__main__':
    if os.environ.get('GITHUB_ACTIONS') != 'true' or os.environ.get('RUNNER_ENVIRONMENT') != 'github-hosted':
        raise SystemExit('Refusing to change APT outside a disposable GitHub-hosted runner')
    print(f'Configured official HTTPS Ubuntu archives ({configure(Path("/etc/apt"))} source files updated) and bounded network retries.')
