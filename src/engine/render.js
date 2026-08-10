// render.js — Canvas 绘制（依赖 S 状态与工具函数；draw 在 pendingFocus 时回调 interaction.applyFocus）。
// 与 interaction.js 存在循环依赖（interaction 也用 draw/resize），但仅在函数运行时互相调用，esbuild 处理无误。
import { S } from "./state.js";
import { W, H, label, vulnColor, COLORS, nodeRadius } from "./util.js";
import { applyFocus, kick } from "./interaction.js";
import { visibleSet } from "./model.js";

// 同步画布后备尺寸与元素实际 CSS 尺寸；尺寸无变化或布局未就绪时跳过。返回 true 表示本次确实改变了尺寸。
export function syncSize() {
  if (!S.cv) return false;
  var dpr = (typeof window !== "undefined" && window.devicePixelRatio) || 1;
  var w = S.cv.clientWidth || (S.cv.parentNode && S.cv.parentNode.clientWidth) || (typeof window !== "undefined" && window.innerWidth);
  var h = S.cv.clientHeight || (S.cv.parentNode && S.cv.parentNode.clientHeight) || (typeof window !== "undefined" && window.innerHeight);
  if (!w || !h) return false;                       // 布局尚未就绪：保持原样，等下一帧自愈
  var bw = Math.round(w * dpr), bh = Math.round(h * dpr);
  if (S.cv.width === bw && S.cv.height === bh) return false;
  S.cv.width = bw; S.cv.height = bh;
  S.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  S.canvasReady = true;
  return true;
}

export function resize() {
  var changed = syncSize();
  if (S.running) kick();                              // 尺寸变化后重启循环（或借已有循环重绘）
  else if (changed) draw(visibleSet());              // 已停止时至少重绘一次当前帧
}

// 某 产品/零部件 是否还有「隐藏的供应商」（用于画可展开 + 提示）
function hasHiddenSuppliers(n, vis) {
  var es = S.adj[n._key];
  for (var i = 0; i < es.length; i++) {
    var o = es[i].other;
    if (o.type === "Supplier" && !vis.has(o._key)) return true;
  }
  return false;
}

// 沿可见边绘制流动粒子：方向统一为 link.b → link.a（供应商 → 零部件 → 产品 → 产品线，
// 表现供应链的「流动」），让图谱始终「活着」而非冻结成静态圆点。
// 克制（P1-5）：默认（无选中）仅极轻全局脉动——粒子更小/更慢/更淡；仅选中/悬停的子图流动更亮。
// 低端/小屏按设备降采样粒子数（P2 性能）。
function drawParticles(vis, nb, now) {
  if (!S.flow) return;
  var small = Math.min(W(), H()) < 560;
  var hasSel = !!S.selected;
  S.links.forEach(function (l) {
    if (!vis.has(l.a._key) || !vis.has(l.b._key)) return;
    var inSel = !nb || (nb.has(l.a._key) && nb.has(l.b._key));
    if (hasSel && !inSel) return;                  // 选中时仅高亮子图粒子，其余保持静态线
    var fx = l.b.x, fy = l.b.y, dx = l.a.x - fx, dy = l.a.y - fy;
    // 默认态：极轻脉动；选中子图：更亮更快
    var speed = hasSel ? 0.30 : 0.10;
    var np = (small ? 1 : (hasSel ? 2 : 1));
    var rad = hasSel ? 2.6 : 1.2;
    var alpha = hasSel ? 0.95 : 0.16;
    var col = hasSel ? "140,210,255" : "120,180,235";
    for (var p = 0; p < np; p++) {
      var phase = (now * speed + (l.phase || 0) + p / np) % 1;
      var x = fx + dx * phase, y = fy + dy * phase;
      S.ctx.beginPath();
      S.ctx.arc(x, y, rad, 0, Math.PI * 2);
      S.ctx.fillStyle = "rgba(" + col + "," + alpha + ")";
      S.ctx.fill();
    }
  });
}

export function draw(vis) {
  syncSize();                                      // 每次绘制前保证后备尺寸正确（首屏布局晚到 / 窗口缩放自愈）
  if (S.pendingFocus && W() && H()) { var nf = S.pendingFocus; S.pendingFocus = null; applyFocus(nf); }
  S.ctx.clearRect(0, 0, W(), H());
  var sel = S.selected ? S.selected._key : null;
  var nb = sel ? new Set([sel].concat(S.adj[sel].map(function (e) { return e.other._key; }))) : null;
  var now = ((typeof window !== "undefined" && window.performance) ? window.performance.now() : Date.now()) / 1000;
  S.ctx.save(); S.ctx.translate(S.view.ox, S.view.oy); S.ctx.scale(S.view.scale, S.view.scale);
  S.links.forEach(function (l) {
    if (!vis.has(l.a._key) || !vis.has(l.b._key)) return;
    var hot = nb && nb.has(l.a._key) && nb.has(l.b._key);
    S.ctx.strokeStyle = hot ? "rgba(150,180,255,.9)" : (nb ? "rgba(120,135,170,.08)" : "rgba(120,135,170,.22)");
    S.ctx.lineWidth = hot ? 1.6 : 1;
    S.ctx.beginPath(); S.ctx.moveTo(l.a.x, l.a.y); S.ctx.lineTo(l.b.x, l.b.y); S.ctx.stroke();
  });
  drawParticles(vis, nb, now);                     // 流动粒子在边之上、节点之下
  S.nodes.forEach(function (n) {
    if (!vis.has(n._key)) return;
    var r = nodeRadius(n);
    var dim = nb && !nb.has(n._key);
    // 产品线「聚合/分类」节点：用圆角矩形 + 虚线环区分「实体」实心圆（P1-6），避免被误认为真实供应链一环。
    if (n.type === "Line") {
      var rw = r * 2.6, rh = r * 1.5, x0 = n.x - rw / 2, y0 = n.y - rh / 2, rr = rh / 2;
      S.ctx.globalAlpha = dim ? 0.25 : 1;
      S.ctx.beginPath();
      S.ctx.moveTo(x0 + rr, y0);
      S.ctx.arcTo(x0 + rw, y0, x0 + rw, y0 + rh, rr);
      S.ctx.arcTo(x0 + rw, y0 + rh, x0, y0 + rh, rr);
      S.ctx.arcTo(x0, y0 + rh, x0, y0, rr);
      S.ctx.arcTo(x0, y0, x0 + rw, y0, rr);
      S.ctx.closePath();
      S.ctx.fillStyle = "rgba(139,92,246,0.14)";
      S.ctx.fill();
      S.ctx.setLineDash([5, 4]);
      S.ctx.lineWidth = (S.selected === n) ? 3 : 1.6;
      S.ctx.strokeStyle = (S.selected === n) ? "#fff" : "#8b5cf6";
      S.ctx.stroke();
      S.ctx.setLineDash([]);
      S.ctx.globalAlpha = dim ? 0.3 : 1;
      S.ctx.fillStyle = "#e9d5ff"; S.ctx.font = "bold 12px sans-serif";
      S.ctx.textAlign = "center"; S.ctx.textBaseline = "middle";
      S.ctx.fillText(label(n), n.x, n.y);
      S.ctx.textBaseline = "alphabetic";
      return;   // forEach 回调内用 return 跳过当前节点（Line 已绘制完毕）
    }
    S.ctx.globalAlpha = dim ? 0.18 : 1;
    S.ctx.beginPath(); S.ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
    // 风险视图：组件/产品节点按脆弱性着色（供应商节点保持原类型色）
    S.ctx.fillStyle = (S.riskMode && n.type !== "Supplier" && n.vuln != null) ? vulnColor(n.vuln) : COLORS[n.type];
    S.ctx.fill();
    S.ctx.lineWidth = (S.selected === n) ? 3 : 1.2;
    S.ctx.strokeStyle = (S.selected === n) ? "#fff" : "rgba(255,255,255,.35)";
    S.ctx.stroke();
    // 风险视图：单点依赖组件加红色警示外圈
    if (S.riskMode && n.type === "Component" && n.single_point) {
      S.ctx.beginPath(); S.ctx.arc(n.x, n.y, r + 3, 0, Math.PI * 2);
      S.ctx.strokeStyle = "#ef4444"; S.ctx.lineWidth = 2; S.ctx.stroke();
    }
    // 首屏「关键洞察」浮层自动高亮的最关键节点（琥珀环，静止态也可见，非动画）
    if (n._key === S.criticalId) {
      S.ctx.beginPath(); S.ctx.arc(n.x, n.y, r + 6, 0, Math.PI * 2);
      S.ctx.strokeStyle = "#fbbf24"; S.ctx.lineWidth = 2.5; S.ctx.stroke();
    }
    // 可展开提示：产品/零部件存在隐藏供应商时，右上角画绿色「+」
    if ((n.type === "Product" || n.type === "Component") && hasHiddenSuppliers(n, vis)) {
      S.ctx.globalAlpha = 1;
      S.ctx.fillStyle = "#10b981"; S.ctx.font = "bold 13px sans-serif"; S.ctx.textAlign = "center";
      S.ctx.fillText("+", n.x + r + 6, n.y - r + 4);
    }
    if (S.view.scale > 0.7 || n.type === "Product" || n.type === "Line" || S.selected === n || S.hover === n || n._key === S.criticalId) {
      S.ctx.globalAlpha = dim ? 0.25 : 1;
      S.ctx.fillStyle = "#dfe7f7"; S.ctx.font = "11px sans-serif"; S.ctx.textAlign = "center";
      S.ctx.fillText(label(n), n.x, n.y + r + 12);
    }
    S.ctx.globalAlpha = 1;
  });
  S.ctx.restore();
}
