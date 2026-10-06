"""The optimization pass must leave source media and download URLs intact."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from PIL import Image
from prepare_site import prepare


class PreparationTests(unittest.TestCase):
    def test_downloads_themes_deferred_slides_and_nested_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            site = root / "site"
            for folder in ("assets", "css", "js", "nested", "sponsors"):
                (site / folder).mkdir(parents=True, exist_ok=True)
            image = site / "assets/photo.jpg"
            Image.effect_noise((1600, 1000), 80).convert("RGB").save(image)
            logo = site / "sponsors/logo.png"
            Image.new("RGBA", (1600, 350), (192, 12, 24, 255)).save(logo)
            digest = hashlib.sha256(image.read_bytes()).hexdigest()
            (site / "css/extra.css").write_text("body {color:red}")
            (site / "js/site.js").write_text("console.log('test')")
            page = site / "nested/index.html"
            page.write_text('<!DOCTYPE html><link href="../css/extra.css" rel="stylesheet">'
                            '<script src="../js/site.js"></script><a href="/assets/photo.jpg" download>Original</a>'
                            '<img src="/assets/photo.jpg" alt="Photo" class="slideshow-image">'
                            '<img src="/sponsors/logo.png" alt="Brand">'
                            '<img src="/plot.png" data-plot-light-src="/plot.png" data-plot-dark-src="/plot-dark.png">')
            prepare(site, root / "cache")
            result = page.read_text()
            self.assertEqual(hashlib.sha256(image.read_bytes()).hexdigest(), digest)
            self.assertIn('<a href="/assets/photo.jpg" download>', result)
            self.assertIn('data-plot-dark-src="/plot-dark.png"', result)
            self.assertIn('data-slide-src="/assets/display/', result)
            self.assertIn('data-slide-srcset="', result)
            self.assertRegex(result, r'/css/extra\.[0-9a-f]{12}\.css')
            self.assertRegex(result, r'/js/site\.[0-9a-f]{12}\.js')
            with Image.open(next((site / "assets/display").glob("*-logo.webp"))) as preview:
                self.assertEqual(preview.convert("RGBA").getpixel((100, 100)), (192, 12, 24, 255))


if __name__ == "__main__":
    unittest.main()
