"""Run with: python3 tests/check_engine_versions.py (Playwright + Chromium)."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import subprocess
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
# Historical implementation before the engine selector was introduced.
previous=subprocess.check_output(['git','show','755f4b1:basket-equipes-autonome.html'],cwd=ROOT,text=True)
server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(ROOT)))
Thread(target=server.serve_forever,daemon=True).start()
base=f'http://127.0.0.1:{server.server_port}'
try:
 with sync_playwright() as p:
  # Disable JIT for exact historical comparisons: refactoring can change floating-point optimization and tie-breaking.
  browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox','--js-flags=--jitless'])
  page=browser.new_page()
  old=browser.new_page()
  old.route('**/previous.html',lambda route:route.fulfill(body=previous,content_type='text/html'))
  old.goto(base+'/previous.html')
  page.goto(base+'/basket-equipes-autonome.html')
  assert page.locator('#engineVersion').input_value()=='1.0'
  assert page.locator('#engineVersion option').all_text_contents()==['Moteur v1.0','Moteur v2.0']
  fixture='''()=>{
   players=Array.from({length:11},(_,i)=>({id:String(i),name:'Joueur '+i,height:160+i*5,level:1+i%5,gender:'unspecified',primaryPosition:1+i%5,secondaryPositions:[],positions:[1+i%5],present:i!==10,skills:{creation:1+i%5,shooting:3,rebound:4,speed:2,defense:3,stamina:4}}));render();
  }'''
  page.evaluate(fixture)
  old.evaluate(fixture)
  # Identical RNG stream: every priority and team count must retain exactly the old result.
  generate='''()=>{const original=Math.random;let seed=417;Math.random=()=>((seed=Math.imul(seed,1664525)+1013904223>>>0)/4294967296);try{compute();return lastResult.teams}finally{Math.random=original}}'''
  for priority in ['balanced','roles','level','height','speed']:
   for count in ['2','3','4']:
    for target in [page,old]:
     target.locator('#priority').select_option(priority)
     target.locator('#teamCount').select_option(count)
    a=page.evaluate(generate); b=old.evaluate(generate)
    if a!=b:
     print('MISMATCH',priority,count,a,b,flush=True)
    assert a==b,(priority,count)
  assert page.evaluate('lastResult.engineVersion')=='1.0'
  assert 'Moteur v1.0' in page.locator('#resultMeta').inner_text()
  page.locator('.move-player').first.select_option('1')
  assert page.evaluate('lastResult.engineVersion')=='1.0'
  assert 'Moteur v1.0' in page.locator('#resultMeta').inner_text()
  page.locator('#shuffleBtn').click()
  assert page.evaluate('lastResult.engineVersion')=='1.0'
  # Extend only the test page's registry to verify dispatch to a future implementation.
  html=(ROOT/'basket-equipes-autonome.html').read_text().replace("'1.0':Object.freeze({label:'Moteur v1.0',...ENGINE_V1})", "'1.0':Object.freeze({label:'Moteur v1.0',...ENGINE_V1}),'test':{label:'Test engine',generate:({present,count,priority})=>{window.received={count,priority};return {teams:[present.map(p=>p.id)],bench:[],source:'local'}}}")
  page.route('**/extended.html',lambda route:route.fulfill(body=html,content_type='text/html'))
  page.goto(base+'/extended.html')
  page.evaluate(fixture)
  page.locator('#engineVersion').select_option('test')
  page.locator('#generateBtn').click()
  assert page.evaluate('lastResult.engineVersion')=='test'
  assert page.evaluate('window.received')=={'count':2,'priority':'balanced'}
  assert page.locator('.team').count()==1
  for width in [390,1280]:
   page.set_viewport_size({'width':width,'height':900})
   assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
  browser.close()
finally:
 server.shutdown()
print('PASS: v1.0 exactly matches historical algorithm for 15 seeded scenarios; selector, dispatch, shuffle, manual edits, responsive layout.')
