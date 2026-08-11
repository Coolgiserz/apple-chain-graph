# 供应链瓶颈透视（图分析）方法

> 配套模块：`src/lib/analytics.js` + 引擎集成（`render.js` / `panels.js` / `index.js` / `state.js` / `interaction.js`）
> 数据来源：`data/apple_supply_chain.json`（图谱单一来源，纯标准库、零三方依赖）
> 计算位置：**纯前端**，浏览器内实时计算，无后端、无网络请求。

本页是「供应链瓶颈透视」功能的**技术细节文档**。README 中只放了一段精简说明 + 本页链接。

---

## 1. 目标

在已有的「产品 → 零部件 → 供应商」三层有向图上，直接做经典图分析，回答三类问题：

1. **类型感知度中心性**：一个零部件被多少产品复用？一个供应商供应多少种零部件？（结构性重要度）
2. **断供波及（反向可达）**：如果某一供应商 / 零部件断供，会波及多少款产品？其中多少款真正会停产（无替代）？
3. **网络核心度（PageRank）**：哪些节点被最多的上游路径所依赖，是网络中的「汇聚枢纽」？

产物是产品化的交互层（独家供应 / 断供影响模拟 / 网络核心度），不向用户暴露原始指标数字，只通过语义色与排行呈现。

## 2. 图结构与边方向（决定所有语义）

| 关系 | 方向 | 含义 |
|------|------|------|
| `USES_COMPONENT` | Product → Component | 产品使用某零部件 |
| `SUPPLIED_BY` | Component → Supplier | 零部件由某供应商提供 |
| `ASSEMBLED_BY` | Product → Supplier | 产品由某代工厂组装 |

即出边指向 **Product → Component → Supplier**，**Supplier 是汇点（无出边）**。所有指标都基于这套方向推导，引擎从 `SUPPLIED_BY` 边反推 `compSup`（零部件→供应商集合），不依赖任何冗余字段。

## 3. 算法

### 3.1 类型感知度中心性（Type-aware Degree Centrality）

不混用节点类型，按类型分别统计入/出度：

- **零部件复用率** `reuse(c)` = `USES_COMPONENT` 入边数量 = 使用该零部件的产品数。
- **供应商供应广度** `breadth(s)` = `SUPPLIED_BY` 出边数量 = 该供应商供应的零部件种数。
- **单点依赖**：`SUPPLIED_BY` 入边数 `n_c = 1` 的零部件即为单点（如 `audio_codec → Cirrus Logic`）；`n_c` 越大越可替代。

入度 / 出度按节点类型拆分后归一化，作为「关键度权重」用于红环着色（见第 5 节）。

### 3.2 断供波及（反向可达 BFS / Reach）

对**供应商**或**零部件**做两跳下游遍历，统计受影响产品：

```
供应商 s:
  comps   = { c | s -[SUPPLIED_BY]-> c }                       # 第 1 跳：供应的零部件
  reach(s)= { p | ∃ c∈comps, p -[USES_COMPONENT]-> c }          # 第 2 跳：使用这些零部件的产品（去重计数）
  noAlt(s)= { p∈reach(s) | 其某 component 仅有 1 家供应商 }       # 真正会停产（无替代）的产品

零部件 c:
  reach(c)= { p | p -[USES_COMPONENT]-> c }                     # 复用它的产品（reuse == reach）
  noAlt(c)= reach(c) 中那些 c 本身即单点依赖的产品
```

- `reach` 表示「波及范围」，**不等于停产数量**；多源零部件虽被波及，但可切换到其他供应商，不会停产。
- `noAlt` 才是「无替代将真正停产」的产品集合。当前数据下多数高 `reach` 供应商 `noAlt = 0`（如歌尔股份：`speaker` 28 款 + `mic` 27 款，去重 28 款，但两者均多源 → `noAlt = 0`）。

### 3.3 网络核心度（PageRank）

标准 PageRank，`d = 0.85`，`60` 次迭代，sink 节点概率回填：

```
PR(v) = (1-d)/N + d × Σ_{u→v} PR(u)/outdeg(u)
```

- 因 **Supplier 是汇点（无出边）**，PageRank 权重会汇聚到「被最多上游路径指向」的节点——即供货多零部件、被多产品依赖的**上游汇聚枢纽**（供应商与零部件）。
- 这是合理的「上游核心度」，但语义不同于通用「全局最重要节点」；与断供波及（反向可达）视角互补。

## 4. 指标如何对照排行

`computeMetrics()` 产出 `topByReach` 与 `topByPagerank` 两个排行：

- `topByReach`：按 `reach`（断供波及产品数）降序，用于「断供影响模拟」。
- `topByPagerank`：按 `PR` 降序，用于「网络核心度」。

`compSup` 由 `SUPPLIED_BY` 边推导，是 `reach` / `noAlt` 计算的唯一数据来源（见第 2 节）。

## 5. 可视化映射（填充 = 类型，红环 = 权重）

为避免「颜色撞色」混淆，节点采用**两个独立视觉通道**：

- **填充色 = 节点类型**：Product / Component / Supplier / Line（产品线聚合）/ Base（生产基地）各一色。
- **红色热环 = 关键度权重**（由度中心性 / PageRank 归一化到 0–1，越红越粗越关键），**不占用填充色**。
- 选中节点：白色粗环；聚焦（点击排行项）节点：青色环；单点依赖：琥珀环；首屏关键洞察：白色虚线环。

权重图例（`#weightLegend`）独立于节点类型图例（`#nodeLegend`），明确区分「颜色代表类型」与「红环代表权重」。

## 6. 交互：第 2 跳下游高亮与文案澄清

- **第 2 跳高亮**：选中**供应商 / 零部件**时，图谱高亮集合从 1 跳邻居扩展到**第 2 跳下游产品**（供应商→所供零部件→使用这些零部件的产品），让「断供波及 N 款」在图上直接可见。选中**产品 / 基地**保持 1 跳行为。
- **文案澄清**：详情面板把「波及产品数」与「无替代将停产数」拆开；后者用独立 callout（0 = 绿✓安全，> 0 = 红⚠风险），并明确「『波及』仅表示共用该供应商零件，不代表都会停产」，避免把 28 款误读成「28 款都停产」。

## 7. 已知现象与局限

- **可见层 `reach` ↔ `PageRank` 高度相关**：在默认可见集（产品 + 零部件）上，两者 Pearson 相关约 **0.982**，供应商层仅 0.278。因此默认视图下切换两种指标，图谱着色变化很小（数字仍不同）。缓解方式：切换时重渲染右侧面板 + 显示「在当前指标排行中第 N 位」+ 动态说明文案。可选的进一步增强（未做）：PageRank 反向构图、切到核心度时自动展开供应商。
- **供应商层默认隐藏**：供应商默认不显示，需展开 / 搜索才可见；排名靠前的供应商多在隐藏层，首次查看建议展开供应商。
- **单点快照**：所有结论基于某一时点公开资料的 AI 归纳，可能含错漏 / 幻觉，以官方一手披露为准；不构成投资 / 采购建议。

## 8. 实现与构建

- 算法：`src/lib/analytics.js`（`computeMetrics()` / `getMetrics()`，`compSup` 由 `links` 推导）。
- 引擎集成：`state.js`（bottleneckMode / metric / metrics）、`render.js`（metricColor 优先级链 + `heatRing` + 第 2 跳 `nb`）、`panels.js`（`renderBottleneckPanel`）、`interaction.js`（点击排行项聚焦）、`index.js`（`setBottleneckMode` / `setBottleneckMetric` / `getMetrics`）、`util.js`。
- i18n：`locales/{zh,en,fr,ja}.json`；由 `scripts/build_locales.mjs` 单一来源生成 `dist/locales.js` 并做引用键审计（缺失即失败），覆盖所有 `make` / Docker 构建入口。
- 校验：
  - `node tests/engine.test.mjs`：引擎契约 / 冒烟测试（含面板 HTML 不含原始边类型码、第 2 跳高亮相关契约）。
  - `python3 tools/validate_dataset.py`：数据集交叉验证（含「被使用却无供应商的零部件」检查）。
  - `npm run build` / `python3 build_all.py`：前端打包 + 全站构建。
