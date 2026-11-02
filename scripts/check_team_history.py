#!/usr/bin/env python3
"""Keep historical profiles aligned and roles scoped to the right people."""
import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright
from build_member_avatars import AVATARS
from build_team_role_timelines import load_data, role_lines
from build_team_profile_links import load_links
from build_team_member_summaries import load_summaries, summary_text


ROLES = {
    "Adam Oudeh": "Structures Lead",
    "Aditya Shinde": "Software & Propulsion Engineer",
    "Antonella Ruta": "Combustion Dynamics Lead",
    "Anuja Thurairajah": "Director of Media & Logistics",
    "Audrey Abergel-Preston": "Chief Engineer",
    "Balin Moher": "Co-founder & Director",
    "Ben Kubica": "Propulsion Lead",
    "Daniel Ibanescu": "Telemetry & Control Software Lead",
    "David Machuca": "Lead Engineer – Propellant Management",
    "Evan Bhogal": "Electrical Lead",
    "Farhan Raza": "Senior Mechanical Engineer – Propellant Management",
    "Georgia Jovanovic": "Telemetry & Control Lead",
    "Jack Sinclair": "Chief Safety Officer",
    "Juliano Sciabbarrasi": "Propulsion Dynamics Lead",
    "Kai Stewart": "Telemetry & Control Hardware Lead",
    "Leandro Tomarchio": "Structures Lead",
    "Mark Paul": "Telemetry & Control Software Lead",
    "Matthew Ho": "Captain",
    "Milad Hemmat": "Media Lead",
    "Nikolai Sydorenko": "Combustion Dynamics Lead",
    "Orion Moore": "Combustion Dynamics Lead",
    "Rochelle Suarez-Tapanes": "Propellant Management Lead",
    "Rui Fernandes": "Propellant Management Member / Lead",
    "Shivesh Maraj": "Captain",
    "Umar Shabbir": "Captain",
    "William Pirie": "Captain",
    "Yiwei Luo": "Technical Director",
    "Zak Harrison": "Co-founder · Captain",
    "Zeul Mordasiewicz": "Captain",
}
ADDED = ['Balin Moher', 'Zak Harrison', 'David Machuca', 'Antonella Ruta', 'Farhan Raza', 'Matthew Ho']
# Identity/photo availability is unchanged by native-quality replacements.
EXPECTED_FORMER_PHOTOS = 25


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8886')
    parser.add_argument('--output', type=Path, default=Path('/tmp/mach-team-history'))
    parser.add_argument('--widths', type=int, nargs='+', default=[320, 390, 768, 1440])
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    timeline_data = load_data()
    profile_links = load_links()
    summaries = {p['name']: p for p in load_summaries()['people']}
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        for width in args.widths:
            for scheme in ('light', 'dark'):
                page = browser.new_page(viewport={'width': width, 'height': 950}, color_scheme=scheme,
                                        device_scale_factor=3 if width <= 600 else 1)
                errors = []
                failed = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.on('response', lambda response: failed.append([response.status, response.url])
                        if response.status >= 400 and response.url.startswith(args.url.rstrip('/') + '/') else None)
                page.goto(args.url.rstrip('/') + '/team/', wait_until='networkidle')
                cards = page.locator('.former-member-card')
                assert cards.count() == 30
                names = cards.locator('strong').all_text_contents()
                assert len(set(names)) == 30
                assert set(names) == set(ROLES) | {'Antonella Ruta', 'David Machuca', 'Dmitriy Leminov', 'Farhan Raza'}
                assert page.locator('.former-members-grid').count() == 1
                assert page.locator('.early-members-grid').count() == 0
                assert page.get_by_role('heading', name='Founders and early members', exact=True).count() == 0
                assert all(names.count(name) == 1 for name in ADDED)
                assert names == sorted(names, key=str.casefold)
                assert names.count('Orion Moore') == 1
                assert page.locator('.former-member-card--text-only').count() == 0
                assert page.get_by_role('heading', name='Former Leads', exact=True).count() == 1
                expected_lines = {name: [summary_text(summaries[name], compact=True)] for name in names}
                assert cards.locator('small').count() == sum(map(len, expected_lines.values()))
                assert cards.locator('.former-member-initials').count() == 30 - EXPECTED_FORMER_PHOTOS
                assert cards.locator('img').count() == EXPECTED_FORMER_PHOTOS
                assert 'Founder' not in cards.locator('small').all_text_contents()
                assert page.locator('a.former-member-card, .former-member-card a a').count() == 0
                assert cards.locator('.former-member-link--linkedin').count() == 28
                assert cards.locator('.former-member-link--website').count() == 4
                for card in cards.all():
                    card.scroll_into_view_if_needed()
                    for image in card.locator('img').all():
                        image.evaluate('i=>i.decode()')
                    name = card.locator('strong').inner_text()
                    assert card.evaluate('c=>c.tagName') == 'DIV'
                    assert card.get_attribute('href') is None
                    assert card.locator('.former-member-details').count() == 1
                    role = card.locator('small')
                    expanded = summary_text(summaries[name], compact=True)
                    for short, full in [('T&C Lead', 'Telemetry and Control Lead'),
                                        ('PM Lead', 'Propellant Management Lead'),
                                        ('Tech. Director', 'Technical Director')]:
                        if expanded.startswith(short):
                            expanded = full + expanded[len(short):]
                    assert role.all_text_contents() in (expected_lines[name], [summary_text(summaries[name])], [expanded])
                    assert role.evaluate('''s=>{
                      const text=s.textContent, font=s.style.fontSize;
                      s.style.fontSize='';
                      const range=document.createRange();let preferred;
                      for(const candidate of new Set([s.dataset.fullSummary,s.dataset.expandedSummary,s.dataset.compactSummary])){
                        preferred=candidate;s.textContent=candidate;range.selectNodeContents(s);
                        if(range.getBoundingClientRect().width*.9<=s.clientWidth-.5)break;
                      }
                      s.textContent=text;s.style.fontSize=font;
                      return text===preferred;
                    }'''), name
                    expected_links = [(kind, profile_links[name][kind]) for kind in ('website', 'linkedin')
                                      if profile_links[name][kind]]
                    active_card = card
                    if width <= 760:
                        for link in card.locator('.former-member-link').all():
                            assert link.is_visible()
                            assert link.evaluate('''a=>{
                              const r=a.getBoundingClientRect(),p=a.closest('.former-member-card').getBoundingClientRect();
                              return r.width>=24&&r.height>=24&&r.right>=p.right-4&&r.bottom<=p.bottom&&
                                document.elementFromPoint(r.x+r.width/2,r.y+r.height/2).closest('a')===a;
                            }'''), name
                            assert link.locator('svg').evaluate('s=>{const r=s.getBoundingClientRect(),w=s.closest(".former-member-card").getBoundingClientRect().width,n=Math.min(16,Math.max(8,w*.09));return Math.abs(r.width-n)<.05&&Math.abs(r.height-n)<.05}')
                            assert link.evaluate('a=>{const s=getComputedStyle(a,"::before"),w=a.closest(".former-member-card").getBoundingClientRect().width,n=Math.min(16,Math.max(8,w*.09))*1.4;return Math.abs(parseFloat(s.width)-n)<.05&&Math.abs(parseFloat(s.height)-n)<.05}')
                        opener = card.locator('.former-member-open')
                        assert opener.is_visible() and opener.get_attribute('aria-haspopup') == 'dialog'
                        assert card.locator('.former-member-details').is_visible()
                        opener.click()
                        active_card = page.locator('dialog.former-member-dialog[open]')
                        assert active_card.count() == 1
                        assert active_card.locator('strong').inner_text() == name
                        assert active_card.locator('small').all_text_contents() == [summary_text(summaries[name])]
                        assert all(s.is_visible() for s in active_card.locator('small').all())
                        assert active_card.locator('button a, a button, button button').count() == 0
                        assert active_card.locator('.former-member-close').evaluate('a=>{const r=a.getBoundingClientRect();return r.width>=44&&r.height>=44}')
                        assert active_card.locator('.former-member-overlay').evaluate('''o=>{
                          const p=o.closest('.former-member-portrait').getBoundingClientRect(),r=o.getBoundingClientRect();
                          return r.top>=p.top&&r.bottom<=p.bottom+1&&o.scrollWidth<=o.clientWidth+1;
                        }''')
                    links = active_card.locator('.former-member-link')
                    assert links.count() == len(expected_links)
                    assert active_card.locator('.former-member-links').count() == bool(expected_links)
                    if expected_links:
                        assert active_card.locator('.former-member-links').evaluate('''g=>{
                          const card=g.closest('.former-member-card,.former-member-viewer'),r=g.getBoundingClientRect();
                          const p=card.querySelector('.former-member-portrait').getBoundingClientRect(),a=card.getBoundingClientRect();
                          const text=card.querySelector('.former-member-details').getBoundingClientRect();
                          return r.height>=44&&r.top>=p.top&&r.bottom<=p.bottom&&
                            Math.abs(r.bottom-(p.bottom-4))<1&&r.left>=text.right&&r.right<=p.right;
                        }'''), name
                    for link, (kind, url) in zip(links.all(), expected_links):
                        label = f"{name}'s {'website' if kind == 'website' else 'LinkedIn'}"
                        assert link.get_attribute('href') == url
                        assert link.get_attribute('aria-label') == label and link.get_attribute('title') == label
                        assert link.get_attribute('target') == '_blank'
                        assert {'noopener', 'noreferrer'} <= set(link.get_attribute('rel').split())
                        svg = link.locator('svg')
                        assert svg.count() == 1 and svg.is_visible()
                        assert svg.get_attribute('aria-hidden') == 'true'
                        assert svg.get_attribute('focusable') == 'false'
                        assert link.evaluate("a=>getComputedStyle(a).color==='rgb(255, 255, 255)'")
                        assert link.evaluate('a=>{const r=a.getBoundingClientRect();return r.width>=44&&r.height>=44}')
                        assert svg.evaluate('s=>{const r=s.getBoundingClientRect(),w=s.closest(".former-member-card,.former-member-viewer").getBoundingClientRect().width,n=Math.min(16,Math.max(8,w*.09));return Math.abs(r.width-n)<.05&&Math.abs(r.height-n)<.05}')
                        page.keyboard.press('Tab')
                        link.focus()
                        assert link.evaluate('a=>getComputedStyle(a).outlineStyle') != 'none'
                        assert float(link.evaluate('a=>parseFloat(getComputedStyle(a).outlineWidth)')) >= 2
                        link.evaluate('a=>a.blur()')
                    if width <= 760:
                        page.keyboard.press('Escape')
                        assert not active_card.is_visible()
                        assert opener.evaluate('b=>document.activeElement===b')
                    if not card.locator('img').count():
                        assert card.locator('.former-member-initials').count() == 1
                        assert card.locator('.former-member-initials').get_attribute('aria-hidden') == 'true'
                    photo = next((entry for entry in AVATARS if entry['name'] == name), None)
                    if photo:
                        image = card.locator('img')
                        assert image.count() == 1
                        assert (image.get_attribute('data-original-src') or image.get_attribute('src')).endswith('/' + photo['output'].removeprefix('docs/'))
                        # Larger square tiles honestly retain native small portraits;
                        # no fabricated3x-resolution assertion or asset upscaling.
                        assert image.evaluate('i=>i.naturalWidth>0&&i.naturalHeight>0')
                        assert image.evaluate('i=>i.src').startswith(args.url.rstrip('/') + '/')
                        slug = name.casefold().replace(' ', '-')
                        card.screenshot(path=str(args.output / f'{width}-{scheme}-{slug}.png'),
                                        animations='disabled', style='.md-header{visibility:hidden!important}')
                    if name == 'Matthew Ho':
                        assert card.locator('.former-member-link--linkedin').get_attribute('href') == 'https://ca.linkedin.com/in/m1ho'
                    if name == 'Orion Moore':
                        assert card.locator('.former-member-link--linkedin').get_attribute('href') == 'https://www.linkedin.com/in/orion-moore/'
                        assert card.locator('.former-member-initials').count() == 1
                metrics = cards.evaluate_all('''async cards=>Promise.all(cards.map(async c=>{
                  const r=c.getBoundingClientRect(), d=c.querySelector('.former-member-details').getBoundingClientRect();
                  const portrait=c.querySelector('.former-member-portrait');
                  const a=portrait.getBoundingClientRect();
                  const strong=c.querySelector('strong').getBoundingClientRect();
                  const name=c.querySelector('.former-member-name');
                  const n=name.getBoundingClientRect();
                  const overlay=c.querySelector('.former-member-overlay'),o=overlay.getBoundingClientRect();
                  const socials=c.querySelector('.former-member-links');
                  const f=socials&&getComputedStyle(socials).display!=='none'?socials.getBoundingClientRect():null;
                  const compact=window.innerWidth<=760;
                  const roles=[...c.querySelectorAll('small')].map(s=>s.getBoundingClientRect());
                  const image=portrait.querySelector('img'),i=image?.getBoundingClientRect();
                  // naturalWidth on a srcset element is density-corrected.
                  // Decode the selected URL alone to measure real bitmap pixels.
                  const bitmap=image?new Image():null;
                  if(bitmap){bitmap.src=image.currentSrc;await bitmap.decode();}
                  const initials=portrait.querySelector('.former-member-initials');
                  const style=getComputedStyle(c),font=parseFloat(getComputedStyle(c.querySelector('strong')).fontSize);
                  return {name:c.querySelector('strong').textContent,compact,portrait:[a.width,a.height],
                    border:parseFloat(style.borderTopWidth),shadow:style.boxShadow,
                    overflow:c.scrollWidth>c.clientWidth+1,
                    allInfoInside:Math.abs(r.bottom-a.bottom)<1&&(!f||f.bottom<=a.bottom&&a.bottom-f.bottom<=4.1&&f.top>=a.top&&f.left>=d.right)&&o.top>=a.top&&o.bottom<=a.bottom+1&&
                      roles.every((role,index)=>role.left>=a.left&&role.right<=a.right&&
                        role.top>=(index?roles[index-1].bottom:n.bottom)-1&&role.bottom<=a.bottom+1),
                    roleFits:[...c.querySelectorAll('small')].every(s=>s.scrollWidth<=s.clientWidth+1),
                    roleFont:[...c.querySelectorAll('small')].every(s=>parseFloat(getComputedStyle(s).fontSize)>(window.innerWidth<=360?4:5)),
                    roleMaxFont:Math.max(...[...c.querySelectorAll('small')].map(s=>parseFloat(getComputedStyle(s).fontSize))),
                    overlayHeight:o.height,
                    singleLines:[c.querySelector('strong'),...c.querySelectorAll('small')].every(s=>{
                      const r=document.createRange();r.selectNodeContents(s);
                      const t=r.getBoundingClientRect();
                      return t.left>=a.left&&t.right<=a.right+1&&t.width<=s.clientWidth+1&&s.getBoundingClientRect().height<=parseFloat(getComputedStyle(s).lineHeight)+1;
                    }),
                    whiteText:[c.querySelector('strong'),...c.querySelectorAll('small')].every(s=>getComputedStyle(s).color==='rgb(255, 255, 255)'&&getComputedStyle(s).opacity==='1'),
                    clearPortrait:(o.top-a.top)/a.height,
                    nameInside:n.left>=a.left-1&&n.right<=a.right+1&&n.top>=a.top&&n.bottom<=a.bottom+1,
                    nameFits:name.scrollWidth<=name.clientWidth+1&&strong.bottom<=a.bottom+1,
                    nameFont:font,nameHeight:n.height/a.height,
                    imageCovers:!image||(i.left<=a.left+1&&i.top<=a.top+1&&i.right>=a.right-1&&i.bottom>=a.bottom-1),
                    native:image?[Number(image.getAttribute('width'))||bitmap.naturalWidth,Number(image.getAttribute('height'))||bitmap.naturalHeight]:null,
                    deliveredPixels:bitmap?[bitmap.naturalWidth,bitmap.naturalHeight]:null,
                    sourceDensity:bitmap?Math.min(bitmap.naturalWidth/i.width,bitmap.naturalHeight/i.height):null,
                    squareInitials:!initials||Math.abs(initials.getBoundingClientRect().width-a.width)<1,
                    squareRadius:parseFloat(getComputedStyle(portrait).borderRadius)};
                }))''')
                for m in metrics:
                    assert abs(m['portrait'][0]-m['portrait'][1])<1 and m['portrait'][0]>70, m
                    assert not m['overflow'] and m['allInfoInside'] and m['roleFits'] and m['nameInside'] and m['nameFits'], m
                    # User explicitly chose tiny single-line labels in the
                    # three-column phone grid beside real24px link targets.
                    # Only <=360px compact tiles relax the former5px floor;
                    # wider cards and the readable expanded viewer stay unchanged.
                    assert m['nameFont']>(4 if width<=360 else 5) and m['roleFont'] and m['whiteText'] and m['singleLines'], m
                    if width <= 760:
                        assert m['nameFont'] <= 11.01 and m['roleMaxFont'] <= 9.01, m
                        assert m['overlayHeight'] <= 27, m
                    assert m['clearPortrait']>=.4, m
                    assert m['imageCovers'] and m['squareInitials'] and m['squareRadius']==0, m
                    assert m['border']==0 and m['shadow']=='none', m
                columns=page.locator('.former-members-grid').evaluate('g=>getComputedStyle(g).gridTemplateColumns.split(" ").length')
                expected_columns = 4 if width >= 1200 else 3
                assert columns == expected_columns, [width, columns]
                assert page.locator('.team-portrait').count() == 6
                for image in page.locator('.team-portrait img').all():
                    image.scroll_into_view_if_needed()
                    image.evaluate('i=>i.decode()')
                assert page.locator('.team-portrait-history').count() == 0
                assert page.locator('.team-employer-link').count() == 11
                assert page.get_by_role('heading', name='Our members have been employed by;', exact=True).count() == 1
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                assert not errors and not failed, [errors, failed]
                page.locator('.former-members-grid').screenshot(path=str(args.output / f'{width}-{scheme}-former.png'),
                                                               animations='disabled', style='.md-header{visibility:hidden!important}')
                if width == 320 and scheme == 'light':
                    # Exercise navigation/back-to-Team whether the theme chooses
                    # instant replacement or a full fallback page load.
                    for _ in range(2):
                        page.locator('.md-header [data-md-component="logo"]').click()
                        page.wait_for_url(args.url.rstrip('/') + '/')
                        assert not page.locator('.former-member-dialog[open]').count()
                        page.get_by_role('link', name='Team', exact=True).first.evaluate('a=>a.click()')
                        page.wait_for_url(args.url.rstrip('/') + '/team/')
                        page.locator('.former-member-open').first.wait_for(state='visible')
                        assert page.locator('.former-member-open').count() == 30
                        assert page.locator('.former-member-dialog').count() <= 1
                        first = page.locator('.former-member-open').first
                        first.focus()
                        page.keyboard.press('Enter')
                        assert page.locator('.former-member-dialog[open]').count() == 1
                        page.locator('.former-member-close').click()
                        assert first.evaluate('b=>document.activeElement===b')
                results.append({'width': width, 'scheme': scheme, 'cards': metrics,
                                'former_photos': cards.locator('img').count(),
                                'former_role_lines': cards.locator('small').count(),
                                'current_history_role_lines': page.locator('.team-portrait-history small').count(),
                                'linkedin_icons': cards.locator('.former-member-link--linkedin').count(),
                                'website_icons': cards.locator('.former-member-link--website').count(),
                                'former_columns': columns,
                                'initials': cards.locator('.former-member-initials').count(),
                                'lead_photos': 6, 'employers': 11,
                                'page_errors': errors, 'failed_local_responses': failed,
                                'horizontal_overflow': False})
                page.close()
        browser.close()
    (args.output / 'report.json').write_text(json.dumps(results, indent=2))
    print(f'{len(results)} team-history alignment/role checks passed.')


if __name__ == '__main__':
    main()
