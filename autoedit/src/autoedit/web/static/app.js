function pollStatus(slug){
  async function tick(){
    try{
      const r = await fetch(`/p/${slug}/status.json`); if(!r.ok) return;
      const s = await r.json();
      for(const [stage, st] of Object.entries(s.stages)){
        const el = document.getElementById(`st-${stage}`); if(el){ el.textContent = st; el.className = `st ${st}`; }
        const bar = document.getElementById(`bar-${stage}`); const msg = document.getElementById(`msg-${stage}`);
        const pr = s.progress[stage];
        if(bar){ bar.style.width = (pr && st === 'running' ? pr.frac*100 : (st==='done'?100:0)) + '%'; }
        if(msg){ msg.textContent = (pr && st === 'running') ? pr.msg : ''; }
      }
    }catch(e){}
  }
  tick(); setInterval(tick, 3000);
}
function timelineSeek(){
  const tl = document.getElementById('timeline'); const v = document.getElementById('preview'); if(!tl || !v) return;
  tl.querySelectorAll('.mk').forEach(m => m.addEventListener('click', () => { v.currentTime = parseFloat(m.dataset.t); v.play(); }));
  v.addEventListener('timeupdate', () => {
    let cur = tl.querySelector('.cursor'); if(!cur){ cur = document.createElement('div'); cur.className='cursor'; cur.style.cssText='position:absolute;top:0;width:2px;height:28px;background:#fff;pointer-events:none'; tl.appendChild(cur); }
    const dur = parseFloat(tl.dataset.dur) || v.duration || 1; cur.style.left = (v.currentTime/dur*100) + '%';
  });
}
