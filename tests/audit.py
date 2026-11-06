OPEN_ALL="document.addEventListener('DOMContentLoaded',()=>document.querySelectorAll('details').forEach(d=>d.open=true))"
import asyncio,sys
from playwright.async_api import async_playwright
U=sys.argv[2] if len(sys.argv)>2 else 'https://alot-indol.vercel.app/?v=audit'  # pass a local URL to test before publishing
EXE=sys.argv[1]; R=[]
def rec(b,name,ok,detail=''): R.append(ok); print(('PASS' if ok else 'FAIL'),b.ljust(8),name.ljust(36),str(detail)[:88])
INIT="window.__a=[];const o=HTMLMediaElement.prototype.play;HTMLMediaElement.prototype.play=function(){if(!__a.includes(this))__a.push(this);return o.apply(this,arguments)};window.__w=[];if(window.WakeLock){const r=WakeLock.prototype.request;WakeLock.prototype.request=function(t){__w.push('req');return r.call(this,t).then(l=>{__w.push('granted');return l}).catch(e=>{__w.push('refused');throw e})}}"
CANVAS="(()=>{const c=document.getElementById('bnCanvas'),g=c.getContext('2d'),d=g.getImageData(0,0,c.width,c.height).data;let s=0;for(let i=0;i<d.length;i+=397)s=(s*31+d[i])%1000003;return s})()"
async def run(p,b_name):
    if b_name=='chromium':
        b=await p.chromium.launch(executable_path=EXE,args=['--autoplay-policy=no-user-gesture-required']); c=await b.new_context(viewport={'width':1280,'height':860})
    else:
        b=await p.webkit.launch(); c=await b.new_context(**p.devices['iPhone 14'])
    q=await c.new_page(); errs=[]; q.on('pageerror',lambda x:errs.append(str(x))); q.on('console',lambda m:errs.append(m.text) if m.type=='error' else None); await q.add_init_script(INIT)
    await q.add_init_script(OPEN_ALL); await q.goto(U); await q.wait_for_timeout(700)
    A=lambda n:q.evaluate("n=>document.documentElement.getAttribute(n)",n)
    cs=lambda sel,prop:q.evaluate("([s,p])=>getComputedStyle(document.querySelector(s))[p]",[sel,prop])
    async def opn(): await q.click('#gear'); await q.wait_for_timeout(220)
    async def cls(): await q.keyboard.press('Escape'); await q.wait_for_timeout(180)
    async def pick(k,v): await q.locator(f'[data-set="{k}:{v}"]').click(); await q.wait_for_timeout(180)
    rec(b_name,'gear visible',await q.locator('#gear').is_visible()); rec(b_name,'language toggle visible',await q.locator('.lang-toggle').is_visible())
    rec(b_name,'default Spanish',await q.evaluate('document.documentElement.lang')=='es' and await q.inner_text('#layerNoiseName')=='Ruido')
    await q.click('.lang-toggle button:has-text("EN")'); await q.wait_for_timeout(120); en=await q.inner_text('#layerNoiseName'); t=await q.title()
    await q.click('.lang-toggle button:has-text("ES")'); await q.wait_for_timeout(120); rec(b_name,'EN then ES switches text and title',en=='Noise' and 'alot' in t and await q.inner_text('#layerNoiseName')=='Ruido',en+' | '+t)
    await opn(); rec(b_name,'panel opens',await q.locator('.sheet').is_visible()); await q.click('#settingsClose'); await q.wait_for_timeout(120); rec(b_name,'close button closes',await q.locator('#settings').is_hidden())
    await opn(); await cls(); rec(b_name,'Esc closes',await q.locator('#settings').is_hidden()); await opn()
    await q.mouse.click(4,300) if b_name=='chromium' else None
    if b_name=='chromium': await q.wait_for_timeout(120); rec(b_name,'click outside closes',await q.locator('#settings').is_hidden()); await opn()
    # background
    await cls(); hashes={}
    for bg in ['threads','stars','mist','ripples','fireflies','constellation','aurora','still']:
        await opn(); await pick('bg',bg); await cls(); await q.wait_for_timeout(450); h1=await q.evaluate(CANVAS); await q.wait_for_timeout(500); h2=await q.evaluate(CANVAS); hashes[bg]=(h1,h2)
    rec(b_name,'7 moving backgrounds move',all(hashes[k][0]!=hashes[k][1] for k in ['threads','stars','mist','ripples','fireflies','constellation','aurora']))
    rec(b_name,'7 backgrounds look different',len({hashes[k][1] for k in ['threads','stars','mist','ripples','fireflies','constellation','aurora']})==7)
    rec(b_name,'Still background does not move',hashes['still'][0]==hashes['still'][1])
    await opn(); await pick('bg','threads')
    await q.evaluate("(()=>{const v=document.getElementById('setBgLevel');v.value=30;v.dispatchEvent(new Event('input',{bubbles:true}))})()"); await q.wait_for_timeout(120); rec(b_name,'background brightness',abs(float(await cs('#bnCanvas','opacity'))-.3)<.01,await cs('#bnCanvas','opacity'))
    await q.evaluate("(()=>{const v=document.getElementById('setBgLevel');v.value=100;v.dispatchEvent(new Event('input',{bubbles:true}))})()")
    # accent
    colors=set()
    for a in ['rose','sage','sky','lilac','amber']: await pick('accent',a); colors.add(await cs('.brand-name','color'))
    rec(b_name,'5 accent colors each differ',len(colors)==5,len(colors))
    # sizes independent
    fs=lambda:cs('.bn-label','fontSize'); sl=lambda:cs('#bn-tone','height'); ch=lambda:cs('#bnPresets button','minHeight'); pl=lambda:cs('.bn-play','width')
    f0,s0,c0,p0=await fs(),await sl(),await ch(),await pl()
    await pick('textSize','s'); fss=await fs(); await pick('textSize','xl'); fx=await fs(); rec(b_name,'text size s/xl; sliders+buttons same',float(fss[:-2])<float(f0[:-2])<float(fx[:-2]) and await sl()==s0 and await ch()==c0,f'{fss} {f0} {fx}'); await pick('textSize','m')
    await pick('sliderSize','s'); ss=await sl(); await pick('sliderSize','xl'); sx=await sl(); rec(b_name,'slider size s/xl; text+buttons same',float(ss[:-2])<float(s0[:-2])<float(sx[:-2]) and await fs()==f0 and await ch()==c0,f'{ss} {s0} {sx}'); await pick('sliderSize','m')
    await pick('controlSize','s'); cs1=await ch(); await pick('controlSize','l'); cl=await ch(); pb=await pl(); rec(b_name,'button size s/l; text+sliders same',float(cs1[:-2])<float(c0[:-2])<float(cl[:-2]) and float(pb[:-2])>float(p0[:-2]) and await fs()==f0 and await sl()==s0,f'{cs1} {c0} {cl} play {pb}'); await pick('controlSize','m')
    g0=await cs('main','rowGap'); await pick('spacing','airy'); gx=await cs('main','rowGap'); await pick('spacing','tight'); gt=await cs('main','rowGap'); rec(b_name,'spacing tight/airy',float(gt[:-2])<float(g0[:-2])<float(gx[:-2]),f'{gt} {g0} {gx}'); await pick('spacing','normal')
    b0=await cs('.layers','backgroundColor'); await pick('panels','solid'); bs=await cs('.layers','backgroundColor'); await pick('panels','clear'); bc=await cs('.layers','backgroundColor'); rec(b_name,'panels clear/glass/solid differ',len({b0,bs,bc})==3,f'{bc} | {bs}'); await pick('panels','glass')
    # calm
    await q.click('.switch:has(#setCalm)'); await q.wait_for_timeout(150); await cls(); h1=await q.evaluate(CANVAS); await q.wait_for_timeout(500); h2=await q.evaluate(CANVAS); rec(b_name,'Less motion stops background',h1==h2 and await A('data-calm')=='true'); await opn(); await q.click('.switch:has(#setCalm)'); await q.wait_for_timeout(120); await cls()
    # persistence
    await opn(); await pick('accent','sky'); await pick('textSize','l'); await q.reload(); await q.wait_for_timeout(500); rec(b_name,'settings survive reload',[await A('data-accent'),await A('data-text')]==['sky','l'])
    await opn(); await q.click('#settingsReset'); await q.wait_for_timeout(150); rec(b_name,'Reset restores defaults, keeps language',[await A('data-accent'),await A('data-text')]==['amber','m'] and await q.evaluate('document.documentElement.lang')=='es'); await cls()
    # keep awake
    if b_name=='chromium': await opn(); await q.click('.switch:has(#setKeep)'); await q.wait_for_timeout(100); await cls()  # computers default to off; test with it on
    await q.click('#bnPlay'); await q.wait_for_timeout(500); w=await q.evaluate('__w'); await q.click('#bnPlay'); await q.wait_for_timeout(120)
    rec(b_name,'Keep screen on requests it when playing','req' in w or await q.evaluate("!('wakeLock' in navigator)"),w)
    await q.evaluate('__w.length=0'); await opn(); await q.click('.switch:has(#setKeep)'); await q.wait_for_timeout(100); await cls(); await q.wait_for_timeout(100); await q.evaluate('__w.length=0'); await q.click('#bnPlay'); await q.wait_for_timeout(350); rec(b_name,'Keep screen off makes no request',(await q.evaluate('__w'))==[]); await q.click('#bnPlay'); await opn(); await q.click('.switch:has(#setKeep)'); await cls()
    # locked mode
    await opn(); await q.click('.switch:has(#setBackground)'); await cls(); await q.click('#bnPlay'); await q.wait_for_timeout(7000); st=await q.evaluate("__a.map(a=>({p:a.paused,d:Math.round(a.duration||0),t:Math.round(a.currentTime)}))"); rec(b_name,'Locked-screen mode plays a recording',any((not x['p']) and x['d']==3600 for x in st),st); await q.click('#bnPlay'); await q.wait_for_timeout(120); rec(b_name,'Locked-screen mode stops',all(x['p'] for x in await q.evaluate("__a.map(a=>({p:a.paused}))"))); await opn(); await q.click('.switch:has(#setBackground)'); await cls()
    rec(b_name,'no page errors',errs==[],errs[:2]); await b.close()
    # messages in clean sessions
    async def session():
        if b_name=='chromium':
            bb=await p.chromium.launch(executable_path=EXE); cc=await bb.new_context(viewport={'width':1280,'height':860})
        else:
            bb=await p.webkit.launch(); cc=await bb.new_context(**p.devices['iPhone 14'])
        qq=await cc.new_page(); await qq.add_init_script(OPEN_ALL); await qq.goto(U); await qq.wait_for_timeout(350); return bb,qq
async def main():
    async with async_playwright() as p:
        for n in ['chromium','webkit']: await run(p,n)
    print('TOTAL',sum(R),'of',len(R),'passed')
asyncio.run(main())
