from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest

from configure_ci_apt import APT_LIMITS, configure, official_https_sources


class ConfigureCiAptTests(unittest.TestCase):
    def test_cli_refuses_non_hosted_environment_before_any_write(self):
        for changes in ({'GITHUB_ACTIONS': '', 'RUNNER_ENVIRONMENT': ''},
                        {'GITHUB_ACTIONS': 'true', 'RUNNER_ENVIRONMENT': 'self-hosted'}):
            result = subprocess.run(
                [sys.executable, str(Path(__file__).with_name('configure_ci_apt.py'))],
                env={**os.environ, **changes}, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Refusing to change APT', result.stderr)

    def test_runner_mirror_and_direct_sources(self):
        for source in ('mirror+file:/etc/apt/apt-mirrors.txt',
                       'http://azure.archive.ubuntu.com/ubuntu/',
                       'http://archive.ubuntu.com/ubuntu'):
            self.assertEqual(official_https_sources(f'URIs: {source}\n'),
                             'URIs: https://archive.ubuntu.com/ubuntu/\n')
        self.assertEqual(official_https_sources('http://security.ubuntu.com/ubuntu\n'),
                         'https://security.ubuntu.com/ubuntu/\n')

    def test_unrelated_urls_keys_and_security_are_unchanged(self):
        original = ('Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg\n'
                    'URIs: https://packages.microsoft.com/ubuntu/24.04/prod\n'
                    'http://azure.archive.ubuntu.com/ubuntu-spoof\n'
                    'http://archive.ubuntu.com.invalid/ubuntu/\n')
        self.assertEqual(official_https_sources(original), original)
        self.assertNotIn('Verify-Peer', APT_LIMITS)
        self.assertNotIn('AllowUnauthenticated', APT_LIMITS)

    def test_scoped_changes_and_idempotence(self):
        with tempfile.TemporaryDirectory() as directory:
            apt = Path(directory)
            (apt / 'sources.list.d').mkdir()
            (apt / 'apt.conf.d').mkdir()
            ubuntu = apt / 'sources.list.d/ubuntu.sources'
            ubuntu.write_text('URIs: mirror+file:/etc/apt/apt-mirrors.txt\nSuites: noble noble-updates\n')
            other = apt / 'sources.list.d/other.list'
            other.write_text('deb http://third-party.test/ubuntu noble main\n')
            self.assertEqual(configure(apt), 1)
            self.assertEqual(configure(apt), 0)
            self.assertIn('Suites: noble noble-updates', ubuntu.read_text())
            self.assertEqual(other.read_text(), 'deb http://third-party.test/ubuntu noble main\n')
            self.assertEqual((apt / 'apt.conf.d/99-mach-ci-network').read_text(), APT_LIMITS)


if __name__ == '__main__':
    unittest.main()
