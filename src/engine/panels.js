// panels.js — 右侧信息面板渲染（普通面板 + 风险因子面板）。归属「面板」模块，可由专人维护，
// 与物理/渲染/交互解耦。依赖 S 状态与 util 翻译/转义工具。
import { S } from "./state.js";
import { esc, label, i18nText, i18nVal, nm, COLORS, BASE_R, typeLabel } from "./util.js";

export function showRiskPanel(on) {
  var rp = document.getElementById("riskPanel");
  if (rp) rp.style.display = on ? "flex" : "none";
}

// 选中变化广播（P0 反向联动）：让「企业表格」等外部面板能订阅图谱选中事件，
// 从而把图谱/右侧面板的选中状态同步回表格高亮。key 为 null 表示清空选中。
function emitSelect(n) {
  try {
    if (typeof document !== "undefined" && document.dispatchEvent && typeof CustomEvent !== "undefined") {
      document.dispatchEvent(new CustomEvent("sc:select", {
        detail: { key: n ? n._key : null, type: n ? n.type : null, name: n ? (n.name || n.id) : null }
      }));
    }
  } catch (e) { /* DOM 桩环境无 CustomEvent 时静默跳过（make test 安全） */ }
}

export function selectNode(n) {
  S.selected = n;
  emitSelect(n);   // 广播选中变化（含清空）；所有选中路径经此函数，表格据此同步高亮
  var panel = document.getElementById("panel");
  if (!n) {
    if (panel) panel.style.display = "none";
    // 风险视图下保留说明面板，仅清空「当前节点」区
    if (S.riskMode) renderRiskPanel(null);
    return;
  }
  if (S.riskMode) { renderRiskPanel(n); showRiskPanel(true); }
  else {
    renderPanel(n);
    if (panel) panel.style.display = "block";
  }
}

// 风险因子表：自变量（输入）→ 因变量（输出）。因变量行高亮，直观区分「指标」与「结果」。
export function rfTable(rows) {
  var h = "<table class='rf'><thead><tr><th>" + i18nText("risk.role") + "</th><th>" +
          i18nText("risk.variable") + "</th><th>" + i18nText("risk.value") + "</th></tr></thead><tbody>";
  rows.forEach(function (r) {
    var role = r.role === "dep" ? i18nText("risk.dep") : i18nText("risk.indep");
    h += "<tr class='" + (r.role === "dep" ? "dep" : "") + "'><td class='role'>" + role +
         "</td><td>" + esc(r.v) + "</td><td class='val'>" + esc(String(r.val)) + "</td></tr>";
  });
  return h + "</tbody></table>";
}

export function renderPanel(n) {
  var p = document.getElementById("pbody"); if (!p) return;
  var col = COLORS[n.type];
  var h = "<h3>" + esc(n.name || n.id) + "</h3><div class='sub'>" + esc(n.english_name || "") + "</div>";
  h += "<span class='tag' style='background:" + col + "22;color:" + col + ";border:1px solid " + col + "'>" + typeLabel(n.type) + "</span>";
  if (n.type === "Product" && n.product_line) h += "<span class='tag' style='background:#2a3450;color:#cfe0ff'>" + esc(i18nVal("product_line", n.product_line)) + "</span>";
  h += "<dl>";
  function fieldRow(k, v) {
    var val = v;
    if (k === "status") val = i18nVal("status", v);
    else if (k === "country") val = i18nVal("country", v);
    else if (k === "region") val = i18nVal("region", v);
    else if (k === "category") val = i18nVal("category", v);
    else if (k === "subcategory") val = i18nVal("subcategory", v);
    else if (k === "tier") val = i18nVal("tier", v);
    else if (k === "product_line") val = i18nVal("product_line", v);
    return [i18nText("field." + k), val];
  }
  var assemblyTxt = (n.assembly || []).map(function (id) { return nm("S", id); }).join("、");
  var weakestTxt = n.weakest_component ? (nm("C", n.weakest_component) + "（" + (n.weakest != null ? n.weakest.toFixed(3) : "") + "）") : "";
  var spTxt = n.single_point === undefined ? "" : (n.single_point ? i18nText("field.single_point_yes") : i18nText("field.single_point_no"));
  var fields = n.type === "Product"
    ? [fieldRow("release_date", n.release_date), fieldRow("status", n.status), fieldRow("price", n.price_usd ? ("$" + n.price_usd) : ""), fieldRow("soc", n.soc), fieldRow("display", n.display), fieldRow("alias", n.alias), fieldRow("assembly", assemblyTxt),
       fieldRow("vuln", n.vuln != null ? n.vuln.toFixed(3) : ""),
       fieldRow("sp_count", n.sp_count != null ? n.sp_count : ""),
       fieldRow("weakest", weakestTxt)]
    : n.type === "Component"
      ? [fieldRow("category", n.category), fieldRow("subcategory", n.subcategory),
         fieldRow("vuln", n.vuln != null ? n.vuln.toFixed(3) : ""),
         fieldRow("n_suppliers", n.n_suppliers != null ? n.n_suppliers : ""),
         fieldRow("single_point", spTxt)]
      : [fieldRow("short_name", n.short_name), fieldRow("country", n.country), fieldRow("region", n.region), fieldRow("category", n.category), fieldRow("tier", n.tier)];
  fields.forEach(function (kv) { if (kv[1]) h += "<dt>" + kv[0] + "</dt><dd>" + esc(String(kv[1])) + "</dd>"; });
  h += "</dl>";
  var out = [];
  S.adj[n._key].forEach(function (e) { if (e.dir === "out") out.push(e); });
  if (out.length) {
    h += "<dt style='margin-top:12px;color:#9fb0d0;font-size:11px'>" + i18nText("panel.rel") + "（" + out.length + " · " + i18nText("panel.relHint") + "）</dt><dd><ul>";
    out.forEach(function (e) {
      var extra = e.link.share ? " · 份额 " + e.link.share + "%" : "";
      h += "<li class='rel' data-key='" + esc(e.other._key) + "' title='点击聚焦：" + esc(label(e.other)) + "'>"
        + "<b>" + e.link.type + "</b> → " + esc(label(e.other)) + extra + "</li>";
    });
    h += "</ul></dd>";
  }
  // 逐项展开/收起供应商：与「选中看信息」解耦（点击节点只选中，展开由本按钮或节点上的＋触发）。
  if (n.type === "Product" || n.type === "Component") {
    var isExp = S.expanded.has(n._key);
    h += "<div style='margin-top:10px'><button class='expand-btn' data-key='" + esc(n._key) + "' data-act='" +
         (isExp ? "collapse" : "expand") + "'>" +
         (isExp ? i18nText("home.collapseSup") : i18nText("home.expandSup")) + "</button></div>";
  }
  var sec = n.type === "Product" ? "sec-products" : n.type === "Component" ? "sec-components" : "sec-suppliers";
  if (S.reportLink) h += "<p style='margin-top:10px'>" + S.reportLink(n, sec) + "</p>";
  if (S.mapLink && n.type === "Supplier") h += "<p style='margin-top:6px'>" + S.mapLink(n) + "</p>";
  p.innerHTML = h;
}

export function renderRiskPanel(n) {
  var body = document.getElementById("riskBody"); if (!body) return;
  if (!n) { body.innerHTML = "<div class='risk-pick'>" + i18nText("risk.pick") + "</div>"; return; }
  var col = COLORS[n.type];
  var h = "<h3>" + esc(n.name || n.id) + "</h3><div class='sub'>" + esc(n.english_name || "") + "</div>";
  h += "<span class='tag' style='background:" + col + "22;color:" + col + ";border:1px solid " + col + "'>" + typeLabel(n.type) + "</span>";
  if (n.type === "Product" && n.product_line) h += "<span class='tag' style='background:#2a3450;color:#cfe0ff'>" + esc(i18nVal("product_line", n.product_line)) + "</span>";
  if (n.type === "Supplier") {
    h += "<div class='risk-note'>" + i18nText("risk.supplierNote") + "</div>";
  } else if (n.type === "Component") {
    var sp = n.single_point ? i18nText("field.single_point_yes") : i18nText("field.single_point_no");
    var rows = [
      { role: "indep", v: i18nText("risk.cN"), val: (n.n_suppliers != null ? n.n_suppliers : "—") },
      { role: "indep", v: i18nText("risk.cSingle"), val: sp },
      { role: "dep", v: i18nText("risk.cV"), val: (n.vuln != null ? n.vuln.toFixed(3) : "—") }
    ];
    h += "<h4>" + i18nText("risk.current") + "</h4>" + rfTable(rows) +
         "<div class='risk-formula'>" + i18nText("risk.formulaComp") + "</div>";
  } else if (n.type === "Product") {
    var spRateTxt = (n.sp_count != null && n.n_components) ? (n.sp_count + " / " + n.n_components + " = " + (n.sp_rate != null ? n.sp_rate.toFixed(3) : (n.sp_count / n.n_components).toFixed(3))) : "—";
    var weakTxt = n.weakest_component ? "（" + nm("C", n.weakest_component) + "）" : "";
    var rows = [
      { role: "indep", v: i18nText("risk.pMean"), val: (n.mean_v != null ? n.mean_v.toFixed(3) : "—") },
      { role: "indep", v: i18nText("risk.pWeakest"), val: (n.weakest != null ? n.weakest.toFixed(3) : "—") + weakTxt },
      { role: "indep", v: i18nText("risk.pSpRate"), val: spRateTxt },
      { role: "dep", v: i18nText("risk.pV"), val: (n.vuln != null ? n.vuln.toFixed(3) : "—") }
    ];
    h += "<h4>" + i18nText("risk.current") + "</h4>" + rfTable(rows) +
         "<div class='risk-formula'>" + i18nText("risk.formulaProd") + "</div>";
  }
  var sec = n.type === "Product" ? "sec-products" : n.type === "Component" ? "sec-components" : "sec-suppliers";
  if (S.reportLink) h += "<p style='margin-top:10px'>" + S.reportLink(n, sec) + "</p>";
  if (S.mapLink && n.type === "Supplier") h += "<p style='margin-top:6px'>" + S.mapLink(n) + "</p>";
  body.innerHTML = h;
}
