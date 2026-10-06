"""The optimization pass must leave source media and download URLs intact."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from PIL import Image
from prepare_site import prepare, navigation_assets, NAVIGATION_MEDIA, immediate_navigation_close, Media, Rewriter, portrait_encoding


class PreparationTests(unittest.TestCase):
    def add_theme_assets(self, site):
        stylesheet = site / "assets/stylesheets/modern/main.test.min.css"
        bundle = site / "assets/javascripts/bundle.test.min.js"
        stylesheet.parent.mkdir(parents=True, exist_ok=True)
        bundle.parent.mkdir(parents=True, exist_ok=True)
        stylesheet.write_text('@media (min-width:76.25em){.md-tabs{display:block}}'
                              '@media (max-width:76.234375em){.md-tabs{display:none}}')
        bundle.write_text('matchMedia("(min-width: 76.25em)");'
                          'I(br,vr).pipe(Mr(125)).subscribe(()=>{$o("drawer",!1),$o("search",!1)})')
        return stylesheet, bundle

    def test_only_post_navigation_drawer_cleanup_is_immediate(self):
        cleanup = 'I(br,vr).pipe(Mr(125)).subscribe(()=>{$o("drawer",!1),$o("search",!1)})'
        unrelated = 'other.pipe(Mr(125)).subscribe(refresh)'
        output = immediate_navigation_close(cleanup + ';' + unrelated)
        self.assertIn('pipe(Mr(0)).subscribe', output)
        self.assertIn(unrelated, output)
        with self.assertRaisesRegex(RuntimeError, 'cleanup not found'):
            immediate_navigation_close(unrelated)

    def test_navigation_css_and_js_share_content_fit_breakpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            paths = self.add_theme_assets(site)
            original = [path.read_bytes() for path in paths]
            assets = navigation_assets(site)
            self.assertEqual(len(assets), 2)
            for path, content in zip(paths, original):
                self.assertEqual(path.read_bytes(), content)
                generated = (site / assets["/" + path.relative_to(site).as_posix()].lstrip("/")).read_text()
                self.assertIn(NAVIGATION_MEDIA["76.25em"], generated)
                self.assertNotIn("76.25em", generated)
                self.assertNotIn("76.234375em", generated)
            self.assertEqual(navigation_assets(site), assets)
            paths[1].write_text('matchMedia("(min-width: 80em)")')
            with self.assertRaisesRegex(RuntimeError, "breakpoint not found"):
                navigation_assets(site)

    def test_downloads_themes_responsive_images_and_nested_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            site = root / "site"
            for folder in ("assets", "css", "js", "nested", "sponsors"):
                (site / folder).mkdir(parents=True, exist_ok=True)
            self.add_theme_assets(site)
            image = site / "assets/photo.jpg"
            Image.effect_noise((1600, 1000), 80).convert("RGB").save(image)
            logo = site / "sponsors/logo.png"
            Image.new("RGBA", (1600, 350), (192, 12, 24, 255)).save(logo)
            digest = hashlib.sha256(image.read_bytes()).hexdigest()
            (site / "css/extra.css").write_text("body {color:red}")
            (site / "js/site.js").write_text("console.log('test')")
            page = site / "nested/index.html"
            page.write_text('<!DOCTYPE html><link href="../assets/stylesheets/modern/main.test.min.css" rel="stylesheet">'
                            '<script src="../assets/javascripts/bundle.test.min.js"></script>'
                            '<link href="../css/extra.css" rel="stylesheet">'
                            '<script src="../js/site.js"></script><a href="/assets/photo.jpg" download>Original</a>'
                            '<img src="/assets/photo.jpg" alt="Photo">'
                            '<img src="/sponsors/logo.png" alt="Brand">'
                            '<img src="/plot.png" data-plot-light-src="/plot.png" data-plot-dark-src="/plot-dark.png">')
            prepare(site, root / "cache")
            result = page.read_text()
            self.assertEqual(hashlib.sha256(image.read_bytes()).hexdigest(), digest)
            self.assertIn('<a href="/assets/photo.jpg" download>', result)
            self.assertIn('data-plot-dark-src="/plot-dark.png"', result)
            self.assertIn('src="/assets/display/', result)
            self.assertIn('srcset="', result)
            self.assertIn('data-original-src="/assets/photo.jpg"', result)
            self.assertNotIn('data-slide-', result)
            self.assertRegex(result, r'/css/extra\.[0-9a-f]{12}\.css')
            self.assertRegex(result, r'/js/site\.[0-9a-f]{12}\.js')
            self.assertRegex(result, r'/main\.test\.min\.nav-[0-9a-f]{12}\.css')
            self.assertRegex(result, r'/bundle\.test\.min\.nav-[0-9a-f]{12}\.js')
            with Image.open(next((site / "assets/display").glob("*-logo.webp"))) as preview:
                self.assertEqual(preview.convert("RGBA").getpixel((100, 100)), (192, 12, 24, 255))

    def test_portrait_derivatives_keep_native_master_and_explicit_sizes(self):
        self.assertEqual(portrait_encoding(True), {'lossless': True, 'quality': 100})
        self.assertEqual(portrait_encoding(False), {'lossless': False, 'quality': 96})
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory) / 'site'
            site.mkdir()
            master = site / 'portrait.webp'
            Image.effect_noise((900, 1100), 40).convert('RGB').save(master, 'WEBP', lossless=True, exact=True)
            digest = hashlib.sha256(master.read_bytes()).hexdigest()
            media = Media(site, Path(directory) / 'cache')
            writer = Rewriter(site / 'index.html', media, {})
            writer.feed('<img src="/portrait.webp" data-display-original data-portrait-delivery sizes="75vw">')
            result = ''.join(writer.parts)
            self.assertIn('sizes="75vw"', result)
            self.assertIn('data-original-src="/portrait.webp"', result)
            self.assertIn('320w', result)
            self.assertIn('900w', result)
            self.assertEqual(hashlib.sha256(master.read_bytes()).hexdigest(), digest)
            with Image.open(next(media.output.glob('*-320-portrait-q96.webp'))) as display:
                self.assertEqual(display.size, (320, 391))
            with Image.open(master) as source, Image.open(next(media.output.glob('*-900-portrait-lossless.webp'))) as native:
                self.assertEqual(source.convert('RGBA').tobytes(), native.convert('RGBA').tobytes())


if __name__ == "__main__":
    unittest.main()
