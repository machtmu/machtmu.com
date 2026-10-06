#!/usr/bin/env python3
"""Audit all sponsor logos at 3x display density and common responsive widths."""
import argparse
from collections import Counter
import base64
import io
import json
import re
import shutil
from pathlib import Path
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

from playwright.sync_api import sync_playwright
from PIL import Image
import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument('--url', default='http://127.0.0.1:8876')
parser.add_argument('--chrome', default=shutil.which('google-chrome') or '/opt/google/chrome/chrome')
parser.add_argument('--quick', action='store_true')
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
out = Path('/tmp/mach-sponsor-audit')
out.mkdir(exist_ok=True)

original = Image.open(root/'docs/sponsors/flownex-logo.png').convert('RGBA')
aqua_original = (root/'docs/sponsors/aqua-environment-logo.svg').read_text().strip()
aqua_dark = (root/'docs/sponsors/aqua-environment-logo-dark.svg').read_text().strip()
aqua_text_filter = '.cls-2,.cls-3{filter:invert(1) hue-rotate(180deg) saturate(1.05) brightness(1.08);}'
assert aqua_dark == aqua_original.replace('</style>', aqua_text_filter+'</style>')
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

brand_colours = {}
sif_bounds = Image.open(root/'docs/sponsors/SIF-logo.png').getchannel('A').getbbox()
assert sif_bounds == (23, 196, 1003, 815), ('SIF artwork changed; recheck crop', sif_bounds)
for sponsor, filename in (('dishoncnc.com', 'dishon-logo-hires.png'),
                          ('hoskin.ca', 'hoskin-logo-hires.png'),
                          ('innovationboostzone', 'ibz-logo-transparent.png')):
    source = np.array(Image.open(root/'docs/sponsors'/filename).convert('RGBA'))
    red = ((source[:, :, 0].astype(float) > source[:, :, 1]*1.4)
           & (source[:, :, 0].astype(float) > source[:, :, 2]*1.1)
           & (source[:, :, 3] == 255))
    brand_colours[sponsor] = Counter(map(tuple, source[red, :3])).most_common(1)[0][0]

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=args.chrome, headless=True, args=['--no-sandbox'])
    for width in ((390, 768) if args.quick else (320, 390, 430, 768, 1024, 1440)):
        for theme in ('light', 'dark'):
            page = browser.new_page(viewport={'width':width, 'height':900}, device_scale_factor=3, color_scheme=theme, is_mobile=width<=430, has_touch=width<=430)
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(args.url.rstrip('/')+'/sponsors/', wait_until='domcontentloaded')
            page.wait_for_function('(dark)=>document.body.dataset.mdColorScheme===(dark?"slate":"default")', arg=theme=='dark')
            assert page.locator('.sponsor-grid > a.sponsor-item').count() == 24
            assert page.locator('.sponsor-grid > :not(a)').count() == 0
            assert page.get_by_role('link', name='Artwork credits', exact=True).count() == 0
            assert '© 2017 MEGAPRO Tools' in page.locator('.sponsor-item[href*="megaprotools"]').get_attribute('title')
            aqua = page.locator('.sponsor-item[href*="aquaenvironment"] img:visible')
            assert aqua.evaluate('(img)=>getComputedStyle(img).filter') == 'none'
            assert aqua.get_attribute('src').endswith('aqua-environment-logo-dark.svg' if theme == 'dark' else 'aqua-environment-logo.svg')
            if width == 390 and theme == 'dark':
                comparison = page.locator('.sponsor-item[href*="aquaenvironment"]').evaluate('''async tile=>{
                    const images=[...tile.querySelectorAll('img')].map(source=>{
                        const img=new Image(); img.src=source.src; return img;
                    });
                    await Promise.all(images.map(img=>img.decode()));
                    const buffers=images.map(img=>{
                        const canvas=document.createElement('canvas');
                        canvas.width=1954; canvas.height=275;
                        const ctx=canvas.getContext('2d');
                        ctx.drawImage(img,0,0,1954,275);
                        return ctx.getImageData(0,0,1954,275).data;
                    });
                    let symbolChanges=0, textChanges=0;
                    for(let y=0;y<275;y++) for(let x=0;x<1954;x++) {
                        const i=(y*1954+x)*4;
                        if(buffers[0].slice(i,i+4).some((v,c)=>v!==buffers[1][i+c])) {
                            if(x<300) symbolChanges++; else textChanges++;
                        }
                    }
                    return {symbolChanges,textChanges};
                }''')
                assert comparison['symbolChanges'] == 0 and comparison['textChanges'] > 0, comparison
            if width <= 768:
                spacing = page.locator('.sponsor-grid').evaluate('''grid=>{
                    const tiles=[...grid.children].map(e=>e.getBoundingClientRect());
                    const bounds=grid.getBoundingClientRect();
                    const last=tiles.at(-1);
                    return {firstHeight:tiles[0].height, gap:tiles[2].y-tiles[0].bottom,
                        lastBalanced:tiles.length%2
                            ? Math.abs(last.x+last.width/2-bounds.x-bounds.width/2)<1
                            : Math.abs(last.y-tiles.at(-2).y)<1};
                }''')
                assert spacing['firstHeight'] < 85 and 8 <= spacing['gap'] <= 16 and spacing['lastBalanced'], spacing
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
            sif = page.locator('.sponsor-item.logo-sif')
            sif_geometry = sif.evaluate('''tile=>{
                const img=tile.querySelector('img'), r=img.getBoundingClientRect();
                const c=tile.querySelector('.sponsor-logo__crop').getBoundingClientRect();
                const x=r.width/1024, y=r.height/1024;
                return {filter:getComputedStyle(img).filter,
                    margins:[r.x+23*x-c.x,r.y+196*y-c.y,
                        c.right-r.x-1003*x,c.bottom-r.y-815*y]};
            }''')
            assert sif_geometry['filter'] == ('none' if theme == 'dark' else 'brightness(0)'), sif_geometry
            assert all(-.05 <= margin <= 1 for margin in sif_geometry['margins']), ('SIF clipped or padded', sif_geometry)
            sif_pixels = np.array(Image.open(io.BytesIO(sif.screenshot())).convert('RGB'))
            sif_ink = sif_pixels.min(axis=2)>245 if theme=='dark' else sif_pixels.max(axis=2)<10
            assert sif_ink.sum()>100, ('SIF lacks contrast', width, theme)
            if width == 390:
                sif.screenshot(path=str(out/f'sif-{theme}.png'))
            for sponsor, brand_colour in brand_colours.items():
                tile = page.locator(f'.sponsor-item[href*="{sponsor}"]')
                pixels = np.array(Image.open(io.BytesIO(tile.screenshot())).convert('RGB'))
                # Dishon's narrow red line is resampled even at 3x screen density.
                tolerance = 45 if sponsor == 'dishoncnc.com' else 2
                matching = np.max(np.abs(pixels.astype(int)-np.array(brand_colour)), axis=2) <= tolerance
                assert matching.sum() > 30, ('brand colour changed', sponsor, width, theme)
                if theme == 'dark':
                    assert (pixels.min(axis=2) > 245).sum() > 30, ('lettering not visible', sponsor)
                    if sponsor == 'innovationboostzone':
                        crop = tile.locator('.sponsor-logo__crop')
                        edge_pixels = np.array(Image.open(io.BytesIO(crop.screenshot())).convert('RGB'))
                        # The first 30% contains only red artwork/background, before Z.
                        # Any bright green channel here is a pale/white edge halo.
                        red_region = edge_pixels[:, :int(edge_pixels.shape[1]*.30)]
                        assert red_region[:, :, 1].max() <= 20, ('IBZ white edge fringe', width, red_region[:, :, 1].max())
                        if width == 390:
                            crop.screenshot(path=str(out/'ibz-clean-dark.png'))
            result = page.locator('.sponsor-item').evaluate_all('''items=>items.map(item=>{
                const img=[...item.querySelectorAll('img')].find(i=>getComputedStyle(i).display!=='none');
                const image=img.getBoundingClientRect(), crop=item.querySelector('.sponsor-logo__crop').getBoundingClientRect(), tile=item.getBoundingClientRect();
                return {name:item.getAttribute('aria-label')||img.alt, src:img.currentSrc||img.src, natural:img.naturalWidth, naturalHeight:img.naturalHeight,
                    width:image.width, height:image.height, centered:Math.abs(crop.x+crop.width/2-tile.x-tile.width/2)<1,
                    ratio:crop.width/crop.height, visible:[...item.querySelectorAll('img')].filter(i=>getComputedStyle(i).display!=='none').length};
            })''')
            for logo in result:
                assert logo['name'] and logo['visible'] == 1 and logo['centered'], logo
                relative = urlsplit(logo['src']).path.lstrip('/')
                path = root/('site' if relative.startswith('assets/display/') else 'docs')/relative
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
                    # A w-descriptor srcset makes naturalWidth density-corrected
                    # (and integer-rounded), not the stored raster resolution.
                    with Image.open(path) as raster:
                        available, native_height = raster.size
                    assert abs((logo['width']/logo['height'])/(available/native_height)-1)<.002, ('stretched raster',logo)
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
print('All 24 logos: 3x-or-vector sharpness, tight centered bounds and light/dark rendering passed.')
