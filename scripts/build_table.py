#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成供应链企业列表页（dist/supplier_table.html）。

把图谱中所有企业（供应商节点，共 60 家）以表格形式呈现：
  - 按地区 / 国家 / 类别 / 层级 下拉筛选 + 关键字搜索；
  - 点击任意列标题升/降序排序；
  - 每行提供「图谱 / 地图」链接，可回到图谱定位或地图打点（双向导航）。

前端模版为 templates/table_page.html（表格逻辑内联在模版中，本脚本不硬编码前端）。
页面位于 dist/，root="../"，与报告页同级。
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)               # repo root (this script lives in <repo>/scripts/)
TEMPLATES = os.path.join(ROOT, "templates")
sys.path.insert(0, ROOT)
from topnav import topnav, TOPNAV_CSS

DATA = json.load(open(os.path.join(ROOT, "data", "apple_supply_chain.json"), encoding="utf-8"))
SUPPLIERS = DATA["nodes"]["suppliers"]


def load(name):
    with open(os.path.join(TEMPLATES, name), encoding="utf-8") as f:
        return f.read()


def main():
    # 注入前转义 </，避免数据意外闭合 <script>（数据受控，仅为稳妥）
    payload = json.dumps(SUPPLIERS, ensure_ascii=False).replace("</", "<\\/")
    page = (load("table_page.html")
            .replace("__DATA__", payload)
            .replace("__TOPNAV_CSS__", TOPNAV_CSS)
            .replace("__TOPNAV__", topnav("../", "table")))     # 页面在 dist/，root="../"

    dst = os.path.join(ROOT, "dist", "supplier_table.html")
    with open(dst, "w", encoding="utf-8") as f:
        f.write(page)

    print("written:", dst, "bytes:", len(page), "suppliers:", len(SUPPLIERS))


if __name__ == "__main__":
    main()
