/* graph_bootstrap.js — 首页图谱启动脚本（由 build_viewer.py 注入到根 index.html）
 * 首页位于仓库根目录，故跨页链接用根相对路径：
 *   报告  -> dist/apple_supply_chain_report.html#sec-...
 *   地图  -> tools/visualizations/supplier_geo.html?supplier=...
 */
(function () {
  var g = window.GraphEngine.init({
    reportLink: function (n, sec) {
      return "<a class='lk' href='dist/apple_supply_chain_report.html#" + sec + "' target='_blank'>在报告中查看 →</a>";
    },
    mapLink: function (n) {
      return "<a class='lk' href='tools/visualizations/supplier_geo.html?supplier=" + window.GraphEngine.esc(n.id) + "' target='_blank'>在地图中查看 →</a>";
    }
  });
  g.start();
  // 深链：从其它页面带 ?focus=KEY 跳转过来时，自动选中并居中该节点
  var pk = new URLSearchParams(location.search).get("focus");
  if (pk) g.focus(pk);
})();
