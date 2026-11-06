import asyncio,sys
from playwright.async_api import async_playwright
U='file:///Users/blossom/Documents/_bench-src/alot/index.html?lang=en#studio'
H="window.__all=new Set();const o=HTMLMediaElement.prototype.play;HTMLMediaElement.prototype.play=function(){__all.add(this);return o.apply(this,arguments)};"
S="[...__all].filter(a=>a.duration>5).map(a=>({t:+a.currentTime.toFixed(1),p:a.paused}))"
fails=[]
def check(n,ok,d=''):
    print(('PASS' if ok else 'FAIL'),n,str(d)[:110]); 
    if not ok: fails.append(n)
async def run(p,name):
    if name=='chromium':
        b=await p.chromium.launch(executable_path=sys.argv[1],args=['--autoplay-policy=no-user-gesture-required']); c=await b.new_context(viewport={'width':1100,'height':900})
    else:
        b=await p.webkit.launch(); c=await b.new_context(**p.devices['iPhone 14'])
    q=await c.new_page(); e=[]; q.on('pageerror',lambda x:e.append(str(x))); await q.add_init_script(H); await q.goto(U); await q.wait_for_timeout(500)
    P='.take-btn.play'
    await q.set_input_files('#uploadMp3','long.wav'); await q.wait_for_selector('.take-item'); await q.wait_for_timeout(300); await q.locator(P).first.click()
    await q.wait_for_timeout(5000); await q.locator(P).first.click(); await q.wait_for_timeout(700); check(name+' stop before crossfade',all(x['p'] for x in await q.evaluate(S)) and 'Play' in await q.get_attribute(P,'aria-label'))
    await q.locator(P).first.click(); await q.wait_for_timeout(12000); st=await q.evaluate(S); check(name+' both overlap at crossfade',sum(1 for x in st if not x['p'])==2 and 'Stop' in await q.get_attribute(P,'aria-label'),st)
    await q.locator(P).first.click(); await q.wait_for_timeout(700); check(name+' stop during crossfade',all(x['p'] for x in await q.evaluate(S)) and 'Play' in await q.get_attribute(P,'aria-label'),await q.evaluate(S))
    await q.locator(P).first.click(); silent=0
    for i in range(62):
        await q.wait_for_timeout(500)
        if not any(not x['p'] for x in await q.evaluate(S)): silent+=1
    check(name+' 31 s of looping never silent',silent==0 and 'Stop' in await q.get_attribute(P,'aria-label'),silent); await q.locator(P).first.click(); await q.wait_for_timeout(500)
    await q.set_input_files('#uploadMp3','tone.wav'); await q.wait_for_function("document.querySelectorAll('#takesList .take-item').length==2"); await q.wait_for_timeout(300); await q.locator('#takesList .take-btn.del').first.click(); await q.wait_for_timeout(150); await q.locator(P).first.click(); both=0; silent=0
    for i in range(40):
        await q.wait_for_timeout(200); st=[x for x in await q.evaluate("[...__all].filter(a=>a.duration>2&&a.duration<4).map(a=>({p:a.paused}))") if not x['p']]; both+=len(st)==2; silent+=len(st)==0
    check(name+' short file overlaps, never silent',both>0 and silent==0,(both,silent)); await q.locator(P).first.click(); await q.wait_for_timeout(500); await q.locator('#takesList .take-btn.del').first.click(); await q.wait_for_timeout(100); await q.set_input_files('#uploadMp3','long.wav'); await q.wait_for_selector('.take-item'); await q.wait_for_timeout(300)
    await q.set_input_files('#uploadMp3','long2.wav'); await q.wait_for_function("document.querySelectorAll('#takesList .take-item').length==2"); await q.wait_for_timeout(300); await q.locator(P).first.click(); await q.wait_for_timeout(11500)
    now=await q.inner_text('.take-item.is-playing .take-name'); check(name+' list advances to next file',now=='long2.wav',now); await q.locator('.take-item.is-playing '+P).click(); await q.wait_for_timeout(500)
    check(name+' no page errors',e==[],e); check(name+' no sideways scroll',await q.evaluate('document.documentElement.scrollWidth-innerWidth')==0); await b.close()
async def main():
    async with async_playwright() as p:
        await run(p,'chromium'); await run(p,'webkit')
    print('GATE','FAILED '+str(fails) if fails else 'PASSED')
asyncio.run(main())
