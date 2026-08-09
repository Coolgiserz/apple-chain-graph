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
TOPNAV_CSS = """
.wb-topnav{position:fixed;top:0;left:0;right:0;height:52px;z-index:9999;
  display:flex;align-items:center;gap:6px;padding:0 14px;
  background:linear-gradient(135deg,#0a2540,#0a66c2);color:#fff;
  font-family:-apple-system,'Segoe UI',Roboto,'PingFang SC','Microsoft YaHei',sans-serif;
  box-shadow:0 2px 8px rgba(0,0,0,.18)}
.wb-topnav .brand{font-weight:700;font-size:14px;margin-right:10px;white-space:nowrap;opacity:.95}
.wb-topnav a{color:#dbeafe;text-decoration:none;font-size:13.5px;padding:7px 13px;border-radius:8px;
  white-space:nowrap;transition:background .15s}
.wb-topnav a:hover{background:rgba(255,255,255,.16);color:#fff}
.wb-topnav a.active{background:#fff;color:#0a2540;font-weight:700}
.wb-topnav .spacer{flex:1}
.wb-topnav .wb-github{display:flex;align-items:center;justify-content:center;width:34px;height:34px;
  margin-left:6px;border-radius:8px;color:#fff;opacity:.9;transition:background .15s,opacity .15s}
.wb-topnav .wb-github:hover{background:rgba(255,255,255,.16);color:#fff;opacity:1}
.wb-topnav #langSwitch{height:34px;margin-left:6px;border-radius:8px;border:1px solid rgba(255,255,255,.25);
  background:rgba(255,255,255,.08);color:#fff;font-size:13px;padding:0 6px;cursor:pointer}
.wb-topnav #langSwitch:hover{background:rgba(255,255,255,.16);color:#fff}
.wb-topnav #langSwitch option{color:#111}
"""


def topnav(root="../", active=None):
    """返回统一导航条的 HTML 片段（含响应式导航库 + 访问统计脚本）。

    菜单包进 `.nav-collapse`，由本地 vendored 的 responsive-nav.js 在窄屏
    折叠为汉堡菜单、宽屏保持横向排列，从而解决移动端导航栏「显示不全」。
    库 CSS/JS 经 `root` 拼接路径，离线 / 国内访问均可用。
    """
    parts = ["<nav class='wb-topnav'>", "<span class='brand'>Apple 供应链</span>"]
    # 菜单区：响应式框架管理，窄屏折叠为汉堡
    parts.append("<nav class='nav-collapse'><ul>")
    for key, label, path in NAV_ITEMS:
        cls = " class='active'" if key == active else ""
        parts.append("<li><a href='%s'%s data-i18n='nav.%s'>%s</a></li>" % (root + path, cls, key, label))
    parts.append("</ul></nav>")
    # 语言切换下拉（始终可见，移动端也不折叠进汉堡）
    parts.append("<select id='langSwitch' aria-label='Language' "
                  "onchange='window.i18n&&window.i18n.changeLanguage(this.value)'>"
                  "<option value='zh'>中文</option><option value='en'>English</option>"
                  "<option value='fr'>Français</option><option value='ja'>日本語</option></select>")
    parts.append("<span class='spacer'></span>")
    parts.append(GITHUB_LINK % GITHUB_URL)
    parts.append("</nav>")
    # 响应式导航库（本地 vendored，离线可用；库会自动在 .nav-collapse 前生成汉堡 toggle）
    parts.append("<link rel='stylesheet' href='%sdist/vendor/responsive-nav.css'>" % root)
    parts.append("<script src='%sdist/vendor/responsive-nav.min.js'></script>" % root)
    parts.append("<script>responsiveNav('.nav-collapse', { transition: true, label: '☰' });</script>")
    # 国际化框架（i18next + http-backend，本地 vendored；i18n.js 自初始化并按页面深度加载 locales/）
    parts.append("<script src='%sdist/vendor/i18next.min.js'></script>" % root)
    parts.append("<script src='%sdist/vendor/i18nextHttpBackend.min.js'></script>" % root)
    parts.append("<script src='%sdist/i18n.js'></script>" % root)
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

