"""Guarantee lossless delivery preserves the approved native hero artwork."""
from pathlib import Path
import unittest

from PIL import Image


class HeroLogoDeliveryTests(unittest.TestCase):
    def test_delivery_preserves_every_rgba_pixel(self):
        images = Path(__file__).resolve().parents[1] / 'docs/img'
        with Image.open(images / 'logo-hero-dark.png') as original, Image.open(images / 'logo-hero-dark.webp') as delivery:
            self.assertEqual(original.size, (2048, 636))
            self.assertEqual(delivery.size, original.size)
            self.assertEqual(delivery.convert('RGBA').tobytes(), original.convert('RGBA').tobytes())
        self.assertLess((images / 'logo-hero-dark.webp').stat().st_size, (images / 'logo-hero-dark.png').stat().st_size)


if __name__ == '__main__':
    unittest.main()
