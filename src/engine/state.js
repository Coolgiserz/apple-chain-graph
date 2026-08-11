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
  criticalId: null,        // 首屏静止后自动高亮的最关键节点（信息浮层用，非动画）
  insightsShown: false,    // 关键洞察卡是否已在本会话展示过（仅首屏静止时弹一次）
  expanded: new Set(),     // 渐进式展开：已展开（显示其供应商）的产品/零部件节点 key 集合
  showAll: false,          // 「展开全部供应商」全局开关（与逐项展开解耦，见 P0-2）
  showBases: false,        // 「生产基地」全局开关：显示 ProductionBase 节点（默认隐藏，与供应商同层按需展开）
  flow: true,              // 沿边流动粒子动画开关（开启时图谱持续「活着」，不会冻结成静态）
  // 无障碍/性能：尊重系统「减少动效」偏好；静止且无交互一段时间后可停止 rAF 省电（见 P0-4）
  lastInteract: (typeof Date !== "undefined" ? Date.now() : 0),
  flowIdle: 15000,         // 流动开启后，静止且空闲超过该毫秒数则停止循环（交互时自动重启）
};

// 启动即读取系统偏好：reduced-motion 用户默认关闭流动粒子，避免前庭刺激与无谓耗电。
(function initMotionPref() {
  try {
    if (typeof window !== "undefined" && window.matchMedia &&
        window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      S.flow = false;
    }
  } catch (e) { /* 无 matchMedia 时保持默认 true */ }
})();

// 物理阻尼与停机阈值
export const ALPHA_MIN = 0.005;
export const ALPHA_DEC = 0.008;

// 脆弱性颜色阈值（与 risk.py 的 HIGH_THRESHOLD=0.6 / MEDIUM_THRESHOLD=0.3 对齐）
export const RISK_HIGH = 0.6;
export const RISK_MED = 0.3;
