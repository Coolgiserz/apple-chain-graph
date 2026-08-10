// 引擎打包产物的契约 / 冒烟测试（Node，无需浏览器）。
// 用最小 DOM 桩加载 dist/graph_engine.js（esbuild 打包后的 IIFE），断言：
//   1) 打包成功并对外暴露 window.GraphEngine 及其文档化 API；
//   2) init() 能从 fixture 装配图、不抛错，getViewport 返回有效视口；
//   3) visibleNodes() 在默认筛选下返回全部节点（真实命中 model.js 逻辑）；
//   4) setRiskMode / focus / selectNode 调用不抛错（真实命中 render/interaction/panels）。
//
// 运行：node tests/engine.test.mjs   （需在 npm run build 之后，dist/graph_engine.js 已生成）
import assert from "node:assert/strict";
import { fileURLToPath } from "node:url";
import path from "node:path";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const bundlePath = path.join(__dirname, "..", "dist", "graph_engine.js");

// ---- 最小 DOM / Canvas 桩 ----
const ctxStub = new Proxy({}, {
  get(_t, prop) {
    if (prop === "measureText") return () => ({ width: 0 });
    if (prop === "canvas") return canvas;
    return () => {}; // 任何绘制方法都视为 no-op
  },
  set() { return true; },
});

const makeEl = (extra = {}) => Object.assign({
  style: {},
  classList: { add: () => {}, remove: () => {} },
  addEventListener: () => {},
  appendChild: () => {},
  getContext: () => ctxStub,
  getBoundingClientRect: () => ({ left: 0, top: 0, width: 800, height: 600 }),
  clientWidth: 800,
  clientHeight: 600,
  width: 800,
  height: 600,
  value: "",
  checked: true,
  textContent: "",
}, extra);

// 画布初始后备尺寸故意与 CSS 尺寸(800x600)不一致，模拟浏览器默认 300x150，
// 使 syncSize() 触发尺寸设置并把 canvasReady 置真（否则静止分支永不触发）。
const canvas = makeEl({ width: 300, height: 150 });

const registry = {
  cv: canvas,
  line: makeEl({ value: "" }),
  q: makeEl({ value: "" }),
  cbP: makeEl({ checked: true }),
  cbC: makeEl({ checked: true }),
  cbS: makeEl({ checked: false }),   // 新默认：供应商隐藏，需展开/勾选「全部供应商」
  flow: makeEl({ classList: { add: () => {}, remove: () => {}, toggle: () => {} } }),
  panel: makeEl(),
  langSwitch: makeEl({ value: "" }),
  insightCard: makeEl({ style: { display: "none" } }),
  insScale: makeEl(),
  insLine: makeEl(),
  insSP: makeEl(),
  insFocus: makeEl(),
  insightClose: makeEl(),
  insightToggle: makeEl(),
};

globalThis.window = globalThis;
globalThis.document = {
  getElementById: (id) => registry[id] || null,
  createElement: () => makeEl(),
  addEventListener: () => {},
  querySelectorAll: () => [],
  readyState: "complete",
  dispatchEvent: () => {},
};
globalThis.location = { search: "", href: "http://localhost/" };
globalThis.history = { replaceState: () => {} };
// 队列式 rAF：把回调入队，由测试在 start() 后手动排空，驱动动画循环直到静止（非递归，避免爆栈）。
let rafQ = [];
globalThis.requestAnimationFrame = (cb) => { rafQ.push(cb); return rafQ.length; };
globalThis.cancelAnimationFrame = () => {};
globalThis.addEventListener = () => {}; // window.addEventListener（mouseup/resize 绑定）

// ---- fixture 数据（需匹配 model.js build() 期望的 window.SUPPLY_DATA 结构）----
globalThis.SUPPLY_DATA = {
  nodes: {
    products: [{ id: "iphone", name: "iPhone", product_line: "iPhone" }],
    components: [{ id: "soc", name: "SoC", product_line: "iPhone" }],
    suppliers: [{ id: "tsmc", name: "TSMC" }],
  },
  edges: {
    uses_component: [{ from: "iphone", to: "soc" }],
    supplied_by: [{ from: "soc", to: "tsmc", share: 1.0, note: "" }],
    assembled_by: [{ from: "iphone", to: "tsmc" }],
  },
};

let failures = 0;
function check(name, fn) {
  try { fn(); console.log("  ✓ " + name); }
  catch (e) { failures++; console.error("  ✗ " + name + "\n    " + e.message); }
}

await import(bundlePath);

check("window.GraphEngine 已暴露且为对象", () => {
  assert.equal(typeof window.GraphEngine, "object");
});

const api = window.GraphEngine;
const expected = ["init", "start", "stop", "focus", "reheat", "resize", "esc",
  "visibleNodes", "setRiskMode", "getViewport", "fitView"];
expected.forEach((m) => {
  check("api." + m + " 是可调用函数", () => {
    assert.equal(typeof api[m], "function", "期望 " + m + " 为函数");
  });
});

check("init() 装配图且不抛错", () => {
  assert.doesNotThrow(() => api.init({}));
});

check("getViewport() 返回有效视口", () => {
  const vp = api.getViewport();
  assert.equal(typeof vp.scale, "number");
  assert.equal(typeof vp.ox, "number");
  assert.equal(typeof vp.oy, "number");
});

check("visibleNodes() 默认隐藏供应商（仅显示 产品线/产品/零部件 三层）", () => {
  const nodes = api.visibleNodes();
  const types = {};
  nodes.forEach((n) => { types[n.type] = (types[n.type] || 0) + 1; });
  assert.equal(types.Supplier, undefined, "默认不应显示供应商节点");
  assert.ok(types.Line >= 1 && types.Product >= 1 && types.Component >= 1,
    "默认应含 产品线/产品/零部件（实际 " + JSON.stringify(types) + "）");
});

check("勾选「展开全部供应商」(cbS) 后供应商出现", () => {
  registry.cbS.checked = true;
  const hasSupplier = api.visibleNodes().some((n) => n.type === "Supplier");
  assert.ok(hasSupplier, "展开全部后应有供应商节点");
  registry.cbS.checked = false;   // 复位为默认（隐藏）
});

check("setRiskMode(true/false) 不抛错（真实命中 draw/render）", () => {
  assert.doesNotThrow(() => api.setRiskMode(true));
  assert.doesNotThrow(() => api.setRiskMode(false));
});

check("focus() 不抛错", () => {
  assert.doesNotThrow(() => api.focus("S:tsmc"));
});

check("esc() 转义 HTML 特殊字符", () => {
  assert.equal(api.esc("<b>&'</b>"), "&lt;b&gt;&amp;'&lt;/b&gt;");
});

check("fitView() 不抛错且将视口缩放到有效正值", () => {
  assert.doesNotThrow(() => api.fitView());
  const vp = api.getViewport();
  assert.ok(vp.scale > 0 && Number.isFinite(vp.scale), "scale 应为有限正值，实际 " + vp.scale);
});

// 驱动动画循环到静止，验证「关键洞察」浮层首屏自动弹出并填充内容（Option A）。
check("settle 后关键洞察浮层弹出且填充内容", () => {
  rafQ = [];
  assert.doesNotThrow(() => api.start());
  let n = 0;
  while (rafQ.length && n < 6000) { const cb = rafQ.shift(); cb(); n++; }
  const card = registry.insightCard;
  assert.equal(card.style.display, "block", "静止后浮层应显示（display=block），实际 " + card.style.display);
  assert.ok(registry.insScale.textContent.length > 0, "规模文本应非空");
  assert.ok(registry.insFocus.textContent.length > 0, "重点关注节点文本应非空");
});

if (failures > 0) {
  console.error("\n✗ 引擎测试失败：" + failures + " 项");
  process.exit(1);
}
console.log("\n✓ 引擎测试全部通过");
