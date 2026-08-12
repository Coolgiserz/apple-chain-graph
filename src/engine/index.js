// index.js — 引擎入口：组装对外 API 并挂到 window.GraphEngine（IIFE 打包后行为与原 graph_engine.js 一致）。
// 把「物理 / 渲染 / 交互 / 面板」各自独立为模块后，此处只做编排，便于分模块协作。
import { S } from "./state.js";
import { W, H, esc, safeUrl, i18nText } from "./util.js";
import { build, visibleSet, visibleNodes } from "./model.js";
import { bindEvents, focus, reheat, start, stop, kick, fitView } from "./interaction.js";
import { selectNode, renderPanel, renderRiskPanel, showRiskPanel, showBottleneckPanel, renderBottleneckPanel } from "./panels.js";
import { initTreeView, toggleTreeView } from "./treeview.js";
import { computeMetrics } from "../lib/analytics.js";
import { draw, syncSize, resize } from "./render.js";

function init(opts, data) {
  opts = opts || {};
  // 运行时数据注入（Plan C）：首页改为在浏览器端 fetch 数据，而非构建期内联。
  // 传入 data 时写入全局 window.SUPPLY_DATA（model.build() 的唯一事实来源）；
  // 未传则沿用已设置的全局（测试 / 其它调用方可能已直接赋值），保证向后兼容。
  if (data) window.SUPPLY_DATA = data;
  if (!window.SUPPLY_DATA) throw new Error("GraphEngine.init: 缺少图数据（window.SUPPLY_DATA 或 init 的 data 参数）");
  S.reportLink = opts.reportLink || null;
  S.mapLink = opts.mapLink || null;
  S.cv = document.getElementById("cv");
  if (!S.cv) throw new Error("GraphEngine.init: #cv not found");
  S.ctx = S.cv.getContext("2d");
  build();
  bindEvents();
  return api;
}

var api = {
  init: init,
  start: start,
  stop: stop,
  focus: focus,
  reheat: reheat,
  resize: resize,
  fitView: fitView,
  esc: esc,
  safeUrl: safeUrl,
  visibleNodes: visibleNodes,
  // 树状视图（第三种视图）：Apple → 产品线 → 产品 → 零部件；点击零部件打开独立详情栏
  initTreeView: initTreeView,
  toggleTreeView: toggleTreeView,
  // 风险视图开关：开启后节点按脆弱性着色 + 单点标记；弹出右侧「风险因子说明」面板
  setRiskMode: function (on) {
    S.riskMode = !!on;
    var panel = document.getElementById("panel");
    if (S.riskMode) {
      showRiskPanel(true);
      if (panel) panel.style.display = "none";
      renderRiskPanel(S.selected || null);
    } else {
      showRiskPanel(false);
      if (S.selected) { renderPanel(S.selected); if (panel) panel.style.display = "block"; }
    }
    if (S.running) kick();
    else if (S.cv) draw(visibleSet());
    updateLegends();
  },
  // 瓶颈透视开关（feat/graph-analytics）：开启后节点按瓶颈指标热力着色，弹出右侧瓶颈面板。
  // 与风险视图互斥：开启瓶颈时自动退出风险视图，避免两种着色/面板叠加。
  setBottleneckMode: function (on) {
    S.bottleneckMode = !!on;
    var panel = document.getElementById("panel");
    if (S.bottleneckMode) {
      computeMetrics();              // 惰性计算并缓存（首次开启时）
      S.riskMode = false; showRiskPanel(false);
      showBottleneckPanel(true);
      if (panel) panel.style.display = "none";
      renderBottleneckPanel(S.selected || null);
    } else {
      showBottleneckPanel(false);
      if (S.selected) { renderPanel(S.selected); if (panel) panel.style.display = "block"; }
    }
    if (S.running) kick();
    else if (S.cv) draw(visibleSet());
    updateLegends();
  },
  // 瓶颈着色指标切换：reach（按波及范围）/ pagerank（按网络核心度）。
  // 不仅重绘图谱着色，还要重渲染右侧面板（概览排行随指标切换；选中节点详情显示当前指标排名），
  // 否则用户切换指标时右侧「组件数据无变动」，无法感知差异（feat 修复）。
  setBottleneckMetric: function (kind) {
    S.bottleneckMetric = (kind === "pagerank") ? "pagerank" : "reach";
    if (S.bottleneckMode) {
      renderBottleneckPanel(S.selected || null);
      showBottleneckPanel(true);
    }
    if (S.running) kick();
    else if (S.cv) draw(visibleSet());
  },
  getMetrics: function () { return computeMetrics(); },
  getViewport: function () { return { ox: S.view.ox, oy: S.view.oy, scale: S.view.scale }; }
};

// 模式感知图例：仅瓶颈/风险视图显示「权重图例」(#weightLegend)，并据模式切换标题/提示文案。
// 类型图例(#nodeLegend)始终显示——因为节点填充色在所有模式下都表示「类型」，不再与权重撞色。
function updateLegends() {
  var box = document.getElementById("weightLegend");
  if (!box) return;
  var title = document.getElementById("wlTitle");
  var hint = document.getElementById("wlHint");
  var focusRow = document.getElementById("wlFocusRow");
  if (S.bottleneckMode) {
    box.style.display = "flex";
    if (title) title.textContent = i18nText("bottleneck.ringTitle");
    if (hint) hint.textContent = i18nText("bottleneck.ringHint");
    if (focusRow) focusRow.style.display = "flex";   // 洋红环 = 当前查看的排行项
  } else if (S.riskMode) {
    box.style.display = "flex";
    if (title) title.textContent = i18nText("risk.ringTitle");
    if (hint) hint.textContent = i18nText("risk.ringHint");
    if (focusRow) focusRow.style.display = "none";    // 洋红聚焦环仅瓶颈详情使用
  } else {
    box.style.display = "none";
  }
}

// 挂全局，保持 graph_bootstrap.js 通过 window.GraphEngine 使用的契约
window.GraphEngine = api;
