# 项目里程碑（Milestones Wiki）

> 本文件梳理 **Apple Supply Chain Graph（苹果供应链上下游图谱）** 的关键里程碑，
> 按"能力演进"而非提交顺序组织，便于新成员快速建立项目全景认知。
>
> 项目集中开发于 **2026-08-09 ~ 2026-08-11**（约 3 天端到端产出），
> 全程由 AI 编程（WorkBuddy Hy3）完成。各阶段的代表提交以 `commit` 锚点标注，
> 可用 `git show <commit>` 查看细节。
>
> 项目定位：**演示 / 探索性作品**，侧重可复现的工程实现与交互体验，
> 分析结论为 AI 联网整合的二手数据，**非正式投资 / 采购依据**（见 `README.md` 免责声明）。

---

## 一、总览时间线

| 阶段 | 主题 | 时间窗 | 代表提交 |
|------|------|--------|----------|
| P0 | 立项与数据底座 | 08-09 | `fb522b5` |
| P1 | 可视化与多页融合 | 08-09 | `8fd4b82` `94e8235` `c1e1523` |
| P2 | 供应商研究层 | 08-09 | `61eb6c8` `2f44eae` |
| P3 | 国际化 i18n | 08-09 | `6aea85f` `229c781` |
| P4 | SEO 与定位 | 08-09 | `7c9adab` |
| P5 | 工程化与协作 | 08-10 | `296087c` `90e5ba0` |
| P6 | PM / 交互评审与修复 | 08-10 | `b380635` `bb88369` `44bb286` `a0e0a5e` `4c87313` |
| P7 | 移动端适配与导航重构 | 08-10 ~ 08-11 | `1a4615b` `b8b26f1` `ab2c751` |

> 说明：日期为提交日期（`git show -s --format='%ad' --date=short`），
> 单日内的多个提交按主题归并到对应阶段，并非严格的先后次序。

---

## 二、P0 — 立项与数据底座（Foundation）

**目标**：用一份单一数据源，把"某款具体型号 → 用了哪些零部件 → 由谁供应 / 代工"串成可查询、可导入图数据库、可复现的图。

核心交付：
- **三层有向图数据模型**：`Product → Component → Supplier`，约 115 节点 / 510 关系（覆盖 iPhone / Mac / iPad / Watch / Vision Pro / AirPods·HomePod 六大产品线，精确到具体型号如 `iPhone 17 Pro`）。
- **Neo4j 官方批量导入格式**：6 个 CSV（`:ID`/`:LABEL`/`:START_ID`/`:END_ID`/`:TYPE` 表头）+ 离线（`neo4j-admin`）/ 在线（`LOAD CSV`）两种导入方式（见 `docs/neo4j-import.md`，提交 `fb522b5` 前的基座）。
- **数据与代码分离、可复现**：`scripts/generate.py` 从 `data/apple_supply_chain.json` 单一来源生成全部图数据；改 CSV/JSON 即重算。

意义：奠定"单一事实来源 + 零三方依赖纯标准库"的产出范式，后续所有页面都由脚本重生成。

---

## 三、P1 — 可视化与多页融合（Visualization & Navigation）

**目标**：让图谱"活"起来、可读、可跳转，避免各页面成为孤岛。

关键节点：
- **首页力导向图谱**（`index.html`，Canvas + 自写力导向物理引擎 `templates/graph_engine.js`）：滚轮缩放、拖拽平移、拖动节点、筛选（产品 / 零部件 / 供应商 / 产品线）、搜索定位（`8fd4b82` 前后）。
- **企业列表表格视图**（`dist/supplier_table.html`）：全部 60 家供应商，支持按地区 / 国家 / 类别 / 层级筛选、关键字搜索、点击列标题升/降序排序（`94e8235`）。
- **统一顶部导航 `topnav.py`**：一处维护、全局生效，首页 / 表格 / 报告 / 地图 / 看板 5 大板块互相跳转，形成"融合"而非聚合页（`8fd4b82`）。
- **跨页深链**：报告表格实体 → `index.html?focus=S:tsmc` 定位图谱；供应商 → `supplier_geo.html?supplier=tsmc` 定位地图；表格每行"图谱 / 地图"一键直达。
- **右侧信息面板联动**：点击"关联"邻居可聚焦并同步图谱与详情（`c1e1523`）。
- **地图页双后端**：默认 Leaflet + OSM（免 Key、纯静态托管直接可用），可选腾讯地图 GL 增强（`fb522b5`）。

意义：从"能画图"到"可用、可穿行"，多页互相链接构成完整站点。

---

## 四、P2 — 供应商研究层（Research Layer）

**目标**：在"结构图谱"之外，补充 60 家供应商中 **15 家重点企业**的基本面 / 估值 / 舆情 / 脆弱性研究。

交付：
- **基本面与同业相对估值**（`tools/supplier_research/valuation.py`）：当前倍数（P/E·P/B·EV/EBITDA）÷ 同业中位，判断高估 / 低估 / 合理；数据层 `tools/data/supplier_fundamentals.csv` 可人工核改（`61eb6c8`）。
- **舆情分析**（`run_sentiment.py`）：新闻情绪 + 卖方共识 + 催化剂 / 风险 / 来源链接，识别"情绪—估值"背离。
- **供应链脆弱性分析**（`run_risk.py` + `risk.py`）：从"零部件供应商数"出发，自下而上聚合产品、上卷产品线，识别单点依赖（如 `audio_codec → Cirrus Logic`）（`2f44eae` `61eb6c8`）。
- **可视化看板**（`tools/visualizations/supplier_dashboard.html`，Chart.js）：同业估值分布、情绪—估值背离矩阵、舆情分布、盈利质量、行业市值分布等 6 张图。
- **风险视图**集成进图谱：勾选"风险视图"弹出风险因子说明侧栏（`8bb3d80` `cd583d9`）。

意义：把作品从"结构可视化"升级为"带分析结论的研究型作品"。

---

## 五、P3 — 国际化（i18n）

**目标**：界面与内容支持中 / 英 / 法 / 日四语，面向国际读者。

交付：
- **接入 i18next 框架**（`6aea85f`），四语言切换器置于统一导航。
- **内联语言包根除 404**：`dist/locales.js` 由 `build_viewer.py` 从 `locales/{zh,en,fr,ja}.json` 内联生成，`i18n.js` 直接读取，规避 `locales/` 目录遗漏与 `file://` CORS 限制（`229c781`）。
- **全量接入**：图谱面板、报告（含数据枚举值）、看板标题 / 章节 / 卡片 / 图表轴 / 表格 均经自动翻译（提交 `0839e5d` `dc5785a` `aa2a16f` 等）。
- 双语 README（`README_en.md`）。

意义：消除语言壁垒，配合 SEO 面向全球读者。

---

## 六、P4 — SEO 与定位（SEO & Positioning）

**目标**：让静态站点可被搜索引擎索引，同时严谨界定数据性质。

交付：
- **P0 首页 SEO 基础设施**（`7c9adab`）：数据驱动的可索引文本 + 结构化数据（JSON-LD）+ `sitemap.xml` / `robots.txt`。
- **谨慎措辞定位**：图谱定位为"可复现研究 / 实验数据集（参考性，非成熟基准）"，README 与报告均明确局限性（`7066ed3` `d95af77`）。
- 安全修复：两处数据驱动 HTML 注入（`1cdddd5`）。

意义：在可发现性与学术诚信之间取得平衡——既能被检索，又明确"非权威基准"。

---

## 七、P5 — 工程化与协作（Engineering & CI）

**目标**：让项目适配多人协作、可构建、可自动部署。

交付：
- **前端 ESM 化 + esbuild 打包**（`296087c`，`refactor/team-ready`）：画布引擎抽为 `src/engine/` 模块，打包为 `dist/graph_engine.js`（IIFE）+ `dist/i18n.js`，可被 Node 单测。
- **CI / 部署**：PR 经流水线门禁、仅 `main` 推送才部署（`90e5ba0`）；GitHub Pages 自动发布（发布 `index.html`/`dist/`/`tools/visualizations/`/`docs/` 等静态产物，不发布源码与 `data/`）。
- **资源版本戳机制**：`?v=` 资源戳 + 内容哈希，强制浏览器放弃旧缓存（看板 / 报告重建时递增）。
- **Docker 一键托管**（nginx 容器，`make up`）与 HTTPS 生产覆盖（`make up-prod`）。
- 测试体系：`make test` = 引擎单测（`tests/engine.test.mjs`，DOM-stub 加载 `dist/graph_engine.js`）+ Python 单测 + `tools/validate_dataset.py` 数据集校验。

意义：从"能跑"到"可协作、可交付、防回归"。

---

## 八、P6 — PM / 交互评审与修复（UX Review & Fixes）

**目标**：以项目经理 / 交互设计师视角做严苛评审并落地修复。

交付：
- **PM 视角报告内容评审**（`1d533ac` 评审文档 + 落地 `b380635`）：围绕"是否合适 / 合规 / 有明显错误 / 有必要 / 偏题"五维度测试报告。
- **报告 P0/P1 内容修复 + 去除偏题 Neo4j 入口**（`4c87313`）：加生成日期、修正"总部位于东亚"占比表述、覆盖年限口径、补充单点依赖风险提示并附来源；移除与主题无关的 Neo4j 文案。
- **企业表格 / 图谱 / 右侧面板三方联动**（analyze 分支 → `bb88369`，PR #3~#4）：
  - 引入 `sc:select`（选中广播）、`sc:view`（视图/筛选变化广播）CustomEvent，打通图谱→表格反向联动；
  - 修 P0 单向联动、残留高亮、`applyFocus` 改调 `selectNode` 等。
- **严苛交互审查 + P2 不可见节点聚焦**（`44bb286`）：`ensureVisible` 处理搜索 / 产品线过滤后节点不可见、供应商兜底 `showAll`；修缩放边界夹紧、表格自动弹开侵扰等 5 项问题；测试扩至 24 项。
- **非美供应商 FX 市值校正**（`a0e0a5e`）：用权威直接 USD 市值校正 10 家非美供应商（如 skhynix 979.0、samsung_elec 1196.0），并修 `report.py` 对缺失 ROE 崩溃（None 安全格式化）。

意义：把"能用"打磨为"交互合理、内容可信"。

---

## 九、P7 — 移动端适配与导航重构（Mobile & Nav）

**目标**：解决移动端体验差（导航栏遮挡 / 溢出）的问题。

交付与迭代（同一个未合并分支 `fix/mobile-responsive`，3 次提交）：
1. **移动端适配**（`1a4615b`）：主图谱页控制栏折叠（☰ 汉堡，点控件自动收起，避免 11 个控件换行遮挡顶部）；`env(safe-area-inset-*)` 安全区适配刘海 / Home 指示条；触控目标放大到 ≥44px；详情面板改底部抽屉；`#cv` 加 `touch-action:none` 防止 iOS Safari 把画布手势当页面滚动；表格页补窄屏媒体查询。
2. **导航栏改用原生 `<details>` 汉堡**（`b8b26f1`）：弃用第三方 `responsive-nav.js`（其折叠态依赖 JS 注入的 `.js` 类，脚本失败就横向溢出），改用纯 CSS `<details>`，零 JS 依赖。
3. **修复 PC 端导航消失**（`ab2c751`）：`<details>` 关闭态由浏览器引擎级隐藏内容，导致桌面端"菜单常驻"媒体查询失效、整条导航消失；改用**纯 CSS 复选框汉堡**（checkbox hack）：菜单 `<ul>` 始终是普通子元素，桌面端 `≥860px` 强制 `display:flex` 常驻，移动端由 `:checked` 下拉展开。

> 关键教训（已记入项目记忆）：做"桌面常驻 / 移动折叠"导航**不要用 `<details>`**（关闭态引擎级隐藏内容）；用 checkbox/label hack 或单纯媒体查询控制 `display` 更稳。跨页面共享导航 / 顶栏**不要依赖"靠 JS 注入 class 才折叠"的第三方库**。

---

## 十、项目边界与约定（Conventions）

以下为协作中沉淀的硬约束，新人务必遵守：

- **`tools/visualizations/supplier_geo.html` 含未提交本地改动，提交 / 重建时必须排除**：凡经 `build_all.py` / `build_viewer.py` 等脚本重建后提交，只 `git add` 模板 + 受影响产物，**不要**把它纳入。涉及重建前用 `git stash` 保护，重建后 `git stash pop` 恢复。
- **无 `gh` CLI**：创建 PR 用网页链接（如 `https://github.com/Coolgiserz/apple-chain-graph/compare/main...<branch>?expand=1`），无法命令行建 PR。
- **i18n 四语言同步**：`locales/{zh,en,fr,ja}.json` 已有键不回退，增删键须四语言同改。
- **`index.html` 噪声 diff**：`build_viewer.py` 会重嵌 `SUPPLY_DATA` 与递增 `?v=` 戳，提交前若确认数据未变可用 `git checkout -- index.html` 还原无关改动（资源戳校正属正常自洽）。
- **`make test` 是回归底线**：引擎单测（24 项）+ Python 单测 + 数据集校验，改动后必跑。

---

## 十一、未决 / 待办（Roadmap Backlog）

来自 `README.md` 路线图与评审中识别但尚未完成项：

- [ ] 数据时效自动化更新（行情快照刷新脚本，当前为单时点快照）。
- [ ] 更多产品线 / 未发布机型覆盖补全。
- [ ] 图谱与地图**双向联动**（点击供应商同时在图谱高亮上下游链路、在地图聚焦基地）——P6 已打通图谱↔表格，地图联动仍待做。
- [ ] 估值从"截面中位倍数"升级为多年 PE/PB 历史分位 + DCF 交叉验证。
- [ ] 舆情改为量化 NLP 情感分析（时间序列、拐点识别）。
- [ ] 关系边补「份额 / 营收权重」，使"主要供应商"从定性走向定量。
- [ ] `docs/graph-risk-integration.md` 仍为"设计阶段"——脆弱性数据 → 图谱可视化集成尚未实现。

---

*最后更新：2026-08-11（P7 导航修复）｜ 维护者：项目贡献者 ｜ 许可：MIT*
