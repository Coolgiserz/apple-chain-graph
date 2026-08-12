# 引用数据清单（Data Sources & Citations）

> 本清单由 `data/apple_supply_chain.json` 的 `meta.source_registry`（27 条）抽取整理，
> 并**逐条核实了 URL 的可访问性与内容**（自动 HTTP 探测，探测时间 2026-08-12）。
> 每个来源标注了验证状态，防止把不可达/失效链接当作有效引用。

## 重要前提（引用前必读）

- 本项目全部数据为 **AI 联网检索公开资料的二手整合**，属探索性参考数据集，**非一手事实、非基准**。
- 引用时**必须同时标注版本（commit）+ 数据快照时间**，并声明上述局限性（详见 `README.md` 的「数据来源与口径」与「分析方法局限性」）。
- 生产基地草稿（`data/production_bases.draft.json`，**DRAFT 未接入构建**）的 base→product 归属多为「EMS+所在地」**推断**，Apple 不公开逐厂产量。

## 验证状态图例

| 标记 | 含义 |
| --- | --- |
| ✅ 已验证 | HTTP 200，且返回页面主题与标注一致、确有内容 |
| 🔒 机器人拦截 | 返回 403（Cloudflare / SEC「Undeclared Automated Tool」等），**站点与链接真实，浏览器可正常打开**；沙箱自动请求被拦 |
| ⏱ 沙箱不可达 | 请求超时（000）；域名为真实站点，但当前网络环境无法连通，**需人工在浏览器核实** |
| ❌ 链接失效 | HTTP 404（含软 404），路径已失效，**需替换** |

## 数据集级 provenance

| 文件 | 内容 | 来源口径 |
| --- | --- | --- |
| `data/apple_supply_chain.json` | 产品/零部件/供应商/基地拓扑（28 产品 / 27 零部件 / 60 供应商 / 17 基地） | `meta.source`：公开供应链报告 2024–2026 + 苹果 2024 供应商名单（187 家核心供应商，≈98% 直接支出）；`sources_accessed: 2026-08-05` |
| `data/supply_chain_risk.json` | 单点依赖 / 脆弱性评分 | 模型 `component_supplier_count_v1`；权重 `mean 0.5 / weakest 0.3 / single_point_rate 0.2`；阈值 `high 0.6 / medium 0.3`；`as_of: 见图谱 meta.source` |
| `data/production_bases.draft.json` | 17 个总装基地（**DRAFT，未接入 build**） | 方法：联网公开资料二手整合（AppleInsider、WSJ 经媒体转述、越南投资评论 VIR、中国官方媒体、行业研究） |

## 来源清单（27 条）

### 🏛 官方披露（2）

| id | 发布方 | 标题 | URL | 状态 |
| --- | --- | --- | --- | --- |
| `apple_supplier_list` | Apple Inc. | Apple Supplier List（官方供应链名单） | https://www.apple.com/supplier-responsibility/ | ✅ 已验证（重定向至 https://www.apple.com/supply-chain/ ，内容有效） |
| `apple_10k` | U.S. SEC（Apple CIK 0000320193） | Apple Inc. Form 10-K | https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0000320193&type=10-K | 🔒 机器人拦截（SEC 拦截自动工具；EDGAR 查询在浏览器有效） |

### 🔬 拆解 / BOM（2）

| id | 发布方 | 标题 | URL | 状态 |
| --- | --- | --- | --- | --- |
| `techinsights` | TechInsights | 硬件拆解与 BOM 分析 | https://www.techinsights.com/teardown | ❌ 链接失效（404，`/teardown` 路径已失效，需替换） |
| `ifixit` | iFixit | 产品拆解数据库 | https://www.ifixit.com/Teardown | ✅ 已验证（200；JS 渲染外壳，浏览器可见内容） |

### 📊 行业分析 / 研报（9）

| id | 发布方 | 标题 | URL | 状态 |
| --- | --- | --- | --- | --- |
| `counterpoint` | Counterpoint Research | 零部件供应与份额研究 | https://www.counterpointresearch.com/ | ✅ 已验证 |
| `trendforce` | TrendForce | 存储 / 半导体供需与份额报告 | https://www.trendforce.com/press-center/ | ❌ 链接失效（404 软 404，`/press-center/` 路径已失效，需替换） |
| `dscc` | DSCC / Omdia | 显示面板供给分析 | https://www.displaysupplychain.com/ | ⏱ 沙箱不可达（域名为真实站点，需浏览器核实） |
| `omdia` | Omdia (Informa) | 显示与半导体市场追踪 | https://omdia.tech.informa.com/ | 🔒 机器人拦截（Cloudflare；浏览器可开） |
| `nikkei` | Nikkei Asia | 苹果供应链报道 | https://asia.nikkei.com/ | ⏱ 沙箱不可达（域名为真实站点，需浏览器核实） |
| `base_appleinsider` | AppleInsider | Where Apple products are assembled | https://appleinsider.com/articles/26/04/22/where-apple-products-are-assembled-and-where-their-parts-come-from | ✅ 已验证 |
| `base_techbloat` | TechBloat | Where are iPhones manufactured | https://www.techbloat.com/where-are-iphones-manufactured-complete-guide.html | 🔒 机器人拦截（Cloudflare；浏览器可开；注意该站为 SEO/商业站，仅作交叉印证） |
| `base_deluair` | Delu Air (consultancy) | Apple China supply chain 2026 | https://deluair.com/consultancy/insights/apple-china-supply-chain-2026 | ✅ 已验证（确为相关分析文章） |
| `base_outlookbiz` | Outlook Business | India iPhone exports jump 50%+ H1 2025 | https://outlookbusiness.com/explainers/indias-iphone-exports-jump-over-50-in-h1-2025-amid-trumps-tariff-tantrum-chinas-pressure | ✅ 已验证 |

### 🏢 政府 / 投资促进（2）

| id | 发布方 | 标题 | URL | 状态 |
| --- | --- | --- | --- | --- |
| `base_itpc` | ITPC Ho Chi Minh City | Apple suppliers reinforce Vietnam footprint | https://itpc.hochiminhcity.gov.vn/web/en/-/apple-suppliers-reinforce-footprint-with-vietnam-plans | ✅ 已验证 |
| `base_itpc_goertek` | ITPC Ho Chi Minh City | GoerTek invests $280M in Vietnam | https://itpc.hochiminhcity.gov.vn/web/en/-/goertek-to-invest-another-280-million-in-vietnamese-consumer-electronics-subsidiary | ✅ 已验证 |

### 🏛 官方媒体 / 国资（2）

| id | 发布方 | 标题 | URL | 状态 |
| --- | --- | --- | --- | --- |
| `base_china` | 中国网 (China.org.cn) | 成都高新区制造产能报道 | https://big5.china.com.cn/gate/big5/photo.china.com.cn/2024-10/29/content_117513984.shtml | ⏱ 沙箱不可达（域名为真实站点，需浏览器核实） |
| `base_jingjiribao` | 经济日报 | 苹果供应链（中国组装 / 研发）报道 | https://www.jingjiribao.cn/static/detail.jsp?id=644291 | ✅ 已验证 |

### 📰 媒体（6）

| id | 发布方 | 标题 | URL | 状态 |
| --- | --- | --- | --- | --- |
| `base_ifeng` | 凤凰网科技 | 苹果供应链制造 / 组装报道 | https://tech.ifeng.com/c/8sYhZT05ZlM | ✅ 已验证 |
| `base_hindustantimes` | Hindustan Times | Apple India plants ramp iPhone 17 | https://hindustantimes.com/business/apple-india-plants-operating-at-full-steam-to-roll-out-iphone-17-to-the-world-101757477862528.html | 🔒 机器人拦截（Access Denied；浏览器可开） |
| `base_nfnews` | 南方+ (Southern+) | 印度 iPhone 产能 / 供应链报道 | https://static.nfnews.com/content/202509/07/c11698706.html | ✅ 已验证 |
| `base_stheadline` | 星岛日报 (Sing Tao) | Mac mini 产线移回美国（Foxconn 德州） | https://www.stheadline.com/realtime-world/3547062/%E8%98%8B%E6%9E%9CMac-Mini-%E9%83%A8%E5%88%86%E7%94%9F%E7%94%A2%E7%B7%9A%E5%B0%87%E7%A7%BB%E5%9B%9E%E7%BE%8E%E5%9C%8B-%E7%94%B1%E9%B4%BB%E6%B5%B7%E4%BC%81%E6%96%AF%E6%95%A6%E5%BB%A0%E8%A3%BD%E9%80%A0 | ✅ 已验证 |
| `base_tomshardware` | Tom's Hardware FR | Apple Mac mini production to USA | https://www.tomshardware.fr?p=904410/ | ✅ 已验证（注册 URL `?p=904410/` 已重定向至正确文章 `/apple-rapatrie-une-partie-de-sa-production...`） |
| `base_cool3c` | Cool3C | 苹果 Mac mini 美国产线报道 | https://www.cool3c.com/article/246601 | ✅ 已验证 |

### 📚 百科（1）

| id | 发布方 | 标题 | URL | 状态 |
| --- | --- | --- | --- | --- |
| `base_sogou` | 搜狗百科 | 鸿富成（成都富士康）词条 | https://baike.sogou.com/v10004421896.htm | ✅ 已验证（200；JS 渲染外壳，浏览器可见内容） |

### 💼 商业 / 工商注册（3）

| id | 发布方 | 标题 | URL | 状态 |
| --- | --- | --- | --- | --- |
| `base_sav` | Sourcing Agent Vietnam (commercial) | OEM manufacturers in Vietnam | https://sourcing-agent-vietnam.com/oem-manufacturers-vietnam/ | ✅ 已验证（商业站，仅作交叉印证） |
| `base_aiqicha` | 爱企查 (commercial registry) | 富士康 / 立讯越南厂区工商信息 | https://aiqicha.baidu.com/details/ugknowledge?id=a58b5d89c28bfa30b1142f9f8efed80d | ✅ 已验证 |
| `base_aiqicha_rank` | 爱企查 (commercial registry) | 富士康巴西厂区工商信息 | https://aiqicha.baidu.com/details/rankList?query=d5c361cfcc0aae78b0cfa191c811ecd4&type=20 | ✅ 已验证 |

## 验证汇总（2026-08-12 自动探测）

| 状态 | 数量 | 条目 |
| --- | --- | --- |
| ✅ 已验证可访问 | 18 | apple_supplier_list, ifixit, counterpoint, base_appleinsider, base_deluair, base_jingjiribao, base_sogou, base_ifeng, base_outlookbiz, base_nfnews, base_sav, base_itpc, base_itpc_goertek, base_aiqicha, base_stheadline, base_tomshardware, base_cool3c, base_aiqicha_rank |
| 🔒 机器人拦截（浏览器可开） | 4 | apple_10k, omdia, base_techbloat, base_hindustantimes |
| ⏱ 沙箱不可达（需浏览器核实） | 3 | dscc, nikkei, base_china |
| ❌ 链接失效（需替换） | 2 | techinsights, trendforce |

> 说明：🔒 / ⏱ 两类**并非失效**——域名真实、路径大概率有效，仅因沙箱自动化请求被反爬拦截或网络不可达而无法在此确认。建议引用前在浏览器人工点开核验。

## 需跟进的修复

1. **`techinsights` / `trendforce` 两条为 404 死链**：建议替换为各站当前有效的列表页 / 最新文章页，并重新跑一次 URL 探测确认 200 后再写入 `meta.source_registry`（同时影响图谱内溯源链接 `panels.js`）。
2. **`base_tomshardware`** 注册 URL 带多余查询串 `?p=904410/`，虽能重定向到正确文章，建议清理为规范地址 `https://www.tomshardware.fr/apple-rapatrie-une-partie-de-sa-production-sur-le-sol-americain/`。

## 建议引用格式

> *Apple Chain Graph（apple-chain-graph），数据集 v1.6.x，commit `<sha>`，数据快照 2026-08-05，MIT License。*
> *数据为 AI 联网检索公开资料的二手整合，非一手事实、非基准；生产基地归属为推断。引用须标注版本与快照时间。*
