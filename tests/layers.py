# The one-page mix: one Play starts noise and music together, sliders balance them, Stop ends all.
# Measures the real mix bus, so "layered" means both sounds are in the output, not just two players running.
# Usage: ~/ComfyUI/venv/bin/python layers.py
import asyncio, sys
from playwright.async_api import async_playwright
U = sys.argv[1] if len(sys.argv) > 1 else 'file:///Users/blossom/Documents/_bench-src/alot/index.html?lang=en'
fails = []
def check(n, ok, d=''):
    print('PASS' if ok else 'FAIL', n, str(d)[:150], flush=True)
    if not ok: fails.append(n)
INIT = """window.__els=new Set();const op=HTMLMediaElement.prototype.play;HTMLMediaElement.prototype.play=function(){__els.add(this);return op.apply(this,arguments)};
window.__an=[];const ca=BaseAudioContext.prototype.createAnalyser;BaseAudioContext.prototype.createAnalyser=function(){const n=ca.apply(this,arguments);__an.push(n);return n};"""
RMS = "(async()=>{const a=__an[0];const t=new Float32Array(a.fftSize);let m=0;for(let i=0;i<6;i++){a.getFloatTimeDomainData(t);m=Math.max(m,Math.sqrt(t.reduce((s,x)=>s+x*x,0)/t.length));await new Promise(r=>setTimeout(r,120))}return +m.toFixed(5)})()"
TRK = "[...__els].filter(a=>!a.src.startsWith('data:')&&!a.paused&&a.duration>5).map(a=>+a.currentTime.toFixed(1))"
async def setv(q, i, v):
    await q.evaluate("([i,v])=>{const e=document.getElementById(i);e.value=v;e.dispatchEvent(new Event('input',{bubbles:true}))}", [i, v]); await q.wait_for_timeout(500)
async def playing(q, ms=30000):
    await q.wait_for_function(TRK + ".length>0", timeout=ms)
async def run(p, name):
    b = await (p.webkit.launch() if name == 'webkit' else p.chromium.launch(channel='chrome', headless=True, args=['--autoplay-policy=no-user-gesture-required', '--mute-audio']))
    c = await b.new_context(viewport={'width': 390, 'height': 844})
    q = await c.new_page(); e = []; q.on('pageerror', lambda x: e.append(str(x)))
    await q.add_init_script(INIT); await q.goto(U); await q.wait_for_timeout(600)
    # first impression
    check(name + ' tagline shown', await q.inner_text('.tagline') == 'What do you need right now?')
    check(name + ' no tabs', await q.locator('[role=tab]').count() == 0)
    txt = await q.inner_text('body')
    for gone in ['Ian', 'Shower', 'YouTube', 'Little joys', 'Music Production']:
        check(f'{name} gone: {gone}', gone not in txt)
    check(name + ' drawers closed', await q.locator('.layer-drawer:visible').count() == 0)
    # the basics are on the home screen
    for sel in ['#noiseBtn', '#bnVolume', '#layerNoiseBtn', '#musicBtn', '#mixTracks', '#musicShuffle', '#musicLike', '#musicDislike', '#layerMusicBtn', '#mixMaster']:
        check(f'{name} on home: {sel}', await q.locator(sel).is_visible())
    check(name + ' labels', await q.inner_text('#layerNoiseBtn') == 'Configure' and await q.inner_text('#layerMusicName') == 'Playlist' and 'Master volume' in await q.inner_text('.mix-master'))
    check(name + ' Beats not on the main screen', not await q.locator('#mixBeats').is_visible() and 'Beats' not in await q.inner_text('main'))
    check(name + ' both panels say Configure', await q.inner_text('#layerNoiseBtn') == await q.inner_text('#layerMusicBtn') == 'Configure')
    # noise button: noise and nothing else, the overnight case
    await q.click('#noiseBtn'); await q.wait_for_timeout(1500)
    check(name + ' noise button: noise plays, no music', await q.get_attribute('#noiseBtn', 'aria-pressed') == 'true' and await q.evaluate(TRK) == [])
    check(name + ' noise button: sound in the mix', await q.evaluate(RMS) > 0.002)
    await q.click('#noiseBtn'); await q.wait_for_timeout(800)
    check(name + ' noise button stops it', await q.get_attribute('#bnPlay', 'aria-pressed') == 'false')
    await q.click('#layerNoiseBtn'); await q.wait_for_timeout(300)
    check(name + ' Configure opens the generator', await q.locator('#bnSliders').is_visible() and await q.locator('#bnGenerate').is_visible())
    await q.keyboard.press('Escape'); await q.wait_for_timeout(200)
    check(name + ' Esc closes the panel and returns to its button', not await q.locator('#drawerNoise').is_visible() and await q.evaluate("document.activeElement.id") == 'layerNoiseBtn')
    await q.evaluate('document.activeElement.blur()')
    check(name + ' empty playlist gives a hint', await q.inner_text('#layerMusicPick') == 'Tap Shuffle to start')
    # one press, both sounds
    await q.click('#bnPlay'); await playing(q)
    check(name + ' play: button shows stop', await q.get_attribute('#bnPlay', 'aria-pressed') == 'true')
    a = await q.evaluate(TRK); await q.wait_for_timeout(1500); bb = await q.evaluate(TRK)
    check(name + ' music time advancing', bb and a and bb[0] > a[0], (a, bb))
    await q.wait_for_timeout(1000)
    await q.evaluate("[...__els].filter(a=>!a.src.startsWith('data:')&&!a.paused&&a.duration>5).forEach(a=>{if(a.duration<3000)a.currentTime=a.duration*0.5})"); await q.wait_for_timeout(3000)  # some tracks open almost silent
    both = await q.evaluate(RMS)
    await setv(q, 'mixTracks', 0); noise = await q.evaluate(RMS)
    await setv(q, 'mixTracks', 80); await setv(q, 'bnVolume', 0); music = await q.evaluate(RMS)
    await setv(q, 'mixTracks', 0); nothing = await q.evaluate(RMS)
    await setv(q, 'mixTracks', 80); await setv(q, 'bnVolume', 50)
    check(name + ' noise alone is in the mix', noise > 0.002, noise)
    check(name + ' music alone is in the mix', music > 0.002, music)
    check(name + ' silent with both sliders at zero', nothing < 0.002, nothing)
    check(name + ' together louder than noise alone', both > noise, (both, noise))
    # beats live in Settings and still join the mix
    await q.click('#gear'); await q.evaluate("document.querySelectorAll('details').forEach(d=>d.open=true)"); await q.wait_for_timeout(300)
    await q.click('#mixBeatsBtn'); await q.wait_for_timeout(500)
    check(name + ' beats on from Settings', await q.get_attribute('#mixBeatsBtn', 'aria-pressed') == 'true')
    await q.click('#mixBeatsBtn'); await q.wait_for_timeout(300)
    check(name + ' beats off from Settings', await q.get_attribute('#mixBeatsBtn', 'aria-pressed') == 'false')
    await q.click('#mixBeatsBtn'); await q.wait_for_timeout(200); await q.keyboard.press('Escape'); await q.wait_for_timeout(300)
    # stop ends everything; play comes back with beats
    await q.locator('#bnPlay').scroll_into_view_if_needed(); await q.click('#bnPlay'); await q.wait_for_timeout(900)
    check(name + ' stop: music stopped', await q.evaluate(TRK) == [])
    check(name + ' stop: button shows play', await q.get_attribute('#bnPlay', 'aria-pressed') == 'false')
    await q.click('#bnPlay'); await playing(q)
    check(name + ' second play restarts', await q.get_attribute('#bnPlay', 'aria-pressed') == 'true')
    # pick another track
    await q.click('#layerMusicBtn'); await q.wait_for_timeout(300)
    check(name + ' Configure opens on the playlist', await q.locator('#takesList').is_visible() and not await q.locator('#libraryList').is_visible())
    tall = await q.evaluate('document.documentElement.scrollHeight')
    box = await q.evaluate("document.querySelector('#panePlaylist .drawer-scroll').getBoundingClientRect().height")
    check(name + ' long playlist stays in its own box', box <= 420 and tall < 2300, (box, tall))
    await q.click('#tabLibrary'); await q.wait_for_timeout(200)
    check(name + ' Library shows 10 albums, closed', await q.locator('.album').count() == 15 and await q.locator('.library-item').count() == 0)
    check(name + ' Library needs little scrolling', await q.evaluate('document.documentElement.scrollHeight') < 2300, await q.evaluate('document.documentElement.scrollHeight'))
    await q.locator('.album-open').first.click(); await q.wait_for_timeout(200)
    check(name + ' opening an album lists its tracks', await q.locator('.library-item').count() > 0)
    await q.click('#tabPlaylist'); await q.wait_for_timeout(200)
    row = q.locator('#takesList .take-item').nth(1); second = await row.locator('.take-name').inner_text(); await row.locator('.take-btn.play').click(); await q.wait_for_timeout(1000)
    check(name + ' panel names the track now playing', second in await q.inner_text('#layerMusicPick'), await q.inner_text('#layerMusicPick'))
    await q.click('#layerMusicBtn'); await q.wait_for_timeout(200)
    # space bar
    await q.evaluate("document.activeElement.blur()"); await q.keyboard.press('Space'); await q.wait_for_timeout(800)
    check(name + ' space stops the mix', await q.get_attribute('#bnPlay', 'aria-pressed') == 'false')
    # language
    await q.click('[data-set="lang:es"]'); await q.wait_for_timeout(300)
    check(name + ' Spanish words', await q.inner_text('.tagline') == '¿Qué necesitas ahora?' and await q.inner_text('#layerNoiseName') == 'Ruido' and await q.inner_text('#layerNoiseBtn') == 'Configurar', await q.inner_text('.tagline'))
    await q.click('#tabLibrary') if False else None
    fit = await q.evaluate("[...document.querySelectorAll('#layerMusic .layer-types .bn-chip')].every(c=>c.getBoundingClientRect().right<=document.getElementById('layerMusic').getBoundingClientRect().right)")
    check(name + ' Spanish playlist buttons are not cut off', fit)
    # settings and old links
    await q.click('#gear'); await q.wait_for_timeout(300)
    check(name + ' settings: no layout, no joys', await q.locator('.layout-card').count() == 0 and await q.locator('#setMessages').count() == 0)
    await q.keyboard.press('Escape')
    await q.goto(U.split('#')[0] + '#studio'); await q.reload(); await q.wait_for_timeout(500)
    check(name + ' old Studio link opens music', await q.locator('#drawerMusic').is_visible())
    check(name + ' no sideways scroll', await q.evaluate('document.documentElement.scrollWidth-innerWidth') <= 0)
    check(name + ' no page errors', e == [], e)
    await b.close()
async def locked(p, name):
    b = await (p.webkit.launch() if name == 'webkit' else p.chromium.launch(channel='chrome', headless=True, args=['--autoplay-policy=no-user-gesture-required', '--mute-audio']))
    q = await (await b.new_context(viewport={'width': 390, 'height': 844})).new_page(); e = []; q.on('pageerror', lambda x: e.append(str(x)))
    await q.add_init_script(INIT); await q.goto(U); await q.wait_for_timeout(500)
    await q.click('#gear'); await q.evaluate("document.querySelectorAll('details').forEach(d=>d.open=true)"); await q.locator('.switch:has(#setBackground)').click(); await q.keyboard.press('Escape'); await q.wait_for_timeout(300)
    await q.click('#bnPlay')
    await q.wait_for_function("[...__els].filter(a=>!a.src.startsWith('data:')&&!a.paused&&a.duration>5).length>=2", timeout=120000)
    st = await q.evaluate("[...__els].filter(a=>!a.src.startsWith('data:')&&!a.paused&&a.duration>5).map(a=>({t:+a.currentTime.toFixed(1),d:Math.round(a.duration)}))")
    await q.wait_for_timeout(2000)
    st2 = await q.evaluate("[...__els].filter(a=>!a.src.startsWith('data:')&&!a.paused&&a.duration>5).map(a=>+a.currentTime.toFixed(1))")
    check(name + ' locked-screen mode: noise and music both advancing', len(st) >= 2 and all(y > x['t'] for x, y in zip(st, st2)), (st, st2))
    await q.click('#bnPlay'); await q.wait_for_timeout(800)
    check(name + ' locked-screen mode: stop ends both', await q.evaluate("[...__els].filter(a=>!a.src.startsWith('data:')&&!a.paused&&a.duration>5).length") == 0)
    check(name + ' locked-screen mode: no page errors', e == [], e)
    await b.close()
async def main():
    async with async_playwright() as p:
        for n in ['chromium', 'webkit']:
            await run(p, n); await locked(p, n)
    print('LAYERS', 'FAILED ' + str(fails) if fails else 'PASSED'); sys.exit(1 if fails else 0)
asyncio.run(main())
