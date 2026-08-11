# 时效数据接口（Data Feeds）设计

> 阶段 1 落地说明。目标：**把"市场/分析类时效数据"与"结构性数据"分离，并在前后端之间建立可切换的清晰接口**，便于未来在不改 UI 的情况下更换数据来源（如接真实 API）。
> 项目部署在 GitHub Pages（纯静态、无后端），更新方案见末尾。

## 一、双域分离

| 域 | 内容 | 变化频率 | 事实来源 |
|---|---|---|---|
| **结构性域** | 产品/零部件/供应商/基地拓扑与属性 | 慢（季度级） | `data/apple_supply_chain.json`（内联进页面） |
| **时效域** | 风险分、估值/财务、舆情 | 快（周/月级） | `data/feeds/*.json`（运行时 `fetch`） |

前端只通过 `DataLayer` 读取时效域，**绝不直接 `fetch` 文件路径**；生产者（`scripts/`）与消费者（`src/`）通过下方契约解耦。

## 二、统一信封契约

每个 feed 文件形如：

```json
{
  "meta": {
    "dataset": "risk",
    "version": 2,
    "schema_ref": "data/schemas/risk.json",
    "generated": "2026-08-09",
    "valid_until": "2026-09-08",
    "sources": ["apple_supplier_list", "..."],
    "build": "v1.3.0-5-gabcdef0"
  },
  "data": { "...": "具体指标" }
}
```

- `generated` / `valid_until`：驱动 UI 新鲜度判定（`valid_until` 之前为 `fresh`，之后为 `stale`）。
- `schema_ref`：指向 `data/schemas/<dataset>.json`（JSON Schema），作为 CI 校验与接口文档。
- `sources`：来源溯源 id（引用 `data/apple_supply_chain.json` 的 `meta.source_registry`），满足项目一贯的"来源可追溯"。

## 三、三个 feed

| 文件 | 来源（producer 输入） | `data` 关键字段 |
|---|---|---|
| `data/feeds/risk.json` | `tools/output/supply_chain_risk.json` | `product_lines / products / components`（含 `vuln`、`sp_rate`、`single_point`） |
| `data/feeds/valuation.json` | `tools/output/supplier_analysis.json` | `suppliers[]`（含 `ticker`、`market_cap_usd_b`、`pe`、`pb`、`ev_ebitda`、`as_of`） |
| `data/feeds/sentiment.json` | `tools/output/supplier_sentiment.md` | `snapshot_date`、`coverage`、`markdown`（原文） |

> 生成器只做"格式归一 + 信封包装"，**不篡改任何分析结论**。

## 四、生产者：`scripts/build_feeds.py`

```bash
python3 scripts/build_feeds.py                # 默认 ttl=30 天，输出 data/feeds/
python3 scripts/build_feeds.py --ttl-days 7   # 周级刷新（调整 valid_until）
```

CI 的 `pages.yml` 已把 `data/feeds/` 拷入 `_site`，使前端可在运行时拉取。

## 五、消费者：`src/lib/data_layer.js`

暴露全局 `window.DataLayer`：

```js
await DataLayer.getRisk();        // → feed.data
await DataLayer.getValuation();
await DataLayer.getSentiment();
DataLayer.freshness("risk");      // 'fresh' | 'stale' | 'unknown'
DataLayer.renderFreshness(el, "risk"); // 渲染新鲜度徽标
```

**Provider 抽象（切换数据源的关键）：**

- `FileFeedProvider`（当前）：拉取仓库内 `data/feeds/<name>.json`。
- `ApiFeedProvider`（未来桩，接口一致）：`DataLayer.setProvider(new ApiFeedProvider("https://api…/{name}.json"))` 即可换源，**UI 零改动**。

**降级：** `fetch` 失败时回退到 `localStorage` 上次成功结果，并标"可能过期"；离线也不致白屏。

## 六、GitHub Pages 更新方案（可行）

- **当前（阶段 1）**：feed 文件随仓库提交，`pages.yml` 发布时拷贝到 `_site`，前端运行时拉取。
- **下一步（阶段 2，计划内）**：新增 `refresh-feeds.yml`，`on: schedule`（cron，如每周）+ `workflow_dispatch`（手动），在 CI 内重跑分析与 `build_feeds.py` → 用 `GITHUB_TOKEN` 回写 `main` → 触发现有 Pages 部署。纯静态、零服务器。
- **可选（阶段 3）**：实现 `ApiFeedProvider`，配置 Secrets 接外部数据源。

## 七、前端新鲜度显示

首页（`index.html`）顶栏右侧"更新于 X · 下次 Y"徽标，由 `DataLayer` 拉取 `risk` feed 渲染，过时变红并提示；语言切换时自动重绘。报告页 / 估值看板可按需在同样方式接入（同 `DataLayer` 接口）。

## 八、版本号（自动派生，零手动维护）

版本号采用**两大流派组合**，全部自动、无需手改：

### 流派 B — 构建戳（git 图元数据，每次部署唯一）
- 来源：`scripts/version.py`，封装 `git describe --tags --dirty --always --match "v[0-9]*"`。
- 格式：`v1.3.0`（恰在 tag 上）/ `v1.3.0-5-gabcdef0`（距 tag 5 个 commit）/ `-dirty`（工作区脏）。
- 落点：
  - feeds 信封 `meta.build`（由 `build_feeds.py --build` 注入，CI 通过 `GITHUB_ENV` 传 `BUILD_VERSION`）。
  - `_site/build.json` 部署清单（含 `build_version` + `git_sha` + `build_at`），前端可 `fetch('/build.json')` 显示「本站构建于 X / 提交 abc」。
  - 资产缓存戳已由 `build_viewer.asset_url()` 走**内容哈希**自动处理（内容变则 URL 变），与构建戳互补。
- 回退链：`git describe` 失败 → `BUILD_VERSION` 环境变量 → `0.0.0-unknown`。

### 流派 A — 语义版本（Conventional Commits，对外宣称为「数据集 vX.Y.Z」）
- 来源：`.github/workflows/release-please.yml` + `release-please-config.json` + `.release-please-manifest.json`（初始 `1.3.0`）。
- 机制：每次 push 到 `main`，扫描自上次 tag 起的 commit（`feat:`→minor、`fix:`→patch、`feat!`/`BREAKING`→major），开/更新一个 **Release PR**；合并后自动打 `git tag (vX.Y.Z)` 并生成 `CHANGELOG.md`。
- 协同：合并 Release PR 产生的 push 会触发 Pages 部署，届时 `git describe` 即能拿到新 tag，使 `meta.build` 与 `build.json` 反映最新语义版本（偶尔因 workflow 并发落后一个版本，下次部署修正——非功能性）。

> 惯例：本仓库 commit 采用 Conventional Commits（`feat:`/`fix:`/`docs:`/`chore:` 等），
> 这是 release-please 正确推导版本的前提；新增功能类提交请沿用该前缀。
