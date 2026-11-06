import asyncio,sys
from playwright.async_api import async_playwright
U='file:///Users/blossom/Documents/_bench-src/alot/index.html?lang=en'
INIT=r"""
window.__els=new Set();const op=HTMLMediaElement.prototype.play;HTMLMediaElement.prototype.play=function(){__els.add(this);return op.apply(this,arguments)};
window.__big=[];const cu=URL.createObjectURL;URL.createObjectURL=function(b){if(b&&b.type==='audio/wav'&&b.size>1e7)__big.push(b);return cu.call(URL,b)};
window.__seam=async()=>{const b=__big.at(-1),F=75*44100;const rd=async(f,n)=>new Int16Array(await b.slice(44+f*4,44+(f+n)*4).arrayBuffer());
 const out={mb:Math.round(b.size/1e6),hours:(b.size-44)/4/44100/3600};
 const body=await rd(F,F);let mx=0,sum=0,pk=0,cl=0;for(let c=0;c<2;c++)for(let i=2+c;i<body.length;i+=2){const k=Math.abs(body[i]-body[i-2]);sum+=k;if(k>mx)mx=k;const a=Math.abs(body[i]);if(a>pk)pk=a;if(a>=32767)cl++}
 out.maxStep=mx;out.avgStep=+(sum/body.length).toFixed(1);out.peak=+(pk/32767).toFixed(2);out.clipped=cl;
 const joins=[];for(const f of [F,F*2,F*24,F*47]){const j=await rd(f-1,2);joins.push(Math.abs(j[2]-j[0]))}out.joinSteps=joins;
 const a=await rd(F,2000),c=await rd(F*2,2000);let same=true;for(let i=0;i<a.length;i++)if(a[i]!==c[i])same=false;out.repeatsExact=same;
 const st=await rd(0,1),en=await rd(F*48-1,1);out.fileEnds=[st[0],en[0]];return out};
"""
async def main():
    async with async_playwright() as p:
        for name in ['webkit','chromium']:
            if name=='webkit':
                b=await p.webkit.launch(); c=await b.new_context(**p.devices['iPhone 14'])
            else:
                b=await p.chromium.launch(channel='chrome',headless=True,args=['--autoplay-policy=no-user-gesture-required','--mute-audio']); c=await b.new_context()
            q=await c.new_page(); e=[]; q.on('pageerror',lambda x:e.append(str(x))); await q.add_init_script(INIT); await q.goto(U); await q.wait_for_timeout(500)
            await q.evaluate("(()=>{const e=document.getElementById('setBackground');e.checked=true;e.dispatchEvent(new Event('change',{bubbles:true}))})()")
            await q.evaluate("(()=>{const e=document.getElementById('bnVolume');e.value=5;e.dispatchEvent(new Event('input',{bubbles:true}))})()")
            await q.click('#noiseBtn'); await q.wait_for_function('__big.length>0',timeout=90000); await q.wait_for_timeout(1500)
            print(name,'file',await q.evaluate('__seam()'))
            S="[...__els].map(a=>({t:+a.currentTime.toFixed(2),paused:a.paused,loop:a.loop,dur:+(a.duration||0).toFixed(0),err:a.error&&a.error.code,ready:a.readyState}))"
            print(' players',await q.evaluate(S))
            # cross the first two joins by seeking near one, then watch it run through
            await q.evaluate("[...__els][0].currentTime=73")
            await q.evaluate("window.__ev=[];const a=[...__els][0];['waiting','stalled','pause','ended','seeking','error'].forEach(k=>a.addEventListener(k,()=>__ev.push(k)))")
            await q.wait_for_timeout(5000); print(' across join',await q.evaluate(S),'events',await q.evaluate('__ev'))
            # file end restarts
            await q.evaluate("(()=>{const a=[...__els][0];a.currentTime=a.duration-1.5})()"); await q.wait_for_timeout(3500); print(' past file end',await q.evaluate(S),'events',await q.evaluate('__ev'))
            # change a sound: one player still, new recording loaded
            n=await q.evaluate('__big.length'); await q.click('#layerNoiseBtn'); await q.locator('#bnPresets button').nth(4).click(); await q.click('#layerNoiseBtn'); await q.wait_for_function(f'__big.length>{n}',timeout=90000); await q.wait_for_timeout(4500)
            print(' after change',await q.evaluate(S),'events',await q.evaluate('__ev'))
            await q.click('#noiseBtn'); await q.wait_for_timeout(500); print(' stopped',await q.evaluate(S)); await q.click('#noiseBtn'); await q.wait_for_timeout(2500); print(' restarted',await q.evaluate(S))
            print(' errors',e); await b.close()
asyncio.run(main())
