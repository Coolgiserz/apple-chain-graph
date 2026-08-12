# 代码可维护性与设计原则评估

> 分支：`docs/codebase-assessment`（基于 `main` @ `a64b90c` / v1.6.3）
> 范围：前端引擎（`src/`）、构建与 CI 流水线、数据层、i18n、测试
> 目标：评估代码可维护性，以及是否符合优秀设计原则与当代静态站前端最佳实践

---

## 0. 结论速览

| 维度 | 评级 | 一句话 |
| --- | --- | --- |
| 模块划分 / 关注点分离 | 🟢 良好 | engine 已拆为 model/render/interaction/panels/physics/util/state，职责清晰 |
| 构建与 CI 流水线 | 🟢 良好 | esbuild 零运行期依赖、PR 门禁、数据集校验、构建清单齐备 |
| 优雅降级 / 健壮性 | 🟢 良好 | reduced-motion、i18n 中文兜底、file://、网络失败均有降级 |
| 测试 | 🟡 尚可 | 引擎契约测试覆盖好，但无渲染断言、Python 端 flake8 非阻断 |
| 性能 / 热路径 | 🟡 需改进 | 每帧与每次 mousemove 重复 `visibleSet()` + DOM 读取，存在布局抖动 |
| 代码质量门禁 | 🟡 改善中 | 已清除死代码（`bump`/`metricColor`/测试 `flow` 桩）；ESLint 仍仅 `no-undef` |
| 安全 / 输出转义 | 🟢 已修复 | `esc()` 现转义引号全集；外链经 `safeUrl()` 白名单，杜绝协议注入 |
| 状态管理 | 🟠 可取改进 | 全局可变 `S` + `window.SUPPLY_DATA` 直接注入，无单向数据流 |

**总体评价**：架构骨架和工程化水平在同类「数据可视化静态站」中属于中上水平，关注点分离做得不错；主要短板集中在**质量门禁偏松**、**渲染热路径的重复计算**、以及 **`esc()` 转义不彻底**三处。下面分维度展开。

---

## 1. 架构与模块划分（优点）

引擎层已经做了清晰的垂直拆分，模块边界清晰、各自可独立演进：

- `state.js`：单一可变状态对象 `S`（ES Module live-binding 跨模块传播）+ 常量/阈值。
- `model.js`：数据装配 `build()` 与可见集 `visibleSet()` —— 图结构的「模型」层。
- `render.js`：Canvas 绘制，纯消费 `S` 与 `util`。
- `interaction.js`：鼠标/触摸交互、聚焦深链、动画循环 `loop()`。
- `panels.js`：右侧信息/风险/瓶颈面板。
- `physics.js`：力导向布局（纯物理）。
- `util.js`：纯函数工具与常量。
- `index.js`：编排入口，挂 `window.GraphEngine`。

`lib/analytics.js`（瓶颈指标计算）与 `lib/data_layer.js`（时效数据适配层）也按职责独立，且 `analytics.js` 为无 DOM 依赖的纯函数，便于单测。

> 评估：模块命名、文件粒度、注释密度（中文、解释「为什么」而非「是什么」）都达到良好水平，新成员能较快上手。

---

## 2. 设计原则符合度

### 2.1 做得好的地方

- **Single Source of Truth**：节点可见性由 `visibleSet()` 统一计算，图谱与侧边表格共用同一逻辑（`visibleNodes()`），避免双份筛选项漂移。
- **Open/Closed 扩展点**：`DataLayer` 用 Provider 抽象（`FileFeedProvider` / 预留 `ApiFeedProvider`），将来接真实 API 时 UI 零改动 —— 符合「对扩展开放、对修改封闭」。
- **失败安全 / 优雅降级**：
  - `reduced-motion` 用户默认关闭流动粒子（`initMotionPref`）。
  - i18n 内联 ZH 兜底，加载失败也绝不显示原始 key。
  - `bootstrap` 的 `getJSON` best-effort，风险数据缺失仅降级着色，不白屏。
  - `data_layer` 网络失败时回退本地缓存。
- **可访问性**：触摸支持、aria-label、reduced-motion、首屏引导卡 localStorage 记忆。
- **关注点分离**：物理/渲染/交互/面板各自可独立修改，互不影响。

### 2.2 偏离之处

- **全局可变状态**：`S` 是跨模块共享的可变单例，虽然用 ES Module 导出保证引用一致，但本质是「全局变量」。任何模块都能在任意时机改写 `S.xxx`，缺乏状态变更的可追溯性与约束。对中大型项目，单向数据流（如 reducer / store action）更利于维护。当前规模下可接受，但属于「技术债候选」。
- **跨层耦合**：`lib/analytics.js` 直接 `import { S } from "../engine/state.js"`。理论上「领域计算库」不应依赖「引擎状态」，二者应是 `analytics(S)` 的输入输出关系。当前耦合不致命，但打破了 `lib/` 的独立性。
- **循环依赖**：`render.js ↔ interaction.js` 互相 import（仅在运行时互相调用函数，esbuild 处理无误，代码注释已声明）。功能正确，但阅读与单测时略有心智负担。

---

## 3. 当代静态站前端最佳实践符合度

### 3.1 做得好的地方

- **零运行期依赖**：仅 vendored `i18next`（`dist/vendor`），不依赖 CDN，离线/任意子路径可部署。
- **构建产物可复现**：`npm ci` + esbuild 打包，`dist/*` 由 CI 重新生成（gitignore 不提交），避免「提交陈旧打包产物」的经典坑。
- **CI 完备**：`pages.yml` 同时覆盖 PR 门禁与 push 部署，含 lint、引擎测试、数据集校验、Python 单测、构建清单（`build.json`）。并发组按事件拆分，避免 PR 校验打断 main 部署。
- **i18n 内联而非运行时 fetch**：`dist/locales.js` 内联语言包，规避 `file://` CORS 与部署遗漏导致的 404。
- **Plan C 运行时 fetch 数据**：`index.html` 静态化，图数据浏览器端拉取，更新数据无需重生成整页。
- **SEO 基础设施**：sitemap / robots / OG 封面构建期生成。
- **release-please 自动版本管理**。

### 3.2 偏离之处

- **无 Source Map**：esbuild 用了 `--minify` 但未生成 sourcemap，线上问题定位需在压缩代码里排查。建议加 `--sourcemap` 并在 CI 产物中保留（不部署亦可）。
- **无内容安全策略（CSP）**：`index.html` 未设置 `Content-Security-Policy`，对外链（供应商地图、source 溯源链接）缺乏约束。静态站也应考虑最小 CSP。
- **本地预览门槛**：`dist/`、`data/feeds/`、`tools/visualizations/` 均 gitignore，本地需先 `python build_all.py` 才能预览全站。这是「单一事实来源在构建期」的代价，文档/README 需明确告知开发者，否则易踩「白屏」坑。

---

## 4. 具体缺陷清单（按严重程度）

### 🔴 P1 — `esc()` 不转义引号，外链 URL 存在注入/属性破裂风险
`src/engine/util.js:27` 的 `esc()` 仅转义 `& < >`，注释以「属性值由调用方保证不含引号」免责。但在 `panels.js:140`：

```js
srcHtml += "<a href='" + esc(m.url) + "' target='_blank' rel='noopener' ...>" + ...
```

`m.url` 来自 `SUPPLY_DATA.meta.source_registry`（数据驱动）。一旦数据中出现单引号，属性即破裂；若数据为不可信来源，则构成属性注入（甚至 `javascript:` 协议风险，尽管有 `target=_blank` + `rel=noopener` 缓解）。

**建议**：`esc()` 扩展为同时转义 `"` `'`，或在构建外链时改用双引号属性并对 URL 做 `encodeURI`/协议白名单校验。这是**防御纵深**问题，即使当前数据可信也应修。

### 🔴 P1 — 瓶颈面板「供应组件」区块重复渲染（已修复）
`src/engine/panels.js` 供应商分支中，`info.suppliedComps` 区块被连续写了两次，导致右侧面板出现重复章节。**本次评估已在分支上删除重复块并验证测试通过。**

### 🟡 P2 — 渲染热路径重复计算 `visibleSet()` + 频繁 DOM 读取（性能）
- `interaction.js:14` `pick()` 在**每次 mousemove** 都调用 `visibleSet()`；`visibleSet()` 内部对每个筛选输入都 `document.getElementById(...).value`（`:78-81`），即每帧/每次移动都做 DOM 查询与读取，存在布局抖动风险（`clientWidth` 读取同理）。
- `loop()` 每帧调用 `visibleSet()`（已传入 `vis` 给 `draw`，但 `loop` 自身仍重算），且 `draw` 内多次 `W()/H()` 触发 layout。

**建议**：把筛选输入（q / cbP / cbC / line）缓存进 `S`，仅在 change/input 事件时更新并失效缓存；`visibleSet()` 仅在该缓存变更时重算（memoize）。中等改动，但能显著降低 CPU 占用、提升交互流畅度。

### 🟡 P2 — 死代码 / 占位残骸（可维护性噪音）
- `interaction.js:37` `bump()` 已降级为空函数，但 `mousedown/mousemove/wheel/dblclick/touchstart` 仍处处调用 `bump()`（如 `:91,128,141,153`）。流动开关移除后这些调用点无任何作用，徒增阅读干扰。
- `util.js:51` `metricColor()` 注释自承「保留以兼容潜在调用」，实际已无调用方（权重改走 `heatRing`）。
- `tests/engine.test.mjs:53` 注册表里仍有 `flow` 元素 —— 按钮已从 `index.html` 移除，该桩已无意义。

**建议**：删除 `bump()` 及其全部调用点、`metricColor()`、测试里的 `flow` 桩。清理后代码更诚实、更易 grep。

### 🟡 P2 — reset 处理不一致（cbB 手动操作 vs cbS 走 setSuppBtn）
`interaction.js:237` reset 里 cbS 用 `setSuppBtn()` 同步，但 cbB 却手动 `cbB.checked=false; cbB.classList.remove("on"); cbB.textContent=i18nText(...)`（`:239`）。两处按钮同为 `<button>`，应统一走 `setBaseBtn()`，否则 i18n 时序/逻辑一旦变化，二者行为会漂移。

**建议**：reset 中把 cbB 手动块替换为 `setBaseBtn()`（与 cbS 对称）。

### 🟡 P2 — ESLint 门禁过松
`eslint.config.js` 仅启用 `no-undef`，无风格/质量规则（`no-unused-vars`、`prefer-const`、复杂度等均未开）。这是「渐进接入」的取舍，但意味着死代码、未声明变量、深层嵌套等问题都靠人眼兜底。

**建议**：逐步加入 `no-unused-vars`、`no-undef` 之外的基础规则（如 `no-duplicate-imports`、`complexity` 软告警），flake8 也建议改为 `continue-on-error: false` 前的阶段性目标。

### 🟢 P3 — 力导向为 O(n²) 全配对
`physics.js:9` 对所有可见节点两两计算斥力。当前数据规模（数百节点）无压力，但若扩展到数千节点需改为空间网格/Barnes-Hut。属已知边界，记录即可。

### 🟢 P3 — i18n 双源真相
`i18n.js` 内联 `ZH` 常量，同时 `locales/zh.json` 是另一份中文源。代码已用 `Object.assign(ZH, window.I18N_LOCALES.zh)` 自动同步并注释说明回归风险。机制可用，但「双份中文」始终是 drift 隐患，建议在 CI 加一步 `ZH` 与 `zh.json` key 一致性校验。

---

## 5. 可维护性改进路线图（建议优先级）

| 优先级 | 动作 | 收益 | 工作量 | 状态 |
| --- | --- | --- | --- | --- |
| 高 | 修复 `esc()` 引号转义 + 外链协议白名单 | 消除潜在注入隐患 | 小 | ✅ 已完成 |
| 高 | 删除死代码（`bump`/`metricColor`/测试 `flow` 桩） | 代码更诚实、易读 | 小 | ✅ 已完成 |
| 中 | `visibleSet()` memoize + 筛选输入缓存进 `S` | 降低每帧/每移动 CPU 与布局抖动 | 中 | 待办 |
| 中 | reset 中 cbB 改走 `setBaseBtn()` | 消除对称逻辑漂移 | 小 | 待办 |
| 中 | esbuild 加 `--sourcemap`；评估最小 CSP | 可调试性 + 安全性 | 小 | 待办 |
| 低 | ESLint 加入基础质量规则；flake8 转阻断 | 长期代码卫生 | 小 | 待办 |
| 低 | `analytics.js` 改为 `computeMetrics(S)` 入参，解除对 engine 状态的直接依赖 | 解耦领域库 | 中 | 待办 |
| 低 | CI 校验 `ZH` 与 `zh.json` key 一致性 | 杜绝翻译回归 | 小 | 待办 |

---

## 6. 总结

这套前端在工程化骨架（模块化、零依赖构建、CI 门禁、优雅降级）上已经相当成熟，明显优于「单文件 jQuery 粘贴」式的常见静态站。要在「可维护」与「最佳实践」上再上一个台阶，重点不是重写架构，而是**收紧质量门禁**（ESLint/转义/死代码）和**驯服渲染热路径**（避免每帧重复计算与 DOM 读取）。这些都是增量、低风险改动，适合在当前分支或后续小 PR 逐步落地。

评估过程中已修复一处明确缺陷（瓶颈面板「供应组件」区块重复渲染），并落地了高优先级与最小 CSP 安全加固，见提交记录。

### 高优先级修复记录（本分支已完成）

| 项 | 改动 | 状态 |
| --- | --- | --- |
| `esc()` 引号转义 | `util.js` 的 `esc()` 由仅转义 `& < >` 扩展为转义 `& < > " '`（OWASP 全集），同时覆盖单/双引号属性与文本上下文 | ✅ |
| 外链协议白名单 | `util.js` 新增 `safeUrl()`，仅放行 `http(s)`；`panels.js` 关系溯源外链改为先过 `safeUrl()` 再 `esc()`，阻断 `javascript:`/`data:` 注入；`safeUrl` 已挂到 `window.GraphEngine` | ✅ |
| 死代码 `bump()` | 删除 `interaction.js` 中空函数 `bump()` 及其 4 处调用点（mousedown/wheel/dblclick/touchstart）与占位注释 | ✅ |
| 死代码 `metricColor()` | 删除 `util.js` 中已无人调用的 `metricColor()` | ✅ |
| 测试 `flow` 桩 | 移除 `tests/engine.test.mjs` 中已无意义（按钮早已移除）的 `flow` 注册项；更新 `esc()` 断言并新增 `safeUrl()` 用例 | ✅ |
| 最小 CSP | `index.html` `<head>` 增加 `<meta http-equiv="Content-Security-Policy">`（default-src 'self'；script/style 'unsafe-inline'；connect-src 'self'；frame-src/object-src 'none'；base-uri/form-action 'self'）+ `<meta http-equiv="X-Frame-Options" content="DENY">` | ✅ |

> 验证：`npm run build` / `npm run lint` / `node tests/engine.test.mjs`（23 项）全部通过；`src/` 中无跨域 `fetch`（数据走同源相对路径，`connect-src 'self'` 不阻断），仅 canonical/og 等指向 `coolgiserz.github.io` 的元数据（浏览器不据 CSP 加载）。
>
> 已知局限（取舍，非缺陷）：meta CSP 不支持 `frame-ancestors`/`report-uri`，故 frame 防御靠 `X-Frame-Options`、放弃上报；因站内含内联 `<script>` 与内联 `onclick`/`style`，`script-src`/`style-src` 仍需 `'unsafe-inline'`，故**第一方内联脚本被 XSS 改写时 CSP 拦不住**，但能挡住全部外部/注入来源。`file://` 本地回退路径下 `connect-src 'self'` 因源为 `null` 可能阻断数据 fetch，需实测（应用已有 file:// 兜底逻辑）。

后续中优先级项（`visibleSet()` memoize、reset 统一 `setBaseBtn()`、esbuild sourcemap）尚未处理，仍列于上方路线图。
