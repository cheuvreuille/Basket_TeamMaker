"""Run: python3 tests/check_whatsapp_prototype.py (Playwright and Chromium)."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import re
import subprocess
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
previous=subprocess.check_output(['git','show','dc30c8c:basket-equipes-autonome.html'],cwd=ROOT,text=True)
current=(ROOT/'basket-equipes-autonome.html').read_text()
assert re.findall(r'<script>(.*?)</script>',current,re.S)[:2]==re.findall(r'<script>(.*?)</script>',previous,re.S)
class QuietHandler(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(ROOT)))
Thread(target=server.serve_forever,daemon=True).start()
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
  page=browser.new_page(viewport=dict(width=1280,height=960));errors=[];external=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.on('request',lambda r:external.append(r.url) if not r.url.startswith('http://127.0.0.1:') else None)
  page.goto(f'http://127.0.0.1:{server.server_port}/basket-equipes-autonome.html')
  assert page.locator('#appVersion').inner_text()=='Version 2.2'
  # Normal operations, navigation and storage are independent of the prototype.
  storage=page.evaluate('JSON.stringify({...localStorage})')
  state=page.evaluate('JSON.stringify({players,lastResult,teamColors})')
  assert page.locator('[role=tab]').count()==3
  page.locator('#whatsappTab').click()
  assert page.locator('#whatsappPanel').is_visible()
  assert not page.locator('#historyPanel').is_visible() and not page.locator('#makerPanel').is_visible()
  assert 'MAQUETTE — À NE PAS UTILISER' in page.locator('.wa-warning').inner_text()
  assert page.locator('#waFetch').is_disabled()
  assert not page.locator('#waResults').is_visible()
  page.locator('summary').filter(has_text='Démo fictive, sans connexion').click()
  page.locator('#waWeek').fill('2026-11-21');page.locator('#waWeek').press('Tab')
  assert page.locator('#waWeek').input_value()=='2026-11-16'
  if not page.locator('#waDemo').is_visible():page.locator('summary').filter(has_text='Démo fictive, sans connexion').click()
  page.locator('#waDemo').click()
  assert page.locator('#waResults').is_visible()
  assert 'DONNÉES FICTIVES' in page.locator('#waResults').inner_text()
  assert page.locator('.wa-answer').count()==5
  assert page.locator('.wa-training').count()==3
  assert page.locator('.wa-absence').count()==1 and page.locator('.wa-injury').count()==1
  assert page.locator('.wa-answer li').count()==7
  assert page.locator('#waPollTotals').inner_text()=='5 réponses · 5 votants distincts · 7 choix exprimés'
  assert 'Aucun votant' in page.locator('.wa-training').last.inner_text()
  assert '17/11/2026' in page.locator('.wa-training').first.inner_text()
  assert page.evaluate('JSON.stringify({...localStorage})')==storage
  assert page.evaluate('JSON.stringify({players,lastResult,teamColors})')==state
  # All tab directions work without changing existing tab handlers or business functions.
  for source,key,expected in [('whatsappTab','ArrowRight','makerTab'),('makerTab','ArrowRight','historyTab'),('historyTab','ArrowRight','whatsappTab'),('whatsappTab','Home','makerTab'),('makerTab','End','whatsappTab'),('whatsappTab','ArrowLeft','historyTab')]:
   page.locator('#'+source).click();page.locator('#'+source).press(key)
   assert page.locator('#'+expected).get_attribute('aria-selected')=='true'
   assert page.locator('[role=tabpanel]:visible').count()==1
  page.locator('#whatsappTab').click()
  assert page.locator('#waResults').is_visible()
  # View model supports 2 sessions, arbitrary extra choices and multi-answer votes without inferred attendance.
  model=page.evaluate('''()=>whatsappPrototype.normalizePoll({id:'poll',question:'Présences ?',groupName:'Groupe',options:[
   {id:'a',label:'Mardi',type:'training',voters:[{id:'1',name:'Alex'},{id:'1',name:'Alex'}]},
   {id:'b',label:'Jeudi',type:'training',voters:[{id:'1',name:'Alex'}]},
   {id:'c',label:'Absence',type:'absence',voters:[]},
   {id:'d',label:'Autre réponse',type:'custom',voters:[]}]})''')
  assert len(model['options'][0]['voters'])==1 and len(model['options'][1]['voters'])==1
  assert model['options'][3]['type']=='other'
  assert page.evaluate('''()=>{try{whatsappPrototype.normalizePoll({id:'p',question:'?',groupName:'g',options:[{id:'a',label:'Oui',voteCount:3}]});return false}catch{return true}}''')
  assert page.evaluate('''()=>{try{whatsappPrototype.normalizePoll({id:'p',question:'?',groupName:'g',options:[{id:'a',label:'Oui',voters:[{name:'Sans identifiant'}]}]});return false}catch{return true}}''')
  page.locator('#waWeek').fill('2026-11-23');page.locator('#waWeek').press('Tab')
  assert not page.locator('#waResults').is_visible()
  if not page.locator('#waDemo').is_visible():page.locator('summary').filter(has_text='Démo fictive, sans connexion').click()
  page.locator('#waDemo').click()
  assert '24/11/2026' in page.locator('.wa-training').first.inner_text()
  for width in [1280,390]:
   page.set_viewport_size(dict(width=width,height=960))
   assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
   page.locator('#whatsappPanel').screenshot(path=f'/tmp/whatsapp-prototype-{width}.png')
  page.locator('#waClear').click()
  assert not page.locator('#waResults').is_visible()
  page.reload();page.locator('#whatsappTab').click()
  assert not page.locator('#waResults').is_visible()
  assert not external and not errors,(external,errors)
  browser.close()
finally:server.shutdown()
print('PASS: existing scripts unchanged, three-tab navigation, clear prototype/demo labels, no live request, week boundaries, voters per answer, multivotes, validation, no persistence or presence changes, responsive.')
