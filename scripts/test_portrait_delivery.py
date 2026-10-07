"""Keep format-only portrait delivery faithful to the retained native PNGs."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest

from PIL import Image


class PortraitDeliveryTests(unittest.TestCase):
    def test_explicit_encoder_requires_new_paired_paths(self):
        helper = Path(__file__).with_name('build_portrait_delivery.py')
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'approved.png'
            delivery = Path(folder) / 'new-studio.webp'
            Image.new('RGB', (8, 12), '#b7b7b7').save(source)
            incomplete = subprocess.run([sys.executable, str(helper), '--source', str(source)], capture_output=True)
            self.assertNotEqual(incomplete.returncode, 0)
            encoded = subprocess.run([sys.executable, str(helper), '--source', str(source), '--destination', str(delivery)], capture_output=True)
            self.assertEqual(encoded.returncode, 0, encoded.stderr.decode())
            previous = delivery.read_bytes()
            overwrite = subprocess.run([sys.executable, str(helper), '--source', str(source), '--destination', str(delivery)], capture_output=True)
            self.assertNotEqual(overwrite.returncode, 0)
            self.assertEqual(delivery.read_bytes(), previous)
            with Image.open(source) as original, Image.open(delivery) as output:
                self.assertEqual(original.convert('RGBA').tobytes(), output.convert('RGBA').tobytes())

    def test_jonathan_lighting_edition_provenance_and_native_delivery(self):
        root = Path(__file__).resolve().parents[1]
        directory = root / 'docs/assets/images/leads'
        manifest = json.loads((directory / 'portrait-studio-manifest.json').read_text())
        portrait = next(p for p in manifest['portraits'] if p['name'] == 'Jonathan Al-Hinn')
        edition = next(e for e in portrait['editions'] if e['id'] == portrait['active_edition'])
        self.assertEqual(portrait['active_edition'], 'lighting-v3')
        self.assertEqual({e['id'] for e in portrait['editions']}, {'lighting-v2', 'lighting-v3'})
        self.assertTrue(edition['no_previous_jonathan_edit_as_input'])
        self.assertEqual(list(edition['reference_roles']), ['Julia-Operations-Director-studio.webp'])
        self.assertEqual(hashlib.sha256((directory / 'Julia-Operations-Director-studio.webp').read_bytes()).hexdigest(),
                         edition['reference_sha256']['Julia-Operations-Director-studio.webp'])
        self.assertTrue(edition['direct_original_edit'])
        self.assertFalse(edition['output_master_published'])
        self.assertEqual(edition['mode'], 'built-in image_gen')
        self.assertEqual(edition['source'], portrait['original'])
        self.assertEqual(edition['source_sha256'], portrait['original_sha256'])
        for filename, expected in ((edition['source'], edition['source_sha256']),
                                   (edition['delivery'], edition['delivery_sha256'])):
            self.assertEqual(hashlib.sha256((directory / filename).read_bytes()).hexdigest(), expected)
        with Image.open(directory / edition['delivery']) as delivery:
            self.assertEqual(list(delivery.size), edition['dimensions'])
            self.assertEqual(list(delivery.size), portrait['dimensions'])
        # The retained edit master is intentionally outside published docs;
        # CI verifies the production checksum without assuming private archives.
        self.assertNotEqual(edition['delivery'], portrait['delivery'])
        self.assertTrue((directory / portrait['output']).is_file())
        self.assertTrue((directory / portrait['delivery']).is_file())
        self.assertIn('Image 1', edition['prompt'])
        retained = edition['cached_html_compatibility']
        self.assertEqual(len(retained['files']), 5)
        self.assertEqual(sum((root / 'docs/assets/display' / name).stat().st_size for name in retained['files']), retained['total_bytes'])
        for filename, expected in retained['files'].items():
            self.assertEqual(hashlib.sha256((root / 'docs/assets/display' / filename).read_bytes()).hexdigest(), expected)
        # A new active edition must not discard the prior native master or
        # the previously retained URLs needed by older in-flight team HTML.
        prior = next(e for e in portrait['editions'] if e['id'] == 'lighting-v2')
        self.assertEqual(hashlib.sha256((directory / prior['delivery']).read_bytes()).hexdigest(), prior['delivery_sha256'])
        for filename, expected in prior['cached_html_compatibility']['files'].items():
            self.assertEqual(hashlib.sha256((root / 'docs/assets/display' / filename).read_bytes()).hexdigest(), expected)

    def test_all_six_deliveries_preserve_native_pixels(self):
        directory = Path(__file__).resolve().parents[1] / 'docs/assets/images/leads'
        originals = sorted(directory.glob('*-studio.png'))
        self.assertEqual(len(originals), 6)
        original_bytes = delivery_bytes = 0
        for source in originals:
            delivery = source.with_suffix('.webp')
            with self.subTest(portrait=source.name):
                with Image.open(source) as original, Image.open(delivery) as encoded:
                    self.assertEqual(encoded.size, original.size)
                    self.assertEqual(encoded.convert('RGBA').tobytes(),
                                     original.convert('RGBA').tobytes())
                self.assertLess(delivery.stat().st_size, source.stat().st_size)
            original_bytes += source.stat().st_size
            delivery_bytes += delivery.stat().st_size
        self.assertLess(delivery_bytes, original_bytes * 0.75)


if __name__ == '__main__':
    unittest.main()
