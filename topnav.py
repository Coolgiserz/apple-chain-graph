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
NAV_ITEMS = [
    ("graph",  "🕸️ 供应链图谱", "index.html"),
    ("table",  "📋 企业列表",    "dist/supplier_table.html"),
    ("report", "📄 上下游报告",  "dist/apple_supply_chain_report.html"),
    ("map",    "🗺️ 供应商地图", "tools/visualizations/supplier_geo.html"),
    ("dash",   "📊 估值看板",    "tools/visualizations/supplier_dashboard.html"),
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
"""


def topnav(root="../", active=None):
    """返回统一导航条的 HTML 片段（含可选的访问统计脚本）。"""
    parts = ["<nav class='wb-topnav'>", "<span class='brand'>Apple 供应链</span>"]
    for key, label, path in NAV_ITEMS:
        cls = " class='active'" if key == active else ""
        parts.append("<a href='%s'%s>%s</a>" % (root + path, cls, label))
    parts.append("<span class='spacer'></span>")
    parts.append(GITHUB_LINK % GITHUB_URL)
    parts.append("</nav>")
    parts.append(analytics_js())
    return "".join(parts)


# ---------------------------------------------------------------------------
# 访问统计（隐私友好第三方，可选；默认关闭，配置后启用）
# ---------------------------------------------------------------------------
# 支持 Umami（默认，自托管 / umami.is 云，隐私友好、数据可自持）与 GoatCounter（备用）。
# 启用：填 ANALYTICS_PROVIDER + 对应参数；留空则不加载任何脚本、不发任何外部请求
# （本地 file:// 预览 / 未配置时零副作用）。脚本仅在 http(s) 域名下才发送数据。
#
# Umami 用法：
#   1) 自托管 Umami（Docker）或用 umami.is 云，登录后台 Add Website 得到 Website ID（UUID）
#      与脚本地址（umami.is 云为 https://analytics.umami.is/script.js；自托管换成你的域名，
#      如 https://analytics.你的域名/script.js）。
#   2) 把 ANALYTICS_WEBSITE_ID 改成你的 Website ID（自托管且脚本与 API 不同域时，
#      把 ANALYTICS_UMAMI_SRC 也改成你的地址，必要时在 analytics_js() 里加
#      s.dataset.hostUrl='https://你的实例域名'）。
#   3) 重生成四页。
ANALYTICS_PROVIDER = "umami"             # "umami" 或 "goatcounter"
ANALYTICS_WEBSITE_ID = "126e2a2e-a550-4669-8f17-f31fb60d0861"   # <-- Umami 后台的 Website ID（UUID）
ANALYTICS_UMAMI_SRC = "https://cloud.umami.is/script.js"
# GoatCounter 备用
ANALYTICS_CODE = ""                      # 仅 provider="goatcounter" 时生效


def analytics_js():
    """返回隐私友好统计的注入脚本；未配置时返回空字符串（不加载、不发请求）。"""
    if ANALYTICS_PROVIDER == "umami":
        if not ANALYTICS_WEBSITE_ID:
            return ""
        return ("<script>(function(){"
                "if(location.protocol.indexOf('http')!==0)return;"   # file:// 不计
                "var s=document.createElement('script');s.async=true;"
                "s.src=%r;s.dataset.websiteId=%r;"
                "document.head.appendChild(s);})();</script>"
                % (ANALYTICS_UMAMI_SRC, ANALYTICS_WEBSITE_ID))
    if ANALYTICS_PROVIDER == "goatcounter":
        if not ANALYTICS_CODE:
            return ""
        return ("<script>(function(){"
                "if(location.protocol.indexOf('http')!==0)return;"
                "var s=document.createElement('script');s.async=true;"
                "s.src='https://gc.zgo.at/count.js';"
                "s.dataset.goatcounter='https://%s.goatcounter.com/count';"
                "document.head.appendChild(s);})();</script>" % ANALYTICS_CODE)
    return ""

