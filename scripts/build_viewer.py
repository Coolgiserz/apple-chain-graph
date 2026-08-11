#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""部署前的「前端装配 + SEO 基础设施」步骤（Plan C 之后不再生成 index.html）。

背景（重要）：首页 index.html 自 Plan C 起成为「静态可部署页面」——即仓库根的
templates/graph_page.html 解析占位符后的产物，提交进版本库、由 GitHub Pages 直接托管，
不再在构建期重生成。这样消除了「index.html 双份事实来源 → 模板/数据漂移」「改一行 CSS
就要整体重建」「PR 里混入整页差异」三类问题。

本脚本现在只负责三件与「图数据/风险」无关、且不适合写进静态页面的事：
  1) 把 templates/ 下仍以内联方式维护、随页面特有的胶水脚本复制到 dist/
     （graph_bootstrap.js、graph_table_panel.js）—— 它们与整合 SPA 共用、一并发布；
  2) 把 run_risk 产出的 tools/output/supply_chain_risk.json 复制为仓库根
     data/supply_chain_risk.json，供首页在浏览器端 fetch 后合并进节点（风险视图）。
     该文件由构建产生、非源码，已加入 .gitignore；缺失时首页降级（仅缺风险着色）；
  3) 生成 SEO 基础设施：sitemap.xml / robots.txt / assets/og-cover.png（均落在仓库根，
     GitHub Pages 发布根）。这些是静态资源，可安全重生成。

前端脚本本体由 esbuild 打包（src/ -> dist/graph_engine.js 等），这一步在 build_all.py
的 run_node_build() 中、在跑本脚本之前完成；本脚本仅做存在性校验，缺失即大声失败。
"""
import hashlib, html, json, os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)               # repo root (this script lives in <repo>/scripts/)
TEMPLATES = os.path.join(ROOT, "templates")
sys.path.insert(0, ROOT)

SEO_BASE = "https://coolgiserz.github.io/apple-chain-graph/"

LINE_ZH = {"iPhone": "iPhone", "Mac": "Mac", "iPad": "iPad", "Wearable": "Apple Watch",
           "Spatial": "Vision Pro", "Audio": "AirPods"}


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
    with open(os.path.join(ROOT, "data", "apple_supply_chain.json"), encoding="utf-8") as f:
        data = json.load(f)
    sup = {s["id"]: (s.get("english_name") or s.get("name") or s["id"]) for s in data["nodes"].get("suppliers", [])}
    c2s = {}
    for e in data["edges"].get("supplied_by", []):
        c2s.setdefault(e["from"], []).append(sup.get(e["to"], e["to"]))
    return sup, c2s


def seo_scope():
    with open(os.path.join(ROOT, "data", "apple_supply_chain.json"), encoding="utf-8") as f:
        data = json.load(f)
    n_prod = len(data["nodes"].get("products", []))
    n_comp = len(data["nodes"].get("components", []))
    n_supp = len(data["nodes"].get("suppliers", []))
    n_edge = sum(len(v) for v in data["edges"].values())
    lines = []
    for p in data["nodes"].get("products", []):
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
    """给爬虫的可索引文本块（clip 隐藏但在 DOM 中，忠实反映图谱内容，非欺骗性隐藏）。

    注意：Plan C 后这段 HTML 已被内联进仓库根的静态 index.html，此处函数仅保留供
    单测（XSS 转义不变量）与本地预览；线上内容以 index.html 内联版本为准。
    """
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
    """<head> 中的 description / canonical / OG / Twitter / hreflang（默认中文；多语言经 hreflang 指向 ?lang=）。

    注意：Plan C 后这段 meta 已被内联进仓库根的静态 index.html；此处仅保留供单测/本地预览。
    """
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


def copy_glue_scripts():
    """把 templates/ 下仍以内联方式维护的胶水脚本复制到 dist/（与整合 SPA 共用、一并发布）。

    必须在算哈希/发布前完成；graph_bootstrap.js 现在由浏览器端 fetch 数据，是首页的启动入口。
    """
    for fname in ("graph_bootstrap.js", "graph_table_panel.js"):
        src = os.path.join(TEMPLATES, fname)
        dst = os.path.join(ROOT, "dist", fname)
        if not os.path.exists(src):
            print("✗ 缺少 templates/%s" % fname, file=sys.stderr)
            sys.exit(1)
        shutil.copyfile(src, dst)
        print("copied : dist/%s  (来自 templates/)" % fname)


def copy_risk_data():
    """把 run_risk 产出的风险 JSON 复制为 data/supply_chain_risk.json。

    首页 bootstrap 在浏览器端 fetch 该文件并合并进节点（风险视图）。该文件由构建产生、
    非源码（已加入 .gitignore）；缺失时首页降级（仅缺风险着色），不阻断发布。
    """
    rp = os.path.join(ROOT, "tools", "output", "supply_chain_risk.json")
    dst = os.path.join(ROOT, "data", "supply_chain_risk.json")
    if not os.path.exists(rp):
        print("WARN: 缺少 tools/output/supply_chain_risk.json（run_risk 未运行），"
              "首页将降级为无风险着色；可运行 `python build_all.py` 后再部署。")
        return
    shutil.copyfile(rp, dst)
    print("copied : data/supply_chain_risk.json  (来自 tools/output/supply_chain_risk.json)")


def require_built_assets():
    """校验 esbuild 产物存在，避免带着未更新的旧引擎静默发布（缺失即大声失败）。"""
    for built in ("graph_engine.js", "i18n.js", "data_layer.js", "locales.js"):
        if not os.path.exists(os.path.join(ROOT, "dist", built)):
            print("✗ 缺少前端构建产物 dist/%s，请先运行 `npm run build`（或 `python build_all.py`）。"
                  % built, file=sys.stderr)
            sys.exit(1)


def main():
    # dist/graph_engine.js 等已由 build_all.py 的 run_node_build()（esbuild 打包 src/）
    # 在跑本脚本之前生成。此处校验它们存在，避免带着未更新的旧引擎静默发布。
    require_built_assets()
    copy_glue_scripts()
    copy_risk_data()

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

    print("done   : 首页 index.html 为静态页面（Plan C），本步骤仅装配 dist 胶水脚本 + 风险数据副本 + SEO 基础设施。")


if __name__ == "__main__":
    main()
