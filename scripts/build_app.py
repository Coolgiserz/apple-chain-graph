# -*- coding: utf-8 -*-
"""Build the integrated Apple Supply-Chain app: graph (图谱) + report (上下游报告).

One self-contained, zero-dependency HTML page. A small view-router shell
(`App`) registers two views — `graph` and `report` — each implementing a
mount / activate / deactivate / focus lifecycle, so adding a third view later
is a one-line registration. Navigation is declarative:
  * top-nav tabs switch views              ->  <button data-view="graph">
  * any element can deep-link to a view    ->  <span data-jump="graph:S:tsmc">
  * URL hash (#/graph/S:tsmc) restores state, making links shareable.

The report body is rendered by the refactored report.py builders (jump=True),
and the graph is lazily initialised on first activation so the canvas always
has a real size when it becomes visible.
"""
import json, os
from report import build_report_inner, CSS as REPORT_CSS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = json.load(open(os.path.join(ROOT, "data", "apple_supply_chain.json"), encoding="utf-8"))

SHELL_CSS = """
* { box-sizing: border-box; }
html, body { margin: 0; height: 100%; font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif; }
#appbar { position: fixed; top: 0; left: 0; right: 0; height: 54px; display: flex; align-items: center; gap: 18px;
  padding: 0 18px; background: linear-gradient(135deg, #0a2540, #0a66c2); color: #fff; z-index: 100;
  box-shadow: 0 2px 10px rgba(0,0,0,.25); }
#appbar .brand { font-weight: 700; font-size: 16px; white-space: nowrap; }
#appbar .tabs { display: flex; gap: 8px; }
#appbar .tab { background: rgba(255,255,255,.12); color: #fff; border: 1px solid rgba(255,255,255,.25);
  border-radius: 8px; padding: 7px 14px; cursor: pointer; font-size: 14px; }
#appbar .tab.active { background: #fff; color: #0a2540; font-weight: 600; }
#appbar a.tab { background: rgba(255,255,255,.12); color: #fff; border: 1px solid rgba(255,255,255,.25);
  border-radius: 8px; padding: 7px 14px; cursor: pointer; font-size: 14px; text-decoration: none; }
#appbar a.tab:hover { background: rgba(255,255,255,.22); }
#appbar .hint { margin-left: auto; font-size: 12px; opacity: .85; }
main { position: absolute; top: 54px; left: 0; right: 0; bottom: 0; }
.view { position: absolute; inset: 0; display: none; }
.view.active { display: block; }
#view-graph { overflow: hidden; background: #0f1320; }
#view-report { overflow: auto; background: #f5f7fa; }
.rep-head { max-width: 1180px; margin: 0 auto; padding: 22px 20px 0; }
.rep-head h1 { margin: 0 0 4px; font-size: 24px; color: #0a2540; }
.rep-head p { margin: 4px 0; color: #5b6b7d; font-size: 13px; }
.lk { cursor: pointer; border-bottom: 1px dashed #0a66c2; }
.lk:hover { color: #0a66c2; background: #e8f1fb; border-radius: 3px; }
"""

GRAPH_CSS = """
#cv { position: absolute; inset: 0; width: 100%; height: 100%; cursor: grab; }
#cv.dragging { cursor: grabbing; }
#top { position: absolute; top: 64px; left: 12px; right: 12px; display: flex; flex-wrap: wrap; gap: 10px; align-items: center;
       background: rgba(20,26,42,.85); border: 1px solid #2a3450; border-radius: 12px; padding: 10px 14px; backdrop-filter: blur(8px); z-index: 10; }
#top .grp { display: flex; align-items: center; gap: 6px; }
#top label { font-size: 12px; color: #9fb0d0; }
#top input[type=search] { background: #0c1020; border: 1px solid #2a3450; color: #e8ecf4; border-radius: 8px; padding: 6px 10px; width: 200px; outline: none; }
#top select { background: #0c1020; border: 1px solid #2a3450; color: #e8ecf4; border-radius: 8px; padding: 6px 8px; outline: none; }
#top .chk { display: flex; align-items: center; gap: 4px; font-size: 13px; cursor: pointer; user-select: none; }
#top button { background: #2f6fed; color: #fff; border: none; border-radius: 8px; padding: 6px 12px; cursor: pointer; font-size: 13px; }
#top button.ghost { background: #2a3450; }
#top .dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
#hint { position: absolute; bottom: 12px; left: 12px; font-size: 12px; color: #7c8aa8; background: rgba(20,26,42,.7); padding: 6px 10px; border-radius: 8px; z-index: 10; }
#panel { position: absolute; top: 120px; right: 12px; width: 320px; max-height: calc(100% - 140px); overflow: auto;
         background: rgba(20,26,42,.95); border: 1px solid #2a3450; border-radius: 12px; padding: 16px; z-index: 9; display: none; }
#panel h3 { margin: 0 0 4px; font-size: 16px; }
#panel .sub { font-size: 12px; color: #9fb0d0; margin-bottom: 10px; }
#panel .tag { display: inline-block; font-size: 11px; padding: 2px 8px; border-radius: 999px; margin: 0 6px 8px 0; }
#panel dl { margin: 0; font-size: 13px; }
#panel dt { color: #9fb0d0; font-size: 11px; margin-top: 8px; }
#panel dd { margin: 2px 0 0; line-height: 1.5; }
#panel .close { position: absolute; top: 10px; right: 12px; cursor: pointer; color: #9fb0d0; font-size: 18px; }
#panel ul { margin: 4px 0 0; padding-left: 16px; }
#panel li { margin: 2px 0; }
#panel a.lk { color: #6ea0ff; border-bottom: 1px dashed #6ea0ff; }
#panel a.lk:hover { background: rgba(110,160,255,.15); }
"""

JS = r"""
const DATA = __DATA__;
const COLORS = { Product: "#2f6fed", Component: "#f59e0b", Supplier: "#10b981" };
const BASE_R = { Product: 11, Component: 7, Supplier: 6 };

/* =========================================================================
 * App shell — view registry + hash router.
 * A "view" is any object: { id, activate(params), deactivate(), focus(key)? }
 * Navigation is declarative:
 *   [data-view="graph"]            -> switch to that view (tab / button)
 *   [data-jump="graph:S:tsmc"]     -> switch + pass params (deep link)
 * Hash (#/graph/S:tsmc) restores state and stays shareable.
 * ========================================================================= */
const App = (function () {
  const views = {};
  let current = null;
  function register(v) {
    views[v.id] = v;
    v.el = document.getElementById("view-" + v.id);
  }
  function show(id, params) {
    const v = views[id];
    if (!v) return;
    if (current && current.id !== id) {
      current.el.classList.remove("active");
      if (current.deactivate) current.deactivate();
    }
    v.el.classList.add("active");
    document.querySelectorAll(".tab").forEach(b => b.classList.toggle("active", b.dataset.view === id));
    current = v;
    if (v.activate) v.activate(params || null);
    const hash = "#/" + id + (params ? "/" + params : "");
    if (location.hash !== hash) history.replaceState(null, "", hash);
  }
  function resolve() {
    const raw = (location.hash || "#/graph").replace(/^#\//, "");
    const parts = raw.split("/");
    show(parts[0] || "graph", parts.slice(1).join("/") || null);
  }
  function init() {
    document.querySelectorAll("[data-view]").forEach(b =>
      b.addEventListener("click", () => show(b.dataset.view)));
    document.addEventListener("click", e => {
      const el = e.target.closest("[data-jump]");
      if (!el) return;
      const seg = el.dataset.jump.split(":");
      show(seg[0], seg.slice(1).join(":") || null);
    });
    window.addEventListener("hashchange", resolve);
    resolve();
  }
  return { register, show, init, get current() { return current; } };
})();

/* =========================================================================
 * Graph view (force-directed canvas; adapted from build_viewer.py).
 * Lazily initialised on first activation so the canvas has real dimensions.
 * Exposes focus(key) so report -> graph deep links can centre a node.
 * ========================================================================= */
const graphView = (function () {
  const cv = document.getElementById("cv");
  const ctx = cv.getContext("2d");

  const idMap = {};
  const nodes = [];
  function addNode(n, type) {
    const o = Object.assign({ type, degree: 0 }, n);
    o.id = n.id; o._key = type[0] + ":" + n.id; idMap[o._key] = o; nodes.push(o);
  }
  DATA.nodes.products.forEach(p => addNode(p, "Product"));
  DATA.nodes.components.forEach(c => addNode(c, "Component"));
  DATA.nodes.suppliers.forEach(s => addNode(s, "Supplier"));

  const links = [];
  function addLink(t, from, to, extra) {
    const a = idMap["P:" + from] || idMap["C:" + from] || idMap["S:" + from];
    const b = idMap["P:" + to] || idMap["C:" + to] || idMap["S:" + to];
    if (a && b) { const l = { type: t, a, b }; if (extra) Object.assign(l, extra); links.push(l); a.degree++; b.degree++; }
  }
  DATA.edges.uses_component.forEach(e => addLink("USES", e.from, e.to));
  DATA.edges.supplied_by.forEach(e => addLink("SUPPLIES", e.from, e.to, { share: e.share, note: e.note }));
  DATA.edges.assembled_by.forEach(e => addLink("ASSEMBLES", e.from, e.to));

  const adj = {};
  nodes.forEach(n => adj[n._key] = []);
  links.forEach(l => { adj[l.a._key].push({ dir: "out", other: l.b, link: l }); adj[l.b._key].push({ dir: "in", other: l.a, link: l }); });

  const W = () => cv.clientWidth || window.innerWidth, H = () => cv.clientHeight || window.innerHeight;
  nodes.forEach((n, i) => {
    const ang = (i / nodes.length) * Math.PI * 2; const r = 200 + (i % 7) * 40;
    n.x = W() / 2 + Math.cos(ang) * r + (Math.random() - 0.5) * 30;
    n.y = H() / 2 + Math.sin(ang) * r + (Math.random() - 0.5) * 30; n.vx = 0; n.vy = 0;
  });

  let view = { ox: 0, oy: 0, scale: 1 };
  let alpha = 1, paused = false;
  const ALPHA_MIN = 0.005, ALPHA_DEC = 0.008;
  function reheat(a) { alpha = Math.max(alpha, (a == null ? 0.5 : a)); }

  function physics() {
    if (alpha < ALPHA_MIN) return;
    const vis = visibleSet();
    const arr = nodes.filter(n => vis.has(n._key));
    for (const n of arr) { n.fx = 0; n.fy = 0; }
    for (let i = 0; i < arr.length; i++) for (let j = i + 1; j < arr.length; j++) {
      const a = arr[i], b = arr[j]; let dx = a.x - b.x, dy = a.y - b.y; let d2 = dx * dx + dy * dy + 0.01; let d = Math.sqrt(d2);
      const f = 1800 / d2; const fx = dx / d * f, fy = dy / d * f; a.fx += fx; a.fy += fy; b.fx -= fx; b.fy -= fy;
    }
    for (const l of links) {
      if (!vis.has(l.a._key) || !vis.has(l.b._key)) continue;
      let dx = l.b.x - l.a.x, dy = l.b.y - l.a.y; let d = Math.sqrt(dx * dx + dy * dy) + 0.01; const f = (d - 90) * 0.03;
      const fx = dx / d * f, fy = dy / d * f; l.a.fx += fx; l.a.fy += fy; l.b.fx -= fx; l.b.fy -= fy;
    }
    for (const n of arr) {
      n.fx += (W() / 2 - n.x) * 0.001; n.fy += (H() / 2 - n.y) * 0.001;
      n.vx = (n.vx + n.fx * alpha) * 0.9; n.vy = (n.vy + n.fy * alpha) * 0.9;
      const sp = Math.hypot(n.vx, n.vy); if (sp > 18) { n.vx *= 18 / sp; n.vy *= 18 / sp; }
      if (!n.fixed) { n.x += n.vx; n.y += n.vy; }
    }
    alpha = Math.max(0, alpha - ALPHA_DEC);
  }

  function visibleSet() {
    const q = document.getElementById("q").value.trim().toLowerCase();
    const cbP = document.getElementById("cbP").checked, cbC = document.getElementById("cbC").checked, cbS = document.getElementById("cbS").checked;
    const line = document.getElementById("line").value;
    const set = new Set();
    for (const n of nodes) {
      if (n.type === "Product" && !cbP) continue;
      if (n.type === "Component" && !cbC) continue;
      if (n.type === "Supplier" && !cbS) continue;
      if (n.type === "Product" && line && n.product_line !== line) continue;
      set.add(n._key);
    }
    if (line) {
      const keep = new Set(set);
      for (const n of nodes) { if (n.type === "Product") continue; let touch = false;
        for (const e of adj[n._key]) { if (keep.has(e.other._key)) { touch = true; break; } }
        if (!touch) set.delete(n._key);
      }
    }
    if (q) {
      const match = new Set();
      for (const n of nodes) { if (set.has(n._key)) {
        const hay = (n.name + " " + (n.english_name || "") + " " + n.id + " " + (n.short_name || "") + " " + (n.alias || "")).toLowerCase();
        if (hay.includes(q)) match.add(n._key);
      } }
      const keep = new Set(match);
      for (const k of match) for (const e of adj[k]) keep.add(e.other._key);
      return keep;
    }
    return set;
  }

  function resize() {
    const w = cv.clientWidth || window.innerWidth, h = cv.clientHeight || window.innerHeight;
    cv.width = w * devicePixelRatio; cv.height = h * devicePixelRatio;
    ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
  }
  function label(n) { return n.name || n.english_name || n.id; }

  let selected = null, hover = null, dragNode = null, panning = false, last = { x: 0, y: 0 }, moved = false;
  function toWorld(px, py) { return { x: (px - view.ox) / view.scale, y: (py - view.oy) / view.scale }; }
  function pick(px, py) {
    const w = toWorld(px, py); let best = null, bd = 1e9; const vis = visibleSet();
    for (const n of nodes) { if (!vis.has(n._key)) continue; const dx = n.x - w.x, dy = n.y - w.y; const d = dx * dx + dy * dy;
      const r = BASE_R[n.type] + Math.min(n.degree, 12) * 0.35 + 4; if (d < r * r && d < bd) { best = n; bd = d; } }
    return best;
  }

  function draw() {
    ctx.clearRect(0, 0, W(), H());
    const vis = visibleSet();
    const select = selected ? selected._key : null;
    const nb = select ? new Set([select, ...adj[select].map(e => e.other._key)]) : null;
    ctx.save(); ctx.translate(view.ox, view.oy); ctx.scale(view.scale, view.scale);
    for (const l of links) {
      if (!vis.has(l.a._key) || !vis.has(l.b._key)) continue;
      const hot = nb && nb.has(l.a._key) && nb.has(l.b._key);
      ctx.strokeStyle = hot ? "rgba(150,180,255,.9)" : (nb ? "rgba(120,135,170,.08)" : "rgba(120,135,170,.22)");
      ctx.lineWidth = hot ? 1.6 : 1; ctx.beginPath(); ctx.moveTo(l.a.x, l.a.y); ctx.lineTo(l.b.x, l.b.y); ctx.stroke();
    }
    for (const n of nodes) {
      if (!vis.has(n._key)) continue;
      const r = BASE_R[n.type] + Math.min(n.degree, 12) * 0.35;
      const dim = nb && !nb.has(n._key);
      ctx.globalAlpha = dim ? 0.18 : 1;
      ctx.beginPath(); ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
      ctx.fillStyle = COLORS[n.type]; ctx.fill();
      ctx.lineWidth = (select === n._key) ? 3 : 1.2; ctx.strokeStyle = (select === n._key) ? "#fff" : "rgba(255,255,255,.35)"; ctx.stroke();
      if (view.scale > 0.7 || n.type === "Product" || select === n._key || hover === n) {
        ctx.globalAlpha = dim ? 0.25 : 1; ctx.fillStyle = "#dfe7f7"; ctx.font = "11px sans-serif"; ctx.textAlign = "center";
        ctx.fillText(label(n), n.x, n.y + r + 12);
      }
      ctx.globalAlpha = 1;
    }
    ctx.restore();
  }

  function selectNode(n) {
    selected = n;
    if (!n) { document.getElementById("panel").style.display = "none"; return; }
    renderPanel(n); document.getElementById("panel").style.display = "block";
  }
  function renderPanel(n) {
    const p = document.getElementById("pbody"); const col = COLORS[n.type];
    let h = "<h3>" + esc(n.name || n.id) + "</h3><div class='sub'>" + esc(n.english_name || "") + "</div>";
    h += "<span class='tag' style='background:" + col + "22;color:" + col + ";border:1px solid " + col + "'>" + n.type + "</span>";
    if (n.type === "Product" && n.product_line) h += "<span class='tag' style='background:#2a3450;color:#cfe0ff'>" + esc(n.product_line) + "</span>";
    h += "<dl>";
    const fields = n.type === "Product"
      ? [["发布时间", n.release_date], ["状态", n.status], ["起售价(USD)", n.price_usd ? ("$" + n.price_usd) : ""], ["SoC", n.soc], ["显示屏", n.display], ["别名", n.alias], ["代工", (n.assembly || []).map(id => nm("S", id)).join("、")]]
      : n.type === "Component"
      ? [["类别", n.category], ["子类", n.subcategory]]
      : [["简称", n.short_name], ["国家/地区", n.country], ["区域", n.region], ["类别", n.category], ["层级", n.tier]];
    for (const [k, v] of fields) { if (v) h += "<dt>" + k + "</dt><dd>" + esc(String(v)) + "</dd>"; }
    h += "</dl>";
    const out = [], inc = []; for (const e of adj[n._key]) { (e.dir === "out" ? out : inc).push(e); }
    if (out.length) {
      h += "<dt style='margin-top:12px;color:#9fb0d0;font-size:11px'>关联（" + out.length + "）</dt><dd><ul>";
      for (const e of out) { let extra = e.link.share ? " · 份额 " + e.link.share + "%" : ""; h += "<li><b>" + e.link.type + "</b> → " + esc(label(e.other)) + extra + "</li>"; }
      h += "</ul></dd>";
    }
    const sec = n.type === "Product" ? "sec-products" : n.type === "Component" ? "sec-components" : "sec-suppliers";
    h += "<p style='margin-top:10px'><a class='lk' data-jump='report:" + sec + "'>在报告中查看该" + (n.type === "Product" ? "型号" : n.type === "Component" ? "零部件" : "供应商") + " →</a></p>";
    if (n.type === "Supplier") {
      h += "<p style='margin-top:6px'><a class='lk' href='../tools/visualizations/supplier_geo.html?supplier=" + n.id + "' target='_blank' style='color:#6ea0ff'>在地图中查看 →</a></p>";
    }
    p.innerHTML = h;
  }
  function nm(t, id) { const o = idMap[t + ":" + id]; return o ? label(o) : id; }
  function esc(s) { return String(s).replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c])); }

  cv.addEventListener("mousedown", e => {
    moved = false; last = { x: e.clientX, y: e.clientY }; const n = pick(e.clientX, e.clientY);
    if (n) { dragNode = n; n.fixed = true; reheat(0.3); } else { panning = true; cv.classList.add("dragging"); }
  });
  cv.addEventListener("mousemove", e => {
    const dx = e.clientX - last.x, dy = e.clientY - last.y; if (Math.abs(dx) + Math.abs(dy) > 3) moved = true;
    if (dragNode) { const w = toWorld(e.clientX, e.clientY); dragNode.x = w.x; dragNode.y = w.y; dragNode.vx = 0; dragNode.vy = 0; }
    else if (panning) { view.ox += dx; view.oy += dy; }
    else { hover = pick(e.clientX, e.clientY); cv.style.cursor = hover ? "pointer" : "grab"; }
    last = { x: e.clientX, y: e.clientY };
  });
  window.addEventListener("mouseup", e => {
    if (dragNode) { dragNode.fixed = false; dragNode = null; }
    panning = false; cv.classList.remove("dragging");
    if (!moved) { const n = pick(e.clientX, e.clientY); selectNode(n); }
  });
  cv.addEventListener("wheel", e => {
    e.preventDefault();
    const factor = e.deltaY < 0 ? 1.1 : 0.9, mx = e.clientX, my = e.clientY;
    const wx = (mx - view.ox) / view.scale, wy = (my - view.oy) / view.scale;
    view.scale *= factor; view.ox = mx - wx * view.scale; view.oy = my - wy * view.scale;
  }, { passive: false });

  document.getElementById("pc").onclick = () => selectNode(null);
  document.getElementById("reset").onclick = () => {
    view = { ox: 0, oy: 0, scale: 1 }; selectNode(null);
    document.getElementById("q").value = "";
    document.getElementById("cbP").checked = document.getElementById("cbC").checked = document.getElementById("cbS").checked = true;
    document.getElementById("line").value = ""; reheat(1);
  };
  const lines = [...new Set(DATA.nodes.products.map(p => p.product_line))];
  lines.forEach(l => { const o = document.createElement("option"); o.value = l; o.textContent = l; document.getElementById("line").appendChild(o); });
  ["q", "cbP", "cbC", "cbS", "line"].forEach(id =>
    document.getElementById(id).addEventListener("input", () => { if (id !== "q") selectNode(null); reheat(0.7); }));

  function loop() { if (!paused) physics(); draw(); requestAnimationFrame(loop); }

  let inited = false;
  function focus(key) {
    const n = idMap[key]; if (!n) return;
    selected = n; reheat(1);
    view.ox = W() / 2 - n.x * view.scale; view.oy = H() / 2 - n.y * view.scale;
    renderPanel(n); document.getElementById("panel").style.display = "block";
  }
  return {
    id: "graph",
    activate(params) {
      if (!inited) { inited = true; resize(); reheat(1); loop(); }
      else { resize(); reheat(0.5); }
      if (params) focus(params);
    },
    deactivate() { paused = true; },
    focus
  };
})();

/* =========================================================================
 * Report view — content injected server-side; only handles deep-link scroll.
 * ========================================================================= */
const reportView = {
  id: "report",
  activate(params) {
    if (params && params.indexOf("sec-") === 0) {
      const el = document.getElementById(params);
      if (el) setTimeout(() => el.scrollIntoView({ behavior: "smooth", block: "start" }), 30);
    }
  },
  deactivate() {}
};

App.register(graphView);
App.register(reportView);
App.init();
"""

HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>苹果供应链 · 图谱与上下游报告（整合版）</title>
<style>__SHELL____GRAPH____REPORT_CSS__</style>
</head>
<body>
<header id="appbar">
  <div class="brand">🍎 苹果供应链 · 图谱 &amp; 报告</div>
  <nav class="tabs">
    <button class="tab active" data-view="graph">🕸️ 供应链图谱</button>
    <button class="tab" data-view="report">📄 上下游报告</button>
    <a class="tab" href="../tools/visualizations/supplier_geo.html" target="_blank">🗺️ 供应商地图</a>
    <a class="tab" href="../tools/visualizations/supplier_dashboard.html" target="_blank">📊 估值看板</a>
  </nav>
  <div class="hint">点击报告中的<strong>蓝色虚线实体</strong>可跳转图谱并定位节点</div>
</header>
<main>
  <section id="view-graph" class="view active">
    <canvas id="cv"></canvas>
    <div id="top">
      <div class="grp"><input type="search" id="q" placeholder="搜索产品/零部件/供应商…"></div>
      <div class="grp">
        <label class="chk"><input type="checkbox" id="cbP" checked><span class="dot" style="background:#2f6fed"></span>产品</label>
        <label class="chk"><input type="checkbox" id="cbC" checked><span class="dot" style="background:#f59e0b"></span>零部件</label>
        <label class="chk"><input type="checkbox" id="cbS" checked><span class="dot" style="background:#10b981"></span>供应商</label>
      </div>
      <div class="grp"><label>产品线</label><select id="line"><option value="">全部</option></select></div>
      <button id="reset" class="ghost">重置视图</button>
      <button data-view="report" class="ghost" title="跳转到上下游报告">📄 查看报告 →</button>
    </div>
    <div id="panel"><span class="close" id="pc">×</span><div id="pbody"></div></div>
    <div id="hint">滚轮缩放 · 拖拽画布平移 · 拖动节点 · 单击节点看详情</div>
  </section>
  <section id="view-report" class="view">
    <div class="rep-head">
      <h1>苹果产品供应链上下游图谱报告</h1>
      <p>Apple Product Supply-Chain Graph · 产品线 × 零部件 × 供应商 × 产业链（属性增强版 v2）</p>
      <p>点击下方表格中的<strong>蓝色虚线实体</strong>可跳转到图谱并定位对应节点；图谱节点详情中亦可一键返回本报告。</p>
    </div>
    <div class="wrap" id="report-body">__REPORT__</div>
  </section>
</main>
<script>__JS__</script>
</body>
</html>
"""


def main():
    report_html = build_report_inner(DATA, jump=True)
    out = (HTML
           .replace("__SHELL__", SHELL_CSS)
           .replace("__GRAPH__", GRAPH_CSS)
           .replace("__REPORT__", report_html)
           .replace("__REPORT_CSS__", REPORT_CSS)
           .replace("__JS__", JS)
           .replace("__DATA__", json.dumps(DATA, ensure_ascii=False)))
    dst = os.path.join(ROOT, "dist", "apple_supply_chain_app.html")
    with open(dst, "w", encoding="utf-8") as f:
        f.write(out)
    print("App written:", dst, "bytes:", len(out))


if __name__ == "__main__":
    main()
