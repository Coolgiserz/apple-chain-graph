# Changelog

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
