// model.js — 数据装配与可见集计算（图结构视图的「模型」层，可独立于渲染/交互演进）。
import { S } from "./state.js";
import { W, H } from "./util.js";

function addNode(n, type) {
  var o = Object.assign({ type: type, degree: 0 }, n);
  o.id = n.id; o._key = type[0] + ":" + n.id;
  S.idMap[o._key] = o; S.nodes.push(o);
}
function addLink(t, from, to, extra) {
  var a = S.idMap["P:" + from] || S.idMap["C:" + from] || S.idMap["S:" + from];
  var b = S.idMap["P:" + to] || S.idMap["C:" + to] || S.idMap["S:" + to];
  if (a && b) { var l = { type: t, a: a, b: b }; if (extra) Object.assign(l, extra); S.links.push(l); a.degree++; b.degree++; }
}

export function build() {
  var DATA = window.SUPPLY_DATA;
  S.idMap = {}; S.nodes = []; S.links = [];
  DATA.nodes.products.forEach(function (p) { addNode(p, "Product"); });
  DATA.nodes.components.forEach(function (c) { addNode(c, "Component"); });
  DATA.nodes.suppliers.forEach(function (s) { addNode(s, "Supplier"); });
  DATA.edges.uses_component.forEach(function (e) { addLink("USES", e.from, e.to); });
  DATA.edges.supplied_by.forEach(function (e) { addLink("SUPPLIES", e.from, e.to, { share: e.share, note: e.note }); });
  DATA.edges.assembled_by.forEach(function (e) { addLink("ASSEMBLES", e.from, e.to); });
  S.adj = {}; S.nodes.forEach(function (n) { S.adj[n._key] = []; });
  S.links.forEach(function (l) {
    S.adj[l.a._key].push({ dir: "out", other: l.b, link: l });
    S.adj[l.b._key].push({ dir: "in", other: l.a, link: l });
  });
  // 初始环形布局
  S.nodes.forEach(function (n, i) {
    var ang = (i / S.nodes.length) * Math.PI * 2, r = 200 + (i % 7) * 40;
    n.x = W() / 2 + Math.cos(ang) * r + (Math.random() - 0.5) * 30;
    n.y = H() / 2 + Math.sin(ang) * r + (Math.random() - 0.5) * 30;
    n.vx = 0; n.vy = 0;
  });
  // 产品线下拉
  var lines = Array.from(new Set(DATA.nodes.products.map(function (p) { return p.product_line; })));
  var sel = document.getElementById("line");
  if (sel) lines.forEach(function (l) {
    var o = document.createElement("option"); o.value = l; o.textContent = l; sel.appendChild(o);
  });
}

// 当前筛选条件下可见的节点 key 集合（与图谱渲染、侧边表格共用同一逻辑）。
export function visibleSet() {
  var q = document.getElementById("q").value.trim().toLowerCase();
  var cbP = document.getElementById("cbP").checked,
      cbC = document.getElementById("cbC").checked,
      cbS = document.getElementById("cbS").checked;
  var line = document.getElementById("line").value;
  var set = new Set();
  for (var i = 0; i < S.nodes.length; i++) {
    var n = S.nodes[i];
    if (n.type === "Product" && !cbP) continue;
    if (n.type === "Component" && !cbC) continue;
    if (n.type === "Supplier" && !cbS) continue;
    if (n.type === "Product" && line && n.product_line !== line) continue;
    set.add(n._key);
  }
  if (line) {
    var keep = new Set(set);
    for (var j = 0; j < S.nodes.length; j++) {
      var m = S.nodes[j]; if (m.type === "Product") continue;
      var touch = false;
      var es = S.adj[m._key];
      for (var k = 0; k < es.length; k++) { if (keep.has(es[k].other._key)) { touch = true; break; } }
      if (!touch) set.delete(m._key);
    }
  }
  if (q) {
    var match = new Set();
    for (var a = 0; a < S.nodes.length; a++) {
      var nn = S.nodes[a];
      if (!set.has(nn._key)) continue;
      var hay = (nn.name + " " + (nn.english_name || "") + " " + nn.id + " " + (nn.short_name || "") + " " + (nn.alias || "")).toLowerCase();
      if (hay.indexOf(q) !== -1) match.add(nn._key);
    }
    var keep2 = new Set(match);
    match.forEach(function (key) {
      S.adj[key].forEach(function (e) { keep2.add(e.other._key); });
    });
    return keep2;
  }
  return set;
}

// 返回当前筛选条件下「可见」的节点对象数组（供首页侧边表格面板复用，实现「图 ↔ 表」联动）。
export function visibleNodes() {
  var set = visibleSet();
  return S.nodes.filter(function (n) { return set.has(n._key); });
}
