"""Run: python3 tests/check_history.py (Playwright + /usr/bin/chromium)."""
from datetime import datetime, timezone
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import json
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
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
  assert page.title()=='Basket Team tracker'
  assert page.get_by_role('heading',level=1).inner_text()=='Basket Team tracker'
  def upload(data):
   page.locator('#importFile').set_input_files(dict(name='basket.json',mimeType='application/json',buffer=json.dumps(data).encode()))
   page.wait_for_function('document.getElementById("importFile").value===""')
  def records():return page.evaluate('JSON.parse(localStorage.getItem("basket-sessions-v2")||"[]")')
  def export():
   with page.expect_download() as event:page.locator('#exportBtn').click()
   return json.loads(Path(event.value.path()).read_text())
  def history():page.locator('#historyTab').click()
  def training():page.locator('#trainingTab').click()
  assert page.locator('#appVersion').inner_text()=='Version 3.2.3'
  assert page.get_by_role('tab').all_text_contents()==['Effectif','Entraînement','Match','Statistique','Configuration']
  assert page.locator('#rosterTab').get_attribute('aria-selected')=='true'
  assert page.locator('#saveSessionBtn').is_disabled()
  upload(roster)
  assert page.locator('#roster .player').count()==6
  assert page.locator('#roster input[type=checkbox]').count()==0
  history()
  assert not page.locator('#trainingPanel').is_visible()
  assert 'Aucune séance' in page.locator('#attendanceChart').inner_text()
  page.locator('#historyTab').press('ArrowLeft')
  assert page.locator('#matchTab').get_attribute('aria-selected')=='true'
  assert page.locator('#matchPanel').inner_html()==''
  page.locator('#matchTab').press('End')
  assert page.locator('#configTab').get_attribute('aria-selected')=='true'
  page.locator('#configTab').press('ArrowRight')
  assert page.locator('#rosterTab').get_attribute('aria-selected')=='true'
  page.locator('#rosterTab').press('ArrowRight')
  assert page.locator('#trainingPanel').is_visible()
  assert page.locator('[role=tabpanel]:visible').count()==1
  assert page.locator('#attendanceRoster [data-open-player]').count()==0
  assert page.locator('#presentCount').inner_text()=='4 présents'
  page.locator('#noneBtn').click()
  assert page.locator('#presentCount').inner_text()=='0 présent'
  for i in range(4):
   page.get_by_role('checkbox',name=f'Présence de Joueur {i}').check()
  assert page.locator('#presentCount').inner_text()=='4 présents'
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
  assert saved[0]['compositions'][0]['teams'][0]['color']=='#ff8800'
  assert [t['playerIds'] for t in saved[0]['compositions'][0]['teams']]==result['teams']
  assert saved[0]['compositions'][0]['engineVersion']=='3.0' and saved[0]['compositions'][0]['manuallyEdited']
  assert len(saved[0]['players'])==4
  # Repeated saves never double count a day; dismissal preserves the original.
  save_dialog=page.locator('#sessionSaveDialog')
  page.locator('#saveSessionBtn').click()
  save_dialog.get_by_role('button',name='Annuler').click()
  assert records()==saved
  page.locator('#saveSessionBtn').click()
  save_dialog.get_by_role('button',name='Remplacer la séance').click()
  page.wait_for_function("(old)=>JSON.parse(localStorage.getItem('basket-sessions-v2'))[0].compositions[0].id!==old",arg=saved[0]['compositions'][0]['id'])
  assert len(records())==1 and records()[0]['id']==first_id
  history()
  assert page.locator('#attendanceChart svg').count()==1
  assert page.locator('#attendanceChart polyline').count()==0
  assert page.locator('#attendanceChart circle').count()==1
  assert page.locator('#attendanceChart rect').count()==0
  assert page.locator('#participationChart').count()==0
  assert page.locator('#participationData table').is_visible()
  assert page.locator('#participationData tbody tr').count()==6
  assert page.locator('#participationData tbody tr').last.locator('td:nth-child(3)').text_content()=='0'
  assert page.locator('#attendanceData td').all_text_contents()==['20/11/2026','4']
  # Second day includes all six: the ranking sorts descending and resolves ties alphabetically.
  training();page.clock.set_fixed_time(datetime(2026,11,21,10,tzinfo=timezone.utc))
  page.locator('#allBtn').click()
  # Stale generated composition must not save incorrect attendance.
  page.locator('#saveSessionBtn').click()
  assert len(records())==1 and 'présences ont changé' in page.locator('#notice').inner_text()
  page.locator('#generateBtn').click();page.locator('#saveSessionBtn').click()
  history()
  assert len(records())==2
  assert page.locator('#attendanceData tbody tr').nth(1).locator('td').all_text_contents()==['21/11/2026','6']
  assert page.locator('#participationData tbody tr').evaluate_all('(rows)=>rows.map(row=>row.dataset.rankingPlayer)')==['p0','p1','p2','p3','p4','p5']
  assert page.locator('#participationData tbody tr td:nth-child(3)').all_text_contents()==['2','2','2','2','1','1']
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
  assert len(first['players'])==3 and first['compositions'][0]['teams'][0]['name']=='Les Bleus'
  assert next(p for p in first['players'] if p['id']=='p0')['name']=='Nom historique'
  assert page.locator('#attendanceData tbody tr').first.locator('td').all_text_contents()==['20/11/2026','3']
  assert page.locator('[data-ranking-player="p1"] td:nth-child(3)').text_content()=='1'
  assert page.locator('#participationData tbody tr').evaluate_all('(rows)=>rows.map(row=>row.dataset.rankingPlayer)')==['p0','p2','p3','p1','p4','p5']
  # Remove a team: participants remain present and become unassigned.
  page.locator('.history-delete-team').first.click();page.locator('#saveHistoryEdits').click()
  first=next(s for s in records() if s['id']==first_id)
  assert len(first['compositions'][0]['teams'])==1 and len(first['players'])==3
  assert first['compositions'][0]['bench']
  page.locator('#addHistoryTeam').click()
  page.locator('#historyAddPlayer').select_option('p4');page.locator('#addHistoryPlayer').click()
  team_id=page.locator('[data-history-player="p4"] .history-assignment option').last.get_attribute('value')
  page.locator('[data-history-player="p4"] .history-assignment').select_option(team_id)
  page.locator('#saveHistoryEdits').click()
  first=next(s for s in records() if s['id']==first_id)
  assert len(first['players'])==4
  assert 'p4' in next(t for t in first['compositions'][0]['teams'] if t['id']==team_id)['playerIds']
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
  bad['sessions'][0]['compositions'][0]['teams'][0]['playerIds'].append('unknown')
  alerts=[]
  page.once('dialog',lambda d:(alerts.append(d.message),d.dismiss()))
  upload(bad)
  assert alerts and records()==history_before and page.evaluate('players.length')==6
  # Failure on the final write must also roll back the roster and history.
  page.evaluate('''()=>{window.oldSetItem=Storage.prototype.setItem;window.failedWrite=false;Storage.prototype.setItem=function(key,value){if(key==='basket-statistics-weekdays'&&!window.failedWrite){window.failedWrite=true;throw new DOMException('Storage full','QuotaExceededError')}return window.oldSetItem.call(this,key,value)}}''')
  smaller=dict(package,players=roster[:1],sessions=[],statisticsWeekdays=[4])
  page.once('dialog',lambda d:d.dismiss());upload(smaller)
  page.evaluate('()=>{Storage.prototype.setItem=window.oldSetItem}')
  assert records()==history_before and page.evaluate('players.length')==6
  assert len(page.evaluate('JSON.parse(localStorage.getItem("basket-balancer-v1"))'))==6
  assert export()['statisticsWeekdays']==list(range(7))
  # A renamed player containing markup is displayed as text, never executed.
  hostile=json.loads(json.dumps(package));hostile['sessions'][0]['players'][0]['name']='<img src=x onerror="window.bad=1">'
  upload(hostile)
  assert not page.evaluate('window.bad||false')
  assert page.locator('#historyPanel img').count()==0
  upload(package)
  page.reload();history()
  assert records()==history_before
  assert page.locator('#attendanceChart circle').count()==2
  assert page.locator('#attendanceChart polyline').count()==0
  # Delete an entire day and verify recalculation.
  page.locator('#historyDay').select_option(first_id)
  page.once('dialog',lambda d:d.accept());page.locator('#deleteSession').click()
  assert len(records())==1
  assert page.locator('#attendanceData tbody tr').count()==1
  assert page.locator('#participationData tbody tr td:nth-child(3)').all_text_contents()==['1']*6
  for width in [1280,390]:
   page.set_viewport_size(dict(width=width,height=960))
   assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
   page.screenshot(path=f'/tmp/basket-history-{width}.png',full_page=True)
  # An explicit empty sessions array can replace all history; absent sessions never does.
  empty=json.loads(json.dumps(package));empty['sessions']=[]
  upload(empty)
  assert records()==[] and page.locator('#attendanceChart svg').count()==0
  assert 'Aucune séance' in page.locator('#attendanceChart').inner_text()
  # A manual session adds to the same history and changes both weekday tables.
  wednesdays=[dict(date=date,players=present,teams=[]) for date,present in [
   ('2026-11-04', [roster[0],roster[2]]), ('2026-11-11', [roster[0]]),
   ('2026-11-18', [roster[0],roster[2]])
  ]]
  upload(dict(players=roster,sessions=wednesdays))
  page.locator('#newManualSession').click()
  page.locator('#sessionDate').fill('2026-11-18')
  page.locator('#saveHistoryEdits').click()
  assert len(records())==3 and 'existe déjà' in page.locator('#historyStatus').inner_text()
  page.locator('#sessionDate').fill('2026-11-25')
  page.locator('#historyAddPlayer').select_option('p1')
  page.locator('#addHistoryPlayer').click()
  page.locator('#configTab').click()
  for day in ['Lundi','Mardi','Jeudi','Vendredi','Samedi']:
   page.get_by_role('checkbox',name=day,exact=True).uncheck()
  history()
  assert page.locator('#sessionDate').input_value()=='2026-11-25'
  page.locator('#saveHistoryEdits').click()
  manual=records()[-1]
  assert manual['date']=='2026-11-25' and manual['compositions'][0]['source']=='manual'
  assert manual['compositions'][0]['teams']==[] and manual['compositions'][0]['bench']==['p1']
  assert page.locator('#historyDay').input_value()==manual['id']
  assert page.locator('#weekdayAttendance tbody tr').evaluate_all('(rows)=>rows.map(row=>Array.from(row.cells,cell=>cell.textContent))')==[['Mercredi','4','1,5'],['Dimanche','0','—']]
  assert page.locator('#participationData thead th').all_text_contents()==['Rang','Joueur','Participations','Mercredi (%)','Dimanche (%)']
  assert page.get_by_role('button',name='Dimanche (%)',exact=True).is_disabled()
  assert page.locator('[data-ranking-player="p0"] td[title="3 sur 4 séances"]').inner_text().replace('\xa0',' ')=='75 %'
  assert page.locator('[data-ranking-player="p3"] td[title="0 sur 4 séances"]').inner_text().replace('\xa0',' ')=='0 %'
  assert page.locator('[data-ranking-player="p0"] td:last-child').text_content()=='—'
  manual_backup=export()
  assert manual_backup['sessions'][-1]==manual and manual_backup['statisticsWeekdays']==[2,6]
  page.locator('#newManualSession').click()
  page.locator('#cancelManualSession').click()
  assert len(records())==4 and page.locator('#historyDay').input_value()==manual['id']
  page.reload();history()
  assert page.locator('#weekdayAttendance tbody th').all_text_contents()==['Mercredi','Dimanche']
  assert page.locator('[data-ranking-player="p0"] td[title="3 sur 4 séances"]').count()==1
  # The same alphabetical order applies across lists, regardless of the roster's selected sort.
  unordered=[dict(player,name=name) for player,name in zip(roster,['Zoé','émile','André'])]
  dates=['2026-10-30','2026-10-31','2026-11-02','2026-11-06','2026-11-09']
  groups=[[0],[0,2],[1,2],[0],[1]]
  upload(dict(players=unordered,sessions=[dict(date=date,players=[unordered[i] for i in group],teams=[]) for date,group in zip(dates,groups)],statisticsWeekdays=[4,0,5,4]))
  page.locator('#rosterTab').click()
  alphabetical=['André','émile','Zoé']
  assert page.locator('#rosterSort').input_value()=='name'
  assert page.locator('#roster .name').all_text_contents()==alphabetical
  page.locator('#rosterSort').select_option('original')
  assert page.locator('#roster .name').all_text_contents()==['Zoé','émile','André']
  training()
  assert page.locator('#attendanceRoster .name').all_text_contents()==alphabetical
  history()
  page.locator('#newManualSession').click()
  assert page.locator('#historyAddPlayer option').all_text_contents()[1:]==alphabetical
  page.locator('#cancelManualSession').click()
  # Ranking controls sort the correct numeric column, toggle direction and keep keyboard focus.
  ranking=page.locator('#participationData')
  def ranking_ids():return ranking.locator('tbody tr').evaluate_all('(rows)=>rows.map(row=>row.dataset.rankingPlayer)')
  active_sort=ranking.locator('thead th[aria-sort]')
  assert ranking_ids()==['p0','p2','p1'] and active_sort.inner_text()=='Participations'
  monday=ranking.get_by_role('button',name='Lundi (%)',exact=True)
  monday.click()
  assert ranking_ids()==['p1','p2','p0'] and active_sort.get_attribute('aria-sort')=='descending'
  assert monday.evaluate('button=>document.activeElement===button')
  monday.press('Enter')
  assert ranking_ids()==['p0','p2','p1'] and active_sort.get_attribute('aria-sort')=='ascending'
  total=ranking.get_by_role('button',name='Participations',exact=True)
  total.click();total.click()
  assert ranking_ids()==['p2','p1','p0'] and active_sort.inner_text()=='Participations'
  assert ranking.locator('tbody td:first-child').all_text_contents()==['1','2','3']
  ranking.get_by_role('button',name='Samedi (%)',exact=True).click()
  assert ranking_ids()==['p2','p0','p1'] and active_sort.inner_text()=='Samedi (%)'
  # Marker colours follow weekdays and calendar lines fall between the right dates.
  chart=page.locator('#attendanceChart')
  points=chart.locator('circle').evaluate_all('(points)=>points.map(p=>({x:Number(p.getAttribute("cx")),color:p.getAttribute("fill")})).sort((a,b)=>a.x-b.x)')
  assert points[0]['color']==points[3]['color'] and points[2]['color']==points[4]['color']
  assert len({point['color'] for point in points})==3
  assert points[3]['x']-points[2]['x']>3*(points[1]['x']-points[0]['x'])
  month=chart.locator('.attendance-month-divider')
  weeks=chart.locator('.attendance-week-divider')
  assert month.count()==1 and weeks.count()==2
  assert month.get_attribute('stroke-dasharray') is None and weeks.first.get_attribute('stroke-dasharray')=='1 3'
  assert points[1]['x']<float(month.get_attribute('x1'))<float(weeks.first.get_attribute('x1'))<points[2]['x']
  series=chart.locator('svg g[data-attendance-weekday]')
  assert series.evaluate_all('(groups)=>groups.map(g=>g.dataset.attendanceWeekday)')==['0','4','5']
  for weekday,point_count in [(0,2),(4,2),(5,1)]:
   group=chart.locator(f'[data-attendance-weekday="{weekday}"]')
   assert group.locator('circle').count()==point_count
   if point_count>1:
    curve=group.locator('polyline')
    assert curve.get_attribute('stroke')==group.locator('circle').first.get_attribute('fill')
    assert curve.get_attribute('points').split()==group.locator('circle').evaluate_all('(points)=>points.map(p=>p.getAttribute("cx")+","+p.getAttribute("cy"))')
   else:
    assert group.locator('polyline').count()==0
  assert chart.locator('[data-legend-weekday]').all_text_contents()==['Lundi','Vendredi','Samedi']
  weekday_backup=export()
  assert weekday_backup['statisticsWeekdays']==[0,4,5]
  page.locator('#configTab').click()
  page.get_by_role('checkbox',name='Samedi',exact=True).uncheck()
  upload(unordered) # Old player-only exports retain the current weekday selection.
  history()
  assert chart.locator('[data-legend-weekday]').all_text_contents()==['Lundi','Vendredi']
  assert ranking_ids()==['p0','p2','p1'] and active_sort.inner_text()=='Participations'
  assert chart.locator('circle').count()==4 and chart.locator('polyline').count()==2
  assert page.locator('#attendanceData tbody tr').count()==4
  upload(weekday_backup)
  page.reload()
  page.locator('#configTab').click()
  assert page.locator('#weekdayOptions input:checked').evaluate_all('(inputs)=>inputs.map(input=>input.value)')==['0','4','5']
  history()
  assert chart.locator('circle').count()==5
  previous=records()
  invalid=[]
  page.once('dialog',lambda dialog:(invalid.append(dialog.message),dialog.dismiss()))
  upload(dict(players=roster,sessions=[],statisticsWeekdays=[7]))
  assert '0 (lundi) à 6' in invalid[0] and records()==previous
  assert export()['statisticsWeekdays']==[0,4,5] and page.evaluate('players.length')==3
  upload(dict(weekday_backup,statisticsWeekdays=[]))
  assert export()['statisticsWeekdays']==[] and 'Choisissez les jours' in chart.inner_text()
  assert chart.locator('[data-legend-weekday]').count()==0
  # The same day can retain distinct three-team and two-team compositions.
  multi_roster=[dict(id=f'm{i}',name=f'Joueur {i}',height=180,level=3,positions=[1],present=i<12) for i in range(13)]
  upload(dict(players=multi_roster,sessions=[],statisticsWeekdays=list(range(7))))
  page.clock.set_fixed_time(datetime(2026,11,27,10,tzinfo=timezone.utc))
  training()
  page.locator('#teamCount').select_option('3')
  page.locator('#generateBtn').click();page.locator('#saveSessionBtn').click()
  first=records()[0]
  first_comp=first['compositions'][0]
  assert [len(team['playerIds']) for team in first_comp['teams']]==[4,4,4]
  page.locator('[data-pres="m0"]').uncheck();page.locator('[data-pres="m12"]').check()
  page.locator('#teamCount').select_option('2')
  page.locator('#generateBtn').click();page.locator('#saveSessionBtn').click()
  save_dialog.get_by_role('button',name='Ajouter à la séance').click()
  page.wait_for_function("JSON.parse(localStorage.getItem('basket-sessions-v2'))[0].compositions.length===2")
  history()
  assert len(records())==1
  combined=records()[0]
  assert combined['id']==first['id'] and len(combined['players'])==13
  assert combined['compositions'][0]==first_comp
  second_comp=combined['compositions'][1]
  assert [len(team['playerIds']) for team in second_comp['teams']]==[6,6]
  assert page.locator('#attendanceData td').all_text_contents()==['27/11/2026','13']
  assert page.locator('#participationData tbody td:nth-child(3)').all_text_contents()==['1']*13
  page.locator('#rosterTab').click()
  page.locator('[data-open-player="m1"]').click()
  profile=page.locator('#playerHistory')
  assert profile.locator('.player-history-total dd').inner_text()=='1'
  assert profile.locator('dl div').filter(has=page.get_by_text('Vendredi',exact=True)).locator('dd').inner_text().replace('\xa0',' ')=='1 (100 %)'
  history()
  # Pairs count once per day even when they play in both compositions.
  def shared_pairs(composition):
   return {tuple(sorted((a,b))) for team in composition['teams'] for a in team['playerIds'] for b in team['playerIds'] if a!=b}
  first_pairs,second_pairs=shared_pairs(first_comp),shared_pairs(second_comp)
  reference,_=next(iter(first_pairs & second_pairs))
  expected={id for pair in first_pairs | second_pairs if reference in pair for id in pair if id!=reference}
  page.locator('#teammateReference').select_option(reference)
  assert set(page.locator('#teammateData tbody tr').evaluate_all('(rows)=>rows.map(row=>row.dataset.teammateId)'))==expected
  assert page.locator('#teammateData tbody td').all_text_contents()==['1']*len(expected)
  # History can edit either composition independently and export both together.
  selector=page.locator('#historyComposition')
  assert selector.input_value()==second_comp['id']
  selector.select_option(first_comp['id'])
  assert page.locator('[data-history-player="m12"] .history-assignment').input_value()=='outside'
  page.locator('.history-team-name').first.fill('Premier groupe')
  selector.select_option(second_comp['id'])
  assert page.locator('.history-team-name').first.input_value()=='Équipe 1'
  page.locator('#saveHistoryEdits').click()
  edited=records()[0]
  assert edited['compositions'][0]['teams'][0]['name']=='Premier groupe' and edited['compositions'][1]==second_comp
  upload(export())
  assert records()==[edited]
  training()
  page.locator('#saveSessionBtn').click()
  save_dialog.get_by_role('button',name='Remplacer la séance').click()
  page.wait_for_function("JSON.parse(localStorage.getItem('basket-sessions-v2'))[0].compositions.length===1")
  replacement=records()[0]
  assert replacement['id']==first['id'] and len(replacement['players'])==12
  assert 'm0' not in [player['id'] for player in replacement['players']]
  assert [len(team['playerIds']) for team in replacement['compositions'][0]['teams']]==[6,6]
  # Long names wrap and stay visible while reading the last weekday on narrow screens.
  long_name='Alexandre Jean-Baptiste de La Rochefoucauld'
  mobile_backup=export()
  next(player for player in mobile_backup['players'] if player['id']=='m1')['name']=long_name
  upload(mobile_backup)
  history()
  name_cell=ranking.locator('[data-ranking-player="m1"] th')
  for width in [320,390]:
   page.set_viewport_size(dict(width=width,height=860))
   assert name_cell.inner_text()==long_name
   assert name_cell.evaluate("""cell=>{
    const range=document.createRange();
    range.selectNodeContents(cell);
    const lines=[...range.getClientRects()],bounds=cell.getBoundingClientRect();
    return bounds.width>=128&&lines.length>1&&lines.every(line=>line.right<=bounds.right);
   }""")
   ranking.evaluate('table=>table.scrollLeft=table.scrollWidth')
   assert ranking.evaluate('table=>table.scrollLeft>0')
   assert abs(name_cell.bounding_box()['x']-ranking.bounding_box()['x'])<2
   assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
  assert not errors,errors
  browser.close()
finally:server.shutdown()
print('PASS: five-tab navigation, attendance selection, daily save/local date, duplicate/stale safeguards, attendance curve, descending player ranking, history editing/deletion, persistence, legacy/new JSON, atomic invalid-import rejection, escaped text, responsive.')
