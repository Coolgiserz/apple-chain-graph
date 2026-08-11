// model.js — 数据装配与可见集计算（图结构视图的「模型」层，可独立于渲染/交互演进）。
import { S } from "./state.js";
import { W, H } from "./util.js";

function addNode(n, type) {
  var o = Object.assign({ type: type, degree: 0 }, n);
  o.id = n.id; o._key = type[0] + ":" + n.id;
  S.idMap[o._key] = o; S.nodes.push(o);
}
function addLink(t, from, to, extra) {
  var a = S.idMap["P:" + from] || S.idMap["C:" + from] || S.idMap["S:" + from] || S.idMap["L:" + from] || S.idMap["B:" + from];
  var b = S.idMap["P:" + to] || S.idMap["C:" + to] || S.idMap["S:" + to] || S.idMap["L:" + to] || S.idMap["B:" + to];
  if (a && b) { var l = { type: t, a: a, b: b }; if (extra) Object.assign(l, extra); S.links.push(l); a.degree++; b.degree++; }
}

export function build() {
  var DATA = window.SUPPLY_DATA;
  S.idMap = {}; S.nodes = []; S.links = [];
  DATA.nodes.products.forEach(function (p) { addNode(p, "Product"); });
  DATA.nodes.components.forEach(function (c) { addNode(c, "Component"); });
  DATA.nodes.suppliers.forEach(function (s) { addNode(s, "Supplier"); });
  // 产品线虚拟顶层节点（仅展示层聚合，不写入数据文件；与现有 3 节点/3 边 schema 解耦）。
  // 让默认视图呈「产品线 → 产品 → 零部件」三层结构，供应商默认隐藏、按需展开。
  var lineNames = Array.from(new Set(DATA.nodes.products.map(function (p) { return p.product_line; })));
  lineNames.forEach(function (ln) {
    var o = { type: "Line", id: "line:" + ln, line: ln, name: ln, english_name: ln, degree: 0 };
    o._key = "L:" + ln; S.idMap[o._key] = o; S.nodes.push(o);
  });
  DATA.edges.uses_component.forEach(function (e) { addLink("USES", e.from, e.to); });
  DATA.edges.supplied_by.forEach(function (e) { addLink("SUPPLIES", e.from, e.to, { share: e.share, note: e.note }); });
  DATA.edges.assembled_by.forEach(function (e) { addLink("ASSEMBLES", e.from, e.to); });
  // 生产基地层（研究中台新增）：ProductLine -[MANUFACTURED_AT]-> ProductionBase，
  // ProductionBase -[OPERATED_BY]-> Supplier。缺失时（如测试 fixture）安全跳过。
  if (DATA.nodes.bases && DATA.edges.manufactured_at && DATA.edges.operated_by) {
    DATA.nodes.bases.forEach(function (b) { addNode(b, "Base"); });
    DATA.edges.manufactured_at.forEach(function (e) { addLink("MANUFACTURED", e.from, e.to, { source: e.source, confidence: e.confidence }); });
    DATA.edges.operated_by.forEach(function (e) { addLink("OPERATED", e.from, e.to, { source: e.source }); });
  }
  // 产品线 → 产品 边（展示层聚合边，dir 同其它边一致：下游=产品）
  DATA.nodes.products.forEach(function (p) {
    var ln = S.idMap["L:" + p.product_line];
    if (ln) { S.links.push({ type: "LINE", a: ln, b: S.idMap["P:" + p.id] }); ln.degree++; }
  });
  // 每条边一个稳定随机相位，使流动粒子不必同步、更自然
  S.links.forEach(function (l) { l.phase = Math.random(); });
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

// 当前筛选/展开状态下可见的节点 key 集合（与图谱渲染、侧边表格共用同一逻辑）。
// 默认：仅显示 产品线(Line) → 产品(Product) → 零部件(Component)；供应商(Supplier)默认隐藏，
// 除非勾选「展开全部供应商」(cbS) 或所在 产品/零部件 已被展开(S.expanded)。
export function visibleSet() {
  // 「双击聚焦」拓扑隔离：仅显示该节点及其 1 跳邻居，覆盖其余筛选（含隐藏供应商/基地也一并露出）。
  // 让用户在密图上也能一眼看清「一个节点连着谁、连了多少个」。
  if (S.isolated) {
    var iso = new Set([S.isolated]);
    var adjIso = S.adj[S.isolated];
    if (adjIso) adjIso.forEach(function (e) { iso.add(e.other._key); });
    return iso;
  }
  var qel = document.getElementById("q"), q = qel ? qel.value.trim().toLowerCase() : "";
  var cbP = document.getElementById("cbP").checked,
      cbC = document.getElementById("cbC").checked;
  var line = document.getElementById("line").value;
  var set = new Set();
  for (var i = 0; i < S.nodes.length; i++) {
    var n = S.nodes[i];
    if (n.type === "Line") { if (!line || n.line === line) set.add(n._key); continue; }
    if (n.type === "Product") { if (!cbP) continue; if (line && n.product_line !== line) continue; set.add(n._key); continue; }
    if (n.type === "Component") { if (!cbC) continue; set.add(n._key); continue; }
    // Supplier：默认隐藏；「展开全部」(S.showAll) 则全显，否则仅显示与已展开节点相邻的供应商
    if (n.type === "Supplier") {
      if (S.showAll) { set.add(n._key); continue; }
      var adj = S.adj[n._key], shown = false;
      for (var s = 0; s < adj.length; s++) { if (S.expanded.has(adj[s].other._key)) { shown = true; break; } }
      if (shown) set.add(n._key);
      continue;
    }
    // ProductionBase：默认隐藏（与供应商一致）。出现条件：
    //   1) 「展开全部」(S.showAll) 或新增「生产基地」开关(S.showBases) 开启；
    //   2) 与已展开节点相邻（点击产品/零部件展开后可露出其运营基地）；
    //   3) 其运营商(Supplier)当前可见（点击供应商展开时可露出其运营基地）。
    // 搜索分支已覆盖「直接搜基地名」的场景。
    if (n.type === "Base") {
      if (S.showAll || S.showBases) { set.add(n._key); continue; }
      var adjB = S.adj[n._key], showB = false;
      for (var sb = 0; sb < adjB.length; sb++) {
        var ob = adjB[sb].other;
        if (S.expanded.has(ob._key)) { showB = true; break; }
        if (ob.type === "Supplier" && set.has(ob._key)) { showB = true; break; }
      }
      if (showB) set.add(n._key);
      continue;
    }
  }
  // 产品线聚焦：仅保留与已保留「产品」相邻的非产品节点（零部件/供应商随对应产品线收敛）
  if (line) {
    var keep = new Set(set);
    for (var j = 0; j < S.nodes.length; j++) {
      var m = S.nodes[j]; if (m.type === "Product" || m.type === "Line") continue;
      var es = S.adj[m._key], touch = false;
      for (var k = 0; k < es.length; k++) { if ((es[k].other.type === "Product" || es[k].other.type === "Line") && keep.has(es[k].other._key)) { touch = true; break; } }
      if (!touch) set.delete(m._key);
    }
  }
  // 搜索：跨全部节点匹配（隐藏供应商也能搜到），返回匹配项 + 其邻居，覆盖当前筛选
  if (q) {
    var match = new Set();
    for (var a = 0; a < S.nodes.length; a++) {
      var nn = S.nodes[a];
      var hay = (nn.name + " " + (nn.english_name || "") + " " + nn.id + " " + (nn.short_name || "") + " " + (nn.alias || "")).toLowerCase();
      if (hay.indexOf(q) !== -1) match.add(nn._key);
    }
    var out = new Set(match);
    match.forEach(function (key) {
      S.adj[key].forEach(function (e) { out.add(e.other._key); });
    });
    return out;
  }
  return set;
}

// 返回当前筛选条件下「可见」的节点对象数组（供首页侧边表格面板复用，实现「图 ↔ 表」联动）。
export function visibleNodes() {
  var set = visibleSet();
  return S.nodes.filter(function (n) { return set.has(n._key); });
}
