#!/usr/bin/env python3
"""Stress real same-document navigation back to home and its lower media."""
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser()
parser.add_argument('--url', default='http://127.0.0.1:8876')
parser.add_argument('--webkit', action='store_true')
parser.add_argument('--webkit-executable')
parser.add_argument('--quick', action='store_true')
parser.add_argument('--output', default='/tmp/mach-home-navigation')
args = parser.parse_args()
base = args.url.rstrip('/')
out = Path(args.output)
out.mkdir(parents=True, exist_ok=True)

with sync_playwright() as playwright:
    browser = (playwright.webkit.launch(**({'executable_path': args.webkit_executable} if args.webkit_executable else {}))
               if args.webkit else playwright.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox']))
    widths = (390, 1440) if args.quick else (320, 390, 599, 600, 1440)
    for width in widths:
        for start in ('/team/', '/'):
            context = browser.new_context(viewport={'width': width, 'height': 844},
                                          color_scheme='dark' if width < 600 else 'light')
            page = context.new_page()
            errors, documents = [], []
            page.on('pageerror', lambda error: errors.append(str(error)))
            if not args.webkit:
                cdp = context.new_cdp_session(page)
                cdp.send('Network.enable')
                cdp.on('Network.requestWillBeSent', lambda event: documents.append(event['request']['url']) if event['type'] == 'Document' else None)
            page.goto(base + start, wait_until='networkidle')
            page.evaluate('window.__machNavigationIdentity="same-original-document"')

            def confirm_same_document():
                assert page.evaluate('window.__machNavigationIdentity') == 'same-original-document'
                if not args.webkit:
                    assert len(documents) == 1, documents

            def top_link(name, route):
                if width < 600:
                    page.locator('[data-mach-drawer-toggle]').click()
                page.get_by_role('link', name=name, exact=True).click()
                page.wait_for_url(base + route)
                page.wait_for_function('route=>document.querySelector("link[rel=canonical]").href.endsWith(route)', arg=route)
                confirm_same_document()

            def return_home():
                page.locator('.md-header [data-md-component="logo"]').click()
                page.wait_for_url(base + '/')
                page.wait_for_selector('.home-hero')
                confirm_same_document()

            def check_home(label):
                page.wait_for_function('document.documentElement.classList.contains("js")')
                plot = page.locator('.home-data img[data-home-deferred-src]')
                plot.scroll_into_view_if_needed()
                page.wait_for_function('i=>i.dataset.homeLoaded==="true"', arg=plot.element_handle())
                plot.evaluate('i=>i.decode()')
                assert plot.is_visible() and plot.bounding_box()['width'] > 100
                for dark in (True, False):
                    page.emulate_media(color_scheme='dark' if dark else 'light')
                    page.wait_for_function('dark=>document.querySelector(".home-data img").dataset.plotTheme===(dark?"dark":"light")', arg=dark)
                    plot.evaluate('i=>i.decode()')
                    assert plot.get_attribute('src').endswith('-dark.png') == dark
                images = page.locator('.home-project-links a > img')
                assert images.count() == 3
                for image in images.all():
                    image.scroll_into_view_if_needed()
                    page.wait_for_function('i=>Boolean(i.getAttribute("src"))', arg=image.element_handle())
                    image.evaluate('i=>i.decode()')
                    assert image.is_visible() and image.bounding_box()['width'] >= 44
                assert page.locator('noscript').evaluate_all('elements=>elements.every(e=>getComputedStyle(e).display==="none")')
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                page.screenshot(path=str(out / f'{width}-{start.strip("/") or "home"}-{label}.png'))
                confirm_same_document()

            if start == '/':
                top_link('Team', '/team/')
            return_home()
            check_home('first-return')
            top_link('SPRINT', '/SPRINT/')
            page.locator('.project-cards a[href$="electronics/"]').first.click()
            page.wait_for_url(base + '/SPRINT/electronics/')
            confirm_same_document()
            top_link('Team', '/team/')
            top_link('Seraphina', '/Seraphina/')
            return_home()
            check_home('project-return')
            top_link('Team', '/team/')
            page.go_back()
            page.wait_for_url(base + '/')
            page.wait_for_selector('.home-hero')
            check_home('back')
            page.go_forward()
            page.wait_for_url(base + '/team/')
            return_home()
            check_home('forward-return')
            assert not errors, errors
            print(f'Actual same-document click/Back/Forward/theme/media checks passed: {width}px, initial {start}', flush=True)
            context.close()
    browser.close()
