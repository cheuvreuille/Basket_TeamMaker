"""Run: python3 tests/check_history.py (Playwright + /usr/bin/chromium)."""
from datetime import datetime, timezone
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import json
import re
import subprocess
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
previous=subprocess.check_output(['git','show','1ce3c68:basket-equipes-autonome.html'],cwd=ROOT,text=True)
current=(ROOT/'basket-equipes-autonome.html').read_text()
# The original application script is byte-for-byte unchanged outside import/export.
def application_without_io(html):
 script=re.search(r'<script>(.*?)</script>',html,re.S).group(1)
 start=script.index("$('exportBtn').onclick")
 end=script.index('\nfunction updateCount',start)
 return script[:start]+'IMPORT_EXPORT'+script[end:]
assert application_without_io(previous)==application_without_io(current)
class QuietHandler(SimpleHTTPRequestHandler):
 def log_message(self,*args): pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(ROOT)))
Thread(target=server.serve_forever,daemon=True).start()
base=f'http://127.0.0.1:{server.server_port}'
roster=[dict(id=f'p{i}',name=f'Joueur {i}',height=175+i,level=3,positions=[i%5+1],present=i<4) for i in range(6)]
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
  context=browser.new_context(timezone_id='Europe/Paris',viewport=dict(width=1280,height=960))
  page=context.new_page();errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.clock.install(time=datetime(2026,11,19,23,30,tzinfo=timezone.utc))
  page.goto(base+'/')
  page.wait_for_url('**/basket-equipes-autonome.html')
  def upload(data):
   page.locator('#importFile').set_input_files(dict(name='basket.json',mimeType='application/json',buffer=json.dumps(data).encode()))
   page.wait_for_function('document.getElementById("importFile").value===""')
  def records():return page.evaluate('JSON.parse(localStorage.getItem("basket-sessions-v2")||"[]")')
  def export():
   with page.expect_download() as event:page.locator('#exportBtn').click()
   return json.loads(Path(event.value.path()).read_text())
  def history():page.locator('#historyTab').click()
  def maker():page.locator('#makerTab').click()
  assert page.locator('#appVersion').inner_text()=='Version 2.0.1'
  assert page.locator('#makerTab').get_attribute('aria-selected')=='true'
  assert page.locator('#saveSessionBtn').is_disabled()
  history()
  assert not page.locator('#makerPanel').is_visible()
  assert 'Aucune séance' in page.locator('#attendanceChart').inner_text()
  page.locator('#historyTab').press('ArrowLeft')
  assert page.locator('#makerPanel').is_visible()
  upload(roster)
  page.locator('#generateBtn').click()
  page.wait_for_function('!document.getElementById("saveSessionBtn").disabled')
  original=page.evaluate('JSON.stringify(lastResult)')
  # Capture a manual change and a custom team color.
  row=page.locator('[data-player="p0"]')
  destination=1-int(row.get_attribute('data-from'))
  row.locator('select').select_option(str(destination))
  page.locator('[data-team="0"] .team-custom-color').fill('#ff8800')
  result=page.evaluate('lastResult')
  page.locator('#saveSessionBtn').click()
  saved=records()
  assert len(saved)==1 and saved[0]['date']=='2026-11-20' # Local day, not UTC.
  first_id=saved[0]['id']
  assert saved[0]['teams'][0]['color']=='#ff8800'
  assert [t['playerIds'] for t in saved[0]['teams']]==result['teams']
  assert saved[0]['engineVersion']=='3.0' and saved[0]['manuallyEdited']
  assert len(saved[0]['players'])==4
  # Repeated saves never double count a day; dismissal preserves the original.
  page.once('dialog',lambda d:d.dismiss());page.locator('#saveSessionBtn').click()
  assert records()==saved
  page.once('dialog',lambda d:d.accept());page.locator('#saveSessionBtn').click()
  assert len(records())==1 and records()[0]['id']==first_id
  history()
  assert page.locator('#attendanceChart svg').count()==1
  assert page.locator('#attendanceChart polyline').count()==1
  assert page.locator('#attendanceChart circle').count()==1
  assert page.locator('#attendanceChart rect').count()==0
  assert page.locator('#participationChart').count()==0
  assert page.locator('#participationData table').is_visible()
  assert page.locator('#participationData tbody tr').count()==6
  assert page.locator('#participationData tbody tr').last.locator('td').last.text_content()=='0'
  assert page.locator('#attendanceData td').all_text_contents()==['20/11/2026','4']
  # Second day includes all six: the ranking sorts descending and resolves ties alphabetically.
  maker();page.clock.set_fixed_time(datetime(2026,11,21,10,tzinfo=timezone.utc))
  page.locator('#allBtn').click()
  # Stale generated composition must not save incorrect attendance.
  page.locator('#saveSessionBtn').click()
  assert len(records())==1 and 'présences ont changé' in page.locator('#notice').inner_text()
  page.locator('#generateBtn').click();page.locator('#saveSessionBtn').click()
  history()
  assert len(records())==2
  assert page.locator('#attendanceData tbody tr').nth(1).locator('td').all_text_contents()==['21/11/2026','6']
  assert page.locator('#participationData tbody tr').evaluate_all('(rows)=>rows.map(row=>row.dataset.rankingPlayer)')==['p0','p1','p2','p3','p4','p5']
  assert page.locator('#participationData tbody tr td:last-child').all_text_contents()==['2','2','2','2','1','1']
  # Edit an old day without touching the current roster/results.
  current_roster=page.evaluate('JSON.stringify(players)')
  current_result=page.evaluate('JSON.stringify(lastResult)')
  page.locator('#historyDay').select_option(first_id)
  page.locator('[data-history-player="p0"] .history-player-name').fill('Nom historique')
  page.locator('[data-history-player="p1"] .history-delete-player').click()
  page.locator('.history-team-name').first.fill('Les Bleus')
  page.locator('#saveHistoryEdits').click()
  assert page.evaluate('JSON.stringify(players)')==current_roster
  assert page.evaluate('JSON.stringify(lastResult)')==current_result
  first=next(s for s in records() if s['id']==first_id)
  assert len(first['players'])==3 and first['teams'][0]['name']=='Les Bleus'
  assert next(p for p in first['players'] if p['id']=='p0')['name']=='Nom historique'
  assert page.locator('#attendanceData tbody tr').first.locator('td').all_text_contents()==['20/11/2026','3']
  assert page.locator('[data-ranking-player="p1"] td').last.text_content()=='1'
  assert page.locator('#participationData tbody tr').evaluate_all('(rows)=>rows.map(row=>row.dataset.rankingPlayer)')==['p0','p2','p3','p1','p4','p5']
  # Remove a team: participants remain present and become unassigned.
  page.locator('.history-delete-team').first.click();page.locator('#saveHistoryEdits').click()
  first=next(s for s in records() if s['id']==first_id)
  assert len(first['teams'])==1 and len(first['players'])==3
  assert first['bench']
  page.locator('#addHistoryTeam').click()
  page.locator('#historyAddPlayer').select_option('p4');page.locator('#addHistoryPlayer').click()
  team_id=page.locator('[data-history-player="p4"] .history-assignment option').last.get_attribute('value')
  page.locator('[data-history-player="p4"] .history-assignment').select_option(team_id)
  page.locator('#saveHistoryEdits').click()
  first=next(s for s in records() if s['id']==first_id)
  assert len(first['players'])==4
  assert 'p4' in next(t for t in first['teams'] if t['id']==team_id)['playerIds']
  # Collision on changing date is rejected without modifying stored data.
  before=records();page.locator('#sessionDate').fill('2026-11-21');page.locator('#saveHistoryEdits').click()
  assert records()==before and 'date en double' in page.locator('#historyStatus').inner_text()
  page.locator('#historyDay').select_option(first_id)
  # Safe imported/exported history, including players deleted later from the live roster.
  package=export()
  assert package['version']==1 and len(package['players'])==6 and len(package['sessions'])==2
  history_before=records()
  upload(roster[:2]) # Historical JSON must preserve history.
  assert records()==history_before and page.evaluate('players.length')==2
  assert page.locator('#participationData tbody tr').count()==6
  upload(package)
  assert records()==history_before and page.evaluate('players.length')==6
  # Malformed history must not partially import the roster.
  bad=json.loads(json.dumps(package));bad['players']=roster[:1]
  bad['sessions'][0]['teams'][0]['playerIds'].append('unknown')
  alerts=[]
  page.once('dialog',lambda d:(alerts.append(d.message),d.dismiss()))
  upload(bad)
  assert alerts and records()==history_before and page.evaluate('players.length')==6
  # If storage fails during import, both the old roster and history are restored.
  page.evaluate('''()=>{window.oldSetItem=Storage.prototype.setItem;window.failedWrite=false;Storage.prototype.setItem=function(key,value){if(key==='basket-sessions-v2'&&!window.failedWrite){window.failedWrite=true;throw new DOMException('Storage full','QuotaExceededError')}return window.oldSetItem.call(this,key,value)}}''')
  smaller=json.loads(json.dumps(package));smaller['players']=roster[:1]
  page.once('dialog',lambda d:d.dismiss());upload(smaller)
  page.evaluate('()=>{Storage.prototype.setItem=window.oldSetItem}')
  assert records()==history_before and page.evaluate('players.length')==6
  assert len(page.evaluate('JSON.parse(localStorage.getItem("basket-balancer-v1"))'))==6
  # A renamed player containing markup is displayed as text, never executed.
  hostile=json.loads(json.dumps(package));hostile['sessions'][0]['players'][0]['name']='<img src=x onerror="window.bad=1">'
  upload(hostile)
  assert not page.evaluate('window.bad||false')
  assert page.locator('#historyPanel img').count()==0
  upload(package)
  page.reload();history()
  assert records()==history_before
  assert page.locator('#attendanceChart circle').count()==2
  assert page.locator('#attendanceChart polyline').count()==1
  # Delete an entire day and verify recalculation.
  page.locator('#historyDay').select_option(first_id)
  page.once('dialog',lambda d:d.accept());page.locator('#deleteSession').click()
  assert len(records())==1
  assert page.locator('#attendanceData tbody tr').count()==1
  assert page.locator('#participationData tbody tr td:last-child').all_text_contents()==['1']*6
  for width in [1280,390]:
   page.set_viewport_size(dict(width=width,height=960))
   assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
   page.screenshot(path=f'/tmp/basket-history-{width}.png',full_page=True)
  # An explicit empty sessions array can replace all history; absent sessions never does.
  empty=json.loads(json.dumps(package));empty['sessions']=[]
  upload(empty)
  assert records()==[] and page.locator('#attendanceChart svg').count()==0
  assert 'Aucune séance' in page.locator('#attendanceChart').inner_text()
  assert not errors,errors
  browser.close()
finally:server.shutdown()
print('PASS: original app untouched outside IO; tabs, daily save/local date, duplicate/stale safeguards, attendance curve, descending player ranking, history editing/deletion, persistence, legacy/new JSON, atomic invalid-import rejection, escaped text, responsive.')
