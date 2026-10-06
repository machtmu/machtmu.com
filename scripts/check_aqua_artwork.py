#!/usr/bin/env python3
"""Check Aqua's actual rendered colors and unchanged symbol across engines."""
import argparse
import json
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright
from prepare_aqua_artwork import dark_artwork

parser = argparse.ArgumentParser()
parser.add_argument('--url', default='http://127.0.0.1:8876')
parser.add_argument('--browser', choices=('chromium', 'webkit'), default='chromium')
parser.add_argument('--executable', help='Optional browser executable override')
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
original = (root/'docs/sponsors/aqua-environment-logo.svg').read_text()
assert (root/'docs/sponsors/aqua-environment-logo-dark-v2.svg').read_text() == dark_artwork(original)

with sync_playwright() as p:
    options = {}
    if args.browser == 'chromium':
        options = {'executable_path': shutil.which('google-chrome'), 'args': ['--no-sandbox']}
    if args.executable:
        options['executable_path'] = args.executable
    browser = getattr(p, args.browser).launch(**options)
    for width in (320, 390, 430, 768):
        for theme in ('light', 'dark'):
            page = browser.new_page(viewport={'width': width, 'height': 844},
                                    device_scale_factor=3, color_scheme=theme,
                                    is_mobile=width<=430, has_touch=width<=430)
            page.goto(args.url.rstrip('/')+'/sponsors/', wait_until='domcontentloaded')
            page.wait_for_function('(dark)=>document.body.dataset.mdColorScheme===(dark?"slate":"default")', arg=theme=='dark')
            tile = page.locator('.sponsor-item[href*="aquaenvironment"]')
            visible = tile.locator('img:visible')
            expected = 'aqua-environment-logo-dark-v2.svg' if theme=='dark' else 'aqua-environment-logo.svg'
            assert visible.get_attribute('src').endswith(expected)
            assert visible.evaluate('(img)=>getComputedStyle(img).filter') == 'none'
            result = tile.evaluate('''async tile=>{
                const imgs=await Promise.all([...tile.querySelectorAll('img')].map(async source=>{
                    const img=new Image(); img.src=source.src; await img.decode(); return img;
                }));
                const buffers=imgs.map(img=>{
                    const canvas=document.createElement('canvas');
                    canvas.width=1954; canvas.height=275;
                    const ctx=canvas.getContext('2d'); ctx.drawImage(img,0,0);
                    return ctx.getImageData(0,0,1954,275).data;
                });
                let symbolChanges=0; const opaqueColors={};
                for(let y=0;y<275;y++) for(let x=0;x<1954;x++) {
                    const i=(y*1954+x)*4;
                    if(x<300 && buffers[0].slice(i,i+4).some((v,c)=>v!==buffers[1][i+c])) symbolChanges++;
                    if(x>=300 && buffers[1][i+3]===255) {
                        const rgb=[...buffers[1].slice(i,i+3)].join(',');
                        opaqueColors[rgb]=(opaqueColors[rgb]||0)+1;
                    }
                }
                return {symbolChanges, opaqueColors};
            }''')
            assert result['symbolChanges'] == 0, result
            assert set(result['opaqueColors']) == {'167,205,255', '189,189,189'}, result
            assert min(result['opaqueColors'].values()) > 10000, result
            print(json.dumps({'browser': args.browser, 'width': width, 'theme': theme, **result}))
            page.close()
    browser.close()
