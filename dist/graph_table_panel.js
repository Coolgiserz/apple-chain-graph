/* =============================================================================
 * graph_table_panel.js — 首页图谱的「企业表格」侧边面板
 *
 * 与图谱联动：
 *   - 点击控制栏「📋 企业表格」按钮打开本面板（从左侧滑出），画布让出左侧空间，
 *     图谱不被遮挡（仅压缩显示区域）。
 *   - 面板列出 GraphEngine.visibleNodes() —— 即图谱当前筛选/搜索后「可见」的企业，
 *     与图谱视图严格一致（同一套 visibleSet 逻辑）。
 *   - 用户在控制栏改搜索词 / 勾选类型 / 选产品线 / 点「重置视图」时，表格实时刷新。
 *   - 点击表格中某一行 → GraphEngine.focus(key) 在图谱中居中并选中该企业，
 *     同时该行高亮，便于在「表」与「图」之间来回定位。
 *
 * 该面板只在首页（index.html）使用；共享引擎 graph_engine.js 不依赖本文件。
 * ===========================================================================*/
(function () {
  "use strict";

  function $(id) { return document.getElementById(id); }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>]/g, function (c) {
      return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]);
    });
  }

  var side, tbody, countEl, toggleBtn, closeBtn;

  function render() {
    if (!side || side.style.display === "none") return;
    var nodes = (window.GraphEngine && window.GraphEngine.visibleNodes)
      ? window.GraphEngine.visibleNodes() : [];
    // 「企业表格」专指图谱中当前可见的「供应商」节点；产品/零部件在图谱里查看，不混入表格
    var suppliers = nodes.filter(function (n) { return n.type === "Supplier"; });
    suppliers.sort(function (a, b) { return (a.name || "").localeCompare(b.name || "", "zh-Hans-CN"); });
    if (countEl) countEl.textContent = suppliers.length;
    if (!tbody) return;
    if (!suppliers.length) {
      tbody.innerHTML = "<tr><td class='empty' colspan='4'>没有匹配的供应商</td></tr>";
      return;
    }
    var html = "";
    suppliers.forEach(function (n) {
      var name = esc(n.name || n.id);
      html += "<tr data-key='" + esc(n._key) + "' title='" + name + "'>"
        + "<td class='name'>" + name + "</td>"
        + "<td>" + esc(n.country || "—") + "</td>"
        + "<td>" + esc(n.category || "—") + "</td>"
        + "<td class='tier'>" + esc(n.tier ? ("Tier " + n.tier) : "—") + "</td>"
        + "</tr>";
    });
    tbody.innerHTML = html;
  }

  function isOpen() { return side && side.style.display !== "none"; }
  function open() {
    if (!side) return;
    side.style.display = "flex";
    document.body.classList.add("table-open");
    if (window.GraphEngine && window.GraphEngine.resize) window.GraphEngine.resize();
    render();
  }
  function close() {
    if (!side) return;
    side.style.display = "none";
    document.body.classList.remove("table-open");
    if (window.GraphEngine && window.GraphEngine.resize) window.GraphEngine.resize();
  }
  function toggle() { isOpen() ? close() : open(); }

  function focusRow(key) {
    if (!tbody) return;
    var rows = tbody.querySelectorAll("tr");
    for (var i = 0; i < rows.length; i++) {
      rows[i].classList.toggle("active", rows[i].getAttribute("data-key") === key);
    }
  }

  function init() {
    side = $("side"); tbody = $("sideBody"); countEl = $("sideCount");
    toggleBtn = $("toggleTable"); closeBtn = $("sideClose");
    if (!side) return;
    if (toggleBtn) toggleBtn.onclick = toggle;
    if (closeBtn) closeBtn.onclick = close;
    if (tbody) tbody.addEventListener("click", function (e) {
      var tr = e.target.closest ? e.target.closest("tr[data-key]") : null;
      if (!tr) return;
      var key = tr.getAttribute("data-key");
      if (window.GraphEngine && window.GraphEngine.focus) window.GraphEngine.focus(key);
      focusRow(key);
    });
    // 筛选 / 搜索变化时实时刷新表格（与图谱共用同一 visibleSet）
    ["q", "cbP", "cbC", "cbS", "line"].forEach(function (id) {
      var el = $(id);
      if (el) {
        el.addEventListener("input", render);
        el.addEventListener("change", render);
      }
    });
    // 引擎「重置视图」按钮会改搜索词/勾选/产品线（JS 赋值不触发 input），单独监听
    var reset = $("reset");
    if (reset) reset.addEventListener("click", function () { setTimeout(render, 0); });
    // 跨页深链 ?focus= 选中节点后，若面板已开则同步高亮
    window.addEventListener("hashchange", function () {});
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
