"""Run: python3 tests/check_teamwork.py (Playwright and Chromium)."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import json
import subprocess
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
current=(ROOT/'basket-equipes-autonome.html').read_text()
previous=subprocess.check_output(['git','show','cdcf9b5:basket-equipes-autonome.html'],cwd=ROOT,text=True)
for engine in ['ENGINE_V1','ENGINE_V2']:
 def implementation(html):
  start=html.index('const '+engine+'=')
  return html[start:html.index('\n})();',start)+len('\n})();')]
 assert implementation(current)==implementation(previous),engine+' changed'
server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(ROOT)))
Thread(target=server.serve_forever,daemon=True).start()
base=[dict(id=str(i),name=f'Joueur {i}',height=180,level=3,primaryPosition=1,secondaryPositions=[],skills=dict.fromkeys(['creation','shooting','rebound','speed','defense','stamina'],3),present=True) for i in range(9)]
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
  page=browser.new_page();errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(f'http://127.0.0.1:{server.server_port}/basket-equipes-autonome.html')
  def upload(data):
   page.locator('#importFile').set_input_files(dict(name='players.json',mimeType='application/json',buffer=json.dumps(data).encode()))
   page.wait_for_function('document.getElementById("importFile").value === ""')
  assert page.locator('#appVersion').inner_text()=='Version 2.0.1'
  assert page.locator('#teamwork').input_value()=='0'
  # Pre-feature browser state and both import formats migrate to balanced.
  page.evaluate('(data)=>localStorage.setItem("basket-balancer-v1",JSON.stringify(data))',base)
  page.reload()
  assert page.evaluate('players.every(p=>p.teamwork===0)')
  for data in [base,dict(version=1,players=base)]:
   upload(data)
   assert page.evaluate('players.length===9&&players.every(p=>p.teamwork===0)')
  # Editing, all three labels, cancellation, creation, persistence.
  page.locator('[data-edit="0"]').click()
  for value,label in [(-1,'Trop perso'),(0,'Équilibré'),(1,'Trop altruiste')]:
   page.locator('#teamwork').fill(str(value))
   assert label in page.locator('#teamworkValue').inner_text()
   assert page.locator('#teamwork').get_attribute('aria-valuetext')==label
  page.locator('#saveBtn').click()
  assert page.evaluate('players[0].teamwork')==1
  assert page.locator('#teamwork').input_value()=='0'
  page.reload();page.locator('[data-edit="0"]').click()
  assert page.locator('#teamwork').input_value()=='1'
  page.locator('#teamwork').fill('-1');page.locator('#cancelBtn').click()
  assert page.evaluate('players[0].teamwork')==1
  page.locator('#playerName').fill('Perso');page.locator('#primaryPosition').select_option('2')
  page.locator('#teamwork').fill('-1');page.locator('#saveBtn').click()
  assert page.evaluate('players.at(-1).teamwork')==-1
  with page.expect_download() as event:page.locator('#exportBtn').click()
  exported=json.loads(Path(event.value.path()).read_text())
  assert exported['version']==1 and exported['players'][-1]['teamwork']==-1
  upload(exported)
  assert page.evaluate('players[0].teamwork===1&&players.at(-1).teamwork===-1')
  upload([dict(player,teamwork=value) for player,value in zip(base,[-1,0,1,'-1','1',99,None,True,{}])])
  assert page.evaluate('players.map(p=>p.teamwork)')==[-1,0,1,-1,1,0,0,0,0]
  # Existing engines ignore the new attribute under identical random streams.
  assert page.evaluate('''()=>{
   const run=(engine,present)=>{let seed=17;const old=Math.random;Math.random=()=>((seed=Math.imul(seed,1664525)+1013904223>>>0)/4294967296);try{return engine.generate({present,count:2,priority:'balanced'})}finally{Math.random=old}};
   return [ENGINE_V1,ENGINE_V2].every(engine=>JSON.stringify(run(engine,players))===JSON.stringify(run(engine,players.map(p=>({...p,teamwork:0})))));
  }''')
  # V3 actively prefers mixed tendencies over stacking the extremes; all-neutral recovers V2 scoring.
  assert page.evaluate('''()=>{
   const p=players.slice(0,6).map((p,i)=>({...p,teamwork:[-1,-1,0,0,1,1][i]}));
   const good=[[p[0],p[2],p[4]],[p[1],p[3],p[5]]],bad=[p.slice(0,3),p.slice(3)];
   const neutral=good.map(t=>t.map(p=>({...p,teamwork:0})));
   return ENGINE_V3.compare(ENGINE_V3.score(good),ENGINE_V3.score(bad))<0&&JSON.stringify(ENGINE_V3.score(neutral))===JSON.stringify(ENGINE_V2.score(neutral));
  }''')
  upload([dict(player,teamwork=[-1,-1,0,0,1,1][i]) for i,player in enumerate(base[:6])])
  page.locator('#engineVersion').select_option('3.0')
  assert page.locator('#priority').is_disabled()
  assert 'jeu en équipe' in page.locator('#engineHelp').inner_text()
  page.locator('#generateBtn').click()
  assert page.evaluate('lastResult.teams.every(t=>JSON.stringify(t.map(id=>players.find(p=>p.id===id).teamwork).sort())==="[-1,0,1]")')
  # Odd counts, unknown attribute and absent players still form complete unique teams.
  upload([dict(player,teamwork=(i%3)-1,present=i!=8) for i,player in enumerate(base)])
  for count in ['2','3','4']:
   page.locator('#teamCount').select_option(count);page.locator('#generateBtn').click()
   result=page.evaluate('lastResult');ids=sum(result['teams'],[]);sizes=list(map(len,result['teams']))
   assert result['engineVersion']=='3.0'
   assert len(ids)==len(set(ids))==8 and '8' not in ids
   assert max(sizes)-min(sizes)<=1
  for width in [390,1280]:
   page.set_viewport_size(dict(width=width,height=900))
   assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
  assert not errors,errors
  browser.close()
finally:server.shutdown()
print('PASS: V1/V2 source unchanged, legacy defaults, three-state CRUD/storage/JSON, V1/V2 ignore teamwork, V3 balances tendencies, complete teams, responsive.')
