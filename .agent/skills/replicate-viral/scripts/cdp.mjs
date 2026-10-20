// Minimal raw CDP client over global WebSocket (Node 22+). Avoids playwright browser-level calls (Chrome 149 quirk).
export class CDP {
  constructor(wsUrl){ this.wsUrl=wsUrl; this.id=0; this.pending=new Map(); this.handlers=new Map(); }
  connect(){ return new Promise((res,rej)=>{
    this.ws=new WebSocket(this.wsUrl);
    this.ws.addEventListener('open',()=>res());
    this.ws.addEventListener('error',e=>rej(new Error('ws error '+(e.message||''))));
    this.ws.addEventListener('message',ev=>{
      const m=JSON.parse(ev.data);
      if(m.id&&this.pending.has(m.id)){ const {res,rej}=this.pending.get(m.id); this.pending.delete(m.id);
        if(m.error) rej(new Error(m.method+' '+JSON.stringify(m.error))); else res(m.result); }
      else if(m.method){ const h=this.handlers.get(m.method); if(h) h(m.params); }
    });
  });}
  send(method,params={}){ const id=++this.id; return new Promise((res,rej)=>{ this.pending.set(id,{res,rej});
    this.ws.send(JSON.stringify({id,method,params})); setTimeout(()=>{ if(this.pending.has(id)){ this.pending.delete(id); rej(new Error('timeout '+method)); } },60000); });}
  on(method,fn){ this.handlers.set(method,fn); }
  async evaluate(expr){ const r=await this.send('Runtime.evaluate',{expression:expr,returnByValue:true,awaitPromise:true}); 
    if(r.exceptionDetails) throw new Error('eval: '+JSON.stringify(r.exceptionDetails.exception?.description||r.exceptionDetails.text)); return r.result.value; }
  async screenshot(path,fmt='png'){ const r=await this.send('Page.captureScreenshot',{format:fmt}); 
    const fs=await import('fs'); fs.writeFileSync(path,Buffer.from(r.data,'base64')); return path; }
  close(){ try{this.ws.close();}catch{} }
}
export async function pageWs(filter){
  const res=await fetch('http://localhost:9222/json'); const tabs=await res.json();
  const t=tabs.find(filter); if(!t) throw new Error('no matching tab'); return {ws:t.webSocketDebuggerUrl, tab:t};
}
