"""Keep display-cache lifecycle independent of clean builds/late test failures."""
from pathlib import Path
import unittest

import yaml


class DocumentationWorkflowTests(unittest.TestCase):
    def test_validated_display_cache_lifecycle(self):
        workflow = yaml.safe_load((Path(__file__).resolve().parents[1] /
                                   '.github/workflows/docs.yml').read_text())
        steps = workflow['jobs']['deploy']['steps']

        def index(key, value):
            return next(i for i, step in enumerate(steps) if step.get(key) == value)

        build = index('run', 'zensical build --clean')
        restore = index('uses', 'actions/cache/restore@v4')
        prepare = index('run', 'python scripts/prepare_site.py')
        media = index('run', 'python scripts/check_site_media.py')
        seo = index('run', 'python scripts/check_site_seo.py')
        save = index('uses', 'actions/cache/save@v4')
        browser = index('name', 'Check browser interactions and accessibility')
        lighthouse = index('name', 'Run key-page Lighthouse checks')
        self.assertEqual(sorted((build, restore, prepare, media, seo, save, browser, lighthouse)),
                         [build, restore, prepare, media, seo, save, browser, lighthouse])
        self.assertEqual(steps[restore]['with']['path'], '.cache/media')
        self.assertEqual(steps[save]['with']['path'], '.cache/media')
        self.assertEqual(steps[save]['with']['key'],
                         '${{ steps.display-cache.outputs.cache-primary-key }}')
        self.assertEqual(steps[save]['if'], "steps.display-cache.outputs.cache-hit != 'true'")


if __name__ == '__main__':
    unittest.main()
