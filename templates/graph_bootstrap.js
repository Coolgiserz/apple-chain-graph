/* graph_bootstrap.js — 首页图谱启动脚本（Plan C：模板即页面，数据运行时拉取）。
 *
 * 旧方案：构建期把整份图数据内联进 index.html（window.SUPPLY_DATA = __DATA__），
 * 每次数据/风险更新都需重生成整页、易与模板漂移。
 * 新方案（Plan C）：index.html 成为静态可部署页面，本脚本在浏览器端：
 *   1) fetch 图数据 data/apple_supply_chain.json；
 *   2) best-effort fetch 风险分析结果 data/supply_chain_risk.json 并合并进节点
 *      （风险视图所需的 vuln / single_point 等字段），缺则降级（图谱仅缺风险着色）；
 *   3) 写入 window.SUPPLY_DATA 后启动引擎。
 *
 * 跨页链接用根相对路径（首页位于仓库根目录）：
 *   报告  -> dist/apple_supply_chain_report.html#sec-...
 *   地图  -> tools/visualizations/supplier_geo.html?supplier=...
 */
(function () {
  // 用 JS 翻译（window.i18n.t）而非 data-i18n：面板是点击节点后动态生成的，
  // 需每次渲染都取当前语言；i18n.t 在未就绪时也会回退中文（见 i18n.js 的 api.t 兜底）。
  function L(k) { return window.i18n ? window.i18n.t(k) : k; }

  // 把供应链脆弱性分析结果合并进图节点（组件 / 产品），供「风险视图」使用。
  // 字段对齐旧 build_viewer.merge_risk：组件加 vuln / n_suppliers / single_point；
  // 产品加 vuln / sp_count / weakest / weakest_component / n_components / mean_v / sp_rate。
  // 风险数据缺失或解析失败时原样返回（不报错、不白屏），图谱仅缺风险着色。
  function mergeRisk(data, risk) {
    if (!risk || !data || !data.nodes) return data;
    var comp = {};
    (risk.components || []).forEach(function (c) { comp[c.component_id] = c; });
    var prod = {};
    (risk.products || []).forEach(function (p) { prod[p.product_id] = p; });
    (data.nodes.components || []).forEach(function (c) {
      var r = comp[c.id];
      if (r) { c.vuln = r.vuln; c.n_suppliers = r.n_suppliers; c.single_point = r.single_point; }
    });
    (data.nodes.products || []).forEach(function (p) {
      var r = prod[p.id];
      if (r) {
        p.vuln = r.product_vuln;
        p.sp_count = r.sp_count;
        p.weakest = r.weakest;
        p.weakest_component = r.weakest_component;
        // 风险因子分解表所需的自变量：部件总数、平均脆弱性、单点率
        p.n_components = r.n_components;
        p.mean_v = r.mean_v;
        p.sp_rate = r.sp_rate;
      }
    });
    return data;
  }

  // 拉取 JSON，失败返回 null（best-effort：风险数据 / 数据文件缺失都不应阻断页面）。
  function getJSON(url) {
    return fetch(url, { cache: "no-cache" })
      .then(function (r) { if (!r.ok) throw new Error(url + " -> " + r.status); return r.json(); })
      .catch(function (e) { console.warn("[bootstrap] 拉取失败（降级）：", url, e.message); return null; });
  }

  function showFatal(msg) {
    var el = document.getElementById("hint");
    if (el) {
      el.style.display = "block";
      el.style.color = "#ffb4b4";
      el.textContent = msg;
    }
    console.error("[bootstrap] " + msg);
  }

  function boot(data) {
    var g = window.GraphEngine.init({
      reportLink: function (n, sec) {
        return "<a class='lk' href='dist/apple_supply_chain_report.html#" + sec + "' target='_blank'>" + L("link.report") + "</a>";
      },
      mapLink: function (n) {
        // P1-#5：id 含 &/# 等字符会破坏 URL，esc 仅做 HTML 转义不够，必须用 encodeURIComponent。
        return "<a class='lk' href='tools/visualizations/supplier_geo.html?supplier=" + encodeURIComponent(n.id) + "' target='_blank'>" + L("link.map") + "</a>";
      }
    }, data);
    g.start();
    // 第三种视图：供应链树状视图（feat/tree-view）。缓存 DOM 引用并接线工具栏按钮。
    try { g.initTreeView(); } catch (e) { console.error("[treeView] initTreeView 失败：", e); }
    var treeBtn = document.getElementById("treeBtn");
    if (treeBtn) treeBtn.addEventListener("click", function () { try { g.toggleTreeView(true); } catch (e) { console.error("[treeView] toggleTreeView 失败：", e); } });
    // 瓶颈透视元素（feat/graph-analytics）：与风险视图互斥
    var bt = document.getElementById("bnToggle");
    var bnLegend = document.getElementById("bnLegend");
    // 风险视图开关：勾选后图谱按脆弱性着色 + 单点标记，并显示颜色图例
    var rt = document.getElementById("riskToggle");
    var legend = document.getElementById("legend");
    if (rt) rt.addEventListener("change", function () {
      try {
        g.setRiskMode(rt.checked);
        if (legend) legend.style.display = rt.checked ? "flex" : "none";
        if (rt.checked && bt) { bt.checked = false; if (bnLegend) bnLegend.style.display = "none"; g.setBottleneckMode(false); }
      } catch (e) {
        // 不再静默吞错：引擎脚本若被旧缓存加载（缺 setRiskMode）会在此暴露，便于排查
        console.error("[riskView] setRiskMode 失败：", e);
      }
    });
    // 风险因子面板关闭按钮：取消勾选并退出风险视图
    var rc = document.getElementById("riskClose");
    if (rc) rc.addEventListener("click", function () {
      if (rt) rt.checked = false;
      if (legend) legend.style.display = "none";
      try { g.setRiskMode(false); } catch (e) { console.error("[riskView] 关闭面板失败：", e); }
    });
    // 瓶颈透视开关：勾选后图谱按瓶颈指标着色 + 弹出右侧瓶颈面板，并隐藏风险视图
    if (bt) bt.addEventListener("change", function () {
      try {
        g.setBottleneckMode(bt.checked);
        if (bnLegend) bnLegend.style.display = bt.checked ? "flex" : "none";
        if (bt.checked && rt) { rt.checked = false; if (legend) legend.style.display = "none"; g.setRiskMode(false); }
      } catch (e) { console.error("[bottleneck] setBottleneckMode 失败：", e); }
    });
    // 瓶颈着色指标切换：reach（按波及范围）/ pagerank（按网络核心度）
    var bm = document.getElementById("bnMetric");
    if (bm) bm.addEventListener("change", function () {
      try { g.setBottleneckMetric(bm.value); } catch (e) { console.error("[bottleneck] setBottleneckMetric 失败：", e); }
    });
    // 瓶颈面板关闭按钮：取消勾选并退出瓶颈视图
    var bc = document.getElementById("bnClose");
    if (bc) bc.addEventListener("click", function () {
      if (bt) bt.checked = false;
      if (bnLegend) bnLegend.style.display = "none";
      try { g.setBottleneckMode(false); } catch (e) { console.error("[bottleneck] 关闭面板失败：", e); }
    });
    // 深链：从其它页面带 ?focus=KEY 跳转过来时，自动选中并居中该节点
    var pk = new URLSearchParams(location.search).get("focus");
    if (pk) g.focus(pk);
  }

  // 运行时装配数据：图数据（必需）+ 风险数据（可选），合并后启动。
  Promise.all([getJSON("data/apple_supply_chain.json"), getJSON("data/supply_chain_risk.json")])
    .then(function (res) {
      var data = res[0], risk = res[1];
      if (!data) { showFatal("数据加载失败：请确认 data/apple_supply_chain.json 可通过 HTTP 访问（直接双击打开 index.html 会因 file:// 的 CORS 限制无法 fetch）"); return; }
      boot(mergeRisk(data, risk));
    });
})();
