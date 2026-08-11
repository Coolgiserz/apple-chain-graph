# 苹果生产基地 × 产品线关系调研

> **调研角色**：数据分析师 / 行业研究员
> **调研日期**：2026-08-11
> **目的**：评估能否收集足够数据，构建「产品线 → 苹果生产基地」的关系，用于拓展供应链图谱；
> 并**逐条标注数据来源与置信度**，确保可追溯；数据缺失处如实说明。
>
> **结论先行**：数据**足够支撑一个「中等粒度、带置信度与来源」的生产基地关系层**，但**无法做到官方逐厂逐型号级别**——
> Apple 从不公开逐厂产量与型号分配，所有归属均为「EMS（电子制造服务商）+ 所在地」的二级推断。
> 因此建议：以**基地（城市/省）为节点**、**产品线为关联**，每条边带 `operator`（代工厂）、`confidence`、`sources`，
> 而非声称"某厂精确生产某型号 X 万台"。
>
> **集成状态：✅ 已接入**（2026-08-11 核验通过后）。原始调研初稿 `data/production_bases.draft.json` 已归一化并入
> `scripts/generate.py` 的 `PRODUCTION_BASES`，重生成 `data/apple_supply_chain.json`（新增 `nodes.bases`、边
> `manufactured_at` / `operated_by`）及 Neo4j CSV（`bases.csv` / `product_lines.csv` / `rel_base_line.csv` /
> `rel_base_supplier.csv`）；前端引擎新增 `ProductionBase` 节点（粉色方块）、`MANUFACTURED_AT` / `OPERATED_BY` 边，
> 顶栏「展开全部生产基地」开关（默认隐藏，与供应商同层）。详见第六节。

---

## 一、可行性判断

| 维度 | 评估 | 说明 |
|------|------|------|
| 能否建立「产品线 ↔ 基地」关系 | ✅ 可以（中等粒度） | 国别/省级归属证据充分 |
| 能否细化到「型号 ↔ 具体厂房」 | ⚠️ 部分/推断 | Apple 不披露；仅个别厂有"主力机型"描述（如郑州 Pro/Pro Max） |
| 能否拿到产能/占比数字 | ⚠️ 仅聚合口径 | 印度 iPhone ~20–25%、中国整体 ~70%+、越南为 AirPods/Watch/iPad 强项；逐厂数字不可得 |
| 来源可追溯性 | ✅ 可控 | 本报告每条关系附 URL + 置信度；已区分强源/弱源 |
| 地图集成可行性 | ⚠️ 需补坐标 | 本报告未采集经纬度，避免编造；集成时需做地理编码 |

**推荐方案**：新增 `ProductionBase` 节点类型（属性：城市/省/国、`operator` EMS、`confidence`），
与现有 `Product`（产品线维度）建立 `MANUFACTURED_AT` 关系；基地再与 `Supplier`（EMS 代工厂）建立 `OPERATED_BY` 关系。
结构化初稿已落地于 `data/production_bases.draft.json`。

---

## 二、关系总表：产品线 → 生产基地（含代工厂与来源）

> 置信度：🔴 high（多源强证）／🟡 medium（可靠但单一或推断）／⚪ low（弱源或前瞻）。
> 来源编号对应文末「来源清单」。

### iPhone
| 生产基地 | 代工厂(EMS) | 角色 | 置信度 | 来源 |
|----------|-------------|------|--------|------|
| 郑州·河南·中国 | Foxconn（富士康） | "iPhone City"，Pro/Pro Max 主力总装 | 🔴 | S1,S2,S3 |
| 深圳·广东·中国 | Foxconn | iPhone 总装；深圳含苹果应用研究实验室 | 🔴 | S1,S4 |
| 成都·四川·中国 | Foxconn | 历史上亦参与 iPhone 总装 | 🟡 | S5 |
| 上海·中国 | Pegatron（和硕） | 部分 iPhone 机型总装 | 🔴 | S1,S2 |
| 昆山/无锡·江苏·中国 | Luxshare（立讯） | 曾总装 iPhone Plus（现 iPhone Air 取代），高毛利 tier | 🟡 | S3,S1 |
| 泰米尔纳德邦·印度 | Foxconn / Tata Pegatron | 印度 iPhone 主力之一（Foxconn 占印度出口 ~52%） | 🔴 | S6,S7,S8 |
| 卡纳塔克邦·印度 | Foxconn（Devanahalli）/ Tata（原纬创） | 保印度 ~20% 产能关键；Tata 整合纬创+和硕印度 | 🟡 | S7,S8,S3 |
| 圣保罗州·巴西 | Foxconn | 本地市场低端 iPhone（避进口税，非出口） | 🟡 | S1,S9 |

### iPad
| 生产基地 | 代工厂(EMS) | 角色 | 置信度 | 来源 |
|----------|-------------|------|--------|------|
| 郑州·河南·中国 | Foxconn | iPad 总装 | 🔴 | S1 |
| 成都·四川·中国 | Foxconn | **全球 ~60% iPad 产自成都高新区** | 🔴 | S5,S4,S1 |
| 泰米尔纳德/卡纳塔克·印度 | Foxconn / Tata / Wistron / Pegatron | 印度 iPad 总装 | 🟡 | S1,S2 |
| 北江省·越南 | Luxshare / Foxconn | iPad 组装 | 🟡 | S3,S10 |
| 广宁省·越南 | Foxconn | iPad 组装 | 🟡 | S10,S11 |
| 富寿/北江·越南 | BYD Electronics（比亚迪电子） | 部分 iPad 型号（越南产线） | 🟡 | S9,S11 |
| 中国/台湾/越南 | Compal（仁宝） | 特定型号如 iPad mini | 🟡 | S1,S2 |

### Mac
| 生产基地 | 代工厂(EMS) | 角色 | 置信度 | 来源 |
|----------|-------------|------|--------|------|
| 成都·四川·中国 | Foxconn | **全球 ~50% MacBook 产自成都**；亦 MacBook Neo | 🔴 | S5,S4,S1 |
| 中国 / 台湾 | Quanta（广达）/ Foxconn | MacBook Air/Pro 主总装（仍主要在中国） | 🔴 | S1,S12 |
| 北宁/北江/广宁·越南 | Foxconn / Luxshare | MacBook Air/Mini、iPad 模块；MacBook Pro 试产 | 🟡 | S3,S10 |
| 休斯顿·德州·美国 | Foxconn | **2026 年底起**总装 Mac mini（供美国内需） | 🔴（前瞻） | S13,S14,S15 |
| 科克·爱尔兰 | Apple 自有 | 为 EMEA 市场总装定制配置 iMac | 🔴 | S1,S12 |

### Apple Watch
| 生产基地 | 代工厂(EMS) | 角色 | 置信度 | 来源 |
|----------|-------------|------|--------|------|
| 中国（多厂） | Foxconn / Luxshare / Quanta | **约 90% Apple Watch 在中国生产** | 🔴 | S1,S12 |
| 北宁省·越南 | Foxconn / Luxshare / Goertek | 第二大组装中心 | 🟡 | S3,S10 |
| 北江省·越南 | Luxshare | Watch 组装（扩产中） | 🟡 | S3,S10 |
| 义安省·越南 | Luxshare | 规划 Apple Watch 产线（2026 中投产） | ⚪ | S10 |

### AirPods
| 生产基地 | 代工厂(EMS) | 角色 | 置信度 | 来源 |
|----------|-------------|------|--------|------|
| 中国（多厂） | Foxconn / Luxshare / BYD / Inventec / Goertek | 主要组装中心 | 🟡 | S1,S12 |
| 北江省·越南 | Luxshare | **AirPods Pro / AirPods 4 主力** | 🟡 | S3,S10 |
| 北宁省·越南 | Goertek / Foxconn / Luxshare | AirPods / 声学模块 | 🟡 | S3,S10,S16 |
| 海得拉巴·特伦甘纳·印度 | Foxconn | 自 2025-03 总装 AirPods 4 / Pro 3 | 🔴 | S1,S3 |

### Apple Vision Pro
| 生产基地 | 代工厂(EMS) | 角色 | 置信度 | 来源 |
|----------|-------------|------|--------|------|
| 中国（初期） | Luxshare（主） | 首发仅在中国组装 | 🟡 | S12,S17 |
| 越南（M5 版） | Luxshare（主）/ Goertek | 搭载 M5 的型号转越南组装 | 🟡 | S1,S12,S17 |

### HomePod
| 生产基地 | 代工厂(EMS) | 角色 | 置信度 | 来源 |
|----------|-------------|------|--------|------|
| 中国 / 越南 | Foxconn / Luxshare / BYD / Inventec / Goertek | HomePod 系列主组装 | 🟡 | S1,S12 |

---

## 三、零部件产地（区别于"总装基地"，单列避免混淆）

这些**不是最终总装基地**，而是关键零部件来源，供图谱另一层关系（`PART_ORIGIN`）使用，勿与上面的 `MANUFACTURED_AT` 混用：

| 零部件 | 主要产地/厂商 | 来源 |
|--------|---------------|------|
| A 系列 / M 系列芯片 | TSMC 台湾（亚利桑那厂在建） | S1 |
| OLED 显示 | Samsung Display / LG Display（韩国）、BOE（中国） | S1 |
| 摄像头传感器 | Sony（日本） | S1 |
| 电池 | 宁德时代 / 欣旺达 / 德赛（中国）、Samsung | S1,S4 |
| 音频芯片 | Cirrus Logic（美/英/中/日/台/新） | S1 |
| 玻璃/Ceramic Shield | Corning（美国） | S1 |

---

## 四、数据缺口与诚实声明（务必随数据发布）

1. **无官方逐厂清单**：Apple 从不披露"某厂生产某型号多少台"。本草案全部 base→product 归属为 **EMS + 所在地** 的二级推断，置信度最高仅到"省级主力"。
2. **逐厂产能不可得**：仅有国别聚合口径（印度 iPhone ~20–25%、中国整体 ~70%+、越南为 AirPods/Watch/iPad 强项）。成都"全球 60% iPad / 50% MacBook"为**单一官方/半官方媒体引述**，未见独立交叉验证，标注为 🟡。
3. **坐标缺失**：本报告**未采集经纬度**，地图集成需另行地理编码；已避免编造坐标。
4. **前瞻/过渡状态**：Mac mini 休斯顿（2026 年底启动）、Vision Pro M5 转越南、印度产能持续爬坡——标注为前瞻，状态可能变动。
5. **来源质量分层**：强源（AppleInsider、WSJ 经媒体转述、越南投资评论 VIR、中国官方媒体）用于主断言；SEO/八卦站（如 techbloat 带广告、iphonenews.cc）仅作旁证，未用于核心结论。
6. **零部件 vs 总装混淆风险**：第三节单列，确保图谱不把"零件产地"误标为"生产基地"。

---

## 五、图谱集成方式（✅ 已接入，2026-08-11）

```
ProductLine (现有 Product 节点，按产品线聚合)
   -[MANUFACTURED_AT {confidence, source}]-> ProductionBase (新节点类型)
ProductionBase -[OPERATED_BY {source}]-> Supplier (EMS: foxconn/pegatron/luxshare/quanta/byd_e/apple)
```

- `ProductionBase` 节点属性：`city / province / country / operator / products / role / confidence / sources`。
- 边 `MANUFACTURED_AT` 带 `confidence` + `source`（指向 `meta.source_registry` 的 id，面板内可点击溯源）；
  `OPERATED_BY` 带 `source`。
- **前端呈现**：新增粉色方块节点 `ProductionBase`；顶栏「展开全部生产基地」开关（默认隐藏，与供应商同层按需展开）；
  点击相关产品/零部件或运营商时其基地自动露出；侧栏展示城市/省/国/运营方/产品线/角色/可信度及可点击来源链接；
  常驻图例新增「生产基地」方块。
- 已并入 `scripts/generate.py` 的 `PRODUCTION_BASES`，重生成 `data/apple_supply_chain.json`（`nodes.bases` +
  `edges.manufactured_at` / `operated_by`）、Neo4j CSV（`bases.csv` / `product_lines.csv` / `rel_base_line.csv` /
  `rel_base_supplier.csv`）。
- 地图页 `supplier_geo.html` **暂未接入**基地层（该页坐标来自既有供应商地理数据，且含未提交本地改动）；
  基地层如需上图，需先补齐基地经纬度坐标后单独处理。

### 5.1 调研初稿 → 集成数据的归一化与核验修正

核验通过后，对 `data/production_bases.draft.json` 做了如下修正（均已在 `scripts/generate.py` 落实）：

1. **成都（iPad / Mac）升级为 high**：中国网、经济日报、成都高新区等多源官方/半官方媒体交叉确认占比，置信度由 medium 上调。
2. **深圳剔除 Spatial（Vision Pro）归属**：Vision Pro 成品总装不在深圳（初稿属弱源推断），已删除；深圳保留 iPhone / iPad（high），notes 说明其研发+组装重镇定位。
3. **成都剔除 iPhone 归属**：初稿「历史上亦参与 iPhone 总装」证据偏弱，未纳入集成数据（成都产品线定为 iPad / Mac / Wearable）。
4. **产品线归一化为图谱枚举**：`iPhone / Mac / iPad / Wearable / Spatial / Audio`（对应原 Apple Watch / Vision Pro / AirPods 等表述）。
5. **运营商归一到既有 Supplier id**：`foxconn / pegatron / luxshare / quanta / byd_e / apple`；**未新建** `tata` / `inventec` 供应商，
   仅在 `notes` 中说明（如印度 Tata 整合纬创+和硕印度产线、AirPods/HomePod 涉及 Inventec 等）。
6. **共 17 个基地节点**入图，默认隐藏，与上述交互开关 / 邻接展开联动。

---

## 六、来源清单（URL，均可追溯）

- **S1** AppleInsider（2026-04-22）Where Apple products are assembled, and where parts come from
  https://appleinsider.com/articles/26/04/22/where-apple-products-are-assembled-and-where-their-parts-come-from
- **S2** Techbloat — Where Are iPhones Manufactured? Complete Guide
  https://www.techbloat.com/where-are-iphones-manufactured-complete-guide.html
- **S3** Deluair Consultancy（2026）Apple in 2026: India at 17%, Vietnam Modules, China Anchor
  https://deluair.com/consultancy/insights/apple-china-supply-chain-2026
- **S4** 经济日报（中国）苹果公司深化在华供应链协同（成都富士康 MacBook Neo 总装）
  https://www.jingjiribao.cn/static/detail.jsp?id=644291
- **S5** 中国网 / 网易 成都高新区：全球超 60% iPad、50% MacBook 产自成都
  https://big5.china.com.cn/gate/big5/photo.china.com.cn/2024-10/29/content_117513984.shtml
- **S6** Hindustan Times（2025）Apple India plants operating at full steam… iPhone 17
  https://hindustantimes.com/business/apple-india-plants-operating-at-full-steam-to-roll-out-iphone-17-to-the-world-101757477862528.html
- **S7** Outlook Business（2025）India's iPhone exports jump over 50% in H1 2025
  https://outlookbusiness.com/explainers/indias-iphone-exports-jump-over-50-in-h1-2025-amid-trumps-tariff-tantrum-chinas-pressure
- **S8** 南方+（2025-09）iPhone17 美版印度制造，中国掌控核心供应链
  https://static.nfnews.com/content/202509/07/c11698706.html
- **S9** 百度爱企查 — 苹果在全球的工厂（概览）
  https://aiqicha.baidu.com/details/rankList?query=d5c361cfcc0aae78b0cfa191c811ecd4&type=20
- **S10** 胡志明市 ITPC — Apple suppliers reinforce footprint with Vietnam plans（越南投资评论 VIR）
  https://itpc.hochiminhcity.gov.vn/web/en/-/apple-suppliers-reinforce-footprint-with-vietnam-plans
- **S11** 越南通社 — 越南成为国际电子公司投资乐土（BYD 越南 iPad）
  https://zh.vietnamplus.vn/article-post172869.vnp
- **S12** 凤凰网科技（转 AppleInsider）一部 iPhone 的全球旅行——苹果供应链大起底
  https://tech.ifeng.com/c/8sYhZT05ZlM
- **S13** 星岛头条（2026-02-24）Mac Mini 部分产线移回美国，鸿海休斯顿厂制造（引 WSJ）
  https://www.stheadline.com/realtime-world/3547062/...
- **S14** Tom's Hardware FR — Apple rapatrie une partie de sa production…
  https://www.tomshardware.fr?p=904410/
- **S15** Cool3c（2026）苹果确认部分 Mac mini 产线转移德州
  https://www.cool3c.com/article/246601
- **S16** ITPC — Goertek to invest another $280M in Vietnamese subsidiary（Bac Ninh，VR/耳机）
  http://itpc.hochiminhcity.gov.vn/web/en/-/goertek-to-invest-another-280-million-in-vietnamese-consumer-electronics-subsidiary
- **S17** 百度爱企查 — 苹果手机代工厂越南（Vision Pro 越南组装）
  https://aiqicha.baidu.com/details/ugknowledge?id=a58b5d89c28bfa30b1142f9f8efed80d

---

*本调研为公开资料二手整合，仅供研究/教学参考，**不构成任何投资或采购依据**。所有关系均带来源与置信度，集成进图谱前建议再做一轮人工核验。*
