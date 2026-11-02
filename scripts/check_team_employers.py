#!/usr/bin/env python3
"""Focused employer-grid checks: native artwork, density, themes and navigation."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright


COMPANIES = ["SpaceX", "Tesla", "Rocket Lab / Sinclair Interplanetary", "Pratt & Whitney",
             "Bombardier", "Safran", "NordSpace", "Reaction Dynamics", "Celestica",
             "Cesaroni Technology", "Dishon"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8886')
    parser.add_argument('--browser', choices=('chromium', 'webkit'), default='chromium')
    parser.add_argument('--widths', type=int, nargs='+', default=[320, 390, 768, 1440])
    parser.add_argument('--output', type=Path, default=Path('/tmp/mach-team-employers'))
    args = parser.parse_args()
    assets = Path(__file__).resolve().parents[1] / 'docs/assets/images/member-employers'
    cti_original = (assets / 'cesaroni-queens.png').read_bytes()
    assert hashlib.sha256(cti_original).hexdigest() == 'ad76bd0404940425398b2b54be72ff4ff23c453c5aba17cbc3a8f9b60df7a359'
    embedded = next(ET.parse(assets / 'cesaroni-queens-dark.svg').getroot().iter('{http://www.w3.org/2000/svg}image'))
    original_uri = embedded.get('href') or embedded.get('{http://www.w3.org/1999/xlink}href')
    assert base64.b64decode(original_uri.split(',', 1)[1]) == cti_original
    args.output.mkdir(parents=True, exist_ok=True)
    base = args.url.rstrip('/')
    results = []
    with sync_playwright() as p:
        browser = (p.webkit.launch() if args.browser == 'webkit' else
                   p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox']))
        for width in args.widths:
            for scheme in ('light', 'dark'):
                page = browser.new_page(viewport={'width': width, 'height': 950}, color_scheme=scheme)
                errors, failed = [], []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.on('response', lambda response: failed.append([response.status, response.url])
                        if response.status >= 400 and response.url.startswith(base) else None)
                page.goto(base + '/team/', wait_until='domcontentloaded')
                page.wait_for_function('(dark)=>document.body.dataset.mdColorScheme===(dark?"slate":"default")',
                                       arg=scheme == 'dark')
                # DOMContentLoaded need not await CSS downloads. The normal
                # head stylesheet blocks first paint, so wait for its rules
                # rather than testing unpainted DOM during a Tailnet fetch.
                page.wait_for_function('''() => {
                  const list = document.querySelector('.team-employer-list');
                  return list && getComputedStyle(list).display === 'flex';
                }''')
                links = page.locator('.team-employer-link')
                assert page.get_by_role('heading', name='Our members have been employed by;', exact=True).count() == 1
                assert links.count() == len(COMPANIES)
                assert [link.get_attribute('aria-label') for link in links.all()] == COMPANIES
                sinclair = links.nth(2)
                assert sinclair.get_attribute('href') == 'https://rocketlabcorp.com/space-systems/satellite-components/reaction-wheels/'
                assert sinclair.locator('img').first.get_attribute('alt') == 'Rocket Lab'
                assert sinclair.locator('.team-employer-caption').inner_text() == 'Sinclair Interplanetary'
                assert [image.get_attribute('src').split('/')[-1] for image in sinclair.locator('img').all()] == [
                    'rocket-lab.png', 'rocket-lab-dark.png']
                cti = page.locator('.team-employer-link--cesaroni')
                assert [image.get_attribute('src').split('/')[-1] for image in cti.locator('img').all()] == [
                    'cesaroni-queens.png', 'cesaroni-queens-dark.svg']
                for link in links.all():
                    link.scroll_into_view_if_needed()
                    displayed = [image for image in link.locator('img').all()
                                 if image.evaluate('i=>getComputedStyle(i).display!=="none"')]
                    assert len(displayed) == 1
                    image = displayed[0]
                    image.evaluate('i => i.decode()')
                    assert link.locator('img:visible').count() == 1
                    assert image.get_attribute('loading') == 'lazy'
                    assert image.get_attribute('decoding') == 'async'
                    assert image.get_attribute('width') and image.get_attribute('height')
                    assert urlsplit(link.get_attribute('href')).scheme == 'https'
                metrics = links.evaluate_all('''links => links.map(a => {
                  const i = [...a.querySelectorAll('img')].find(i => getComputedStyle(i).display !== 'none');
                  const r = a.getBoundingClientRect(), b = i.getBoundingClientRect();
                  const caption=a.querySelector('.team-employer-caption')?.getBoundingClientRect();
                  const top=caption?Math.min(b.top,caption.top):b.top;
                  const bottom=caption?Math.max(b.bottom,caption.bottom):b.bottom;
                  return {name:a.getAttribute('aria-label'), src:i.currentSrc,
                    native:[i.naturalWidth,i.naturalHeight], declared:[Number(i.getAttribute('width')),Number(i.getAttribute('height'))],
                    rendered:[b.width,b.height],
                    filter:getComputedStyle(i).filter, row:r.top, column:r.left,
                    cssOrder:getComputedStyle(a.parentElement).order,
                    center:[Math.abs((r.left+r.right-b.left-b.right)/2),Math.abs((r.top+r.bottom-top-bottom)/2)],
                    contains:b.left>=r.left-1 && b.right<=r.right+1 && top>=r.top-1 && bottom<=r.bottom+1,
                    captionFits:!caption || (caption.left>=r.left-1 && caption.right<=r.right+1 && caption.top>=b.bottom)};
                })''')
                for m in metrics:
                    assert all(m['native']) and all(m['rendered']) and m['contains'], m
                    assert m['captionFits'], m
                    assert max(m['center']) < 1, m
                    # WebKit reports SVG naturalWidth at rounded rendered size.
                    # Native declared dimensions are exact for all source art.
                    assert abs(m['declared'][0] / m['declared'][1] - m['rendered'][0] / m['rendered'][1]) < .02, m
                    if not m['src'].endswith('.svg'):
                        assert m['native'][0] / m['rendered'][0] >= 3, m
                        assert m['native'][1] / m['rendered'][1] >= 3, m
                    if m['name'] == 'Cesaroni Technology':
                        # The dark SVG embeds this same 1024px native PNG, not
                        # vector paths; enforce its actual raster density too.
                        assert 1024 / m['rendered'][0] >= 3 and 368 / m['rendered'][1] >= 3, m
                    if m['name'] not in ('NordSpace', 'Dishon'):
                        assert m['filter'] == 'none', m
                # A theme ul:not([hidden]) rule must not silently replace flex
                # with flow-root and turn a responsive grid into one long list.
                first_row = [m for m in metrics if abs(m['row'] - metrics[0]['row']) < 1]
                assert len(first_row) == (2 if width <= 760 else 4), first_row
                assert all(m['cssOrder'] == '0' for m in metrics)
                assert [m['name'] for m in sorted(metrics, key=lambda m: (round(m['row']), m['column']))] == COMPANIES
                assert page.locator('.team-portrait').count() == 6
                assert page.locator('.former-member-card').count() == 31
                if width == 1440 and scheme == 'dark':
                    cti_proof = page.evaluate('''async base=>{
                      const urls=['cesaroni-queens.png','cesaroni-queens-dark.svg'];
                      const images=await Promise.all(urls.map(async name=>{
                        const image=new Image();image.src=base+'/assets/images/member-employers/'+name;
                        await image.decode();return image;
                      }));
                      const pixels=images.map(image=>{
                        const canvas=document.createElement('canvas');canvas.width=1024;canvas.height=368;
                        const ctx=canvas.getContext('2d');ctx.drawImage(image,0,0,1024,368);
                        return ctx.getImageData(0,0,1024,368).data;
                      });
                      let symbolChanges=0,alphaChanges=0,textChanges=0;
                      for(let y=0;y<368;y++)for(let x=0;x<1024;x++){
                        const i=(y*1024+x)*4;
                        const changed=pixels[0].slice(i,i+4).some((v,c)=>v!==pixels[1][i+c]);
                        if(changed){if(x<400)symbolChanges++;else textChanges++;}
                        if(pixels[0][i+3]!==pixels[1][i+3])alphaChanges++;
                      }
                      return {symbolChanges,alphaChanges,textChanges};
                    }''', base)
                    assert cti_proof['symbolChanges'] == 0 and cti_proof['alphaChanges'] == 0, cti_proof
                    assert cti_proof['textChanges'] > 0, cti_proof
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), width
                links.first.focus()
                assert links.first.evaluate('a=>getComputedStyle(a).outlineStyle') != 'none'
                links.first.evaluate('a=>a.blur()')
                page.locator('.team-employers').screenshot(
                    path=str(args.output / f'{args.browser}-{width}-{scheme}.png'),
                    animations='disabled', style='.md-header{visibility:hidden!important}')
                # Native instant navigation must reinsert both theme variants and
                # the local SVG filter without displaying duplicate logos.
                page.locator('.md-logo').first.click()
                page.wait_for_url(lambda url: url.split('#', 1)[0] == base + '/')
                page.locator('.home-hero').wait_for(state='visible')
                if width >= 768:
                    page.locator('.md-tabs a[href$="team/"]').first.click()
                    page.wait_for_url(base + '/team/')
                    page.locator('.team-employers').wait_for(state='visible')
                    for link in page.locator('.team-employer-link').all():
                        link.scroll_into_view_if_needed()
                        for image in link.locator('img').all():
                            if image.evaluate('i=>getComputedStyle(i).display!=="none"'):
                                image.evaluate('i=>i.decode()')
                        assert link.locator('img:visible').count() == 1
                assert not errors and not failed, [errors, failed]
                results.append({'width': width, 'scheme': scheme, 'logos': metrics,
                                **({'ctiBrandProof': cti_proof} if width == 1440 and scheme == 'dark' else {})})
                page.close()
        browser.close()
    (args.output / f'{args.browser}.json').write_text(json.dumps(results, indent=2))
    print(f'{args.browser}: {len(results)} employer grid/theme/navigation checks passed.')


if __name__ == '__main__':
    main()
