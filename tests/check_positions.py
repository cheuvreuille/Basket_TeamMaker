"""Run with: python3 tests/check_positions.py (requires Playwright and Chromium)."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import json
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
server = ThreadingHTTPServer(('127.0.0.1', 0), partial(SimpleHTTPRequestHandler, directory=str(ROOT)))
Thread(target=server.serve_forever, daemon=True).start()
base = f'http://127.0.0.1:{server.server_port}'
skills = dict.fromkeys(['creation', 'shooting', 'rebound', 'speed', 'defense', 'stamina'], 3)
legacy = [dict(id=str(i), name=f'Joueur {i}', height=180, level=3, skills=skills, present=True) for i in range(10)]

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox'])
        page = browser.new_page()
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(base + '/basket-equipes-autonome.html')

        def upload(data):
            page.locator('#importFile').set_input_files(dict(name='players.json', mimeType='application/json', buffer=json.dumps(data).encode()))
            page.wait_for_function('document.getElementById("importFile").value === ""')

        # Existing local data and both historical JSON formats retain the whole roster.
        page.evaluate('(v)=>localStorage.setItem("basket-balancer-v1",JSON.stringify(v))', legacy)
        page.reload()
        assert page.locator('.player').count() == 10
        assert page.evaluate('players.every(p=>p.positions.length===0)')
        for data in [legacy, dict(version=1, players=legacy)]:
            upload(data)
            assert page.locator('.player').count() == 10
            assert page.evaluate('players.every(p=>p.positions.length===0)')
        page.locator('#generateBtn').click()
        assert page.locator('.teamline').count() == 10

        # Editing, multiple choices, cancellation, creation and reload.
        page.locator('[data-edit="0"]').click()
        page.locator('#position_1').check()
        page.locator('#position_3').check()
        page.locator('#saveBtn').click()
        assert page.locator('#positions input:checked').count() == 0
        page.reload()
        page.locator('[data-edit="0"]').click()
        assert page.locator('#position_1').is_checked()
        assert page.locator('#position_3').is_checked()
        page.locator('#position_5').check()
        page.locator('#cancelBtn').click()
        assert page.evaluate('players[0].positions') == [1, 3]
        page.locator('#playerName').fill('Polyvalent')
        for n in [2, 4, 5]:
            page.locator(f'#position_{n}').check()
        page.locator('#saveBtn').click()
        assert page.evaluate('players.at(-1).positions') == [2, 4, 5]
        with page.expect_download() as event:
            page.locator('#exportBtn').click()
        exported = json.loads(Path(event.value.path()).read_text())
        assert exported['version'] == 1
        assert exported['players'][0]['positions'] == [1, 3]
        upload(exported)
        assert page.evaluate('players.at(-1).positions') == [2, 4, 5]
        page.locator('[data-edit="0"]').click()
        page.locator('#position_1').uncheck()
        page.locator('#position_3').uncheck()
        page.locator('#saveBtn').click()
        assert page.evaluate('players[0].positions') == []

        # Invalid optional data cannot become executable markup or phantom positions.
        dirty = [dict(player, positions=[1, '2', 2, 0, 6, None, True, '<img>', 3.5]) for player in legacy]
        upload(dict(version=1, players=dirty))
        assert page.evaluate('players.every(p=>JSON.stringify(p.positions)==="[1,2]")')
        upload([dict(player, positions='1,2') for player in legacy])
        assert page.evaluate('players.every(p=>p.positions.length===0)')

        # A flexible player covers only one slot; matching handles constrained teammates.
        assert page.evaluate('ENGINE_V1.positionCoverage([{positions:[1,2,3,4,5]}])') == 1
        assert page.evaluate('ENGINE_V1.positionCoverage([{positions:[1,2]},{positions:[1]}])') == 2
        assert page.evaluate('ENGINE_V1.positionCoverage([{positions:[]},{positions:[]}])') == 0

        # Same attributes: only the new positions distinguish good and bad team splits.
        positioned = [dict(player, positions=[i % 5 + 1]) for i, player in enumerate(legacy)]
        upload(positioned)
        assert page.evaluate('''()=>{
          const w={...ENGINE_V1.weights(),positions:ENGINE_V1.positionContext(players,2)};
          const good=[players.slice(0,5),players.slice(5)];
          const bad=[[0,1,2,5,6].map(i=>players[i]),[3,4,7,8,9].map(i=>players[i])];
          return ENGINE_V1.penalty(good,w)<ENGINE_V1.penalty(bad,w);
        }''')
        for priority in ['balanced', 'roles', 'level', 'height', 'speed']:
            page.locator('#priority').select_option(priority)
            page.locator('#generateBtn').click()
            assert page.evaluate('lastResult.teams.every(t=>ENGINE_V1.positionCoverage(t.map(id=>players.find(p=>p.id===id)))===5)')
            assert page.locator('.teamline').count() == 10
        # Flexible players can be used for different slots in each team.
        flexible = [dict(player, positions=[1,2] if i % 5 == 0 else [i % 5 + 1]) for i, player in enumerate(legacy)]
        upload(flexible)
        page.locator('#generateBtn').click()
        assert page.evaluate('lastResult.teams.every(t=>ENGINE_V1.positionCoverage(t.map(id=>players.find(p=>p.id===id)))===5)')

        # Uneven teams, missing information, absent players and impossible coverage.
        mixed = [dict(player, positions=[1,2] if i % 2 else [], present=i != 9) for i, player in enumerate(legacy)]
        upload(mixed)
        for count in [2, 3, 4]:
            page.locator('#teamCount').select_option(str(count))
            page.locator('#generateBtn').click()
            result = page.evaluate('lastResult')
            ids = sum(result['teams'], [])
            sizes = list(map(len, result['teams']))
            assert len(ids) == len(set(ids)) == 9 and '9' not in ids
            assert len(sizes) == count and max(sizes) - min(sizes) <= 1

        # Inspect the actual AI request with a mocked provider, without credentials/network calls.
        def provider(route):
            payload = route.request.post_data_json
            prompt = payload['messages'][1]['content']
            assert 'Un joueur polyvalent ne couvre qu’un poste à la fois' in prompt
            assert '"positions"' in prompt
            selected = [player['id'] for player in mixed if player['present']]
            answer = dict(teams=[selected[:3], selected[3:5], selected[5:7], selected[7:]], bench=[])
            route.fulfill(json=dict(choices=[dict(message=dict(content=json.dumps(answer)))]))
        page.route('https://api.openai.com/**', provider)
        page.locator('#apiKey').fill('test-only-placeholder')
        page.locator('#aiBtn').click()
        page.wait_for_function('lastResult.source === "ia"')
        assert page.locator('.teamline').count() == 9

        for width in [390, 1280]:
            page.set_viewport_size(dict(width=width, height=900))
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        assert not errors, errors
        browser.close()
finally:
    server.shutdown()
print('PASS: legacy import/storage, multi-select CRUD, export round-trip, normalization, matching, position-aware generation (5 priorities), uneven/missing/absent cases, mocked AI request, mobile/desktop.')
