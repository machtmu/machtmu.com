#!/usr/bin/env python3
"""Check responsive team framing, image delivery and navigation at crop breakpoints."""
import argparse
import hashlib
import io
import json
from pathlib import Path

from PIL import Image, ImageStat
from playwright.sync_api import sync_playwright


NAMES = ['Julia Puszynska', 'Tobechukwu Okoh', 'Samuel Li',
         'Jonathan Al-Hinn', 'Kasper Pajak', 'Madison Warren']
LANDMARKS = json.loads(Path(__file__).with_name('team_portrait_landmarks.json').read_text())


def check(page, base, width):
    page.goto(base + '/team/', wait_until='domcontentloaded')
    images = page.locator('.team-portrait img')
    assert images.count() == 6
    for image in images.all():
        image.scroll_into_view_if_needed()
        image.evaluate('i => i.decode()')
    assert page.locator('.team-portrait-caption strong').all_text_contents() == NAMES
    assert page.locator('.former-member-card').count() == 24
    measurements = images.evaluate_all('''(images, landmarks) => images.map(i => {
      const card = i.closest('.team-portrait');
      const r = card.getBoundingClientRect(), b = i.getBoundingClientRect();
      const style = getComputedStyle(card), imageStyle = getComputedStyle(i);
      const size = i.sizes.split(',').map(s => s.trim()).find(s => {
        const media = s.match(/^(\\(max-width:\\s*\\d+px\\))/);
        return !media || matchMedia(media[1]).matches;
      }).replace(/^\\(max-width:\\s*\\d+px\\)\\s*/, '');
      const probe = document.createElement('span');
      probe.style.cssText = 'position:fixed;visibility:hidden;display:block;width:'+size;
      document.body.appendChild(probe);
      const advertisedWidth = probe.getBoundingClientRect().width;
      probe.remove();
      const center = parseFloat(style.getPropertyValue('--portrait-subject-center')) / 100;
      const eye = -parseFloat(style.getPropertyValue('--portrait-eye-lift')) / 100;
      const measured = landmarks.portraits.find(p => p.name === i.alt);
      const sourceY = y => (b.top + y/measured.height*b.height - r.top)/r.height;
      const captionTop = (card.querySelector('.team-portrait-caption strong').getBoundingClientRect().top-r.top)/r.height;
      return {name:i.alt, source:i.currentSrc, native:i.dataset.originalSrc,
        complete:i.complete && i.naturalWidth>0,
        declaredWidth:Number(i.dataset.portraitDelivery),
        cssWidth:parseFloat(style.getPropertyValue('--portrait-width')),
        scale:parseFloat(style.getPropertyValue('--portrait-scale')),
        ratio:r.width/r.height, imageRatio:b.width/b.height,
        sourceRatio:Number(i.getAttribute('width'))/Number(i.getAttribute('height')),
        cover:[b.left-r.left,b.top-r.top,b.right-r.right,b.bottom-r.bottom],
        subjectX:(b.left+center*b.width-r.left)/r.width,
        eyeY:(b.top+eye*b.height-r.top)/r.height,
        expectedEye:parseFloat(style.getPropertyValue('--portrait-eye-line') || '35')/100,
        crownY:sourceY(measured.crown_y), chinY:sourceY(measured.chin_y),
        measuredHeadHeight:(measured.chin_y-measured.crown_y)/measured.height*b.height/r.height,
        measuredEyesY:sourceY(measured.eyes_y), captionTop,
        filter:imageStyle.filter,
        expectedWidth:r.width*parseFloat(style.getPropertyValue('--portrait-width'))/100*
          parseFloat(style.getPropertyValue('--portrait-scale')),
        renderedWidth:b.width,
        advertisedWidth,
        scrollbar:innerWidth-document.documentElement.getBoundingClientRect().width,
        captionFits:card.querySelector('.team-portrait-caption').scrollWidth <= r.width+1};
    })''', LANDMARKS)
    for entry in measurements:
        assert entry['complete'], entry
        assert entry['declaredWidth'] == entry['cssWidth'], entry
        assert abs(entry['renderedWidth'] - entry['expectedWidth']) < 1, entry
        # sizes describes overlay-scrollbar/mobile layout. A desktop layout
        # scrollbar can reduce the actual tile by a bounded few pixels.
        allowance = entry['scrollbar'] * entry['cssWidth']/100 * entry['scale'] / (2 if width <= 760 else 3)
        assert -1.5 < entry['advertisedWidth']-entry['renderedWidth'] < allowance+1.5, entry
        assert abs(entry['ratio'] - (.8 if width <= 760 else 1)) < .005, entry
        assert abs(entry['imageRatio'] - entry['sourceRatio']) < .006, entry
        # Every source must cover the crop: avoid artificial empty strips
        # when moving an off-centre subject towards the centre of the tile.
        left, top, right, bottom = entry['cover']
        assert left <= 1 and top <= 1 and right >= -1 and bottom >= -1, entry
        assert abs(entry['subjectX'] - .5) < .005, entry
        assert abs(entry['eyeY'] - entry['expectedEye']) < .005, entry
        # Independent native-pixel landmarks, not CSS zoom values, define the
        # equal visual head size. Check the actual rendered source geometry.
        assert abs(entry['measuredHeadHeight'] - LANDMARKS['target_card_height']) < .003, entry
        assert abs(entry['crownY'] - LANDMARKS['crown_margin']) < .003, entry
        assert abs(entry['measuredEyesY'] - entry['expectedEye']) < .003, entry
        assert entry['captionTop'] - entry['chinY'] > .015, entry
        assert entry['filter'] == 'none', entry
        assert entry['captionFits'], entry
    assert max(e['measuredHeadHeight'] for e in measurements)-min(e['measuredHeadHeight'] for e in measurements) < .003
    for image in page.locator('.former-member-avatar').all():
        image.scroll_into_view_if_needed()
        image.evaluate('i => i.decode()')
        assert image.evaluate('i => i.complete && i.naturalWidth > 0')
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    # The same portraits must decode after instant navigation back to Team.
    page.locator('.md-logo').first.click()
    page.wait_for_url(base + '/')
    # A new URL can arrive before the replacement document/instant-navigation
    # content. In WebKit, a second goto at that point interrupts the first.
    page.locator('.home-hero').wait_for(state='visible')
    page.wait_for_load_state('domcontentloaded')
    page.locator('.md-tabs a[href$="team/"]').first.click() if width >= 768 else page.goto(base + '/team/', wait_until='domcontentloaded')
    page.wait_for_url(base + '/team/')
    page.locator('.team-leads').wait_for(state='visible')
    for image in page.locator('.team-portrait img').all():
        image.scroll_into_view_if_needed()
        image.evaluate('i => i.decode()')
    for card in page.locator('.team-portrait').all():
        card.scroll_into_view_if_needed()
        page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
        # decode() can finish before an image paints after instant navigation.
        # Confirm the actual face-area bitmap is not just the grey backdrop.
        bitmap = Image.open(io.BytesIO(card.screenshot(
            animations='disabled', style='.md-header{visibility:hidden!important}'))).convert('RGB')
        w, h = bitmap.size
        area = bitmap.crop((int(w*.3), int(h*.2), int(w*.7), int(h*.6)))
        assert max(ImageStat.Stat(area).stddev) > 15, card.get_attribute('class')
    return measurements


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8886')
    parser.add_argument('--browser', choices=('chromium', 'webkit'), default='chromium')
    parser.add_argument('--webkit-executable', help='Optional local WebKit runtime override.')
    parser.add_argument('--output', type=Path, default=Path('/tmp/mach-team-portrait-review'))
    parser.add_argument('--quick', action='store_true')
    parser.add_argument('--widths', type=int, nargs='+')
    parser.add_argument('--scheme', choices=('light', 'dark', 'both'), default='both')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    for source in LANDMARKS['portraits']:
        path = root/'docs/assets/images/leads'/source['file']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == source['sha256'], source['name']
        with Image.open(path) as image:
            assert image.size == (source['width'], source['height']), source['name']
    args.output.mkdir(parents=True, exist_ok=True)
    results = []
    with sync_playwright() as p:
        browser = p.webkit.launch(**({'executable_path': args.webkit_executable} if args.webkit_executable else {})) if args.browser == 'webkit' else p.chromium.launch(
            executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        for width in (args.widths or ((390, 1440) if args.quick else (320, 390, 600, 601, 760, 761, 1440))):
            for scheme in (('light', 'dark') if args.scheme == 'both' else (args.scheme,)):
                context = browser.new_context(viewport={'width': width, 'height': 950},
                                              color_scheme=scheme,
                                              device_scale_factor=3 if width <= 600 else 1)
                page = context.new_page()
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                measurements = check(page, args.url.rstrip('/'), width)
                page.locator('.team-leads').screenshot(
                    path=str(args.output / f'{args.browser}-{width}-{scheme}.png'),
                    animations='disabled', style='.md-header{visibility:hidden!important}')
                if width == 1440 and scheme == 'light':
                    page.locator('.former-members-grid').screenshot(
                        path=str(args.output / f'{args.browser}-former-leads.png'),
                        animations='disabled', style='.md-header{visibility:hidden!important}')
                assert not errors, errors
                results.append({'width': width, 'scheme': scheme, 'portraits': measurements})
                context.close()
        browser.close()
    (args.output / f'{args.browser}.json').write_text(json.dumps(results, indent=2))
    print(f'{args.browser}: {len(results)} responsive framing/navigation checks passed.')


if __name__ == '__main__':
    main()
