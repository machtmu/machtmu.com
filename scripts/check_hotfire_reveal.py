#!/usr/bin/env python3
"""Private-preview checks for the home relight panel; no published writes."""
import argparse
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser()
parser.add_argument('--url', default='http://127.0.0.1:8886')
parser.add_argument('--webkit', action='store_true')
args = parser.parse_args()
base = args.url.rstrip('/')

with sync_playwright() as p:
    browser = (p.webkit.launch(executable_path='/home/zeul/.cache/ms-playwright/webkit-2248/minibrowser-wpe/bin/MiniBrowser')
               if args.webkit else p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox']))
    for width, touch, motion in [(1440, False, 'no-preference'), (390, True, 'no-preference'),
                                  (1440, False, 'reduce'), (320, True, 'reduce')]:
        context = browser.new_context(viewport={'width': width, 'height': 900},
                                      is_mobile=touch, has_touch=touch, reduced_motion=motion)
        page = context.new_page()
        errors = []
        poster_requests = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('request', lambda request: poster_requests.append(request.url) if request.url.endswith('/seraphina-oct-4-poster.webp') else None)
        page.goto(base + '/', wait_until='domcontentloaded')
        panel = page.locator('.home-hotfire')
        video = panel.locator('video')
        page.wait_for_function('document.querySelector(".home-hotfire")?.dataset.playing==="false"')
        if video.bounding_box()['y'] >= 1000:
            page.wait_for_timeout(150)
            assert not poster_requests and not video.get_attribute('poster'), poster_requests
        assert page.evaluate('document.querySelector(".home-team-intro").nextElementSibling===document.querySelector(".home-hotfire")')
        video.scroll_into_view_if_needed()
        page.wait_for_function('''()=>{const video=document.querySelector('.home-hotfire video');return video.poster===new URL(video.dataset.poster,document.baseURI).href;}''')
        video.evaluate('''async video=>{const image=new Image();image.src=video.poster;await image.decode();return image.naturalWidth>0;}''')
        assert video.evaluate('v=>v.poster===new URL(v.dataset.poster,document.baseURI).href')
        assert len(poster_requests) == 1, poster_requests
        page.mouse.move(0, 0)
        page.wait_for_function('getComputedStyle(document.querySelector(".home-hotfire video")).filter==="grayscale(1)"')
        assert video.evaluate('v=>v.paused&&!v.autoplay&&v.controls&&v.preload==="none"')
        frame = page.locator('.home-hotfire__frame').bounding_box()
        assert abs(frame['width'] - page.locator('.home-team-intro').bounding_box()['width']) < 1
        assert abs(frame['width'] / frame['height'] - 16 / 9) < .01
        native_box = video.bounding_box()

        def check_content_only_zoom():
            assert video.evaluate('v=>getComputedStyle(v).transform') == 'none'
            assert video.evaluate('v=>getComputedStyle(v,"::-webkit-media-controls").transform') == 'none'
            box = video.bounding_box()
            assert abs(box['width']-native_box['width']) < 1 and abs(box['height']-native_box['height']) < 1
            page.wait_for_function('''()=>{
              const v=document.querySelector('.home-hotfire video'),panel=v.closest('.home-hotfire'),s=getComputedStyle(v);
              if(!CSS.supports('object-view-box','inset(1%)'))return !s.objectViewBox||s.objectViewBox==='none';
              const active=panel.dataset.revealed==='true'||panel.dataset.playing==='true'||v.matches(':focus-visible')||(matchMedia('(hover:hover) and (pointer:fine)').matches&&panel.matches(':hover'));
              const expected=matchMedia('(prefers-reduced-motion:reduce)').matches||!active?0:1.22;
              return Math.abs(parseFloat(s.objectViewBox.replace(/^inset\\(/,''))-expected)<.001;
            }''')

        check_content_only_zoom()
        if touch:
            video.tap(position={'x': width / 2, 'y': 35})
        else:
            video.hover()
        page.wait_for_function('getComputedStyle(document.querySelector(".home-hotfire video")).filter==="grayscale(0)"')
        # Only the replaced picture can crop; native controls and their element
        # never scale, including unsupported WebKit and reduced-motion modes.
        check_content_only_zoom()
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        if not touch:
            page.mouse.move(0, 0)
            page.wait_for_function('getComputedStyle(document.querySelector(".home-hotfire video")).filter==="grayscale(1)"')
            # Keyboard users receive the same reveal without a mouse.
            video.focus()
            page.keyboard.press('Tab')
            page.keyboard.press('Shift+Tab')
            page.wait_for_function('getComputedStyle(document.querySelector(".home-hotfire video")).filter==="grayscale(0)"')
        # Playback must stay in colour even when a pointer leaves the panel.
        if args.webkit:
            # Linux WPE may lack the MP4 decoder available in Safari. Exercise
            # the playback observer independently; Chromium below decodes and
            # plays the actual source with native controls.
            video.evaluate('v=>{Object.defineProperty(v,"paused",{configurable:true,get:()=>false});v.dispatchEvent(new Event("play"));}')
        else:
            video.evaluate('''async v=>{v.muted=true;await Promise.race([v.play(),new Promise((_,reject)=>setTimeout(()=>reject(new Error('Playback did not start')),10000))]);}''')
        page.wait_for_function('document.querySelector(".home-hotfire").dataset.playing==="true"')
        assert panel.get_attribute('data-playing') == 'true'
        page.mouse.move(0, 0)
        page.wait_for_function('getComputedStyle(document.querySelector(".home-hotfire video")).filter==="grayscale(0)"')
        check_content_only_zoom()
        if args.webkit:
            video.evaluate('v=>{v.pause();delete v.paused;v.dispatchEvent(new Event("pause"));}')
        else:
            video.evaluate('v=>v.pause()')
        page.wait_for_function('document.querySelector(".home-hotfire").dataset.playing==="false"')
        assert panel.get_attribute('data-playing') == 'false'
        if not args.webkit:
            assert panel.get_attribute('data-controls-ready') == 'true'
        check_content_only_zoom()
        # Telemetry and the shared team assets must not inherit video styling.
        assert page.locator('.hotfire-data img').evaluate('e=>getComputedStyle(e).filter') == 'none'
        assert page.locator('.home-team-intro__photo').evaluate('e=>getComputedStyle(e).filter') == 'grayscale(1)'
        page.locator('.home-project-links a[href$="Seraphina/"]').click()
        page.wait_for_url(base + '/Seraphina/')
        page.go_back()
        page.wait_for_url(base + '/')
        page.wait_for_function('document.querySelector(".home-hotfire")?.dataset.playing==="false"')
        assert not errors, errors
        print(f'Relight reveal, layout, controls and navigation passed: {width}px, touch={touch}, motion={motion}', flush=True)
        context.close()
    browser.close()
