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
args=parser.parse_args()
out=Path(args.output);out.mkdir(exist_ok=True)
base=args.url.rstrip('/')
with sync_playwright() as p:
 b=p.chromium.launch(executable_path=args.chrome,headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
 for width,scheme in [(1440,'light'),(390,'light'),(390,'dark')]:
  ctx=b.new_context(viewport={'width':width,'height':900},color_scheme=scheme)
  page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  for path in ['/','/team/','/sponsors/','/Seraphina/aug-20-hotfire/','/timeline/','/SPRINT/']:
   page.goto(base+path,wait_until='domcontentloaded');page.wait_for_timeout(500)
   assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), (path,'overflow')
   assert page.locator('[data-mach-drawer-toggle]').is_visible() == (width < 1220)
   if path=='/':
    sections=page.locator('.md-content section').evaluate_all('(s)=>s.map(e=>e.className)');assert sections[0]=='video-showcase',sections
    if width==390:assert page.locator('.hero-bg').get_attribute('src') is None
    hero=page.locator('[data-hero-motion]');hero.click();page.wait_for_timeout(300)
    hero.click();page.wait_for_timeout(300)
    assert page.locator('.slideshow-image').first.get_attribute('src').endswith('/SPRINT/electronics/overview.webp')
    assert page.locator('.slideshow-image').evaluate_all('(images)=>images.every(i=>getComputedStyle(i).objectFit==="contain"&&getComputedStyle(i).maxHeight==="none")')
    frame=page.locator('.image-slideshow').bounding_box();assert abs(frame['width']-frame['height'])<1 and frame['width']<=700
    if width==1440:assert abs(frame['width']-700)<1
    for img in page.locator('.slideshow-image').all():
     box=img.bounding_box();assert abs(box['width']-frame['width'])<1 and abs(box['height']-frame['height'])<1
    page.locator('[data-slide-next]').click();assert 'tank assembly' in page.locator('.slideshow-caption').inner_text()
    page.locator('[data-slide-previous]').click()
   if path=='/team/':
    current=page.locator('.team-leads').inner_text();former=page.locator('.former-members-grid').inner_text()
    assert 'Zeul' not in current and 'Audrey' not in current and 'Safety Officer' in current and 'Operations Director' in current
    assert 'Zeul Mordasiewicz' in former and 'Audrey Abergel-Preston' in former
   if path=='/Seraphina/aug-20-hotfire/':
    controls=page.get_by_role('button',name='Expand plot:',exact=False);assert controls.count()==2
    controls.nth(1).click();page.wait_for_timeout(300)
    assert page.locator('dialog').is_visible()
    w=page.locator('dialog img').evaluate('(i)=>i.width')
    page.get_by_role('button',name='Zoom in',exact=True).click();page.wait_for_timeout(100)
    assert page.locator('dialog img').evaluate('(i)=>i.width')>w*1.9
    page.screenshot(path=str(out/f'viewer-{width}-{scheme}.png'))
    page.keyboard.press('Escape');assert not page.locator('dialog').is_visible()
    assert controls.nth(1).evaluate('(e)=>e===document.activeElement')
   if path=='/timeline/':
    page.locator('[data-filter="project"]').select_option('Seraphina')
    page.locator('[data-filter="type"]').select_option('hotfire')
    count=page.locator('.gare-timeline__event:visible').count();assert count==2,count
    page.locator('[data-filter="year"]').select_option('2018');assert page.locator('.gare-timeline__event:visible').count()==0
    page.get_by_role('button',name='Clear filters').click();assert page.locator('.gare-timeline__event:visible').count()>30
    page.locator('[data-filter="year"]').select_option('2026')
   for y in range(0,min(page.evaluate('document.body.scrollHeight'),6500),700):page.evaluate('(y)=>scrollTo(0,y)',y);page.wait_for_timeout(60)
   page.wait_for_timeout(250);page.evaluate('scrollTo(0,0)')
   slug=path.strip('/').replace('/','-')or'home'
   page.screenshot(path=str(out/f'{slug}-{width}-{scheme}.png'),full_page=True)
   page.add_script_tag(url='https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.3/axe.min.js')
   axe=page.evaluate('async()=>{const r=await axe.run(document,{runOnly:{type:"tag",values:["wcag2a","wcag2aa","wcag21aa"]}});return r.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary})).slice(0,3)}))}')
   print(json.dumps({'page':path,'width':width,'scheme':scheme,'errors':errors,'axe':axe}),flush=True)
   assert not errors, errors
   assert not axe, axe
  if width==390:
   page.locator('[data-mach-drawer-toggle]').click();page.keyboard.press('Escape');assert not page.locator('#__drawer').is_checked()
  ctx.close()
 ctx=b.new_context(viewport={'width':1440,'height':900},reduced_motion='reduce');page=ctx.new_page();page.goto(base,wait_until='domcontentloaded');page.wait_for_timeout(300)
 assert page.locator('.hero-bg').get_attribute('src') is None
 print('Reduced motion: no hero download; functional checks passed',flush=True)
 b.close()
