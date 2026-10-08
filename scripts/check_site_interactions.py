#!/usr/bin/env python3
"""Check MACH browser interactions against a built site. Requires Playwright.

Run after the build with a local server, e.g. python -m http.server 8876 -d site.
Screenshots are saved outside the repository. No published files are modified.
"""
from playwright.sync_api import sync_playwright
from pathlib import Path
import json, argparse, shutil
parser=argparse.ArgumentParser()
parser.add_argument('--url', default='http://127.0.0.1:8876')
parser.add_argument('--chrome', default=shutil.which('google-chrome') or '/opt/google/chrome/chrome')
parser.add_argument('--output', default='/tmp/mach-polish-preview')
parser.add_argument('--axe', default=str(Path(__file__).resolve().parents[1]/'ci/node_modules/axe-core/axe.min.js'))
parser.add_argument('--quick', action='store_true', help='Deployment smoke coverage; full checks run on PRs/manual audits.')
args=parser.parse_args()
out=Path(args.output);out.mkdir(exist_ok=True)
base=args.url.rstrip('/')
NAVIGATION_BREAKPOINT=600
def check_black_gradient(locator, pseudo, z_index):
 geometry=locator.evaluate('''(e,pseudo)=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e,pseudo);return {width:r.width,height:r.height,overlayWidth:parseFloat(s.width),overlayHeight:parseFloat(s.height),background:s.backgroundImage,position:s.position,z:s.zIndex}}''',pseudo)
 assert geometry['position']=='absolute' and geometry['z']==str(z_index),geometry
 assert abs(geometry['overlayWidth']-geometry['width'])<1 and abs(geometry['overlayHeight']-geometry['height'])<1,geometry
 gradient=geometry['background']
 assert gradient.startswith('linear-gradient(') and 'rgba(0, 0, 0, 0) 55%' in gradient and 'rgba(0, 0, 0, 0.45) 80%' in gradient and 'rgba(0, 0, 0, 0.85) 100%' in gradient,gradient
 return gradient

with sync_playwright() as p:
 b=p.chromium.launch(executable_path=args.chrome,headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
 for width,scheme in ([(1440,'light'),(320,'dark')] if args.quick else [(1440,'light'),(390,'light'),(390,'dark'),(320,'dark')]):
  ctx=b.new_context(viewport={'width':width,'height':900},color_scheme=scheme,reduced_motion='reduce')
  page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)));gradient_reference=None
  for path in ['/','/team/','/sponsors/','/Seraphina/','/Seraphina/aug-20-hotfire/','/Seraphina/oct-4-hotfire/','/timeline/','/SPRINT/','/GAR-E/']:
   page.goto(base+path,wait_until='domcontentloaded');page.wait_for_timeout(500)
   assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), (path,'overflow')
   assert page.locator('[data-md-component="top"]').count()==0
   assert page.locator('.md-footer__link--prev, .md-footer__link--next').count()==0
   for selector in ('.md-sidebar--primary','.md-sidebar--secondary'):
    assert page.locator(selector).get_attribute('hidden') is not None,(path,selector)
   assert page.locator('.md-content a').filter(has_text='complete MACH test timeline').count()==0
   assert page.locator('.md-content a').filter(has_text='Back to the complete timeline').count()==0
   assert page.locator('[data-mach-drawer-toggle]').is_visible() == (width < NAVIGATION_BREAKPOINT)
   assert page.locator('[data-mach-search-open], .mach-search-toggle').count()==0
   assert page.get_by_role('button',name='Search',exact=True).count()==0
   assert page.locator('label[for^="__palette"]').count()==0
   assert page.locator('[data-md-component="palette"]').is_hidden()
   assert page.locator('body').get_attribute('data-md-color-scheme')==('slate' if scheme=='dark' else 'default')
   assert page.locator('.md-header [data-md-component="logo"]').count()==1
   assert page.locator('.md-logo[title], .md-logo [title], .home-hero__logo[title]').count()==0
   assert page.locator('.md-header [data-md-component="logo"]').is_visible()==(width>=NAVIGATION_BREAKPOINT or path!='/')
   assert page.locator('.md-tabs').count()==1
   assert [text.strip() for text in page.locator('.md-tabs__link').all_text_contents()]==['Team','Resources','Sponsors','GAR-E','SPRINT','Seraphina']
   assert page.locator('.md-tabs a[href$="/timeline/"], .md-nav--primary a[href$="/timeline/"]').count()==0
   if width>=NAVIGATION_BREAKPOINT:
    row=page.locator('.md-header').evaluate('''h=>{const rect=e=>e.getBoundingClientRect();const es=[h.querySelector('[data-md-component="logo"]'),...h.querySelectorAll('.md-tabs__link')];return {height:h.offsetHeight,centers:es.map(e=>{const r=rect(e);return r.top+r.height/2}),boxes:es.map(e=>rect(e).toJSON()),title:getComputedStyle(h.querySelector('.md-header__title')).display}}''')
    assert row['height']==52 and row['title']=='none',row
    assert max(row['centers'])-min(row['centers'])<.1,row
    assert all(a['right']<=b['left'] for a,b in zip(row['boxes'],row['boxes'][1:])),row
    assert page.locator('.md-tabs__link').all_text_contents() and page.locator('.md-tabs__link').filter(has_text='MACH').count()==0
   else:
    assert page.locator('.md-tabs').is_hidden()
   assert page.locator('.md-header a[href*="github.com"], .md-sidebar a[href*="github.com"]').count()==0
   assert page.locator('.md-header__source, .md-nav__source').count()==0
   assert page.locator('.md-footer .md-social a[href="https://github.com/machtmu/"]').count()==1
   # One spacing system for the footer, independent of native child margins.
   footer=page.locator('.md-footer-meta__inner').evaluate('''el=>{
    const box=e=>e.getBoundingClientRect().toJSON();
    return {outer:box(el),copyright:box(el.querySelector('.md-copyright')),
     social:box(el.querySelector('.md-social')),location:box(el.querySelector('.mach-footer-location'))};
   }''')
   if width < 960:
    assert abs(footer['social']['top']-footer['copyright']['bottom']-8)<1, footer
    assert abs(footer['location']['top']-footer['social']['bottom']-8)<1, footer
    assert abs(footer['copyright']['top']-footer['outer']['top']-16)<1, footer
    assert abs(footer['outer']['bottom']-footer['location']['bottom']-16)<1, footer
   else:
    centers=[footer[key]['top']+footer[key]['height']/2 for key in ('copyright','social','location')]
    assert max(centers)-min(centers)<1, footer
   themed=page.locator('img[data-plot-dark-src]')
   if themed.count():
    for image in themed.all():
     image.scroll_into_view_if_needed()
     page.wait_for_function('(img)=>img.complete&&img.naturalWidth>0',arg=image.element_handle())
     assert image.get_attribute('data-plot-theme')==('dark' if scheme=='dark' else 'light')
     assert image.get_attribute('src').endswith('-dark.png')==(scheme=='dark')
    page.evaluate('scrollTo(0,0)');page.wait_for_timeout(100)
   if path=='/':
    projects=page.locator('.home-project-links a')
    assert projects.count()==3
    boxes=[link.bounding_box() for link in projects.all()]
    strip=page.locator('.home-project-links').bounding_box()
    visible_width=page.locator('body').bounding_box()['width']
    assert abs(strip['x'])<1 and abs(strip['width']-visible_width)<1,(strip,visible_width)
    assert page.locator('.home-project-links').evaluate('e=>getComputedStyle(e).columnGap')=='0px'
    assert abs(boxes[0]['x']-strip['x'])<1 and abs(boxes[-1]['x']+boxes[-1]['width']-strip['x']-strip['width'])<1,(strip,boxes)
    assert all(abs(box['width']-strip['width']/3)<1 for box in boxes),(strip,boxes)
    assert max(box['y'] for box in boxes)-min(box['y'] for box in boxes)<1,boxes
    assert all(abs(a['x']+a['width']-b['x'])<1 for a,b in zip(boxes,boxes[1:])),boxes
    assert all(box['height']>=(220 if width<=768 else 380)-1 for box in boxes),boxes
    assert page.locator('.home-project-link__name').all_text_contents()==['Seraphina','SPRINT','GAR-E']
    assert page.locator('.home-project-link__years').all_text_contents()==['2026','2025','2023–2024']
    assert page.evaluate('document.querySelector(".home-data").nextElementSibling===document.querySelector(".home-project-strip")')
    sprint_image=projects.nth(1).locator('img')
    assert sprint_image.get_attribute('src').endswith('/sept-14-hotfire-2s.webp')
    assert sprint_image.get_attribute('data-display-original') is not None
    assert sprint_image.get_attribute('width')=='960' and sprint_image.get_attribute('height')=='540'
    for link in projects.all():
     gradient=check_black_gradient(link,'::after',-1)
     if gradient_reference is None:gradient_reference=gradient
     assert gradient==gradient_reference
     assert link.locator('.home-project-link__caption').evaluate('e=>getComputedStyle(e).color')=='rgb(255, 255, 255)'
     assert link.bounding_box()['width']>=44 and link.bounding_box()['height']>=44
     link.scroll_into_view_if_needed()
     link.locator('img').evaluate('''i=>Promise.race([i.decode(),new Promise((_,reject)=>setTimeout(()=>reject(new Error('Project image did not decode')),15000))])''')
     assert link.locator('img').get_attribute('alt') is not None
     assert link.inner_text().strip()
     panel=link.bounding_box()
     for selector in ('.home-project-link__name','.home-project-link__years'):
      label=link.locator(selector).bounding_box()
      assert label['x']>=panel['x'] and label['x']+label['width']<=panel['x']+panel['width']+1,(panel,label)
      assert label['y']>=panel['y'] and label['y']+label['height']<=panel['y']+panel['height']+1,(panel,label)
    page.evaluate('scrollTo(0,0)');page.wait_for_timeout(100)
    assert page.evaluate('''()=>{const p=[...document.querySelectorAll(".md-content p")].find(p=>p.textContent.startsWith("Explore Seraphina, SPRINT and GAR-E"));return p&&Boolean(document.querySelector(".home-project-strip").compareDocumentPosition(p)&Node.DOCUMENT_POSITION_FOLLOWING)}''')
    assert themed.evaluate('(i)=>getComputedStyle(i).backgroundColor')=='rgba(0, 0, 0, 0)'
    assert themed.evaluate('(i)=>getComputedStyle(i).borderRadius')=='0px'
    framing=page.locator('.hero-bg').evaluate('(v)=>({hero:v.parentElement.getBoundingClientRect().toJSON(),video:v.getBoundingClientRect().toJSON(),transform:getComputedStyle(v).transform,position:getComputedStyle(v).objectPosition})')
    assert framing['video']['top']<=framing['hero']['top'] and framing['video']['bottom']>=framing['hero']['bottom'], framing
    assert abs(framing['video']['height']-framing['hero']['height'])<1, framing
    assert framing['transform']=='none', framing
    assert page.locator('.hero-bg').evaluate('(v)=>getComputedStyle(v).filter')=='saturate(1.06)'
    if width<=768:
     assert framing['position']=='90% 50%', framing
    else:
     assert framing['position']=='50% 50%', framing
    assert page.locator('.home-hero__subtitle').inner_text()=='TMU Liquid Rocketry'
    branding=page.locator('.home-hero__inner').evaluate('''(el)=>{
     const logo=el.querySelector('img').getBoundingClientRect(), subtitle=el.querySelector('p').getBoundingClientRect(), hero=el.closest('.home-hero').getBoundingClientRect();
     return {wordAxis:logo.left+logo.width*.43,subtitleAxis:subtitle.left+subtitle.width/2,logoWidth:logo.width,viewportAxis:hero.left+hero.width/2,gap:subtitle.top-logo.bottom};
    }''')
    assert abs(branding['wordAxis']-branding['subtitleAxis']-branding['logoWidth']*.02)<1, branding
    assert abs(branding['subtitleAxis']-branding['viewportAxis'])<1, branding
    assert abs(branding['gap']-(8 if width<=768 else 10))<1, branding
    assert page.locator('.home-hero__logo').get_attribute('alt')=='MACH'
    assert page.locator('.home-hero__logo').get_attribute('src').endswith('/logo-hero-dark.webp')
    assert page.locator('.home-hero__logo').evaluate('i=>[i.naturalWidth,i.naturalHeight]')==[2048,636]
    if not page.evaluate('matchMedia("(dynamic-range: high)").matches'):
     assert page.locator('.home-hero__title').evaluate('(e)=>getComputedStyle(e,"::after").display')=='none'
     assert page.locator('.home-hero__title').evaluate('(e)=>getComputedStyle(e,"::before").display')=='none'
    hero_video=page.locator('.hero-bg')
    # Retain the optimized native-resolution hero rather than a video thumbnail.
    assert hero_video.get_attribute('poster').endswith('.webp')
    assert hero_video.get_attribute('poster')==hero_video.get_attribute('data-light-poster')==hero_video.get_attribute('data-dark-poster')
    poster_preload=page.locator('link[rel="preload"][as="image"][fetchpriority="high"]')
    assert poster_preload.count()==1 and poster_preload.get_attribute('type')=='image/webp'
    assert page.evaluate('document.querySelector("link[rel=preload][as=image][fetchpriority=high]").href===document.querySelector(".hero-bg").poster')
    poster_size=hero_video.evaluate('''async v=>{const image=new Image();image.src=v.poster;await image.decode();return [image.naturalWidth,image.naturalHeight];}''')
    assert poster_size==[2688,1446], poster_size
    intro=page.locator('.home-team-intro')
    assert page.evaluate('document.querySelector(".home-hero").nextElementSibling===document.querySelector(".home-team-intro")')
    assert page.locator('.home-team-intro p').inner_text()=="MACH is Toronto Metropolitan University's student liquid rocketry team, based in Toronto, Ontario. We design, build and test liquid rocket engines, avionics and ground-support systems."
    assert page.get_by_text("MACH is Toronto Metropolitan University's student liquid rocketry team, based in Toronto, Ontario. We design, build and test liquid rocket engines, avionics and ground-support systems.",exact=True).count()==1
    intro_photo=page.locator('.home-team-intro__photo')
    assert intro_photo.get_attribute('src').endswith('/seraphina-relight-team-intro.webp')
    assert intro_photo.get_attribute('data-display-original') is not None
    assert intro_photo.evaluate('e=>getComputedStyle(e).filter')=='grayscale(1)'
    intro_box=intro.bounding_box();hero_box=page.locator('.home-hero').bounding_box()
    assert abs(intro_box['y']-(hero_box['y']+hero_box['height']))<1
    content_box=page.locator('.home-team-intro__content').bounding_box()
    assert content_box['x']>=intro_box['x'] and content_box['x']+content_box['width']<=intro_box['x']+intro_box['width']+1
    assert content_box['y']+content_box['height']<=intro_box['y']+intro_box['height']+1
    assert intro_photo.evaluate('e=>getComputedStyle(e).objectFit')=='cover'
    assert page.get_by_role('button',name='Expand plot:',exact=False).count()==0
    assert page.locator('.hotfire-data a, .hotfire-data button').count()==0
    assert page.locator('.hotfire-data figcaption').count()==0
    assert themed.bounding_box()['width']>0 and themed.bounding_box()['height']>0
    assert page.get_by_role('heading',name='Rigorous data collection',exact=True).count()==0
    assert page.evaluate('document.querySelector(".home-hotfire").nextElementSibling===document.querySelector(".home-data")')
    crop=page.locator('.hotfire-data__viewport').bounding_box();plot_box=themed.bounding_box()
    assert abs(crop['width']/crop['height']-1771/850)<.01,crop
    assert abs(plot_box['y']-crop['y']+crop['width']*205/1771)<1,(crop,plot_box)
    assert abs(plot_box['width']-crop['width'])<1,(crop,plot_box)
    assert page.locator('.hotfire-data__viewport').evaluate('e=>getComputedStyle(e).overflow')=='hidden'
    assert page.locator('.home-hotfire h2').inner_text()=='Latest hotfire: October 4 relight'
    assert page.evaluate('document.querySelector(".home-team-intro").nextElementSibling===document.querySelector(".home-hotfire")')
    hotfire=page.locator('.home-hotfire');hotfire_box=hotfire.bounding_box()
    assert abs(hotfire_box['y']-(intro_box['y']+intro_box['height']))<1,hotfire_box
    assert abs(hotfire_box['width']-intro_box['width'])<1 and abs(hotfire_box['x']-intro_box['x'])<1,hotfire_box
    showcase=hotfire.locator('.showcase-video')
    assert showcase.evaluate('v=>getComputedStyle(v).filter')=='grayscale(1)'
    assert showcase.evaluate('v=>v.controls&&!v.autoplay&&v.paused&&v.preload==="none"')
    assert showcase.locator('source').get_attribute('src').endswith('/seraphina-oct-4-hotfire.mp4')
    assert page.get_by_role('link',name='View all test data',exact=True).count()==0
    themed.click();assert page.locator('dialog:visible').count()==0
    assert page.locator('.photo-showcase, .image-slideshow, .slideshow-image, [data-slide-previous], [data-slide-next]').count()==0
    assert page.locator('.home-explore').count()==1
    assert page.locator('.hero-bg').get_attribute('src') is None
    hero=page.locator('[data-hero-motion]')
    assert hero.get_attribute('aria-label')=='Play hero video' and hero.get_attribute('title') is None and hero.inner_text()==''
    control_box=hero.bounding_box();hero_panel=page.locator('.home-hero').bounding_box()
    assert abs(control_box['width']-44)<1 and abs(control_box['height']-44)<1,control_box
    assert abs(hero_panel['x']+hero_panel['width']-control_box['x']-control_box['width']-12)<1 and abs(hero_panel['y']+hero_panel['height']-control_box['y']-control_box['height']-12)<1,(control_box,hero_panel)
    icon=hero.locator('.hero-motion-icon--play').bounding_box();assert abs(icon['width']-12)<1 and abs(icon['height']-12)<1,icon
    hero.click()
    page.wait_for_function('document.querySelector(".hero-bg").readyState>=1')
    page.wait_for_function('document.querySelector("[data-hero-motion]").getAttribute("aria-label")==="Pause hero video"')
    assert abs(page.locator('.hero-bg').evaluate('(v)=>v.duration')-14.6)<.1
    assert page.locator('.hero-bg').evaluate('(v)=>v.muted')
    hero.click();page.wait_for_timeout(300)
    assert hero.get_attribute('aria-label')=='Play hero video'
    assert page.get_by_role('img',name='All teams gathered at Launch Canada 2026',exact=True).count()==0
   if path=='/Seraphina/':
    assert page.locator('.seraphina-team-gallery').count()==0
    assert page.get_by_role('img',name='All teams gathered at Launch Canada 2026',exact=True).count()==0
    assert "At Launch Canada, MACH was able to press a single button" in page.locator('.md-content').inner_text()
    assert "Seraphina is MACH's project for 2026." in page.locator('.md-content').inner_text()
    card=page.locator('.program-test-grid article').filter(has=page.get_by_role('heading',name='Relight test',exact=True))
    assert card.locator('img').get_attribute('alt')=='Seraphina team at the August 20 Launch Canada relight test'
   if path=='/Seraphina/aug-20-hotfire/':
    group=page.get_by_role('img',name='All teams gathered at Launch Canada 2026',exact=True)
    assert group.count()==1
    assert group.locator('..').get_attribute('href').endswith('/assets/images/launch-canada-2026-all-teams.jpg')
    photos=page.locator('.seraphina-team-gallery figure')
    assert photos.count()==2
    assert page.locator('.seraphina-team-gallery').count()==2
    for photo in photos.all():
     gallery=photo.locator('..').bounding_box()
     box=photo.bounding_box()
     frame=photo.locator('.seraphina-team-photo').bounding_box()
     assert abs(box['width']-frame['width'])<1, (box,frame)
     assert abs(frame['width']/frame['height']-16/9)<.01, frame
     if width<=760:
      assert abs(box['width']-gallery['width'])<1, (box,gallery)
    if width<=760:
     first,second=[photo.bounding_box() for photo in photos.all()]
     assert second['y']>=first['y']+first['height']
    celebration=page.get_by_role('img',name='Seraphina team celebrating the August Launch Canada relight test',exact=True)
    assert celebration.locator('..').get_attribute('href').endswith('/team-celebration-full.jpg')
    celebration.scroll_into_view_if_needed()
    assert page.locator('#team-celebration').evaluate('e=>getComputedStyle(e).textAlign')=='center'
    assert page.locator('.md-content h2:not(#team-celebration)').evaluate_all('(els)=>els.every(e=>getComputedStyle(e).textAlign!=="center")')
    caption=celebration.locator('..').locator('..').locator('figcaption')
    assert caption.evaluate('e=>getComputedStyle(e).textAlign')=='center'
    celebration.evaluate('(i)=>i.decode()')
    assert celebration.evaluate('(i)=>[i.naturalWidth,i.naturalHeight]')==[2767,1556]
    assert celebration.evaluate('(i)=>i.closest("figure")===Array.from(document.querySelectorAll(".md-content figure")).at(-1)')
   if path=='/team/':
    current=page.locator('.team-leads').inner_text();former=page.locator('.former-members-grid').inner_text()
    assert 'Zeul' not in current and 'Audrey' not in current and 'Safety Officer' in current and 'Operations Director' in current
    assert 'Zeul Mordasiewicz' in former and 'Audrey Abergel-Preston' in former
    assert page.locator('#former-leads').inner_text()=='Former Leads'
    assert page.locator('.former-members-grid .former-member-card').count()==24
    assert 'Milad Hemmat' in former and 'Milad Hemmat' not in current
    cards=page.locator('.team-leads li')
    expected=[('Julia Puszynska','Team Captain'),('Tobechukwu Okoh','Propulsion Lead'),('Samuel Li','Operations Director'),('Jonathan Al-Hinn','Safety Officer'),('Kasper Pajak','Electrical Lead'),('Madison Warren','Media & Logistics Lead')]
    assert cards.count()==len(expected)
    for card,(name,role) in zip(cards.all(),expected):
     assert card.locator('strong').inner_text()==name
     assert card.locator('em').inner_text()==role
     background=card.locator('.team-portrait').evaluate('e=>{const s=getComputedStyle(e);return [s.backgroundImage,s.backgroundColor]}')
     assert background==['none','rgb(183, 183, 183)'],(name,background)
     image=card.locator('img');image.scroll_into_view_if_needed()
     image.evaluate('''i=>Promise.race([i.decode(),new Promise((_,reject)=>setTimeout(()=>reject(new Error('Lead portrait did not decode')),15000))])''')
     assert image.get_attribute('data-original-src').endswith('-studio.webp') and image.get_attribute('data-portrait-delivery') is not None
     dimensions=image.evaluate('i=>[i.naturalWidth,i.naturalHeight]')
     master_width,master_height=int(image.get_attribute('width')),int(image.get_attribute('height'))
     assert dimensions[0]<=master_width and abs(dimensions[0]/dimensions[1]-master_width/master_height)<0.01,(name,dimensions)
     mask=image.evaluate('i=>getComputedStyle(i).maskImage')
     assert mask=='none',(name,mask)
     panel_box=card.locator('.team-portrait').bounding_box();image_box=image.bounding_box()
     assert image_box['x']<=panel_box['x']+1 and image_box['y']<=panel_box['y']+1 and image_box['x']+image_box['width']>=panel_box['x']+panel_box['width']-1 and image_box['y']+image_box['height']>=panel_box['y']+panel_box['height']-1,(name,panel_box,image_box)
   if path=='/sponsors/':
    crops=page.locator('.sponsor-logo__crop');assert crops.count()==25
    assert page.locator('.sponsor-item').evaluate_all('(es)=>es.every(e=>!e.innerText.trim()&&e.querySelector("img")?.alt.trim())')
    assert crops.evaluate_all('(es)=>es.every(e=>{const r=e.getBoundingClientRect(),c=getComputedStyle(e);return r.width>0&&r.height>0&&Math.abs(r.width/r.height-parseFloat(c.getPropertyValue("--logo-ratio")))<0.03&&c.backgroundColor==="rgba(0, 0, 0, 0)"})')
   if path in ('/Seraphina/aug-20-hotfire/', '/Seraphina/oct-4-hotfire/'):
    controls=page.get_by_role('button',name='Expand plot:',exact=False);assert controls.count()==2
    controls.nth(1).click();page.wait_for_timeout(300)
    assert page.locator('dialog').is_visible()
    active_plot=page.locator('.md-content img.mach-plot').nth(1)
    assert page.locator('dialog img').get_attribute('src')==active_plot.get_attribute('src')
    assert page.locator('dialog [data-plot-original]').get_attribute('href')==active_plot.get_attribute('src')
    assert page.locator('dialog').get_attribute('data-plot-theme')==('dark' if scheme=='dark' else 'light')
    w=page.locator('dialog img').evaluate('(i)=>i.width')
    page.get_by_role('button',name='Zoom in',exact=True).click();page.wait_for_timeout(100)
    assert page.locator('dialog img').evaluate('(i)=>i.width')>w*1.9
    page.screenshot(path=str(out/f'viewer-{width}-{scheme}.png'))
    page.keyboard.press('Escape');assert not page.locator('dialog').is_visible()
    assert controls.nth(1).evaluate('(e)=>e===document.activeElement')
   if path=='/timeline/':
    assert page.locator('.gare-timeline__card').count()==56
    assert page.locator('.gare-timeline__media').count()==37
    assert page.locator('.gare-timeline__caption').count()==37
    assert page.locator('.gare-timeline__card p').count()==55
    assert page.locator('.gare-timeline__caption h2 a').count()==37
    assert page.locator('.gare-timeline__caption h2 a').evaluate_all('(els)=>els.every(e=>e.getBoundingClientRect().height>=24)')
    assert page.locator('.gare-timeline__link').count()==0
    assert page.locator('.gare-timeline__card').evaluate_all('(els)=>els.every(e=>{const s=getComputedStyle(e);return s.borderTopWidth==="0px"&&s.boxShadow==="none"&&s.backgroundColor==="rgba(0, 0, 0, 0)"})')
    assert page.locator('.gare-timeline__caption').evaluate_all('(els)=>els.every(e=>getComputedStyle(e).color==="rgb(255, 255, 255)")')
    assert page.locator('.gare-timeline__media--full-frame, .gare-timeline__media--portrait-context').count()==7
    assert page.locator('.gare-timeline__media--full-frame, .gare-timeline__media--portrait-context').evaluate_all('(els)=>els.every(e=>getComputedStyle(e,"::after").display==="none"&&getComputedStyle(e.parentElement.querySelector(".gare-timeline__caption")).gridRowStart==="caption")')
    page.locator('[data-filter="project"]').select_option('Seraphina')
    page.locator('[data-filter="type"]').select_option('hotfire')
    count=page.locator('.gare-timeline__event:visible').count();assert count==3,count
    assert page.locator('.gare-timeline__event:visible').first.locator('time').get_attribute('datetime')=='2026-10-04'
    page.locator('[data-filter="year"]').select_option('2018');assert page.locator('.gare-timeline__event:visible').count()==0
    page.get_by_role('button',name='Clear filters').click();assert page.locator('.gare-timeline__event:visible').count()>30
    page.locator('[data-filter="year"]').select_option('2026')
   if path in ('/Seraphina/','/SPRINT/','/GAR-E/'):
    cards=page.locator('.project-cards > article')
    assert page.locator('.project-cards p, .project-card-more').count()==0,path
    assert cards.count()=={'/Seraphina/':5,'/SPRINT/':9,'/GAR-E/':6}[path]
    for card in cards.all():
     card.scroll_into_view_if_needed();card.locator('img').evaluate('i=>i.decode()')
     full_frame=bool(card.locator(':scope > a.project-card-media--full-frame').count())
     if full_frame:
      assert card.locator('img').evaluate('i=>getComputedStyle(i).objectFit')=='contain'
      assert card.locator('img').evaluate('i=>Number(i.getAttribute("width"))>0&&Number(i.getAttribute("height"))>0')
      # A whole-frame photo must fill its panel with real pixels, not be
      # contained at the top of an oversized black title strip.
      photo=card.locator('img').evaluate('i=>{const r=i.getBoundingClientRect();return {w:r.width,h:r.height,nw:Number(i.getAttribute("width")),nh:Number(i.getAttribute("height"))}}')
      assert abs(photo['h']-photo['w']*photo['nh']/photo['nw'])<1,photo
     gradient=check_black_gradient(card,'::before',1)
     if gradient_reference is None:gradient_reference=gradient
     assert gradient==gradient_reference
     assert card.evaluate('e=>getComputedStyle(e).backgroundColor')=='rgb(0, 0, 0)'
     assert card.locator(':scope > div').evaluate('e=>getComputedStyle(e).color')=='rgb(255, 255, 255)'
     geometry=card.evaluate('''e=>{const r=e.getBoundingClientRect(),i=e.querySelector("img").getBoundingClientRect(),c=e.querySelector(":scope > div").getBoundingClientRect(),s=getComputedStyle(e);return {card:r.toJSON(),image:i.toJSON(),caption:c.toJSON(),minimum:parseFloat(getComputedStyle(e.querySelector(":scope > a")).minHeight),border:s.borderWidth,radius:s.borderRadius,shadow:s.boxShadow}}''')
     r,i,c=geometry['card'],geometry['image'],geometry['caption']
     assert geometry['border']=='0px' and geometry['radius']=='0px' and geometry['shadow']=='none',geometry
     assert c['left']>=r['left']-1 and c['right']<=r['right']+1 and c['bottom']<=r['bottom']+1,geometry
     assert c['top']>=i['top']-1 and c['bottom']<=i['bottom']+1,geometry
     assert i['height']>=r['height']-1,geometry
     if full_frame:
      assert abs(r['height']-i['height'])<1,geometry
     else:
      # A neighbouring whole-frame photo may set a taller desktop grid row.
      # Cover panels fill that row, while the photograph itself reserves it.
      peer_photo_height=card.evaluate('''e=>{const y=e.getBoundingClientRect().top;return Math.max(0,...[...e.parentElement.children].filter(p=>Math.abs(p.getBoundingClientRect().top-y)<1&&p.querySelector(':scope>.project-card-media--full-frame')).map(p=>p.querySelector('img').getBoundingClientRect().height))}''')
      assert r['height']<=max(geometry['minimum'],c['height'],peer_photo_height)+1,geometry
     assert card.locator('a').first.get_attribute('href'),path
   for y in range(0,min(page.evaluate('document.body.scrollHeight'),6500),700):page.evaluate('(y)=>scrollTo(0,y)',y);page.wait_for_timeout(60)
   page.wait_for_timeout(250);page.evaluate('scrollTo(0,0)')
   slug=path.strip('/').replace('/','-')or'home'
   page.screenshot(path=str(out/f'{slug}-{width}-{scheme}.png'),full_page=True)
   page.add_script_tag(path=args.axe)
   axe=page.evaluate('async()=>{const r=await axe.run(document,{runOnly:{type:"tag",values:["wcag2a","wcag2aa","wcag21aa"]}});return r.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary})).slice(0,3)}))}')
   print(json.dumps({'page':path,'width':width,'scheme':scheme,'errors':errors,'axe':axe}),flush=True)
   assert not errors, errors
   assert not axe, axe
  if width==390:
   page.locator('[data-mach-drawer-toggle]').click();page.keyboard.press('Escape');assert not page.locator('#__drawer').is_checked()
  ctx.close()
 # Check both sides of the content-fit breakpoint, including the range where
 # the native theme previously hid the tabs and moved primary navigation offscreen.
 ctx=b.new_context(viewport={'width':900,'height':900},reduced_motion='reduce')
 page=ctx.new_page()
 for path in ['/', '/team/', '/Seraphina/aug-20-hotfire/', '/SPRINT/']:
  page.goto(base+path,wait_until='domcontentloaded')
  for width in [599,600,620,680,700,768,840,899,900,960,1024,1219,1220,599]:
   page.set_viewport_size({'width':width,'height':900});page.wait_for_timeout(150)
   desktop=width>=NAVIGATION_BREAKPOINT
   assert page.locator('.md-tabs').is_visible()==desktop, (path,width)
   assert page.locator('[data-mach-drawer-toggle]').is_visible()==(not desktop), (path,width)
   assert page.locator('.md-header [data-md-component="logo"]').is_visible()==(desktop or path!='/'), (path,width)
   assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), (path,width)
   if desktop:
    boxes=page.locator('.md-header').evaluate('''h=>[h.querySelector('.md-logo'),...h.querySelectorAll('.md-tabs__link')].map(e=>e.getBoundingClientRect().toJSON())''')
    assert all(a['right']<=b['left'] for a,b in zip(boxes,boxes[1:])), (path,width,boxes)
    assert boxes[-1]['right']<=width, (path,width,boxes)
    if path=='/Seraphina/aug-20-hotfire/':
     sidebar=page.locator('.md-sidebar--primary')
     assert sidebar.is_hidden(),width
     assert page.locator('.md-sidebar--secondary').is_hidden(),width
   else:
    page.locator('[data-mach-drawer-toggle]').click()
    assert page.locator('#__drawer').is_checked(),width
    page.keyboard.press('Escape')
    assert not page.locator('#__drawer').is_checked(),width
 print('Navigation breakpoint, drawer and project sidebar checks passed: 599–1220px',flush=True)
 ctx.close()
 # Only the deliberately long technical documents opt into reading sidebars.
 ctx=b.new_context(viewport={'width':1440,'height':900},reduced_motion='reduce')
 page=ctx.new_page()
 for path in ['/SPRINT/avionics/resources/dfmguide/','/SPRINT/avionics/PCB-Modules/gps/']:
  page.goto(base+path,wait_until='domcontentloaded')
  for selector in ('.md-sidebar--primary','.md-sidebar--secondary'):
   assert page.locator(selector).get_attribute('hidden') is None,(path,selector)
   assert page.locator(selector).is_visible(),(path,selector)
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),path
 print('Short-page sidebars hidden; long technical documents retain navigation and contents',flush=True)
 ctx.close()
 # Intermediate widths must keep the introduction over real photograph,
 # rather than letting its paragraph spill below the mobile image.
 ctx=b.new_context(viewport={'width':390,'height':844},reduced_motion='reduce')
 page=ctx.new_page();page.goto(base,wait_until='domcontentloaded')
 for width in (320,390,599,600,679,680,700,768,769,840,960,1440):
  page.set_viewport_size({'width':width,'height':844})
  photo=page.locator('.home-team-intro__photo')
  photo.scroll_into_view_if_needed()
  # A picture's media-selected source changes asynchronously during resize;
  # decoding the old source at that instant may reject with EncodingError.
  page.wait_for_function('''portrait=>{const i=document.querySelector('.home-team-intro__photo');return i.complete&&i.naturalWidth>0&&i.currentSrc.includes('portrait')===portrait}''',arg=width<=768)
  photo.evaluate('''i=>Promise.race([i.decode(),new Promise((_,reject)=>setTimeout(()=>reject(new Error('Introduction image did not decode')),15000))])''')
  frame=page.locator('.home-team-intro').bounding_box()
  image=photo.bounding_box()
  paragraph=page.locator('.home-team-intro p').bounding_box()
  assert image['y']<=frame['y']+1 and image['y']+image['height']>=frame['y']+frame['height']-1,(width,image,frame)
  assert paragraph['y']>=image['y'] and paragraph['y']+paragraph['height']<=image['y']+image['height']+1,(width,paragraph,image)
  assert photo.evaluate('i=>getComputedStyle(i).objectFit')=='cover',width
  assert ('portrait' in photo.evaluate('i=>i.currentSrc'))==(width<=768),width
 print('Introduction image covers paragraph across mobile and intermediate widths',flush=True)
 ctx.close()
 # Cropped telemetry is full bleed until the viewport-height limit applies.
 for width,height in [(1440,900),(1920,1080),(2560,1080),(390,844)]:
  ctx=b.new_context(viewport={'width':width,'height':height},reduced_motion='reduce')
  page=ctx.new_page();page.goto(base,wait_until='domcontentloaded')
  crop=page.locator('.hotfire-data__viewport').bounding_box();panel=page.locator('.home-data').bounding_box()
  expected=min(panel['width'],height*.9*1771/850)
  assert abs(crop['width']-expected)<1,(width,height,crop,expected)
  assert crop['height']<=height*.9+1,(width,height,crop)
  assert abs(crop['x']+crop['width']/2-panel['x']-panel['width']/2)<1,(width,height,crop,panel)
  print(f'Full-width telemetry and viewport-height limit passed: {width}x{height}',flush=True)
  ctx.close()
 # Desktop hero grows with the original image's aspect ratio; mobile keeps
 # its approved height and right-biased framing rather than inheriting this.
 for width,height in [(1280,800),(1440,900),(1920,1080),(2560,1080),(390,844),(320,844)]:
  ctx=b.new_context(viewport={'width':width,'height':height},reduced_motion='reduce')
  page=ctx.new_page();page.goto(base,wait_until='domcontentloaded')
  box=page.locator('.home-hero').bounding_box()
  expected=max(446,min(height*.56,580)) if width<=768 else max(446,min(width*1446/2688,height*.9))
  assert abs(box['height']-expected)<1,(width,height,box,expected)
  intro_box=page.locator('.home-team-intro').bounding_box()
  assert abs(intro_box['y']-box['y']-box['height'])<1,(width,height)
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),(width,height)
  assert page.locator('.hero-bg').evaluate('v=>getComputedStyle(v).objectPosition')==('90% 50%' if width<=768 else '50% 50%')
  print(f'Hero height and section adjacency passed: {width}x{height}, {box["height"]:.1f}px',flush=True)
  ctx.close()
 # Browser toolbar height changes must not recrop a touch hero mid-swipe.
 ctx=b.new_context(viewport={'width':390,'height':844},has_touch=True,is_mobile=True)
 page=ctx.new_page();page.goto(base,wait_until='domcontentloaded')
 page.wait_for_function('document.querySelector(".home-hero").style.getPropertyValue("--hero-mobile-height")')
 initial=page.locator('.home-hero').bounding_box()['height']
 page.evaluate('scrollTo(0,100)')
 for height in (780,740,844):
  page.set_viewport_size({'width':390,'height':height});page.wait_for_timeout(100)
  assert abs(page.locator('.home-hero').bounding_box()['height']-initial)<.1,height
 page.set_viewport_size({'width':844,'height':390})
 page.wait_for_function('!document.querySelector(".home-hero").style.getPropertyValue("--hero-mobile-height")')
 page.set_viewport_size({'width':390,'height':844})
 page.wait_for_function('document.querySelector(".home-hero").style.getPropertyValue("--hero-mobile-height")')
 assert abs(page.locator('.home-hero').bounding_box()['height']-initial)<.1
 print('Touch hero toolbar-height stability and orientation reset passed',flush=True)
 ctx.close()
 # Exercise instant navigation, not just independent page loads. The header
 # deliberately survives transitions and its logo must follow the new page.
 for width,scheme in [(390,'light'),(390,'dark'),(900,'light'),(900,'dark'),(1440,'light'),(1440,'dark')]:
  for initial in ['/','/team/']:
   ctx=b.new_context(viewport={'width':width,'height':900},color_scheme=scheme,reduced_motion='reduce')
   page=ctx.new_page();page.goto(base+initial,wait_until='domcontentloaded')
   page.evaluate('window.__machHeaderAudit=document.querySelector(".md-header")')
   def check_navigation_logo(home):
    page.wait_for_function('(home)=>document.querySelector(".md-header [data-md-component=logo]").dataset.machHome===String(home)',arg=home)
    logo=page.locator('.md-header [data-md-component="logo"]')
    assert logo.count()==1 and logo.is_visible()==(width>=NAVIGATION_BREAKPOINT or not home)
    assert logo.get_attribute('aria-current')==('page' if home else None)
    assert page.evaluate('window.__machHeaderAudit===document.querySelector(".md-header")')
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
   check_navigation_logo(initial=='/')
   if initial!='/':
    page.locator('.md-header [data-md-component="logo"]').click()
    page.wait_for_url(base+'/');check_navigation_logo(True)
   page.locator('.home-project-links a[href$="Seraphina/"]').click()
   page.wait_for_url(base+'/Seraphina/');check_navigation_logo(False)
   page.go_back();page.wait_for_url(base+'/');check_navigation_logo(True)
   page.go_forward();page.wait_for_url(base+'/Seraphina/');check_navigation_logo(False)
   print(f'Instant navigation and Back/Forward logo visibility passed: {width}px, {scheme}, start {initial}',flush=True)
   ctx.close()
 ctx=b.new_context(viewport={'width':1440,'height':900},reduced_motion='reduce');page=ctx.new_page();page.goto(base,wait_until='domcontentloaded');page.wait_for_timeout(300)
 assert page.locator('.hero-bg').get_attribute('src') is None
 print('Reduced motion: no hero download; functional checks passed',flush=True)
 ctx.close()
 for width,motion_pref in [(1440,'no-preference'),(390,'no-preference'),(390,'reduce')]:
  ctx=b.new_context(viewport={'width':width,'height':900},reduced_motion=motion_pref)
  page=ctx.new_page();page.goto(base,wait_until='domcontentloaded')
  page.wait_for_timeout(200)
  hero=page.locator('.home-hero')
  def parallax_geometry():
   return hero.evaluate('''e=>{const r=e.getBoundingClientRect(),video=e.querySelector('.hero-bg'),v=video.getBoundingClientRect(),b=e.querySelector('.home-hero__inner'),s=getComputedStyle(video);return {top:r.top,bottom:r.bottom,height:r.height,videoTop:v.top,videoBottom:v.bottom,media:s.transform==='none'?0:new DOMMatrixReadOnly(s.transform).m42,brand:0,brandTransform:getComputedStyle(b).transform,timeline:s.animationTimeline,willChange:s.willChange}}''')
  start=parallax_geometry()
  assert abs(start['media'])<1 and abs(start['brand'])<1,start
  assert start['willChange']==('auto' if motion_pref=='reduce' else 'transform'),start
  # Exercise the first few pixels on a cold page, then leave/re-enter rest.
  # Geometry must remain continuous; scrolling must not change the crop/height.
  for y in (1,2,4,8,16,32,0,1,0):
   page.evaluate('(y)=>scrollTo(0,y)',y)
   page.wait_for_timeout(50)
   geometry=parallax_geometry()
   assert abs(geometry['top']-(start['top']-y))<.1,geometry
   assert abs(geometry['height']-start['height'])<.1,geometry
   expected=0 if motion_pref=='reduce' else y*(.18 if width<=768 else .24)
   assert abs(geometry['media']-expected)<.1,geometry
  for fraction in (.25,.6,.9):
   page.evaluate('(y)=>scrollTo(0,y)',start['height']*fraction)
   page.wait_for_timeout(100)
   geometry=parallax_geometry()
   travel=min(max(-geometry['top'],0),geometry['height'])
   if motion_pref=='reduce':
    assert geometry['media']==geometry['brand']==0 and geometry['brandTransform']=='none',geometry
   else:
    assert geometry['timeline']=='--hero-scroll',geometry
    assert abs(geometry['media']-travel*(.18 if width<=768 else .24))<1,geometry
    assert geometry['brandTransform']=='none',geometry
    # No uncovered strip, even near the bottom of the hero.
    assert geometry['videoTop']<=max(0,geometry['top'])+1,geometry
    assert geometry['videoBottom']>=geometry['bottom']-1,geometry
  assert page.locator('.hero-bg').get_attribute('src') is None
  assert hero.get_attribute('style').find('--hero-media-shift')==-1
  page.emulate_media(reduced_motion='reduce');page.wait_for_timeout(100)
  assert parallax_geometry()['media']==parallax_geometry()['brand']==0
  page.evaluate('scrollTo(0,0)');page.emulate_media(reduced_motion='no-preference');page.wait_for_timeout(100)
  assert abs(parallax_geometry()['media'])<1
  print(f'Hero parallax crop, scroll coverage and reduced-motion checks passed: {width}px, {motion_pref}',flush=True)
  ctx.close()
 for width,motion_pref,touch in [(1440,'no-preference',False),(1024,'no-preference',False),(390,'no-preference',True),(1440,'reduce',False),(1024,'no-preference',True)]:
  ctx=b.new_context(viewport={'width':width,'height':900},reduced_motion=motion_pref,has_touch=touch)
  page=ctx.new_page();page.goto(base,wait_until='domcontentloaded');page.wait_for_timeout(200)
  intro=page.locator('.home-team-intro')
  def team_geometry():
   return intro.evaluate('''e=>{const r=e.getBoundingClientRect(),i=e.querySelector('.home-team-intro__photo'),ir=i.getBoundingClientRect(),s=getComputedStyle(i);return {top:r.top,bottom:r.bottom,height:r.height,photoTop:ir.top,photoBottom:ir.bottom,media:s.transform==='none'?0:new DOMMatrixReadOnly(s.transform).m42,timeline:s.animationTimeline,willChange:s.willChange,contentTransform:getComputedStyle(e.querySelector('.home-team-intro__content')).transform}}''')
  start=team_geometry();animated=width>768 and motion_pref!='reduce' and not touch
  assert abs(start['media'])<.1,start
  assert start['willChange']==('transform' if animated else 'auto'),start
  for fraction in (0,.01,.25,.6,.9,0):
   page.evaluate('(y)=>scrollTo(0,y)',start['top']+start['height']*fraction)
   expected=start['height']*fraction*.2 if animated else 0
   page.wait_for_function('''expected=>{const s=getComputedStyle(document.querySelector('.home-team-intro__photo'));return Math.abs((s.transform==='none'?0:new DOMMatrixReadOnly(s.transform).m42)-expected)<.1}''',arg=expected)
   geometry=team_geometry()
   assert abs(geometry['height']-start['height'])<.1,geometry
   assert geometry['contentTransform']=='none',geometry
   if animated:
    assert geometry['timeline']=='--home-team-scroll',geometry
    assert geometry['photoTop']<=max(0,geometry['top'])+1,geometry
    assert geometry['photoBottom']>=geometry['bottom']-1,geometry
  page.emulate_media(reduced_motion='reduce');page.wait_for_timeout(100)
  assert team_geometry()['media']==0 and team_geometry()['willChange']=='auto'
  print(f'Team photo desktop parallax, static text, coverage and motion fallback passed: {width}px, {motion_pref}, touch={touch}',flush=True)
  ctx.close()
 for width in (1440,390):
  ctx=b.new_context(viewport={'width':width,'height':900})
  page=ctx.new_page();page.goto(base,wait_until='domcontentloaded')
  # Headless CI has no HDR display. Exercise the real HDR CSS rules in-page;
  # this checks the branch and mask geometry, not physical screen luminance.
  page.evaluate('''()=>{for(const sheet of document.styleSheets){let rules;try{rules=sheet.cssRules}catch{continue}for(const rule of rules){if(rule.type===CSSRule.MEDIA_RULE&&rule.conditionText==="(dynamic-range: high)")rule.media.mediaText="all";}}}''')
  hdr=page.locator('.home-hero__title').evaluate('''e=>{const s=getComputedStyle(e,"::after"),r=e.getBoundingClientRect();return {display:s.display,opacity:s.opacity,mask:s.maskImage,image:s.backgroundImage,pointer:s.pointerEvents,width:parseFloat(s.width),height:parseFloat(s.height),titleWidth:r.width,titleHeight:r.height}}''')
  assert hdr['display']=='block' and hdr['opacity']=='0.5' and hdr['pointer']=='none',hdr
  assert 'logo-hero-hdr-mask.png' in hdr['mask'] and 'white-7.5x.jpg' in hdr['image'],hdr
  page.locator('.home-hero__logo').evaluate('i=>i.decode()')
  assert page.locator('.home-hero__logo').evaluate('i=>[i.naturalWidth,i.naturalHeight]')==[2048,636]
  assert abs(hdr['width']-hdr['titleWidth'])<1 and abs(hdr['height']-hdr['titleHeight'])<1,hdr
  accent=page.locator('.home-hero__title').evaluate('''e=>{const s=getComputedStyle(e,"::before");return {display:s.display,opacity:s.opacity,mask:s.maskImage,image:s.backgroundImage,pointer:s.pointerEvents,width:parseFloat(s.width),height:parseFloat(s.height)}}''')
  assert accent['display']=='block' and accent['opacity']=='0.5' and accent['pointer']=='none',accent
  assert 'logo-hero-hdr-accent-mask.png' in accent['mask'] and 'red-7.5x.jpg' in accent['image'],accent
  assert abs(accent['width']-hdr['width'])<1 and abs(accent['height']-hdr['height'])<1,accent
  print(f'Hero HDR lettering and red circle 50-percent alignment passed: {width}px',flush=True)
  page.goto(base+'/team/',wait_until='domcontentloaded')
  assert page.locator('.md-logo .mach-logo__hdr').evaluate_all('(els)=>els.every(e=>getComputedStyle(e).display==="none")')
  page.emulate_media(color_scheme='dark')
  page.wait_for_function('()=>document.body.dataset.mdColorScheme==="slate"')
  page.evaluate('''()=>{for(const sheet of document.styleSheets){let rules;try{rules=sheet.cssRules}catch{continue}for(const rule of rules){if(rule.type===CSSRule.MEDIA_RULE&&rule.conditionText==="(dynamic-range: high)")rule.media.mediaText="all";}}}''')
  nav_hdr=page.locator('.md-logo .mach-logo__hdr').evaluate_all('(els)=>els.map(e=>({opacity:getComputedStyle(e).opacity,display:getComputedStyle(e).display}))')
  assert len(nav_hdr)>=2 and all(s['opacity']=='0.5' and s['display']=='block' for s in nav_hdr),nav_hdr
  print(f'Top-bar and drawer HDR match hero at 50 percent: {width}px',flush=True)
  ctx.close()
 ctx=b.new_context(viewport={'width':1440,'height':900},color_scheme='light')
 page=ctx.new_page();page.goto(base,wait_until='domcontentloaded')
 plot=page.locator('img[data-plot-dark-src]')
 plot.scroll_into_view_if_needed()
 def check_theme(theme):
  page.wait_for_function('(theme)=>document.querySelector("img[data-plot-dark-src]")?.dataset.plotTheme===theme',arg=theme)
  assert plot.evaluate('(img)=>!img.closest("a") || img.closest("a").href===img.src')
  page.wait_for_function('()=>{const img=document.querySelector("img[data-plot-dark-src]");return img.complete&&img.naturalWidth>0}')
 # Only OS appearance selects the scheme. Legacy saved overrides must not win.
 check_theme('light')
 assert page.locator('label[for^="__palette"]').count()==0
 page.emulate_media(color_scheme='dark');check_theme('dark')
 page.emulate_media(color_scheme='light');check_theme('light')
 for system,old_index,old_scheme in [('light',2,'slate'),('dark',1,'default')]:
  page.emulate_media(color_scheme=system)
  page.evaluate('''({index,scheme})=>__md_set('__palette',{index,color:{media:scheme==='slate'?'(prefers-color-scheme: dark)':'(prefers-color-scheme: light)',scheme,primary:'indigo',accent:'indigo'}})''',{'index':old_index,'scheme':old_scheme})
  page.reload(wait_until='domcontentloaded');check_theme(system)
  assert page.evaluate('__md_get("__palette").index')==0
  assert page.locator('body').get_attribute('data-md-color-scheme')==('slate' if system=='dark' else 'default')
 # An open viewer on a test page also follows the system preference.
 page.goto(base+'/Seraphina/oct-4-hotfire/',wait_until='domcontentloaded')
 plot=page.locator('img[data-plot-dark-src]').last
 link=page.get_by_role('button',name='Expand plot:',exact=False).last
 link.focus();page.keyboard.press('Enter')
 page.get_by_role('button',name='Zoom in',exact=True).click()
 page.emulate_media(color_scheme='light');check_theme('light')
 assert page.locator('dialog[open] img').get_attribute('src')==plot.get_attribute('src')
 assert page.locator('[data-plot-zoom]').inner_text()=='2×'
 page.emulate_media(color_scheme='dark');check_theme('dark')
 assert page.locator('dialog[open] [data-plot-original]').get_attribute('href')==plot.get_attribute('src')
 assert page.locator('.plot-viewer__stage').evaluate('(e)=>getComputedStyle(e).backgroundColor')=='rgb(11, 13, 15)'
 page.keyboard.press('Escape');assert link.evaluate('(e)=>e===document.activeElement')
 print('System-only appearance: no theme controls, OS changes, stale preferences, keyboard and open viewer passed',flush=True)
 ctx.close()
 b.close()
