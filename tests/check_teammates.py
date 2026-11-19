"""Run: python3 tests/check_teammates.py (Playwright and Chromium)."""
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
people=[dict(id=id,name=name,height=180,level=3,positions=[1]) for id,name in [('a','Alex'),('b','Bob'),('c','Camille'),('d','Dany'),('e','Evan'),('f','Fran')]]
def session(day,groups):
 assigned=sum(groups,[])
 return dict(id=f's{day}',date=f'2026-11-{day}',players=people[:5],teams=[dict(id=f't{i}',name=f'Équipe {i}',color='#2563eb',playerIds=ids) for i,ids in enumerate(groups)],bench=[p['id'] for p in people[:5] if p['id'] not in assigned])
package=dict(version=1,players=people,sessions=[session(10,[['a','b','d'],['c']]),session(11,[['a','b','c'],['d']]),session(12,[['a','b','c'],['d']])])
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
  page=browser.new_page(viewport=dict(width=1280,height=960));errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(f'http://127.0.0.1:{server.server_port}/basket-equipes-autonome.html')
  def upload(data):
   page.locator('#importFile').set_input_files(dict(name='basket.json',mimeType='application/json',buffer=json.dumps(data).encode()))
   page.wait_for_function('document.getElementById("importFile").value===""')
  def counts():
   return page.locator('#teammateGraph .teammate-node').evaluate_all('(nodes)=>Object.fromEntries(nodes.map(n=>[n.dataset.teammateId,Number(n.dataset.count)]))')
  page.locator('#historyTab').click()
  assert 'Sélectionnez' in page.locator('#teammateGraph').inner_text()
  upload(package)
  page.locator('#teammateReference').select_option('a')
  assert counts()=={'b':3,'c':2,'d':1} # Excludes self, opponents, bench and a never-present player.
  assert page.locator('#teammateGraph line').count()==3
  assert page.locator('#teammateGraph .teammate-reference').count()==1
  radii=page.locator('#teammateGraph .teammate-node circle').evaluate_all('(nodes)=>nodes.map(n=>Number(n.getAttribute("r")))')
  assert radii[0]>radii[1]>radii[2]
  assert page.locator('#teammateData tbody tr td').all_text_contents()==['3','2','1']
  assert 'Alex' in page.locator('#teammateSummary').inner_text()
  # Counts are symmetric and do not confuse attendance/opponents with shared teams.
  page.locator('#teammateReference').select_option('b');assert counts()=={'a':3,'c':2,'d':1}
  page.locator('#teammateReference').select_option('d');assert counts()=={'a':1,'b':1}
  for id in ['e','f']:
   page.locator('#teammateReference').select_option(id)
   assert page.locator('#teammateGraph svg').count()==0
   assert 'Aucun coéquipier' in page.locator('#teammateGraph').inner_text()
  # Current roster removal does not erase an archived player or their links.
  archived=json.loads(json.dumps(package));archived['players']=[p for p in people if p['id']!='b']
  upload(archived)
  page.locator('#teammateReference').select_option('b');assert counts()=={'a':3,'c':2,'d':1}
  # Editing and deleting sessions recalculates the graph while retaining selection.
  page.locator('#teammateReference').select_option('a')
  page.locator('#historyDay').select_option('s10')
  page.locator('[data-history-player="d"] .history-assignment').select_option('t1')
  page.locator('#saveHistoryEdits').click()
  assert counts()=={'b':3,'c':2} and page.locator('#teammateReference').input_value()=='a'
  page.locator('#historyDay').select_option('s11')
  page.once('dialog',lambda d:d.accept());page.locator('#deleteSession').click()
  assert counts()=={'b':2,'c':1}
  page.reload();page.locator('#historyTab').click();page.locator('#teammateReference').select_option('a')
  assert counts()=={'b':2,'c':1}
  with page.expect_download() as event:page.locator('#exportBtn').click()
  saved=json.loads(Path(event.value.path()).read_text());upload(saved)
  assert counts()=={'b':2,'c':1}
  # Limit controls keep the full data available and all-mode supports larger rosters.
  many=[dict(id=f'p{i}',name=f'Joueur {i}',height=180,level=3,positions=[1]) for i in range(25)]
  large=dict(version=1,players=many,sessions=[dict(id='large',date='2026-11-13',players=many,teams=[dict(id='one',name='Une équipe',color='#ffffff',playerIds=[p['id'] for p in many])],bench=[])])
  upload(large);page.locator('#teammateReference').select_option('p0')
  assert len(counts())==8 and page.locator('#teammateData tbody tr').count()==24
  page.locator('#teammateLimit').select_option('16');assert len(counts())==16
  page.locator('#teammateLimit').select_option('all');assert len(counts())==24
  for width in [390,1280]:
   page.set_viewport_size(dict(width=width,height=960))
   assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
  # Markup in names and special identifiers must stay inert in labels/options/SVG.
  hostile=json.loads(json.dumps(package));hostile['players'][0]['name']='<img src=x onerror="window.bad=1">'
  hostile['players'][1]['name']='Bob <script>window.bad=1</script>'
  upload(hostile);page.locator('#teammateReference').select_option('a')
  assert not page.evaluate('window.bad||false')
  assert page.locator('#teammateGraph img,#teammateGraph script').count()==0
  assert counts()=={'b':3,'c':2,'d':1}
  # Screenshots of the standard view on both form factors.
  upload(package);page.locator('#teammateLimit').select_option('8');page.locator('#teammateReference').select_option('a')
  for width in [1280,390]:
   page.set_viewport_size(dict(width=width,height=960))
   page.locator('#teammateGraph').scroll_into_view_if_needed()
   page.locator('#teammateGraph').screenshot(path=f'/tmp/teammates-{width}.png')
   assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
  upload(dict(version=1,players=people,sessions=[]))
  page.locator('#teammateReference').select_option('a')
  assert counts()=={} and 'Aucun coéquipier' in page.locator('#teammateGraph').inner_text()
  assert not errors,errors
  browser.close()
finally:server.shutdown()
print('PASS: reference dropdown, exact shared-team counts/symmetry, proportional circles, bench/opponent exclusion, archived players, edits/deletions, persistence/import/export, limits, mobile, escaped labels.')
