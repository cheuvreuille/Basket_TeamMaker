"""Run: python3 tests/check_whatsapp_bridge.py. Browser flow with a simulated Node API."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import json
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
class QuietHandler(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(ROOT)))
Thread(target=server.serve_forever,daemon=True).start()
people=[dict(id=f'p{i}',name=name,height=180,level=3,positions=[1],present=i in (1,2)) for i,name in enumerate(['Alex','Sam','Inconnu','Tom'])]
poll=dict(id='poll-1',groupId='basket@g.us',groupName='Basket',question='Présences mardi et jeudi',createdAt='2026-11-17T12:00:00Z',checkedAt='2026-11-17T13:00:00Z',availability='votes_returned',options=[
 dict(id='0',label='Mardi',type='training',voters=[dict(id='a@lid',name='Alex'),dict(id='t@lid',name='Tom')]),
 dict(id='1',label='Jeudi',type='training',voters=[dict(id='a@lid',name='Alex')]),
 dict(id='2',label='Absent',type='absence',voters=[dict(id='s@lid',name='Sam')])])
state={'ready':False,'group':None,'mapping':{'unknown@lid':'p2'},'fail_votes':False,'poll':poll}
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
  page=browser.new_page(viewport=dict(width=1280,height=960));errors=[];calls=[]
  page.on('pageerror',lambda error:errors.append(str(error)))
  def api(route):
   from urllib.parse import urlparse
   request=route.request;path=urlparse(request.url).path;calls.append((request.method,path))
   if path.endswith('/connect'):return route.fulfill(status=202,json={'state':'connecting'})
   if path.endswith('/status'):return route.fulfill(json={'state':'ready' if state['ready'] else 'qr','qrImage':None if state['ready'] else 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aX0kAAAAASUVORK5CYII=','groupId':state['group']})
   if path.endswith('/groups'):return route.fulfill(json={'groups':[{'id':'basket@g.us','name':'Basket'}]})
   if path.endswith('/group'):state['group']=request.post_data_json['groupId'];return route.fulfill(json={'id':state['group']})
   if path.endswith('/mapping'):
    if request.method=='POST':state['mapping']=request.post_data_json['mapping']
    return route.fulfill(json={'mapping':state['mapping']})
   if path.endswith('/polls'):return route.fulfill(json={'polls':[{'id':'poll-1','question':poll['question'],'createdAt':poll['createdAt']}],'scannedMessages':500})
   if path.endswith('/poll'):
    if state['fail_votes']:return route.fulfill(status=502,json={'error':'Votes non vérifiés'})
    return route.fulfill(json=state['poll'])
   return route.fulfill(status=404,json={'error':'Unknown API'})
  page.route('**/api/wa/**',api)
  base=f'http://127.0.0.1:{server.server_port}'
  page.goto(base+'/basket-equipes-autonome.html')
  page.locator('#importFile').set_input_files(dict(name='players.json',mimeType='application/json',buffer=json.dumps(people).encode()))
  page.wait_for_function('document.getElementById("importFile").value===""')
  baseline=page.evaluate('players.map(p=>p.present)')
  page.locator('#whatsappTab').click();page.locator('#waServiceUrl').fill(base);page.locator('#waServiceUrl').press('Tab')
  page.locator('#waConnect').click();page.wait_for_function('!document.getElementById("waQrBox").hidden')
  assert 'Scan' in page.locator('#waQrBox').inner_text() or page.locator('#waQr').is_visible()
  state['ready']=True;page.locator('#waConnect').click();page.wait_for_function('!document.getElementById("waGroup").disabled')
  assert not page.locator('#waQrBox').is_visible()
  page.locator('#waGroup').select_option('basket@g.us');page.wait_for_function('!document.getElementById("waFetch").disabled')
  page.locator('#waFetch').click();page.wait_for_function('!document.getElementById("waMappingPanel").hidden')
  assert page.evaluate('players.map(p=>p.present)')==baseline
  assert 'WHATSAPP' in page.locator('#waSourceTag').inner_text()
  page.locator('[data-wa-answer="0"]').click()
  assert page.locator('#waApply').is_disabled()
  assert 'votants à associer' in page.locator('#waApplyInfo').inner_text()
  for wa,player in [('a@lid','p0'),('s@lid','p1'),('t@lid','p3')]:
   page.locator(f'[data-wa-voter="{wa}"]').select_option(player)
   page.wait_for_function('!document.querySelector("[data-wa-voter]").disabled')
  assert state['mapping']['a@lid']=='p0'
  assert not page.locator('#waApply').is_disabled()
  assert 'Aucune réponse connue' in page.locator('#waAttendancePreview').inner_text()
  page.locator('#waApply').click()
  page.wait_for_function('players[0].present===true&&players[1].present===false&&players[3].present===true')
  assert page.evaluate('players.map(p=>p.present)')==[True,False,True,True]
  assert page.evaluate('JSON.parse(localStorage.getItem("basket-sessions-v2")||"[]").length')==0
  page.locator('#waApplyMode').select_option('replace');page.locator('#waApply').click()
  page.wait_for_function('players[2].present===false')
  assert page.evaluate('players.map(p=>p.present)')==[True,False,False,True]
  # A provider error blocks any presence change instead of treating it as no votes.
  before=page.evaluate('players.map(p=>p.present)');state['fail_votes']=True
  page.locator('#waRefreshVotes').click();page.wait_for_function('document.getElementById("waStatus").textContent.includes("Votes non vérifiés")')
  assert page.locator('#waApply').is_disabled() and page.evaluate('players.map(p=>p.present)')==before
  state['fail_votes']=False;page.locator('#waRefreshVotes').click();page.wait_for_function('!document.getElementById("waApply").disabled')
  # Re-read on application: new votes force review rather than silently changing the planned selection.
  state['poll']=json.loads(json.dumps(poll));state['poll']['options'][0]['voters']=[dict(id='a@lid',name='Alex')]
  page.locator('#waApply').click();page.wait_for_function('document.getElementById("waStatus").textContent.includes("Les votes ont changé")')
  assert page.evaluate('players.map(p=>p.present)')==before
  page.locator('#waApply').click();page.wait_for_function('players[3].present===false')
  # Demo cannot write mappings or apply fake voters.
  page.locator('summary').filter(has_text='Démo fictive, sans connexion').click();page.locator('#waDemo').click()
  assert not page.locator('#waMappingPanel').is_visible()
  assert page.locator('#waApply').is_disabled()
  page.locator('#waStopWatch').click()
  for width in [390,1280]:
   page.set_viewport_size(dict(width=width,height=960))
   assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
  assert all(method=='GET' or path.endswith(('/connect','/group','/mapping')) for method,path in calls)
  assert not errors,errors
  browser.close()
finally:server.shutdown()
print('PASS: QR/status, groups/polls, persistent mapping requests, explicit presence import, no-response distinction, fresh-vote review, read errors, demo isolation, responsive UI.')
