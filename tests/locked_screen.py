import asyncio,time
from playwright.async_api import async_playwright
U='file:///Users/blossom/Documents/_bench-src/alot/index.html?lang=en'
INIT="window.__els=new Set();const op=HTMLMediaElement.prototype.play;HTMLMediaElement.prototype.play=function(){__els.add(this);return op.apply(this,arguments)};"
S="[...__els].map(a=>({t:+a.currentTime.toFixed(2),paused:a.paused,loop:a.loop,dur:+(a.duration||0).toFixed(0),err:a.error&&a.error.code}))"
fails=[]
def check(n,ok,d=''):
    print('PASS' if ok else 'FAIL',n,str(d)[:200],flush=True)
    if not ok: fails.append(n)
async def main():
    async with async_playwright() as p:
        for name in ['webkit','chromium']:
            b=await (p.webkit.launch() if name=='webkit' else p.chromium.launch(channel='chrome',headless=True,args=['--autoplay-policy=no-user-gesture-required','--mute-audio']))
            q=await (await b.new_context()).new_page(); e=[]; q.on('pageerror',lambda x:e.append(str(x))); await q.add_init_script(INIT); await q.goto(U); await q.wait_for_timeout(500)
            await q.evaluate("(()=>{const e=document.getElementById('setBackground');e.checked=true;e.dispatchEvent(new Event('change',{bubbles:true}))})()")
            await q.evaluate("window.__ended=0;document.addEventListener('ended',()=>__ended++,true)")
            await q.click('#noiseBtn'); await q.wait_for_function("[...__els].some(a=>a.duration>100)",timeout=90000); await q.wait_for_timeout(300)
            check(name+' placeholder does not restart while recording is made',await q.evaluate('__ended')<=1,await q.evaluate('__ended'))
            await q.evaluate("window.__ev=[];const a=[...__els][0];['waiting','stalled','pause','ended','seeking','error'].forEach(k=>a.addEventListener(k,()=>__ev.push(k)))")
            s0=(await q.evaluate(S))[0]; w0=time.time(); await q.wait_for_timeout(85000); s1=await q.evaluate(S); w=time.time()-w0
            check(name+' 85 s unattended through the first real join, one player',len(s1)==1 and not s1[0]['paused'] and abs((s1[0]['t']-s0['t'])-w)<1.5 and s1[0]['t']>75,(s0['t'],s1[0]['t'],round(w,1),await q.evaluate('__ev')))
            check(name+' no stall events',await q.evaluate('__ev')==[])
            await q.evaluate("[...__els][0].dispatchEvent(new Event('error'))"); await q.wait_for_timeout(3000); s2=await q.evaluate(S)
            check(name+' error falls back to short file, keeps playing',s2[0]['dur']==150 and not s2[0]['paused'] and s2[0]['loop'],s2)
            await q.evaluate("(()=>{const a=[...__els][0];a.currentTime=a.duration-1})()"); await q.wait_for_timeout(3000); s3=await q.evaluate(S)
            check(name+' short file restarts',not s3[0]['paused'] and s3[0]['t']<5,s3)
            await q.click('#noiseBtn'); await q.wait_for_timeout(400); check(name+' stops',(await q.evaluate(S))[0]['paused'])
            check(name+' no page errors',e==[],e); await b.close()
    print('EXTRA','FAILED '+str(fails) if fails else 'PASSED')
asyncio.run(main())
