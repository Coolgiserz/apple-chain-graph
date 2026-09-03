# Changelog

## [1.11.5](https://github.com/Coolgiserz/apple-chain-graph/compare/v1.11.4...v1.11.5) (2026-09-03)


### Bug Fixes

* **report:** 报告页浅色令牌收敛到 body，修复表格文字看不清 ([2d1c832](https://github.com/Coolgiserz/apple-chain-graph/commit/2d1c832eae558d5ea911564701fc3086fb5d3acb))

## [1.11.4](https://github.com/Coolgiserz/apple-chain-graph/compare/v1.11.3...v1.11.4) (2026-09-02)


### Bug Fixes

* **dashboard:** as_of 从 CSV 透传到看板与报告，替换硬编码 2026-08-10 ([46c5cd0](https://github.com/Coolgiserz/apple-chain-graph/commit/46c5cd0a08896a43e8f024d7868423bc8c97b9ae))
* **dashboard:** as_of 从 CSV 透传到看板与报告，替换硬编码 2026-08-10 ([ccc7a4a](https://github.com/Coolgiserz/apple-chain-graph/commit/ccc7a4a2b54dd720127f0a80fd428ada3bfc213d))

## [1.11.3](https://github.com/Coolgiserz/apple-chain-graph/compare/v1.11.2...v1.11.3) (2026-09-02)


### Bug Fixes

* **dash:** 估值看板数据接回构建管道，不再手写快照 ([5cd9e04](https://github.com/Coolgiserz/apple-chain-graph/commit/5cd9e04bd84c7447c5274add5389e7388e4c1f08))
* **dash:** 看板估值数据接回构建管道，不再手写快照 ([418970d](https://github.com/Coolgiserz/apple-chain-graph/commit/418970de90d4dd429158a6539eb53b20431b788e))

## [1.11.2](https://github.com/Coolgiserz/apple-chain-graph/compare/v1.11.1...v1.11.2) (2026-09-01)


### Bug Fixes

* **ui:** 移动端搜索框不再被收起逻辑抹掉，搜索功能恢复可用 ([1ccad79](https://github.com/Coolgiserz/apple-chain-graph/commit/1ccad79a017006b28e62789ea34a368888cf687a))
* **ui:** 移动端搜索框不再被收起逻辑抹掉，搜索功能恢复可用 ([3b70d32](https://github.com/Coolgiserz/apple-chain-graph/commit/3b70d32c2f80b84ffc8bb2458c703fe19ad3d68a))

## [1.11.1](https://github.com/Coolgiserz/apple-chain-graph/compare/v1.11.0...v1.11.1) (2026-09-01)


### Bug Fixes

* **ci:** 登记 getComputedStyle 到 ESLint 白名单，修复色值令牌化的 no-undef 红灯 ([3a657f8](https://github.com/Coolgiserz/apple-chain-graph/commit/3a657f856e817f7807a6a981e3b52d1ed9a21260))

## [1.11.0](https://github.com/Coolgiserz/apple-chain-graph/compare/v1.10.0...v1.11.0) (2026-09-01)


### Features

* **ci:** 自动版本号 CD 流程（git describe 构建戳 + release-please 语义版本） ([993ff40](https://github.com/Coolgiserz/apple-chain-graph/commit/993ff40ec73d25350b061aafaee730e31020492b))
* **ci:** 自动版本号 CD 流程（git describe 构建戳 + release-please 语义版本） ([cea6213](https://github.com/Coolgiserz/apple-chain-graph/commit/cea621324b156874c3cc80f78a89cfda02cd3989))
* **deploy:** 可选 HTTPS 生产覆盖，默认仍走 HTTP ([d42283e](https://github.com/Coolgiserz/apple-chain-graph/commit/d42283eb09091dcc85bd99d7660156017260c1f7))
* **graph:** 右侧信息框「关联」邻居可点击，点击聚焦并同步图谱与详情 ([c1e1523](https://github.com/Coolgiserz/apple-chain-graph/commit/c1e1523ba865a523a9e24b68de831a1f5e52ed25))
* **graph:** 渐进式展开 + 沿边流动粒子，让图谱「活」起来 ([c0b19a0](https://github.com/Coolgiserz/apple-chain-graph/commit/c0b19a01bb8f18a1ba1ee5d9af89204c91fdc78e))
* **graph:** 风险视图弹出「风险因子说明」侧边栏（自变量→因变量分解表） ([8bb3d80](https://github.com/Coolgiserz/apple-chain-graph/commit/8bb3d80a5624bf72331c3c3fdf0aa659c55d6b27))
* **graph:** 首屏静止后弹「关键洞察」浮层，让静态空间承载可读结论 (Option A) ([88e585f](https://github.com/Coolgiserz/apple-chain-graph/commit/88e585f40890d3f8c06821a2acf2aec291e3b1b8))
* **i18n:** 接入 i18next 国际化框架，支持中/英/法/日四语切换 ([6aea85f](https://github.com/Coolgiserz/apple-chain-graph/commit/6aea85fb1ba9c131cafd5d11bb87d02c88b187fc))
* **map:** 地图页双后端，默认 Leaflet 免 Key 静态托管可用 ([fb522b5](https://github.com/Coolgiserz/apple-chain-graph/commit/fb522b5612055b62727e886a5f5a6a4266f8af9f))
* **pages:** 增加 GitHub Pages 自动部署配置 ([6b416a8](https://github.com/Coolgiserz/apple-chain-graph/commit/6b416a8eacaa06f957e38fc59f41aa9315665ddf))
* **responsive,P0:** 节点半径随视口缩放 + 首屏/手动 fitView + 顶栏汉堡阈值 52→64em ([18e0029](https://github.com/Coolgiserz/apple-chain-graph/commit/18e0029a2887e23bfaa47649a72620003545c51a))
* **seo:** P0 首页 SEO 基础设施（数据驱动的可索引文本 + 结构化数据 + sitemap/robots） ([7c9adab](https://github.com/Coolgiserz/apple-chain-graph/commit/7c9adabcef3d7151f5f3a60d831f57ce974821b8))
* **supplier-map:** 优化供应商地图交互逻辑 ([308d146](https://github.com/Coolgiserz/apple-chain-graph/commit/308d146949f39a61d683c396923d86b394db8ef0))
* **supplier-map:** 优化供应商地图交互逻辑 ([54a777d](https://github.com/Coolgiserz/apple-chain-graph/commit/54a777dff9ca93a01d52a20ff1de62e13e6737a6))
* **table:** 新增企业列表表格视图，支持按属性筛选与列排序 ([ca3527d](https://github.com/Coolgiserz/apple-chain-graph/commit/ca3527d4e3589e086305707d0c84e5679c3d0f85))
* **ui:** 全站统一暗色主题——dashboard 令牌翻转 + geo 地图/面板暗色化 ([cbfb44c](https://github.com/Coolgiserz/apple-chain-graph/commit/cbfb44ce1540ada257dc871f1f42cac220e96fdf))
* **ui:** 全站统一暗色主题——dashboard 令牌翻转 + geo 地图/面板暗色化 ([5ca6cd8](https://github.com/Coolgiserz/apple-chain-graph/commit/5ca6cd8194d7b4d8f830001ae97e25c48465d188))
* 企业表格 ([94e8235](https://github.com/Coolgiserz/apple-chain-graph/commit/94e823506d951157e63e28bd32df2697fabb9eda))
* 供应链树状视图（第三种视图：Apple→产品线→产品→零部件） ([1c9d2aa](https://github.com/Coolgiserz/apple-chain-graph/commit/1c9d2aa211fb5190e81c120cbdeae837eb107308))
* 供应链瓶颈透视（图分析）— 类型中心性 / 断供波及 / PageRank ([6c59df0](https://github.com/Coolgiserz/apple-chain-graph/commit/6c59df00ed2d17b02235d578d1c1fa2321b82a0e))
* 供应链瓶颈透视（图分析）— 类型中心性 / 断供波及 / PageRank ([93ba97b](https://github.com/Coolgiserz/apple-chain-graph/commit/93ba97b0f71e71c4ba9dcaa1551a0b62c88f6675))
* 供应链脆弱性分析工具（零部件→产品→产品线） ([2f44eae](https://github.com/Coolgiserz/apple-chain-graph/commit/2f44eae558e01e20aeaab9435984acc53a627a32))
* 供应链脆弱性数据集成到图谱（风险视图） ([61eb6c8](https://github.com/Coolgiserz/apple-chain-graph/commit/61eb6c85bd3c26528f1d4c2ebffc4d6713cbf33d))
* 双击节点聚焦其邻居（拓扑隔离视图） ([3dee753](https://github.com/Coolgiserz/apple-chain-graph/commit/3dee753c8b829775fcdc1975431faef62620a115))
* 双击节点聚焦其邻居（拓扑隔离视图） ([1743ba8](https://github.com/Coolgiserz/apple-chain-graph/commit/1743ba8ec4f27fca2ab3f5a06981526c723e321d))
* 增加 Docker 一键启动与站点入口落地页 ([d528a34](https://github.com/Coolgiserz/apple-chain-graph/commit/d528a34a9fd2d3f9620ab2b226998263cb3d8603))
* 时效性数据接口（阶段1）— feeds / schema / DataLayer + UI 新鲜度徽标 ([39f88b2](https://github.com/Coolgiserz/apple-chain-graph/commit/39f88b243d239780e97ae26395e53ab3e0724d0e))
* 瓶颈视图增加单国供应集中度与数据置信度（仅用现有字段） ([952f0e7](https://github.com/Coolgiserz/apple-chain-graph/commit/952f0e7784732a47212fd038fb38b09be2a848ee))
* 瓶颈视图增加单国供应集中度与数据置信度（仅用现有字段） ([7fced2f](https://github.com/Coolgiserz/apple-chain-graph/commit/7fced2feb84b66862c438061eaafef09cd54a15e))
* 生产基地层接入图谱 + 时效性数据接口（阶段1）+ 移动端打磨 ([c0b0dd6](https://github.com/Coolgiserz/apple-chain-graph/commit/c0b0dd636e2b6e0f4e5a519a76ee10fb0711edb8))
* 生产基地层接入图谱 + 移动端交互打磨 + supplier_geo 数据刷新 ([c914856](https://github.com/Coolgiserz/apple-chain-graph/commit/c914856e6b958f59b13fd55361a7879c0bcb6fd9))
* 移动端适配——导航栏响应式汉堡 + 图谱触摸交互 + 响应式布局 ([2a481a8](https://github.com/Coolgiserz/apple-chain-graph/commit/2a481a850a15fcdb08c3949ff410ef8980d2a9bc))


### Bug Fixes

* **analytics:** P1 数据正确性 — impactReach 补 ASSEMBLES 总装边 + share 字段归一化 ([ead2f3e](https://github.com/Coolgiserz/apple-chain-graph/commit/ead2f3e3b4b3df25b56bb47141b1eadc697cfd25))
* **build:** geo_build 依赖 supplier_analysis.json，补 run_analysis 步骤；镜像源改为完整镜像名参数 ([40d6e51](https://github.com/Coolgiserz/apple-chain-graph/commit/40d6e51ee062a23ad9d98d93956d333cfc550daf))
* **ci:** 先建 _site/tools 与 _site/docs 父目录，修复 cp 多级目标报错 ([cf26861](https://github.com/Coolgiserz/apple-chain-graph/commit/cf26861f6d90f7cc937acac80f07dd770b899115))
* **docker:** 去掉 BuildKit 前端拉取，BASE_REGISTRY 支持国内镜像源 ([056b850](https://github.com/Coolgiserz/apple-chain-graph/commit/056b850f5bd21ee2cfefdafa14bfc23cfb4287c7))
* **geo:** i18n 接入 + 双源坐标漂移修复 ([7e15c4f](https://github.com/Coolgiserz/apple-chain-graph/commit/7e15c4fe87c8a0f98c9f92dc8f4455c03961dfe4))
* **geo:** i18n 接入 + 双源坐标漂移修复 ([acc411f](https://github.com/Coolgiserz/apple-chain-graph/commit/acc411fc4bb7e9d33c3d731cb42deb255ce79955))
* **graph/nav:** 修复首页图谱空白、表格跳图谱空白，移除冗余聚合页 ([1c391b3](https://github.com/Coolgiserz/apple-chain-graph/commit/1c391b3a40e62553d42b62bd37648aae1d7ae784))
* **graph:** P2 不可见节点聚焦 + 严苛交互审查修复 ([fd97d6a](https://github.com/Coolgiserz/apple-chain-graph/commit/fd97d6a6129922beae3f8eba67b2b1aa291b8e91))
* **graph:** P2 不可见节点聚焦 + 严苛交互审查修复 ([44bb286](https://github.com/Coolgiserz/apple-chain-graph/commit/44bb28666d4380bcb83f3cbf863a0862dd705b9f))
* **graph:** 修复企业表格/图谱/右侧面板三方联动（P0+P1） ([324b707](https://github.com/Coolgiserz/apple-chain-graph/commit/324b707d946a3175db8301dda85b0e15ea4790aa))
* **graph:** 修复企业表格/图谱/右侧面板三方联动（P0+P1） ([bb88369](https://github.com/Coolgiserz/apple-chain-graph/commit/bb88369b3abc8bddf28a9bc45fd0311d97ef4cee))
* **graph:** 修复点击节点被误判为拖动画布 + 企业表格侧边面板与图谱联动 ([d1ac43f](https://github.com/Coolgiserz/apple-chain-graph/commit/d1ac43f17959f20bcb188c5d3cc144cf8ad303e4))
* **graph:** 修复首页图谱画布未拉伸（固有 300x150 导致看不到图谱） ([d3dbede](https://github.com/Coolgiserz/apple-chain-graph/commit/d3dbedea65042723bcbef02a05ba5ed43a16bb78))
* **graph:** 移除企业表格中“产品不在本供应商表”的误导提示 ([ebfe5c5](https://github.com/Coolgiserz/apple-chain-graph/commit/ebfe5c5c76261408eb3e54d4d01a5f1edf9517e2))
* **graph:** 移除企业表格中“产品不在本供应商表”的误导提示 ([26a0ef1](https://github.com/Coolgiserz/apple-chain-graph/commit/26a0ef126c8a460dd32bb9970ba5026a6b9bf871))
* **graph:** 风险因子面板横向排列排版错乱 → 改为纵向 flex 布局 ([02a9594](https://github.com/Coolgiserz/apple-chain-graph/commit/02a959496cea5bff6674b7728d020d491a086236))
* **graph:** 风险视图勾选无反应——引擎/启动脚本加内容哈希缓存戳 ([cd583d9](https://github.com/Coolgiserz/apple-chain-graph/commit/cd583d9681d722ba7d7e61f05696733241b922df))
* **i18n:** 内联语言包，根除 locales/ 404 与切换失效 ([229c781](https://github.com/Coolgiserz/apple-chain-graph/commit/229c781e9a376d948efc75f6aef67397f054baad))
* **i18n:** 默认中文 + 切换健壮性 ([1e0fda7](https://github.com/Coolgiserz/apple-chain-graph/commit/1e0fda7b2596aaaa65db99a1d11d7321cc4817f3))
* **Makefile:** 修正 .PHONY 目标名含冒号导致的 multiple target patterns ([cd04a78](https://github.com/Coolgiserz/apple-chain-graph/commit/cd04a78b6b3797ad491f02651d4aa9ffc6b9e6d3))
* **nav:** PC 端导航丢失——弃用 &lt;details&gt;，改纯 CSS 复选框汉堡 ([3b6d78c](https://github.com/Coolgiserz/apple-chain-graph/commit/3b6d78ce15eb16fa2c680d6462dcfd1e8fbb2877))
* **nav:** PC 端导航丢失——弃用 &lt;details&gt;，改纯 CSS 复选框汉堡 ([ab2c751](https://github.com/Coolgiserz/apple-chain-graph/commit/ab2c751e6cf996ff7af19d007659d79ea5585eae))
* **nav:** 导航栏改用原生 details 汉堡，彻底修复移动端溢出 ([c10ebee](https://github.com/Coolgiserz/apple-chain-graph/commit/c10ebee03eedad77e39509df766a1bc2f429a2f5))
* **nav:** 导航栏改用原生 details 汉堡，彻底修复移动端溢出 ([b8b26f1](https://github.com/Coolgiserz/apple-chain-graph/commit/b8b26f11c806993331c5209a014d211e512b8683))
* **pages:** 创建 _site/data 目录，修复首页图数据未发布导致的 404 ([73b2a74](https://github.com/Coolgiserz/apple-chain-graph/commit/73b2a74169cd5fa256cd07aaa080db14c769750d))
* **pages:** 创建 _site/data 目录，修复首页图数据未发布导致的 404 ([1139826](https://github.com/Coolgiserz/apple-chain-graph/commit/11398263e2a004107419679db29649b40b091e12))
* panels.js 改用 offsetParent 判面板可见性，修复 CI lint no-undef ([5f77eaf](https://github.com/Coolgiserz/apple-chain-graph/commit/5f77eaff7f51f3250e6e30e5755c89b8e8435c8d))
* **report:** 修复上下游报告 P0/P1 内容问题并移除偏题 Neo4j 入口 ([4c87313](https://github.com/Coolgiserz/apple-chain-graph/commit/4c8731300ee73e33e33b386b853fd052d0da761c))
* **report:** 重写供应链分层模型为数据驱动的完整四层图 ([0e9df17](https://github.com/Coolgiserz/apple-chain-graph/commit/0e9df17387cd1fb086e94678a1dc9df3736b8f09))
* **report:** 重写供应链分层模型为数据驱动的完整四层图 ([ac90704](https://github.com/Coolgiserz/apple-chain-graph/commit/ac90704d2ee25699925201b6e8339c415f55cb42))
* **security,repro:** P1 安全与可复现 — 深链守卫/URL 编码/时间戳/Python 版本统一 ([83be734](https://github.com/Coolgiserz/apple-chain-graph/commit/83be734509b181e154f3315f9af31531bcde07ea))
* **topbar:** 展开/收起供应商与生产基地按钮状态与图谱同步 ([6c336fe](https://github.com/Coolgiserz/apple-chain-graph/commit/6c336fe37b0e923c0872a29acdb08ca01f0fa3ff))
* **topbar:** 彻底移除「展开全部供应商」对生产基地的级联（上轮修复不完整） ([e508c11](https://github.com/Coolgiserz/apple-chain-graph/commit/e508c1141ded11e67d71d735ce85ad9a875201b6))
* **topbar:** 彻底移除「展开全部供应商」对生产基地的级联（上轮修复不完整） ([1979cd4](https://github.com/Coolgiserz/apple-chain-graph/commit/1979cd4306473cf4f0c56393a675d97f0fe7e17f))
* **topbar:** 移除「流动」开关按钮，流动粒子常驻开启 ([5cda180](https://github.com/Coolgiserz/apple-chain-graph/commit/5cda180de0f8d200ab51a6d03bac071af59efabb))
* **topbar:** 移除「流动」开关按钮，流动粒子常驻开启 ([6a73ad1](https://github.com/Coolgiserz/apple-chain-graph/commit/6a73ad1e70004a1f727a7b4c5625485a752ff326))
* **topbar:** 解耦「展开全部供应商」与「生产基地」两个独立开关 ([5673d12](https://github.com/Coolgiserz/apple-chain-graph/commit/5673d12d90b35f3e18bb24da5b397a27a45a76a9))
* **topbar:** 解耦「展开全部供应商」与「生产基地」两个独立开关 ([cb15acd](https://github.com/Coolgiserz/apple-chain-graph/commit/cb15acd08119d4dfb6d01fc1e0f389679701acd7))
* **topbar:** 重置视图退出风险/瓶颈模式；流动改为持续动画且更清晰 ([a82930d](https://github.com/Coolgiserz/apple-chain-graph/commit/a82930dc4c0fd46cc5384b69f8ea6872ed48ae6e))
* **ui:** 可访问性速赢包——键盘焦点/label 绑定/键盘排序/canvas aria/触控目标/对比度 ([82d6229](https://github.com/Coolgiserz/apple-chain-graph/commit/82d6229018ada06741120f8baf4184ee0e087118))
* **ui:** 可访问性速赢包——键盘焦点/label 绑定/键盘排序/canvas aria/触控目标/对比度 ([d6fb34c](https://github.com/Coolgiserz/apple-chain-graph/commit/d6fb34c91d15e70ba66592f7d40e121de791cd1b))
* **ui:** 响应式断点收敛——480/600/820/860/880 五档收敛为 480/860 两档 ([da73b06](https://github.com/Coolgiserz/apple-chain-graph/commit/da73b06728f646a3698e5db3117b76b2d282b7ae))
* **ui:** 响应式断点收敛——480/600/820/860/880 五档收敛为 480/860 两档 ([92faed8](https://github.com/Coolgiserz/apple-chain-graph/commit/92faed85e87c7d9d2337ac94be51498960e73340))
* **ui:** 移动端适配（控制栏折叠 + 安全区 + 触控目标 + 底部抽屉） ([316cc5b](https://github.com/Coolgiserz/apple-chain-graph/commit/316cc5bfc7d8230eb6711721aca3108846e4c69f))
* **ui:** 移动端适配（控制栏折叠 + 安全区 + 触控目标 + 底部抽屉） ([1a4615b](https://github.com/Coolgiserz/apple-chain-graph/commit/1a4615befe894eddfa9e1849bc97346db0d5f046))
* **ux:** 修复 b380635 引入的两处回归 ([68227cc](https://github.com/Coolgiserz/apple-chain-graph/commit/68227ccce97ceb355a1ae3219c7aab66b422d0d8))
* **ux:** 落地 PM/交互评审修复（P0 全 + 关键 P1） ([b380635](https://github.com/Coolgiserz/apple-chain-graph/commit/b380635b84b37939716ec52eae99b9051a76090b))
* **val:** 用权威直接USD市值校正10家非美供应商 并修复缺失ROE渲染崩溃 ([a0e0a5e](https://github.com/Coolgiserz/apple-chain-graph/commit/a0e0a5ebdb8ccb0fb9a63a566a1249a8464671bd))
* 仅移除无实质内容的通用出版商主页链接，保留具体文章类来源 ([d707f86](https://github.com/Coolgiserz/apple-chain-graph/commit/d707f86a2dfacd8618099a234803e4d6c92559ab))
* 供应商地图 POI 显示中文供应商名并支持名称标签 ([246b4cb](https://github.com/Coolgiserz/apple-chain-graph/commit/246b4cb28ce173554313de51b96450069aca0a47))
* 供应商地图 POI 显示中文供应商名并支持名称标签 ([219c4c2](https://github.com/Coolgiserz/apple-chain-graph/commit/219c4c2588784fd0d6f65a363832c4660ed682e0))
* 修复四项 P0 级缺陷（CI 门禁/置信度/凭据泄露/i18n 审计） ([eb86e2f](https://github.com/Coolgiserz/apple-chain-graph/commit/eb86e2f7dfbfffc913895fc6d11c8c9c56f730cb))
* 修复四项 P0 级缺陷（CI 门禁/置信度/凭据泄露/i18n 审计） ([1130f51](https://github.com/Coolgiserz/apple-chain-graph/commit/1130f51fa011b1ce10ecbf9983598aec13f9b75e))
* 修复风险视图右侧面板内容被遮挡 ([d38f6d0](https://github.com/Coolgiserz/apple-chain-graph/commit/d38f6d0c4e19d502e28bf66cee407b40ea9f0490))
* 修复风险视图右侧面板内容被遮挡 ([0694bec](https://github.com/Coolgiserz/apple-chain-graph/commit/0694bece1b81f67048fe4994965ab991afa7b269))
* 恢复 5 家孤立供应商的真实供应链关系（修正 generate.py 源） ([a3a1123](https://github.com/Coolgiserz/apple-chain-graph/commit/a3a1123ad822521d796406b0bf73977a292710a7))
* 恢复 5 家孤立供应商的真实供应链关系（修正 generate.py 源） ([753d7c5](https://github.com/Coolgiserz/apple-chain-graph/commit/753d7c5d92e87cae808a00f1f135f93bd74e095f))
* 本地部署与 CI 构建修复（feeds 可达 / sentiment 缺失 / Python 3.14） ([544a8eb](https://github.com/Coolgiserz/apple-chain-graph/commit/544a8eb227256747aa9147412f71dd1d21318705))
* 连接孤立的摄像头模组节点到对应产品 ([7d01576](https://github.com/Coolgiserz/apple-chain-graph/commit/7d01576c1b452af3d8229bbc61809fc72d9c51ee))
* 连接孤立的摄像头模组节点到对应产品 ([fd65bb2](https://github.com/Coolgiserz/apple-chain-graph/commit/fd65bb29ea88093d40bdc27836e424a4006e7710))
* 高优先级可维护性修复（esc 转义/外链白名单/清理死代码） ([a66124b](https://github.com/Coolgiserz/apple-chain-graph/commit/a66124bdb54b960fabac1366d8a22a4ec1236c8c))
* 高优先级可维护性修复（esc 转义/外链白名单/清理死代码） ([fdb1da1](https://github.com/Coolgiserz/apple-chain-graph/commit/fdb1da1b4a8b0d9e4c35911d105892c0687bf774))

## [1.10.0](https://github.com/Coolgiserz/apple-chain-graph/compare/v1.9.4...v1.10.0) (2026-09-01)


### Features

* **ui:** 全站统一暗色主题——dashboard 令牌翻转 + geo 地图/面板暗色化 ([cbfb44c](https://github.com/Coolgiserz/apple-chain-graph/commit/cbfb44ce1540ada257dc871f1f42cac220e96fdf))
* **ui:** 全站统一暗色主题——dashboard 令牌翻转 + geo 地图/面板暗色化 ([5ca6cd8](https://github.com/Coolgiserz/apple-chain-graph/commit/5ca6cd8194d7b4d8f830001ae97e25c48465d188))

## [1.9.4](https://github.com/Coolgiserz/apple-chain-graph/compare/v1.9.3...v1.9.4) (2026-09-01)


### Bug Fixes

* **ui:** 可访问性速赢包——键盘焦点/label 绑定/键盘排序/canvas aria/触控目标/对比度 ([82d6229](https://github.com/Coolgiserz/apple-chain-graph/commit/82d6229018ada06741120f8baf4184ee0e087118))
* **ui:** 可访问性速赢包——键盘焦点/label 绑定/键盘排序/canvas aria/触控目标/对比度 ([d6fb34c](https://github.com/Coolgiserz/apple-chain-graph/commit/d6fb34c91d15e70ba66592f7d40e121de791cd1b))

## [1.9.3](https://github.com/Coolgiserz/apple-chain-graph/compare/v1.9.2...v1.9.3) (2026-08-28)


### Bug Fixes

* **geo:** i18n 接入 + 双源坐标漂移修复 ([7e15c4f](https://github.com/Coolgiserz/apple-chain-graph/commit/7e15c4fe87c8a0f98c9f92dc8f4455c03961dfe4))

## [1.9.2](https://github.com/Coolgiserz/apple-chain-graph/compare/v1.9.1...v1.9.2) (2026-08-28)


### Bug Fixes

* **analytics:** P1 数据正确性 — impactReach 补 ASSEMBLES 总装边 + share 字段归一化 ([ead2f3e](https://github.com/Coolgiserz/apple-chain-graph/commit/ead2f3e3b4b3df25b56bb47141b1eadc697cfd25))
* **security,repro:** P1 安全与可复现 — 深链守卫/URL 编码/时间戳/Python 版本统一 ([83be734](https://github.com/Coolgiserz/apple-chain-graph/commit/83be734509b181e154f3315f9af31531bcde07ea))

## [1.9.1](https://github.com/Coolgiserz/apple-chain-graph/compare/v1.9.0...v1.9.1) (2026-08-28)


### Bug Fixes

* **report:** 重写供应链分层模型为数据驱动的完整四层图 ([0e9df17](https://github.com/Coolgiserz/apple-chain-graph/commit/0e9df17387cd1fb086e94678a1dc9df3736b8f09))
* 修复四项 P0 级缺陷（CI 门禁/置信度/凭据泄露/i18n 审计） ([eb86e2f](https://github.com/Coolgiserz/apple-chain-graph/commit/eb86e2f7dfbfffc913895fc6d11c8c9c56f730cb))
* 修复四项 P0 级缺陷（CI 门禁/置信度/凭据泄露/i18n 审计） ([1130f51](https://github.com/Coolgiserz/apple-chain-graph/commit/1130f51fa011b1ce10ecbf9983598aec13f9b75e))

## [1.9.0](https://github.com/Coolgiserz/apple-chain-graph/compare/v1.8.0...v1.9.0) (2026-08-13)


### Features

* **supplier-map:** 优化供应商地图交互逻辑 ([308d146](https://github.com/Coolgiserz/apple-chain-graph/commit/308d146949f39a61d683c396923d86b394db8ef0))
* **supplier-map:** 优化供应商地图交互逻辑 ([54a777d](https://github.com/Coolgiserz/apple-chain-graph/commit/54a777dff9ca93a01d52a20ff1de62e13e6737a6))

## [1.8.0](https://github.com/Coolgiserz/apple-chain-graph/compare/v1.7.1...v1.8.0) (2026-08-13)


### Features

* 瓶颈视图增加单国供应集中度与数据置信度（仅用现有字段） ([952f0e7](https://github.com/Coolgiserz/apple-chain-graph/commit/952f0e7784732a47212fd038fb38b09be2a848ee))
* 瓶颈视图增加单国供应集中度与数据置信度（仅用现有字段） ([7fced2f](https://github.com/Coolgiserz/apple-chain-graph/commit/7fced2feb84b66862c438061eaafef09cd54a15e))

## [1.7.1](https://github.com/Coolgiserz/apple-chain-graph/compare/v1.7.0...v1.7.1) (2026-08-12)


### Bug Fixes

* 连接孤立的摄像头模组节点到对应产品 ([7d01576](https://github.com/Coolgiserz/apple-chain-graph/commit/7d01576c1b452af3d8229bbc61809fc72d9c51ee))
* 连接孤立的摄像头模组节点到对应产品 ([fd65bb2](https://github.com/Coolgiserz/apple-chain-graph/commit/fd65bb29ea88093d40bdc27836e424a4006e7710))

## [1.7.0](https://github.com/Coolgiserz/apple-chain-graph/compare/v1.6.4...v1.7.0) (2026-08-12)


### Features

* 供应链树状视图（第三种视图：Apple→产品线→产品→零部件） ([1c9d2aa](https://github.com/Coolgiserz/apple-chain-graph/commit/1c9d2aa211fb5190e81c120cbdeae837eb107308))


### Bug Fixes

* 仅移除无实质内容的通用出版商主页链接，保留具体文章类来源 ([d707f86](https://github.com/Coolgiserz/apple-chain-graph/commit/d707f86a2dfacd8618099a234803e4d6c92559ab))

## [1.6.4](https://github.com/Coolgiserz/apple-chain-graph/compare/v1.6.3...v1.6.4) (2026-08-12)


### Bug Fixes

* 高优先级可维护性修复（esc 转义/外链白名单/清理死代码） ([a66124b](https://github.com/Coolgiserz/apple-chain-graph/commit/a66124bdb54b960fabac1366d8a22a4ec1236c8c))
* 高优先级可维护性修复（esc 转义/外链白名单/清理死代码） ([fdb1da1](https://github.com/Coolgiserz/apple-chain-graph/commit/fdb1da1b4a8b0d9e4c35911d105892c0687bf774))

## [1.6.3](https://github.com/Coolgiserz/apple-chain-graph/compare/v1.6.2...v1.6.3) (2026-08-11)


### Bug Fixes

* **topbar:** 展开/收起供应商与生产基地按钮状态与图谱同步 ([6c336fe](https://github.com/Coolgiserz/apple-chain-graph/commit/6c336fe37b0e923c0872a29acdb08ca01f0fa3ff))
* **topbar:** 彻底移除「展开全部供应商」对生产基地的级联（上轮修复不完整） ([e508c11](https://github.com/Coolgiserz/apple-chain-graph/commit/e508c1141ded11e67d71d735ce85ad9a875201b6))
* **topbar:** 彻底移除「展开全部供应商」对生产基地的级联（上轮修复不完整） ([1979cd4](https://github.com/Coolgiserz/apple-chain-graph/commit/1979cd4306473cf4f0c56393a675d97f0fe7e17f))
* **topbar:** 移除「流动」开关按钮，流动粒子常驻开启 ([5cda180](https://github.com/Coolgiserz/apple-chain-graph/commit/5cda180de0f8d200ab51a6d03bac071af59efabb))
* **topbar:** 移除「流动」开关按钮，流动粒子常驻开启 ([6a73ad1](https://github.com/Coolgiserz/apple-chain-graph/commit/6a73ad1e70004a1f727a7b4c5625485a752ff326))
* **topbar:** 解耦「展开全部供应商」与「生产基地」两个独立开关 ([5673d12](https://github.com/Coolgiserz/apple-chain-graph/commit/5673d12d90b35f3e18bb24da5b397a27a45a76a9))
* **topbar:** 解耦「展开全部供应商」与「生产基地」两个独立开关 ([cb15acd](https://github.com/Coolgiserz/apple-chain-graph/commit/cb15acd08119d4dfb6d01fc1e0f389679701acd7))
* **topbar:** 重置视图退出风险/瓶颈模式；流动改为持续动画且更清晰 ([a82930d](https://github.com/Coolgiserz/apple-chain-graph/commit/a82930dc4c0fd46cc5384b69f8ea6872ed48ae6e))

## [1.6.2](https://github.com/Coolgiserz/apple-chain-graph/compare/v1.6.1...v1.6.2) (2026-08-11)


### Bug Fixes

* **pages:** 创建 _site/data 目录，修复首页图数据未发布导致的 404 ([73b2a74](https://github.com/Coolgiserz/apple-chain-graph/commit/73b2a74169cd5fa256cd07aaa080db14c769750d))
* **pages:** 创建 _site/data 目录，修复首页图数据未发布导致的 404 ([1139826](https://github.com/Coolgiserz/apple-chain-graph/commit/11398263e2a004107419679db29649b40b091e12))

## [1.6.1](https://github.com/Coolgiserz/apple-chain-graph/compare/v1.6.0...v1.6.1) (2026-08-11)


### Bug Fixes

* panels.js 改用 offsetParent 判面板可见性，修复 CI lint no-undef ([5f77eaf](https://github.com/Coolgiserz/apple-chain-graph/commit/5f77eaff7f51f3250e6e30e5755c89b8e8435c8d))
* 修复风险视图右侧面板内容被遮挡 ([d38f6d0](https://github.com/Coolgiserz/apple-chain-graph/commit/d38f6d0c4e19d502e28bf66cee407b40ea9f0490))
* 修复风险视图右侧面板内容被遮挡 ([0694bec](https://github.com/Coolgiserz/apple-chain-graph/commit/0694bece1b81f67048fe4994965ab991afa7b269))

## [1.6.0](https://github.com/Coolgiserz/apple-chain-graph/compare/v1.5.0...v1.6.0) (2026-08-11)


### Features

* 双击节点聚焦其邻居（拓扑隔离视图） ([3dee753](https://github.com/Coolgiserz/apple-chain-graph/commit/3dee753c8b829775fcdc1975431faef62620a115))
* 双击节点聚焦其邻居（拓扑隔离视图） ([1743ba8](https://github.com/Coolgiserz/apple-chain-graph/commit/1743ba8ec4f27fca2ab3f5a06981526c723e321d))

## [1.5.0](https://github.com/Coolgiserz/apple-chain-graph/compare/v1.4.0...v1.5.0) (2026-08-11)


### Features

* 供应链瓶颈透视（图分析）— 类型中心性 / 断供波及 / PageRank ([6c59df0](https://github.com/Coolgiserz/apple-chain-graph/commit/6c59df00ed2d17b02235d578d1c1fa2321b82a0e))
* 供应链瓶颈透视（图分析）— 类型中心性 / 断供波及 / PageRank ([93ba97b](https://github.com/Coolgiserz/apple-chain-graph/commit/93ba97b0f71e71c4ba9dcaa1551a0b62c88f6675))

## [1.4.0](https://github.com/Coolgiserz/apple-chain-graph/compare/v1.3.0...v1.4.0) (2026-08-11)


### Features

* **ci:** 自动版本号 CD 流程（git describe 构建戳 + release-please 语义版本） ([993ff40](https://github.com/Coolgiserz/apple-chain-graph/commit/993ff40ec73d25350b061aafaee730e31020492b))
* **ci:** 自动版本号 CD 流程（git describe 构建戳 + release-please 语义版本） ([cea6213](https://github.com/Coolgiserz/apple-chain-graph/commit/cea621324b156874c3cc80f78a89cfda02cd3989))
* **graph:** 渐进式展开 + 沿边流动粒子，让图谱「活」起来 ([c0b19a0](https://github.com/Coolgiserz/apple-chain-graph/commit/c0b19a01bb8f18a1ba1ee5d9af89204c91fdc78e))
* **graph:** 首屏静止后弹「关键洞察」浮层，让静态空间承载可读结论 (Option A) ([88e585f](https://github.com/Coolgiserz/apple-chain-graph/commit/88e585f40890d3f8c06821a2acf2aec291e3b1b8))
* **responsive,P0:** 节点半径随视口缩放 + 首屏/手动 fitView + 顶栏汉堡阈值 52→64em ([18e0029](https://github.com/Coolgiserz/apple-chain-graph/commit/18e0029a2887e23bfaa47649a72620003545c51a))
* 时效性数据接口（阶段1）— feeds / schema / DataLayer + UI 新鲜度徽标 ([39f88b2](https://github.com/Coolgiserz/apple-chain-graph/commit/39f88b243d239780e97ae26395e53ab3e0724d0e))
* 生产基地层接入图谱 + 时效性数据接口（阶段1）+ 移动端打磨 ([c0b0dd6](https://github.com/Coolgiserz/apple-chain-graph/commit/c0b0dd636e2b6e0f4e5a519a76ee10fb0711edb8))
* 生产基地层接入图谱 + 移动端交互打磨 + supplier_geo 数据刷新 ([c914856](https://github.com/Coolgiserz/apple-chain-graph/commit/c914856e6b958f59b13fd55361a7879c0bcb6fd9))


### Bug Fixes

* **graph:** P2 不可见节点聚焦 + 严苛交互审查修复 ([fd97d6a](https://github.com/Coolgiserz/apple-chain-graph/commit/fd97d6a6129922beae3f8eba67b2b1aa291b8e91))
* **graph:** P2 不可见节点聚焦 + 严苛交互审查修复 ([44bb286](https://github.com/Coolgiserz/apple-chain-graph/commit/44bb28666d4380bcb83f3cbf863a0862dd705b9f))
* **graph:** 修复企业表格/图谱/右侧面板三方联动（P0+P1） ([324b707](https://github.com/Coolgiserz/apple-chain-graph/commit/324b707d946a3175db8301dda85b0e15ea4790aa))
* **graph:** 修复企业表格/图谱/右侧面板三方联动（P0+P1） ([bb88369](https://github.com/Coolgiserz/apple-chain-graph/commit/bb88369b3abc8bddf28a9bc45fd0311d97ef4cee))
* **graph:** 移除企业表格中“产品不在本供应商表”的误导提示 ([ebfe5c5](https://github.com/Coolgiserz/apple-chain-graph/commit/ebfe5c5c76261408eb3e54d4d01a5f1edf9517e2))
* **graph:** 移除企业表格中“产品不在本供应商表”的误导提示 ([26a0ef1](https://github.com/Coolgiserz/apple-chain-graph/commit/26a0ef126c8a460dd32bb9970ba5026a6b9bf871))
* **Makefile:** 修正 .PHONY 目标名含冒号导致的 multiple target patterns ([cd04a78](https://github.com/Coolgiserz/apple-chain-graph/commit/cd04a78b6b3797ad491f02651d4aa9ffc6b9e6d3))
* **nav:** PC 端导航丢失——弃用 &lt;details&gt;，改纯 CSS 复选框汉堡 ([3b6d78c](https://github.com/Coolgiserz/apple-chain-graph/commit/3b6d78ce15eb16fa2c680d6462dcfd1e8fbb2877))
* **nav:** PC 端导航丢失——弃用 &lt;details&gt;，改纯 CSS 复选框汉堡 ([ab2c751](https://github.com/Coolgiserz/apple-chain-graph/commit/ab2c751e6cf996ff7af19d007659d79ea5585eae))
* **nav:** 导航栏改用原生 details 汉堡，彻底修复移动端溢出 ([c10ebee](https://github.com/Coolgiserz/apple-chain-graph/commit/c10ebee03eedad77e39509df766a1bc2f429a2f5))
* **nav:** 导航栏改用原生 details 汉堡，彻底修复移动端溢出 ([b8b26f1](https://github.com/Coolgiserz/apple-chain-graph/commit/b8b26f11c806993331c5209a014d211e512b8683))
* **report:** 修复上下游报告 P0/P1 内容问题并移除偏题 Neo4j 入口 ([4c87313](https://github.com/Coolgiserz/apple-chain-graph/commit/4c8731300ee73e33e33b386b853fd052d0da761c))
* **ui:** 移动端适配（控制栏折叠 + 安全区 + 触控目标 + 底部抽屉） ([316cc5b](https://github.com/Coolgiserz/apple-chain-graph/commit/316cc5bfc7d8230eb6711721aca3108846e4c69f))
* **ui:** 移动端适配（控制栏折叠 + 安全区 + 触控目标 + 底部抽屉） ([1a4615b](https://github.com/Coolgiserz/apple-chain-graph/commit/1a4615befe894eddfa9e1849bc97346db0d5f046))
* **ux:** 修复 b380635 引入的两处回归 ([68227cc](https://github.com/Coolgiserz/apple-chain-graph/commit/68227ccce97ceb355a1ae3219c7aab66b422d0d8))
* **ux:** 落地 PM/交互评审修复（P0 全 + 关键 P1） ([b380635](https://github.com/Coolgiserz/apple-chain-graph/commit/b380635b84b37939716ec52eae99b9051a76090b))
* **val:** 用权威直接USD市值校正10家非美供应商 并修复缺失ROE渲染崩溃 ([a0e0a5e](https://github.com/Coolgiserz/apple-chain-graph/commit/a0e0a5ebdb8ccb0fb9a63a566a1249a8464671bd))
* 恢复 5 家孤立供应商的真实供应链关系（修正 generate.py 源） ([a3a1123](https://github.com/Coolgiserz/apple-chain-graph/commit/a3a1123ad822521d796406b0bf73977a292710a7))
* 恢复 5 家孤立供应商的真实供应链关系（修正 generate.py 源） ([753d7c5](https://github.com/Coolgiserz/apple-chain-graph/commit/753d7c5d92e87cae808a00f1f135f93bd74e095f))
* 本地部署与 CI 构建修复（feeds 可达 / sentiment 缺失 / Python 3.14） ([544a8eb](https://github.com/Coolgiserz/apple-chain-graph/commit/544a8eb227256747aa9147412f71dd1d21318705))
