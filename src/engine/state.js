// state.js — 引擎共享可变状态（单一对象，便于 ES Module 的 live-binding 跨模块传播）。
// 各模块通过 `S.xxx` 读写；重新赋值用 S.nodes = [] 而非重绑导入变量，
// 这样其它模块导入的 S 引用始终指向同一对象，属性变更对所有模块可见。
export const S = {
  nodes: [], links: [], adj: {}, idMap: {},
  cv: null, ctx: null,
  view: { ox: 0, oy: 0, scale: 1 },
  alpha: 1, running: false, animating: false, rafId: null, canvasReady: false,
  selected: null, hover: null, dragNode: null, panning: false,
  last: { x: 0, y: 0 }, downNode: null, downX: 0, downY: 0,
  pointerDown: false, touchActive: false, pinching: false, pinchDist: 0, pinchScale: 1,
  DRAG_THRESH: 5,
  riskMode: false,
  reportLink: null, mapLink: null,
  pendingFocus: null,
  fitDone: false,
};

// 物理阻尼与停机阈值
export const ALPHA_MIN = 0.005;
export const ALPHA_DEC = 0.008;

// 脆弱性颜色阈值（与 risk.py 的 HIGH_THRESHOLD=0.6 / MEDIUM_THRESHOLD=0.3 对齐）
export const RISK_HIGH = 0.6;
export const RISK_MED = 0.3;
