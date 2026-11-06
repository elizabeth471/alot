# Overnight behaviour: the page goes quiet visually but the sound never stops, and the screen is only held when it should be.
# Usage: ~/ComfyUI/venv/bin/python overnight.py URL
import asyncio, json, sys
from playwright.async_api import async_playwright
U = sys.argv[1]; fails = []
def check(n, ok, d=''):
    print('PASS' if ok else 'FAIL', n, str(d)[:140], flush=True)
    if not ok: fails.append(n)
INIT = """window.__els=new Set();const op=HTMLMediaElement.prototype.play;HTMLMediaElement.prototype.play=function(){__els.add(this);return op.apply(this,arguments)};
window.__wake=0;window.__asked=0;if(navigator.wakeLock){const r=navigator.wakeLock.request.bind(navigator.wakeLock);navigator.wakeLock.request=function(t){__asked++;return r(t).then(l=>{__wake=1;l.addEventListener('release',()=>{__wake=0});return l})}}"""
TRK = "[...__els].filter(a=>!a.paused&&a.duration>5).map(a=>+a.currentTime.toFixed(1))"
HASH = "(()=>{const c=document.getElementById('bnCanvas'),d=c.getContext('2d').getImageData(0,0,c.width,c.height).data;let s=0;for(let i=0;i<d.length;i+=397)s=(s*31+d[i])%1000003;return s})()"
def launch(p): return p.chromium.launch(channel='chrome', headless=True, args=['--autoplay-policy=no-user-gesture-required', '--mute-audio'])
async def page(b, stored=None, **ctx):
    c = await b.new_context(viewport={'width': 1280, 'height': 800}, **ctx); q = await c.new_page(); await q.add_init_script(INIT)
    if stored is not None: await q.add_init_script("if(!sessionStorage.seeded){sessionStorage.seeded=1;localStorage.setItem('alot.settings.v1',%r)}" % json.dumps(stored))
    await q.goto(U); await q.wait_for_timeout(800); return q
async def main():
    async with async_playwright() as p:
        b = await launch(p)
        q = await page(b); await q.click('#bnPlay'); await q.wait_for_function(TRK + '.length>0', timeout=30000)
        check('computer default: screen not held', await q.evaluate('__asked') == 0)
        check('playing has no endless animation', await q.evaluate("document.getAnimations().filter(a=>a.effect.getTiming().iterations===Infinity).length") == 0)
        await q.wait_for_timeout(2000); h0 = await q.evaluate(HASH); await q.wait_for_timeout(1500); h1 = await q.evaluate(HASH)
        check('background moves while in use', h0 != h1)
        # Sampled, because the track loops: a single before-and-after can't tell a loop from a stall.
        ALL = "[...__els].filter(a=>!a.paused&&a.duration>5).map(a=>({t:a.currentTime,d:a.duration}))"
        moved = 0; silent = 0; prev = await q.evaluate(ALL)
        for i in range(33):
            await q.wait_for_timeout(2000); now = await q.evaluate(ALL)
            if not now: silent += 1
            elif prev:
                gain = max(n['t'] for n in now) - max(x['t'] for x in prev)
                moved += gain if gain > 0 else 2  # looped back to the start during this sample
            prev = now
        h2 = await q.evaluate(HASH); await q.wait_for_timeout(2500); h3 = await q.evaluate(HASH)
        check('after 60 s idle: background frozen', h2 == h3)
        check('after 60 s idle: never silent, about 66 s of music played', silent == 0 and moved > 60 and await q.get_attribute('#bnPlay', 'aria-pressed') == 'true', dict(silent=silent, moved=round(moved, 1)))
        await q.mouse.move(300, 300); await q.wait_for_timeout(1500); h4 = await q.evaluate(HASH)
        check('mouse movement wakes the background', h4 != h3)
        await q.click('#bnPlay'); await b.close()
        b = await launch(p)
        q = await page(b, {'keepAwake': True}); await q.click('#bnPlay'); await q.wait_for_timeout(1500)
        check('old saved setting no longer holds a computer screen', await q.evaluate('__asked') == 0); await b.close()
        b = await launch(p)
        q = await page(b, {'keepAwake': True, 'powerV': 1}); await q.click('#bnPlay'); await q.wait_for_timeout(1500)
        check('a choice made after the change still holds it', await q.evaluate('__asked') == 1); await q.click('#bnPlay'); await b.close()
        b = await launch(p)
        q = await page(b, {'keepAwake': True, 'powerV': 1, 'background': True}); await q.click('#bnPlay'); await q.wait_for_timeout(1500)
        check('locked-screen mode never holds the screen', await q.evaluate('__asked') == 0); await b.close()
        b = await launch(p)
        q = await page(b, None, has_touch=True, is_mobile=True); await q.tap('#bnPlay'); await q.wait_for_timeout(1500)
        check('phone default still holds the screen (live sound stops on lock)', await q.evaluate('__asked') == 1); await b.close()
    print('OVERNIGHT', 'FAILED ' + str(fails) if fails else 'PASSED'); sys.exit(1 if fails else 0)
asyncio.run(main())
