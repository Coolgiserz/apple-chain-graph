# -*- coding: utf-8 -*-
"""Build the HTML report (v2) from the generated JSON graph.

Refactored for reusability: report content is assembled from small builders
(product_table / component_table / supplier_table / concentration / data_dictionary
/ summary_section / model_section / ...) that all accept a `jump` flag. With
jump=True entity names become clickable spans (<span class="lk" data-jump="graph:KEY">)
so the standalone report and the integrated SPA share one source of truth.
"""
import json, os, sys
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
        g = "graph_viewer.html?focus=%s" % esc(key)
        out = "<a class='lk' href='%s' title='在图谱中查看'>%s</a>" % (g, name)
        if kind == "S":
            m = "../tools/visualizations/supplier_geo.html?supplier=%s" % esc(sid)
            out += " <a class='lk' href='%s' title='在地图中查看'>🗺</a>" % m
        return Safe(out)
    return Safe('<span class="lk" data-jump="graph:%s" title="在图谱中查看">%s</span>' % (esc(key), name))


CSS = """
:root{--bg:#f5f7fa;--card:#fff;--ink:#1c2430;--muted:#5b6b7d;--line:#e3e8ef;
  --blue:#0a66c2;--blue2:#e8f1fb;--green:#0e7c4f;--amber:#b06a00;--red:#b3261e;}
*{box-sizing:border-box}
body{margin:0;font-family:-apple-system,'Segoe UI',Roboto,'PingFang SC','Microsoft YaHei',sans-serif;
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
    h = "".join("<th>%s</th>" % esc(x) for x in headers)
    body = ""
    for r in rows:
        cells = ("<td>%s</td>" % (x.s if isinstance(x, Safe) else esc(x)) for x in r)
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
            "<div><b>%d</b><span>产品型号</span></div>" % len(products) +
            "<div><b>%d</b><span>核心零部件</span></div>" % len(components) +
            "<div><b>%d</b><span>供应商/代工厂</span></div>" % len(suppliers) +
            "<div><b>%d</b><span>图谱关系边</span></div>" % (len(uses) + len(supplied_by) + len(assembled_by)) +
            "</div>")


def product_table(G, jump=False, mode="spa"):
    _, sup_by_id, prod_assembly, _, _ = _indexes(G)
    rows = []
    for p in sorted(G["nodes"]["products"], key=lambda x: x["release_date"]):
        comps = [c["name"] for c in G["nodes"]["components"] if c["id"] in p["components"]]
        assemblers = [sup_by_id[a]["short_name"] for a in prod_assembly[p["id"]]]
        alias = p["alias"] if p["alias"] else Safe("<span style='color:#9aa7b5'>—</span>")
        rows.append([link(p["name"], "P:" + p["id"], jump, mode), p["product_line"], p["english_name"], alias,
                     p["release_date"], p["status"], p["soc"], p["display"],
                     "$%s" % p["price_usd"], str(len(comps)), " / ".join(assemblers)])
    return table(["型号全称", "产品线", "英文名", "别名/代号", "发布时间", "状态", "主芯片", "显示", "起售价", "零部件数", "代工厂"], rows)


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
        rows.append([link(c["name"], "C:" + c["id"], jump, mode), c["english_name"], c["category"], c["subcategory"], sups_names, str(len(sups))])
    return table(["零部件(中)", "英文名", "大类", "子类", "主要供应商", "供应商数"], rows)


def supplier_table(G, jump=False, mode="spa"):
    _, _, _, _, sup_products = _indexes(G)
    rows = []
    for s in sorted(G["nodes"]["suppliers"], key=lambda x: (x["region"], x["short_name"])):
        reach = len(sup_products.get(s["id"], []))
        rows.append([link(s["name"], "S:" + s["id"], jump, mode), s["english_name"],
                     link(s["short_name"], "S:" + s["id"], jump, mode),
                     s["country"], s["region"], s["category"], s["tier"], str(reach)])
    return table(["全称", "英文名称", "简称", "国家/地区", "区域", "类别", "层级", "触及产品数"], rows)


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
        region_bars += "<div style='margin:6px 0'><span style='display:inline-block;width:120px'>%s</span><span class='bar' style='width:%dpx'></span> <b>%d</b></div>" % (esc(reg), w, cnt)
    top_rows = [[link(sup_by_id[sid]["name"], "S:" + sid, jump, mode), sup_by_id[sid]["short_name"],
                 sup_by_id[sid]["country"], sup_by_id[sid]["category"], str(len(plist))]
                for sid, plist in top_suppliers[:18]]
    top_table = table(["全称", "简称", "国家/地区", "类别", "触及产品型号数"], top_rows)
    cat_rows = [[k, str(v)] for k, v in cat_counter.most_common()]
    cat_table = table(["供应商类别", "数量"], cat_rows)
    return ("<h3>6.1 区域分布</h3>" + region_bars +
            "<h3>6.2 供应商类别分布</h3>" + cat_table +
            "<h3>6.3 触及产品型号最多的供应商（供应链影响力）</h3>" +
            "<p>下表按「被多少款产品型号直接或间接使用」排序，反映供应商在苹果体系中的嵌入深度。</p>" + top_table)


def data_dictionary(G):
    ddict = G["meta"].get("data_dictionary", {})
    def dd_table(rows):
        return table(["字段", "含义", "可获取性"], [[r["field"], r["desc"], r["obtainable"]] for r in rows])
    html = ""
    for node, fields in ddict.items():
        html += "<h3>%s 节点</h3>" % esc(node)
        html += dd_table(fields)
    return html


def summary_section(G):
    components = G["nodes"]["components"]; suppliers = G["nodes"]["suppliers"]
    return ("<section id='sec-summary'><h2>一、执行摘要</h2>"
            "<p>本报告以<strong>具体产品型号</strong>为起点，逐层向上游拆解出核心零部件（SoC、显示面板、图像传感器、存储、调制解调器、电池、结构件、封装等 %d 类）及其供应商/代工厂（%d 家），构建「产品 → 零部件 → 供应商」三层有向图。数据表明苹果供应链呈现三大特征：</p>" % (len(components), len(suppliers)) +
            "<ul>"
            "<li><b>亚洲中枢、日韩把持技术命脉：</b>超过 80% 的核心供应商在大陆/台湾设厂；日本索尼独占高端 CIS、韩国三星/LG 主导 OLED、台积电(台湾)独家代工最先进制程芯片。</li>"
            "<li><b>多源化策略对冲风险：</b>几乎所有关键零部件都有 ≥2 家供应商（如 DRAM 三家、NAND 五家、OLED 三家），以维持议价权与供应韧性。</li>"
            "<li><b>「中国 + N」产能外移：</b>iPhone 主力组装向印度、AirPods/Watch/Vision Pro 向越南、部分 Mac 向泰/马转移，但核心精密零部件仍高度依赖东亚。</li>"
            "</ul>"
            "<div class='note'><b>本版（v2）属性增强：</b>供应商节点已拆分 <b>全称(name) / 英文名称(english_name) / 简称(short_name)</b> 三个独立字段；产品节点新增 <b>英文名称、别名/代号、发布时间(release_date)、状态(status)、起售价(price_usd)</b> 等属性；组件节点新增英文名称。字段含义与可获取性见第九节「数据字段字典」。</div>"
            "</section>")


def model_section(G):
    svg = '''<svg viewBox='0 0 680 220' width='100%' style='max-width:680px;margin:8px 0'>
 <rect x='12' y='20' width='190' height='150' rx='12' fill='#e8f1fb' stroke='#0a66c2'/>
 <text x='107' y='44' text-anchor='middle' fill='#0a66c2' font-size='13' font-weight='bold'>第0层 产品 Product</text>
 <text x='107' y='74' text-anchor='middle' font-size='12'>iPhone 17 Pro</text>
 <text x='107' y='96' text-anchor='middle' font-size='12'>MacBook Pro 14"</text>
 <text x='107' y='118' text-anchor='middle' font-size='12'>Vision Pro (M5)</text>
 <text x='107' y='140' text-anchor='middle' font-size='12'>AirPods Pro 3</text>
 <rect x='245' y='20' width='190' height='150' rx='12' fill='#e7f6ee' stroke='#0e7c4f'/>
 <text x='340' y='44' text-anchor='middle' fill='#0e7c4f' font-size='13' font-weight='bold'>第1层 零部件 Component</text>
 <text x='340' y='74' text-anchor='middle' font-size='12'>Apple Silicon SoC</text>
 <text x='340' y='96' text-anchor='middle' font-size='12'>OLED 显示面板</text>
 <text x='340' y='118' text-anchor='middle' font-size='12'>CIS / 镜头</text>
 <text x='340' y='140' text-anchor='middle' font-size='12'>DRAM / NAND / 电池</text>
 <rect x='478' y='20' width='190' height='150' rx='12' fill='#fff3e0' stroke='#b06a00'/>
 <text x='573' y='44' text-anchor='middle' fill='#b06a00' font-size='13' font-weight='bold'>第2层 供应商 Supplier</text>
 <text x='573' y='74' text-anchor='middle' font-size='12'>TSMC / 索尼</text>
 <text x='573' y='96' text-anchor='middle' font-size='12'>三星/LG/京东方</text>
 <text x='573' y='118' text-anchor='middle' font-size='12'>富士康/立讯</text>
 <text x='573' y='140' text-anchor='middle' font-size='12'>海力士/美光</text>
 <line x1='202' y1='95' x2='245' y2='95' stroke='#0a66c2' stroke-width='2' marker-end='url(#ar)'/>
 <line x1='435' y1='95' x2='478' y2='95' stroke='#0e7c4f' stroke-width='2' marker-end='url(#ar)'/>
 <text x='223' y='88' text-anchor='middle' font-size='10' fill='#0a66c2'>USES</text>
 <text x='456' y='88' text-anchor='middle' font-size='10' fill='#0e7c4f'>SUPPLIED_BY</text>
 <defs><marker id='ar' markerWidth='8' markerHeight='8' refX='6' refY='3' orient='auto'><path d='M0,0 L6,3 L0,6 Z' fill='#444'/></marker></defs>
 </svg>'''
    return ("<section id='sec-model'><h2>二、供应链分层模型</h2>"
            "<p>图谱采用三层节点 + 三类关系，反映上下游传导路径：</p>"
            "<p><code>Product ──USES_COMPONENT──▶ Component ──SUPPLIED_BY──▶ Supplier</code><br>"
            "<code>Product ──ASSEMBLED_BY──▶ Supplier(代工)</code></p>"
            "<h3>层级定义</h3>"
            "<ul>"
            "<li><b>第 0 层 终端产品（Product）：</b>精确到具体型号，如 iPhone 17 Pro、MacBook Pro 14\" (M4)、Apple Vision Pro (M5)；含发布时间、状态、起售价等属性。</li>"
            "<li><b>第 1 层 核心零部件（Component）：</b>SoC、显示面板、CIS、镜头、存储、调制解调器、 PMIC、电池、结构件、FPC/载板、先进封装等；含中英文名称。</li>"
            "<li><b>第 2 层 供应商/代工厂（Supplier）：</b>按类别分为晶圆代工、显示、存储、半导体、声学、结构件、FPC/载板、OSAT、组装等；全称/英文名/简称分列，tier=1 为核心/技术壁垒高者，tier=2 为次级/可替代性较强者。</li>"
            "</ul>" + svg + "</section>")


def risk_section():
    return ("<section id='sec-risk'><h2>七、关键风险点</h2>"
            "<div class='risk'><b>① 晶圆代工单点依赖（台积电 / 台湾）：</b>A19 / A19 Pro / M 系列等最先进芯片 100% 由台积电台湾厂代工（3nm N3E/N3P），且先进制程依法不得外移。地缘风险高度集中，亚利桑那厂目前仅承接旧款 A16 及封装环节。</div>"
            "<div class='risk'><b>② 图像传感器单点依赖（索尼 / 日本）：</b>iPhone 主摄 CIS 由索尼独占，单部 iPhone 摄像头组件中日本元件占比超 60%，短期内难以替代（三星仅为未来潜在二供）。</div>"
            "<div class='risk'><b>③ 显示面板双雄格局（三星显示 / LG 显示）：</b>OLED 由韩厂主导；京东方(BOE)在 iPhone 17/17 Air 与 MacBook Air 快速上量（MacBook 面板份额达 51%），但高端 Pro 机型仍以韩厂为主。</div>"
            "<div class='risk'><b>④ 关税与「中国 + N」重构：</b>美国对华关税推动组装外移印度/越南，但核心零部件仍大量自东亚进口（印度 iPhone 约 52% 核心组件需自华空运），转移速度与良率受限。</div>"
            "<div class='risk'><b>⑤ 先进封装短板：</b>台积电亚利桑那产出的晶圆仍需在亚洲完成 InFO/CoWoS 等先进封装，Amkor 美国厂预计 2028 年才投产，短期难闭环。</div>"
            "</section>")


def neo4j_section():
    return ("<section id='sec-neo4j'><h2>八、Neo4j 图数据库导入指南</h2>"
            "<p>随附文件位于 <code>data/neo4j/</code> 目录：</p>"
            "<ul>"
            "<li><code>products.csv</code> · <code>components.csv</code> · <code>suppliers.csv</code> — 节点文件（含 :ID / :LABEL）</li>"
            "<li><code>rel_product_component.csv</code> · <code>rel_component_supplier.csv</code> · <code>rel_product_assembly.csv</code> — 关系文件（含 :START_ID / :END_ID / :TYPE）</li>"
            "<li><code>import_admin.sh</code> — <b>推荐</b>：Neo4j 原生离线批量导入脚本（neo4j-admin），已写死 CSV 绝对路径，无需 import/ 目录，从任意目录运行即可</li>"
            "<li><code>refresh_import.sh</code> — 把最新 6 个 CSV 同步进你的 <code>import/neo4j/</code> 目录（若你用 neo4j-admin 指向 import 目录的布局)</li>"
            "<li><code>apple_supply_chain.json</code> — 完整图数据（nodes + edges + 数据字段字典）</li>"
            "</ul>"
            "<p><b>推荐导入步骤（Neo4j 原生批量导入，最稳最快）：</b></p>"
            "<pre style='background:#0a2540;color:#dbeafe;padding:12px;border-radius:8px;overflow:auto;font-size:12.5px'>bash data/neo4j/import_admin.sh            # 默认库名 apple-supply-chain\n# 或自定义库名：  bash data/neo4j/import_admin.sh mydb\n# 等价手写命令（CSV 须绝对路径；neo4j-admin 从 PATH 或 NEO4J_HOME 取）：\nneo4j-admin database import full apple-supply-chain \\\n  --nodes=data/neo4j/products.csv \\\n  --nodes=data/neo4j/components.csv \\\n  --nodes=data/neo4j/suppliers.csv \\\n  --relationships=data/neo4j/rel_product_component.csv \\\n  --relationships=data/neo4j/rel_component_supplier.csv \\\n  --relationships=data/neo4j/rel_product_assembly.csv \\\n  --overwrite-destination</pre>"
            "<p>前提：目标数据库<b>必须停机</b>（Neo4j Desktop 中先 Stop，再 Open Terminal 运行；服务器版先停服务）。本机报错 <code>Unable to find the parent of the path: products.csv</code> 正是因为传了裸文件名——改成上面的绝对路径即可。<code>--overwrite-destination</code> 让重复导入可覆盖。</p>"
            "<p><b>关于导入格式：</b>Neo4j 官方支持的批量导入就是 <code>neo4j-admin database import</code> 读取上面这 6 个带 <code>:ID</code>/<code>:LABEL</code>/<code>:START_ID</code>/<code>:END_ID</code>/<code>:TYPE</code> 表头的 CSV —— CSV 本身就是导入文件，不需要任何 Cypher 脚本。若你的库无法停机（如 Aura 云库），才需用 Cypher 的 <code>LOAD CSV</code> 作为替代方案，但那属于「运行中的库」场景，不在本次离线批量导入范围内。</p>"
            "<h3>示例查询</h3>"
            "<p>查询某型号完整上游链（含供应商全称/英文名/简称）：</p>"
            "<pre style='background:#0a2540;color:#dbeafe;padding:12px;border-radius:8px;overflow:auto;font-size:12.5px'>MATCH (p:Product {name:'iPhone 17 Pro'})-[:USES_COMPONENT]-&gt;(c:Component)-[:SUPPLIED_BY]-&gt;(s:Supplier)\nRETURN p.name, c.name, s.name, s.english_name, s.short_name, s.country, s.tier\nORDER BY c.category, s.tier;</pre>"
            "<p>按发布时间查看产品时间线：</p>"
            "<pre style='background:#0a2540;color:#dbeafe;padding:12px;border-radius:8px;overflow:auto;font-size:12.5px'>MATCH (p:Product)\nRETURN p.release_date AS ReleaseDate, p.name AS Product, p.product_line AS Line,\n       p.price_usd AS PriceUSD, p.status AS Status\nORDER BY p.release_date;</pre>"
            "</section>")


def limits_section():
    return ("<section id='sec-limits'><h2>十、数据口径与局限</h2>"
            "<ul>"
            "<li>型号覆盖截至 2025–2026 年苹果在售/已发布主力机型；部分尚未发布机型（如折叠屏 iPhone）仅作前瞻未纳入。</li>"
            "<li>供应商份额（share）仅对公开披露较明确的少数环节（如 MacBook 面板 BOE 51%、DRAM 三星约 60–70%）标注，其余以「主要供应商」定性描述，未逐一量化。</li>"
            "<li>零部件-供应商映射基于公开拆解/BOM 与供应链报道，反映主流配置；同一型号不同批次/地区可能存在二供差异。</li>"
            "<li>别名(alias)仅记录公开可信的发布前代号或别称，无则留空；发布时间以发布会/发售日期为准，未确认机型标注年份。</li>"
            "<li>数据用于产业链结构研究与教学，不构成任何投资或采购建议。</li>"
            "</ul></section>")


def footer_html():
    return "<footer>Generated by WorkBuddy · Apple Supply Chain Graph v2 · 2026-08-04</footer>"


def build_report_inner(G, jump=False, mode="spa"):
    """Assemble the full report body (no <html>/<head> wrapper)."""
    s = []
    s.append("<section>%s</section>" % report_kpi(G))
    s.append(summary_section(G))
    s.append(model_section(G))
    s.append("<section id='sec-products'><h2>三、产品线 · 具体型号总览</h2>")
    s.append("<p>覆盖 iPhone / Mac / iPad / Apple Watch / Vision Pro / AirPods·HomePod 六大产品线，共 %d 个型号（按发布时间排序）。</p>" % len(G["nodes"]["products"]))
    s.append(product_table(G, jump, mode))
    s.append("</section>")
    s.append("<section id='sec-components'><h2>四、核心零部件 → 供应商映射</h2>")
    s.append(component_table(G, jump, mode))
    s.append("</section>")
    s.append("<section id='sec-suppliers'><h2>五、供应商 / 代工厂目录</h2>")
    s.append("<p>全称、英文名称、简称分列；层级 tier=1 为核心/高壁垒供应商。按区域排序。</p>")
    s.append(supplier_table(G, jump, mode))
    s.append("</section>")
    s.append("<section id='sec-geo'><h2>六、地理与集中度分析</h2>")
    s.append(concentration(G, jump, mode))
    s.append("</section>")
    s.append(risk_section())
    s.append(neo4j_section())
    s.append("<section id='sec-dict'><h2>九、数据字段字典（字段含义与可获取性）</h2>")
    s.append("<p>以下说明每个节点/关系的属性字段、含义与数据可获取性，便于后续维护与扩展。</p>")
    s.append(data_dictionary(G))
    s.append("</section>")
    s.append(limits_section())
    s.append(footer_html())
    return "".join(s)


def build_report_full(G, jump=False, mode="web"):
    """Standalone full HTML document with the unified cross-page nav bar."""
    nav = topnav("../", "report")
    prefix = ("<!DOCTYPE html><html lang='zh-CN'><head><meta charset='utf-8'>"
              "<meta name='viewport' content='width=device-width,initial-scale=1'>"
              "<title>苹果产品供应链上下游图谱报告（v2 属性增强版）</title>"
              "<style>" + CSS + TOPNAV_CSS + " body{padding-top:52px}section{scroll-margin-top:60px}</style></head><body>" + nav +
              "<header><h1>苹果产品供应链上下游图谱报告</h1>"
              "<p>Apple Product Supply-Chain Graph · 产品线 × 零部件 × 供应商 × 产业链（属性增强版 v2）</p>"
              "<p>数据来源：公开供应链报告（2024–2026）+ 苹果 2024 年供应商名单（187 家核心供应商，约占直接支出的 98%）</p>"
              "<p>生成日期：2026-08-04 · 可导入 Neo4j 图数据库的结构化数据已随附（CSV 官方导入文件 / JSON）</p></header>"
              "<div class='wrap'>")
    return prefix + build_report_inner(G, jump, mode) + "</div></body></html>"


def main():
    G = load_graph()
    # 多页模式下，报告实体点击 -> 跳转到独立图谱(聚焦节点)/地图(定位供应商)
    out = build_report_full(G, jump=True, mode="web")
    dst = os.path.join(ROOT, "dist", "apple_supply_chain_report.html")
    open(dst, "w", encoding="utf-8").write(out)
    print("Report written:", dst, "bytes:", len(out))


if __name__ == "__main__":
    main()
