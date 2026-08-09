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
import hashlib, json, os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)               # repo root (this script lives in <repo>/scripts/)
TEMPLATES = os.path.join(ROOT, "templates")
sys.path.insert(0, ROOT)
from topnav import topnav, TOPNAV_CSS

DATA = json.load(open(os.path.join(ROOT, "data", "apple_supply_chain.json"), encoding="utf-8"))


def merge_risk(data):
    """把供应链脆弱性分析结果合并进图节点（组件 / 产品），供图谱「风险视图」使用。

    风险数据来源 tools/output/supply_chain_risk.json（run_risk 产出，与图谱同源单一来源）。
    组件节点加 vuln / n_suppliers / single_point；产品节点加 vuln / sp_count / weakest / weakest_component。
    文件缺失或解析失败时原样返回（不报错、不白屏），图谱仅缺风险着色。
    """
    rp = os.path.join(ROOT, "tools", "output", "supply_chain_risk.json")
    if not os.path.exists(rp):
        return data
    try:
        risk = json.load(open(rp, encoding="utf-8"))
    except Exception as e:
        print("WARN: 读取供应链风险数据失败，跳过风险注入：", e)
        return data
    comp = {c["component_id"]: c for c in risk.get("components", [])}
    prod = {p["product_id"]: p for p in risk.get("products", [])}
    for c in data["nodes"]["components"]:
        r = comp.get(c["id"])
        if r:
            c["vuln"] = r["vuln"]
            c["n_suppliers"] = r["n_suppliers"]
            c["single_point"] = r["single_point"]
    for p in data["nodes"]["products"]:
        r = prod.get(p["id"])
        if r:
            p["vuln"] = r["product_vuln"]
            p["sp_count"] = r["sp_count"]
            p["weakest"] = r["weakest"]
            p["weakest_component"] = r["weakest_component"]
    return data


def load(name):
    with open(os.path.join(TEMPLATES, name), encoding="utf-8") as f:
        return f.read()


def asset_url(relpath):
    """相对仓库根的路径，返回带内容哈希 ?v= 戳的 URL。

    浏览器会按完整 URL 做缓存——脚本改动后只要内容哈希变化，URL 即变化，
    强制拉取新文件。这正是「勾选风险视图无反应」的根因：旧 dist/graph_engine.js
    不含 setRiskMode，被浏览器缓存后切换时抛异常并静默失败。先复制 dist 再算
    哈希，保证 ?v= 反映最新内容。
    """
    abspath = os.path.join(ROOT, relpath)
    if os.path.exists(abspath):
        with open(abspath, "rb") as f:
            h = hashlib.sha1(f.read()).hexdigest()[:10]
        return relpath + "?v=" + h
    return relpath


def main():
    DATA_merged = merge_risk(DATA)

    # 先复制共享引擎与启动脚本到 dist/（与整合 SPA 共用、一并发布）——
    # 必须在算哈希之前，否则 ?v= 戳会是上一版内容、与即将写入的新文件不匹配。
    for fname in ("graph_engine.js", "graph_bootstrap.js", "graph_table_panel.js", "i18n.js"):
        shutil.copyfile(os.path.join(TEMPLATES, fname), os.path.join(ROOT, "dist", fname))

    # 把 locales/*.json 内联成一个 vendored JS 全局（dist/locales.js），
    # 由 i18n.js 直接读取——不再依赖运行时 fetch/XHR。
    # 这样无论部署到 GitHub Pages（dist/ 之外的根目录资源可能没发布）、
    # 还是本地用 file:// 直接打开，翻译都能加载，彻底规避「语言包 404 / 切换无效」。
    try:
        bundles = {}
        for lng in ("zh", "en", "fr", "ja"):
            lp = os.path.join(ROOT, "locales", lng + ".json")
            if os.path.exists(lp):
                with open(lp, encoding="utf-8") as lf:
                    bundles[lng] = json.load(lf)
        with open(os.path.join(ROOT, "dist", "locales.js"), "w", encoding="utf-8") as bf:
            bf.write("/* 自动生成：locales/*.json 内联为全局，供 i18n.js 使用。勿手改，改 locales/*.json 后重跑 build_all.py */\n")
            bf.write("window.I18N_LOCALES = " + json.dumps(bundles, ensure_ascii=False) + ";\n")
            # 数据枚举值的 raw->键 映射（locales/enum_map.json），graph_engine.js 运行时用来把
            # 数据集里的枚举值转成 i18n 键（译文仍在 locales/*.json，不在 JS 里硬编码）。
            enum_map_path = os.path.join(ROOT, "locales", "enum_map.json")
            if os.path.exists(enum_map_path):
                with open(enum_map_path, encoding="utf-8") as emf:
                    enum_map = json.load(emf)
                bf.write("window.I18N_ENUM_MAP = " + json.dumps(enum_map, ensure_ascii=False) + ";\n")
        print("generated:", "dist/locales.js", "packs:", list(bundles.keys()))
    except Exception as e:
        print("WARN: 生成 dist/locales.js 失败：", e)

    # 脚本 URL 带内容哈希戳，避免浏览器加载缓存的旧引擎（缺 setRiskMode 时静默失败）
    page = (load("graph_page.html")
            .replace("__DATA__", json.dumps(DATA_merged, ensure_ascii=False))
            .replace("__TOPNAV_CSS__", TOPNAV_CSS)
            .replace("__TOPNAV__", topnav("", "graph"))        # 首页在根目录，root=""
            .replace("__ENGINE_SRC__", asset_url("dist/graph_engine.js"))
            .replace("__BOOTSTRAP_SRC__", asset_url("dist/graph_bootstrap.js"))
            .replace("__TABLE_PANEL_SRC__", asset_url("dist/graph_table_panel.js")))

    dst = os.path.join(ROOT, "index.html")
    with open(dst, "w", encoding="utf-8") as f:
        f.write(page)

    print("written:", dst, "bytes:", len(page))
    print("copied :", "dist/graph_engine.js, dist/graph_bootstrap.js, dist/graph_table_panel.js, dist/i18n.js")


if __name__ == "__main__":
    main()
