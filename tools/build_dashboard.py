# -*- coding: utf-8 -*-
"""生成估值看板页面（tools/visualizations/supplier_dashboard.html）。

与 tools/geo_build.py 一致：从 templates/supplier_dashboard_template.html 读取模板，
用统一的 topnav() 注入顶部导航（含「企业列表」与 GitHub 按钮），避免再手写一份
陈旧、缺项的导航条。看板数据为内嵌快照（const S = [...]，无需运行时 fetch）。
"""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from topnav import topnav, TOPNAV_CSS, analytics_js

TPL = os.path.join(ROOT, "templates", "supplier_dashboard_template.html")
OUT = os.path.join(ROOT, "tools", "visualizations", "supplier_dashboard.html")


def main():
    html = open(TPL, encoding="utf-8").read()
    # topnav() 本身已附带 analytics_js()，故 __ANALYTICS__ 占位用空串移除重复统计脚本
    html = (html
            .replace("__TOPNAV_CSS__", TOPNAV_CSS)
            .replace("__TOPNAV__", topnav("../../", "dash"))
            .replace("__ANALYTICS__", ""))
    open(OUT, "w", encoding="utf-8").write(html)
    print("Dashboard written:", OUT, "bytes:", len(html))


if __name__ == "__main__":
    main()
