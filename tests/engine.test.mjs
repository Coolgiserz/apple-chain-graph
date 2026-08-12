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
  cbS: makeEl({ classList: { add: () => {}, remove: () => {}, toggle: () => {} } }),   // 现为「展开全部」按钮（onclick 切换 S.showAll）
  panel: makeEl(),
  pbody: makeEl(),
  bottleneckPanel: makeEl({ style: { display: "none" } }),
  bnBody: makeEl(),
  reset: makeEl(),
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
const dispatched = [];   // 记录 document.dispatchEvent 派发的事件类型（验证 sc:select / sc:view 联动契约）
globalThis.CustomEvent = class { constructor(type, init) { this.type = type; this.detail = (init && init.detail) || {}; } };
globalThis.document = {
  getElementById: (id) => registry[id] || null,
  createElement: () => makeEl(),
  addEventListener: () => {},
  querySelectorAll: () => [],
  readyState: "complete",
  dispatchEvent: (evt) => { dispatched.push(evt.type); return true; },
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
  "visibleNodes", "setRiskMode", "setBottleneckMode", "setBottleneckMetric", "getMetrics", "getViewport", "fitView"];
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

check("点击「展开全部供应商」(cbS) 后供应商出现", () => {
  assert.equal(typeof registry.cbS.onclick, "function", "cbS 应绑定 onclick 切换 S.showAll");
  registry.cbS.onclick();   // 触发展开全部
  const hasSupplier = api.visibleNodes().some((n) => n.type === "Supplier");
  assert.ok(hasSupplier, "展开全部后应有供应商节点");
  registry.cbS.onclick();   // 再次点击 = 收起全部（同时清除逐项展开），回到默认隐藏
});

check("setRiskMode(true/false) 不抛错（真实命中 draw/render）", () => {
  assert.doesNotThrow(() => api.setRiskMode(true));
  assert.doesNotThrow(() => api.setRiskMode(false));
});

check("setBottleneckMode(true/false) + getMetrics 不抛错且产出结构指标", () => {
  assert.doesNotThrow(() => api.setBottleneckMode(true));
  const m = api.getMetrics();
  assert.ok(m && !m.empty, "getMetrics 应返回非空指标对象");
  assert.ok(Array.isArray(m.topByReach), "应含 topByReach 排行数组");
  // fixture：tsmc 供应 soc，soc 被 iphone 使用 → tsmc 的波及产品数应为 1
  assert.equal(m.info["S:tsmc"].reach, 1, "tsmc 断供应波及 1 款产品（iphone）");
  assert.equal(m.info["C:soc"].reach, 1, "soc 被 1 款产品使用（iphone）");
  assert.ok(typeof m.geoCN === "number", "应含地理集中度 geoCN");
  // 切回指标不应抛错，且面板隐藏
  assert.doesNotThrow(() => api.setBottleneckMetric("pagerank"));
  assert.doesNotThrow(() => api.setBottleneckMode(false));
});

check("瓶颈面板渲染：开启后 bnBody 含排行节点可点击聚焦（li.rel[data-key]）", () => {
  api.setBottleneckMode(true);
  const html = registry.bnBody.innerHTML || "";
  assert.ok(html.includes("li class='rel'") || html.includes('class="rel"'), "概览应渲染可点击排行行");
  api.setBottleneckMode(false);
});

check("切换指标（波及范围↔网络核心度）后面板内容应变化（修复右侧无感知）", () => {
  api.setBottleneckMode(true);
  api.setBottleneckMetric("reach");
  const htmlReach = registry.bnBody.innerHTML || "";
  api.setBottleneckMetric("pagerank");
  const htmlPR = registry.bnBody.innerHTML || "";
  assert.notEqual(htmlReach, htmlPR, "切换指标后右侧面板（说明+排行）应发生变化");
  // pagerank 排行应出现 reach 排行中没有的节点（iPhone 产品节点）。
  const prHasProduct = htmlPR.includes("iPhone") && !htmlReach.includes("iPhone");
  assert.ok(prHasProduct, "网络核心度排行应包含产品节点（reach 排行不含）");
  api.setBottleneckMode(false);
});

check("瓶颈模式选中节点：详情显示统计卡且受影响列表带数量（修复数字对应）", () => {
  api.setBottleneckMode(true);
  api.setBottleneckMetric("reach");
  const m = api.getMetrics();
  const sup = m.topByReach.find((r) => r.key.startsWith("S:"));
  assert.ok(sup, "应有供应商进入 reach 排行");
  api.focus(sup.key);
  const html = registry.bnBody.innerHTML || "";
  assert.ok(html.includes("bn-stat-row"), "详情应含统计卡行（醒目呼应排行数字）");
  assert.ok(/sharedProducts（\d+）/.test(html) || html.includes("sharedProducts"), "共用组件的产品列表应带数量标题");
  api.setBottleneckMode(false);
});

check("focus() 不抛错", () => {
  assert.doesNotThrow(() => api.focus("S:tsmc"));
});

check("esc() 转义 HTML 特殊字符（含引号）", () => {
  assert.equal(api.esc("<b>&'</b>\"x"), "&lt;b&gt;&amp;&#39;&lt;/b&gt;&quot;x");
  // 外链白名单：仅 http(s) 放行，危险协议返回空
  assert.equal(api.safeUrl("javascript:alert(1)"), "");
  assert.equal(api.safeUrl("https://example.com/a"), "https://example.com/a");
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

// ---- 新增联动 / 交互契约（严苛标准）----
check("focus() 派发 sc:select 且使隐藏供应商变为可见（修复 P2 选中找不到）", () => {
  dispatched.length = 0;
  api.focus("S:tsmc");
  assert.ok(dispatched.includes("sc:select"), "focus 应广播 sc:select（反向联动表格/面板）");
  const vis = api.visibleNodes().some((n) => n._key === "S:tsmc");
  assert.ok(vis, "聚焦隐藏供应商后该节点应变为可见（否则「选中了却找不到」）");
});

check("右侧面板为供应商展示上下游关系（修复空关系列表 + 不再输出原始边类型码）", () => {
  const html = registry.pbody.innerHTML || "";
  assert.ok(html.includes("SoC") && html.includes("iPhone"),
    "供应商面板应包含其上游节点（SoC / iPhone）关系，实际：" + html.slice(0, 160));
  assert.ok(!html.includes("<b>"), "不应再输出原始边类型码 <b>USES</b> 等");
});

check("点击「展开全部」派发 sc:view（表格据此刷新，修复联动断点）", () => {
  dispatched.length = 0;
  registry.cbS.onclick();        // 展开全部
  assert.ok(dispatched.includes("sc:view"), "cbS 切换应广播 sc:view（按钮不触发 input，表格靠此刷新）");
  registry.cbS.onclick();        // 收起全部，回到默认
});

check("重置视图派发 sc:view", () => {
  dispatched.length = 0;
  registry.reset.onclick();
  assert.ok(dispatched.includes("sc:view"), "reset 应广播 sc:view");
});

if (failures > 0) {
  console.error("\n✗ 引擎测试失败：" + failures + " 项");
  process.exit(1);
}
console.log("\n✓ 引擎测试全部通过");
