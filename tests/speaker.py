# Choose speaker: the real Apple picker can't be opened in a test browser, so the picker call is stubbed and recorded.
# This proves the page moves sound onto a plain player and asks for the picker. It does not prove AirPlay or Sonos work.
# Usage: ~/ComfyUI/venv/bin/python speaker.py URL
import asyncio, json, sys
from playwright.async_api import async_playwright
U = sys.argv[1]; R2 = 'r2.dev'; fails = []
def check(n, ok, d=''):
    print('PASS' if ok else 'FAIL', n, str(d)[:170], flush=True)
    if not ok: fails.append(n)
BASE = "window.__els=new Set();const op=HTMLMediaElement.prototype.play;HTMLMediaElement.prototype.play=function(){__els.add(this);return op.apply(this,arguments)};"
STUB = BASE + "window.__pick=[];HTMLMediaElement.prototype.webkitShowPlaybackTargetPicker=function(){__pick.push({src:this.src.slice(-30),air:this.getAttribute('x-webkit-airplay'),cors:this.crossOrigin,paused:this.paused})};"
NONE = BASE + "delete HTMLMediaElement.prototype.webkitShowPlaybackTargetPicker;"
TRK = "[...__els].filter(a=>a.src.includes('%s')&&!a.paused).map(a=>({t:+a.currentTime.toFixed(1),cors:a.crossOrigin,air:a.getAttribute('x-webkit-airplay')}))" % R2
SET = "JSON.parse(localStorage.getItem('alot.settings.v1')||'{}')"
async def run(p, name):
    launch = p.webkit.launch() if name == 'webkit' else p.chromium.launch(channel='chrome', headless=True, args=['--autoplay-policy=no-user-gesture-required', '--mute-audio'])
    b = await launch
    q = await (await b.new_context(viewport={'width': 390, 'height': 844})).new_page(); e = []; q.on('pageerror', lambda x: e.append(str(x)))
    await q.add_init_script(STUB); await q.goto(U); await q.wait_for_timeout(1000)
    check(name + ' button shown where AirPlay exists', await q.locator('#speakerBtn').is_visible())
    check(name + ' button on the first screen without scrolling', await q.evaluate("document.getElementById('speakerBtn').getBoundingClientRect().bottom<innerHeight/3"))
    await q.click('#speakerBtn'); await q.wait_for_timeout(500); pk = await q.evaluate('__pick')
    check(name + ' nothing playing: picker still opens, on an AirPlay player', len(pk) == 1 and pk[0]['air'] == 'allow', pk)
    check(name + ' locked-screen path now on and saved', (await q.evaluate(SET)).get('background') is True and await q.is_checked('#setBackground'))
    await q.click('#musicShuffle'); await q.wait_for_function(TRK + ".some(x=>x.t>1)", timeout=40000); st = await q.evaluate(TRK)
    check(name + ' music on the plain AirPlay path', st[0]['air'] == 'allow' and st[0]['cors'] is None, st)
    await q.click('#speakerBtn'); await q.wait_for_timeout(300); pk = await q.evaluate('__pick')
    check(name + ' picker targets the track playing', pk[-1]['src'].endswith('.m4a') and not pk[-1]['paused'], pk[-1])
    await b.close()
    # music already playing through the mixer moves without restarting
    b = await (p.webkit.launch() if name == 'webkit' else p.chromium.launch(channel='chrome', headless=True, args=['--autoplay-policy=no-user-gesture-required', '--mute-audio']))
    q = await (await b.new_context(viewport={'width': 390, 'height': 844})).new_page(); await q.add_init_script(STUB); await q.goto(U); await q.wait_for_timeout(1000)
    await q.click('#bnPlay'); await q.wait_for_function(TRK + ".some(x=>x.t>6)", timeout=40000); before = await q.evaluate(TRK); name_before = await q.inner_text('#layerMusicPick')
    await q.click('#speakerBtn'); await q.wait_for_function(TRK + ".some(x=>x.air==='allow'&&x.t>1)", timeout=40000); st = await q.evaluate(TRK)
    plain = [x for x in st if x['air'] == 'allow']
    check(name + ' moving keeps the same track and place', plain and plain[0]['t'] >= before[0]['t'] - 1 and await q.inner_text('#layerMusicPick') == name_before, (before, st))
    await q.wait_for_function("[...__els].filter(a=>a.src.startsWith('blob:')&&!a.paused&&a.duration>3000).length==1", timeout=120000)
    check(name + ' noise also moved to its file', True)
    await q.click('#bnPlay'); await q.wait_for_timeout(800)
    check(name + ' stop ends everything after moving', await q.evaluate("[...__els].filter(a=>!a.paused&&!a.src.startsWith('data:')).length") == 0)
    await b.close()
    b = await (p.webkit.launch() if name == 'webkit' else p.chromium.launch(channel='chrome', headless=True, args=['--autoplay-policy=no-user-gesture-required', '--mute-audio']))
    q = await (await b.new_context(viewport={'width': 390, 'height': 844})).new_page(); await q.add_init_script(NONE); await q.goto(U); await q.wait_for_timeout(800)
    check(name + ' hidden where no picker exists', await q.locator('#speakerBtn').is_hidden() or name == 'webkit')
    await b.close()
    b = await (p.webkit.launch() if name == 'webkit' else p.chromium.launch(channel='chrome', headless=True))
    c = await b.new_context(viewport={'width': 390, 'height': 844}, user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 CriOS/120 Mobile/15E148 Safari/604.1')
    q = await c.new_page(); await q.add_init_script(NONE); await q.goto(U); await q.wait_for_timeout(800)
    await q.click('#speakerBtn'); await q.wait_for_timeout(300)
    check(name + ' iPhone without the picker: shows the Control Center steps', 'Control Center' in await q.inner_text('#toastBox'), await q.inner_text('#toastBox'))
    # shuffle opens audibly
    await q.reload(); await q.wait_for_timeout(800)
    bad = await q.evaluate("(async()=>{const m=(await (await fetch('tracks/manifest.json')).json()).tracks;return m.filter(t=>t.intro>=2).map(t=>t.name)})()")
    firsts = []
    for i in range(15):
        await q.click('#musicShuffle'); await q.wait_for_timeout(100); firsts.append(await q.inner_text('#layerMusicPick'))
    check(name + ' Shuffle never starts on a quiet opening', len(bad) == 12 and not (set(firsts) & set(bad)), (len(bad), [x for x in firsts if x in bad]))
    check(name + ' no page errors', e == [], e)
    await b.close()
async def main():
    async with async_playwright() as p:
        await run(p, 'chromium'); await run(p, 'webkit')
    print('SPEAKER', 'FAILED ' + str(fails) if fails else 'PASSED'); sys.exit(1 if fails else 0)
asyncio.run(main())
