# -*- coding: utf-8 -*-
"""Build the integrated Apple Supply-Chain app: graph (图谱) + report (上下游报告).

前端已抽离到 templates/ 单独维护：
  - templates/app_page.html  整合页 HTML 模版（含统一顶部导航 __TOPNAV__ + 二级图谱/报告 tab 条）
  - templates/app.js         视图路由壳（复用共享图谱引擎，注入报告/地图跨页链接）
  - templates/graph_engine.js 共享力导向引擎（与首页图谱共用，单一事实来源）

本脚本只负责：取报告 HTML -> 填模版 -> 输出 dist/apple_supply_chain_app.html，
并复制共享引擎与 app.js 到 dist/。导航由 topnav.py 统一生成。
"""
import json, os, shutil, sys
from report import build_report_inner, CSS as REPORT_CSS

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
    out = (load("app_page.html")
           .replace("__DATA__", json.dumps(DATA, ensure_ascii=False))
           .replace("__TOPNAV_CSS__", TOPNAV_CSS)
           .replace("__TOPNAV__", topnav("../", "app"))     # 整合页在 dist/，root="../"
           .replace("__REPORT__", build_report_inner(DATA, jump=True))
           .replace("__REPORT_CSS__", REPORT_CSS)
           .replace("__ENGINE_SRC__", "graph_engine.js")     # 同目录 dist/
           .replace("__APP_JS__", "app.js"))

    dst = os.path.join(ROOT, "dist", "apple_supply_chain_app.html")
    with open(dst, "w", encoding="utf-8") as f:
        f.write(out)

    # 共享引擎与路由壳复制到 dist/（与首页图谱共用、一并发布）
    for fname in ("graph_engine.js", "app.js"):
        shutil.copyfile(os.path.join(TEMPLATES, fname), os.path.join(ROOT, "dist", fname))

    print("App written:", dst, "bytes:", len(out))
    print("copied     :", "dist/graph_engine.js, dist/app.js")


if __name__ == "__main__":
    main()
