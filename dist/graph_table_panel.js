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
  var lastKey = null, lastType = null, lastName = null;

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
    // 重渲染后恢复当前选中高亮（P2：搜索/筛选导致表格重建时，已选中供应商仍保持高亮）。
    if (lastKey) highlightRow(lastKey);
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

  // 高亮与 key 匹配的行（无滚动）；返回匹配到的 <tr> 或 null（key 为空或非供应商时清除全部高亮）。
  function highlightRow(key) {
    if (!tbody) return null;
    var rows = tbody.querySelectorAll("tr[data-key]");
    var found = null;
    for (var i = 0; i < rows.length; i++) {
      var match = !!key && rows[i].getAttribute("data-key") === key;
      rows[i].classList.toggle("active", match);
      if (match) found = rows[i];
    }
    return found;
  }
  // 表格行高亮 + 滚动到可见区（P1：选中后定位到该行）。
  function focusRow(key) {
    var r = highlightRow(key);
    if (r && r.scrollIntoView) { try { r.scrollIntoView({ block: "nearest" }); } catch (e) {} }
    return r;
  }

  // 订阅引擎广播的选中事件（P0 反向联动）：图谱/右侧面板选中变化时同步本表。
  function onSelect(e) {
    var d = (e && e.detail) || {};
    lastKey = d.key || null;
    lastType = d.type || null;
    lastName = d.name || null;
    // 不再自动弹开表格：尊重用户主动关闭表格的操作（避免每次选供应商都被弹回，侵扰）；
    // 选中状态记入 lastKey，待用户重新打开表格时由 render() 恢复高亮。
    // 「企业表格」只列供应商；选中产品/零部件时本就不对应任何行，仅清高亮即可，
    // 不再显示「不在本供应商表」之类的告警提示（产品本就不是供应商，属预期行为，非错误）。
    focusRow(lastKey);   // null 或非供应商 → 清除高亮；供应商 → 高亮+滚动
  }

  function init() {
    side = $("side"); tbody = $("sideBody"); countEl = $("sideCount");
    toggleBtn = $("toggleTable"); closeBtn = $("sideClose");
    if (!side) return;
    // 订阅引擎选中广播（P0 反向联动 / P0 清空去高亮）。
    document.addEventListener("sc:select", onSelect);
    if (toggleBtn) toggleBtn.onclick = toggle;
    if (closeBtn) closeBtn.onclick = close;
    if (tbody) tbody.addEventListener("click", function (e) {
      var tr = e.target.closest ? e.target.closest("tr[data-key]") : null;
      if (!tr) return;
      var key = tr.getAttribute("data-key");
      if (window.GraphEngine && window.GraphEngine.focus) window.GraphEngine.focus(key);
      focusRow(key);
    });
    // 订阅引擎「视图/筛选变化」事件统一刷新表格（覆盖 搜索/勾选/产品线/展开全部/逐项展开/重置
    // 等所有会改变可见供应商集的路径；按钮与程序化改值不触发 input/change，由引擎统一广播 sc:view 弥合）。
    document.addEventListener("sc:view", render);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
