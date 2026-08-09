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
  // 深链：从其它页面带 ?focus=KEY 跳转过来时，自动选中并居中该节点
  var pk = new URLSearchParams(location.search).get("focus");
  if (pk) g.focus(pk);
})();
