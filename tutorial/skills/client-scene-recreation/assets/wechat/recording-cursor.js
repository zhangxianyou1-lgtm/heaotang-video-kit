// Visible pointer for tab-only capture; follows actual pointer events and never clicks controls.
(() => {
  if (!new URLSearchParams(location.search).has('record')) return;
  const style=document.createElement('style');
  style.textContent='.recording-pointer{position:fixed;left:0;top:0;z-index:2147483646;pointer-events:none;transform:translate(1700px,950px);transition:transform .32s ease-out;width:24px;height:30px;filter:drop-shadow(1px 2px 1px #0003)}.recording-pointer svg{width:24px;height:30px}.recording-click{position:fixed;z-index:2147483645;pointer-events:none;width:34px;height:34px;margin:-17px 0 0 -17px;border:2px solid #e4aa37;border-radius:50%;animation:recording-click .65s ease-out both}@keyframes recording-click{from{opacity:.7;transform:scale(.4)}to{opacity:0;transform:scale(1.7)}}body.portrait dialog{transform:scale(2.1);transform-origin:center}';
  document.head.append(style);
  const pointer=document.createElement('div');pointer.className='recording-pointer';pointer.setAttribute('aria-hidden','true');
  pointer.innerHTML='<svg viewBox="0 0 24 30"><path d="M2 2v23l6-6 4 9 4-2-4-9h9z" fill="white" stroke="#1d2922" stroke-width="1.5"/></svg>';
  document.body.append(pointer);
  document.addEventListener('pointermove',e=>{pointer.style.transform=`translate(${e.clientX}px,${e.clientY}px)`},{passive:true});
  document.addEventListener('pointerdown',e=>{const ring=document.createElement('i');ring.className='recording-click';ring.setAttribute('aria-hidden','true');ring.style.left=e.clientX+'px';ring.style.top=e.clientY+'px';document.body.append(ring);ring.addEventListener('animationend',()=>ring.remove(),{once:true})},{passive:true});
})();
