"""Small parser regressions for the static site-wide Dark Reader opt-out."""

import unittest

from check_site_media import ReferenceParser, darkreader_lock_is_valid


class DarkReaderLockTests(unittest.TestCase):
    def test_exactly_one_in_head(self):
        parser = ReferenceParser()
        parser.feed('<html><head><meta name="darkreader-lock"></head><body></body></html>')
        self.assertTrue(darkreader_lock_is_valid(parser))

    def test_missing_duplicate_or_body_lock_is_rejected(self):
        for document in (
            '<html><head></head><body></body></html>',
            '<head><meta name="darkreader-lock"><meta name="darkreader-lock"></head>',
            '<head></head><body><meta name="darkreader-lock"></body>',
            '<head><meta name="darkreader-lock"></head><body><meta name="darkreader-lock"></body>',
        ):
            with self.subTest(document=document):
                parser = ReferenceParser()
                parser.feed(document)
                self.assertFalse(darkreader_lock_is_valid(parser))

    def test_self_closing_meta_in_head(self):
        parser = ReferenceParser()
        parser.feed('<head><meta name="darkreader-lock" /></head>')
        self.assertTrue(darkreader_lock_is_valid(parser))


if __name__ == '__main__':
    unittest.main()
