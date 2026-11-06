# Measures processor time the browser spends in each playback situation, so battery work is measured, not guessed.
# Processor time is a stand-in for battery use; it does not include the screen itself.
# Usage: ~/ComfyUI/venv/bin/python power.py URL [seconds]
import asyncio, json, re, subprocess, sys
from playwright.async_api import async_playwright
U = sys.argv[1]; SECS = int(sys.argv[2]) if len(sys.argv) > 2 else 20
def tree_cpu(root):
    rows = subprocess.run(['ps', '-axo', 'pid=,ppid=,time='], capture_output=True, text=True).stdout.splitlines()
    kids = {}; times = {}
    for r in rows:
        p, pp, t = r.split()
        m = re.match(r'(?:(\d+):)?(\d+):(\d+(?:\.\d+)?)', t)
        times[int(p)] = int(m.group(1) or 0) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
        kids.setdefault(int(pp), []).append(int(p))
    total, stack = 0, [root]
    while stack:
        n = stack.pop(); total += times.get(n, 0); stack += kids.get(n, [])
    return total
def browser_pid():
    out = subprocess.run(['pgrep', '-f', 'remote-debugging-pipe'], capture_output=True, text=True).stdout.split()
    return min(int(x) for x in out)
async def measure(q, pid, label):
    await q.wait_for_timeout(4000)
    a = tree_cpu(pid); await q.wait_for_timeout(SECS * 1000); b = tree_cpu(pid)
    pct = (b - a) / SECS * 100
    wake = await q.evaluate("window.__wake||0")
    print(f'{label:48s} {pct:6.1f}% of one core   screen held awake: {"yes" if wake else "no"}', flush=True)
    return pct
INIT = """window.__wake=0;if(navigator.wakeLock){const r=navigator.wakeLock.request.bind(navigator.wakeLock);navigator.wakeLock.request=function(t){return r(t).then(l=>{window.__wake=1;l.addEventListener('release',()=>{window.__wake=0});return l})}}"""
async def scenario(p, label, settings, press=True, hide=False, idle=0):
    b = await p.chromium.launch(channel='chrome', headless=True, args=['--autoplay-policy=no-user-gesture-required', '--mute-audio'])
    pid = browser_pid()
    c = await b.new_context(viewport={'width': 1280, 'height': 800}, device_scale_factor=2)
    q = await c.new_page(); await q.add_init_script(INIT)
    await q.add_init_script("try{const k='alot.settings.v1';localStorage.setItem(k,JSON.stringify(Object.assign(JSON.parse(localStorage.getItem(k)||'{}'),%s)))}catch(e){}" % json.dumps(settings))
    await q.goto(U); await q.wait_for_timeout(1000)
    if press:
        await q.click('#bnPlay')
        if settings.get('background'):
            await q.wait_for_function("document.querySelector('#bnPlay').getAttribute('aria-pressed')==='true'")
            await q.wait_for_timeout(25000)
        else:
            await q.wait_for_timeout(9000)
    if idle: await q.wait_for_timeout(idle * 1000)
    if hide:
        q2 = await c.new_page(); await q2.goto('about:blank'); await q2.bring_to_front()
        r = await measure(q2, pid, label)
    else:
        r = await measure(q, pid, label)
    await b.close(); return r
async def main():
    async with async_playwright() as p:
        await scenario(p, 'stopped, animated background', {}, press=False)
        await scenario(p, 'playing, animated background (default)', {})
        await scenario(p, 'playing, default, nobody touching it for 65 s', {}, idle=65)
        await scenario(p, 'playing, still background', {'bg': 'still'})
        await scenario(p, 'playing, tab in the background', {}, hide=True)
        await scenario(p, 'locked-screen mode, animated background', {'background': True})
        await scenario(p, 'locked-screen mode, still background', {'background': True, 'bg': 'still'})
asyncio.run(main())
