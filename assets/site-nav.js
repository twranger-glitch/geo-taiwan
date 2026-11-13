/* 海佃地圖 site navigation — one list for every page (see DESIGN.md › Navigation).
   Pages include: <nav class="gnav" id="gnav" aria-label="網站導覽"></nav> as the first element of <body>,
   plus this script. To add a page, add it to SITE below; nothing else changes. */
(()=>{
const BASE='https://geo.twranger.com/';
const SITE=[
 {u:'第一單元',t:'臺灣的地理位置',pages:[{f:'unit1.html',n:'世界上有爭議的領土',d:'轉動地球，看看哪些島嶼不只一個國家說是自己的'}]},
 {u:'第二單元',t:'臺灣的自然環境與生活',pages:[
   {f:'index.html',n:'臺灣的自然環境與生活',d:'板塊、地形、颱風、季風、雨量、氣溫'},
   {f:'gnss.html',n:'臺灣每年都在移動',d:'300 多個 GPS 測站 15 年的真實紀錄'},
   {f:'sealevel.html',n:'如果海平面上升了',d:'拉動海平面，看看哪些地方會淹水'},
   {f:'energy.html',n:'臺灣現在用什麼發電？',d:'台電即時資料和發電廠地圖'}]},
 {u:'第三單元',t:'尋根探源話臺灣',pages:[
   {f:'unit3.html',n:'尋根探源話臺灣',d:'史前文化、考古遺址、原住民族'},
   {f:'prehistory.html',n:'史前生存大冒險',d:'走進 3D 的史前村落，完成生存任務'}]},
 {u:'第四單元',t:'大航海時代的臺灣',pages:[{f:'unit4.html',n:'大航海時代的臺灣',d:'荷蘭、西班牙、鄭氏，臺江內海的變化'}]},
 {u:'主題探究',t:'守護臺灣最美的風景',pages:[{f:'explore.html',n:'守護臺灣最美的風景',d:'選景點、查資料、做出你的推薦表'}]}];
const here=document.documentElement.dataset.page||location.pathname.split('/').pop()||'index.html';
const cur=SITE.findIndex(g=>g.pages.some(p=>p.f===here));const curP=cur>=0?SITE[cur].pages.find(p=>p.f===here):null;
const I={chev:'<svg class="gn-i" viewBox="0 0 16 16" aria-hidden="true"><path d="M4 6l4 4 4-4" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>',
 menu:'<svg class="gn-i" viewBox="0 0 20 20" aria-hidden="true"><path d="M3 5.5h14M3 10h14M3 14.5h14" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/></svg>',
 x:'<svg class="gn-i" viewBox="0 0 20 20" aria-hidden="true"><path d="M5 5l10 10M15 5L5 15" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/></svg>',
 here:'<svg class="gn-i" viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="4" fill="currentColor"/></svg>',
 mark:'<svg viewBox="0 0 32 32" aria-hidden="true"><rect width="32" height="32" rx="8" fill="#10313b"/><path d="M19.5 5.5c-2.6 1.4-4.8 4.6-6.3 8.4-1.2 3-2.9 6.4-5.7 9.6 3.2.4 6.2-.6 8.2-2.6 2.3-2.3 3.9-5.9 4.6-9.6.4-2.1.2-4.2-.8-5.8z" fill="#b8c79f"/><circle cx="21.5" cy="23" r="2.3" fill="#E69F00"/></svg>'};
const nav=document.getElementById('gnav');if(!nav)return;
const link=p=>`<a class="gn-pg" href="${BASE}${p.f==='index.html'?'':p.f}"${p.f===here?' aria-current="page"':''}><span class="gn-pn">${p.f===here?I.here:''}${p.n}</span><span class="gn-pd">${p.d}</span></a>`;
nav.innerHTML=`<div class="gn-in">
 <a class="gn-brand" href="${BASE}">${I.mark}<span>海佃地圖</span></a>
 ${curP?`<span class="gn-where" aria-hidden="true">${SITE[cur].u}<span>›</span>${curP.n}</span>`:''}
 <ul class="gn-tabs">${SITE.map((g,i)=>`<li><button class="gn-tab" aria-expanded="false" aria-controls="gnp${i}"${i===cur?' data-cur="1"':''}>${g.u}${I.chev}</button>
   <div class="gn-pop" id="gnp${i}" hidden><div class="gn-ph">${g.u}<b>${g.t}</b></div>${g.pages.map(link).join('')}</div></li>`).join('')}</ul>
 <button class="gn-menu" aria-expanded="false" aria-controls="gnSheet">${I.menu}<span>目錄</span></button></div>
 <div class="gn-sheet" id="gnSheet" hidden><div class="gn-sh"><b>全部單元</b><button class="gn-close" aria-label="關閉目錄">${I.x}</button></div>
 ${SITE.map((g,i)=>`<section class="gn-sg${i===cur?' cur':''}"><h2>${g.u}<span>${g.t}</span></h2>${g.pages.map(link).join('')}</section>`).join('')}</div>`;
const tabs=[...nav.querySelectorAll('.gn-tab')];
const closeAll=except=>tabs.forEach(t=>{if(t!==except){t.setAttribute('aria-expanded','false');document.getElementById(t.getAttribute('aria-controls')).hidden=true;}});
tabs.forEach(t=>t.addEventListener('click',e=>{e.stopPropagation();const open=t.getAttribute('aria-expanded')==='true';closeAll(t);t.setAttribute('aria-expanded',String(!open));document.getElementById(t.getAttribute('aria-controls')).hidden=open;
  if(!open)document.getElementById(t.getAttribute('aria-controls')).querySelector('a')?.focus({preventScroll:true});}));
const menu=nav.querySelector('.gn-menu'),sheet=nav.querySelector('#gnSheet');
const setSheet=o=>{menu.setAttribute('aria-expanded',String(o));sheet.hidden=!o;document.documentElement.classList.toggle('gn-lock',o);if(o)sheet.querySelector('.gn-close').focus();else menu.focus({preventScroll:true});};
menu.addEventListener('click',()=>setSheet(true));sheet.querySelector('.gn-close').addEventListener('click',()=>setSheet(false));
document.addEventListener('click',e=>{if(!nav.contains(e.target))closeAll();});
document.addEventListener('keydown',e=>{if(e.key!=='Escape')return;const t=tabs.find(t=>t.getAttribute('aria-expanded')==='true');if(t){closeAll();t.focus();}if(!sheet.hidden)setSheet(false);});
})();
/* Small SVG map targets (labels, island dots): add an invisible hit area so each is at least 28px tall on screen. */
(()=>{const MIN=28,NS='http://www.w3.org/2000/svg';let t=0;
const run=()=>{document.querySelectorAll('svg g[role="button"]').forEach(g=>{if(g.querySelector(':scope>rect.hit'))return;let b;try{b=g.getBBox();}catch(e){return;}
  const m=g.getScreenCTM();if(!m||!b.width)return;const k=Math.hypot(m.a,m.b)||1;const h=b.height*k,w=b.width*k;if(h>=24)return;
  const H=MIN/k,W=Math.max(b.width,MIN/k);const r=document.createElementNS(NS,'rect');r.setAttribute('class','hit');
  r.setAttribute('x',b.x+b.width/2-W/2);r.setAttribute('y',b.y+b.height/2-H/2);r.setAttribute('width',W);r.setAttribute('height',H);
  r.setAttribute('fill','transparent');r.style.pointerEvents='all';g.insertBefore(r,g.firstChild);});};
const sch=()=>{if(t)return;t=setTimeout(()=>{t=0;run();},300);};
new MutationObserver(sch).observe(document.body,{childList:true,subtree:true});addEventListener('load',sch);addEventListener('resize',()=>{document.querySelectorAll('rect.hit').forEach(r=>r.remove());sch();});sch();})();
