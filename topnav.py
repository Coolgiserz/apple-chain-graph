# -*- coding: utf-8 -*-
"""统一的跨页面顶部导航条（共享组件）。

所有页面（首页图谱 / 报告 / 整合页 / 地图 / 看板 / 融合页）共用同一导航，
互相可点击跳转，不再彼此孤立。首页即供应链图谱（仓库根目录 index.html）。

`root` 是当前页面相对于「仓库根目录」的相对路径：
  - 根目录首页（图谱）：                        root = ""
  - dist 下的页面（报告 / 整合页）：            root = "../"
  - tools/visualizations 下的页面（地图 / 看板 / 融合）：root = "../../"

`active` 为当前页的 key：graph / report / app / map / dash / combined（用于高亮）。
"""
NAV_ITEMS = [
    ("graph",  "🕸️ 供应链图谱", "index.html"),
    ("report", "📄 上下游报告",  "dist/apple_supply_chain_report.html"),
    ("app",    "🧩 整合页",      "dist/apple_supply_chain_app.html"),
    ("map",    "🗺️ 供应商地图", "tools/visualizations/supplier_geo.html"),
    ("dash",   "📊 估值看板",    "tools/visualizations/supplier_dashboard.html"),
    ("combined", "🔗 融合页",    "tools/visualizations/supplier_combined.html"),
]

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
"""


def topnav(root="../", active=None):
    """返回统一导航条的 HTML 片段（含可选的访问统计脚本）。"""
    parts = ["<nav class='wb-topnav'>", "<span class='brand'>Apple 供应链</span>"]
    for key, label, path in NAV_ITEMS:
        cls = " class='active'" if key == active else ""
        parts.append("<a href='%s'%s>%s</a>" % (root + path, cls, label))
    parts.append("<span class='spacer'></span>")
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

