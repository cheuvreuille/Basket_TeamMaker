"""Run with: python3 tests/check_manual_teams.py (Playwright + Chromium)."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import json
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
server = ThreadingHTTPServer(('127.0.0.1', 0), partial(SimpleHTTPRequestHandler, directory=str(ROOT)))
Thread(target=server.serve_forever, daemon=True).start()
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox'])
        page = browser.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(f'http://127.0.0.1:{server.server_port}/')
        page.wait_for_url('**/basket-equipes-autonome.html')
        assert page.locator('#appVersion').inner_text() == 'Version 1.4'
        assert not page.locator('#manualHelp').is_visible()
        data = [dict(id=str(i), name=f'Joueur {i}', height=170 + i*10, level=i+1, positions=[i+1]) for i in range(4)]
        page.locator('#importFile').set_input_files(dict(name='players.json', mimeType='application/json', buffer=json.dumps(data).encode()))
        page.wait_for_function('document.getElementById("importFile").value === ""')
        page.locator('#generateBtn').click()
        assert page.locator('#manualHelp').is_visible()
        assert page.locator('.move-player').count() == 4

        def fixture(source='local', count=2):
            teams = [['0','1'], ['2','3']] if count == 2 else [['0','1'], ['2'], ['3'], []]
            page.evaluate('(v)=>displayResult(v)', dict(teams=teams, bench=[], source=source))

        def invariant():
            assert sorted(page.evaluate('lastResult.teams.flat()')) == ['0','1','2','3']
            assert page.locator('.teamline').count() == 4
            assert page.evaluate('players.every(p=>p.present)')

        fixture()
        # Keyboard/mobile-friendly select moves the selected player only, and restores focus.
        page.locator('[data-player="0"] select').select_option('1')
        assert page.evaluate('lastResult.teams') == [['1'], ['2','3','0']]
        assert page.locator('[data-player="0"] select').evaluate('(e)=>e===document.activeElement')
        assert page.locator('[data-team="0"] .chip').inner_text() == '1 joueur'
        assert page.locator('[data-team="1"] .chip').inner_text() == '3 joueurs'
        stats = page.locator('[data-team="1"] .stats').inner_text()
        assert 'Niveau moy. 2.7' in stats and 'Taille moy. 186.7 cm' in stats
        assert 'Modifiées manuellement' in page.locator('#resultMeta').inner_text()
        invariant()
        # Empty teams have finite/meaningful stats and can receive a player again.
        page.locator('[data-player="1"] select').select_option('1')
        assert page.locator('[data-team="0"] .empty-team').is_visible()
        assert 'NaN' not in page.locator('#teams').inner_text()
        assert 'Niveau moy. —' in page.locator('[data-team="0"]').inner_text()
        page.locator('[data-player="2"] select').select_option('0')
        invariant()
        # Clipboard follows the edited result.
        page.evaluate('Object.defineProperty(navigator,"clipboard",{configurable:true,value:{writeText:async text=>{window.copied=text}}})')
        page.locator('#copyBtn').click()
        assert page.evaluate('window.copied').splitlines()[0] == 'Équipe 1 : Joueur 2'
        # Desktop drag/drop, including dropping into an empty card.
        fixture(count=4)
        page.locator('[data-player="0"]').drag_to(page.locator('[data-team="3"]'))
        assert page.evaluate('lastResult.teams') == [['1'], ['2'], ['3'], ['0']]
        invariant()
        assert page.locator('.drop-target').count() == 0
        # Ignored invalid/same-team moves cannot lose or duplicate a player.
        before = page.evaluate('lastResult.teams')
        page.evaluate('movePlayer("0",3,3);movePlayer("0",3,8);movePlayer("missing",0,1);movePlayer("0",0,1)')
        assert page.evaluate('lastResult.teams') == before
        # The same editor supports AI-generated results and preserves method provenance.
        fixture(source='ia')
        page.locator('[data-player="0"] select').select_option('1')
        assert page.evaluate('lastResult.source') == 'ia'
        assert 'IA · Modifiées manuellement' in page.locator('#resultMeta').inner_text()
        # Selecting a different generation count must not change destinations of existing results.
        page.locator('#teamCount').select_option('4')
        assert page.locator('[data-player="0"] select option').count() == 2
        # A new generation replaces manual changes and their marker.
        page.locator('#generateBtn').click()
        assert page.locator('.team').count() == 4
        assert 'Modifiées manuellement' not in page.locator('#resultMeta').inner_text()
        invariant()
        for width in [390, 1280]:
            page.set_viewport_size(dict(width=width, height=900))
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        assert not errors, errors
        browser.close()
finally:
    server.shutdown()
print('PASS: v1.4, move menu, drag/drop, empty teams, stats, clipboard, uniqueness, AI results, regeneration, responsive layout.')
