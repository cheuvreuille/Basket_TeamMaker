"""Run: python3 tests/check_teammates.py (Playwright and Chromium)."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from math import dist
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
  def length(line):
   def point(index):
    return [float(line.get_attribute(axis+str(index))) for axis in ('x','y')]
   return dist(point(1),point(2))
  def circles_separated(graph):
   return graph.locator('circle').evaluate_all("""circles => circles.every((circle, i) =>
    circles.slice(i+1).every(other => Math.hypot(circle.cx.baseVal.value-other.cx.baseVal.value,
     circle.cy.baseVal.value-other.cy.baseVal.value) >= circle.r.baseVal.value+other.r.baseVal.value))""")
  page.locator('#historyTab').click()
  assert 'Sélectionnez' in page.locator('#teammateGraph').inner_text()
  upload(package)
  page.locator('#teammateReference').select_option('a')
  assert counts()=={'b':3,'c':2,'d':1} # Excludes self, opponents, bench and a never-present player.
  assert page.locator('#teammateGraph line').count()==3
  assert page.locator('#teammateGraph .teammate-reference').count()==1
  teammates_graph=page.locator('#teammateGraph')
  frequent=teammates_graph.locator('line').filter(has_text='Alex et Bob')
  occasional=teammates_graph.locator('line').filter(has_text='Alex et Camille')
  rare=teammates_graph.locator('line').filter(has_text='Alex et Dany')
  assert length(frequent)<length(occasional)<length(rare)
  assert float(frequent.get_attribute('stroke-width'))>float(rare.get_attribute('stroke-width'))
  assert frequent.get_attribute('stroke')!=rare.get_attribute('stroke')
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
  page.locator('#rosterTab').click()
  page.locator('[data-open-player="p0"]').click()
  assert page.locator('#playerHistory li').count()==5
  assert all('Joueur 0 ·' not in row for row in page.locator('#playerHistory li').all_text_contents())
  page.locator('#historyTab').click()
  page.locator('#teammateLimit').select_option('16');assert len(counts())==16
  page.locator('#teammateLimit').select_option('all');assert len(counts())==24
  assert circles_separated(teammates_graph)
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
  # Open the editable card and use the same attendance history as the statistics tab.
  extra_session=dict(date='2026-11-17',players=[people[1]],teams=[])
  upload(dict(package,statisticsWeekdays=[1,2],sessions=package['sessions']+[extra_session]))
  page.locator('#rosterTab').click()
  card=page.get_by_role('button',name='Ouvrir la fiche de Alex',exact=True)
  card.locator('.details').click()
  profile=page.locator('#playerHistory')
  assert card.get_attribute('aria-current')=='true'
  assert page.locator('#editorTitle').inner_text()=='Alex' and page.locator('#playerName').input_value()=='Alex'
  assert profile.locator('dt').all_text_contents()==['Total','Mardi','Mercredi']
  assert [value.replace('\xa0',' ') for value in profile.locator('dd').all_text_contents()]==['3','1 (50 %)','1 (100 %)']
  assert profile.locator('time').get_attribute('datetime')=='2026-11-12'
  assert profile.locator('li').all_text_contents()==['Bob · 3 séances ensemble','Camille · 2 séances ensemble','Dany · 1 séance ensemble']
  page.locator('#playerName').fill('Alex Martin')
  page.locator('#saveBtn').click()
  updated=page.get_by_role('button',name='Ouvrir la fiche de Alex Martin',exact=True)
  assert updated.evaluate('button=>document.activeElement===button')
  updated.press('Enter')
  assert page.locator('#playerName').input_value()=='Alex Martin' and profile.locator('li').count()==3
  page.locator('#historyTab').click()
  page.locator('#historyDay').select_option('s12')
  page.once('dialog',lambda dialog:dialog.accept());page.locator('#deleteSession').click()
  page.locator('#rosterTab').click()
  assert profile.locator('.player-history-total dd').inner_text()=='2'
  assert profile.locator('time').get_attribute('datetime')=='2026-11-11'
  assert profile.locator('li').all_text_contents()==['Bob · 2 séances ensemble','Camille · 1 séance ensemble','Dany · 1 séance ensemble']
  page.locator('[data-open-player="f"]').click()
  assert profile.locator('.player-history-total dd').inner_text()=='0'
  assert 'Aucune participation' in profile.inner_text() and profile.locator('li').count()==0
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')

  # The global graph counts presences per date and links per saved composition.
  first=session(10,[['a','b','d'],['c']])
  second=session(11,[['a','b','c'],['d']])
  repeat=session(11,[['b','a'],['d','c']]) # Reversed member order still describes the same pairs.
  second['compositions']=[{key:record[key] for key in ('teams','bench')} for record in (second,repeat)]
  wednesday=session(18,[['a','c'],['b','d']])
  solo=dict(id='solo',date='2026-11-12',players=[people[5]],teams=[])
  upload(dict(package,statisticsWeekdays=[2],sessions=[first,second,wednesday,solo]))
  page.locator('#historyTab').click()
  graph=page.locator('#relationshipGraph')
  day=page.locator('#relationshipWeekday')
  alex=graph.get_by_role('button',name='Alex · 3 séances')
  fran=graph.get_by_role('button',name='Fran · 1 séance')
  assert graph.get_by_role('button').count()==6 and graph.locator('line').count()==6
  assert float(alex.locator('circle').get_attribute('r'))>float(fran.locator('circle').get_attribute('r'))
  strong=graph.locator('line').filter(has_text='Alex et Bob')
  medium=graph.locator('line').filter(has_text='Alex et Camille')
  weak=graph.locator('line').filter(has_text='Alex et Dany')
  assert '3 compositions' in strong.locator('title').text_content()
  original_length=length(strong)
  assert original_length<length(medium)<length(weak)
  assert float(strong.get_attribute('stroke-width'))>float(weak.get_attribute('stroke-width'))
  assert strong.get_attribute('stroke')!=weak.get_attribute('stroke')
  alex.press('Enter')
  assert alex.get_attribute('aria-pressed')=='true'
  assert graph.locator('line.is-selected').count()==3
  assert page.locator('#relationshipPartners li').all_text_contents()==['Bob · 3 compositions','Camille · 2 compositions','Dany · 1 composition']
  alex.press('Space')
  assert alex.get_attribute('aria-pressed')=='false'
  day.select_option('1')
  assert graph.get_by_role('button',name='Alex · 1 séance').count()==1
  assert graph.locator('line').count()==3 and not graph.locator('line').filter(has_text='Alex et Camille').count()
  day.select_option('2')
  graph.get_by_role('button',name='Alex · 2 séances').press('Enter')
  assert page.locator('#relationshipPartners li').all_text_contents()==['Bob · 2 compositions','Camille · 2 compositions']
  day.select_option('3')
  fran.press('Enter')
  assert graph.get_by_role('button').count()==1 and not graph.locator('line').count()
  assert 'Aucun coéquipier' in page.locator('#relationshipSelection').inner_text()
  day.select_option('0')
  assert 'Aucune présence' in graph.inner_text() and not graph.locator('svg').count()
  day.select_option('all')
  assert length(strong)==original_length
  page.locator('#historyDay').select_option('s10')
  page.locator('[data-history-player="b"] .history-assignment').select_option('t1')
  page.locator('#saveHistoryEdits').click()
  assert '2 compositions' in strong.locator('title').text_content()
  assert graph.get_by_role('button',name='Bob · 3 séances').count()==1
  for width in [1280,390]:
   page.set_viewport_size(dict(width=width,height=960))
   graph.screenshot(path=f'/tmp/relationships-{width}.png')
   assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
  upload(large)
  assert graph.get_by_role('button').count()==25 and graph.locator('line').count()==300
  assert circles_separated(graph)
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
  upload(hostile)
  assert graph.locator('img,script').count()==0 and not page.evaluate('window.bad||false')
  assert not errors,errors
  browser.close()
finally:server.shutdown()
print('PASS: player and global graphs, weekday filtering, exact attendance and composition counts, keyboard selection, archived players, edits/deletions, import/export, limits, mobile, escaped labels.')
