// physics.js — 力导向布局（仅关心物理，依赖 S 状态与 W/H 尺寸，可独立测试）。
import { S, ALPHA_MIN, ALPHA_DEC } from "./state.js";
import { W, H } from "./util.js";

export function physics(vis) {
  if (S.alpha < ALPHA_MIN) return;
  var arr = S.nodes.filter(function (n) { return vis.has(n._key); });
  arr.forEach(function (n) { n.fx = 0; n.fy = 0; });
  for (var i = 0; i < arr.length; i++) for (var j = i + 1; j < arr.length; j++) {
    var a = arr[i], b = arr[j];
    var dx = a.x - b.x, dy = a.y - b.y;
    var d2 = dx * dx + dy * dy + 0.01, d = Math.sqrt(d2);
    var f = 1800 / d2, fx = dx / d * f, fy = dy / d * f;
    a.fx += fx; a.fy += fy; b.fx -= fx; b.fy -= fy;
  }
  S.links.forEach(function (l) {
    if (!vis.has(l.a._key) || !vis.has(l.b._key)) return;
    var dx = l.b.x - l.a.x, dy = l.b.y - l.a.y;
    var d = Math.sqrt(dx * dx + dy * dy) + 0.01;
    var f = (d - 90) * 0.03, fx = dx / d * f, fy = dy / d * f;
    l.a.fx += fx; l.a.fy += fy; l.b.fx -= fx; l.b.fy -= fy;
  });
  arr.forEach(function (n) {
    n.fx += (W() / 2 - n.x) * 0.001; n.fy += (H() / 2 - n.y) * 0.001;
    n.vx = (n.vx + n.fx * S.alpha) * 0.9; n.vy = (n.vy + n.fy * S.alpha) * 0.9;
    var sp = Math.hypot(n.vx, n.vy);
    if (sp > 18) { n.vx *= 18 / sp; n.vy *= 18 / sp; }
    if (!n.fixed) { n.x += n.vx; n.y += n.vy; }
  });
  S.alpha = Math.max(0, S.alpha - ALPHA_DEC);
}
