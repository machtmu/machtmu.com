#!/usr/bin/env python3
"""Check homepage startup delivery without compromising scrolling or themes."""
import argparse
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser()
parser.add_argument('--url', default='http://127.0.0.1:8876')
parser.add_argument('--webkit', action='store_true')
parser.add_argument('--webkit-executable', help='Optional local WebKit executable override.')
args = parser.parse_args()
base = args.url.rstrip('/')

with sync_playwright() as playwright:
    browser = (playwright.webkit.launch(**({'executable_path': args.webkit_executable} if args.webkit_executable else {}))
               if args.webkit else playwright.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox']))
    for width, height in ((412, 823), (1440, 900)):
        context = browser.new_context(viewport={'width': width, 'height': height}, color_scheme='light')
        page = context.new_page()
        requests = []
        page.on('request', lambda request: requests.append(request.url))
        page.goto(base + '/', wait_until='networkidle')
        poster = 'seraphina-august-relight-hero.webp'
        assert page.locator('link[rel="preload"][as="image"]').count() == 1
        assert page.evaluate('''()=>{
          const preload=document.querySelector('link[rel="preload"][as="image"]');
          const style=document.querySelector('link[rel="stylesheet"]');
          return preload.getAttribute('fetchpriority')==='high' && Boolean(preload.compareDocumentPosition(style)&Node.DOCUMENT_POSITION_FOLLOWING);
        }''')
        assert sum(url.endswith(poster) for url in requests) >= 1, requests
        if not args.webkit:
            assert sum(url.endswith(poster) for url in requests) == 1, requests
            assert not any(url.endswith('.mp4') for url in requests), requests
        else:
            # WPE can refetch native poster resources and preload the secondary
            # MP4 despite preload=none; its Linux codec pipeline is not Safari.
            assert not any('seraphina-august-relight-hero' in url and url.endswith('.mp4') for url in requests)
        deferred = ('seraphina-oct-4-poster.webp', 'sept-14-hotfire-2s.webp',
                    'gare-hotfire-2024-09-29-close-poster.webp', 'double-hotfire.png', 'double-hotfire-dark.png')
        assert not any(url.endswith(deferred) for url in requests), requests
        logo = page.locator('.home-hero__logo')
        assert logo.evaluate('i=>[i.naturalWidth,i.naturalHeight]') == [2048, 636]
        intro = page.locator('.home-team-intro__photo')
        assert intro.get_attribute('fetchpriority') == 'low'
        intro.evaluate('i=>i.decode()')
        assert intro.evaluate('i=>[i.naturalWidth,i.naturalHeight]') == ([1200, 1738] if width <= 768 else [2140, 1204])
        plot = page.locator('.home-data img[data-plot-dark-src]')
        page.emulate_media(color_scheme='dark')
        page.wait_for_function('document.querySelector(".home-data img").dataset.plotTheme==="dark"')
        assert not plot.get_attribute('src')
        plot.scroll_into_view_if_needed()
        page.wait_for_function('document.querySelector(".home-data img").dataset.homeLoaded==="true"')
        plot.evaluate('i=>i.decode()')
        assert plot.get_attribute('src').endswith('double-hotfire-dark.png')
        page.emulate_media(color_scheme='light')
        page.wait_for_function('document.querySelector(".home-data img").dataset.plotTheme==="light"')
        plot.evaluate('i=>i.decode()')
        assert plot.get_attribute('src').endswith('double-hotfire.png')
        for image in page.locator('.home-project-links img').all():
            image.scroll_into_view_if_needed()
            page.wait_for_function('(image)=>Boolean(image.getAttribute("src"))', arg=image.element_handle())
            image.evaluate('i=>i.decode()')
            assert image.evaluate('i=>i.naturalWidth>0')
        video = page.locator('.home-hotfire video')
        assert video.evaluate('v=>v.poster===new URL(v.dataset.poster,document.baseURI).href')
        assert video.evaluate('v=>v.controls&&v.preload==="none"&&v.paused')
        assert video.evaluate('v=>getComputedStyle(v).transform') == 'none'
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        print(f'Homepage startup, exact media, proximity loading and system themes passed: {width}px', flush=True)
        context.close()
    context = browser.new_context(viewport={'width': 390, 'height': 844}, java_script_enabled=False)
    page = context.new_page()
    page.goto(base + '/', wait_until='networkidle')
    assert page.locator('img[data-home-deferred-src]').evaluate_all('images=>images.every(i=>getComputedStyle(i).display==="none")')
    for image in page.locator('.home-data noscript img, .home-project-links noscript img').all():
        assert image.evaluate('i=>i.complete&&i.naturalWidth>0')
    assert 'seraphina-oct-4-poster.webp' in page.locator('.home-hotfire video').evaluate('v=>getComputedStyle(v).backgroundImage')
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    print('No-JavaScript original-image and native-video-poster fallbacks passed.', flush=True)
    context.close()
    browser.close()
