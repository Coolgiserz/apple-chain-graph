// render.js — Canvas 绘制（依赖 S 状态与工具函数；draw 在 pendingFocus 时回调 interaction.applyFocus）。
// 与 interaction.js 存在循环依赖（interaction 也用 draw/resize），但仅在函数运行时互相调用，esbuild 处理无误。
import { S } from "./state.js";
import { W, H, label, COLORS, nodeRadius, heatRing } from "./util.js";
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

// 节点「权重」归一化取值（0..1），用于红环强度；非权重模式返回 null。
// 瓶颈透视：按当前指标（pagerank / reach）归一化；风险视图：取脆弱性 vuln（本就 0..1）。
// 与「类型填充色」严格分离——权重只驱动红环，绝不占用填充通道，杜绝颜色撞车。
function weightOf(n) {
  if (S.bottleneckMode && S.metrics) {
    if (S.bottleneckMetric === "pagerank") {
      var prv = S.metrics.pagerank[n._key];
      var rgp = S.metrics.range.pagerank;
      return (prv != null && rgp.max > rgp.min) ? (prv - rgp.min) / (rgp.max - rgp.min) : 0;
    }
    var rv = S.metrics.info[n._key] ? S.metrics.info[n._key].reach : 0;
    var rgr = S.metrics.range.reach;
    return rgr.max > 0 ? rv / rgr.max : 0;
  }
  if (S.riskMode && n.vuln != null) return n.vuln;
  return null;
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
  // 选中集：默认 1 跳邻居；选中「供应商/零部件」时额外纳入第 2 跳下游产品，
  // 让「断供波及 N 款」在图谱上直接可见（消除「连的节点很少」的错觉）。
  var nb = null;
  if (sel) {
    var sn = S.idMap[sel];
    nb = new Set([sel]);
    if (sn && (sn.type === "Supplier" || sn.type === "Component")) {
      var compKeys = [];
      S.adj[sel].forEach(function (e) {
        nb.add(e.other._key);
        if (sn.type === "Supplier" && e.dir === "out" && e.link.type === "SUPPLIES") compKeys.push(e.other._key);
        if (sn.type === "Component" && e.dir === "in" && e.link.type === "USES") nb.add(e.other._key);
      });
      // 供应商 → 其供应零部件 → 使用这些零部件的产品（第 2 跳下游）
      compKeys.forEach(function (ck) {
        var es = S.adj[ck]; if (!es) return;
        es.forEach(function (e) { if (e.dir === "in" && e.link.type === "USES") nb.add(e.other._key); });
      });
    } else {
      S.adj[sel].forEach(function (e) { nb.add(e.other._key); });
    }
  }
  // 瓶颈模式下选中节点时，其下游受影响节点集合（feat 修复：让排行里的「波及N款」在图谱上可见）
  var focusSet = (S.bottleneckMode && S.bottleneckFocus) ? S.bottleneckFocus : null;
  var now = ((typeof window !== "undefined" && window.performance) ? window.performance.now() : Date.now()) / 1000;
  S.ctx.save(); S.ctx.translate(S.view.ox, S.view.oy); S.ctx.scale(S.view.scale, S.view.scale);
  S.links.forEach(function (l) {
    if (!vis.has(l.a._key) || !vis.has(l.b._key)) return;
    var inFocus = focusSet && focusSet.has(l.a._key) && focusSet.has(l.b._key);
    var hot = inFocus || (nb && nb.has(l.a._key) && nb.has(l.b._key));
    S.ctx.strokeStyle = inFocus ? "rgba(239,68,68,.75)" : (hot ? "rgba(150,180,255,.9)" : ((focusSet || nb) ? "rgba(120,135,170,.06)" : "rgba(120,135,170,.22)"));
    S.ctx.lineWidth = inFocus ? 1.8 : (hot ? 1.6 : 1);
    S.ctx.beginPath(); S.ctx.moveTo(l.a.x, l.a.y); S.ctx.lineTo(l.b.x, l.b.y); S.ctx.stroke();
  });
  drawParticles(vis, nb, now);                     // 流动粒子在边之上、节点之下
  S.nodes.forEach(function (n) {
    if (!vis.has(n._key)) return;
    var r = nodeRadius(n);
    var dim = (focusSet && !focusSet.has(n._key)) || (nb && !nb.has(n._key));
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
      // 关键度红环（与类型紫填充分离）
      var wtL = weightOf(n);
      if (wtL != null) {
        var hrL = heatRing(wtL);
        S.ctx.beginPath(); S.ctx.arc(n.x, n.y, Math.max(rw, rh) / 2 + 4, 0, Math.PI * 2);
        S.ctx.strokeStyle = hrL.color; S.ctx.lineWidth = hrL.width; S.ctx.stroke();
      }
      S.ctx.globalAlpha = dim ? 0.3 : 1;
      S.ctx.fillStyle = "#e9d5ff"; S.ctx.font = "bold 12px sans-serif";
      S.ctx.textAlign = "center"; S.ctx.textBaseline = "middle";
      S.ctx.fillText(label(n), n.x, n.y);
      S.ctx.textBaseline = "alphabetic";
      return;   // forEach 回调内用 return 跳过当前节点（Line 已绘制完毕）
    }
    // 生产基地（ProductionBase）：用方块区分于圆形的实体/供应商节点，颜色取 COLORS.Base（始终类型色）。
    if (n.type === "Base") {
      var rB = nodeRadius(n), hs = rB * 1.6;   // 方块半边长
      S.ctx.globalAlpha = dim ? 0.2 : 1;
      S.ctx.beginPath();
      S.ctx.rect(n.x - hs, n.y - hs, hs * 2, hs * 2);
      S.ctx.fillStyle = COLORS.Base;
      S.ctx.fill();
      // 关键度红环
      var wtB = weightOf(n);
      if (wtB != null) {
        var hrB = heatRing(wtB);
        S.ctx.beginPath(); S.ctx.rect(n.x - hs - 3, n.y - hs - 3, (hs + 3) * 2, (hs + 3) * 2);
        S.ctx.strokeStyle = hrB.color; S.ctx.lineWidth = hrB.width; S.ctx.stroke();
      }
      S.ctx.lineWidth = (S.selected === n) ? 3 : 1.2;
      S.ctx.strokeStyle = (S.selected === n) ? "#fff" : "rgba(255,255,255,.35)";
      S.ctx.stroke();
      // 单点依赖：琥珀环（任意模式都标，保证 nodeLegend 的 ⚠ 有对应）
      if (n.single_point) {
        S.ctx.beginPath(); S.ctx.rect(n.x - hs - 2, n.y - hs - 2, (hs + 2) * 2, (hs + 2) * 2);
        S.ctx.strokeStyle = "#fbbf24"; S.ctx.lineWidth = 2; S.ctx.stroke();
      }
      // 首屏关键洞察自动高亮：白色虚线环（区别于单点琥珀、关键度红）
      if (n._key === S.criticalId) {
        S.ctx.beginPath(); S.ctx.rect(n.x - hs - 5, n.y - hs - 5, (hs + 5) * 2, (hs + 5) * 2);
        S.ctx.setLineDash([4, 3]); S.ctx.strokeStyle = "rgba(255,255,255,.85)"; S.ctx.lineWidth = 1.5; S.ctx.stroke(); S.ctx.setLineDash([]);
      }
      if (S.view.scale > 0.7 || n.type === "Product" || n.type === "Line" || S.selected === n || S.hover === n || n._key === S.criticalId) {
        S.ctx.globalAlpha = dim ? 0.25 : 1;
        S.ctx.fillStyle = "#dfe7f7"; S.ctx.font = "11px sans-serif"; S.ctx.textAlign = "center";
        S.ctx.fillText(label(n), n.x, n.y + hs + 12);
      }
      S.ctx.globalAlpha = 1;
      return;   // Base 已绘制完毕
    }
    S.ctx.globalAlpha = dim ? 0.18 : 1;
    // 瓶颈详情点击：下游受影响节点用「洋红环」高亮（区别于关键度红环 + 选中白环）
    if (focusSet && focusSet.has(n._key) && n._key !== sel) {
      S.ctx.beginPath(); S.ctx.arc(n.x, n.y, r + 4, 0, Math.PI * 2);
      S.ctx.strokeStyle = "#22d3ee"; S.ctx.lineWidth = 2.5; S.ctx.stroke();
    }
    S.ctx.beginPath(); S.ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
    // 填充：始终为「节点类型色」——类型与权重用两个独立视觉通道，图例不再撞色。
    S.ctx.fillStyle = COLORS[n.type];
    S.ctx.fill();
    // 关键度 / 风险「热力红环」：权重唯一通道（t 越大越粗越红），不再占用填充色。
    var wt = weightOf(n);
    if (wt != null) {
      var hr = heatRing(wt);
      S.ctx.beginPath(); S.ctx.arc(n.x, n.y, r + hr.width / 2 + 1, 0, Math.PI * 2);
      S.ctx.strokeStyle = hr.color; S.ctx.lineWidth = hr.width; S.ctx.stroke();
    }
    // 选中：白色粗环（最外层，最醒目）
    if (S.selected === n) {
      S.ctx.beginPath(); S.ctx.arc(n.x, n.y, r + 6, 0, Math.PI * 2);
      S.ctx.strokeStyle = "#fff"; S.ctx.lineWidth = 3; S.ctx.stroke();
    }
    // 单点依赖：琥珀环（任意模式都标，保证 nodeLegend 的 ⚠ 有对应）
    if (n.single_point) {
      S.ctx.beginPath(); S.ctx.arc(n.x, n.y, r + 3, 0, Math.PI * 2);
      S.ctx.strokeStyle = "#fbbf24"; S.ctx.lineWidth = 2; S.ctx.stroke();
    }
    // 首屏「关键洞察」浮层自动高亮的最关键节点：白色虚线环（区别于单点琥珀、关键度红）
    if (n._key === S.criticalId) {
      S.ctx.beginPath(); S.ctx.arc(n.x, n.y, r + 8, 0, Math.PI * 2);
      S.ctx.setLineDash([4, 3]); S.ctx.strokeStyle = "rgba(255,255,255,.85)"; S.ctx.lineWidth = 1.5; S.ctx.stroke(); S.ctx.setLineDash([]);
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
