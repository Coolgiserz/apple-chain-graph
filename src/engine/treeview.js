// treeview.js — 第三种视图「供应链树状视图」（与网络结构视图、企业表格视图并列）。
//
// 结构：Apple（根）→ 产品线(Line) → 产品(Product) → 零部件(Component，叶子)。
// 点击叶子零部件，在「不覆盖树」的独立详情栏（右侧）列出该零部件关联的供应商与生产基地，
// 详情栏支持跨列表搜索与按国家/地区筛选，便于在密集供应链里快速定位。
//
// 数据全部来自 window.SUPPLY_DATA（与引擎同源），不依赖 S/idMap——自包含、便于演进。
// 关系派生：
//   - 供应商：supplied_by 边（from=零部件 → to=供应商），直接可得。
//   - 生产基地：零部件 → 使用它的产品（uses_component 反向）→ 产品所属产品线
//     → 该线路的制造基地（manufactured_at：from=线路名 → to=基地），为传递关联（已在 UI 标注）。
import { esc, label, i18nText, i18nVal, nm, COLORS } from "./util.js";

var built = false;
var refs = {};                 // 缓存的 DOM 引用
var idx = {};                  // 数据索引
var currentCompId = null;      // 当前选中的零部件（i18n 切换时保留重渲染）
var detailState = { search: "", supCountry: "", baseCountry: "" };

function D() { return (typeof window !== "undefined") ? window.SUPPLY_DATA : null; }
function ready() { return !!D(); }

// —— 数据索引：一次构建，供树与详情反复查询 ——
function buildIndexes() {
  var data = D();
  idx.compById = {}; (data.nodes.components || []).forEach(function (c) { idx.compById[c.id] = c; });
  idx.supById = {}; (data.nodes.suppliers || []).forEach(function (s) { idx.supById[s.id] = s; });
  idx.baseById = {}; (data.nodes.bases || []).forEach(function (b) { idx.baseById[b.id] = b; });
  idx.prodById = {}; (data.nodes.products || []).forEach(function (p) { idx.prodById[p.id] = p; });
  // uses_component: from=产品 → to=零部件
  idx.compsByProduct = {};
  idx.productsByComp = {};
  data.edges.uses_component.forEach(function (e) {
    (idx.compsByProduct[e.from] = idx.compsByProduct[e.from] || []).push(e.to);
    (idx.productsByComp[e.to] = idx.productsByComp[e.to] || []).push(e.from);
  });
  // supplied_by: from=零部件 → to=供应商（含份额/备注/来源）
  idx.suppEdgesByComp = {};
  data.edges.supplied_by.forEach(function (e) {
    (idx.suppEdgesByComp[e.from] = idx.suppEdgesByComp[e.from] || []).push(e);
  });
  // manufactured_at: from=产品线名 → to=基地
  idx.basesByLine = {};
  (data.edges.manufactured_at || []).forEach(function (e) {
    (idx.basesByLine[e.from] = idx.basesByLine[e.from] || []).push(e.to);
  });
  // 产品线 → 产品 分组
  idx.lines = {};
  data.nodes.products.forEach(function (p) { (idx.lines[p.product_line] = idx.lines[p.product_line] || []).push(p); });
}

// —— 树渲染：一次性生成完整 DOM，折叠靠 CSS class，避免反复重渲 ——
function dotClass(kind) {
  return kind === "line" ? "line" : kind === "product" ? "prod" : "part";
}
function rowHTML(kind, id, text, caret, depth) {
  var pad = 10 + depth * 18;
  var c = caret ? "<span class='tcaret'>▾</span>" : "<span class='tcaret spacer'></span>";
  return "<div class='trow' data-kind='" + kind + "' data-id='" + esc(id) + "' style='padding-left:" + pad + "px'>" +
    c + "<span class='tdot " + dotClass(kind) + "'></span>" +
    "<span class='tname'>" + esc(text) + "</span></div>";
}
function branchHTML(kind, id, text, depth, childHTML) {
  return "<div class='tnode branch' data-kind='" + kind + "' data-id='" + esc(id) + "'>" +
    rowHTML(kind, id, text, true, depth) +
    "<div class='tchildren'>" + (childHTML || "") + "</div></div>";
}
function leafHTML(id, text, depth) {
  return "<div class='tnode leaf' data-kind='component' data-id='" + esc(id) + "'>" +
    rowHTML("component", id, text, false, depth) + "</div>";
}
function buildTreeHTML() {
  var linesHTML = "";
  Object.keys(idx.lines).forEach(function (line) {
    var productsHTML = "";
    idx.lines[line].forEach(function (p) {
      var compsHTML = "";
      (idx.compsByProduct[p.id] || []).forEach(function (cid) {
        compsHTML += leafHTML(cid, label(idx.compById[cid]), 3);
      });
      productsHTML += branchHTML("product", p.id, label(p), 2, compsHTML);
    });
    linesHTML += branchHTML("line", line, line, 1, productsHTML);
  });
  return branchHTML("root", "apple", i18nText("home.treeRoot"), 0, linesHTML);
}

function renderTree() {
  var pane = refs.treePane;
  if (!pane) return;
  pane.innerHTML = buildTreeHTML();
}

// —— 详情栏：供应商 + 生产基地，含搜索/筛选 ——
function uniq(arr) {
  var seen = {}, out = [];
  arr.forEach(function (v) { if (v && !seen[v]) { seen[v] = 1; out.push(v); } });
  return out;
}
function countryFilter(id, countries, selected) {
  if (!countries.length) return "";
  var h = "<select id='" + id + "' class='td-filter'>" +
    "<option value=''>" + esc(i18nText("home.all")) + "</option>";
  countries.forEach(function (c) {
    h += "<option value='" + esc(c) + "'" + (c === selected ? " selected" : "") + ">" +
      esc(i18nVal("country", c)) + "</option>";
  });
  return h + "</select>";
}
function srcLinks(ids) {
  if (!ids || !ids.length) return "";
  var reg = (D() && D().meta && D().meta.source_registry) || {};
  var html = "";
  ids.forEach(function (sid) {
    var m = reg[sid];
    if (m && m.url) html += "<a class='td-src' href='" + esc(m.url) + "' target='_blank' rel='noopener' onclick='event.stopPropagation()'>" + esc(m.publisher || sid) + "</a>";
  });
  return html ? "<div class='td-srcs'>" + html + "</div>" : "";
}
function supRow(x) {
  var s = x.s;
  var h = "<li class='td-item'>";
  h += "<div class='td-item-main'><span class='td-item-name'>" + esc(label(s)) + "</span>";
  if (x.share) h += " <span class='td-chip'>" + esc(i18nText("field.share")) + " " + esc(String(x.share)) + "%</span>";
  h += "</div>";
  var meta = [];
  if (s.country) meta.push(esc(i18nVal("country", s.country)));
  if (s.tier) meta.push(esc(i18nVal("tier", s.tier)));
  if (s.category) meta.push(esc(i18nVal("category", s.category)));
  if (meta.length) h += "<div class='td-item-meta'>" + meta.join(" · ") + "</div>";
  h += srcLinks(x.source);
  h += "</li>";
  return h;
}
function baseRow(b) {
  var h = "<li class='td-item'>";
  h += "<div class='td-item-main'><span class='td-item-name'>" + esc(b.name) + "</span>";
  var conf = b.confidence;
  if (conf) {
    var ccol = conf === "high" ? "#10b981" : conf === "medium" ? "#f59e0b" : "#ef4444";
    h += " <span class='td-chip' style='color:" + ccol + ";border-color:" + ccol + "'>" + esc(i18nText("field.confidence")) + ": " + esc(conf) + "</span>";
  }
  h += "</div>";
  var meta = [];
  if (b.city) meta.push(esc(b.city));
  if (b.province) meta.push(esc(b.province));
  if (b.country) meta.push(esc(i18nVal("country", b.country)));
  if (b.operator) { var op = idx.supById[b.operator]; meta.push(esc(i18nText("field.operator")) + ": " + esc(op ? label(op) : b.operator)); }
  if (meta.length) h += "<div class='td-item-meta'>" + meta.join(" · ") + "</div>";
  h += srcLinks(b.sources);
  h += "</li>";
  return h;
}

function renderDetail(compId) {
  var detail = refs.treeDetail;
  if (!detail) return;
  var comp = idx.compById[compId];
  if (!comp) return;
  // 供应商（直接）
  var suppEdges = idx.suppEdgesByComp[compId] || [];
  var suppliers = suppEdges.map(function (e) {
    return { s: idx.supById[e.to], share: e.share, note: e.note, source: e.source };
  }).filter(function (x) { return x.s; });
  // 生产基地（传递：产品 → 产品线 → 制造基地）
  var prodIds = idx.productsByComp[compId] || [];
  var lineSet = {};
  prodIds.forEach(function (pid) { var p = idx.prodById[pid]; if (p) lineSet[p.product_line] = true; });
  var baseSet = {};
  Object.keys(lineSet).forEach(function (ln) {
    (idx.basesByLine[ln] || []).forEach(function (bid) { baseSet[bid] = true; });
  });
  var bases = Object.keys(baseSet).map(function (bid) { return idx.baseById[bid]; }).filter(Boolean);

  var h = "";
  h += "<div class='td-header'>";
  h += "<div class='td-htitle'>" + esc(i18nText("home.detailTitle")) + "</div>";
  h += "<div class='td-comp'>" + esc(label(comp)) +
    (comp.english_name && comp.english_name !== label(comp) ? " <span class='td-en'>" + esc(comp.english_name) + "</span>" : "") + "</div>";
  var sub = [];
  if (comp.category) sub.push(esc(i18nVal("category", comp.category)));
  if (comp.subcategory) sub.push(esc(i18nVal("subcategory", comp.subcategory)));
  if (sub.length) h += "<div class='td-sub'>" + sub.join(" · ") + "</div>";
  h += "<button class='td-close' data-act='close' title='" + esc(i18nText("home.detailClose")) + "'>×</button>";
  h += "</div>";
  h += "<div class='td-meta'>" + esc(i18nText("home.detailUsedBy").replace("{n}", prodIds.length)) + "</div>";
  h += "<div class='td-search'><input type='search' id='tdSearch' placeholder='" + esc(i18nText("home.search")) + "' value='" + esc(detailState.search) + "'></div>";

  var supCountries = uniq(suppliers.map(function (x) { return x.s.country; }).filter(Boolean));
  h += "<div class='td-sec'><div class='td-sec-h'><span>" + esc(i18nText("home.supp")) + " (" + suppliers.length + ")</span>" +
    countryFilter("tdSupCountry", supCountries, detailState.supCountry) + "</div>" +
    "<ul class='td-list' id='tdSupList'></ul></div>";

  var baseCountries = uniq(bases.map(function (b) { return b.country; }).filter(Boolean));
  h += "<div class='td-sec'><div class='td-sec-h'><span>" + esc(i18nText("home.base")) + " (" + bases.length + ")</span>" +
    countryFilter("tdBaseCountry", baseCountries, detailState.baseCountry) + "</div>" +
    "<ul class='td-list' id='tdBaseList'></ul></div>";

  detail.innerHTML = h;
  detail._suppliers = suppliers;
  detail._bases = bases;
  renderDetailRows();

  var search = document.getElementById("tdSearch");
  if (search) search.addEventListener("input", function () { detailState.search = search.value; renderDetailRows(); });
  var sc = document.getElementById("tdSupCountry");
  if (sc) sc.addEventListener("change", function () { detailState.supCountry = sc.value; renderDetailRows(); });
  var bc = document.getElementById("tdBaseCountry");
  if (bc) bc.addEventListener("change", function () { detailState.baseCountry = bc.value; renderDetailRows(); });
  var close = detail.querySelector(".td-close");
  if (close) close.addEventListener("click", clearDetail);
}

function renderDetailRows() {
  var detail = refs.treeDetail; if (!detail) return;
  var sup = detail._suppliers || [], bases = detail._bases || [];
  var q = detailState.search.trim().toLowerCase();
  function hay(o, name) {
    if (!q) return true;
    var extra = o.s ? ((o.s.country || "") + " " + (o.s.category || "") + " " + (o.s.tier || ""))
      : ((o.city || "") + " " + (o.province || "") + " " + (o.country || "") + " " + (o.operator || ""));
    return (name + " " + extra).toLowerCase().indexOf(q) !== -1;
  }
  var supList = document.getElementById("tdSupList");
  if (supList) {
    var sf = sup.filter(function (x) {
      if (detailState.supCountry && (x.s.country || "") !== detailState.supCountry) return false;
      return hay(x, label(x.s));
    });
    if (!sup.length) supList.innerHTML = "<li class='td-empty'>" + esc(i18nText("home.detailEmptySup")) + "</li>";
    else if (!sf.length) supList.innerHTML = "<li class='td-empty'>" + esc(i18nText("home.detailNoResult")) + "</li>";
    else supList.innerHTML = sf.map(supRow).join("");
  }
  var baseList = document.getElementById("tdBaseList");
  if (baseList) {
    var bf = bases.filter(function (b) {
      if (detailState.baseCountry && (b.country || "") !== detailState.baseCountry) return false;
      return hay(b, b.name);
    });
    if (!bases.length) baseList.innerHTML = "<li class='td-empty'>" + esc(i18nText("home.detailEmptyBase")) + "</li>";
    else if (!bf.length) baseList.innerHTML = "<li class='td-empty'>" + esc(i18nText("home.detailNoResult")) + "</li>";
    else baseList.innerHTML = bf.map(baseRow).join("");
  }
}

function clearDetail() {
  var detail = refs.treeDetail;
  if (detail) {
    detail.innerHTML = "<div class='td-placeholder'>" + esc(i18nText("home.detailPlaceholder")) + "</div>";
    detail._suppliers = []; detail._bases = [];
  }
  detailState = { search: "", supCountry: "", baseCountry: "" };
  currentCompId = null;
  highlightLeaf(null);
}

function highlightLeaf(id) {
  var pane = refs.treePane;
  if (!pane) return;
  var rows = pane.querySelectorAll(".trow");
  rows.forEach(function (r) {
    if (r.getAttribute("data-kind") !== "component") return;
    if (r.getAttribute("data-id") === id) r.classList.add("leaf-selected");
    else r.classList.remove("leaf-selected");
  });
}

function selectLeaf(id) {
  currentCompId = id;
  highlightLeaf(id);
  renderDetail(id);
}

// —— 事件绑定 ——
function cacheRefs() {
  refs.treeView = document.getElementById("treeView");
  refs.treePane = document.getElementById("treePane");
  refs.treeDetail = document.getElementById("treeDetail");
}
function wireControls() {
  var pane = refs.treePane;
  if (pane && !pane._wired) {
    pane.addEventListener("click", function (e) {
      var row = e.target.closest ? e.target.closest(".trow") : null;
      if (!row) return;
      var kind = row.getAttribute("data-kind");
      var id = row.getAttribute("data-id");
      if (kind === "component") { selectLeaf(id); return; }
      var node = row.parentElement;
      if (node && node.classList.contains("branch")) node.classList.toggle("closed");
    });
    pane._wired = true;
  }
  var ret = document.getElementById("treeReturn");
  if (ret && !ret._wired) { ret.addEventListener("click", function () { toggleTreeView(false); }); ret._wired = true; }
  var exp = document.getElementById("treeExpandAll");
  if (exp && !exp._wired) {
    exp.addEventListener("click", function () {
      if (refs.treePane) refs.treePane.querySelectorAll(".tnode.branch").forEach(function (n) { n.classList.remove("closed"); });
    });
    exp._wired = true;
  }
  var col = document.getElementById("treeCollapseAll");
  if (col && !col._wired) {
    col.addEventListener("click", function () {
      if (refs.treePane) refs.treePane.querySelectorAll(".tnode.branch[data-kind='line'], .tnode.branch[data-kind='product']").forEach(function (n) { n.classList.add("closed"); });
    });
    col._wired = true;
  }
}

export function initTreeView() {
  cacheRefs();
  wireControls();
  // 语言切换后，若树已展开则重建（保留当前选中零部件）
  var rebuild = function () {
    if (!built || !refs.treeView || !document.body.classList.contains("tree-open")) return;
    if (!refs.treePane) return;
    renderTree();
    wireControls();
    if (currentCompId) { renderDetail(currentCompId); highlightLeaf(currentCompId); }
  };
  if (typeof document !== "undefined") {
    document.addEventListener("i18n:changed", rebuild);
    document.addEventListener("i18n:ready", rebuild);
  }
}

export function toggleTreeView(on) {
  cacheRefs();
  if (!refs.treeView) return;
  if (on === undefined) on = !document.body.classList.contains("tree-open");
  if (on && !built) {
    if (!ready()) return;
    buildIndexes();
    renderTree();
    wireControls();
    built = true;
    clearDetail();
  }
  document.body.classList.toggle("tree-open", on);
}
