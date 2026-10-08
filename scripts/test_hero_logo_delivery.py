"""Guarantee lossless delivery preserves the approved native hero artwork."""
from pathlib import Path
import base64
import xml.etree.ElementTree as ET
import unittest

from PIL import Image


class HeroLogoDeliveryTests(unittest.TestCase):
    def test_centered_canvas_preserves_artwork_and_hdr_layers(self):
        images = Path(__file__).resolve().parents[1] / 'docs/img'
        for original, centered in (
            ('logo-hero-dark.webp', 'logo-hero-word-centered.svg'),
            ('logo-hero-hdr-mask.png', 'logo-hero-word-centered-hdr-mask.svg'),
            ('logo-hero-hdr-accent-mask.png', 'logo-hero-word-centered-hdr-accent-mask.svg'),
        ):
            root = ET.parse(images / centered).getroot()
            left, _, width, _ = map(float, root.attrib['viewBox'].split())
            self.assertEqual(left + width / 2, (0 + 1625) / 2)
            image = root.find('{http://www.w3.org/2000/svg}image')
            payload = image.attrib['href'].split(',', 1)[1]
            self.assertEqual(base64.b64decode(payload), (images / original).read_bytes())

    def test_delivery_preserves_every_rgba_pixel(self):
        images = Path(__file__).resolve().parents[1] / 'docs/img'
        with Image.open(images / 'logo-hero-dark.png') as original, Image.open(images / 'logo-hero-dark.webp') as delivery:
            self.assertEqual(original.size, (2048, 636))
            self.assertEqual(delivery.size, original.size)
            self.assertEqual(delivery.convert('RGBA').tobytes(), original.convert('RGBA').tobytes())
        self.assertLess((images / 'logo-hero-dark.webp').stat().st_size, (images / 'logo-hero-dark.png').stat().st_size)


if __name__ == '__main__':
    unittest.main()
