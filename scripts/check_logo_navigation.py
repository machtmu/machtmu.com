#!/usr/bin/env python3
"""Check a single logo surface through actual instant navigation and OS changes."""
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser()
parser.add_argument('--url', default='http://127.0.0.1:8876')
parser.add_argument('--webkit', action='store_true')
parser.add_argument('--webkit-executable')
parser.add_argument('--quick', action='store_true')
parser.add_argument('--output', default='/tmp/mach-logo-navigation')
args = parser.parse_args()
base = args.url.rstrip('/')
out = Path(args.output)
out.mkdir(parents=True, exist_ok=True)

with sync_playwright() as playwright:
    browser = (playwright.webkit.launch(**({'executable_path': args.webkit_executable} if args.webkit_executable else {}))
               if args.webkit else playwright.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox']))
    for width in ((390, 1440) if args.quick else (390, 599, 600, 1440)):
        for scheme in ('light', 'dark'):
            context = browser.new_context(viewport={'width': width, 'height': 844}, color_scheme=scheme,
                                          has_touch=width < 600)
            page = context.new_page()
            errors, documents = [], []
            page.on('pageerror', lambda error: errors.append(str(error)))
            if not args.webkit:
                cdp = context.new_cdp_session(page)
                cdp.send('Network.enable')
                cdp.on('Network.requestWillBeSent', lambda e: documents.append(e['request']['url']) if e['type'] == 'Document' else None)
            page.goto(base + '/team/', wait_until='networkidle')
            page.evaluate('''()=>{
              window.__machLogoDocument = 'unchanged';
              window.__machLogoFrames = [];
              const sample = () => {
                for (const logo of document.querySelectorAll('.md-logo .mach-logo')) {
                  const images = [...logo.querySelectorAll('img')];
                  const hdr = logo.querySelector('.mach-logo__hdr');
                  window.__machLogoFrames.push({count: images.length,
                    visible: images.filter(i=>getComputedStyle(i).display!=='none').length,
                    hdrVisible: getComputedStyle(hdr).display!=='none',
                    hdrHidden: hdr.hidden,
                    source: images[0]?.currentSrc,
                    scheme: document.body.dataset.mdColorScheme,
                    overlay: logo.closest('.md-header')?.dataset.homeHero === 'overlay'});
                }
                requestAnimationFrame(sample);
              };
              requestAnimationFrame(sample);
            }''')

            def check():
                page.wait_for_function('''()=>[...document.querySelectorAll('.md-logo .mach-logo')].every(l=>{
                  const i=l.querySelector('img');
                  const overlay=l.closest('.md-header')?.dataset.homeHero==='overlay';
                  const dark=document.body.dataset.mdColorScheme==='slate';
                  return l.querySelectorAll('img').length===1 && i.complete && i.naturalWidth===512 &&
                    i.currentSrc.endsWith(dark||overlay?'logo-header-dark.png':'logo-header.png') &&
                    l.querySelector('.mach-logo__hdr').hidden===(!dark||overlay);
                })''')
                assert page.evaluate('window.__machLogoDocument') == 'unchanged'
                if not args.webkit:
                    assert len(documents) == 1, documents
                assert page.locator('.md-header .mach-logo').count() == 1
                assert page.locator('.md-header canvas, .md-header .md-header__topic img').count() == 0
                assert page.locator('.md-logo[title], .md-logo [title]').count() == 0
                assert page.locator('.md-header .mach-logo__image').evaluate_all('images=>images.every(i=>{const r=i.getBoundingClientRect();return !r.width||Math.abs(r.width/r.height-512/159)<.01})')
                assert page.locator('.md-nav .mach-logo__image').evaluate_all('images=>images.every(i=>getComputedStyle(i).objectFit==="contain")')

            def link(name, route):
                page.evaluate('scrollTo(0,0)')
                if width < 600:
                    page.locator('[data-mach-drawer-toggle]').click()
                page.get_by_role('link', name=name, exact=True).click()
                page.wait_for_url(base + route)
                page.wait_for_function('route=>document.querySelector("link[rel=canonical]").href.endsWith(route)', arg=route)
                check()

            def home():
                page.locator('.md-header [data-md-component="logo"]').click()
                page.wait_for_url(base + '/')
                page.wait_for_selector('.home-hero')
                check()
                page.evaluate('scrollTo(0,document.querySelector(".home-team-intro").offsetTop+300)')
                page.wait_for_function('document.querySelector(".md-header").dataset.homeHero==="scrolled"')
                check()

            check()
            for name, route in [('Sponsors', '/sponsors/'), ('Resources', '/resources/'), ('SPRINT', '/SPRINT/'), ('Team', '/team/')]:
                link(name, route)
                page.emulate_media(color_scheme='dark' if scheme == 'light' else 'light')
                page.wait_for_function('s=>document.body.dataset.mdColorScheme===s', arg='slate' if scheme == 'light' else 'default')
                check()
                page.emulate_media(color_scheme=scheme)
                page.wait_for_function('s=>document.body.dataset.mdColorScheme===s', arg='slate' if scheme == 'dark' else 'default')
                check()
            home()
            link('Team', '/team/')
            page.go_back()
            page.wait_for_url(base + '/')
            page.wait_for_selector('.home-hero')
            check()
            page.go_forward()
            page.wait_for_url(base + '/team/')
            check()
            # Exercise the HDR CSS branch without claiming physical luminance.
            page.evaluate('''()=>{for(const sheet of document.styleSheets){let rules;try{rules=sheet.cssRules}catch{continue}for(const rule of rules){if(rule.type===CSSRule.MEDIA_RULE&&rule.conditionText==='(dynamic-range: high)')rule.media.mediaText='all';}}}''')
            for mode in ('dark', 'light', 'dark'):
                page.emulate_media(color_scheme=mode)
                page.wait_for_function('s=>document.body.dataset.mdColorScheme===s', arg='slate' if mode == 'dark' else 'default')
                check()
                assert page.locator('.md-logo .mach-logo__hdr').evaluate_all('(els)=>els.every(e=>getComputedStyle(e).display===' + ('"block"' if mode == 'dark' else '"none"') + ')')
            frames = page.evaluate('window.__machLogoFrames')
            assert frames and all(f['count'] == 1 and f['visible'] == 1 for f in frames), frames
            assert all(not f['hdrVisible'] or (f['scheme'] == 'slate' and not f['overlay'] and not f['hdrHidden'] and f['source'].endswith('/logo-header-dark.png')) for f in frames), frames
            assert not errors, errors
            page.screenshot(path=str(out / f'{width}-{scheme}.png'))
            print(f'Single-image native SPA/Back/Forward/OS/HDR source checks passed: {width}px, {scheme}, {len(frames)} frame samples', flush=True)
            context.close()
    # Without script the native theme retains its default light palette, even
    # under a dark OS preference. Its black logo must remain readable there.
    for scheme in ('light', 'dark'):
        context = browser.new_context(java_script_enabled=False, color_scheme=scheme)
        page = context.new_page()
        page.goto(base + '/team/', wait_until='networkidle')
        assert page.locator('body').get_attribute('data-md-color-scheme') == 'default'
        assert page.locator('.mach-logo__image').evaluate_all('(els)=>els.every(i=>i.complete&&i.naturalWidth===512&&i.currentSrc.endsWith("logo-header.png"))')
        assert page.locator('.md-logo .mach-logo').evaluate_all('(els)=>els.every(e=>e.querySelectorAll("img").length===1)')
        context.close()
    browser.close()
