// interaction.js — 鼠标/触摸交互、聚焦深链、动画循环（「交互」模块，可独立演进）。
import { S, ALPHA_MIN } from "./state.js";
import { W, H, esc, BASE_R } from "./util.js";
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
    var r = BASE_R[n.type] + Math.min(n.degree, 12) * 0.35 + 4;
    if (d < r * r && d < bd) { best = n; bd = d; }
  }
  return best;
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
    if (wasClick) selectNode(S.downNode || null);
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
    if (wasClick) selectNode(S.downNode || null);
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
    S.view = { ox: 0, oy: 0, scale: 1 }; selectNode(null);
    var q = document.getElementById("q"); if (q) q.value = "";
    document.getElementById("cbP").checked = document.getElementById("cbC").checked = document.getElementById("cbS").checked = true;
    var line = document.getElementById("line"); if (line) line.value = "";
    reheat(1);
  };
  ["q", "cbP", "cbC", "cbS", "line"].forEach(function (id) {
    var el = document.getElementById(id);
    if (el) el.addEventListener("input", function () { if (id !== "q") selectNode(null); reheat(0.7); });
  });
  document.addEventListener("i18n:ready", function () { if (S.selected) renderPanel(S.selected); });
  document.addEventListener("i18n:changed", function () { if (S.selected) renderPanel(S.selected); });
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
  if (S.alpha < ALPHA_MIN && !S.dragNode && !S.panning && S.canvasReady) {
    S.animating = false;
    return;
  }
  S.rafId = (typeof requestAnimationFrame !== "undefined" ? requestAnimationFrame(loop) : 0);
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

export function start() {
  if (S.running) return;
  S.running = true; syncSize(); reheat(1);
}
export function stop() {
  S.running = false; S.animating = false;
  if (S.rafId && typeof cancelAnimationFrame !== "undefined") cancelAnimationFrame(S.rafId);
}
