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

// 单击节点：产品/零部件「仅展开」其供应商子图（单调递增，绝不因再次单击而误收起）；
// 选中看信息始终发生，与展开结构解耦（P0-3）。收起改由面板按钮 / 重置 / 取消勾选完成。
function onNodeClick(n) {
  if (!n) { selectNode(null); return; }
  if ((n.type === "Product" || n.type === "Component") && !S.expanded.has(n._key)) {
    S.expanded.add(n._key); reheat(0.6); emitView();   // 展开会露出供应商 → 通知表格刷新（联动断点修复）
  }
  selectNode(n);
}

// 「展开全部/收起全部」按钮文案与高亮态随 S.showAll 同步（P0-2）。
function setSuppBtn() {
  var b = document.getElementById("cbS");
  if (!b) return;
  if (b.classList) b.classList.toggle("on", S.showAll);
  if (window.i18n && window.i18n.ready) b.textContent = i18nText(S.showAll ? "home.suppAllOn" : "home.suppAll");
}
// 「生产基地」开关文案随状态刷新（与 setSuppBtn 同构）
function setBaseBtn() {
  var b = document.getElementById("cbB");
  if (!b) return;
  if (b.classList) b.classList.toggle("on", S.showBases);
  if (window.i18n && window.i18n.ready) b.textContent = i18nText(S.showBases ? "home.basesAllOn" : "home.basesAll");
}

// 视图/筛选变化广播（供「企业表格」订阅刷新）。按钮（如 cbS 是 button）与程序化改值（reset/展开）
// 不会触发 input/change 事件，表格无法自动感知 —— 统一在此广播 sc:view 弥合联动断点。
function emitView() {
  try {
    if (typeof document !== "undefined" && document.dispatchEvent && typeof CustomEvent !== "undefined")
      document.dispatchEvent(new CustomEvent("sc:view"));
  } catch (e) { /* DOM 桩环境静默跳过（make test 安全） */ }
}
// 筛选/搜索变化时，仅当「当前选中节点已不可见」才清空选中（修复过度清空：例如选中某产品后，
// 仅切换「组件」勾选不该清掉仍可见的该产品面板）。
function maybeDropSelection() {
  if (S.selected && !visibleSet().has(S.selected._key)) selectNode(null);
}
var ZOOM_MIN = 0.1, ZOOM_MAX = 6;   // 缩放上下限（修复滚轮/pinch 可无限放大缩小的交互缺陷）

// 搜索框旁实时显示命中数（P1-7）。跨全部节点匹配，返回「匹配项」数（不含邻居）。
function updateSearchCount() {
  var qc = document.getElementById("qCount");
  if (!qc) return;
  var qel = document.getElementById("q");
  var q = qel ? qel.value.trim() : "";
  if (!q) { qc.textContent = ""; return; }
  var ql = q.toLowerCase(), n = 0;
  for (var i = 0; i < S.nodes.length; i++) {
    var m = S.nodes[i];
    var hay = (m.name + " " + (m.english_name || "") + " " + m.id + " " + (m.short_name || "") + " " + (m.alias || "")).toLowerCase();
    if (hay.indexOf(ql) !== -1) n++;
  }
  qc.textContent = n + " " + i18nText("home.results");
}

// 逐项展开 / 收起（与「选中看信息」解耦，P0-3/P0-2）。
function expandNode(key) { if (!S.expanded.has(key)) { S.expanded.add(key); reheat(0.6); emitView(); } selectNode(S.idMap[key]); }
function collapseNode(key) { if (S.expanded.has(key)) { S.expanded.delete(key); reheat(0.6); emitView(); } selectNode(S.idMap[key]); }

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
    S.view.scale *= factor;
    S.view.scale = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, S.view.scale));   // 缩放下限/上限
    S.view.ox = l.x - wx * S.view.scale; S.view.oy = l.y - wy * S.view.scale;
    kick();
  }, { passive: false });

  // 双击节点：拓扑隔离聚焦 —— 只渲染该节点及其 1 跳邻居（覆盖其余筛选），
  // 并适配到该子图，让用户在密图上也能看清「连着谁、连了多少」。再次双击同一节点退出。
  S.cv.addEventListener("dblclick", function (e) {
    var n = pick(e.clientX, e.clientY);
    if (!n) return;            // 双击空白处不处理（避免误清除聚焦）
    isolateToggle(n);
    kick();
  });

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
        S.view.scale = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, S.view.scale));   // 缩放下限/上限
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
  // 瓶颈透视面板的排行/关系行同样可点击聚焦（与 #pbody 同构）
  var bnBody = document.getElementById("bnBody");
  if (bnBody) bnBody.addEventListener("click", function (e) {
    var li = e.target.closest ? e.target.closest("li.rel") : null;
    if (!li) return;
    var key = li.getAttribute("data-key");
    if (key) focus(key);
  });
  var reset = document.getElementById("reset");
  if (reset) reset.onclick = function () {
    selectNode(null);
    // 退出风险/瓶颈视图：与筛选一起复位，避免「重置」后图谱仍按脆弱性着色、图例残留
    // （复用 graph_bootstrap 的 change 处理器，统一走 setRiskMode/setBottleneckMode + 隐藏图例）。
    ["riskToggle", "bnToggle"].forEach(function (id) {
      var t = document.getElementById(id);
      if (t && t.checked) { t.checked = false; try { t.dispatchEvent(new CustomEvent("change")); } catch (e) {} }
    });
    S.isolated = null; S.expanded.clear();      // 退出双击聚焦 + 收起所有已展开供应商
    S.showAll = false; setSuppBtn();            // 回到默认态：供应商隐藏（与首屏一致，P0-1/P0-2）
    S.showBases = false;                        // 回到默认态：生产基地隐藏
    var cbB = document.getElementById("cbB"); if (cbB) { cbB.checked = false; if (cbB.classList) cbB.classList.remove("on"); if (window.i18n && window.i18n.ready) cbB.textContent = i18nText("home.basesAll"); }
    var q = document.getElementById("q"); if (q) q.value = "";
    var qc = document.getElementById("qCount"); if (qc) qc.textContent = "";
    // 回到默认态：产品/零部件可见，供应商默认隐藏（与首屏默认一致，而非「全展开」）(P0-1)
    var cbP = document.getElementById("cbP"); if (cbP) cbP.checked = true;
    var cbC = document.getElementById("cbC"); if (cbC) cbC.checked = true;
    var line = document.getElementById("line"); if (line) line.value = "";
    updateIsoBanner();                          // 隐藏聚焦提示条
    emitView();                                 // 通知表格随筛选复位刷新
    reheat(1); S.fitDone = false; fitView();   // 复位筛选并重新适配视口
  };
  // 「展开全部 / 收起全部」独立按钮：与逐项展开解耦（P0-2）。
  // 开启=显示全部供应商；关闭=同时清除逐项展开（真正「收起全部」），但再次点击单个节点仍可单独展开。
  var cbS = document.getElementById("cbS");
  if (cbS) cbS.onclick = function () {
    S.showAll = !S.showAll;
    if (!S.showAll) S.expanded.clear();   // 收起全部 = 清除所有逐项展开
    setSuppBtn();
    maybeDropSelection(); emitView(); reheat(0.7);   // 仅当当前选中供应商变隐藏才清面板；并通知表格刷新
  };
  // 「生产基地」开关：显示/隐藏 ProductionBase 节点（与供应商同层，默认隐藏，按需展开）
  var cbB = document.getElementById("cbB");
  if (cbB) cbB.onclick = function () {
    S.showBases = !S.showBases;
    setBaseBtn();   // 同步高亮/文案（与 cbS 走 setSuppBtn 同构，避免重复 DOM 操作）
    if (S.running) kick(); else if (S.cv) draw(visibleSet());
  };
  (typeof document !== "undefined" ? document : globalThis).addEventListener("visibilitychange", function () {
    if (typeof document !== "undefined" && document.hidden) { S.running = false; }   // 后台标签页停止循环省电
    else { S.running = true; kick(); }
  });
  var fitBtn = document.getElementById("fit");
  if (fitBtn) fitBtn.onclick = function () { fitView(); };
  var isoExit = document.getElementById("isoExit");
  if (isoExit) isoExit.onclick = function () { exitIso(); };
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
  // 搜索框：实时显示命中数（P1-7），并随输入重算可见集
  var qel = document.getElementById("q");
  if (qel) qel.addEventListener("input", function () { updateSearchCount(); maybeDropSelection(); emitView(); reheat(0.7); });
  ["cbP", "cbC", "line"].forEach(function (id) {
    var el = document.getElementById(id);
    if (el) el.addEventListener("input", function () { maybeDropSelection(); emitView(); reheat(0.7); });
  });
  // 信息面板内的「展开/收起供应商」（逐项展开与选中解耦，P0-3/P0-2）
  var pbody = document.getElementById("pbody");
  if (pbody) pbody.addEventListener("click", function (e) {
    var b = e.target.closest ? e.target.closest(".expand-btn") : null;
    if (!b) return;
    var key = b.getAttribute("data-key");
    if (b.getAttribute("data-act") === "collapse") collapseNode(key); else expandNode(key);
  });
  document.addEventListener("i18n:ready", function () { if (S.selected) renderPanel(S.selected); if (insightVisible()) showInsights(); setSuppBtn(); setBaseBtn(); });
  document.addEventListener("i18n:changed", function () { if (S.selected) renderPanel(S.selected); if (insightVisible()) showInsights(); setSuppBtn(); setBaseBtn(); });
  // 首屏一次性引导卡：关闭后记忆，下次不再弹（P1 首屏引导）
  var guide = document.getElementById("guide");
  if (guide) {
    function closeGuide() {
      guide.style.display = "none";
      try { (typeof localStorage !== "undefined") && localStorage.setItem("sc_guide_done", "1"); } catch (e) {}
    }
    var gclose = document.getElementById("guideClose"); if (gclose) gclose.onclick = closeGuide;
    var gok = document.getElementById("guideOk"); if (gok) gok.onclick = closeGuide;
  }
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
  // 流动开启时持续重绘（粒子始终沿边流动，图谱「活着」而非冻结成静态圆点），
  // 关闭时才在静止后停机省电。拖拽/平移/物理未静止时也持续循环。
  if (!settled || S.dragNode || S.panning || S.flow) {
    S.rafId = (typeof requestAnimationFrame !== "undefined" ? requestAnimationFrame(loop) : 0);
  } else {
    S.animating = false;
  }
}
export function reheat(a) { S.alpha = Math.max(S.alpha, (a == null ? 0.5 : a)); kick(); }

// 聚焦前确保目标节点可见（P2 修复：此前聚焦隐藏供应商/被筛选排除的节点时，
// 相机居中但该节点不在 visibleSet 中、draw 不渲染，用户「选中了却找不到」）。
// 最小侵入：清除搜索/产品线筛选、开启对应类别开关、展开上游产品/零部件；
// 供应商极端无上游时兜底 showAll。修改后下一次 draw 即可见到该节点。
function ensureVisible(n) {
  if (visibleSet().has(n._key)) return;
  // 1) 搜索集会覆盖筛选并掩盖目标 → 清除搜索框
  var q = document.getElementById("q");
  if (q && q.value.trim()) { q.value = ""; var qc = document.getElementById("qCount"); if (qc) qc.textContent = ""; }
  // 2) 开启对应类别开关（供应商需其上游产品/零部件可见才能经 expanded 露出）
  if (n.type === "Product" || n.type === "Supplier") { var cbP = document.getElementById("cbP"); if (cbP && !cbP.checked) cbP.checked = true; }
  if (n.type === "Component" || n.type === "Supplier") { var cbC = document.getElementById("cbC"); if (cbC && !cbC.checked) cbC.checked = true; }
  // 3) 产品线筛选可能隐藏目标节点 → 清除
  var line = document.getElementById("line");
  if (line && line.value) line.value = "";
  // 4) 供应商：展开其相邻的上游产品/零部件（最小侵入，仅露出该供应商及其同级）
  if (n.type === "Supplier") {
    var adj = S.adj[n._key] || [];
    for (var i = 0; i < adj.length; i++) { var o = adj[i].other; if (o.type === "Product" || o.type === "Component") S.expanded.add(o._key); }
    if (!visibleSet().has(n._key)) { S.showAll = true; setSuppBtn(); }   // 兜底：无上游则全展开
  }
  // 5) 生产基地：开启「生产基地」开关即可见（无需展开上游）
  if (n.type === "Base") {
    S.showBases = true;
    setBaseBtn();   // 同步按钮高亮/文案（cbB 是 button，不能用 .checked）
  }
  emitView();   // 可见集可能已变（清除搜索/筛选/展开）→ 通知表格刷新
}

export function applyFocus(n) {
  ensureVisible(n);   // 先保证可见，再居中（P2）
  selectNode(n);   // 复用 selectNode：设置 S.selected + 右侧面板，并广播 sc:select（反向联动表格）
  // 同步顶部开关视觉态：复选框(cbP/cbC)用 .checked；按钮(cbS/cbB)用 setXxxBtn
  // （对 <button> 赋 .checked 无效，必须用 classList/textContent 同步，否则按钮与图谱状态脱节）
  if (n.type === "Base") setBaseBtn();
  else if (n.type === "Supplier" && S.showAll) setSuppBtn();
  var cbId = n.type === "Product" ? "cbP" : n.type === "Component" ? "cbC" : null;
  var cb = cbId ? document.getElementById(cbId) : null;
  if (cb && !cb.checked) cb.checked = true;
  reheat(1);
  S.view.ox = W() / 2 - n.x * S.view.scale; S.view.oy = H() / 2 - n.y * S.view.scale;
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

// 将视口适配到给定节点 key 集合（用于双击聚焦子图，而非全图）。
export function fitToKeys(keys) {
  if (!keys || !keys.size || !W() || !H()) return;
  var minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity, any = false;
  keys.forEach(function (k) {
    var n = S.idMap[k]; if (!n) return;
    any = true;
    if (n.x < minX) minX = n.x; if (n.x > maxX) maxX = n.x;
    if (n.y < minY) minY = n.y; if (n.y > maxY) maxY = n.y;
  });
  if (!any) return;
  var bw = Math.max(maxX - minX, 1), bh = Math.max(maxY - minY, 1);
  var small = Math.min(W(), H()) < 560;
  var margin = Math.max(24, Math.min(W(), H()) * (small ? 0.08 : 0.14));   // 子图留更多边距，节点更舒展
  var s = Math.min((W() - 2 * margin) / bw, (H() - 2 * margin) / bh);
  s = Math.max(0.1, Math.min(s, 6));
  S.view.scale = s;
  S.view.ox = W() / 2 - (minX + maxX) / 2 * s;
  S.view.oy = H() / 2 - (minY + maxY) / 2 * s;
  S.fitDone = true;
  kick();
}

// 双击聚焦切换：同一节点双击切换进入/退出；选中该节点让右侧面板列出邻居数量与名单。
export function isolateToggle(n) {
  if (S.isolated === n._key) {
    S.isolated = null;                          // 再次双击 → 退出聚焦，恢复常规视图
  } else {
    S.isolated = n._key;
    // 展开其上游（产品/零部件），使其供应商邻居在「常规视图」下也保持可见态一致（聚焦态本身已强显）
    if (n.type === "Product" || n.type === "Component") S.expanded.add(n._key);
  }
  selectNode(n);                                // 选中 → 面板列出该节点邻居（数量 + 名单）
  emitView();                                   // 通知侧边表格（visibleNodes 自动跟随聚焦态收敛）
  reheat(0.8);
  var iso = new Set([n._key]);
  (S.adj[n._key] || []).forEach(function (e) { iso.add(e.other._key); });
  updateIsoBanner();
  fitToKeys(iso);
}

// 聚焦提示条显隐 + 文案（节点名 + 邻居数 + 退出按钮）。
function updateIsoBanner() {
  var b = document.getElementById("isoBanner");
  if (!b) return;
  if (!S.isolated) { b.style.display = "none"; return; }
  var n = S.idMap[S.isolated];
  if (!n) { b.style.display = "none"; return; }
  var count = (S.adj[S.isolated] || []).length;
  var txt = i18nText("home.isoTitle").replace("{name}", label(n)).replace("{n}", count);
  var nameEl = document.getElementById("isoName");
  if (nameEl) nameEl.textContent = txt;
  b.style.display = "flex";
}
export function exitIso() {
  if (!S.isolated) return;
  S.isolated = null;
  selectNode(S.selected);                       // 仅清聚焦，保留选中
  updateIsoBanner();
  emitView(); reheat(0.6); if (S.cv) draw(visibleSet());
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
    var lineName = LINE_DISPLAY[worstLine] || worstLine || "-";
    if (crit) {
      var sn = compSupplierName(crit.id);
      // 可操作建议（P1）：点明最脆弱产品线 + 单点依赖数 + 建议优先关注的具体零部件（可点击聚焦）
      focusEl.textContent = lineName + i18nText("home.insightLineHas") + sp.length +
        i18nText("home.insightSingleFrag") + i18nText("home.insightAction") +
        label(crit) + (sn ? "（" + sn + "）" : "");
      focusEl.onclick = function () { focus(crit._key); };
    } else if (worstLine) {
      focusEl.textContent = lineName + i18nText("home.insightLineHas") + sp.length + i18nText("home.insightSingleFrag");
      focusEl.onclick = null;
    } else { focusEl.textContent = "-"; focusEl.onclick = null; }
  }
  S.criticalId = crit ? crit._key : null;
  card.style.display = "block";
  if (S.cv) draw(visibleSet());   // 立即绘制高亮环 + 常驻标签（静止态也可见）
}

export function start() {
  if (S.running) return;
  setSuppBtn();
  S.running = true; syncSize(); reheat(1);
  maybeShowGuide();
}

// 首屏一次性引导卡：未关闭过才显示（localStorage 记忆）。
function maybeShowGuide() {
  var guide = document.getElementById("guide");
  if (!guide) return;
  var done = false;
  try { done = (typeof localStorage !== "undefined") && localStorage.getItem("sc_guide_done") === "1"; } catch (e) {}
  if (!done) guide.style.display = "block";
}
export function stop() {
  S.running = false; S.animating = false;
  if (S.rafId && typeof cancelAnimationFrame !== "undefined") cancelAnimationFrame(S.rafId);
}
