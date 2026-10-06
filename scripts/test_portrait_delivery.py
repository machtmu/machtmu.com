"""Keep format-only portrait delivery faithful to the retained native PNGs."""
from pathlib import Path
import unittest

from PIL import Image


class PortraitDeliveryTests(unittest.TestCase):
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
