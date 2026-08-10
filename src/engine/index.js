// index.js — 引擎入口：组装对外 API 并挂到 window.GraphEngine（IIFE 打包后行为与原 graph_engine.js 一致）。
// 把「物理 / 渲染 / 交互 / 面板」各自独立为模块后，此处只做编排，便于分模块协作。
import { S } from "./state.js";
import { W, H, esc } from "./util.js";
import { build, visibleSet, visibleNodes } from "./model.js";
import { bindEvents, focus, reheat, start, stop, kick } from "./interaction.js";
import { selectNode, renderPanel, renderRiskPanel, showRiskPanel } from "./panels.js";
import { draw, syncSize, resize } from "./render.js";

function init(opts) {
  opts = opts || {};
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
  esc: esc,
  visibleNodes: visibleNodes,
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
  },
  getViewport: function () { return { ox: S.view.ox, oy: S.view.oy, scale: S.view.scale }; }
};

// 挂全局，保持 graph_bootstrap.js 通过 window.GraphEngine 使用的契约
window.GraphEngine = api;
