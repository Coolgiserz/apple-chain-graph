#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成首页供应链图谱（仓库根目录 index.html）。

前端已抽离到 templates/ 单独维护：
  - templates/graph_engine.js   共享力导向引擎（首页与整合 SPA 共用，单一事实来源）
  - templates/graph_page.html   首页 HTML 模版（CSS 内联，仅留数据/导航/资源占位符）
  - templates/graph_bootstrap.js 首页启动脚本（注入跨页链接、启动、?focus= 深链）

本脚本只负责：读 JSON -> 填模版 -> 输出根 index.html + 复制引擎/启动脚本到 dist/。
首页即图谱，导航由 topnav.py 统一生成在页面顶部；不再单独生成 dist/graph_viewer.html。
"""
import json, os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)               # repo root (this script lives in <repo>/scripts/)
TEMPLATES = os.path.join(ROOT, "templates")
sys.path.insert(0, ROOT)
from topnav import topnav, TOPNAV_CSS

DATA = json.load(open(os.path.join(ROOT, "data", "apple_supply_chain.json"), encoding="utf-8"))


def load(name):
    with open(os.path.join(TEMPLATES, name), encoding="utf-8") as f:
        return f.read()


def main():
    page = (load("graph_page.html")
            .replace("__DATA__", json.dumps(DATA, ensure_ascii=False))
            .replace("__TOPNAV_CSS__", TOPNAV_CSS)
            .replace("__TOPNAV__", topnav("", "graph"))        # 首页在根目录，root=""
            .replace("__ENGINE_SRC__", "dist/graph_engine.js")
            .replace("__BOOTSTRAP_SRC__", "dist/graph_bootstrap.js")
            .replace("__TABLE_PANEL_SRC__", "dist/graph_table_panel.js"))

    dst = os.path.join(ROOT, "index.html")
    with open(dst, "w", encoding="utf-8") as f:
        f.write(page)

    # 共享引擎与启动脚本复制到 dist/（与整合 SPA 共用、一并发布）
    for fname in ("graph_engine.js", "graph_bootstrap.js", "graph_table_panel.js"):
        shutil.copyfile(os.path.join(TEMPLATES, fname), os.path.join(ROOT, "dist", fname))

    print("written:", dst, "bytes:", len(page))
    print("copied :", "dist/graph_engine.js, dist/graph_bootstrap.js, dist/graph_table_panel.js")


if __name__ == "__main__":
    main()
