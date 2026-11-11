"""Run: python3 tests/check_positions.py (Playwright and /usr/bin/chromium)."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import json
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(ROOT)))
Thread(target=server.serve_forever,daemon=True).start()
skills=dict.fromkeys(['creation','shooting','rebound','speed','defense','stamina'],3)
legacy=[dict(id=str(i),name=f'Joueur {i}',height=180,level=3,skills=skills,present=True) for i in range(10)]
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
  page=browser.new_page();errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(f'http://127.0.0.1:{server.server_port}/basket-equipes-autonome.html')
  def upload(data):
   page.locator('#importFile').set_input_files(dict(name='players.json',mimeType='application/json',buffer=json.dumps(data).encode()))
   page.wait_for_function('document.getElementById("importFile").value === ""')
  # Storage migration, historical bare arrays, v1 objects, no positions or no gender.
  page.evaluate('(v)=>localStorage.setItem("basket-balancer-v1",JSON.stringify(v))',legacy)
  page.reload()
  assert page.evaluate('players.length===10&&players.every(p=>p.primaryPosition===null&&p.secondaryPositions.length===0)')
  for data in [legacy,dict(version=1,players=legacy)]:
   upload(data)
   assert page.locator('.player').count()==10
  upload([dict(v,positions=[3,1,5,3]) for v in legacy])
  assert page.evaluate('players.every(p=>p.primaryPosition===3&&JSON.stringify(p.secondaryPositions)==="[1,5]")')
  page.reload()
  assert page.evaluate('players[0].primaryPosition')==3
  # Explicit new fields take precedence over old compatibility fields; invalid/duplicate values are removed.
  upload([dict(v,positions=[5],primaryPosition='2',secondaryPositions=[2,1,'4',4,0,6,True,None,'<img>']) for v in legacy])
  assert page.evaluate('players.every(p=>p.primaryPosition===2&&JSON.stringify(p.secondaryPositions)==="[1,4]")')
  page.locator('[data-edit="0"]').click()
  assert page.locator('#primaryPosition').input_value()=='2'
  assert page.locator('#position_2').is_disabled()
  assert page.locator('#position_1').is_checked()
  page.locator('#primaryPosition').select_option('1')
  assert not page.locator('#position_1').is_checked()
  page.locator('#position_3').check()
  page.locator('#saveBtn').click()
  assert page.evaluate('players[0].primaryPosition')==1
  assert page.evaluate('players[0].secondaryPositions')==[3,4]
  assert page.locator('#positions input:checked').count()==0
  # New players require a unique primary position.
  page.locator('#playerName').fill('Nouveau')
  alerts=[]
  def dismiss(dialog):alerts.append(dialog.message);dialog.dismiss()
  page.on('dialog',dismiss)
  page.locator('#saveBtn').click()
  assert alerts and page.locator('.player').count()==10
  page.locator('#primaryPosition').select_option('5')
  page.locator('#position_2').check()
  page.locator('#position_4').check()
  page.locator('#saveBtn').click()
  assert page.evaluate('players.at(-1).primaryPosition')==5
  assert page.evaluate('players.at(-1).secondaryPositions')==[2,4]
  with page.expect_download() as event:page.locator('#exportBtn').click()
  exported=json.loads(Path(event.value.path()).read_text())
  assert exported['version']==1
  assert exported['players'][-1]['positions']==[5,2,4]
  upload(exported)
  assert page.evaluate('players.at(-1).primaryPosition')==5
  page.reload()
  assert page.evaluate('players.at(-1).secondaryPositions')==[2,4]
  # V1 must be completely insensitive to secondary positions, with the same random stream.
  assert page.evaluate('''()=>{
   const generate=present=>{const old=Math.random;let seed=31;Math.random=()=>((seed=Math.imul(seed,1664525)+1013904223>>>0)/4294967296);try{return ENGINE_V1.generate({present,count:2,priority:'roles'})}finally{Math.random=old}};
   return JSON.stringify(generate(players))===JSON.stringify(generate(players.map(p=>({...p,secondaryPositions:[],positions:p.primaryPosition?[p.primaryPosition]:[]}))));
  }''')
  # Verify the scoring hierarchy using actual player attributes, not only synthetic score tuples.
  assert page.evaluate('''()=>{
   const base=players.slice(0,4).map(p=>({...p,height:180,level:3,primaryPosition:1,secondaryPositions:[],skills:Object.fromEntries(SKILLS.map(([k])=>[k,3]))}));
   const mixed=p=>[[p[0],p[2]],[p[1],p[3]]],grouped=p=>[p.slice(0,2),p.slice(2)];
   const height=base.map((p,i)=>({...p,height:i<2?160:200,level:i%2?5:1}));
   if(ENGINE_V2.compare(ENGINE_V2.score(mixed(height)),ENGINE_V2.score(grouped(height)))>=0)return false;
   for(const [k] of SKILLS){const data=base.map((p,i)=>({...p,skills:{...p.skills,[k]:i<2?1:5},level:i%2?5:1}));if(ENGINE_V2.compare(ENGINE_V2.score(mixed(data)),ENGINE_V2.score(grouped(data)))>=0)return false}
   const level=base.map((p,i)=>({...p,level:i<2?1:5,secondaryPositions:i%2?[2]:[3]}));
   const primary=base.map((p,i)=>({...p,primaryPosition:i<2?1:2,secondaryPositions:i%2?[4]:[5]}));
   const secondary=base.map((p,i)=>({...p,secondaryPositions:i<2?[2]:[3]}));
   return [level,primary,secondary].every(data=>ENGINE_V2.compare(ENGINE_V2.score(mixed(data)),ENGINE_V2.score(grouped(data)))<0);
  }''')
  # Both engines: no duplicates, absent players excluded, balanced counts even with unknown roles.
  upload([dict(v,positions=[1,2] if i%2 else [],present=i!=9) for i,v in enumerate(legacy)])
  for engine in ['1.0','2.0']:
   page.locator('#engineVersion').select_option(engine)
   assert page.locator('#priority').is_disabled()==(engine=='2.0')
   for count in [2,3,4]:
    page.locator('#teamCount').select_option(str(count))
    page.locator('#generateBtn').click()
    result=page.evaluate('lastResult');ids=sum(result['teams'],[]);sizes=list(map(len,result['teams']))
    assert len(ids)==len(set(ids))==9 and '9' not in ids
    assert len(sizes)==count and max(sizes)-min(sizes)<=1
    assert result['engineVersion']==engine
  # AI receives both role types; no real provider call.
  def provider(route):
   prompt=route.request.post_data_json['messages'][1]['content']
   assert 'primaryPosition' in prompt and 'secondaryPositions' in prompt
   answer=dict(teams=[['0','1','2'],['3','4'],['5','6'],['7','8']],bench=[])
   route.fulfill(json=dict(choices=[dict(message=dict(content=json.dumps(answer)))]))
  page.route('https://api.openai.com/**',provider)
  page.locator('#apiKey').fill('test-placeholder')
  page.locator('#aiBtn').click();page.wait_for_function('lastResult.source==="ia"')
  for width in [390,1280]:
   page.set_viewport_size(dict(width=width,height=900))
   assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
  assert not errors,errors
  browser.close()
finally:server.shutdown()
print('PASS: primary/secondary CRUD, all legacy imports/storage, JSON round trip, V1 ignores secondary, V2 priority hierarchy, both engines/2-4 teams, mocked AI, responsive.')
