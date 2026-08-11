/* graph_bootstrap.js — 首页图谱启动脚本（由 build_viewer.py 注入到根 index.html）
 * 首页位于仓库根目录，故跨页链接用根相对路径：
 *   报告  -> dist/apple_supply_chain_report.html#sec-...
 *   地图  -> tools/visualizations/supplier_geo.html?supplier=...
 */
(function () {
  // 用 JS 翻译（window.i18n.t）而非 data-i18n：面板是点击节点后动态生成的，
  // 需每次渲染都取当前语言；i18n.t 在未就绪时也会回退中文（见 i18n.js 的 api.t 兜底）。
  function L(k) { return window.i18n ? window.i18n.t(k) : k; }

  var g = window.GraphEngine.init({
    reportLink: function (n, sec) {
      return "<a class='lk' href='dist/apple_supply_chain_report.html#" + sec + "' target='_blank'>" + L("link.report") + "</a>";
    },
    mapLink: function (n) {
      return "<a class='lk' href='tools/visualizations/supplier_geo.html?supplier=" + window.GraphEngine.esc(n.id) + "' target='_blank'>" + L("link.map") + "</a>";
    }
  });
  g.start();
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
})();
