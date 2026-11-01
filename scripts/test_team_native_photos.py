"""Former web masters match their chosen source; originals remain recoverable."""
import hashlib
import re
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
import build_member_avatars as portraits


class NativeFormerPhotoTests(unittest.TestCase):
    def test_user_evan_source_is_uncropped_and_css_matches_reviewed_roi(self):
        entry = next(p for p in portraits.NATIVE_AVATARS if p['name'] == 'Evan Bhogal')
        self.assertEqual(entry['source_dimensions'], [1440, 1920])
        self.assertEqual(entry['frame'], 'evan-attachment')
        css = (portraits.ROOT / 'docs/css/team-portraits.css').read_text()
        block = re.search(r'\.former-member-avatar-frame--evan-attachment\s*\{([^}]+)', css)[1]
        values = {key: float(value) / 100 for key, value in
                  re.findall(r'--avatar-([\w-]+):\s*([\d.]+)%;', block)}
        width = values['width']
        height = width * 1920 / 1440
        self.assertAlmostEqual(0.5 - values['center'] * width, -490 / 620, places=7)
        self.assertAlmostEqual(values['eye-line'] - values['eye'] * height, -450 / 620, places=7)
        self.assertAlmostEqual(width, 1440 / 620, places=7)

    def test_checked_in_native_outputs_match_reviewed_pixels(self):
        legacy_paths = {p['output'] for p in portraits.LEGACY_AVATARS}
        for entry in portraits.NATIVE_AVATARS:
            with self.subTest(name=entry['name']):
                self.assertNotIn(entry['output'], legacy_paths)
                marker = '-edited-' if entry.get('source_kind') == 'user_authorized_ai_edit' else '-native-'
                self.assertIn(marker + entry['sha256'][:12], entry['output'])
                self.assertNotIn('crop', entry)
                self.assertNotIn('max_width', entry)
                portraits.verify_native_output(entry)

    def test_authorized_mark_edit_is_not_misrepresented_as_original_pixels(self):
        entry = next(p for p in portraits.NATIVE_AVATARS if p['name'] == 'Mark Paul')
        self.assertEqual(entry['source_kind'], 'user_authorized_ai_edit')
        self.assertEqual(entry['original_output_pixel_sha256'],
                         'b8005accc4dff3ef5a4dd7cb91f05c4fe5917637225e88d156371404214a97c4')
        self.assertEqual(entry['pixel_sha256'],
                         '88a51f56661f0ad624c949ea23eadc5e36ec89a36df87ddaa3471b979240b950')
        self.assertNotEqual(entry['pixel_sha256'], entry['original_output_pixel_sha256'])

    def test_photo_markup_is_reproducible_without_changing_other_content(self):
        source = (portraits.ROOT / 'docs/team.md').read_text()
        self.assertEqual(portraits.render_document(source), source)
        self.assertEqual(source.count('class="former-member-card"'), 30)

    def test_native_builder_is_pixel_exact_and_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / 'original.png', root / 'new-native.webp'
            image = Image.new('RGBA', (8, 12), (96, 128, 160, 200))
            image.save(source)
            original_bytes = source.read_bytes()
            entry = {'name': 'Test', 'source': source.name, 'output': output.name,
                     'sha256': hashlib.sha256(original_bytes).hexdigest(),
                     'source_dimensions': [8, 12],
                     'pixel_sha256': hashlib.sha256(image.tobytes()).hexdigest()}
            with patch.object(portraits, 'ROOT', root), patch.object(portraits, 'NATIVE_AVATARS', [entry]):
                portraits.build()
                first = output.read_bytes()
                portraits.build()
                self.assertEqual(output.read_bytes(), first)
                self.assertEqual(source.read_bytes(), original_bytes)
                Image.new('RGBA', (4, 6), '#fff').save(output, 'WEBP', lossless=True)
                invalid = output.read_bytes()
                with self.assertRaises(AssertionError):
                    portraits.build()
                self.assertEqual(output.read_bytes(), invalid)

    def test_cache_prewarm_uses_temporary_stage_not_live_site(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'native.webp'
            source.write_bytes(b'reviewed-native')
            live = root / 'site'
            live.mkdir()
            sentinel = live / 'index.html'
            sentinel.write_text('live preview unchanged')
            stages = []

            def inspect_variant(url, page, **kwargs):
                stages.append(page.parent)
                self.assertNotEqual(page.parent, live)
                self.assertEqual((page.parent / url.lstrip('/')).read_bytes(), source.read_bytes())
                self.assertEqual(kwargs, {'portrait': True})

            with patch.object(portraits, 'ROOT', root), \
                    patch.object(portraits, 'verify_native_output'), \
                    patch('prepare_site.Media') as media:
                media.return_value.variants.side_effect = inspect_variant
                portraits.warm_cache([{'name': 'Test', 'output': source.name}])
                self.assertEqual(media.call_args.args[1], root / '.cache/media')
            self.assertEqual(sentinel.read_text(), 'live preview unchanged')
            self.assertEqual(len(stages), 1)
            self.assertFalse(stages[0].exists())


if __name__ == '__main__':
    unittest.main()
