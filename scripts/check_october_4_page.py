"""Verify October homepage/card/page, themes, downloads, video and mobile layout."""
import argparse
import hashlib
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser()
parser.add_argument('--url', default='http://127.0.0.1:8894')
parser.add_argument('--output', default='/tmp/mach-oct4-browser-review')
parser.add_argument('--quick', action='store_true')
args = parser.parse_args()
out = Path(args.output)
out.mkdir(parents=True, exist_ok=True)
base = args.url.rstrip('/')
asset = '/Seraphina/oct-4-hotfire/'
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True,
                               args=['--no-sandbox', '--disable-dev-shm-usage'])
    for width in ((390,) if args.quick else (1440, 390, 320)):
        for scheme in ('light', 'dark'):
            context = browser.new_context(viewport={'width': width, 'height': 900}, color_scheme=scheme)
            page = context.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            for path in ('/', '/Seraphina/', asset, '/Seraphina/aug-20-hotfire/'):
                page.goto(base + path, wait_until='domcontentloaded')
                page.wait_for_timeout(400)
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (path, width)
                for image in page.locator('img[data-plot-dark-src]').all():
                    image.scroll_into_view_if_needed()
                    # The homepage intentionally assigns below-the-fold media
                    # after its observer sees the approaching viewport.
                    page.wait_for_function('(i)=>!i.dataset.homeDeferredSrc||i.dataset.homeLoaded==="true"', arg=image.element_handle())
                    image.evaluate('(i)=>i.decode()')
                    assert image.get_attribute('data-plot-theme') == scheme
                    assert image.get_attribute('src').endswith('-dark.png') == (scheme == 'dark')
                    parent = image.locator('xpath=..')
                    if parent.evaluate('(p)=>p.tagName') == 'A':
                        assert parent.get_attribute('href').endswith(image.get_attribute('src').split('/')[-1])
                if path == '/':
                    assert 'October 4' in page.locator('.home-hotfire__heading').inner_text()
                    assert page.locator('.showcase-video source').get_attribute('src').endswith('seraphina-oct-4-hotfire.mp4')
                    assert page.locator('.hotfire-data a, .hotfire-data button').count() == 0
                    page.locator('.showcase-video').scroll_into_view_if_needed()
                    page.screenshot(path=str(out / f'home-{width}-{scheme}.png'))
                elif path == '/Seraphina/':
                    first = page.locator('.program-test-grid article').first
                    assert first.locator('time').get_attribute('datetime') == '2026-10-04'
                    assert first.locator('time').text_content() == 'October 4, 2026'
                    assert first.locator('img').get_attribute('data-original-src').endswith('pumpkin-breaking.webp')
                    first.scroll_into_view_if_needed()
                    page.screenshot(path=str(out / f'card-{width}-{scheme}.png'))
                elif path == asset:
                    headings = page.locator('.md-content h2').all_text_contents()
                    headings = [heading.replace('\u00b6', '').strip() for heading in headings]
                    assert headings[0] == 'Test Video', headings
                    assert headings[-2:] == ['Successes', 'Lessons'], headings
                    assert page.locator('.hotfire-frame-grid img').count() == 2
                    assert page.locator('img[alt*="team photo" i]').count() == 0
                    assert page.locator('img[data-plot-dark-src]').count() == 2
                    controls = page.get_by_role('button', name='Expand plot:', exact=False)
                    assert controls.count() == 2
                    for i in range(2):
                        controls.nth(i).click()
                        dialog = page.locator('dialog[open]')
                        assert dialog.is_visible()
                        assert dialog.get_attribute('data-plot-theme') == scheme
                        assert dialog.locator('img').get_attribute('src').endswith('-dark.png') == (scheme == 'dark')
                        assert dialog.locator('[data-plot-original]').get_attribute('href') == dialog.locator('img').get_attribute('src')
                        page.keyboard.press('Escape')
                    for image in page.locator('.hotfire-frame-grid img').all():
                        image.scroll_into_view_if_needed()
                        image.evaluate('(i)=>i.decode()')
                    for y in range(0, page.evaluate('document.body.scrollHeight'), 600):
                        page.evaluate('(y)=>scrollTo(0,y)', y)
                        page.wait_for_timeout(50)
                    page.screenshot(path=str(out / f'page-{width}-{scheme}.png'), full_page=True)
                assert not errors, errors
            context.close()
            print(json.dumps({'width': width, 'scheme': scheme, 'checks': 'passed'}), flush=True)
    context = browser.new_context(viewport={'width': 1440, 'height': 900}, color_scheme='light')
    page = context.new_page()
    page.goto(base + asset, wait_until='domcontentloaded')
    page.wait_for_timeout(500)
    plot = page.locator('img[data-plot-dark-src]').last
    page.get_by_role('button', name='Expand plot:', exact=False).last.click()
    page.get_by_role('button', name='Zoom in', exact=True).click()
    page.emulate_media(color_scheme='dark')
    page.wait_for_function('()=>document.querySelector("dialog[open]")?.dataset.plotTheme === "dark"')
    assert plot.get_attribute('src').endswith('-dark.png')
    assert page.locator('dialog[open] img').get_attribute('src') == plot.get_attribute('src')
    assert page.locator('[data-plot-zoom]').inner_text() == '2×'
    page.keyboard.press('Escape')
    assert page.locator('video').count() == 3
    video = page.locator('video:has(source[src$="seraphina-oct-4-hotfire.mp4"])')
    assert video.count() == 1
    video.evaluate('(v)=>{v.muted=true;v.preload="auto";v.load()}')
    page.wait_for_function('(v)=>v.readyState>=2', arg=video.element_handle())
    video.evaluate('(v)=>v.play()')
    page.wait_for_timeout(600)
    assert video.evaluate('(v)=>v.currentTime>0 && !v.error')
    # Website edit removes 5.8 s of lead-in, keeping ~1 s before the audio onset.
    assert abs(video.evaluate('(v)=>v.duration') - 26.666667) < .1
    video.evaluate('(v)=>v.pause()')
    for name, duration in (('iphone', 18.566667), ('s10', 19.733333)):
        video = page.locator(f'video:has(source[src$="seraphina-oct-4-{name}.mp4"])')
        assert video.count() == 1
        assert video.get_attribute('controls') is not None
        assert video.get_attribute('playsinline') is not None
        assert video.get_attribute('autoplay') is None
        assert video.get_attribute('preload') == 'none'
        assert video.get_attribute('poster')
        video.scroll_into_view_if_needed()
        bounds = video.bounding_box()
        assert abs(bounds['width'] / bounds['height'] - 16 / 9) < .01
        assert video.evaluate('(v)=>getComputedStyle(v).transform') == 'none'
        video.evaluate('(v)=>{v.muted=true;v.preload="auto";v.load()}')
        page.wait_for_function('(v)=>v.readyState>=2', arg=video.element_handle())
        video.evaluate('(v)=>v.play()')
        page.wait_for_timeout(600)
        assert video.evaluate('(v)=>v.currentTime>0 && !v.error')
        assert video.evaluate('(v)=>v.videoWidth===1920 && v.videoHeight===1080')
        assert abs(video.evaluate('(v)=>v.duration') - duration) < .005
        video.evaluate('(v)=>v.pause()')
    expected = {
        'seraphina-2026-10-04-test-data.csv': 'e1a6491162f0ca62c1e1094f125f1274c6ba1086f864d4f869b0d355cf8e416d',
        'seraphina-2026-10-04-startup.csv': '835ca8a805061dd2c2d9da14fdfd604a83ac269b915b9144bd57fbb4f2323868',
    }
    for name, digest in expected.items():
        response = context.request.get(base + asset + name)
        assert response.ok and hashlib.sha256(response.body()).hexdigest() == digest
    response = context.request.get(base + asset + 'seraphina-oct-4-hotfire.mp4', headers={'Range': 'bytes=0-1023'})
    assert response.status in (200, 206)
    print('Open-viewer theme switching, video playback and original CSV checksums passed', flush=True)
    context.close()
    browser.close()
