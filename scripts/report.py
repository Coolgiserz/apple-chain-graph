# -*- coding: utf-8 -*-
"""Build the HTML report (v2) from the generated JSON graph.

Refactored for reusability: report content is assembled from small builders
(product_table / component_table / supplier_table / concentration / summary_section
/ model_section / risk_section / limits_section / docs_section / ...) that all accept
a `jump` flag. With jump=True entity names become clickable spans that deep-link into
the standalone graph / map pages. Technical-tutorial material (Neo4j import guide,
field dictionary) lives in docs/ rather than the web report — docs_section() points there.

国际化：所有面向用户的静态文案均通过 i18n() 包裹为 <span data-i18n="report.*">，
运行时由 dist/i18n.js（window.I18n）替换为对应语言；zh.json 作为中文默认值兜底。
"""
import json, os, sys, datetime
from collections import defaultdict, Counter

# Repo root: this script lives in <repo>/scripts/, so two dirname levels up.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 共享的统一顶部导航（让四个独立页面互相可跳转）
sys.path.insert(0, ROOT)
from topnav import topnav, TOPNAV_CSS

def load_graph():
    with open(os.path.join(ROOT, "data", "apple_supply_chain.json"), encoding="utf-8") as f:
        return json.load(f)

def esc(x):
    return (str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))

# 中文源（兜底默认值），供未加载 JS 时也有可读内容
try:
    ZH = json.load(open(os.path.join(ROOT, "locales", "zh.json"), encoding="utf-8"))
except Exception:
    ZH = {}

def i18n(key, default=None):
    """返回带 data-i18n 标记的 HTML 片段（普通 str）；运行时由 i18n.js 替换为对应语言。
    默认值取 zh.json 中的中文，确保脚本未执行时页面仍有可读文本。"""
    txt = default if default is not None else ZH.get(key, key)
    return "<span data-i18n=\"%s\">%s</span>" % (key, esc(txt))

def i18na(key, href, target="_blank", rel="noopener"):
    """带 data-i18n 的链接（<a> 自带 data-i18n，i18n.js 只改其 textContent，保留 href）。"""
    txt = ZH.get(key, key)
    return "<a class='lk' href='%s' target='%s' rel='%s' data-i18n='%s'>%s</a>" \
           % (esc(href), target, rel, key, esc(txt))

# 数据枚举值的 i18n 映射（raw -> 键后缀），单一来源：locales/enum_map.json。
# 注意：这里只映射「标识符」，真实译文在 locales/*.json 里，由 i18n 运行时解析——
# 不在任何语言里硬编码译文（满足「通过 i18N 自动翻译，不是硬编码翻译」）。
try:
    ENUM_MAP = json.load(open(os.path.join(ROOT, "locales", "enum_map.json"), encoding="utf-8"))
except Exception:
    ENUM_MAP = {}

def tval(domain, raw):
    """把数据集里的枚举值经 i18n 翻译：raw -> <domain>.<key> -> 对应语言文本。
    未登记的值（专有名词等）原样转义返回。"""
    if raw is None or raw == "":
        return ""
    key = ENUM_MAP.get(domain, {}).get(str(raw))
    if not key:
        return esc(raw)
    return i18n("%s.%s" % (domain, key), default=raw)


class Safe:
    """Wrap a string that is already valid/safe HTML; table() will NOT re-escape it.

    用于单元格里本来就是 HTML 的内容（如 link() 产出的 <a>/<span>、别名占位 <span>、供应商名拼接 HTML）。
    普通数据值仍由 table() 统一 esc，避免 XSS / 标签被当文本显示。
    """
    __slots__ = ("s",)
    def __init__(self, s): self.s = str(s)
    def __str__(self): return self.s

def link(name, key, jump, mode="spa"):
    """Wrap an entity name in a cross-link.

    mode='spa' -> <span data-jump="graph:KEY">（供整合版 SPA 内部跳转）
    mode='web' -> <a href> 跳转到独立的图谱/地图页面（供多页模式互相跳转）
    返回 Safe，避免 table() 把标签当文本转义。
    """
    name = esc(name)
    if not jump or not key:
        return name
    if mode == "web":
        kind, sid = key.split(":", 1)
        g = "../index.html?focus=%s" % esc(key)
        out = "<a class='lk' href='%s' title='在图谱中查看'>%s</a>" % (g, name)
        if kind == "S":
            m = "../tools/visualizations/supplier_geo.html?supplier=%s" % esc(sid)
            out += " <a class='lk' href='%s' title='在地图中查看'>🗺</a>" % m
        return Safe(out)
    return Safe('<span class="lk" data-jump="graph:%s" title="在图谱中查看">%s</span>' % (esc(key), name))


CSS = """
*{box-sizing:border-box}
/* 浅色主题令牌声明在 body、而不是全局根作用域（:root）——这是被真实事故逼出来的：
   共享导航 topnav.py 的 TOPNAV_CSS 在全局根作用域定义了一整套**暗色**令牌
   （--ink:#e8ecf4 / --bg:#0c1020 / --card:#131a2e …），而本页 CSS 先于它拼接，
   同名变量由后定义的暗色值胜出。后果是：body{color:var(--ink)} 拿到亮色文字，
   而斑马纹 tr:nth-child(even) td{background:#fafcff} 是硬编码白色 ——
   亮字压白底、对比度仅 1.15:1（WCAG 正文要求 4.5:1），表格「根本看不清楚有什么字」。
   收敛到 body 后同一处对比度回到 15.2:1。

   CSS 自定义属性就近继承：body 上定义的值优先于从根作用域继承来的值，所以声明在
   body 即可免疫后续的全局覆盖，且**不依赖拼接顺序**（比把整段 CSS 挪到 TOPNAV_CSS
   之后更稳 —— 挪顺序只要有人调整拼接就再次失效）。

   ⚠ 别把这些令牌挪回根作用域：tests/test_report_theme.py 的 RT1 守着这一点。
   ⚠ 也别顺手改 topnav.py：它的令牌块是 test_ui_color_tokens.py CT1/CT2 认定的
     全站共享契约（与 index / table_page / dashboard 模板 / geo_build 逐字比对），
     除本页外其余 4 页都是暗色主题，为唯一浅色页去动共享契约收益小、回归面大。 */
body{--bg:#f5f7fa;--card:#fff;--ink:#1c2430;--muted:#5b6b7d;--line:#e3e8ef;
  --blue:#0a66c2;--blue2:#e8f1fb;--green:#0e7c4f;--amber:#b06a00;--red:#b3261e;
  margin:0;font-family:-apple-system,'Segoe UI',Roboto,'PingFang SC','Microsoft YaHei',sans-serif;
  background:var(--bg);color:var(--ink);line-height:1.6;font-size:15px}
header{background:linear-gradient(135deg,#0a2540,#0a66c2);color:#fff;padding:42px 28px}
header h1{margin:0 0 6px;font-size:28px;letter-spacing:.5px}
header p{margin:4px 0;opacity:.92}
.wrap{max-width:1180px;margin:0 auto;padding:24px 20px 60px}
section{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:22px 24px;margin:18px 0;
  box-shadow:0 1px 3px rgba(20,40,80,.05)}
h2{margin:0 0 12px;font-size:20px;border-left:4px solid var(--blue);padding-left:10px}
h3{font-size:16px;color:var(--blue);margin:18px 0 8px}
p{margin:8px 0}
table{border-collapse:collapse;width:100%;font-size:13px;margin:10px 0}
th,td{border:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}
th{background:var(--blue2);color:var(--blue);font-weight:600}
tr:nth-child(even) td{background:#fafcff}
.tag{display:inline-block;background:var(--blue2);color:var(--blue);border-radius:99px;padding:1px 9px;font-size:12px;margin:2px 3px 2px 0}
.kpi{display:flex;flex-wrap:wrap;gap:14px;margin:6px 0 4px}
.kpi div{flex:1;min-width:140px;background:var(--blue2);border-radius:10px;padding:14px;text-align:center}
.kpi b{display:block;font-size:26px;color:var(--blue)}
.kpi span{font-size:12.5px;color:var(--muted)}
.bar{height:14px;border-radius:7px;background:var(--blue);display:inline-block;vertical-align:middle}
.note{background:#fff8ec;border:1px solid #f3e0b3;border-radius:8px;padding:10px 14px;font-size:13.5px;color:#6b5418}
.risk{background:#fdecea;border:1px solid #f3c0bb;border-radius:8px;padding:10px 14px;margin:8px 0;font-size:14px}
code{background:#eef2f7;padding:1px 6px;border-radius:5px;font-size:13px}
footer{text-align:center;color:var(--muted);font-size:12.5px;padding:20px}
.scroll{max-height:520px;overflow:auto;border:1px solid var(--line);border-radius:8px}
.lk{cursor:pointer;border-bottom:1px dashed var(--blue)}
.lk:hover{color:var(--blue);background:var(--blue2);border-radius:3px}
"""


def table(headers, rows, cls=""):
    hparts = []
    for x in headers:
        # 表头若是 i18n() 片段（含 data-i18n）或 Safe（link 等已转义内容），保留原样；否则转义
        if isinstance(x, Safe):
            hparts.append("<th>%s</th>" % x.s)
        elif isinstance(x, str) and "data-i18n" in x:
            hparts.append("<th>%s</th>" % x)
        else:
            hparts.append("<th>%s</th>" % esc(x))
    h = "".join(hparts)
    body = ""
    for r in rows:
        cells = []
        for x in r:
            if isinstance(x, Safe):
                cells.append("<td>%s</td>" % x.s)
            elif isinstance(x, str) and "data-i18n" in x:
                cells.append("<td>%s</td>" % x)  # i18n() 片段（含 data-i18n）保留原样，交由前端翻译
            else:
                cells.append("<td>%s</td>" % esc(x))
        body += "<tr>" + "".join(cells) + "</tr>"
    return '<div class="scroll"><table class="%s"><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>' % (cls, h, body)


# --------------------------------------------------------------------------
# Data-derived helpers (reach = how many product models a supplier touches)
# --------------------------------------------------------------------------
def _indexes(G):
    comp_by_id = {c["id"]: c for c in G["nodes"]["components"]}
    sup_by_id = {s["id"]: s for s in G["nodes"]["suppliers"]}
    prod_assembly = defaultdict(list)
    for e in G["edges"]["assembled_by"]:
        prod_assembly[e["from"]].append(e["to"])
    comp_sups = defaultdict(list)
    for e in G["edges"]["supplied_by"]:
        comp_sups[e["from"]].append(e["to"])
    sup_products = defaultdict(set)
    for e in G["edges"]["assembled_by"]:
        sup_products[e["to"]].add(e["from"])
    for e in G["edges"]["uses_component"]:
        for s in comp_sups[e["to"]]:
            sup_products[s].add(e["from"])
    return comp_by_id, sup_by_id, prod_assembly, comp_sups, sup_products


# --------------------------------------------------------------------------
# Builders (each returns an HTML fragment; all accept a `jump` flag)
# --------------------------------------------------------------------------
def report_kpi(G):
    products = G["nodes"]["products"]; components = G["nodes"]["components"]; suppliers = G["nodes"]["suppliers"]
    uses = G["edges"]["uses_component"]; supplied_by = G["edges"]["supplied_by"]; assembled_by = G["edges"]["assembled_by"]
    return ("<div class='kpi'>"
            "<div><b>%d</b><span>%s</span></div>" % (len(products), i18n("report.kpi.products")) +
            "<div><b>%d</b><span>%s</span></div>" % (len(components), i18n("report.kpi.components")) +
            "<div><b>%d</b><span>%s</span></div>" % (len(suppliers), i18n("report.kpi.suppliers")) +
            "<div><b>%d</b><span>%s</span></div>" % (len(uses) + len(supplied_by) + len(assembled_by), i18n("report.kpi.edges")) +
            "</div>")


# 产品状态枚举：数据集里是中文值（在售 / 传闻/未发布），需按语言翻译
def product_table(G, jump=False, mode="spa"):
    _, sup_by_id, prod_assembly, _, _ = _indexes(G)
    rows = []
    for p in sorted(G["nodes"]["products"], key=lambda x: x["release_date"]):
        comps = [c["name"] for c in G["nodes"]["components"] if c["id"] in p["components"]]
        assemblers = [sup_by_id[a]["short_name"] for a in prod_assembly[p["id"]]]
        alias = p["alias"] if p["alias"] else Safe("<span style='color:#9aa7b5'>—</span>")
        rows.append([link(p["name"], "P:" + p["id"], jump, mode), tval("product_line", p["product_line"]), p["english_name"], alias,
                     p["release_date"], tval("status", p["status"]), p["soc"], p["display"],
                     "$%s" % p["price_usd"], str(len(comps)), " / ".join(assemblers)])
    return table([i18n("report.th.fullName"), i18n("home.line"), i18n("report.th.engName"), i18n("report.th.aliasCode"),
                  i18n("field.release_date"), i18n("field.status"), i18n("report.th.soc"), i18n("field.display"),
                  i18n("field.price"), i18n("report.th.compCount"), i18n("report.th.assembler")], rows)


def component_table(G, jump=False, mode="spa"):
    _, sup_by_id, _, comp_sups, _ = _indexes(G)
    rows = []
    for c in G["nodes"]["components"]:
        sups = comp_sups.get(c["id"], [])
        if not sups:
            sups_names = Safe("<span style='color:#b3261e'>— 未列</span>")
        else:
            parts = ["<b>%s</b> <span style='color:#5b6b7d'>(%s)</span>" %
                     (link(sup_by_id[s]["short_name"], "S:" + s, jump, mode), esc(sup_by_id[s]["name"])) for s in sups]
            sups_names = Safe(" / ".join(str(p) for p in parts))
        rows.append([link(c["name"], "C:" + c["id"], jump, mode), c["english_name"], tval("category", c["category"]), tval("subcategory", c["subcategory"]), sups_names, str(len(sups))])
    return table([i18n("report.th.compZh"), i18n("report.th.engName"), i18n("report.th.category"), i18n("field.subcategory"),
                  i18n("report.th.mainSuppliers"), i18n("report.th.supCount")], rows)


def supplier_table(G, jump=False, mode="spa"):
    _, _, _, _, sup_products = _indexes(G)
    rows = []
    for s in sorted(G["nodes"]["suppliers"], key=lambda x: (x["region"], x["short_name"])):
        reach = len(sup_products.get(s["id"], []))
        rows.append([link(s["name"], "S:" + s["id"], jump, mode), s["english_name"],
                     link(s["short_name"], "S:" + s["id"], jump, mode),
                     tval("country", s["country"]), tval("region", s["region"]), tval("category", s["category"]), tval("tier", s["tier"]), str(reach)])
    return table([i18n("report.th.fullName"), i18n("report.th.engName"), i18n("field.short_name"),
                  i18n("table.country"), i18n("field.region"), i18n("table.category"), i18n("table.tier"),
                  i18n("report.th.reach")], rows)


def concentration(G, jump=False, mode="spa"):
    suppliers = G["nodes"]["suppliers"]
    region_counter = Counter(s["region"] for s in suppliers)
    cat_counter = Counter(s["category"] for s in suppliers)
    _, sup_by_id, _, _, sup_products = _indexes(G)
    top_suppliers = sorted(sup_products.items(), key=lambda kv: len(kv[1]), reverse=True)
    maxr = max(region_counter.values())
    region_bars = ""
    for reg, cnt in region_counter.most_common():
        w = int(round(460 * cnt / maxr))
        region_bars += "<div style='margin:6px 0'><span style='display:inline-block;width:120px'>%s</span><span class='bar' style='width:%dpx'></span> <b>%d</b></div>" % (tval("region", reg), w, cnt)
    top_rows = [[link(sup_by_id[sid]["name"], "S:" + sid, jump, mode), sup_by_id[sid]["short_name"],
                 tval("country", sup_by_id[sid]["country"]), tval("category", sup_by_id[sid]["category"]), str(len(plist))]
                for sid, plist in top_suppliers[:18]]
    top_table = table([i18n("report.th.fullName"), i18n("field.short_name"), i18n("table.country"),
                       i18n("table.category"), i18n("report.th.reachModels")], top_rows)
    cat_rows = [[tval("category", k), str(v)] for k, v in cat_counter.most_common()]
    cat_table = table([i18n("report.th.supCategory"), i18n("report.th.count")], cat_rows)
    return ("<h3>%s</h3>" % i18n("report.geo.h31") + region_bars +
            "<h3>%s</h3>" % i18n("report.geo.h32") + cat_table +
            "<h3>%s</h3>" % i18n("report.geo.h33") +
            "<p>%s</p>" % i18n("report.geo.p33") + top_table)


def summary_section(G):
    return "".join([
        "<section id='sec-summary'><h2>", i18n("report.sec.summary"), "</h2>",
        "<p>", i18n("report.summary.p1"), "</p>",
        "<ul>",
        "<li>", i18n("report.summary.b1"), "</li>",
        "<li>", i18n("report.summary.b2"), "</li>",
        "<li>", i18n("report.summary.b3"), "</li>",
        "</ul>",
        "<div class='note'>", i18n("report.summary.note"), "</div>",
        "</section>",
    ])


def model_section(G):
    """数据驱动的四层供应链分层模型：产品 → 零部件 → 供应商 → 生产基地。

    每层显示真实计数与代表性实体；相邻层用实线箭头表示传导关系，
    跨层直达关系（ASSEMBLED_BY 总装 / MANUFACTURED_AT 量产）用虚线弧箭头标识。
    """
    _, _, _, comp_sups, sup_products = _indexes(G)
    n_prod = len(G["nodes"]["products"])
    n_comp = len(G["nodes"]["components"])
    n_sup = len(G["nodes"]["suppliers"])
    n_base = len(G["nodes"]["bases"])

    # 代表性实体（数据驱动挑选）
    prod_ex = sorted(G["nodes"]["products"], key=lambda p: -len(p.get("components", [])))[:4]
    comp_ex = sorted(G["nodes"]["components"], key=lambda c: -len(comp_sups.get(c["id"], [])))[:4]
    sup_ex = sorted(G["nodes"]["suppliers"], key=lambda s: -len(sup_products.get(s["id"], set())))[:4]
    base_cnt = {b["id"]: len(b.get("products", [])) for b in G["nodes"]["bases"]}
    base_ex = sorted(G["nodes"]["bases"], key=lambda b: -base_cnt[b["id"]])[:4]

    def trunc(s, n=12):
        s = str(s)
        return s if len(s) <= n else s[:n] + "…"

    cols = [
        ("L0 产品 Product", n_prod, [p["name"] for p in prod_ex], "#0a66c2", "#e8f1fb"),
        ("L1 零部件 Component", n_comp, [c["name"] for c in comp_ex], "#0e7c4f", "#e7f6ee"),
        ("L2 供应商 Supplier", n_sup, [s.get("short_name") or s["name"] for s in sup_ex], "#b06a00", "#fff3e0"),
        ("L3 生产基地 Base", n_base, [b["name"] for b in base_ex], "#6d28d9", "#f1e9ff"),
    ]
    x0, w, gap = 10, 150, 60
    y, h = 64, 232
    svg = ["<svg viewBox='0 0 800 340' width='100%' style='max-width:800px;margin:10px 0' "
           "font-family='-apple-system,Segoe UI,PingFang SC,Microsoft YaHei,sans-serif'>"]

    for i, (title, cnt, items, color, bg) in enumerate(cols):
        x = x0 + i * (w + gap)
        svg.append("<rect x='%d' y='%d' width='%d' height='%d' rx='12' fill='%s' stroke='%s' stroke-width='1.5'/>"
                   % (x, y, w, h, bg, color))
        # 顶部圆角表头带（顶部圆角、底部直角）
        svg.append("<path d='M%d,%d a12,12 0 0 1 12,-12 h%d a12,12 0 0 1 12,12 v18 h-%d z' fill='%s'/>"
                   % (x, y + 12, w - 24, w, color))
        svg.append("<text x='%d' y='%d' text-anchor='middle' fill='#fff' font-size='11' font-weight='bold'>%s</text>"
                   % (x + w // 2, y + 20, esc(title)))
        svg.append("<text x='%d' y='%d' text-anchor='middle' fill='%s' font-size='19' font-weight='bold'>%d</text>"
                   % (x + w // 2, y + 50, color, cnt))
        cy = y + 70
        for it in items:
            svg.append("<rect x='%d' y='%d' width='%d' height='26' rx='6' fill='#fff' stroke='%s' stroke-width='0.8'/>"
                       % (x + 8, cy, w - 16, color))
            svg.append("<text x='%d' y='%d' text-anchor='middle' font-size='10.5' fill='#1c2430'>%s</text>"
                       % (x + w // 2, cy + 17, esc(trunc(it))))
            cy += 32

    # 箭头标记（按颜色区分）
    svg.append("<defs>"
               "<marker id='arB' markerWidth='9' markerHeight='9' refX='7' refY='3' orient='auto'><path d='M0,0 L7,3 L0,6 Z' fill='#0a66c2'/></marker>"
               "<marker id='arG' markerWidth='9' markerHeight='9' refX='7' refY='3' orient='auto'><path d='M0,0 L7,3 L0,6 Z' fill='#0e7c4f'/></marker>"
               "<marker id='arA' markerWidth='9' markerHeight='9' refX='7' refY='3' orient='auto'><path d='M0,0 L7,3 L0,6 Z' fill='#b06a00'/></marker>"
               "<marker id='arP' markerWidth='9' markerHeight='9' refX='7' refY='3' orient='auto'><path d='M0,0 L7,3 L0,6 Z' fill='#6d28d9'/></marker>"
               "</defs>")

    ym = y + h / 2
    # 相邻层直连箭头
    straight = [
        (x0 + w, x0 + (w + gap), "#0a66c2", "arB", "USES_COMPONENT", 402),
        (x0 + 2 * (w + gap) + w, x0 + 3 * (w + gap), "#0e7c4f", "arG", "SUPPLIED_BY", 80),
        (x0 + 3 * (w + gap) + w, x0 + 4 * (w + gap), "#b06a00", "arA", "OPERATED_BY", 17),
    ]
    for x1, x2, col, mk, label, n in straight:
        svg.append("<line x1='%d' y1='%d' x2='%d' y2='%d' stroke='%s' stroke-width='2' marker-end='url(#%s)'/>"
                   % (x1, ym, x2 - 4, ym, col, mk))
        svg.append("<text x='%d' y='%d' text-anchor='middle' font-size='9.5' fill='%s'>%s · %d</text>"
                   % ((x1 + x2) // 2, ym - 8, col, label, n))

    # 跨层直达（虚线弧）：ASSEMBLED_BY 总装（产品→供应商，上方）
    xr0, xl2, xr3 = x0 + w, x0 + 2 * (w + gap), x0 + 3 * (w + gap) + w
    svg.append("<path d='M%d,%d Q400,32 %d,%d' fill='none' stroke='#b06a00' stroke-width='2' "
               "stroke-dasharray='5 3' marker-end='url(#arA)'/>" % (xr0, ym - 6, xl2 + 4, ym - 6))
    svg.append("<text x='400' y='28' text-anchor='middle' font-size='9.5' fill='#b06a00'>ASSEMBLED_BY（EMS 总装）· 45</text>")
    # 跨层直达（虚线弧）：MANUFACTURED_AT 量产（产品→生产基地，下方）
    svg.append("<path d='M%d,%d Q400,322 %d,%d' fill='none' stroke='#6d28d9' stroke-width='2' "
               "stroke-dasharray='5 3' marker-end='url(#arP)'/>" % (xr0, ym + 6, xr3 - 4, ym + 6))
    svg.append("<text x='400' y='336' text-anchor='middle' font-size='9.5' fill='#6d28d9'>MANUFACTURED_AT（量产基地）· 33</text>")

    svg.append("</svg>")
    svg_html = "".join(svg)

    return "".join([
        "<section id='sec-model'><h2>", i18n("report.sec.model"), "</h2>",
        "<p>", i18n("report.model.intro"), "</p>",
        "<p>", i18n("report.model.flow"), "</p>",
        "<p><code>", i18n("report.model.rel1"), "</code><br>",
        "<code>", i18n("report.model.rel2"), "</code><br>",
        "<code>", i18n("report.model.rel3"), "</code><br>",
        "<code>", i18n("report.model.rel4"), "</code></p>",
        "<p class='muted'>", i18n("report.model.caption"), "</p>",
        "<h3>", i18n("report.model.h3"), "</h3>",
        "<ul>",
        "<li>", i18n("report.model.l0"), "</li>",
        "<li>", i18n("report.model.l1"), "</li>",
        "<li>", i18n("report.model.l2"), "</li>",
        "<li>", i18n("report.model.l3"), "</li>",
        "</ul>", svg_html, "</section>",
    ])


def risk_section():
    return "".join([
        "<section id='sec-risk'><h2>", i18n("report.sec.risk"), "</h2>",
        "<div class='risk'>", i18n("report.risk.r1"), "</div>",
        "<div class='risk'>", i18n("report.risk.r2"), "</div>",
        "<div class='risk'>", i18n("report.risk.r3"), "</div>",
        "<div class='risk'>", i18n("report.risk.r4"), "</div>",
        "<div class='risk'>", i18n("report.risk.r5"), "</div>",
        "<div class='risk'>", i18n("report.risk.r6"), "</div>",
        "<div class='note'>", i18n("report.risk.note"), "</div>",
        "</section>",
    ])


def limits_section():
    return "".join([
        "<section id='sec-limits'><h2>", i18n("report.sec.limits"), "</h2>",
        "<ul>",
        "<li>", i18n("report.limits.l1"), "</li>",
        "<li>", i18n("report.limits.l2"), "</li>",
        "<li>", i18n("report.limits.l3"), "</li>",
        "<li>", i18n("report.limits.l4"), "</li>",
        "<li>", i18n("report.limits.l5"), "</li>",
        "</ul></section>",
    ])


def footer_html(today):
    return "<footer><span data-i18n='report.footer'>%s</span> · 生成日期：%s</footer>" % (
        esc(ZH.get("report.footer", "由 WorkBuddy 生成 · 苹果供应链图谱 v2")), today)


def build_report_inner(G, jump=False, mode="spa", today=""):
    """Assemble the full report body (no <html>/<head> wrapper)."""
    s = []
    s.append("<section>%s</section>" % report_kpi(G))
    s.append(summary_section(G))
    s.append(model_section(G))
    s.append("<section id='sec-products'><h2>%s</h2>" % i18n("report.sec.products"))
    s.append("<p>%s</p>" % i18n("report.intro.products"))
    s.append(product_table(G, jump, mode))
    s.append("</section>")
    s.append("<section id='sec-components'><h2>%s</h2>" % i18n("report.sec.components"))
    s.append(component_table(G, jump, mode))
    s.append("</section>")
    s.append("<section id='sec-suppliers'><h2>%s</h2>" % i18n("report.sec.suppliers"))
    s.append("<p>%s</p>" % i18n("report.intro.suppliers"))
    s.append(supplier_table(G, jump, mode))
    s.append("</section>")
    s.append("<section id='sec-geo'><h2>%s</h2>" % i18n("report.sec.geo"))
    s.append(concentration(G, jump, mode))
    s.append("</section>")
    s.append(risk_section())
    s.append(limits_section())
    s.append(footer_html(today))
    return "".join(s)


def build_report_full(G, jump=False, mode="web", today=None):
    """Standalone full HTML document with the unified cross-page nav bar."""
    if today is None:
        today = datetime.date.today().strftime("%Y-%m-%d")
    nav = topnav("../", "report")
    prefix = ("<!DOCTYPE html><html lang='zh-CN'><head><meta charset='utf-8'>"
              "<meta name='viewport' content='width=device-width,initial-scale=1'>"
              "<title>%s</title>"
              "<style>" % esc(ZH.get("report.header.title", "苹果产品供应链上下游图谱报告")) + CSS + TOPNAV_CSS + " body{padding-top:52px}section{scroll-margin-top:60px}</style></head><body>" + nav +
              "<header><h1>%s</h1>" % i18n("report.header.title") +
              "<p>%s</p>" % i18n("report.header.subtitle") +
              "<p>%s</p>" % i18n("report.header.source") +
              "<p><span>生成日期：<b>%s</b></span> · <span data-i18n='report.header.generated'>%s</span></p>"
              % (today, esc(ZH.get("report.header.generated", "结构化数据（CSV / JSON）已随附"))) +
              "</header>"
              "<div class='wrap'>")
    return prefix + build_report_inner(G, jump, mode, today) + "</div></body></html>"


def main():
    G = load_graph()
    # 多页模式下，报告实体点击 -> 跳转到独立图谱(聚焦节点)/地图(定位供应商)
    today = datetime.date.today().strftime("%Y-%m-%d")
    out = build_report_full(G, jump=True, mode="web", today=today)
    dst = os.path.join(ROOT, "dist", "apple_supply_chain_report.html")
    open(dst, "w", encoding="utf-8").write(out)
    print("Report written:", dst, "bytes:", len(out))


if __name__ == "__main__":
    main()
