# Streaming from R2: tracks come from our storage, reach the mix (not silent), seek, hand over, and layer with noise.
# Usage: ~/ComfyUI/venv/bin/python stream.py URL
import asyncio, sys
from playwright.async_api import async_playwright
U = sys.argv[1]; R2 = 'pub-dfe2dc87a34d4016a8782237145e0938.r2.dev'; fails = []
def check(n, ok, d=''):
    print('PASS' if ok else 'FAIL', n, str(d)[:170], flush=True)
    if not ok: fails.append(n)
INIT = """window.__els=new Set();const op=HTMLMediaElement.prototype.play;HTMLMediaElement.prototype.play=function(){__els.add(this);return op.apply(this,arguments)};
window.__an=[];const ca=BaseAudioContext.prototype.createAnalyser;BaseAudioContext.prototype.createAnalyser=function(){const n=ca.apply(this,arguments);__an.push(n);return n};"""
RMS = "(async()=>{const a=__an[0];const t=new Float32Array(a.fftSize);let m=0;for(let i=0;i<8;i++){a.getFloatTimeDomainData(t);m=Math.max(m,Math.sqrt(t.reduce((s,x)=>s+x*x,0)/t.length));await new Promise(r=>setTimeout(r,150))}return +m.toFixed(5)})()"
TRK = "[...__els].filter(a=>a.src.includes('%s')&&!a.paused).map(a=>({t:+a.currentTime.toFixed(1),d:+(a.duration||0).toFixed(1),e:a.error&&a.error.code,src:a.src.split('/').pop().slice(0,40)}))" % R2
async def setv(q, i, v):
    await q.evaluate("([i,v])=>{const e=document.getElementById(i);e.value=v;e.dispatchEvent(new Event('input',{bubbles:true}))}", [i, v]); await q.wait_for_timeout(600)
async def run(p, name):
    b = await (p.webkit.launch() if name == 'webkit' else p.chromium.launch(channel='chrome', headless=True, args=['--autoplay-policy=no-user-gesture-required', '--mute-audio']))
    q = await (await b.new_context(viewport={'width': 390, 'height': 844})).new_page(); e = []; bad = []
    q.on('pageerror', lambda x: e.append(str(x))); q.on('requestfailed', lambda r: bad.append(r.url[-50:]) if R2 in r.url and 'ERR_ABORTED' not in (r.failure or '') and 'cancelled' not in (r.failure or '').lower() else None)
    local = []; q.on('request', lambda r: local.append(r.url) if '.m4a' in r.url and R2 not in r.url else None)
    await q.add_init_script(INIT); await q.goto(U); await q.wait_for_timeout(1000)
    await q.click('#layerMusicBtn'); await q.wait_for_timeout(300)
    await q.click('#tabLibrary'); await q.wait_for_timeout(200)
    check(name + ' 10 albums listed, none built in', await q.locator('.album').count() == 10, await q.locator('.album').count())
    check(name + ' album counts add to 66', sum([int((await x.inner_text()).split('·')[-1]) for x in await q.locator('.album-meta').all()]) == 66)
    items = q.locator('#libraryList .library-item')
    for album, t in [('Ajnia: Oasis', 'Oasis'), ('HuuHaa: Frostient', 'Flake Genesis')]:
        await q.locator('.album-open', has_text=album).click(); await q.wait_for_timeout(200)
        await items.filter(has_text=t).first.locator('.library-add').click(); await q.wait_for_timeout(300)
    await q.click('#tabPlaylist')
    await q.wait_for_function("document.querySelectorAll('#takesList .take-item').length==2"); await q.click('#layerMusicBtn')
    await q.click('#bnPlay'); await q.wait_for_function(TRK + ".some(x=>x.t>1)", timeout=40000)
    st = await q.evaluate(TRK); check(name + ' plays from our storage', st and st[0]['d'] > 100 and not st[0]['e'], st)
    check(name + ' no music from anywhere else', local == [], local[:2])
    await q.wait_for_timeout(1000); both = await q.evaluate(RMS)
    await setv(q, 'bnVolume', 0); music = await q.evaluate(RMS)
    await setv(q, 'bnVolume', 50); await setv(q, 'mixTracks', 0); noise = await q.evaluate(RMS); await setv(q, 'mixTracks', 80)
    check(name + ' streamed music reaches the mix, not silent', music > 0.005, dict(music=music))
    check(name + ' layered with noise', noise > 0.002 and both > 0.002, dict(noise=noise, both=both))
    await q.evaluate("(()=>{const a=[...__els].find(a=>a.src.includes('%s')&&!a.paused);a.currentTime=a.duration*0.6})()" % R2); await q.wait_for_timeout(3000); st2 = await q.evaluate(TRK)
    check(name + ' jumps ahead without downloading the whole file first', st2 and st2[0]['t'] > st[0]['d'] * 0.55, st2)
    await q.evaluate("(()=>{const a=[...__els].find(a=>a.src.includes('%s')&&!a.paused);a.currentTime=a.duration-6})()" % R2)
    await q.wait_for_function("document.querySelector('.take-item.is-playing .take-name')&&document.querySelector('.take-item.is-playing .take-name').textContent.includes('Flake Genesis')", timeout=25000)
    await q.wait_for_timeout(5000); st3 = await q.evaluate(TRK)
    check(name + ' next track streams after the first ends', any('flake-genesis' in x['src'] and x['t'] > 0 for x in st3), st3)
    await q.click('#layerMusicBtn'); await q.click('#tabLibrary'); await q.locator('.album', has_text='GreatOwl').locator('.album-row .library-add').click(); await q.wait_for_timeout(500)
    check(name + ' adding a whole album', await q.locator('#takesList .take-item').count() == 8, await q.locator('#takesList .take-item').count())
    await q.click('#tabPlaylist'); await q.click('#layerMusicBtn')
    await q.click('#bnPlay'); await q.wait_for_timeout(900)
    check(name + ' stop ends it', await q.evaluate(TRK) == [])
    check(name + ' no failed requests or page errors', not e and not bad, (e, bad))
    await b.close()
async def ratings(p, name):
    b = await (p.webkit.launch() if name == 'webkit' else p.chromium.launch(channel='chrome', headless=True, args=['--autoplay-policy=no-user-gesture-required', '--mute-audio']))
    c = await b.new_context(viewport={'width': 390, 'height': 844}); q = await c.new_page(); e = []; q.on('pageerror', lambda x: e.append(str(x)))
    await q.add_init_script(INIT); await q.goto(U); await q.wait_for_timeout(1000)
    order = "[...document.querySelectorAll('#takesList .take-name')].map(x=>x.textContent)"
    check(name + ' Like and Dislike wait until there is a track', await q.is_disabled('#musicLike') and await q.is_disabled('#musicDislike'))
    await q.click('#musicShuffle'); await q.wait_for_function(TRK + ".some(x=>x.t>0.5)", timeout=40000); one = await q.evaluate(order)
    check(name + ' Shuffle: one tap, all 66 queued and playing', len(one) == 66, len(one))
    await q.click('#musicShuffle'); await q.wait_for_timeout(1500); two = await q.evaluate(order)
    check(name + ' Shuffle again gives a new order', sorted(one) == sorted(two) and one != two)
    noise = await q.get_attribute('#noiseBtn', 'aria-pressed'); check(name + ' Shuffle leaves noise alone', noise == 'false')
    await q.wait_for_function(TRK + ".some(x=>x.t>0.3)", timeout=40000)
    first = await q.inner_text('#layerMusicPick'); await q.click('#musicLike'); await q.wait_for_timeout(200)
    check(name + ' Like marks the track', await q.get_attribute('#musicLike', 'aria-pressed') == 'true', first)
    await q.click('#musicDislike'); await q.wait_for_timeout(1200); after = await q.inner_text('#layerMusicPick')
    check(name + ' Dislike moves to another track', after != first, (first, after))
    check(name + ' Dislike takes it off the list', first not in await q.evaluate(order))
    check(name + ' next track is not marked liked', await q.get_attribute('#musicLike', 'aria-pressed') == 'false')
    await q.click('.toast-action'); await q.wait_for_timeout(400)
    check(name + ' Undo puts it back', first in await q.evaluate(order))
    await q.click('#layerMusicPick', force=True, timeout=500) if False else None
    await q.click('#musicDislike'); await q.wait_for_timeout(1000); disliked = after
    bads = [await q.evaluate("JSON.parse(localStorage.getItem('alot.ratings.v1'))")]
    check(name + ' rating stored on this device', list(bads[0].values()).count(-1) == 1, bads[0])
    for i in range(3):
        await q.click('#musicShuffle'); await q.wait_for_timeout(500)
        check(f'{name} shuffle {i + 1} keeps the disliked track out', disliked not in await q.evaluate(order) and len(await q.evaluate(order)) == 65)
    # liked tracks come up sooner, on average
    liked_id = await q.evaluate("(async()=>{const m=(await (await fetch('tracks/manifest.json')).json()).tracks;return m[0]})()")
    await q.evaluate("(id)=>{const r=JSON.parse(localStorage.getItem('alot.ratings.v1'));r[id]=1;localStorage.setItem('alot.ratings.v1',JSON.stringify(r))}", liked_id['id']); await q.reload(); await q.wait_for_timeout(1000)
    spots = []
    for i in range(12):
        await q.click('#musicShuffle'); await q.wait_for_timeout(120); spots.append((await q.evaluate(order)).index(liked_id['name']))
    check(name + ' a liked track averages early in the order', sum(spots) / len(spots) < 22, spots)
    await q.wait_for_timeout(1500); check(name + ' fast Shuffle taps: still playing, no false error', await q.get_attribute('#musicBtn', 'aria-pressed') == 'true' and await q.evaluate(TRK) != [] and 'file' not in await q.inner_text('#toastBox'))
    await q.click('#musicBtn'); await q.wait_for_timeout(700)
    check(name + ' playlist button stops music', await q.evaluate(TRK) == [])
    await q.click('#musicBtn'); await q.wait_for_function(TRK + ".length>0", timeout=30000)
    check(name + ' playlist button starts music', await q.get_attribute('#musicBtn', 'aria-pressed') == 'true'); await q.click('#musicBtn')
    if name == 'chromium':
        await c.grant_permissions(['clipboard-read', 'clipboard-write'])
        await q.click('#layerMusicBtn'); await q.wait_for_timeout(200); await q.click('#ratingsCopy'); await q.wait_for_timeout(300)
        got = __import__('json').loads(await q.evaluate('navigator.clipboard.readText()'))
        check(name + ' Copy my ratings gives usable data', got.get('app') == 'alot' and len(got['ratings']) >= 2, got)
    await q.goto(U.split('?')[0] + 'credits.html'); await q.wait_for_timeout(300)
    txt = await q.inner_text('body')
    check(name + ' credits: every release, license and non-commercial note', txt.count('CC BY') == 10 and 'non-commercial' in txt and await q.locator('li').count() == 66, txt.count('CC BY'))
    check(name + ' no page errors', e == [], e)
    await b.close()
async def main():
    async with async_playwright() as p:
        await run(p, 'chromium'); await ratings(p, 'chromium'); await run(p, 'webkit'); await ratings(p, 'webkit')
    print('STREAM', 'FAILED ' + str(fails) if fails else 'PASSED'); sys.exit(1 if fails else 0)
asyncio.run(main())
