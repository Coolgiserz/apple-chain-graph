const COLORS = { Product:"#2f6fed", Component:"#f59e0b", Supplier:"#10b981" };
const BASE_R = { Product:11, Component:7, Supplier:6 };

// 1) 组装节点与边
const idMap = {};
const nodes = [];
function addNode(n, type){ const o = Object.assign({type, degree:0}, n); o.id = n.id; o._key = type[0]+":"+n.id; idMap[o._key]=o; nodes.push(o); }
DATA.nodes.products.forEach(p=>addNode(p,"Product"));
DATA.nodes.components.forEach(c=>addNode(c,"Component"));
DATA.nodes.suppliers.forEach(s=>addNode(s,"Supplier"));

const links = [];
function addLink(t, from, to, extra){ const a=idMap["P:"+from]||idMap["C:"+from]||idMap["S:"+from]; const b=idMap["P:"+to]||idMap["C:"+to]||idMap["S:"+to]; if(a&&b){ const l={type:t,a,b}; if(extra) Object.assign(l,extra); links.push(l); a.degree++; b.degree++; } }
DATA.edges.uses_component.forEach(e=>addLink("USES", e.from, e.to));
DATA.edges.supplied_by.forEach(e=>addLink("SUPPLIES", e.from, e.to, {share:e.share, note:e.note}));
DATA.edges.assembled_by.forEach(e=>addLink("ASSEMBLES", e.from, e.to));

// 邻接表（用于详情面板）
const adj = {}; nodes.forEach(n=>adj[n._key]=[]);
links.forEach(l=>{ adj[l.a._key].push({dir:"out",other:l.b,link:l}); adj[l.b._key].push({dir:"in",other:l.a,link:l}); });

// 2) 初始布局（环形 + 随机扰动），避免重叠
const cv = document.getElementById("cv");   // 提前声明，避免 W()/H() 在布局阶段访问 TDZ 导致整脚本崩溃
const W = ()=>cv.clientWidth || window.innerWidth, H = ()=>cv.clientHeight || window.innerHeight;
nodes.forEach((n,i)=>{ const ang = (i/nodes.length)*Math.PI*2; const r = 200 + (i%7)*40;
  n.x = W()/2 + Math.cos(ang)*r + (Math.random()-0.5)*30; n.y = H()/2 + Math.sin(ang)*r + (Math.random()-0.5)*30; n.vx=0; n.vy=0; });

// 3) 物理模拟（弹簧-斥力模型 + 退火冷却，稳定后自动停止"跳动"）
let view = {ox:0, oy:0, scale:1};
let alpha = 1;                       // 模拟"温度"，随时间衰减
const ALPHA_MIN = 0.005, ALPHA_DEC = 0.008;
function reheat(a){ alpha = Math.max(alpha, (a==null?0.5:a)); }
function physics(){
  if(alpha < ALPHA_MIN) return;      // 已稳定：不再施力，画面静止
  const vis = visibleSet();
  const arr = nodes.filter(n=>vis.has(n._key));
  for(const n of arr){ n.fx=0; n.fy=0; }
  // 斥力
  for(let i=0;i<arr.length;i++) for(let j=i+1;j<arr.length;j++){
    const a=arr[i], b=arr[j]; let dx=a.x-b.x, dy=a.y-b.y; let d2=dx*dx+dy*dy+0.01; let d=Math.sqrt(d2);
    const f = 1800/d2; const fx=dx/d*f, fy=dy/d*f; a.fx+=fx; a.fy+=fy; b.fx-=fx; b.fy-=fy;
  }
  // 弹簧
  for(const l of links){ if(!vis.has(l.a._key)||!vis.has(l.b._key)) continue;
    let dx=l.b.x-l.a.x, dy=l.b.y-l.a.y; let d=Math.sqrt(dx*dx+dy*dy)+0.01; const f=(d-90)*0.03;
    const fx=dx/d*f, fy=dy/d*f; l.a.fx+=fx; l.a.fy+=fy; l.b.fx-=fx; l.b.fy-=fy; }
  // 向心力 + 积分（力按 alpha 缩放，速度限幅）
  for(const n of arr){ n.fx += (W()/2 - n.x)*0.001; n.fy += (H()/2 - n.y)*0.001;
    n.vx = (n.vx + n.fx*alpha)*0.9; n.vy = (n.vy + n.fy*alpha)*0.9;
    const sp=Math.hypot(n.vx,n.vy); if(sp>18){ n.vx*=18/sp; n.vy*=18/sp; }
    if(!n.fixed){ n.x += n.vx; n.y += n.vy; } }
  alpha = Math.max(0, alpha - ALPHA_DEC);   // 冷却
}
function visibleSet(){
  const q = document.getElementById("q").value.trim().toLowerCase();
  const cbP=document.getElementById("cbP").checked, cbC=document.getElementById("cbC").checked, cbS=document.getElementById("cbS").checked;
  const line=document.getElementById("line").value;
  const set = new Set();
  for(const n of nodes){
    if(n.type==="Product" && !cbP) continue;
    if(n.type==="Component" && !cbC) continue;
    if(n.type==="Supplier" && !cbS) continue;
    if(n.type==="Product" && line && n.product_line!==line) continue;
    set.add(n._key);
  }
  if(line){ // 仅保留与可见产品相连的零部件/供应商
    const keep = new Set(set);
    for(const n of nodes){ if(n.type==="Product") continue; let touch=false;
      for(const e of adj[n._key]){ if(keep.has(e.other._key)){ touch=true; break; } }
      if(!touch) set.delete(n._key);
    }
  }
  if(q){
    const match=new Set();
    for(const n of nodes){ if(set.has(n._key)){ const hay=(n.name+" "+(n.english_name||"")+" "+n.id+" "+(n.short_name||"")+" "+(n.alias||"")).toLowerCase(); if(hay.includes(q)) match.add(n._key); } }
    const keep=new Set(match);
    for(const k of match) for(const e of adj[k]) keep.add(e.other._key);
    return keep;
  }
  return set;
}

// 4) 渲染
const ctx=cv.getContext("2d");
function resize(){ cv.width=W()*devicePixelRatio; cv.height=H()*devicePixelRatio; ctx.setTransform(devicePixelRatio,0,0,devicePixelRatio,0,0); }
window.addEventListener("resize", resize); resize();
function label(n){ return n.name || n.english_name || n.id; }
function draw(){
  ctx.clearRect(0,0,W(),H());
  const vis=visibleSet();
  const select = selected ? selected._key : null;
  const nb = select ? new Set([select, ...adj[select].map(e=>e.other._key)]) : null;
  ctx.save(); ctx.translate(view.ox, view.oy); ctx.scale(view.scale, view.scale);
  // 边
  for(const l of links){ if(!vis.has(l.a._key)||!vis.has(l.b._key)) continue;
    const hot = nb && nb.has(l.a._key) && nb.has(l.b._key);
    ctx.strokeStyle = hot ? "rgba(150,180,255,.9)" : (nb ? "rgba(120,135,170,.08)" : "rgba(120,135,170,.22)");
    ctx.lineWidth = hot ? 1.6 : 1; ctx.beginPath(); ctx.moveTo(l.a.x,l.a.y); ctx.lineTo(l.b.x,l.b.y); ctx.stroke();
  }
  // 节点
  for(const n of nodes){ if(!vis.has(n._key)) continue;
    const r = BASE_R[n.type] + Math.min(n.degree,12)*0.35;
    const dim = nb && !nb.has(n._key);
    ctx.globalAlpha = dim ? 0.18 : 1;
    ctx.beginPath(); ctx.arc(n.x,n.y,r,0,Math.PI*2);
    ctx.fillStyle = COLORS[n.type]; ctx.fill();
    ctx.lineWidth = (select===n._key)?3:1.2; ctx.strokeStyle = (select===n._key)?"#fff":"rgba(255,255,255,.35)"; ctx.stroke();
    // 标签
    if(view.scale>0.7 || n.type==="Product" || select===n._key || hover===n){
      ctx.globalAlpha = dim?0.25:1; ctx.fillStyle="#dfe7f7"; ctx.font="11px sans-serif"; ctx.textAlign="center";
      ctx.fillText(label(n), n.x, n.y + r + 12);
    }
    ctx.globalAlpha = 1;
  }
  ctx.restore();
}

// 5) 交互
let selected=null, hover=null, dragNode=null, panning=false, last={x:0,y:0}, moved=false;
function toWorld(px,py){ return { x:(px-view.ox)/view.scale, y:(py-view.oy)/view.scale }; }
function pick(px,py){ const w=toWorld(px,py); let best=null,bd=1e9; const vis=visibleSet();
  for(const n of nodes){ if(!vis.has(n._key)) continue; const dx=n.x-w.x, dy=n.y-w.y; const d=dx*dx+dy*dy; const r=BASE_R[n.type]+Math.min(n.degree,12)*0.35+4; if(d<r*r && d<bd){ best=n; bd=d; } } return best; }
cv.addEventListener("mousedown", e=>{ moved=false; last={x:e.clientX,y:e.clientY}; const n=pick(e.clientX,e.clientY);
  if(n){ dragNode=n; n.fixed=true; reheat(0.3); } else { panning=true; cv.classList.add("dragging"); } });
cv.addEventListener("mousemove", e=>{ const dx=e.clientX-last.x, dy=e.clientY-last.y; if(Math.abs(dx)+Math.abs(dy)>3) moved=true;
  if(dragNode){ const w=toWorld(e.clientX,e.clientY); dragNode.x=w.x; dragNode.y=w.y; dragNode.vx=0; dragNode.vy=0; }
  else if(panning){ view.ox+=dx; view.oy+=dy; }
  else { hover=pick(e.clientX,e.clientY); cv.style.cursor=hover?"pointer":"grab"; }
  last={x:e.clientX,y:e.clientY};
});
window.addEventListener("mouseup", e=>{ if(dragNode){ dragNode.fixed=false; dragNode=null; } panning=false; cv.classList.remove("dragging");
  if(!moved){ const n=pick(e.clientX,e.clientY); selectNode(n); } });
cv.addEventListener("wheel", e=>{ e.preventDefault(); const factor=e.deltaY<0?1.1:0.9; const mx=e.clientX,my=e.clientY;
  const wx=(mx-view.ox)/view.scale, wy=(my-view.oy)/view.scale; view.scale*=factor; view.ox=mx-wx*view.scale; view.oy=my-wy*view.scale; }, {passive:false});

function selectNode(n){ selected=n; if(!n){ document.getElementById("panel").style.display="none"; return; } renderPanel(n); document.getElementById("panel").style.display="block"; }
function renderPanel(n){
  const p=document.getElementById("pbody"); const col=COLORS[n.type];
  let h=`<h3>${esc(n.name||n.id)}</h3><div class="sub">${esc(n.english_name||"")}</div>`;
  h+=`<span class="tag" style="background:${col}22;color:${col};border:1px solid ${col}">${n.type}</span>`;
  if(n.type==="Product" && n.product_line) h+=`<span class="tag" style="background:#2a3450;color:#cfe0ff">${esc(n.product_line)}</span>`;
  h+=`<dl>`;
  const fields = n.type==="Product"
    ? [["发布时间",n.release_date],["状态",n.status],["起售价(USD)",n.price_usd?("$"+n.price_usd):""],["SoC",n.soc],["显示屏",n.display],["别名",n.alias],["代工",(n.assembly||[]).map(id=>nm("S",id)).join("、")]]
    : n.type==="Component"
    ? [["类别",n.category],["子类",n.subcategory]]
    : [["简称",n.short_name],["国家/地区",n.country],["区域",n.region],["类别",n.category],["层级",n.tier]];
    for(const [k,v] of fields){ if(v) h+=`<dt>${k}</dt><dd>${esc(String(v))}</dd>`; }
  h+=`</dl>`;
  // 跨页面跳转：报告 / 地图
  const sec = n.type==="Product" ? "sec-products" : n.type==="Component" ? "sec-components" : "sec-suppliers";
  let xlinks = `<p style="margin-top:10px"><a class="lk" href="apple_supply_chain_report.html#${sec}" target="_blank">在报告中查看 →</a>`;
  if(n.type==="Supplier") xlinks += ` &nbsp; <a class="lk" href="../tools/visualizations/supplier_geo.html?supplier=${esc(n.id)}" target="_blank">在地图中查看 →</a>`;
  xlinks += `</p>`;
  h+=xlinks;
  // 关联
  const out=[], inc=[]; for(const e of adj[n._key]){ (e.dir==="out"?out:inc).push(e); }
  if(out.length){ h+=`<dt style="margin-top:12px;color:#9fb0d0;font-size:11px">关联（${out.length}）</dt><dd><ul>`;
    for(const e of out){ let extra = e.link.share?` · 份额 ${e.link.share}%`:""; h+=`<li><b>${e.link.type}</b> → ${esc(label(e.other))}${extra}</li>`; } h+=`</ul></dd>`; }
  p.innerHTML=h;
}
function nm(t,id){ const o=idMap[t+":"+id]; return o?label(o):id; }
function esc(s){ return String(s).replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c])); }
document.getElementById("pc").onclick=()=>selectNode(null);
document.getElementById("reset").onclick=()=>{ view={ox:0,oy:0,scale:1}; selectNode(null); document.getElementById("q").value=""; document.getElementById("cbP").checked=document.getElementById("cbC").checked=document.getElementById("cbS").checked=true; document.getElementById("line").value=""; reheat(1); };
// 产品线下拉
const lines=[...new Set(DATA.nodes.products.map(p=>p.product_line))];
lines.forEach(l=>{ const o=document.createElement("option"); o.value=l; o.textContent=l; document.getElementById("line").appendChild(o); });
["q","cbP","cbC","cbS","line"].forEach(id=>document.getElementById(id).addEventListener("input",()=>{ if(id!=="q") selectNode(null); reheat(0.7); }));

// 6) 主循环
function loop(){ physics(); draw(); requestAnimationFrame(loop); }
loop();

// 7) 深链：从其它页面带 ?focus=KEY 跳转过来时，自动选中并居中该节点
(function(){
  const pk = new URLSearchParams(location.search).get("focus");
  if(pk && idMap[pk]){
    const n = idMap[pk];
    selectNode(n);
    view.ox = W()/2 - n.x*view.scale;
    view.oy = H()/2 - n.y*view.scale;
    reheat(0.4);
  }
})();
