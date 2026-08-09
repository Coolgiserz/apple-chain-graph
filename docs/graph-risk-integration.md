# 供应链脆弱性数据 → 图谱集成方案（设计文档）

> 状态：**设计阶段**，尚未实现。本文件对齐 `tools/supplier_research/risk.py` 已产出的
> `tools/output/supply_chain_risk.json`，规划如何把脆弱性数据作为**图谱的附加功能**呈现。
> 读者：实现者（照「实现清单」落地）； reviewer（确认范围）。

## 1. 目标

把「零部件 → 产品 → 产品线」脆弱性分析的结果，从纯报告（`supply_chain_risk.md/json`）
**叠加到交互式供应链图谱**上，让用户在图谱里直接看到：

- 哪些**组件 / 产品节点**最脆弱（按脆弱性着色）；
- 哪些组件是**单点依赖**（警示标记）；
- 点开任意节点，右侧信息框显示其**脆弱性指标**。

核心价值：图相对于表格报告的独有点在于「**脆弱环节在图上以红色 + ⚠ 浮现**」，一眼定位风险集群。

## 2. 可行性（已核对代码）

| 依据 | 现状 | 结论 |
|------|------|------|
| 数据对齐 | `supply_chain_risk.json` 的键即图节点 `component_id` / `product_id`，与 `data/apple_supply_chain.json` 节点一一对应 | 合并零成本 |
| 节点着色 | `graph_engine.js:203` `ctx.fillStyle = COLORS[n.type]` 已按类型着色 | 加「风险视图」分支即可 |
| 节点尺寸 | `graph_engine.js:199` 半径已含 `degree` 缩放 | 单点标记可叠加在节点外圈 |
| 信息框 | `graph_engine.js:249 renderPanel(n)` 已按 `n.type` 渲染字段行（`fieldRow`） | 追加风险字段行即可 |
| 顶部控件 | `graph_page.html` 已有筛选条 `#top`（类型复选 + 搜索 + 重置） | 加「风险视图」开关 + 图例 |
| 数据注入 | `build_viewer.py:31` 用 `json.dumps(DATA)` 注入 `__DATA__` | 注入前合并风险字段即可 |

**结论：完全可行，且为纯增量改动，不动现有图数据结构。**

## 3. 集成点总览

```
build_viewer.py  ──注入──▶  index.html (__DATA__ 含 vuln 字段)
                                    │
                                    ▼
graph_engine.js  draw()      ──风险视图──▶ 节点按脆弱性着色 + 单点⚠标记
               renderPanel() ──增强──────▶ 侧栏显示脆弱性指标
                                    │
                                    ▼
graph_page.html  #top       ──新增──────▶ 「风险视图」开关 + 颜色图例
```

## 4. 数据注入（`build_viewer.py`）

在 `main()` 读 `DATA` 之后、`.replace("__DATA__", ...)` 之前，加载风险 JSON 并合并：

```python
import os, json
RISK_JSON = os.path.join(ROOT, "tools", "output", "supply_chain_risk.json")

def merge_risk(data):
    rp = os.path.join(ROOT, "tools", "output", "supply_chain_risk.json")
    if not os.path.exists(rp):
        return data                      # 容错：缺文件则跳过，不报错
    risk = json.load(open(rp, encoding="utf-8"))
    comp = {c["component_id"]: c for c in risk.get("components", [])}
    prod = {p["product_id"]: p for p in risk.get("products", [])}
    for c in data["nodes"]["components"]:
        r = comp.get(c["id"])
        if r:
            c["vuln"] = r["vuln"]
            c["n_suppliers"] = r["n_suppliers"]
            c["single_point"] = r["single_point"]
    for p in data["nodes"]["products"]:
        r = prod.get(p["id"])
        if r:
            p["vuln"] = r["product_vuln"]
            p["sp_count"] = r["sp_count"]
            p["weakest"] = r["weakest"]
            p["weakest_component"] = r["weakest_component"]
    return data
```

合并进字段（节点原生携带，引擎 `draw` / `renderPanel` 直接读 `n.vuln` 等）：

| 节点类型 | 新增字段 | 来源（risk.json 路径） |
|----------|----------|------------------------|
| Component | `vuln`, `n_suppliers`, `single_point` | `components[].{vuln,n_suppliers,single_point}` |
| Product | `vuln`, `sp_count`, `weakest`, `weakest_component` | `products[].{product_vuln,sp_count,weakest,weakest_component}` |
| Supplier | 无 | 本模型不评分供应商节点 |

> 供应商节点不参与着色（模型不计算供应商脆弱性），保持原 `COLORS.Supplier` 颜色。

## 5. 节点着色（`graph_engine.js` `draw()`）

新增模块级状态 `var riskMode = false;`（由顶部开关切换）。

`draw()` 第 203 行附近改为：

```js
var fill;
if (riskMode && n.type !== "Supplier") {
  fill = vulnColor(n.vuln);          // 绿→琥珀→红
} else {
  fill = COLORS[n.type];
}
ctx.fillStyle = fill; ctx.fill();
```

颜色比例尺（脆弱性 ∈ [0,1]）：

```js
function vulnColor(v) {
  // 0.0 绿(#10b981) → 0.5 琥珀(#f59e0b) → 1.0 红(#ef4444)
  if (v >= 0.6) return "#ef4444";     // 高
  if (v >= 0.3) return "#f59e0b";     // 中
  return "#10b981";                   // 低
}
```

阈值与 `risk.py` 的 `HIGH_THRESHOLD` / `MEDIUM_THRESHOLD` 保持一致（0.6 / 0.3），可抽成常量。

**单点标记**：在 `draw()` 节点描边之后，对 `n.single_point` 的组件节点画一个外圈警示环：

```js
if (riskMode && n.type === "Component" && n.single_point) {
  ctx.beginPath();
  ctx.arc(n.x, n.y, r + 3, 0, Math.PI * 2);
  ctx.strokeStyle = "#ef4444"; ctx.lineWidth = 2; ctx.stroke();
}
```

> 可选增强：单点组件加一个小的 ⚠ 文本角标（在 `label` 绘制分支里判断）。

## 6. 信息框增强（`graph_engine.js` `renderPanel()`）

在 `fields` 定义处（`graph_engine.js:268-272`）按 `n.type` 追加风险字段行：

- **Component**：
  ```js
  fieldRow("vuln", n.vuln != null ? n.vuln.toFixed(3) : ""),
  fieldRow("n_suppliers", n.n_suppliers),
  fieldRow("single_point", n.single_point ? "⚠ 是（单点依赖）" : "否")
  ```
- **Product**：
  ```js
  fieldRow("vuln", n.vuln != null ? n.vuln.toFixed(3) : ""),
  fieldRow("sp_count", n.sp_count),
  fieldRow("weakest", n.weakest_component ? (nm("C", n.weakest_component) + "（" + (n.weakest||0).toFixed(3) + "）") : "")
  ```

字段标签走 i18n：在 `locales/*.json` 的 `field.*` 下加 `vuln` / `n_suppliers` / `single_point` /
`sp_count` / `weakest` 键（四语言）。`fieldRow` 已自动经 `i18nText("field."+k)`，无需改逻辑。

## 7. 顶部开关 + 图例（`graph_page.html` `#top`）

- 加一个 toggle 按钮「风险视图」（checkbox 或按钮，状态写入 `GraphEngine.riskMode`）。
  引擎需暴露 `setRiskMode(on)`：`riskMode = on; kick();`（重绘）。
- 加一个颜色图例（默认隐藏，风险视图开启时显示）：
  `🟥 高(≥0.6)  🟧 中(0.3–0.6)  🟩 低(<0.3)  ⚠ 单点依赖`。
- 开关文案走 i18n（`nav.riskMode` 等键）。

> 注意 `#top` 已有 `pointer-events:none`（仅表单控件可点），新增按钮须保持可点。

## 8. 构建顺序调整（`build_all.py`）

当前 STEPS：`build_viewer`（第 1 步）在 `run_risk`（第 5 步）**之前** →
`build_viewer` 注入时 `supply_chain_risk.json` 尚不存在。

改为把 `run_risk` 提到 `build_viewer` **之前**（与 `run_analysis` 同组，二者都纯本地、无依赖）：

```python
STEPS = [
    ("供应商估值  supplier_analysis.json",  "tools/run_analysis.py"),
    ("供应链风险  supply_chain_risk.json",  "tools/run_risk.py"),
    ("供应链图谱  index.html（首页）",      "scripts/build_viewer.py"),
    ("企业列表    supplier_table.html",     "scripts/build_table.py"),
    ("上下游报告  apple_supply_chain_report.html", "scripts/report.py"),
    ("供应商地图  supplier_geo.html",       "tools/geo_build.py"),
    ("估值看板    supplier_dashboard.html", "tools/build_dashboard.py"),
]
```

`build_viewer.py` 的 `merge_risk()` 已含**容错**（缺文件跳过），即使顺序未完全对齐也不会崩溃。
`run_risk` 不参与 `geo_build` 依赖，不影响其余页面。

## 9. i18n 影响

新增需翻译的键（四语言 `locales/*.json`）：

- `field.vuln` / `field.n_suppliers` / `field.single_point` / `field.sp_count` / `field.weakest`
- `nav.riskMode`（风险视图）/ `panel.riskLegend` 相关

译文在 `locales/*.json`，运行时由 `i18n.js` 解析；**不在 JS 里硬编码任何译文**（与现有 `i18nVal` 机制一致）。

## 10. 实现清单（落地步骤）

1. `build_viewer.py`：`merge_risk()` + 在 `main()` 调用；`run_risk` 已写入 `tools/output/`。
2. `build_all.py`：STEPS 把 `run_risk` 提到 `build_viewer` 之前。
3. `graph_engine.js`：
   - 新增 `riskMode` 状态 + `setRiskMode(on)` 暴露到 `GraphEngine`。
   - `draw()`：风险视图着色分支 + 单点外圈标记。
   - `renderPanel()`：组件 / 产品风险字段行。
   - 新增 `vulnColor(v)`（阈值常量与 `risk.py` 对齐）。
4. `graph_page.html` `#top`：「风险视图」开关 + 颜色图例（默认隐藏）。
5. `locales/*.json`：补 `field.vuln/n_suppliers/single_point/sp_count/weakest` + `nav.riskMode` 四语言。
6. 验证：`build_all.py` 通过；Playwright 真实 Chrome 检查——
   - 默认普通视图（着色不变）；
   - 开风险视图：组件/产品按脆弱性着色、`audio_codec` 显 ⚠ 红环；
   - 点 `audio_codec` 信息框显示「单点依赖：是、供应商数 1、脆弱性 1.000」；
   - 点某 iPhone 显示其脆弱性 + 单点部件数 + 最弱环节组件；
   - 切语言（en/fr/ja）风险标签正确翻译；零 JS 错误。

## 11. 风险与边界

- **缺文件容错**：CI 首次全新 checkout 若顺序异常导致 `supply_chain_risk.json` 缺失，`merge_risk` 跳过 → 图谱仅缺风险着色，不报错、不白屏。
- **数据新鲜度**：风险字段在构建期注入，随 `run_risk` 重算自动更新；与 `supply_chain_risk.md` 同源，不会漂移。
- **性能**：着色仅改 `fillStyle`，单点标记仅对单点组件（当前仅 1 个）额外画环，开销可忽略。
- **不破坏现有交互**：`riskMode=false` 时行为与现完全一致（着色、点查、跨页深链、侧栏联动不变）。

## 12. 未来可扩展（非本次范围）

- **伪冗余高亮**：同国多源组件（地理分散度=1）用特殊描边，提示「看似双源、实则单国」。
- **断供情景**：点某供应商 → 一键灰掉其供应组件、并高亮受影响的下游产品（爆破半径）。
- **产品线汇总层**：风险视图叠加按 `product_line` 的脆弱性区间着色 / 聚合气泡。
