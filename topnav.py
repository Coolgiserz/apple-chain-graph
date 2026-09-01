# -*- coding: utf-8 -*-
"""统一的跨页面顶部导航条（共享组件）。

这就是用户最初想要的「融合」——一个固定在每个页面顶部的导航栏，
让用户能在各板块之间互相点击跳转，无需再为每个板块单独造一个
「整合页 / 融合页」式的页面。当前板块：首页图谱 / 企业列表 / 上下游报告 /
供应商地图 / 估值看板。首页即供应链图谱（仓库根目录 index.html）。

`root` 是当前页面相对于「仓库根目录」的相对路径：
  - 根目录首页（图谱）：              root = ""
  - dist 下的页面（报告 / 列表）：    root = "../"
  - tools/visualizations 下的页面（地图 / 看板）：root = "../../"

`active` 为当前页的 key：graph / table / report / map / dash（用于高亮）。
"""

import os

NAV_ITEMS = [
    ("graph",  "供应链图谱", "index.html"),
    ("table",  "企业列表",    "dist/supplier_table.html"),
    ("report", "上下游报告",  "dist/apple_supply_chain_report.html"),
    ("map",    "供应商地图", "tools/visualizations/supplier_geo.html"),
    ("dash",   "估值看板",    "tools/visualizations/supplier_dashboard.html"),
]

# 源码仓库（GitHub）图标按钮：放在导航条最右侧，所有页面共享。
GITHUB_URL = "https://github.com/Coolgiserz/apple-chain-graph"
GITHUB_LINK = (
    "<a class='wb-github' href='%s' target='_blank' rel='noopener' "
    "title='在 GitHub 查看本项目源码'>"
    "<svg width='20' height='20' viewBox='0 0 16 16' fill='currentColor' aria-hidden='true'>"
    "<path d='M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 "
    "0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 "
    "1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 "
    "0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 "
    "2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 "
    "3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8z'/>"
    "</svg></a>"
)

# 导航条自身的样式（注入到各页面 <style> 中）。固定定位，z-index 最高。
# 移动端用纯 CSS「复选框汉堡」：菜单 <ul> 始终是普通子元素，桌面端永远 display:flex 常驻，
# 移动端点 ☰（label 联动隐藏的 checkbox）才以 :checked 下拉展开。零 JS 依赖，
# 因此即便脚本未执行，也绝不会把链接横向铺开溢出；且不依赖 <details>，避免其关闭态被
# 浏览器引擎级隐藏导致桌面端菜单整条消失的问题。
TOPNAV_CSS = """
:root {
  --bg: #0c1020; --card: #131a2e; --soft: #1b2340; --line: #2a3450; --line-soft: #1c2336;
  --ink: #e8ecf4; --ink-soft: #cfe0ff; --muted: #9fb0d0; --muted-dim: #7c8aa8;
  --bright: #ffffff; --link: #dbeafe; --ink-inverse: #111111;
  --control: #33406a; --control-hover: #3a4a6e; --control-border: #3f4f7a;
  --blue: #6ea0ff; --primary: #2f6fed; --primary-hover: #3b82f6; --focus: #5b8cff;
  --brand: #0a2540; --brand-2: #0a66c2;
  --violet: #8b5cf6; --pink: #ec4899; --cyan: #22d3ee;
  --green: #4ade80; --success-ink: #bbf7d0; --success-bg: #163a2a;
  --red: #f87171; --danger-ink: #ffb4b4; --danger-bg: #3b1520; --danger-line: #7f1d1d;
  --amber: #fbbf24; --warn: #f59e0b; --warn-ink: #fde68a; --warn-bg: #3a2e16; --warn-line: #7a5c14;
  --fs-xs: 11px; --fs-sm: 12px; --fs-base: 13px; --fs-md: 14px;
  --fs-lg: 16px; --fs-xl: 18px; --fs-display: 24px;
}
.wb-topnav{position:fixed;top:0;left:0;right:0;height:calc(52px + env(safe-area-inset-top));padding:env(safe-area-inset-top) 12px 0;z-index:9999;
  display:flex;align-items:center;gap:8px;min-width:0;
  background:linear-gradient(135deg,var(--brand),var(--brand-2));color:var(--bright);
  font-family:-apple-system,'Segoe UI',Roboto,'PingFang SC','Microsoft YaHei',sans-serif;
  box-shadow:0 2px 8px rgba(0,0,0,.18)}
.wb-topnav .brand{font-weight:700;font-size: var(--fs-md);margin-right:8px;white-space:nowrap;opacity:.95;flex:0 0 auto}
.wb-topnav a{color:var(--link);text-decoration:none;font-size: var(--fs-base);padding:7px 13px;border-radius:8px;
  white-space:nowrap;transition:background .15s}
.wb-topnav a:hover{background:rgba(255,255,255,.16);color:var(--bright)}
.wb-topnav a.active{background:var(--bright);color:var(--brand);font-weight:700}
.wb-topnav .spacer{flex:1 1 auto;min-width:0}
/* 隐藏的驱动复选框（label 联动切换）；桌面端一并彻底隐藏 */
.wb-topnav .nav-toggle-cb{position:absolute;width:1px;height:1px;opacity:0;pointer-events:none;margin:0}
/* 汉堡按钮（label）：移动端显示、桌面端媒体查询隐藏 */
.wb-topnav .nav-toggle{display:inline-flex;align-items:center;justify-content:center;width:38px;height:34px;
  margin:0;border-radius:8px;color:var(--bright);font-size: var(--fs-xl);line-height:1;cursor:pointer;user-select:none}
.wb-topnav .nav-toggle:hover{background:rgba(255,255,255,.16)}
.wb-topnav .nav-collapse{position:relative;flex:0 0 auto}
/* 菜单默认隐藏（移动端），由 :checked 切换为下拉 */
.wb-topnav .nav-collapse > ul{position:absolute;top:calc(100% + 8px);left:0;z-index:1;margin:0;padding:6px;
  list-style:none;display:none;flex-direction:column;gap:2px;min-width:172px;
  background:var(--brand);border:1px solid rgba(255,255,255,.16);border-radius:12px;box-shadow:0 10px 30px rgba(0,0,0,.45)}
.wb-topnav .nav-toggle-cb:checked ~ .nav-collapse > ul{display:flex}
.wb-topnav .nav-collapse > ul a{display:block;width:100%;text-align:left}
.wb-topnav .wb-github{display:flex;align-items:center;justify-content:center;width:34px;height:34px;
  margin-left:6px;border-radius:8px;color:var(--bright);opacity:.9;transition:background .15s,opacity .15s;flex:0 0 auto}
.wb-topnav .wb-github:hover{background:rgba(255,255,255,.16);color:var(--bright);opacity:1}
.wb-topnav #langSwitch{height:34px;margin-left:6px;border-radius:8px;border:1px solid rgba(255,255,255,.25);
  background:rgba(255,255,255,.08);color:var(--bright);font-size: var(--fs-base);padding:0 6px;cursor:pointer;flex:0 0 auto}
.wb-topnav #langSwitch:hover{background:rgba(255,255,255,.16);color:var(--bright)}
.wb-topnav #langSwitch option{color:var(--ink-inverse)}
/* 桌面端（≥860px）：菜单常驻横向排列（永远可见），隐藏汉堡与复选框 */
@media (min-width: 860px){
  .wb-topnav .nav-toggle, .wb-topnav .nav-toggle-cb{display:none}
  .wb-topnav .nav-collapse > ul{position:static;display:flex;flex-direction:row;gap:6px;min-width:0;
    background:none;border:none;box-shadow:none;padding:0}
}
"""


def topnav(root="../", active=None):
    """返回统一导航条的 HTML 片段（含国际化框架 + 访问统计脚本）。

    导航菜单用纯 CSS「复选框汉堡」实现：**纯 CSS、零 JS 依赖**。菜单 ``<ul>`` 始终是普通
    子元素——桌面端（≥860px）由媒体查询强制 ``display:flex`` 横向常驻；移动端点 ☰
    （``<label>`` 联动一个隐藏 ``<input type=checkbox>``）才以 ``:checked`` 下拉展开。
    因此即便后续脚本未执行，移动端也绝不会把 5 个链接横向铺开溢出屏幕（此前第三方
    responsive-nav 把折叠态挂在 JS 注入的 ``.js`` 类上，脚本一失败就整条导航溢出）；
    也不依赖 ``<details>``，避免其关闭态被浏览器引擎级隐藏导致桌面端菜单整条消失。
    """
    parts = ["<nav class='wb-topnav'>", "<span class='brand' data-i18n='brand'>Apple 供应链</span>"]
    # 汉堡：隐藏复选框 + 其 label。checkbox 须在 .nav-collapse 之前，使 :checked ~ 兄弟选择器生效。
    parts.append("<input type='checkbox' id='navToggle' class='nav-toggle-cb' aria-hidden='true'>")
    parts.append("<label class='nav-toggle' for='navToggle' aria-label='菜单'>&#9776;</label>")
    # 菜单区：始终为普通 <ul>，桌面端常驻、移动端由 :checked 切换下拉
    parts.append("<nav class='nav-collapse'><ul>")
    for key, label, path in NAV_ITEMS:
        cls = " class='active'" if key == active else ""
        parts.append("<li><a href='%s'%s data-i18n='nav.%s'>%s</a></li>" % (root + path, cls, key, label))
    parts.append("</ul></nav>")
    # 语言切换下拉（始终可见，不折叠进汉堡）
    parts.append("<select id='langSwitch' aria-label='Language' "
                  "onchange='window.i18n&&window.i18n.changeLanguage(this.value)'>"
                  "<option value='zh'>中文</option><option value='en'>English</option>"
                  "<option value='fr'>Français</option><option value='ja'>日本語</option></select>")
    parts.append("<span class='spacer'></span>")
    parts.append(GITHUB_LINK % GITHUB_URL)
    parts.append("</nav>")
    # 国际化框架（i18next，本地 vendored）。
    # dist/locales.js 由 build_viewer.py 从 locales/*.json 内联生成，i18n.js 直接读取，
    # 不依赖运行时 fetch —— 规避「部署遗漏 locales/ 目录 → 404」与 file:// 的 CORS 限制。
    # ?v= 资源版本号：改动语言包/引导脚本后递增，强制浏览器放弃旧缓存
    parts.append("<script src='%sdist/vendor/i18next.min.js?v=20260809k'></script>" % root)
    parts.append("<script src='%sdist/locales.js?v=20260809k'></script>" % root)
    parts.append("<script src='%sdist/i18n.js?v=20260809k'></script>" % root)
    parts.append(analytics_js())
    return "".join(parts)


# ---------------------------------------------------------------------------
# 访问统计（隐私友好第三方，可选；默认关闭，配置后启用）
# ---------------------------------------------------------------------------
# 支持 Umami（默认，自托管 / umami.is 云，隐私友好、数据可自持）与 GoatCounter（备用）。
# 全部配置项均通过「环境变量」注入，源码不再硬编码任何 UUID / 地址；
# 未通过环境变量提供时回退到下方 __DEFAULTS__（项目演示站的占位值），不影响构建。
#
# 配置方式（优先级：进程环境变量 > 仓库根 .env 文件 > 内置默认值）：
#   1) 本地 / 自建：把值写进仓库根目录的 .env（已被 .gitignore 忽略，不会提交到仓库）。
#   2) GitHub Pages CI：在仓库 Settings → Secrets 添加同名 secret，
#      并在 .github/workflows/pages.yml 的 Build 步骤用 env: 注入（见文件内注释示例）。
#   3) 留空则不加载任何脚本、不发任何外部请求（本地 file:// 预览 / 未配置时零副作用）。
#      脚本仅在 http(s) 域名下才发送数据（见 analytics_js 的 location.protocol 门控）。
#
# Umami 用法：
#   1) 自托管 Umami（Docker）或用 umami.is 云，登录后台 Add Website 得到 Website ID（UUID）
#      与脚本地址（umami.is 云为 https://analytics.umami.is/script.js；自托管换成你的域名，
#      如 https://analytics.你的域名/script.js）。
#   2) 把上面得到的 Website ID 设到环境变量 ANALYTICS_WEBSITE_ID（自托管且脚本与 API 不同域时，
#      把 ANALYTICS_UMAMI_SRC 也设成你的地址，必要时在 analytics_js() 里加
#      s.dataset.hostUrl='https://你的实例域名'）。
#   3) 重生成页面（python build_all.py）。

# 内置默认值：仅当未通过环境变量提供时使用（项目演示站占位，可安全覆盖 / 留空禁用）。
__DEFAULTS__ = {
    "ANALYTICS_PROVIDER":   "umami",
    "ANALYTICS_WEBSITE_ID": "126e2a2e-a550-4669-8f17-f31fb60d0861",  # 演示站 Website ID（UUID）
    "ANALYTICS_UMAMI_SRC":  "https://cloud.umami.is/script.js",
    "ANALYTICS_CODE":       "",   # 仅 provider="goatcounter" 时生效
}


def _analytics_config():
    """合并环境变量与默认值，返回访问统计配置字典（源码不持有真实密钥）。"""
    return {k: os.environ.get(k, v) for k, v in __DEFAULTS__.items()}


def analytics_js():
    """返回隐私友好统计的注入脚本；未配置时返回空字符串（不加载、不发请求）。"""
    cfg = _analytics_config()
    provider = cfg["ANALYTICS_PROVIDER"]
    if provider == "umami":
        website_id = cfg["ANALYTICS_WEBSITE_ID"]
        if not website_id:
            return ""
        return ("<script>(function(){"
                "if(location.protocol.indexOf('http')!==0)return;"   # file:// 不计
                "var s=document.createElement('script');s.async=true;"
                "s.src=%r;s.dataset.websiteId=%r;"
                "document.head.appendChild(s);})();</script>"
                % (cfg["ANALYTICS_UMAMI_SRC"], website_id))
    if provider == "goatcounter":
        code = cfg["ANALYTICS_CODE"]
        if not code:
            return ""
        return ("<script>(function(){"
                "if(location.protocol.indexOf('http')!==0)return;"
                "var s=document.createElement('script');s.async=true;"
                "s.src='https://gc.zgo.at/count.js';"
                "s.dataset.goatcounter='https://%s.goatcounter.com/count';"
                "document.head.appendChild(s);})();</script>" % code)
    return ""

