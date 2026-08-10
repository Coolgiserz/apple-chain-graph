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

export function draw(vis) {
  syncSize();                                      // 每次绘制前保证后备尺寸正确（首屏布局晚到 / 窗口缩放自愈）
  if (S.pendingFocus && W() && H()) { var nf = S.pendingFocus; S.pendingFocus = null; applyFocus(nf); }
  S.ctx.clearRect(0, 0, W(), H());
  var sel = S.selected ? S.selected._key : null;
  var nb = sel ? new Set([sel].concat(S.adj[sel].map(function (e) { return e.other._key; }))) : null;
  S.ctx.save(); S.ctx.translate(S.view.ox, S.view.oy); S.ctx.scale(S.view.scale, S.view.scale);
  S.links.forEach(function (l) {
    if (!vis.has(l.a._key) || !vis.has(l.b._key)) return;
    var hot = nb && nb.has(l.a._key) && nb.has(l.b._key);
    S.ctx.strokeStyle = hot ? "rgba(150,180,255,.9)" : (nb ? "rgba(120,135,170,.08)" : "rgba(120,135,170,.22)");
    S.ctx.lineWidth = hot ? 1.6 : 1;
    S.ctx.beginPath(); S.ctx.moveTo(l.a.x, l.a.y); S.ctx.lineTo(l.b.x, l.b.y); S.ctx.stroke();
  });
  S.nodes.forEach(function (n) {
    if (!vis.has(n._key)) return;
    var r = nodeRadius(n);
    var dim = nb && !nb.has(n._key);
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
    if (S.view.scale > 0.7 || n.type === "Product" || S.selected === n || S.hover === n) {
      S.ctx.globalAlpha = dim ? 0.25 : 1;
      S.ctx.fillStyle = "#dfe7f7"; S.ctx.font = "11px sans-serif"; S.ctx.textAlign = "center";
      S.ctx.fillText(label(n), n.x, n.y + r + 12);
    }
    S.ctx.globalAlpha = 1;
  });
  S.ctx.restore();
}
