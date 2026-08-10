// interaction.js — 鼠标/触摸交互、聚焦深链、动画循环（「交互」模块，可独立演进）。
import { S, ALPHA_MIN } from "./state.js";
import { W, H, esc, nodeRadius, label, i18nText } from "./util.js";
import { visibleSet } from "./model.js";
import { draw, syncSize, resize } from "./render.js";
import { selectNode, renderPanel, renderRiskPanel, showRiskPanel } from "./panels.js";
import { physics } from "./physics.js";

// 把鼠标事件坐标（viewport 坐标）换算成画布内部坐标：必须减去画布自身偏移，否则点选/拖拽会整体偏移。
function localXY(px, py) { var r = S.cv.getBoundingClientRect(); return { x: px - r.left, y: py - r.top }; }
function toWorld(px, py) { var l = localXY(px, py); return { x: (l.x - S.view.ox) / S.view.scale, y: (l.y - S.view.oy) / S.view.scale }; }

function pick(px, py) {
  var w = toWorld(px, py), best = null, bd = 1e9, vis = visibleSet();
  for (var i = 0; i < S.nodes.length; i++) {
    var n = S.nodes[i]; if (!vis.has(n._key)) continue;
    var dx = n.x - w.x, dy = n.y - w.y, d = dx * dx + dy * dy;
    var r = nodeRadius(n) + 4;
    if (d < r * r && d < bd) { best = n; bd = d; }
  }
  return best;
}

// 单击节点：产品/零部件切换其供应商子图的展开/收起（渐进式披露）；供应商仅选中看详情。
function onNodeClick(n) {
  if (!n) { selectNode(null); return; }
  if (n.type === "Product" || n.type === "Component") {
    if (S.expanded.has(n._key)) S.expanded.delete(n._key);
    else S.expanded.add(n._key);
    reheat(0.6);
  }
  selectNode(n);
}

export function bindEvents() {
  S.cv.addEventListener("mousedown", function (e) {
    S.downX = e.clientX; S.downY = e.clientY;
    S.downNode = pick(e.clientX, e.clientY);   // 仅记录候选，不立即进入拖拽/平移
    S.pointerDown = true;
    kick();
  });
  S.cv.addEventListener("mousemove", function (e) {
    if (S.dragNode) {
      var w = toWorld(e.clientX, e.clientY); S.dragNode.x = w.x; S.dragNode.y = w.y; S.dragNode.vx = 0; S.dragNode.vy = 0;
    } else if (S.panning) {
      S.view.ox += e.clientX - S.last.x; S.view.oy += e.clientY - S.last.y;
      S.last = { x: e.clientX, y: e.clientY };
    } else if (S.pointerDown) {
      var dx = e.clientX - S.downX, dy = e.clientY - S.downY;
      if (Math.abs(dx) + Math.abs(dy) > S.DRAG_THRESH) {
        if (S.downNode) { S.dragNode = S.downNode; S.dragNode.fixed = true; reheat(0.3);
          var w0 = toWorld(e.clientX, e.clientY); S.dragNode.x = w0.x; S.dragNode.y = w0.y; S.dragNode.vx = 0; S.dragNode.vy = 0; }
        else { S.panning = true; S.cv.classList.add("dragging"); }
        S.last = { x: e.clientX, y: e.clientY };
      } else {
        S.hover = pick(e.clientX, e.clientY); S.cv.style.cursor = S.hover ? "pointer" : "grab";
      }
    } else {
      S.hover = pick(e.clientX, e.clientY); S.cv.style.cursor = S.hover ? "pointer" : "grab";
    }
    kick();
  });
  (typeof window !== "undefined" ? window : globalThis).addEventListener("mouseup", function (e) {
    var wasClick = !S.dragNode && !S.panning;
    if (S.dragNode) { S.dragNode.fixed = false; S.dragNode = null; }
    if (S.panning) { S.panning = false; S.cv.classList.remove("dragging"); }
    if (wasClick) onNodeClick(S.downNode || null);
    S.downNode = null; S.pointerDown = false;
    kick();
  });
  S.cv.addEventListener("wheel", function (e) {
    e.preventDefault();
    var l = localXY(e.clientX, e.clientY);
    var factor = e.deltaY < 0 ? 1.1 : 0.9;
    var wx = (l.x - S.view.ox) / S.view.scale, wy = (l.y - S.view.oy) / S.view.scale;
    S.view.scale *= factor; S.view.ox = l.x - wx * S.view.scale; S.view.oy = l.y - wy * S.view.scale;
    kick();
  }, { passive: false });

  // 触摸支持（移动端）：单指拖拽/点击节点，双指 pinch 缩放
  function touchDist(e) { var a = e.touches[0], b = e.touches[1]; return Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY); }
  function touchMid(e) { var a = e.touches[0], b = e.touches[1]; return { x: (a.clientX + b.clientX) / 2, y: (a.clientY + b.clientY) / 2 }; }
  S.cv.addEventListener("touchstart", function (e) {
    e.preventDefault();
    if (e.touches.length === 1) {
      var t = e.touches[0];
      S.downX = t.clientX; S.downY = t.clientY;
      S.downNode = pick(t.clientX, t.clientY);
      S.touchActive = true; S.panning = false; S.dragNode = null;
      S.last = { x: t.clientX, y: t.clientY };
    } else if (e.touches.length >= 2) {
      S.pinching = true; S.touchActive = false; S.dragNode = null; S.panning = false;
      S.pinchDist = touchDist(e); S.pinchScale = S.view.scale;
    }
    kick();
  }, { passive: false });
  S.cv.addEventListener("touchmove", function (e) {
    if (S.pinching && e.touches.length >= 2) {
      e.preventDefault();
      var d = touchDist(e);
      if (S.pinchDist > 0) {
        var mid = touchMid(e), l = localXY(mid.x, mid.y);
        var factor = d / S.pinchDist;
        var wx = (l.x - S.view.ox) / S.view.scale, wy = (l.y - S.view.oy) / S.view.scale;
        S.view.scale = S.pinchScale * factor;
        S.view.ox = l.x - wx * S.view.scale; S.view.oy = l.y - wy * S.view.scale;
      }
      kick();
      return;
    }
    if (!S.touchActive || e.touches.length !== 1) return;
    e.preventDefault();
    var t = e.touches[0];
    var dx = t.clientX - S.downX, dy = t.clientY - S.downY;
    if (S.dragNode) {
      var w = toWorld(t.clientX, t.clientY); S.dragNode.x = w.x; S.dragNode.y = w.y; S.dragNode.vx = 0; S.dragNode.vy = 0;
    } else if (S.panning) {
      S.view.ox += t.clientX - S.last.x; S.view.oy += t.clientY - S.last.y; S.last = { x: t.clientX, y: t.clientY };
    } else if (Math.abs(dx) + Math.abs(dy) > S.DRAG_THRESH) {
      if (S.downNode) { S.dragNode = S.downNode; S.dragNode.fixed = true; reheat(0.3);
        var w0 = toWorld(t.clientX, t.clientY); S.dragNode.x = w0.x; S.dragNode.y = w0.y; S.dragNode.vx = 0; S.dragNode.vy = 0; }
      else { S.panning = true; }
      S.last = { x: t.clientX, y: t.clientY };
    }
    kick();
  }, { passive: false });
  function onTouchEnd(e) {
    if (S.pinching) { if (e.touches.length < 2) S.pinching = false; return; }
    if (e.touches.length > 0) return;
    var wasClick = S.touchActive && !S.dragNode && !S.panning;
    if (S.dragNode) { S.dragNode.fixed = false; S.dragNode = null; }
    if (S.panning) S.panning = false;
    if (wasClick) onNodeClick(S.downNode || null);
    S.downNode = null; S.touchActive = false;
    kick();
  }
  S.cv.addEventListener("touchend", onTouchEnd, { passive: false });
  S.cv.addEventListener("touchcancel", onTouchEnd, { passive: false });
  (typeof window !== "undefined" ? window : globalThis).addEventListener("resize", resize);

  var pc = document.getElementById("pc"); if (pc) pc.onclick = function () { selectNode(null); kick(); };
  var pbody = document.getElementById("pbody");
  if (pbody) pbody.addEventListener("click", function (e) {
    var li = e.target.closest ? e.target.closest("li.rel") : null;
    if (!li) return;
    var key = li.getAttribute("data-key");
    if (key) focus(key);
  });
  var reset = document.getElementById("reset");
  if (reset) reset.onclick = function () {
    selectNode(null);
    S.expanded.clear();                         // 收起所有已展开供应商
    var q = document.getElementById("q"); if (q) q.value = "";
    document.getElementById("cbP").checked = document.getElementById("cbC").checked = document.getElementById("cbS").checked = true;
    var line = document.getElementById("line"); if (line) line.value = "";
    reheat(1); S.fitDone = false; fitView();   // 复位筛选并重新适配视口
  };
  var flowBtn = document.getElementById("flow");
  if (flowBtn) flowBtn.onclick = function () {
    S.flow = !S.flow;
    if (flowBtn.classList) flowBtn.classList.toggle("on", S.flow);
    if (S.running) kick(); else if (S.cv) draw(visibleSet());
  };
  (typeof document !== "undefined" ? document : globalThis).addEventListener("visibilitychange", function () {
    if (typeof document !== "undefined" && document.hidden) { S.running = false; }   // 后台标签页停止循环省电
    else { S.running = true; kick(); }
  });
  var fitBtn = document.getElementById("fit");
  if (fitBtn) fitBtn.onclick = function () { fitView(); };
  var insClose = document.getElementById("insightClose");
  if (insClose) insClose.onclick = function () {
    var c = document.getElementById("insightCard"); if (c) c.style.display = "none";
    S.criticalId = null; if (S.cv) draw(visibleSet());
  };
  var insToggle = document.getElementById("insightToggle");
  if (insToggle) insToggle.onclick = function () {
    var c = document.getElementById("insightCard");
    if (c && c.style.display === "block") { c.style.display = "none"; S.criticalId = null; if (S.cv) draw(visibleSet()); }
    else { showInsights(); }
  };
  ["q", "cbP", "cbC", "cbS", "line"].forEach(function (id) {
    var el = document.getElementById(id);
    if (el) el.addEventListener("input", function () { if (id !== "q") selectNode(null); reheat(0.7); });
  });
  document.addEventListener("i18n:ready", function () { if (S.selected) renderPanel(S.selected); if (insightVisible()) showInsights(); });
  document.addEventListener("i18n:changed", function () { if (S.selected) renderPanel(S.selected); if (insightVisible()) showInsights(); });
}

// 仅在需要重绘时启动 rAF 循环；模拟静止且无交互时循环自动停止，避免全屏 60fps 持续重绘。
export function kick() {
  if (!S.running || S.animating) return;
  S.animating = true;
  S.rafId = (typeof requestAnimationFrame !== "undefined" ? requestAnimationFrame(loop) : 0);
}
export function loop() {
  if (!S.running) { S.animating = false; return; }
  var vis = visibleSet();
  physics(vis);
  draw(vis);
  var settled = S.alpha < ALPHA_MIN && S.canvasReady;
  if (settled) {
    if (!S.fitDone) { S.fitDone = true; fitView(); }                     // 首屏布局稳定后自动适配视口一次
    if (!S.insightsShown) { S.insightsShown = true; showInsights(); }    // 静止后弹一次「关键洞察」浮层
  }
  // 流动开启 或 仍在物理运动中（或正在交互）→ 持续循环（粒子动画需不断重绘）；
  // 否则（已静止且关闭流动、无交互）→ 停止循环省电，行为与原版一致。
  if (S.flow || !settled || S.dragNode || S.panning) {
    S.rafId = (typeof requestAnimationFrame !== "undefined" ? requestAnimationFrame(loop) : 0);
  } else {
    S.animating = false;
  }
}
export function reheat(a) { S.alpha = Math.max(S.alpha, (a == null ? 0.5 : a)); kick(); }

export function applyFocus(n) {
  S.selected = n;
  var cbId = n.type === "Product" ? "cbP" : n.type === "Component" ? "cbC" : "cbS";
  var cb = document.getElementById(cbId);
  if (cb && !cb.checked) cb.checked = true;
  reheat(1);
  S.view.ox = W() / 2 - n.x * S.view.scale; S.view.oy = H() / 2 - n.y * S.view.scale;
  if (S.riskMode) { renderRiskPanel(n); showRiskPanel(true); }
  else {
    renderPanel(n);
    var panel = document.getElementById("panel"); if (panel) panel.style.display = "block";
  }
}
export function focus(key) {
  var n = S.idMap[key]; if (!n) return;
  if (!W() || !H()) { S.pendingFocus = n; return; }
  applyFocus(n);
}

// 将全部节点包围盒缩放到视口内并居中（首屏自动适配 / 「适配」按钮）。
// 边距随视口收缩：小屏留更少空白以放大节点，提升可读性/可点性。
export function fitView() {
  if (!S.nodes || !S.nodes.length || !W() || !H()) return;
  var minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (var i = 0; i < S.nodes.length; i++) {
    var n = S.nodes[i];
    if (n.x < minX) minX = n.x;
    if (n.x > maxX) maxX = n.x;
    if (n.y < minY) minY = n.y;
    if (n.y > maxY) maxY = n.y;
  }
  var bw = Math.max(maxX - minX, 1), bh = Math.max(maxY - minY, 1);
  var small = Math.min(W(), H()) < 560;
  var margin = Math.max(16, Math.min(W(), H()) * (small ? 0.05 : 0.10));
  var s = Math.min((W() - 2 * margin) / bw, (H() - 2 * margin) / bh);
  s = Math.max(0.05, Math.min(s, 6));
  S.view.scale = s;
  S.view.ox = W() / 2 - (minX + maxX) / 2 * s;
  S.view.oy = H() / 2 - (minY + maxY) / 2 * s;
  S.fitDone = true;
  kick();
}

// 产品线的展示名（与 build_viewer.LINE_ZH 对齐）
var LINE_DISPLAY = { iPhone: "iPhone", Mac: "Mac", iPad: "iPad", Wearable: "Apple Watch", Spatial: "Vision Pro", Audio: "AirPods", HomePod: "HomePod" };

// 从内联 SUPPLY_DATA 找出某零部件的（代表）供应商显示名
function compSupplierName(compId) {
  var data = (typeof window !== "undefined" ? window.SUPPLY_DATA : null);
  if (!data || !data.edges || !data.edges.supplied_by) return "";
  for (var i = 0; i < data.edges.supplied_by.length; i++) {
    if (data.edges.supplied_by[i].from === compId) {
      var sid = data.edges.supplied_by[i].to;
      var s = S.idMap["Supplier:" + sid];
      return s ? (s.english_name || s.name || sid) : sid;
    }
  }
  return "";
}

// 「关键洞察」浮层：图谱首屏静止后弹出一次，把大片静态空间变成可读结论，
// 并把最关键节点（单点依赖零部件，缺省取脆弱性最高者）高亮 + 常驻标签。
function insightVisible() { var c = document.getElementById("insightCard"); return !!(c && c.style.display === "block"); }
export function showInsights() {
  var card = document.getElementById("insightCard");
  if (!card) return;
  var prods = [], comps = [], supps = [];
  S.nodes.forEach(function (n) {
    if (n.type === "Product") prods.push(n);
    else if (n.type === "Component") comps.push(n);
    else supps.push(n);
  });
  var scaleEl = document.getElementById("insScale");
  if (scaleEl) scaleEl.textContent = prods.length + " " + i18nText("home.prod") + " · " + comps.length + " " + i18nText("home.part") + " · " + supps.length + " " + i18nText("home.supp");

  // 最脆弱产品线：按 product_line 聚合产品 vuln 取均值
  var lv = {};
  prods.forEach(function (p) {
    if (p.vuln == null || p.product_line == null) return;
    if (!lv[p.product_line]) lv[p.product_line] = { s: 0, n: 0 };
    lv[p.product_line].s += p.vuln; lv[p.product_line].n += 1;
  });
  var worstLine = null, worstV = -1;
  Object.keys(lv).forEach(function (k) { var v = lv[k].s / lv[k].n; if (v > worstV) { worstV = v; worstLine = k; } });
  var lineEl = document.getElementById("insLine");
  if (lineEl) lineEl.textContent = (LINE_DISPLAY[worstLine] || worstLine || "-") + (worstV >= 0 ? "（" + worstV.toFixed(2) + "）" : "");

  // 单点依赖 + 最关键节点
  var sp = comps.filter(function (c) { return c.single_point; });
  var crit = null;
  function pickMax(arr) { arr.forEach(function (c) { if (!crit || (c.vuln || 0) > (crit.vuln || 0)) crit = c; }); }
  pickMax(sp);
  if (!crit) pickMax(comps);   // 兜底：无单点依赖时取脆弱性最高零部件
  var spEl = document.getElementById("insSP");
  if (spEl) spEl.textContent = sp.length + " " + i18nText("home.insightSingleUnit");
  var focusEl = document.getElementById("insFocus");
  if (focusEl) {
    if (crit) {
      var sn = compSupplierName(crit.id);
      focusEl.textContent = label(crit) + (sn ? " → " + sn : "");
      focusEl.onclick = function () { focus(crit._key); };
    } else { focusEl.textContent = "-"; focusEl.onclick = null; }
  }
  S.criticalId = crit ? crit._key : null;
  card.style.display = "block";
  if (S.cv) draw(visibleSet());   // 立即绘制高亮环 + 常驻标签（静止态也可见）
}

export function start() {
  if (S.running) return;
  S.running = true; syncSize(); reheat(1);
}
export function stop() {
  S.running = false; S.animating = false;
  if (S.rafId && typeof cancelAnimationFrame !== "undefined") cancelAnimationFrame(S.rafId);
}
