"""Real Chromium interaction against the compiled C++ host. No external services."""
import argparse
import base64
import json
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.request
from websockets.sync.client import connect

ROOT=Path(__file__).resolve().parents[2]

def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1',0))
        return s.getsockname()[1]

class Browser:
    def __init__(self,ws): self.ws=ws; self.index=0
    def call(self,method,params=None):
        self.index+=1
        self.ws.send(json.dumps({'id':self.index,'method':method,'params':params or {}}))
        while True:
            msg=json.loads(self.ws.recv())
            if msg.get('id')==self.index:
                if 'error' in msg: raise RuntimeError(msg['error'])
                return msg.get('result',{})
    def evaluate(self,code):
        result=self.call('Runtime.evaluate',{'expression':code,'returnByValue':True,'awaitPromise':True})
        if 'exceptionDetails' in result: raise RuntimeError(result['exceptionDetails'])
        return result.get('result',{}).get('value')

def run(browser,binary):
    with tempfile.TemporaryDirectory(prefix='cda-v3-browser-') as tmp:
        api,debug=free_port(),free_port()
        backend=subprocess.Popen([str(binary),'--database',str(Path(tmp)/'identity.sqlite'),'--port',str(api),'--docs',str(ROOT/'docs')],stdout=subprocess.DEVNULL)
        chrome=None
        try:
            for _ in range(100):
                try:
                    urllib.request.urlopen(f'http://127.0.0.1:{api}/api/v1/health',timeout=1).close();break
                except OSError: time.sleep(.05)
            chrome=subprocess.Popen([browser,'--headless','--no-sandbox','--disable-dev-shm-usage','--disable-gpu','--disable-background-networking','--no-first-run','--remote-allow-origins=*',f'--remote-debugging-port={debug}','--user-data-dir='+tmp+'/chrome','--window-size=1500,1000',f'http://127.0.0.1:{api}/architecture/interactive_architecture.html'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            for _ in range(100):
                try:
                    tabs=json.load(urllib.request.urlopen(f'http://127.0.0.1:{debug}/json',timeout=1))
                    tab=next(t for t in tabs if t.get('type')=='page');break
                except (OSError,StopIteration):time.sleep(.05)
            else:raise RuntimeError('Chromium startup failed')
            with connect(tab['webSocketDebuggerUrl'],open_timeout=5) as ws:
                c=Browser(ws)
                for _ in range(100):
                    if c.evaluate('document.querySelectorAll(".node").length===32'):break
                    time.sleep(.03)
                checks={}
                def check(name,value):
                    if not value: raise AssertionError(name)
                    checks[name]=value
                check('32_actual_nodes',c.evaluate('document.querySelectorAll(".node").length===32'))
                check('24_sections',c.evaluate('''(()=>{const s=document.getElementById('section');for(const o of s.options){s.value=o.value;s.dispatchEvent(new Event('change'));if(!document.querySelector('.node'))return false;}s.value='overview';s.dispatchEvent(new Event('change'));return s.options.length===24;})()'''))
                check('search',c.evaluate('''(()=>{const s=document.getElementById('search');s.value='SQLite / PostgreSQL';s.dispatchEvent(new Event('input'));const ok=document.querySelectorAll('.node').length===1;s.value='';s.dispatchEvent(new Event('input'));return ok;})()'''))
                check('collapse_expand',c.evaluate('''(()=>{const b=document.querySelector('[data-group=Clients]');b.click();const ok=document.querySelectorAll('.node').length===28;document.getElementById('expand').click();return ok&&document.querySelectorAll('.node').length===32;})()'''))
                check('component_inspector',c.evaluate('''(()=>{document.querySelector('[data-node=safety]').dispatchEvent(new Event('click',{bubbles:true}));return document.getElementById('inspector').textContent.includes('CUSTOMER')&&document.getElementById('inspector').textContent.includes('source');})()'''))
                check('edge_details',c.evaluate('''(()=>{document.querySelector('[data-edge]').dispatchEvent(new Event('click',{bubbles:true}));return document.getElementById('inspector').textContent.includes('Direction:');})()'''))
                check('offline_filter',c.evaluate('''(()=>{const s=document.getElementById('path');s.value='offline';s.dispatchEvent(new Event('change'));const ok=!document.querySelector('.edge.online');s.value='all';s.dispatchEvent(new Event('change'));return ok;})()'''))
                check('zoom_buttons',c.evaluate('''(()=>{const g=document.getElementById('graph'),s=+g.dataset.scale;document.getElementById('zoom-in').click();return +g.dataset.scale>s;})()'''))
                check('theme',c.evaluate('''(()=>{document.getElementById('theme').click();return document.body.classList.contains('light');})()'''))
                box=c.evaluate('''(()=>{const r=document.getElementById('graph').getBoundingClientRect();return {x:r.left+5,y:r.top+5};})()''')
                before=c.evaluate('document.getElementById("scene").getAttribute("transform")')
                c.call('Input.dispatchMouseEvent',dict(type='mousePressed',button='left',buttons=1,clickCount=1,**box))
                c.call('Input.dispatchMouseEvent',dict(type='mouseMoved',buttons=1,x=box['x']+50,y=box['y']+30))
                c.call('Input.dispatchMouseEvent',dict(type='mouseReleased',button='left',buttons=0,clickCount=1,x=box['x']+50,y=box['y']+30))
                check('real_pointer_pan',c.evaluate('document.getElementById("scene").getAttribute("transform")')!=before)
                before=c.evaluate('document.getElementById("graph").dataset.scale')
                c.call('Input.dispatchMouseEvent',dict(type='mouseWheel',deltaX=0,deltaY=-100,**box));time.sleep(.1)
                check('real_wheel_zoom',c.evaluate('document.getElementById("graph").dataset.scale')!=before)
                c.evaluate("document.getElementById('refresh').click()")
                for _ in range(100):
                    if 'sqlite_open' in c.evaluate("document.getElementById('metrics').textContent"):break
                    time.sleep(.03)
                check('real_backend_observations',c.evaluate("document.getElementById('metrics').textContent.includes('sqlite_open')&&document.getElementById('metrics').textContent.includes('UNKNOWN')"))
                (ROOT/'docs/testing/architecture-dashboard.png').write_bytes(base64.b64decode(c.call('Page.captureScreenshot',{'format':'png'})['data']))
                c.call('Emulation.setDeviceMetricsOverride',{'width':390,'height':844,'deviceScaleFactor':1,'mobile':True})
                check('responsive_layout',c.evaluate('document.documentElement.scrollWidth<=400'))
                navigation=c.call('Page.navigate',{'url':(ROOT/'docs/architecture/interactive_architecture.html').as_uri()})
                if navigation.get('errorText')=='net::ERR_BLOCKED_BY_ADMINISTRATOR':
                    checks['offline_file_dashboard']={'status':'BLOCKED','reason':'Managed Chromium policy blocks file:// navigation; policy was not bypassed. Local HTTP bundled dashboard passed.'}
                else:
                    for _ in range(100):
                        if c.evaluate('location.protocol==="file:"&&document.querySelectorAll(".node").length===32'):break
                        time.sleep(.03)
                    check('offline_file_dashboard',c.evaluate('location.protocol==="file:"&&document.querySelectorAll(".node").length===32&&document.getElementById("metrics").textContent.includes("UNAVAILABLE")'))
                print(json.dumps({'status':'PASS_WITH_BLOCKED' if isinstance(checks.get('offline_file_dashboard'),dict) else 'PASS','checks':checks},indent=2))
        finally:
            if chrome:chrome.terminate();chrome.wait(timeout=10)
            backend.terminate();backend.wait(timeout=10)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--browser',default=shutil.which('chromium'));parser.add_argument('--binary',type=Path,default=ROOT/'build/dev/cda_backend');args=parser.parse_args()
    if not args.browser:parser.error('Chromium required')
    run(args.browser,args.binary.resolve())
