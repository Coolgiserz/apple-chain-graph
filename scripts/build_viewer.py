#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成首页供应链图谱（仓库根目录 index.html）。

前端脚本分两类来源：
  - 由 esbuild 打包（单一事实来源，src/ 下 ES Module）：
      src/engine/index.js -> dist/graph_engine.js   共享力导向引擎（首页与整合 SPA 共用）
      src/i18n.js          -> dist/i18n.js           站点国际化引导层
    这一步由 build_all.py 的 run_node_build() 在跑本脚本之前完成（npm ci + npm run build）。
  - 仍由 templates/ 内联维护（非 ESM、随页面特有的胶水代码）：
      templates/graph_page.html    首页 HTML 模版（CSS 内联，仅留数据/导航/资源占位符）
      templates/graph_bootstrap.js 首页启动脚本（注入跨页链接、启动、?focus= 深链）
      templates/graph_table_panel.js 企业表格侧栏面板

本脚本只负责：读 JSON -> 填模版 -> 输出根 index.html；并把 templates/ 下的胶水脚本复制到 dist/。
首页即图谱，导航由 topnav.py 统一生成在页面顶部；不再单独生成 dist/graph_viewer.html。
"""
import hashlib, html, json, os, shutil, sys

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
            # 风险因子分解表所需的自变量：部件总数、平均脆弱性、单点率
            p["n_components"] = r["n_components"]
            p["mean_v"] = r["mean_v"]
            p["sp_rate"] = r["sp_rate"]
    return data


def load(name):
    with open(os.path.join(TEMPLATES, name), encoding="utf-8") as f:
        return f.read()


def inline_json(obj):
    """把对象序列化为可安全内联进 <script> 标签的 JSON 字符串。

    数据来自 AI 联网抓取的供应商 / 零部件文本，可能含 "</script>" 片段；
    json.dumps 默认不转义 <，故把 < 替换为 \\u003c（合法 JSON 转义，JS 解析后
    还原为 <），避免脚本注入与页面结构破坏。供测试直接断言此不变量。
    """
    return json.dumps(obj, ensure_ascii=False).replace("<", "\\u003c")


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


# —— SEO（P0）：可索引文本 / 结构化数据 / sitemap / robots，全部由真实图谱数据动态生成 ——
SEO_BASE = "https://coolgiserz.github.io/apple-chain-graph/"

LINE_ZH = {"iPhone": "iPhone", "Mac": "Mac", "iPad": "iPad", "Wearable": "Apple Watch",
           "Spatial": "Vision Pro", "Audio": "AirPods", "HomePod": "HomePod"}


def load_risk():
    """读取风险分析结果（供 SEO 文本/结构化数据使用）；缺失时返回 None 并降级。"""
    rp = os.path.join(ROOT, "tools", "output", "supply_chain_risk.json")
    if not os.path.exists(rp):
        return None
    try:
        return json.load(open(rp, encoding="utf-8"))
    except Exception as e:
        print("WARN: SEO 读取风险数据失败：", e)
        return None


def _index_maps():
    """供应商 id→显示名、组件 id→[供应商显示名]。"""
    sup = {s["id"]: (s.get("english_name") or s.get("name") or s["id"]) for s in DATA["nodes"].get("suppliers", [])}
    c2s = {}
    for e in DATA["edges"].get("supplied_by", []):
        c2s.setdefault(e["from"], []).append(sup.get(e["to"], e["to"]))
    return sup, c2s


def seo_scope():
    n_prod = len(DATA["nodes"].get("products", []))
    n_comp = len(DATA["nodes"].get("components", []))
    n_supp = len(DATA["nodes"].get("suppliers", []))
    n_edge = sum(len(v) for v in DATA["edges"].values())
    lines = []
    for p in DATA["nodes"].get("products", []):
        pl = p.get("product_line", "")
        if pl and pl not in lines:
            lines.append(pl)
    lines_zh = "、".join(LINE_ZH.get(l, l) for l in lines)
    return n_prod, n_comp, n_supp, n_edge, lines_zh


def seo_single_points(risk):
    """[(组件名, 供应商名, vuln), ...] 单点依赖部件（独家供应商），由风险数据动态生成。"""
    if not risk:
        return []
    out = []
    _, c2s = _index_maps()
    for c in risk.get("components", []):
        if c.get("single_point"):
            name = c.get("name") or c["component_id"]
            sp = "、".join(c2s.get(c["component_id"], [])) or "（未知）"
            out.append((name, sp, c.get("vuln")))
    return out


def seo_worst_line(risk):
    if not risk:
        return None
    lines = risk.get("product_lines", [])
    if not lines:
        return None
    best = max(lines, key=lambda r: r.get("mean_product_vuln", 0))
    return best.get("product_line"), best.get("mean_product_vuln")


def seo_description(risk):
    """页面 meta description（中文，默认语言）。"""
    n_prod, n_comp, n_supp, n_edge, lines_zh = seo_scope()
    nlines = len(lines_zh.split("、"))
    return ("苹果产品供应链上下游知识图谱：以「产品→零部件→供应商」三层模型覆盖%d大产品线（%s）、%d款产品、"
            "%d个核心零部件、%d家供应商，量化单点依赖与供应脆弱性并给出最脆弱产品线排名；"
            "数据源自公开供应链报告与苹果供应商名单，以 MIT 许可开源，可作为供应链图分析、脆弱性建模与"
            "图神经网络（GNN）教学的参考性实验数据（尚非成熟基准，使用前请留意数据口径与局限性）。"
            % (nlines, lines_zh, n_prod, n_comp, n_supp))


def seo_text_html(risk):
    """给爬虫的可索引文本块（clip 隐藏但在 DOM 中，忠实反映图谱内容，非欺骗性隐藏）。"""
    n_prod, n_comp, n_supp, n_edge, lines_zh = seo_scope()
    nlines = len(lines_zh.split("、"))
    sps = seo_single_points(risk)
    wl = seo_worst_line(risk)
    h = "<h2>苹果产品供应链上下游知识图谱（Apple Supply Chain Knowledge Graph）</h2>"
    h += "<p>以「产品 → 零部件 → 供应商」三层有向图建模苹果供应链，量化单点依赖与供应脆弱性。</p>"
    h += "<p><b>数据规模：</b>覆盖 %s 大产品线（%s），共 %d 款产品型号、%d 个核心零部件、%d 家供应商与代工厂、%d 条上下游关系边。</p>" % (
        nlines, lines_zh, n_prod, n_comp, n_supp, n_edge)
    h += "<p><b>脆弱性模型：</b>零部件脆弱性 V = 1 / n（n = 供应商数；n=1 即单点依赖，V=1.0）；产品脆弱性 = 0.5×均值 + 0.3×最弱环节 + 0.2×单点率。</p>"
    if sps:
        h += "<p><b>单点依赖部件（独家供应商）：</b></p><ul>"
        for name, sp, vuln in sps[:6]:
            # name / sp 来自数据集（AI 抓取的组件/供应商名），必须 HTML 转义，
            # 否则名称含 < & 等字符会破坏可索引文本甚至形成 HTML 注入。
            h += "<li>%s：由 %s 独家供应（脆弱性 %.2f）。</li>" % (html.escape(name), html.escape(sp), vuln if vuln is not None else 0.0)
        h += "</ul>"
    if wl:
        pl = LINE_ZH.get(wl[0], wl[0])
        h += "<p><b>最脆弱产品线：</b>%s 产品线（脆弱性 %.3f）。</p>" % (pl, wl[1] if wl[1] is not None else 0.0)
    h += "<p><b>数据来源：</b>2024–2026 年公开供应链报告与苹果 2024 年供应商名单（约覆盖 98% 直接支出），以 MIT 许可开源，附 CSV / JSON 结构化数据。完整上下游分析见报告页。</p>"
    h += ("<p><b>研究用途（参考性）：</b>本图谱可作为供应链图分析、供应脆弱性建模与图神经网络（GNN）"
          "教学的<strong>参考性实验数据</strong>，而非经校验的成熟基准——规模有限（约 %d 节点 / %d 边）、"
          "为 AI 联网检索公开资料的二手整合、属单点时点快照，存在口径不一致与模型幻觉风险。"
          "所有 CSV / JSON / 网页均由脚本从单一数据源重生成，便于复现、二次加工与算法探索；"
          "使用前请务必阅读项目文档中的「数据来源与口径」与「分析方法局限性」，并注明数据与局限。</p>"
          % (n_prod + n_comp + n_supp, n_edge))
    return h


def jsonld(risk):
    """schema.org 结构化数据：Organization + WebSite + Dataset + BreadcrumbList。"""
    n_prod, n_comp, n_supp, n_edge, lines_zh = seo_scope()
    desc = ("Apple product supply-chain knowledge graph modelling Product→Component→Supplier relations, "
            "quantifying single-point dependency and supply-chain vulnerability across %d products, %d components and %d suppliers. "
            "Released as a reproducible, illustrative experimental dataset for supply-chain graph analysis, vulnerability modeling "
            "and GNN teaching under the MIT license — an exploratory sample, not a validated benchmark; see the project's "
            "data-source and limitations notes before use."
            % (n_prod, n_comp, n_supp))
    org = {"@context": "https://schema.org", "@type": "Organization", "name": "Apple Chain Graph", "url": SEO_BASE}
    site = {"@context": "https://schema.org", "@type": "WebSite", "name": "Apple Supply Chain Knowledge Graph", "url": SEO_BASE}
    ds = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": "Apple Supply Chain Knowledge Graph",
        "alternateName": "苹果产品供应链上下游图谱",
        "description": desc,
        "url": SEO_BASE,
        "creator": {"@type": "Organization", "name": "Apple Chain Graph"},
        "license": "https://opensource.org/licenses/MIT",
        "isAccessibleForFree": True,
        "keywords": ["Apple supply chain", "supply chain risk", "single-point dependency", "research dataset",
                     "experimental dataset", "supply chain graph analysis", "vulnerability modeling",
                     "graph neural network", "GNN teaching example", "TSMC", "Sony", "BOE", "OLED", "CIS",
                     "knowledge graph", "supplier concentration"],
        "spatialCoverage": {"@type": "Place", "name": "Global (East Asia concentrated)"},
        "variableMeasured": ["component vulnerability", "product vulnerability", "supplier count", "single-point dependency rate"],
        "distribution": {"@type": "DataDownload", "encodingFormat": "application/json",
                         "contentUrl": SEO_BASE + "data/apple_supply_chain.json"},
        "about": {"@type": "Thing", "name": "Apple Inc. supply chain and supplier risk"},
    }
    bc = {"@context": "https://schema.org", "@type": "BreadcrumbList",
          "itemListElement": [
              {"@type": "ListItem", "position": 1, "name": "Home", "item": SEO_BASE},
              {"@type": "ListItem", "position": 2, "name": "Report", "item": SEO_BASE + "dist/apple_supply_chain_report.html"},
          ]}
    return json.dumps([org, site, ds, bc], ensure_ascii=False)


def seo_meta(risk):
    """<head> 中的 description / canonical / OG / Twitter / hreflang（默认中文；多语言经 hreflang 指向 ?lang=）。"""
    desc = seo_description(risk)
    b = SEO_BASE
    tags = [
        '<meta name="description" content="%s">' % desc,
        '<link rel="canonical" href="%s">' % b,
        '<meta property="og:type" content="website">',
        '<meta property="og:title" content="苹果供应链上下游图谱">',
        '<meta property="og:description" content="%s">' % desc,
        '<meta property="og:url" content="%s">' % b,
        '<meta property="og:image" content="%sassets/og-cover.png">' % b,
        '<meta property="og:site_name" content="Apple Chain Graph">',
        '<meta name="twitter:card" content="summary_large_image">',
        '<meta name="twitter:title" content="苹果供应链上下游图谱">',
        '<meta name="twitter:description" content="%s">' % desc,
        '<meta name="twitter:image" content="%sassets/og-cover.png">' % b,
        '<link rel="alternate" hreflang="zh" href="%s?lang=zh">' % b,
        '<link rel="alternate" hreflang="en" href="%s?lang=en">' % b,
        '<link rel="alternate" hreflang="fr" href="%s?lang=fr">' % b,
        '<link rel="alternate" hreflang="ja" href="%s?lang=ja">' % b,
        '<link rel="alternate" hreflang="x-default" href="%s?lang=zh">' % b,
    ]
    return "\n    ".join(tags)


def sitemap_xml():
    b = SEO_BASE
    langs = ["zh", "en", "fr", "ja"]

    def alts(path):
        out = ['    <xhtml:link rel="alternate" hreflang="%s" href="%s%s?lang=%s"/>' % (l, b, path, l) for l in langs]
        out.append('    <xhtml:link rel="alternate" hreflang="x-default" href="%s%s?lang=zh"/>' % (b, path))
        return "\n".join(out)

    urls = [
        ("", "1.0", "weekly"),
        ("dist/apple_supply_chain_report.html", "0.9", "weekly"),
        ("dist/supplier_table.html", "0.6", "monthly"),
        ("tools/visualizations/supplier_geo.html", "0.5", "monthly"),
        ("tools/visualizations/supplier_dashboard.html", "0.5", "monthly"),
    ]
    body = []
    for path, pri, freq in urls:
        has_alt = path in ("", "dist/apple_supply_chain_report.html")
        body.append('  <url>\n    <loc>%s%s</loc>\n%s    <changefreq>%s</changefreq>\n    <priority>%s</priority>\n  </url>'
                    % (b, path, (alts(path) + "\n") if has_alt else "", freq, pri))
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
            '        xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
            + "\n".join(body) + "\n</urlset>\n")


def robots_txt():
    return "User-agent: *\nAllow: /\n\nSitemap: %ssitemap.xml\n" % SEO_BASE


def write_og_cover(path, w=1200, h=630):
    """纯 stdlib 生成纯色品牌封面 PNG（P0 占位；P1 可替换为带文字/图谱缩略的成品）。"""
    try:
        import zlib, struct
        r, g, bl = 17, 24, 58  # 品牌深蓝 #11183a
        raw = b"".join(b"\x00" + bytes((r, g, bl)) * w for _ in range(h))
        comp = zlib.compress(raw, 9)

        def chunk(typ, data):
            return struct.pack(">I", len(data)) + typ + data + struct.pack(">I", zlib.crc32(typ + data) & 0xffffffff)

        png = (b"\x89PNG\r\n\x1a\n"
               + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
               + chunk(b"IDAT", comp)
               + chunk(b"IEND", b""))
        with open(path, "wb") as f:
            f.write(png)
    except Exception as e:
        print("WARN: 生成 OG 封面失败：", e)


def main():
    DATA_merged = merge_risk(DATA)

    # dist/graph_engine.js 与 dist/i18n.js 已由 build_all.py 的 run_node_build()
    # （esbuild 打包 src/）在跑本脚本之前生成。此处校验它们存在，避免带着未更新的
    # 旧引擎 / 缺 i18n 静默发布。这两个文件是「团队就绪」重构后的唯一事实来源。
    for built in ("graph_engine.js", "i18n.js", "data_layer.js"):
        if not os.path.exists(os.path.join(ROOT, "dist", built)):
            print("✗ 缺少前端构建产物 dist/%s，请先运行 `npm run build`（或 `python build_all.py`）。"
                  % built, file=sys.stderr)
            sys.exit(1)

    # 复制 templates/ 下仍以内联方式维护的胶水脚本到 dist/（与整合 SPA 共用、一并发布）——
    # 必须在算哈希之前，否则 ?v= 戳会是上一版内容、与即将写入的新文件不匹配。
    for fname in ("graph_bootstrap.js", "graph_table_panel.js"):
        shutil.copyfile(os.path.join(TEMPLATES, fname), os.path.join(ROOT, "dist", fname))

    # dist/locales.js（i18n 语言包内联产物）由 build_all.py 的 run_node_build() 在跑本脚本
    # 之前通过 `npm run build` → scripts/build_locales.mjs 生成（含构建期 i18n 审计，fail-fast）。
    # 该脚本是语言包生成 + 审计的唯一实现（Node 版），build_viewer.py 不再各自实现一份，
    # 避免「Python/JS 双份实现漂移」再次导致漏翻的 key 以后台标签上线。
    # 此处只做存在性校验——缺失即大声失败，绝不静默用陈旧 bundle 发布。
    if not os.path.exists(os.path.join(ROOT, "dist", "locales.js")):
        print("✗ 缺少 dist/locales.js，请先运行 `npm run build`（或 `python build_all.py`）。"
              "语言包由 scripts/build_locales.mjs 生成并做 i18n 审计。", file=sys.stderr)
        sys.exit(1)

    # 脚本 URL 带内容哈希戳，避免浏览器加载缓存的旧引擎（缺 setRiskMode 时静默失败）
    risk = load_risk()
    # 内联 JSON 防 </script> 逃逸：DATA 含 AI 抓取的供应商/零部件文本，可能含
    # "</script>" 片段；json.dumps 不转义 <，故把 < 替换为 \u003c（合法 JSON 转义，
    # JS 解析后还原为 <），避免脚本注入与页面结构破坏。
    data_json = inline_json(DATA_merged)
    page = (load("graph_page.html")
            .replace("__DATA__", data_json)
            .replace("__TOPNAV_CSS__", TOPNAV_CSS)
            .replace("__TOPNAV__", topnav("", "graph"))        # 首页在根目录，root=""
            .replace("__ENGINE_SRC__", asset_url("dist/graph_engine.js"))
            .replace("__FEED_SRC__", asset_url("dist/data_layer.js"))
            .replace("__BOOTSTRAP_SRC__", asset_url("dist/graph_bootstrap.js"))
            .replace("__TABLE_PANEL_SRC__", asset_url("dist/graph_table_panel.js"))
            .replace("__SEO_META__", seo_meta(risk))
            .replace("__JSONLD__", '<script type="application/ld+json">\n' + jsonld(risk) + "\n</script>")
            .replace("__SEO_TEXT__", '<div class="seo-text">\n' + seo_text_html(risk) + "\n</div>"))

    dst = os.path.join(ROOT, "index.html")
    with open(dst, "w", encoding="utf-8") as f:
        f.write(page)

    # —— SEO 基础设施（P0）：sitemap / robots / OG 封面，均落在仓库根（GitHub Pages 发布根）——
    try:
        with open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8") as sf:
            sf.write(sitemap_xml())
        with open(os.path.join(ROOT, "robots.txt"), "w", encoding="utf-8") as rf:
            rf.write(robots_txt())
        assets_dir = os.path.join(ROOT, "assets")
        os.makedirs(assets_dir, exist_ok=True)
        write_og_cover(os.path.join(assets_dir, "og-cover.png"))
        print("SEO    : sitemap.xml / robots.txt / assets/og-cover.png 已生成")
    except Exception as e:
        print("WARN: 生成 SEO 基础设施失败：", e)

    print("written:", dst, "bytes:", len(page))
    print("copied :", "dist/graph_bootstrap.js, dist/graph_table_panel.js  (graph_engine.js / i18n.js 由 esbuild 生成)")


if __name__ == "__main__":
    main()
