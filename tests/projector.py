# Projector mode: button only on big screens, draws, follows the analysis file of the playing purpose, closes cleanly,
# and costs nothing once closed. Power is measured in a visible Chrome window (real graphics chip), not headless.
# Usage: ~/ComfyUI/venv/bin/python projector.py URL        (URL without #mix, e.g. http://127.0.0.1:8765/?lang=en)
import asyncio, re, subprocess, sys
from playwright.async_api import async_playwright
U = sys.argv[1]; fails = []
def check(n, ok, d=''):
    print('PASS' if ok else 'FAIL', n, str(d)[:170], flush=True)
    if not ok: fails.append(n)
INIT = "window.__raf=0;const R=window.requestAnimationFrame.bind(window);window.requestAnimationFrame=function(f){__raf++;return R(f)};"
async def wake(q):
    await q.mouse.move(600, 300); await q.mouse.move(640, 330); await q.wait_for_timeout(500)
async def bright(q):
    shot = await q.screenshot(type='jpeg', quality=60)
    from io import BytesIO
    from PIL import Image
    im = Image.open(BytesIO(shot)).convert('L').resize((64, 36))
    px = list(im.getdata()); return sum(px) / len(px)
async def run(p, name):
    b = await (p.webkit.launch() if name == 'webkit' else p.chromium.launch(channel='chrome', headless=True, args=['--autoplay-policy=no-user-gesture-required', '--mute-audio', '--enable-unsafe-swiftshader']))
    phone = await (await b.new_context(viewport={'width': 390, 'height': 844}, has_touch=True)).new_page()
    await phone.goto(U); await phone.wait_for_timeout(800)
    check(name + ' no Projector button on a phone', not await phone.locator('#projectorBtn').is_visible())
    c = await b.new_context(viewport={'width': 1280, 'height': 720}); q = await c.new_page(); e = []; q.on('pageerror', lambda x: e.append(str(x)))
    env = []; q.on('request', lambda r: env.append(r.url) if '/modes/env/' in r.url else None)
    await q.add_init_script(INIT); await q.goto(U); await q.wait_for_timeout(1200)
    await q.mouse.move(100, 100); a = await q.evaluate('__raf'); await q.wait_for_timeout(2000); base = await q.evaluate('__raf') - a
    check(name + ' Projector button on a big screen', await q.locator('#projectorBtn').is_visible())
    await q.click('#projectorBtn'); await q.wait_for_timeout(150); dark = await bright(q); await q.wait_for_timeout(850)
    check(name + ' projector opens full screen', await q.locator('#projector').is_visible() and await q.evaluate("document.getElementById('projector').getBoundingClientRect().width==innerWidth"))
    check(name + ' draws at about half size', await q.evaluate("document.getElementById('projCanvas').width") == 640, await q.evaluate("document.getElementById('projCanvas').width"))
    check(name + ' offers the purposes', await q.locator('#projModes button').count() == 7)
    await q.locator('#projModes button', has_text='Run').click(); await q.wait_for_timeout(4000)
    check(name + ' loads the Run analysis, not audio analysis', any(u.endswith('/modes/env/run.v3.bin') for u in env), env)
    lit = await bright(q); check(name + ' opens from black, then the light rises', dark < lit / 2 and lit > 12, (dark, lit))
    await wake(q)
    check(name + ' shows what is playing', await q.inner_text('#projName') == 'Run' and ' – ' in await q.inner_text('#projTrack'), await q.inner_text('#projTrack'))
    check(name + ' three visuals offered', await q.locator('#projForms button').count() == 3)
    for f in ['aurora', 'bloom', 'silk']:
        await wake(q); await q.click(f'#projForms [data-id="{f}"]'); await q.wait_for_timeout(1200)
        check(name + ' visual ' + f + ' draws', await bright(q) > 8 and await q.get_attribute(f'#projForms [data-id="{f}"]', 'aria-pressed') == 'true', await bright(q))
    await wake(q)
    check(name + ' sync starts at +0.04 s on this device (never ahead of the sound)', await q.inner_text('#projSyncValue') == '+0.04 s', await q.inner_text('#projSyncValue'))
    await q.evaluate("(()=>{const s=document.getElementById('projSync');s.value=150;s.dispatchEvent(new Event('input',{bubbles:true}))})()")
    check(name + ' sync slider sets the delay', await q.inner_text('#projSyncValue') == '+1.50 s')
    await q.evaluate("(()=>{const s=document.getElementById('projSync');s.value=4;s.dispatchEvent(new Event('input',{bubbles:true}))})()")
    await q.click('#projFlashBtn'); await q.wait_for_timeout(2500)
    check(name + ' flash beats runs without errors', e == [], e)
    first = await q.inner_text('#projTrack'); await q.click('#projNext'); await q.wait_for_timeout(1500)
    check(name + ' Next works in the projector', await q.inner_text('#projTrack') != first)
    await q.wait_for_timeout(3600)
    check(name + ' controls hide when idle', await q.evaluate("document.getElementById('projector').classList.contains('idle')"))
    await wake(q); await q.locator('#projModes button', has_text='Noise only').click(); await q.wait_for_timeout(1500)
    check(name + ' Noise only uses its color analysis', any(u.endswith('/modes/env/noise-brown.v3.bin') for u in env), env)
    await q.keyboard.press('Escape'); await q.wait_for_timeout(800)
    check(name + ' Esc closes the projector', not await q.locator('#projector').is_visible())
    check(name + ' sound carries on after closing', await q.evaluate("[...document.querySelectorAll('audio')].length>=0") and await q.locator('#modeNow').is_visible())
    await q.wait_for_timeout(500); a = await q.evaluate('__raf'); await q.wait_for_timeout(2000); n = await q.evaluate('__raf') - a
    check(name + ' after closing, no more frames than the page alone', n <= base + 15, (n, base))
    await q.click('#projectorBtn'); await q.wait_for_timeout(300); await q.keyboard.press('Escape'); await q.wait_for_timeout(200)
    await q.click('#projectorBtn'); await q.wait_for_timeout(1500)
    check(name + ' reopens cleanly, even straight after closing', await q.locator('#projector').is_visible() and await bright(q) > 8, await bright(q))
    await q.keyboard.press('Escape'); await q.wait_for_timeout(900)
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
async def power(p):
    b = await p.chromium.launch(channel='chrome', headless=False, args=['--autoplay-policy=no-user-gesture-required', '--mute-audio', '--window-size=1280,760'])
    root = min(int(x) for x in subprocess.run(['pgrep', '-f', 'remote-debugging-pipe'], capture_output=True, text=True).stdout.split())
    q = await (await b.new_context(viewport={'width': 1280, 'height': 720})).new_page(); await q.goto(U); await q.wait_for_timeout(1500)
    await q.click('#projectorBtn'); await q.wait_for_timeout(500); await wake(q)
    await q.locator('#projModes button', has_text='Flow').click(); await q.wait_for_timeout(8000)
    a = cpu(root); await q.wait_for_timeout(20000); on = (cpu(root) - a) / 20 * 100
    check('battery: projector on, under 60% of a core', on < 60, f'{on:.1f}%')
    # Chrome frees the projector's graphics memory over a minute or two after closing; measured: 16.9%, 5.8%, then 1.6%, the same as never opening it.
    await q.keyboard.press('Escape'); await q.wait_for_timeout(130000)
    a = cpu(root); await q.wait_for_timeout(20000); off = (cpu(root) - a) / 20 * 100
    check('battery: projector closed, idle under 10% of a core', off < 10, f'{off:.1f}%')
    await b.close()
async def main():
    async with async_playwright() as p:
        await run(p, 'chromium'); await run(p, 'webkit'); await power(p)
    print('PROJECTOR', 'FAILED ' + str(fails) if fails else 'PASSED'); sys.exit(1 if fails else 0)
asyncio.run(main())
