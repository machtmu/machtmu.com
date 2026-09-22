#!/usr/bin/env python3
"""Audit all sponsor logos at 3x display density and common responsive widths."""
import argparse
import base64
import io
import json
import re
from pathlib import Path
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

from playwright.sync_api import sync_playwright
from PIL import Image
import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument('--url', default='http://127.0.0.1:8876')
parser.add_argument('--chrome', default='/opt/google/chrome/chrome')
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
out = Path('/tmp/mach-sponsor-audit')
out.mkdir(exist_ok=True)

original = Image.open(root/'docs/sponsors/flownex-logo.png').convert('RGBA')
bounds = original.getchannel('A').getbbox()
light = np.array(Image.open(root/'docs/sponsors/flownex-logo-original.png'))
dark = np.array(Image.open(root/'docs/sponsors/flownex-logo-dark.png'))
assert np.array_equal(light, np.array(original.crop(bounds)))
assert np.array_equal(light[:100-bounds[1]], dark[:100-bounds[1]])
assert np.array_equal(light[:, :, 3], dark[:, :, 3])
# No rectangular remnant outside the bottom-right of Megapro's O.
for name in ('megapro-wordmark.png', 'megapro-wordmark-dark.png'):
    source = Image.open(root/'docs/sponsors'/name)
    assert source.info['Author'] == 'MEGAPRO Tools'
    assert 'creativecommons.org/licenses/by-sa/4.0/' in source.info['License']
    logo = np.array(source)
    assert logo[78:80, 565:569, 3].max() < 20

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=args.chrome, headless=True, args=['--no-sandbox'])
    for width in (320, 390, 430, 768, 1024, 1440):
        for theme in ('light', 'dark'):
            page = browser.new_page(viewport={'width':width, 'height':900}, device_scale_factor=3, color_scheme=theme, is_mobile=width<=430, has_touch=width<=430)
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(args.url.rstrip('/')+'/sponsors/', wait_until='domcontentloaded')
            page.wait_for_function('(dark)=>document.body.dataset.mdColorScheme===(dark?"slate":"default")', arg=theme=='dark')
            assert page.locator('.sponsor-grid > a.sponsor-item').count() == 23
            assert page.locator('.sponsor-grid > :not(a)').count() == 0
            assert page.get_by_role('link', name='Artwork credits', exact=True).count() == 0
            assert '© 2017 MEGAPRO Tools' in page.locator('.sponsor-item[href*="megaprotools"]').get_attribute('title')
            if width <= 768:
                spacing = page.locator('.sponsor-grid').evaluate('''grid=>{
                    const tiles=[...grid.children].map(e=>e.getBoundingClientRect());
                    const bounds=grid.getBoundingClientRect();
                    const last=tiles.at(-1);
                    return {firstHeight:tiles[0].height, gap:tiles[2].y-tiles[0].bottom,
                        lastCentered:Math.abs(last.x+last.width/2-bounds.x-bounds.width/2)<1};
                }''')
                assert spacing['firstHeight'] < 85 and 8 <= spacing['gap'] <= 16 and spacing['lastCentered'], spacing
                # Pair the thin wordmarks instead of leaving Stein beside SolidWorks.
                pair = page.locator('.sponsor-grid').evaluate('''grid=>{
                    const a=grid.querySelector('[href*="voestalpine"]').getBoundingClientRect();
                    const b=grid.querySelector('[href*="steinindustries"]').getBoundingClientRect();
                    return {sameRow:Math.abs(a.y-b.y)<1, leftOfStein:a.right<b.x};
                }''')
                assert pair['sameRow'] and pair['leftOfStein'], pair
            for item in page.locator('.sponsor-item').all():
                item.scroll_into_view_if_needed()
                item.locator('img:visible').evaluate('(img)=>img.decode()')
            result = page.locator('.sponsor-item').evaluate_all('''items=>items.map(item=>{
                const img=[...item.querySelectorAll('img')].find(i=>getComputedStyle(i).display!=='none');
                const image=img.getBoundingClientRect(), crop=item.querySelector('.sponsor-logo__crop').getBoundingClientRect(), tile=item.getBoundingClientRect();
                return {name:item.getAttribute('aria-label')||img.alt, src:img.src, natural:img.naturalWidth, naturalHeight:img.naturalHeight,
                    width:image.width, height:image.height, centered:Math.abs(crop.x+crop.width/2-tile.x-tile.width/2)<1,
                    ratio:crop.width/crop.height, visible:[...item.querySelectorAll('img')].filter(i=>getComputedStyle(i).display!=='none').length};
            })''')
            for logo in result:
                assert logo['name'] and logo['visible'] == 1 and logo['centered'], logo
                path = root/'docs'/urlsplit(logo['src']).path.lstrip('/')
                if path.suffix == '.svg':
                    doc = ET.parse(path).getroot()
                    viewbox = list(map(float, doc.get('viewBox').split()))
                    assert abs((logo['width']/logo['height'])/(viewbox[2]/viewbox[3])-1)<.002, ('stretched SVG',logo)
                    embedded = doc.findall('.//{http://www.w3.org/2000/svg}image')
                    if not embedded:
                        logo['quality'] = 'vector'
                        continue
                    assert len(embedded) == 1, path
                    part = embedded[0]
                    # Raster icon occupies only part of Aqua's vector wordmark.
                    # Account for its placement instead of treating it as full-width.
                    assert re.fullmatch(r'translate\([^)]*\)', part.get('transform', '')), part.attrib
                    href = part.get('{http://www.w3.org/1999/xlink}href') or part.get('href')
                    native = Image.open(io.BytesIO(base64.b64decode(href.split(',')[1]))).width
                    available = native / float(part.get('width')) * float(doc.get('viewBox').split()[2])
                else:
                    available = logo['natural']
                    assert abs((logo['width']/logo['height'])/(logo['natural']/logo['naturalHeight'])-1)<.002, ('stretched raster',logo)
                density = available / logo['width']
                assert density >= 3, (width, theme, logo['name'], density)
                logo['quality'] = f'{density:.1f}x'
            assert not errors, errors
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            page.evaluate('scrollTo(0,0)')
            page.wait_for_timeout(150)
            if width in (390, 768, 1440):
                page.screenshot(path=str(out/f'sponsors-{width}-{theme}.png'), full_page=True)
            if width == 390:
                for name in ('flownex', 'megaprotools', 'steinindustries', 'notion'):
                    page.locator(f'.sponsor-item[href*="{name}"]').screenshot(path=str(out/f'{name}-{theme}.png'))
            print(json.dumps({'width':width,'theme':theme,'logos':[{k:logo[k] for k in ('name','quality')} for logo in result]}), flush=True)
            page.close()
    browser.close()
print('All 23 logos: 3x-or-vector sharpness, tight centered bounds and light/dark rendering passed.')
