# Purpose panels: one stream per purpose, one player, Like, Dislike and Next by chapter, no mixer running, votes per purpose.
# Usage: ~/ComfyUI/venv/bin/python modes.py URL
import asyncio, json, subprocess, re, sys
from playwright.async_api import async_playwright
U = sys.argv[1]; fails = []
def check(n, ok, d=''):
    print('PASS' if ok else 'FAIL', n, str(d)[:170], flush=True)
    if not ok: fails.append(n)
INIT = """window.__els=new Set();const op=HTMLMediaElement.prototype.play;HTMLMediaElement.prototype.play=function(){__els.add(this);return op.apply(this,arguments)};
window.__ctx=0;const AC=window.AudioContext||window.webkitAudioContext;if(AC){const W=function(o){__ctx++;return new AC(o)};W.prototype=AC.prototype;window.AudioContext=W;window.webkitAudioContext=W}
window.__pick=[];HTMLMediaElement.prototype.webkitShowPlaybackTargetPicker=function(){__pick.push({src:this.src.slice(-24),air:this.getAttribute('x-webkit-airplay')})};"""
ON = "[...__els].filter(a=>!a.paused&&!a.src.startsWith('data:')).map(a=>({s:a.src.split('/').pop(),t:+a.currentTime.toFixed(1),d:Math.round(a.duration||0),l:a.loop,e:a.error&&a.error.code}))"
SEEK = "(t)=>{const a=[...__els].find(a=>!a.paused);a.currentTime=t}"
async def run(p, name):
    b = await (p.webkit.launch() if name == 'webkit' else p.chromium.launch(channel='chrome', headless=True, args=['--autoplay-policy=no-user-gesture-required', '--mute-audio']))
    c = await b.new_context(viewport={'width': 390, 'height': 844}); q = await c.new_page(); e = []; q.on('pageerror', lambda x: e.append(str(x)))
    sent = []
    async def vote(route):
        if route.request.method == 'POST': sent.append(json.loads(route.request.post_data))
        await route.fulfill(status=204, headers={'Access-Control-Allow-Origin': route.request.headers.get('origin', '*'), 'Access-Control-Allow-Headers': 'Content-Type', 'Access-Control-Allow-Methods': 'POST'})
    await c.route('**/vote', vote)
    await q.add_init_script(INIT); await q.goto(U); await q.wait_for_timeout(1200)
    rows = q.locator('.mode-row')
    check(name + ' six purposes and Noise only listed', await rows.count() == 7 and 'Love' in await q.inner_text('#modeList') and 'Noise only' in await q.inner_text('#modeList'), await q.inner_text('#modeList'))
    check(name + ' question shown', await q.inner_text('.tagline') == 'What do you need right now?')
    check(name + ' first screen: all purposes visible', await q.evaluate("document.querySelector('#modeList').getBoundingClientRect().bottom<innerHeight"))
    check(name + ' mixer tucked under Customize', not await q.locator('#bnPlay').is_visible() and await q.locator('#customizeBtn').is_visible() and await q.locator('#mixMaster').is_visible())
    check(name + ' now-playing hidden until something plays', not await q.locator('#modeNow').is_visible())
    await rows.filter(has_text='Flow').click(); await q.wait_for_function(ON + ".some(x=>x.t>1)", timeout=40000); st = await q.evaluate(ON)
    check(name + ' Flow plays one stream', len(st) == 1 and st[0]['s'] == 'flow-v2.m4a' and st[0]['l'] and not st[0]['e'], st)
    check(name + ' no audio mixer running', await q.evaluate('__ctx') == 0, await q.evaluate('__ctx'))
    first = await q.inner_text('#modeNowName'); check(name + ' now playing names a track', ' – ' in first, first)
    await q.click('#modeNext'); await q.wait_for_timeout(1500); second = await q.inner_text('#modeNowName')
    check(name + ' Next moves to the next track', second != first and ' – ' in second, (first, second))
    await q.click('#modeLike'); await q.wait_for_timeout(300); check(name + ' Like marked', await q.get_attribute('#modeLike', 'aria-pressed') == 'true')
    v = list(sent[-1]['votes'].items())[-1] if sent else ('', 0)
    check(name + ' Like sent for this purpose', v[0].startswith('flow--') and v[1] == 1 and len(v[0]) <= 100, v)
    await q.click('#modeDislike'); await q.wait_for_timeout(1500); third = await q.inner_text('#modeNowName')
    check(name + ' Dislike skips the track', third != second, (second, third))
    v = list(sent[-1]['votes'].items())[-1]; check(name + ' Dislike sent for this purpose', v[0].startswith('flow--') and v[1] == -1, v)
    k = v[0]
    # a disliked track is skipped when reached again in this purpose, and not in others
    ch = await q.evaluate("(async()=>(await (await fetch('tracks/modes.json')).json()).modes)()")
    flow = [m for m in ch if m['id'] == 'flow'][0]; bad = [x for x in flow['chapters'] if k == 'flow--' + x['id']][0]
    await q.evaluate(SEEK, bad['t'] + 2); await q.wait_for_timeout(1800)
    check(name + ' disliked track is skipped next time', await q.inner_text('#modeNowName') != bad['name'], await q.inner_text('#modeNowName'))
    await q.click('.toast-action') if await q.locator('.toast-action').count() else None
    # switching
    await rows.filter(has_text='Meditate').click(); await q.wait_for_function(ON + ".some(x=>x.s=='meditate-v2.m4a'&&x.t>1)", timeout=40000); st = await q.evaluate(ON)
    check(name + ' switching leaves one stream playing', len(st) == 1, st)
    await q.locator('.mode-row', has_text='Meditate').click(); await q.wait_for_timeout(400)
    check(name + ' tapping again stops it', await q.evaluate(ON) == [] and not await q.locator('#modeNow').is_visible())
    # Noise only: brown by default, one looping stream, color buttons instead of Like/Dislike/Next
    await rows.filter(has_text='Noise only').click(); await q.wait_for_function(ON + ".some(x=>x.s=='noise-brown.m4a'&&x.t>1)", timeout=40000); st = await q.evaluate(ON)
    check(name + ' Noise only plays brown alone, looping', len(st) == 1 and st[0]['l'] and st[0]['d'] == 3600 and await q.evaluate('__ctx') == 0, st)
    check(name + ' Noise only shows colors, not Like', await q.locator('#modeColors button').count() == 3 and not await q.locator('#modeLike').is_visible() and await q.inner_text('#modeNowName') == 'Brown')
    await q.locator('#modeColors button', has_text='Pink').click(); await q.wait_for_function(ON + ".some(x=>x.s=='noise-pink.m4a'&&x.t>1)", timeout=40000); st = await q.evaluate(ON)
    check(name + ' Pink switches the stream', len(st) == 1 and st[0]['s'] == 'noise-pink.m4a' and await q.locator('#modeColors button', has_text='Pink').get_attribute('aria-pressed') == 'true', st)
    await q.locator('#modeColors button', has_text='Brown').click(); await q.wait_for_timeout(300)
    await q.locator('.mode-row', has_text='Noise only').click(); await q.wait_for_timeout(400)
    check(name + ' tapping Noise only again stops it', await q.evaluate(ON) == [])
    # Run climbs in tempo
    run = [m for m in ch if m['id'] == 'run'][0]
    check(name + ' Run has the new music and starts on the slower tracks', len(run['chapters']) == 34 and ('Barby' in run['chapters'][0]['name'] or 'Octogoat' in run['chapters'][0]['name']), run['chapters'][0]['name'])
    await rows.filter(has_text='Run').click(); await q.wait_for_function(ON + ".some(x=>x.s=='run.m4a'&&x.t>1)", timeout=40000)
    check(name + ' Run plays', ' – ' in await q.inner_text('#modeNowName'))
    # Sleep arc: music, then noise only
    await rows.filter(has_text='Sleep').click(); await q.wait_for_function(ON + ".some(x=>x.t>0.5)", timeout=40000); st = await q.evaluate(ON)
    check(name + ' Sleep plays the Night Arc, does not repeat', 'night-arc' in st[0]['s'] and not st[0]['l'] and st[0]['d'] == 21600, st)
    await q.evaluate(SEEK, 4000); await q.wait_for_timeout(1500)
    check(name + ' after the fade: noise only, nothing to rate', await q.inner_text('#modeNowName') == 'Noise only' and await q.is_disabled('#modeLike') and await q.is_disabled('#modeNext'))
    await q.evaluate("document.getElementById('mixMaster').value=50;document.getElementById('mixMaster').dispatchEvent(new Event('input',{bubbles:true}))"); await q.wait_for_timeout(200)
    check(name + ' Master volume reaches the stream', abs(await q.evaluate("[...__els].find(a=>!a.paused).volume") - 0.25) < 0.01)
    await q.click('#speakerBtn'); await q.wait_for_timeout(300); pk = await q.evaluate('__pick')
    check(name + ' Choose speaker targets the stream', pk and 'night-arc' in pk[-1]['src'] and pk[-1]['air'] == 'allow', pk)
    check(name + ' screen not held awake', await q.evaluate("!window.__wakeHeld"))
    # mixer takes over cleanly
    await q.click('#customizeBtn'); await q.wait_for_timeout(200)
    check(name + ' Customize opens the mixer', await q.locator('#bnPlay').is_visible() and await q.locator('#noiseBtn').is_visible())
    await q.evaluate('scrollTo(0, document.body.scrollHeight)'); await q.wait_for_timeout(400)
    check(name + ' no mixer play icon while a purpose plays', not await q.locator('#bnMini').is_visible())
    await q.evaluate('scrollTo(0, 0)'); await q.wait_for_timeout(200)
    check(name + ' purpose buttons have clean names', await q.get_attribute('.mode-row[data-mode="sleep"]', 'aria-label') == 'Sleep')
    await q.click('#noiseBtn'); await q.wait_for_timeout(1200)
    check(name + ' mixer stops the purpose stream', not any('night-arc' in x['s'] for x in await q.evaluate(ON)) and not await q.locator('#modeNow').is_visible())
    await q.click('#noiseBtn'); await q.wait_for_timeout(500)
    await q.click('#layerMusicBtn'); await q.click('#tabLibrary'); await q.wait_for_timeout(200)
    check(name + ' noise colors are in the Library', await q.locator('#paneLibrary #bnColors button').count() == 7)
    await q.locator('#bnColors button').nth(1).click(); await q.wait_for_timeout(300)
    check(name + ' choosing a color works', await q.locator('#bnColors button').nth(1).get_attribute('aria-pressed') == 'true')
    await q.click('[data-set="lang:es"]'); await q.wait_for_timeout(300)
    check(name + ' Spanish', await q.inner_text('.tagline') == '¿Qué necesitas ahora?' and 'Dormir' in await q.inner_text('#modeList'), await q.inner_text('#modeList'))
    await q.click('[data-set="lang:en"]'); await q.wait_for_timeout(200)
    for lay in ['tiles', 'compact', 'large', 'list']:
        await q.evaluate(f"document.querySelector('[data-set=\\'layout:{lay}\\']').click()"); await q.wait_for_timeout(250)
        check(name + ' layout ' + lay + ' applies, no sideways scroll', await q.evaluate("document.documentElement.getAttribute('data-layout')") == lay and await q.evaluate('document.documentElement.scrollWidth-innerWidth') <= 0)
    await q.evaluate("document.querySelector('[data-set=\\'icons:off\\']').click()"); await q.wait_for_timeout(200)
    check(name + ' icons can be hidden', not await q.locator('.mode-row[data-mode="love"] .mode-glyph').is_visible())
    await q.evaluate("document.querySelector('[data-set=\\'icons:on\\']').click()"); await q.wait_for_timeout(200)
    check(name + ' icons shown by default', await q.locator('.mode-row[data-mode="love"] .mode-glyph').is_visible())
    await q.evaluate("document.querySelector('[data-set=\\'buttons:square\\']').click()"); await q.wait_for_timeout(200)
    check(name + ' square buttons', await q.evaluate("getComputedStyle(document.querySelector('.mode-icon')).borderRadius") == '4px')
    await q.evaluate("document.querySelector('[data-set=\\'buttons:round\\']').click()"); await q.wait_for_timeout(200)
    check(name + ' no sideways scroll', await q.evaluate('document.documentElement.scrollWidth-innerWidth') <= 0)
    check(name + ' no page errors', e == [], e)
    await b.close()
def cpu(root):
    kids, times = {}, {}
    for r in subprocess.run(['ps', '-axo', 'pid=,ppid=,time='], capture_output=True, text=True).stdout.splitlines():
        x, y, z = r.split(); m = re.match(r'(?:(\d+):)?(\d+):(\d+(?:\.\d+)?)', z)
        times[int(x)] = int(m.group(1) or 0) * 3600 + int(m.group(2)) * 60 + float(m.group(3)); kids.setdefault(int(y), []).append(int(x))
    total, st = 0, [root]
    while st:
        n = st.pop(); total += times.get(n, 0); st += kids.get(n, [])
    return total
async def battery(p):
    b = await p.chromium.launch(channel='chrome', headless=True, args=['--autoplay-policy=no-user-gesture-required', '--mute-audio'])
    root = min(int(x) for x in subprocess.run(['pgrep', '-f', 'remote-debugging-pipe'], capture_output=True, text=True).stdout.split())
    q = await (await b.new_context(viewport={'width': 1280, 'height': 800}, device_scale_factor=2)).new_page(); await q.goto(U); await q.wait_for_timeout(1200)
    await q.locator('.mode-row', has_text='Sleep').click(); await q.wait_for_timeout(66000)
    a = cpu(root); await q.wait_for_timeout(20000); pct = (cpu(root) - a) / 20 * 100
    check('battery limit: Sleep idle under 10% of a core', pct < 10, f'{pct:.1f}%')
    await b.close()
async def main():
    async with async_playwright() as p:
        await run(p, 'chromium'); await run(p, 'webkit'); await battery(p)
    print('MODES', 'FAILED ' + str(fails) if fails else 'PASSED'); sys.exit(1 if fails else 0)
asyncio.run(main())
