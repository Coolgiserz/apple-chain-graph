// panels.js — 右侧信息面板渲染（普通面板 + 风险因子面板）。归属「面板」模块，可由专人维护，
// 与物理/渲染/交互解耦。依赖 S 状态与 util 翻译/转义工具。
import { S } from "./state.js";
import { esc, label, i18nText, i18nVal, nm, COLORS, BASE_R, typeLabel } from "./util.js";
import { computeMetrics } from "../lib/analytics.js";

export function showRiskPanel(on) {
  var rp = document.getElementById("riskPanel");
  if (rp) rp.style.display = on ? "flex" : "none";
}

// 瓶颈透视面板显隐（与 #riskPanel 同槽同款 chrome）。
export function showBottleneckPanel(on) {
  var bp = document.getElementById("bottleneckPanel");
  if (bp) bp.style.display = on ? "flex" : "none";
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
    // 风险/瓶颈视图下保留说明面板，仅清空「当前节点」区
    if (S.bottleneckMode) renderBottleneckPanel(null);
    else if (S.riskMode) renderRiskPanel(null);
    return;
  }
  if (S.bottleneckMode) { renderBottleneckPanel(n); showBottleneckPanel(true); }
  else if (S.riskMode) { renderRiskPanel(n); showRiskPanel(true); }
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
  if (n.type === "Base" && n.confidence) {
    var ccol = n.confidence === "high" ? "#10b981" : n.confidence === "medium" ? "#f59e0b" : "#ef4444";
    h += "<span class='tag' style='background:" + ccol + "22;color:" + ccol + ";border:1px solid " + ccol + "'>" + esc(i18nText("field.confidence")) + ": " + esc(n.confidence) + "</span>";
  }
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
      : n.type === "Base"
        ? [fieldRow("city", n.city), fieldRow("province", n.province || ""), fieldRow("country", n.country),
           fieldRow("operator", n.operator ? nm("S", n.operator) : ""),
           fieldRow("products", (n.products || []).map(function (pl) { return i18nVal("product_line", pl); }).join("、")),
           fieldRow("role", n.role), fieldRow("confidence", n.confidence)]
        : [fieldRow("short_name", n.short_name), fieldRow("country", n.country), fieldRow("region", n.region), fieldRow("category", n.category), fieldRow("tier", n.tier)];
  fields.forEach(function (kv) { if (kv[1]) h += "<dt>" + kv[0] + "</dt><dd>" + esc(String(kv[1])) + "</dd>"; });
  h += "</dl>";
  // 关系列表：列出该节点全部相邻边（含上下游两个方向），用友好关系名替代原始边类型码
  // （ USES/SUPPLIES/ASSEMBLES/LINE ），并修复「供应商节点无任何关系」的空缺（其边均为入方向）。
  var rels = S.adj[n._key];
  if (rels.length) {
    h += "<dt style='margin-top:12px;color:#9fb0d0;font-size:11px'>" + i18nText("panel.rel") + "（" + rels.length + " · " + i18nText("panel.relHint") + "）</dt><dd><ul>";
    rels.forEach(function (e) {
      var isOut = e.dir === "out";                       // out：供应链从本节点「流出」（使用/供应/组装）；in：反向
      var verb = i18nText("edge." + e.link.type);        // 友好关系名（使用/供应/组装/归属/生产于/运营）
      var nm = esc(label(e.other));
      var phrase = isOut ? (verb + " → " + nm) : (nm + " → " + verb);   // 出方向「动词→对象」，入方向「对象→动词」
      var extra = e.link.share ? " · 份额 " + e.link.share + "%" : "";
      // 来源溯源：每条边附 source（来源注册表 id 列表），渲染为可点击外链，确保关系可追溯到公开资料
      var srcHtml = "";
      if (e.link.source && e.link.source.length) {
        var reg = (window.SUPPLY_DATA && window.SUPPLY_DATA.meta && window.SUPPLY_DATA.meta.source_registry) || {};
        srcHtml = " <span class='src'>";
        e.link.source.forEach(function (sid) {
          var m = reg[sid];
          if (m && m.url) srcHtml += "<a href='" + esc(m.url) + "' target='_blank' rel='noopener' onclick='event.stopPropagation()'>" + esc(m.publisher || sid) + "</a>";
        });
        srcHtml += "</span>";
      }
      h += "<li class='rel' data-key='" + esc(e.other._key) + "' title='点击聚焦：" + esc(label(e.other)) + "'>"
        + phrase + extra + srcHtml + "</li>";
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

// —— 瓶颈透视面板（feat/graph-analytics）——
// 无选中 → 全局概览（摘要卡 + 断供影响排行）；选中节点 → 该节点瓶颈分析（断供模拟 / 复用率 / 单点）。
function bnRow(key, name, sub) {
  return "<li class='rel' data-key='" + esc(key) + "'>" + esc(name) +
    (sub ? " <span class='bn-sub'>" + esc(sub) + "</span>" : "") + "</li>";
}

export function renderBottleneckPanel(n) {
  var body = document.getElementById("bnBody"); if (!body) return;
  var m = computeMetrics();
  if (m.empty) { body.innerHTML = "<div class='risk-pick'>" + i18nText("bottleneck.pick") + "</div>"; return; }

  if (!n) {
    // —— 概览 ——
    S.bottleneckFocus = null;   // 无选中：清除图谱下游高亮（feat 修复：点击排行项后图谱呼应）
    var cnPct = Math.round(m.geoCN * 100);
    var metric = S.bottleneckMetric === "pagerank" ? "pagerank" : "reach";
    var h = "";
    // 动态说明：让用户理解「当前按哪个指标着色」以及「红色代表什么」（修复切换指标无感知、无法理解）。
    h += "<div class='bn-caption'>" +
      i18nText(metric === "pagerank" ? "bottleneck.captionPagerank" : "bottleneck.captionReach") + "</div>";
    h += "<div class='bn-cards'>";
    h += "<div class='bn-card'><div class='bn-card-v'>" + m.singleSourced.length + "</div><div class='bn-card-k'>" + i18nText("bottleneck.cardSingle") + "</div></div>";
    h += "<div class='bn-card'><div class='bn-card-v'>" + cnPct + "%</div><div class='bn-card-k'>" + i18nText("bottleneck.cardGeo") + "</div></div>";
    h += "<div class='bn-card'><div class='bn-card-v' style='font-size:13px;line-height:1.4'>" + esc(m.worstSingle || "—") + "</div><div class='bn-card-k'>" + i18nText("bottleneck.cardWorst") + "</div></div>";
    h += "</div>";
    // 排行随指标切换：reach → 断供影响排行；pagerank → 网络核心度排行。
    var ranking = metric === "pagerank" ? m.topByPagerank : m.topByReach;
    var rankTitle = metric === "pagerank" ? i18nText("bottleneck.rankTitlePagerank") : i18nText("bottleneck.rankTitle");
    h += "<h4 style='margin:14px 0 6px;font-size:13px;color:#cfe0ff'>" + rankTitle + "</h4>";
    h += "<ul class='bn-rank'>";
    if (!ranking.length) h += "<li class='bn-empty'>" + i18nText("bottleneck.pick") + "</li>";
    ranking.forEach(function (r) {
      var sub;
      if (metric === "pagerank") {
        var pct = m.range.pagerank.max > 0 ? (r.score / m.range.pagerank.max * 100) : 0;
        sub = i18nText("bottleneck.coreUnit").replace("{p}", pct.toFixed(0));
      } else {
        sub = r.reach + " " + i18nText("bottleneck.reachUnit") + (r.noAlt ? " · " + r.noAlt + " " + i18nText("bottleneck.noAlt") : "");
      }
      h += bnRow(r.key, r.label, sub);
    });
    h += "</ul>";
    body.innerHTML = h;
    return;
  }

  // —— 选中节点详情 ——
  var col = COLORS[n.type];
  var h = "<h3>" + esc(n.name || n.id) + "</h3><div class='sub'>" + esc(n.english_name || "") + "</div>";
  h += "<span class='tag' style='background:" + col + "22;color:" + col + ";border:1px solid " + col + "'>" + typeLabel(n.type) + "</span>";
  if (n.type === "Product" && n.product_line) h += "<span class='tag' style='background:#2a3450;color:#cfe0ff'>" + esc(i18nVal("product_line", n.product_line)) + "</span>";
  var info = m.info[n._key] || { reach: 0, noAlt: 0, affected: [], suppliedComps: [], reuseProducts: [], spComps: [] };

  // 选中节点在当前指标排行中的位次（让「切换指标」在详情视图也有可见反馈）。
  var activeRanking = (S.bottleneckMetric === "pagerank") ? m.topByPagerank : m.topByReach;
  var rankIdx = -1;
  for (var ri = 0; ri < activeRanking.length; ri++) { if (activeRanking[ri].key === n._key) { rankIdx = ri + 1; break; } }
  if (rankIdx > 0) {
    h += "<div class='bn-rank-note'>" + i18nText("bottleneck.yourRank")
      .replace("{n}", rankIdx).replace("{t}", activeRanking.length)
      .replace("{m}", S.bottleneckMetric === "pagerank" ? i18nText("home.bnMetricPagerank") : i18nText("home.bnMetricReach")) + "</div>";
  }

  if (n.type === "Supplier") {
    var aff = info.affected;
    // 图谱下游高亮集合：选中供应商 + 其供应零部件 + 受影响产品（feat 修复：让排行里的「波及N款」在图上可见）
    S.bottleneckFocus = new Set([n._key].concat(info.suppliedComps, aff.map(function (a) { return a.key; })));
    h += "<div class='bn-impact'>";
    h += "<div class='bn-impact-h'>" + i18nText("bottleneck.impactTitle") + "</div>";
    h += "<div class='bn-stat-row'>";
    h += "<div class='bn-stat'><div class='bn-stat-v'>" + aff.length + "</div><div class='bn-stat-k'>" + i18nText("bottleneck.statReach") + "</div></div>";
    h += "<div class='bn-stat'><div class='bn-stat-v'>" + info.suppliedComps.length + "</div><div class='bn-stat-k'>" + i18nText("bottleneck.suppliedComps") + "</div></div>";
    h += "</div>";
    // 澄清：「波及」≠「停产」——共用零件不代表都会停线
    h += "<div class='bn-impact-b'>" + i18nText("bottleneck.reachClarify") + "</div>";
    // 无替代将真正停产：单独突出（0=安全，>0=风险），避免被误读成「28 款都停产」
    h += "<div class='bn-noalt " + (info.noAlt ? "bn-noalt-bad" : "bn-noalt-ok") + "'>" +
      (info.noAlt ? "⚠ " : "✓ ") + i18nText("bottleneck.noAltBox") + "：<span class='bn-noalt-n'>" + info.noAlt + "</span> " + i18nText("bottleneck.reachUnit") + "</div>";
    if (aff.length) {
      h += "<h4 style='margin:12px 0 4px;font-size:13px;color:#cfe0ff'>" + i18nText("bottleneck.sharedProducts") + "（" + aff.length + "）</h4><ul class='bn-rank'>" + aff.map(function (a) {
        return bnRow(a.key, label(S.idMap[a.key]), a.single ? "⚠ " + i18nText("bottleneck.noAlt") : "");
      }).join("") + "</ul>";
    }
    if (info.suppliedComps.length) {
      h += "<h4 style='margin:12px 0 4px;font-size:13px;color:#cfe0ff'>" + i18nText("bottleneck.suppliedComps") + "</h4><ul class='bn-rank'>" +
        info.suppliedComps.map(function (k) { return bnRow(k, label(S.idMap[k]), ""); }).join("") + "</ul>";
    }
    h += "</div>";
    if (info.suppliedComps.length) {
      h += "<h4 style='margin:12px 0 4px;font-size:13px;color:#cfe0ff'>" + i18nText("bottleneck.suppliedComps") + "</h4><ul class='bn-rank'>" +
        info.suppliedComps.map(function (k) { return bnRow(k, label(S.idMap[k]), ""); }).join("") + "</ul>";
    }
  } else if (n.type === "Component") {
    var reuse = info.reuseProducts.length;
    var sp = n.single_point || n.n_suppliers === 1;
    // 图谱下游高亮集合：零部件自身 + 共用它的产品
    S.bottleneckFocus = new Set([n._key].concat(info.reuseProducts));
    h += "<div class='bn-impact'>";
    h += "<div class='bn-impact-h'>" + i18nText("bottleneck.impactTitle") + "</div>";
    h += "<div class='bn-stat-row'>";
    h += "<div class='bn-stat'><div class='bn-stat-v'>" + reuse + "</div><div class='bn-stat-k'>" + i18nText("bottleneck.statReuse") + "</div></div>";
    h += "<div class='bn-stat'><div class='bn-stat-v'>" + info.reach + "</div><div class='bn-stat-k'>" + i18nText("bottleneck.statReach") + "</div></div>";
    h += "</div>";
    // 零部件：被 N 款产品共用，断供即波及这 N 款（reuse==reach，合并为单一清晰表述，避免重复数字困惑）
    h += "<div class='bn-impact-b'>" + i18nText("bottleneck.impactDescComp").replace("{n}", reuse) + "</div>";
    h += "</div>";
    if (sp) h += "<div class='bn-warn'>⚠ " + i18nText("bottleneck.singleWarn") + "</div>";
    else if (reuse) {
      h += "<div class='bn-impact-b' style='margin-top:8px'>" + i18nText("bottleneck.reachClarify") + "</div>";
      h += "<h4 style='margin:12px 0 4px;font-size:13px;color:#cfe0ff'>" + i18nText("bottleneck.sharedProducts") + "（" + reuse + "）</h4><ul class='bn-rank'>" +
        info.reuseProducts.map(function (k) { return bnRow(k, label(S.idMap[k]), ""); }).join("") + "</ul>";
    }
  } else if (n.type === "Product") {
    // 图谱高亮：产品自身 + 其单点依赖零部件（一旦这些零件断供，该产品直接受影响）
    S.bottleneckFocus = new Set([n._key].concat(info.spComps));
    h += "<div class='bn-impact'><div class='bn-stat-row'>";
    h += "<div class='bn-stat'><div class='bn-stat-v'>" + info.compCount + "</div><div class='bn-stat-k'>" + i18nText("bottleneck.statComp") + "</div></div>";
    h += "<div class='bn-stat'><div class='bn-stat-v'" + (info.spComps.length ? " style='color:#ef4444'" : "") + ">" + info.spComps.length + "</div><div class='bn-stat-k'>" + i18nText("bottleneck.statSP") + "</div></div>";
    h += "</div><div class='bn-impact-b'>" +
      i18nText("bottleneck.compCount") + " <b>" + info.compCount + "</b>；" +
      i18nText("bottleneck.spComps") + " <b style='color:" + (info.spComps.length ? "#ef4444" : "#10b981") + "'>" + info.spComps.length + "</b>。</div></div>";
    if (info.spComps.length) {
      h += "<h4 style='margin:12px 0 4px;font-size:13px;color:#cfe0ff'>" + i18nText("bottleneck.affectedProducts") + "（" + info.spComps.length + "）</h4><ul class='bn-rank'>" + info.spComps.map(function (k) { return bnRow(k, label(S.idMap[k]), "⚠ " + i18nText("bottleneck.noAlt")); }).join("") + "</ul>";
    }
  } else {
    S.bottleneckFocus = null;
    h += "<div class='risk-pick'>" + i18nText("bottleneck.pickNode") + "</div>";
  }
  var sec = n.type === "Product" ? "sec-products" : n.type === "Component" ? "sec-components" : "sec-suppliers";
  if (S.reportLink) h += "<p style='margin-top:10px'>" + S.reportLink(n, sec) + "</p>";
  if (S.mapLink && n.type === "Supplier") h += "<p style='margin-top:6px'>" + S.mapLink(n) + "</p>";
  body.innerHTML = h;
}
