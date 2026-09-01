# -*- coding: utf-8 -*-
"""
构建「苹果供应商生产基地地理数据集」并生成合规腾讯地图看板。
- 数据来源：各供应商公开资料整理的生产基地/总部城市（城市级近似坐标，公开可核）。
- 坐标：WGS84 录入；中国大陆 + 中国台湾按国家标准转换为 GCJ-02（腾讯地图坐标系统）。
- 合规：地图用腾讯地图 GL JS（代理模式，前端零密钥），台湾/南海按国家标准呈现。
"""
import csv, json, math, os, re, sys, urllib.parse, collections

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)
from topnav import topnav, TOPNAV_CSS, analytics_js
DATA = os.path.join(REPO, "data")
OUT_DATA = os.path.join(REPO, "tools", "data", "supplier_geo.csv")
OUT_HTML = os.path.join(REPO, "tools", "visualizations", "supplier_geo.html")

REGION_LABEL = {
    "CN": "中国大陆", "TW": "中国台湾", "HK": "中国香港",
    "KR": "韩国", "JP": "日本", "US": "美国", "IN": "印度",
    "VN": "越南", "MY": "马来西亚", "SG": "新加坡",
    "CH": "瑞士", "AT": "奥地利", "DE": "德国", "UK": "英国",
}
GC_REGIONS = {"CN", "TW", "HK"}  # 大中华区

# ---------------------------------------------------------------------------
# 1) 重点供应商（15 家，含基本面/估值）的生产基地明细
#    (supplier_id, 城市, 区域, WGS84 lng, WGS84 lat, 生产内容)
# ---------------------------------------------------------------------------
BASES = [
    ("tsmc", "新竹", "TW", 120.9675, 24.8138, "总部/研发 + 晶圆厂"),
    ("tsmc", "台南(南部科学园区)", "TW", 120.27, 23.05, "先进制程晶圆厂(3nm/2nm)"),
    ("tsmc", "台中(中科)", "TW", 120.67, 24.15, "晶圆厂(7/5nm)"),
    ("tsmc", "凤凰城(美国亚利桑那)", "US", -111.84, 33.30, "5/4nm 美国厂(地缘分散)"),
    ("tsmc", "熊本(日本)", "JP", 130.70, 32.80, "JASM 合资厂(索尼/丰田)"),

    ("foxconn", "深圳(龙华)", "CN", 114.05, 22.66, "早期 iPhone 组装/总部体系"),
    ("foxconn", "郑州", "CN", 113.62, 34.75, "iPhone 主力组装基地(最大单体)"),
    ("foxconn", "成都", "CN", 104.07, 30.57, "iPad / Mac 组装"),
    ("foxconn", "新北(土城)", "TW", 121.46, 25.01, "鸿海总部"),
    ("foxconn", "钦奈(印度)", "IN", 79.90, 12.92, "iPhone 印度组装(分散风险)"),
    ("foxconn", "北宁(越南)", "VN", 106.06, 21.18, "部分组装/零部件"),

    ("samsung_elec", "水原", "KR", 127.03, 37.26, "总部"),
    ("samsung_elec", "华城", "KR", 126.82, 37.20, "半导体/存储/晶圆代工"),
    ("samsung_elec", "平泽", "KR", 127.08, 36.99, "最大半导体复合体(HBM/DRAM/代工)"),
    ("samsung_elec", "牙山", "KR", 127.00, 36.80, "显示面板"),

    ("skhynix", "利川", "KR", 127.44, 37.27, "总部/DRAM 研发"),
    ("skhynix", "清州", "KR", 127.49, 36.64, "DRAM/NAND 晶圆厂"),
    ("skhynix", "无锡(中国)", "CN", 120.29, 31.57, "DRAM 封装/测试"),

    ("sony", "熊本", "JP", 130.70, 32.80, "CMOS 图像传感器主力厂"),
    ("sony", "长崎", "JP", 129.87, 32.75, "CMOS 图像传感器"),
    ("sony", "山形", "JP", 140.36, 38.24, "CMOS 图像传感器"),

    ("qualcomm", "圣迭戈(美国)", "US", -117.16, 32.72, "总部/芯片设计(无晶圆厂)"),
    ("broadcom", "圣何塞(美国)", "US", -121.89, 37.33, "总部/芯片设计(无晶圆厂)"),

    ("boe", "北京", "CN", 116.40, 40.00, "B5/B8 面板厂"),
    ("boe", "成都", "CN", 104.07, 30.57, "B7 柔性 OLED"),
    ("boe", "重庆", "CN", 106.55, 29.56, "B8 面板"),
    ("boe", "合肥", "CN", 117.23, 31.82, "B5/B9 面板"),
    ("boe", "绵阳", "CN", 104.68, 31.47, "B11 柔性 OLED"),
    ("boe", "昆山", "CN", 120.98, 31.39, "B10 面板"),
    ("boe", "武汉", "CN", 114.30, 30.59, "B17 面板"),

    ("lgd", "坡州", "KR", 126.60, 37.70, "最大 OLED/LCD 复合体"),
    ("lgd", "龟尾", "KR", 128.34, 36.13, "OLED 工厂"),
    ("lgd", "广州(中国)", "CN", 113.26, 23.13, "OLED(原 LCD)工厂"),

    ("murata", "长冈京(京都)", "JP", 135.68, 34.94, "总部/MLCC 主力"),
    ("murata", "野洲", "JP", 136.00, 35.00, "MLCC"),
    ("murata", "无锡(中国)", "CN", 120.29, 31.57, "MLCC/组件"),
    ("murata", "北宁(越南)", "VN", 106.06, 21.18, "MLCC/组件"),

    ("largan", "台中", "TW", 120.67, 24.15, "总部/手机镜头"),

    ("corning", "康宁(美国纽约)", "US", -77.05, 42.14, "总部/玻璃研发"),
    ("corning", "合肥(中国)", "CN", 117.23, 31.82, "LCD 玻璃基板"),
    ("corning", "上海(中国)", "CN", 121.47, 31.23, "光通信/显示"),
    ("corning", "台南(中国台湾)", "TW", 120.27, 23.05, "光学/玻璃"),

    ("luxshare", "东莞(中国)", "CN", 113.75, 23.02, "AirPods/连接器"),
    ("luxshare", "昆山(中国)", "CN", 120.98, 31.39, "零部件"),
    ("luxshare", "宜春(江西)", "CN", 114.40, 27.80, "零部件"),
    ("luxshare", "北江(越南)", "VN", 106.20, 21.27, "组装/零部件"),

    ("ase", "高雄", "TW", 120.30, 22.60, "总部/封测"),
    ("ase", "中坜(桃园)", "TW", 121.22, 24.95, "封测"),
    ("ase", "苏州(中国)", "CN", 120.60, 31.30, "封测"),
    ("ase", "槟城(马来西亚)", "MY", 100.30, 5.40, "封测"),

    ("micron", "博伊西(美国爱达荷)", "US", -116.20, 43.60, "总部/研发"),
    ("micron", "马纳萨斯(美国弗吉尼亚)", "US", -77.47, 38.75, "DRAM"),
    ("micron", "广岛(日本)", "JP", 132.45, 34.40, "DRAM/NAND"),
    ("micron", "台中(中国台湾)", "TW", 120.67, 24.15, "DRAM 封测"),
    ("micron", "新加坡", "SG", 103.82, 1.35, "NAND 制造"),
]

# ---------------------------------------------------------------------------
# 2) 宇宙内其余主要供应商（仅总部/代表点，用于呈现网络广度）
# ---------------------------------------------------------------------------
OTHERS = [
    ("pegatron", "台北", "TW", 121.52, 25.05),
    ("quanta", "桃园", "TW", 121.22, 24.99),
    ("wistron", "台北", "TW", 121.54, 25.03),
    ("byd_e", "深圳", "CN", 114.05, 22.66),
    ("catcher", "桃园", "TW", 121.22, 24.99),
    ("lens_tech", "长沙", "CN", 112.94, 28.23),
    ("goertek", "潍坊", "CN", 119.16, 36.71),
    ("sunwoda", "深圳", "CN", 114.05, 22.66),
    ("desay", "惠州", "CN", 114.42, 23.11),
    ("zhending", "桃园", "TW", 121.22, 24.99),
    ("unimicron", "桃园", "TW", 121.22, 24.99),
    ("ibiden", "大垣", "JP", 136.62, 35.37),
    ("amkor", "坦佩(美国)", "US", -111.91, 33.39),
    ("cirrus", "奥斯汀(美国)", "US", -97.74, 30.27),
    ("ti", "达拉斯(美国)", "US", -96.80, 32.78),
    ("st", "日内瓦", "CH", 6.14, 46.18),
    ("arm", "剑桥(英国)", "UK", 0.12, 52.20),
    ("ams", "普雷斯塔滕(奥地利)", "AT", 15.41, 46.99),
    ("alps", "东京", "JP", 139.76, 35.68),
    ("tdk", "东京", "JP", 139.76, 35.68),
    ("knowles", "伊塔斯卡(美国)", "US", -88.02, 41.97),
    ("aac", "深圳", "CN", 114.05, 22.66),
    ("sunny", "余姚(宁波)", "CN", 121.16, 30.05),
    ("cowell", "东莞", "CN", 113.75, 23.02),
    ("gis", "台中", "TW", 120.67, 24.15),
    ("genius", "台中", "TW", 120.67, 24.15),
    ("crystal", "台州", "CN", 121.43, 28.68),
    ("lante", "宁波", "CN", 121.55, 29.87),
    ("viseira", "新竹", "TW", 120.97, 24.81),
    ("zhaowei", "深圳", "CN", 114.05, 22.66),
    ("apple", "库比蒂诺(美国)", "US", -122.03, 37.32),
    ("kioxia", "东京", "JP", 139.76, 35.68),
    ("wdc", "圣何塞(美国)", "US", -121.89, 37.33),
    ("sdc", "牙山", "KR", 127.00, 36.80),
    ("sharp", "堺市", "JP", 135.49, 34.57),
    ("berne", "惠州", "CN", 114.42, 23.11),
    ("atl", "东莞", "CN", 113.75, 23.02),
    ("bosch", "斯图加特", "DE", 9.18, 48.78),
    ("mitsumi", "东京", "JP", 139.76, 35.68),
    ("nanya_pcb", "台北", "TW", 121.54, 25.03),
    ("flexium", "桃园", "TW", 121.22, 24.99),
    ("dongshan", "苏州", "CN", 120.60, 31.30),
    ("shennan", "深圳", "CN", 114.05, 22.66),
    ("changying", "深圳", "CN", 114.05, 22.66),
    ("lingyi", "深圳", "CN", 114.05, 22.66),
]


# ---------------------------------------------------------------------------
# GCJ-02 坐标转换（仅中国大陆 + 中国台湾需转换；海外用 WGS84）
# ---------------------------------------------------------------------------
def _transform_lat(lng, lat):
    ret = -100.0 + 2.0 * lng + 3.0 * lat + 0.2 * lat * lat + 0.1 * lng * lat + 0.2 * math.sqrt(abs(lng))
    ret += (20.0 * math.sin(6.0 * lng * math.pi) + 20.0 * math.sin(2.0 * lng * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lat * math.pi) + 40.0 * math.sin(lat / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (160.0 * math.sin(lat / 12.0 * math.pi) + 320.0 * math.sin(lat * math.pi / 30.0)) * 2.0 / 3.0
    return ret

def _transform_lng(lng, lat):
    ret = 300.0 + lng + 2.0 * lat + 0.1 * lng * lng + 0.1 * lng * lat + 0.1 * math.sqrt(abs(lng))
    ret += (20.0 * math.sin(6.0 * lng * math.pi) + 20.0 * math.sin(2.0 * lng * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lng * math.pi) + 40.0 * math.sin(lng / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (150.0 * math.sin(lng / 12.0 * math.pi) + 300.0 * math.sin(lng / 30.0 * math.pi)) * 2.0 / 3.0
    return ret

def to_gcj02(lng, lat, region):
    if region not in GC_REGIONS:
        return lng, lat
    a, ee = 6378245.0, 0.00669342162296594323
    dlat = _transform_lat(lng - 105.0, lat - 35.0)
    dlng = _transform_lng(lng - 105.0, lat - 35.0)
    radlat = lat / 180.0 * math.pi
    magic = math.sin(radlat)
    magic = 1 - ee * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((a * (1 - ee)) / (magic * sqrtmagic) * math.pi)
    dlng = (dlng * 180.0) / (a / sqrtmagic * math.cos(radlat) * math.pi)
    return lng + dlng, lat + dlat


# ---------------------------------------------------------------------------
# 载入估值结论与品类
# ---------------------------------------------------------------------------
def load_valuation():
    d = json.load(open(os.path.join(REPO, "tools", "output", "supplier_analysis.json"), encoding="utf-8"))
    out = {}
    for s in d["suppliers"]:
        out[s["id"]] = {"verdict": s["valuation"]["verdict"], "mcap": s.get("market_cap_usd_b")}
    return out

def load_category():
    g = json.load(open(os.path.join(DATA, "apple_supply_chain.json"), encoding="utf-8"))
    out = {}
    for s in g["nodes"]["suppliers"]:
        out[s["id"]] = s.get("category", "")
    return out

def load_names():
    """供应商可读名映射（nodes.suppliers 的 short_name / name / english_name）。
    地图上 POI 默认显示的是内部 supplier_id（如 tsmc），可读性差；
    优先取简短别名 short_name（如「TSMC / 台积电」），回退到全称/英文名/id。"""
    g = json.load(open(os.path.join(DATA, "apple_supply_chain.json"), encoding="utf-8"))
    out = {}
    for s in g["nodes"]["suppliers"]:
        out[s["id"]] = (s.get("short_name") or s.get("name", "") or s.get("english_name", "") or s["id"],
                        s.get("english_name", "") or "")
    return out


# ---------------------------------------------------------------------------
# 苹果组装厂代表据点（用于绘制「供应商基地 → 组装厂」物流连线）
# 坐标 WGS84，转换 GCJ-02。来源：data/geo_hubs.json（与 production_bases.draft.json 共享，避免双源漂移）。
# ---------------------------------------------------------------------------
def load_geo_hubs():
    d = json.load(open(os.path.join(DATA, "geo_hubs.json"), encoding="utf-8"))
    return d["assembly_hubs"], d["markets"]

def make_arrow_metas(line_geoms, tier, start=0):
    """为每条连线生成一枚带朝向的箭头标记元数据。start 保证 styleId 全局唯一。"""
    metas = []
    for g in line_geoms:
        idx = start + len(metas)
        brg = bearing(g["plat"], g["plng"], g["alat"], g["alng"])
        color = COLORS.get(g["styleId"], "#64748b") if tier == "up" else "#7c3aed"
        mid = [(g["plat"] + g["alat"]) / 2.0, (g["plng"] + g["alng"]) / 2.0]
    metas.append({
        "id": f"A{idx}", "styleId": f"A{idx}", "tier": tier,
        "start": [g["plat"], g["plng"]], "end": [g["alat"], g["alng"]],
        "mid": mid, "src": arrow_svg(color, brg),
        "supplier": g.get("supplier"),
    })
    return metas

# 品类粗分组（用于地图过滤 UI）。返回稳定 slug，UI 文案走 i18n（geo.cat.*）。
def coarse_cat(c):
    c = c or ""
    if c == "Memory": return "storage"
    if c in ("Foundry", "Semiconductor"): return "foundry"
    if "Display" in c or "Glass" in c or "Touch" in c: return "display"
    if "Optics" in c or "Optical" in c or "Camera" in c or "CIS" in c: return "optics"
    if c == "OSAT": return "osat"
    if c.startswith("Assembly"): return "assembly"
    if "Acoustics" in c: return "acoustics"
    if "Battery" in c or "Passive" in c: return "battery"
    if "Enclosure" in c or "Mech" in c: return "enclosure"
    if "FPC" in c or "PCB" in c or "Substrate" in c: return "connector"
    if "Sensor" in c: return "sensor"
    if "IP" in c or "EDA" in c: return "ip"
    if "Material" in c: return "material"
    return "other"

def _hexint(h):
    return int(h.lstrip("#"), 16)

def compute_flow():
    """返回 (supplier->组装厂集合, 组装厂hub坐标GCJ02)。边链：supplier→component→product→assembler。"""
    g = json.load(open(os.path.join(DATA, "apple_supply_chain.json"), encoding="utf-8"))
    E = g["edges"]
    comp_to_sups = collections.defaultdict(set)
    for e in E["supplied_by"]:
        comp_to_sups[e["from"]].add(e["to"])
    prod_to_comps = collections.defaultdict(set)
    for e in E["uses_component"]:
        prod_to_comps[e["from"]].add(e["to"])
    prod_to_asms = collections.defaultdict(set)
    for e in E["assembled_by"]:
        prod_to_asms[e["from"]].add(e["to"])
    sup_to_asms = collections.defaultdict(set)
    for comp, sups in comp_to_sups.items():
        for prod in [p for p, cs in prod_to_comps.items() if comp in cs]:
            for a in prod_to_asms.get(prod, ()):
                for s in sups:
                    sup_to_asms[s].add(a)
    ASM_HUBS, _ = load_geo_hubs()
    hubs = {}
    for a, h in ASM_HUBS.items():
        glng, glat = to_gcj02(h["lng"], h["lat"], h["region"])
        hubs[a] = (h["city"], glat, glng)
    return sup_to_asms, hubs


def build_records():
    val = load_valuation()
    cat = load_category()
    names = load_names()
    KEY_IDS = sorted({b[0] for b in BASES})
    recs = []
    # 重点供应商多基地
    for sid, city, region, lng, lat, prod in BASES:
        glng, glat = to_gcj02(lng, lat, region)
        v = val.get(sid, {})
        verdict = v.get("verdict", "定性（未上市/无倍数）")
        recs.append({
            "supplier_id": sid, "city": city, "region": region,
            "lng": round(glng, 5), "lat": round(glat, 5),
            "produces": prod, "verdict": verdict,
            "mcap": v.get("mcap"), "category": cat.get(sid, ""),
            "coarse": coarse_cat(cat.get(sid, "")),
            "name": names.get(sid, (sid, ""))[0],
            "key": True,
        })
    # 其余供应商总部点
    for sid, city, region, lng, lat in OTHERS:
        glng, glat = to_gcj02(lng, lat, region)
        v = val.get(sid, {})
        verdict = v.get("verdict", "定性（未上市/无倍数）")
        recs.append({
            "supplier_id": sid, "city": city, "region": region,
            "lng": round(glng, 5), "lat": round(glat, 5),
            "produces": "总部/代表据点", "verdict": verdict,
            "mcap": v.get("mcap"), "category": cat.get(sid, ""),
            "coarse": coarse_cat(cat.get(sid, "")),
            "name": names.get(sid, (sid, ""))[0],
            "key": (sid == "apple"),
        })
    return recs, KEY_IDS


def write_csv(recs):
    os.makedirs(os.path.dirname(OUT_DATA), exist_ok=True)
    cols = ["supplier_id", "name", "city", "region", "region_label", "lng_gcj02", "lat_gcj02",
            "produces", "verdict", "market_cap_usd_b", "category", "is_key_supplier"]
    with open(OUT_DATA, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in recs:
            w.writerow([r["supplier_id"], r["name"], r["city"], r["region"], REGION_LABEL.get(r["region"], r["region"]),
                        r["lng"], r["lat"], r["produces"], r["verdict"], r["mcap"], r["category"], r["key"]])
    print("写出", OUT_DATA, "共", len(recs), "个点")


# ---------------------------------------------------------------------------
# 洞察计算
# ---------------------------------------------------------------------------
def compute_insights(recs, key_ids):
    # 区域分布（全部点）
    region_cnt = {}
    for r in recs:
        region_cnt[r["region"]] = region_cnt.get(r["region"], 0) + 1
    region_dist = sorted(region_cnt.items(), key=lambda x: -x[1])

    # 大中华区暴露（全部生产基地）
    total = len(recs)
    gc = sum(1 for r in recs if r["region"] in GC_REGIONS)
    gc_share = gc / total * 100

    # 重点供应商：覆盖区域 / 集中度
    names = load_names()
    key_recs = [r for r in recs if r["supplier_id"] in key_ids]
    by_sup = {}
    for r in key_recs:
        by_sup.setdefault(r["supplier_id"], set()).add(r["region"])
    single_region = [s for s, regs in by_sup.items() if len(regs) == 1]
    multi_region = [s for s, regs in by_sup.items() if len(regs) >= 2]
    single_region_names = [names.get(s, (s, ""))[0] for s in single_region]

    # 估值 × 地理
    val = load_valuation()
    verdict_regions = {}
    for s, regs in by_sup.items():
        vd = val.get(s, {}).get("verdict", "定性")
        verdict_regions.setdefault(vd, []).append(len(regs))
    verdict_geo = {k: (sum(v) / len(v), len(v)) for k, v in verdict_regions.items()}

    # 品类 × 区域
    cat = load_category()
    cat_region = {}
    for s, regs in by_sup.items():
        c = cat.get(s, "其他")
        cat_region.setdefault(c, set()).update(regs)

    return {
        "region_dist": region_dist,
        "total": total, "gc": gc, "gc_share": gc_share,
        "n_key": len(by_sup), "single_region": sorted(single_region),
        "single_region_names": sorted(single_region_names),
        "multi_region": sorted(multi_region),
        "verdict_geo": verdict_geo, "cat_region": cat_region,
    }


# ---------------------------------------------------------------------------
# HTML 生成（腾讯地图 GL JS，代理模式，合规）
# ---------------------------------------------------------------------------
COLORS = {"低估": "#2563eb", "高估": "#dc2626", "困境": "#d97706",
          "基准": "#111827", "其他": "#64748b"}
EMOJI = {"低估": "🔵", "高估": "🔴", "困境": "⚠️", "基准": "🖥️", "其他": "⚪"}

def style_for(r):
    v = r["verdict"]
    if "低估" in v: return "低估"
    if "高估" in v: return "高估"
    if "困境" in v: return "困境"
    if "基准" in v: return "基准"
    return "其他"

def marker_svg(color):
    svg = (f"<svg xmlns='http://www.w3.org/2000/svg' width='22' height='22'>"
           f"<circle cx='11' cy='11' r='8' fill='{color}' stroke='white' stroke-width='2'/></svg>")
    return "data:image/svg+xml," + urllib.parse.quote(svg, safe="")

def bearing(lat1, lng1, lat2, lng2):
    """初始方位角（度，0=正北，顺时针），用于箭头朝向。"""
    lat1r, lat2r = math.radians(lat1), math.radians(lat2)
    dlng = math.radians(lng2 - lng1)
    x = math.sin(dlng) * math.cos(lat2r)
    y = math.cos(lat1r) * math.sin(lat2r) - math.sin(lat1r) * math.cos(lat2r) * math.cos(dlng)
    brg = math.degrees(math.atan2(x, y))
    return (brg + 360) % 360

def arrow_svg(color, deg):
    """带旋转三角箭头的 data URI（指向流动方向）。"""
    svg = (f"<svg xmlns='http://www.w3.org/2000/svg' width='18' height='18'>"
           f"<g transform='rotate({deg:.1f} 9 9)'>"
           f"<path d='M9 1 L14 14 L9 10.5 L4 14 Z' fill='{color}' stroke='white' stroke-width='1.2'/>"
           f"</g></svg>")
    return "data:image/svg+xml," + urllib.parse.quote(svg, safe="")

def market_svg():
    """终端市场标记（金色四角星）。"""
    svg = ("<svg xmlns='http://www.w3.org/2000/svg' width='24' height='24'>"
           "<path d='M12 2 L14.6 9.4 L22 12 L14.6 14.6 L12 22 L9.4 14.6 L2 12 L9.4 9.4 Z' "
           "fill='#f59e0b' stroke='white' stroke-width='1.5'/></svg>")
    return "data:image/svg+xml," + urllib.parse.quote(svg, safe="")

def dim_marker_svg():
    """聚焦时用于淡化非目标供应商的灰色圆点。"""
    svg = ("<svg xmlns='http://www.w3.org/2000/svg' width='22' height='22'>"
           "<circle cx='11' cy='11' r='8' fill='#cbd5e1' stroke='white' stroke-width='2'/></svg>")
    return "data:image/svg+xml," + urllib.parse.quote(svg, safe="")

def build_geo_data(recs, insights):
    """构建地图所需的全部数据（标记 / 连线 / 箭头 / 侧栏面板），供 build_html 复用。"""
    styles = {}
    for name, color in COLORS.items():
        styles[name] = marker_svg(color)

    geometries = []
    for i, r in enumerate(recs):
        st = style_for(r)
        vshort = st
        mcap = r["mcap"]
        mcap_s = f"{mcap:.0f}" if isinstance(mcap, (int, float)) else "-"
        geometries.append({
            "id": str(i), "styleId": st, "sid": r["supplier_id"],
            "lat": r["lat"], "lng": r["lng"],
            "name": r["name"], "city": r["city"], "region": r["region"],
            "produces": r["produces"], "verdict": r["verdict"], "mcap": mcap_s,
            "label": r["name"], "cat": r["coarse"],
        })

    # 侧栏洞察：区域分布 / 估值×地理 交由浏览器按 i18n 渲染（见 build_html 内 localizeGeo）；
    # 单区域供应商名单为专名，保留原样。
    cr = "".join(f"<span class='chip'>{c}</span>" for c in insights["single_region_names"])

    # ---- 供应链物流连线（供应商基地 -> 苹果组装厂）----
    val = load_valuation()
    sup_to_asms, hubs = compute_flow()
    primary = {}
    for sid, city, region, lng, lat, prod in BASES:
        if sid not in primary:
            glng, glat = to_gcj02(lng, lat, region)
            primary[sid] = (glat, glng)
    line_geoms = []
    li = 0
    for sid, asms in sup_to_asms.items():
        if sid not in primary:
            continue
        plat, plng = primary[sid]
        st = style_for({"verdict": val.get(sid, {}).get("verdict", "")})
        for a in sorted(asms):
            if a not in hubs:
                continue
            _, alat, alng = hubs[a]
            line_geoms.append({"id": f"L{li}", "styleId": st,
                               "plat": plat, "plng": plng, "alat": alat, "alng": alng,
                               "supplier": sid, "assembler": a})
            li += 1

    # ---- 下游连线（组装厂 -> 终端市场）+ 终端市场标记 + 箭头元数据 ----
    _, MARKETS = load_geo_hubs()
    market_coords = []
    for m in MARKETS:
        mname, mregion, mlng, mlat, mdesc = m["name"], m["region"], m["lng"], m["lat"], m["desc"]
        glng, glat = to_gcj02(mlng, mlat, mregion)
        market_coords.append((mname, glat, glng))
    down_geoms = []
    di = 0
    for a, (city, alat, alng) in hubs.items():
        for (mname, mlat, mlng) in market_coords:
            down_geoms.append({"id": f"D{di}", "styleId": "downstream",
                               "plat": alat, "plng": alng, "alat": mlat, "alng": mlng,
                               "assembler": a, "market": mname})
            di += 1
    market_geoms = []
    for i, m in enumerate(MARKETS):
        mname, mregion, mlng, mlat, mdesc = m["name"], m["region"], m["lng"], m["lat"], m["desc"]
        glng, glat = to_gcj02(mlng, mlat, mregion)
        market_geoms.append({"id": f"M{i}", "lat": round(glat, 5), "lng": round(glng, 5),
                             "name": mname, "region": mregion, "desc": mdesc})
    arrow_metas = make_arrow_metas(line_geoms, "up", start=0) + make_arrow_metas(down_geoms, "down", start=len(line_geoms))

    # ---- 品类过滤（按钮文案由浏览器按 i18n 渲染，data-cat-key 供 localizeGeo 填充） ----
    all_cats = sorted({r["coarse"] for r in recs})
    cat_buttons = "".join(
        f"<button class='fbtn on' data-cat='{c}' data-cat-key='geo.cat.{c}'>{c}</button>" for c in all_cats
    )
    line_styles_js = ",\n".join(
        f"        {name}: new TMap.PolylineStyle({{ color: 0x{h}, width: 1.5 }})"
        for name, h in [("低估", "2563eb"), ("高估", "dc2626"), ("困境", "d97706"),
                        ("其他", "64748b"), ("downstream", "7c3aed")]
    )
    arrow_styles_js = ",\n".join(
        f"        {m['id']}: new TMap.MarkerStyle({{ width: 16, height: 16, src: '{m['src']}' }})"
        for m in arrow_metas
    )
    arrow_meta_list = [{'id': m['id'], 'styleId': m['styleId'], 'tier': m['tier'],
                        'start': m['start'], 'end': m['end'], 'mid': m['mid'],
                        'supplier': m['supplier']} for m in arrow_metas]

    panel = f"""
    <div id="panel">
      <h1 data-i18n="geo.panel.title">苹果供应商 · 生产基地地理洞察</h1>
      <p class="muted" data-i18n="geo.panel.intro">数据：各供应商公开资料整理的生产基地/总部（城市级近似坐标，GCJ-02）。标记按估值判定着色。</p>

      <h2 data-i18n="geo.sec1">① 生产基地区域分布</h2>
      <div class="bars" id="geoBars"></div>
      <div class="hl" id="geoHl"></div>

      <h2 data-i18n="geo.sec2">② 重点供应商区域覆盖与集中度风险</h2>
      <p id="geoSec2Note"></p>
      <div class="chips"><span class="chip-h" data-i18n="geo.popup.singleRegion">单区域：</span>{cr}</div>

      <h2 data-i18n="geo.sec3">③ 估值 × 地理（平均覆盖区域数/家）</h2>
      <div class="kvs" id="geoVg"></div>
      <p class="muted" data-i18n="geo.sec3Note">说明：覆盖区域越多通常意味着产能分散、地缘韧性更强；可结合估值判定观察“被低估是否伴随更强的地理韧性”。</p>

      <h2 data-i18n="geo.sec4">④ 图例</h2>
      <div class="legend">
        <span><i style="background:{COLORS['低估']}"></i><span data-i18n="geo.legend.undervalued">低估</span></span>
        <span><i style="background:{COLORS['高估']}"></i><span data-i18n="geo.legend.overvalued">高估</span></span>
        <span><i style="background:{COLORS['困境']}"></i><span data-i18n="geo.legend.distressed">困境(亏损)</span></span>
        <span><i style="background:{COLORS['基准']}"></i><span data-i18n="geo.legend.apple">苹果(基准)</span></span>
        <span><i style="background:{COLORS['其他']}"></i><span data-i18n="geo.legend.other">其他供应商</span></span>
        <span><i style="background:#7c3aed"></i><span data-i18n="geo.legend.downstream">下游(组装→市场)</span></span>
        <span><i style="background:var(--warn)"></i><span data-i18n="geo.legend.market">终端市场</span></span>
      </div>
      <p class="muted" data-i18n="geo.tipClick">点击地图标记查看生产基地 / 市场详情。</p>

      <h2 data-i18n="geo.sec5">⑤ 供应链物流连线</h2>
      <p class="muted" data-i18n="geo.sec5Note">蓝/红/橙线 = 供应商基地 → 苹果组装厂（按估值着色）；紫色线 = 组装厂 → 终端市场（美/中/欧）。连线依据图谱 edge 链推导，箭头指示流动方向。点击地图供应商标记可高亮其连线、淡化其余。</p>
      <input id="supSearch" class="sup-search" type="search" data-i18n-attr="placeholder:geo.searchPlaceholder" placeholder="搜索供应商（名称或 ID）…" />
      <div class="chips">
        <button id="upToggle" class="fbtn on" onclick="toggleUp(this)">隐藏供应连线</button>
        <button id="downToggle" class="fbtn on" onclick="toggleDown(this)">隐藏下游连线</button>
        <button id="flowToggle" class="fbtn" onclick="toggleFlow(this)">▶ 流动动画</button>
        <button id="labelToggle" class="fbtn" onclick="toggleLabels(this)">显示供应商名称</button>
        <button id="resetView" class="fbtn" data-i18n="geo.btn.reset" onclick="resetView()">重置视图</button>
        <button id="clearFocus" class="fbtn" data-i18n="geo.btn.clear" onclick="clearFocus()">清除高亮</button>
      </div>

      <h2 data-i18n="geo.sec6">⑥ 按品类过滤</h2>
      <div class="chips" id="catFilter">{cat_buttons}<button class="fbtn on" data-cat="__ALL__" data-i18n="geo.catAll">全部</button></div>
      <p class="muted" data-i18n="geo.sec6Note">点击品类标签可显示/隐藏对应生产基地（含其余供应商）。</p>

      <h2 data-i18n="geo.sec7">⑦ 终端市场（汇聚点）</h2>
      <div class="chips"><span class="chip gold" data-i18n="geo.market.us">美国 · 库比蒂诺</span><span class="chip gold" data-i18n="geo.market.cn">中国 · 上海</span><span class="chip gold" data-i18n="geo.market.eu">欧洲 · 慕尼黑</span></div>
      <p class="muted" data-i18n="geo.sec7Note">组装厂经紫色下游连线向三大终端市场出货，形成「供应商→组装→市场」全链路视图。</p>
    </div>
    """

    geo_i = {
        "total": insights["total"], "gc": insights["gc"], "gc_share": round(insights["gc_share"]),
        "n_key": insights["n_key"],
        "single_region": len(insights["single_region"]),
        "multi_region": len(insights["multi_region"]),
        "region_dist": insights["region_dist"],
        "verdict_geo": {k: [round(v[0], 2), v[1]] for k, v in insights["verdict_geo"].items()},
        "all_cats": all_cats,
    }

    return {
        "styles": styles, "geometries": geometries, "panel": panel,
        "all_cats": all_cats, "line_styles_js": line_styles_js,
        "arrow_styles_js": arrow_styles_js, "arrow_meta_list": arrow_meta_list,
        "market_geoms": market_geoms, "line_geoms": line_geoms, "down_geoms": down_geoms,
        "geo_i": geo_i,
    }


def build_html(recs, insights):
    G = build_geo_data(recs, insights)
    styles = G["styles"]; geometries = G["geometries"]; panel = G["panel"]
    all_cats = G["all_cats"]; line_styles_js = G["line_styles_js"]
    arrow_styles_js = G["arrow_styles_js"]; arrow_meta_list = G["arrow_meta_list"]
    market_geoms = G["market_geoms"]; line_geoms = G["line_geoms"]; down_geoms = G["down_geoms"]
    geo_i = G["geo_i"]
    styles_js = ",\n".join(f"        {name}: new TMap.MarkerStyle({{ width: 22, height: 22, src: '{styles[name]}' }})" for name in COLORS)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>苹果供应商生产基地地理洞察</title>
<style>
  :root {{
    --bg: #0c1020; --card: #131a2e; --soft: #1b2340; --line: #2a3450; --line-soft: #1c2336;
    --ink: #e8ecf4; --ink-soft: #cfe0ff; --muted: #9fb0d0; --muted-dim: #7c8aa8;
    --bright: #ffffff; --link: #dbeafe; --ink-inverse: #111111;
    --control: #33406a; --control-hover: #3a4a6e; --control-border: #3f4f7a;
    --blue: #6ea0ff; --primary: #2f6fed; --primary-hover: #3b82f6; --focus: #5b8cff;
    --brand: #0a2540; --brand-2: #0a66c2;
  --violet: #8b5cf6; --pink: #ec4899; --cyan: #22d3ee;
    --green: #4ade80; --success-ink: #bbf7d0; --success-bg: #163a2a;
    --red: #f87171; --danger-ink: #ffb4b4; --danger-bg: #3b1520; --danger-line: #7f1d1d;
    --amber: #fbbf24; --warn: #f59e0b; --warn-ink: #fde68a; --warn-bg: #3a2e16; --warn-line: #7a5c14;
    --fs-xs: 11px; --fs-sm: 12px; --fs-base: 13px; --fs-md: 14px;
    --fs-lg: 16px; --fs-xl: 18px; --fs-display: 24px;
  }}
  html, body {{ margin: 0; padding: 0; height: 100%; background: var(--bg); font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif; }}
  #map {{ position: absolute; top: 52px; left: 0; right: 0; bottom: 0; }}
__TOPNAV_CSS__
  #panel {{
    position: absolute; top: 64px; right: 12px; width: 340px; max-height: calc(100vh - 76px);
    overflow-y: auto; background: rgba(19,26,46,0.96); border-radius: 12px;
    box-shadow: 0 8px 30px rgba(0,0,0,0.45); padding: 16px 18px; font-size: var(--fs-base); color: var(--ink); z-index: 1000;
  }}
  #panel h1 {{ font-size: var(--fs-lg); margin: 0 0 4px; }}
  #panel h2 {{ font-size: var(--fs-base); margin: 16px 0 6px; color: var(--ink); }}
  .muted {{ color: var(--muted); font-size: var(--fs-xs); line-height: 1.5; }}
  .bars {{ display: flex; flex-direction: column; gap: 4px; }}
  .bar-row {{ display: flex; align-items: center; gap: 6px; }}
  .bar-label {{ width: 64px; flex: none; font-size: var(--fs-sm); }}
  .bar-track {{ flex: 1; background: var(--soft); border-radius: 4px; height: 14px; overflow: hidden; }}
  .bar-fill {{ display: block; height: 100%; background: linear-gradient(90deg,var(--blue),var(--primary)); }}
  .bar-num {{ width: 24px; text-align: right; font-size: var(--fs-sm); }}
  .hl {{ margin-top: 8px; padding: 8px 10px; background: var(--warn-bg); border-left: 3px solid var(--warn); border-radius: 6px; font-size: var(--fs-sm); }}
  .hl b {{ font-size: var(--fs-md); color: var(--amber); }}
  .chips {{ display: flex; flex-wrap: wrap; gap: 4px; margin-top: 6px; }}
  .chip {{ background: var(--danger-bg); color: var(--red); border: 1px solid var(--danger-line); border-radius: 999px; padding: 2px 8px; font-size: var(--fs-xs); }}
  .chip-h {{ color: var(--muted); align-self: center; }}
  .kvs {{ display: flex; flex-direction: column; gap: 3px; }}
  .kv {{ display: flex; align-items: baseline; gap: 6px; font-size: var(--fs-sm); }}
  .kv b {{ color: var(--blue); }}
  .kv .sub {{ color: var(--muted); font-size: var(--fs-xs); }}
  .legend {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 6px; font-size: var(--fs-sm); }}
  .legend span {{ display: flex; align-items: center; gap: 4px; }}
  .legend i {{ width: 12px; height: 12px; border-radius: 50%; display: inline-block; }}
  .fbtn {{ cursor: pointer; border: 1px solid var(--line); background: var(--soft); color: var(--ink-soft); border-radius: 999px; padding: 5px 12px; font-size: var(--fs-xs); margin: 2px 0; }}
  .fbtn.on {{ background: var(--primary); color: var(--bright); border-color: var(--primary); }}
  .fbtn:hover {{ border-color: var(--primary-hover); color: var(--blue); }}
  .fbtn.on:hover {{ color: var(--bright); }}
  .chip.gold {{ background: var(--warn-bg); color: var(--amber); border: 1px solid var(--warn-line); }}
  .poi-label {{ background: rgba(27,35,64,0.92); border: 1px solid var(--line); border-radius: 4px; padding: 0 4px; font-size: var(--fs-xs); line-height: 15px; color: var(--ink); white-space: nowrap; box-shadow: 0 1px 2px rgba(0,0,0,0.12); }}
  .sup-search {{ width: 100%; box-sizing: border-box; margin: 6px 0; padding: 6px 10px; border: 1px solid var(--line); background: var(--card); color: var(--ink); border-radius: 8px; font-size: var(--fs-sm); outline: none; }}
  .sup-search:focus {{ border-color: var(--primary-hover); }}
  .leaflet-popup-content-wrapper {{ background: var(--card); color: var(--ink); border: 1px solid var(--line); border-radius: 8px; box-shadow: 0 8px 30px rgba(0,0,0,0.45); }}
  .leaflet-popup-tip {{ background: var(--card); border: 1px solid var(--line); }}
  .leaflet-popup-content {{ color: var(--ink); line-height: 1.5; }}
  a.leaflet-popup-close-button {{ color: var(--muted); }}
</style>
<script type="text/javascript">
  window._TMapSecurityConfig = {{
    serviceHost: 'http://127.0.0.1:__WB_HTTP_PORT__/_TMapService/_wbt/__WB_TMAP_SECRET__',
  }};
</script>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://map.qq.com/api/gljs?v=1.exp"></script>
</head>
<body>
__TOPNAV__
<div id="map"></div>
{panel}
<script>
  // 地图后端选择：serviceHost 仍为本地 127.0.0.1 占位符（未配腾讯代理）时，
  // 默认用 Leaflet + OpenStreetMap（纯前端、免 Key、免代理，GitHub Pages 等静态托管直接可用）；
  // 若已配置真实代理域名（自建签名代理 + Key），则保留腾讯地图 GL 原样式。
  const __SH = 'http://127.0.0.1:__WB_HTTP_PORT__/_TMapService/_wbt/__WB_TMAP_SECRET__';
  const __USE_TMAP = !__SH.includes('127.0.0.1') && typeof TMap !== 'undefined';
  const __HEX = {{ '低估':'#2563eb', '高估':'#dc2626', '困境':'#d97706', '基准':'#111827', '其他':'#64748b', 'market':'#f59e0b', 'downstream':'#7c3aed' }};

  const RAW = {json.dumps(geometries, ensure_ascii=False)};
  const GEOMS = RAW.map(r => ({{ id: r.id, styleId: r.styleId, sid: r.sid, lat: r.lat, lng: r.lng,
    name: r.name, city: r.city, region: r.region, produces: r.produces, verdict: r.verdict, mcap: r.mcap,
    label: r.label, cat: r.cat }}));
  const GEO_I = {json.dumps(geo_i, ensure_ascii=False)};
  const ALL_CATS = GEO_I.all_cats;
  let activeCats = new Set(ALL_CATS);
  let upVisible = true, downVisible = true, flowOn = false, flowRAF = null, flowT = 0.5;
  let labelsOn = false;
  let searchTerm = "";
  let focusSid = null;

  // ---- 搜索 / 聚焦 辅助 ----
  function matchesSearch(g) {{
    if (!searchTerm) return true;
    const t = searchTerm.toLowerCase();
    return (g.name && g.name.toLowerCase().indexOf(t) >= 0) || (g.sid && g.sid.toLowerCase().indexOf(t) >= 0);
  }}
  function setFocus(sid) {{
    focusSid = sid;
    if (window.__B) {{ window.__B.filter(); window.__B.applyUp(); window.__B.applyDown(); window.__B.refreshArrows(); }}
  }}
  function doSearch(v) {{
    searchTerm = (v || "").trim();
    if (window.__B) window.__B.filter();
    if (searchTerm) {{
      const ms = GEOMS.filter(g => activeCats.has(g.cat) && matchesSearch(g));
      if (ms.length && window.__B) window.__B.fitTo(ms);
    }}
  }}
  function resetView() {{ if (window.__B) window.__B.resetView(); }}
  function clearFocus() {{ setFocus(null); }}

  const MARKET_RAW = {json.dumps(market_geoms, ensure_ascii=False)};
  const MARKET_GEOMS = MARKET_RAW.map(r => ({{ id: r.id, lat: r.lat, lng: r.lng, name: r.name, region: r.region, desc: r.desc }}));
  const UP_RAW = {json.dumps(line_geoms, ensure_ascii=False)};
  const UP_LINES = UP_RAW.map(r => ({{ id: r.id, styleId: r.styleId, supplier: r.supplier, plat: r.plat, plng: r.plng, alat: r.alat, alng: r.alng }}));
  const DOWN_RAW = {json.dumps(down_geoms, ensure_ascii=False)};
  const DOWN_LINES = DOWN_RAW.map(r => ({{ id: r.id, styleId: r.styleId, plat: r.plat, plng: r.plng, alat: r.alat, alng: r.alng }}));
  const ARROW_META = {json.dumps(arrow_meta_list, ensure_ascii=False)};

  // ---- i18n 渲染辅助：缺译文时由 dist/i18n.js 运行时自动翻译（MyMemory），离线回退中文 ----
  function T(k, o) {{ return (window.i18n ? window.i18n.t(k, o) : ((o && o.defaultValue) || k)); }}
  const VERDICT_EMOJI = {{ '低估':'🔵', '高估':'🔴', '困境':'⚠️', '基准':'🖥️', '其他':'⚪' }};
  function supHtml(g) {{
    const rl = T('geo.region.' + g.region, {{ defaultValue: g.region }});
    const emo = VERDICT_EMOJI[g.styleId] || '';
    let h = "<div style='font-size: var(--fs-base);line-height:1.5'>"
      + "<b>" + g.name + "</b> <span style='color:var(--muted-dim)'>(" + g.sid + ")</span> · " + g.city + "<br>"
      + T('geo.popup.region') + "：" + rl + "<br>"
      + T('geo.popup.content') + "：" + g.produces + "<br>"
      + T('geo.popup.verdict') + "：" + emo + " " + g.verdict + "<br>";
    if (g.mcap && g.mcap !== '-') h += T('geo.popup.mcap') + "：" + g.mcap + " " + T('geo.popup.mcapUnit') + "<br>";
    h += "</div><div style='margin-top:6px'>"
      + "<a href='../../index.html?focus=S:" + g.sid + "' target='_blank' style='color:var(--blue)'>" + T('geo.popup.viewLink') + "</a>"
      + "</div>";
    return h;
  }}
  function marketHtml(g) {{
    const rl = T('geo.region.' + g.region, {{ defaultValue: g.region }});
    return "<div style='font-size: var(--fs-base);line-height:1.5'><b>" + g.name + "</b><br>" + T('geo.popup.region') + "：" + rl + "<br>" + g.desc + "</div>";
  }}
  function localizeGeo() {{
    const I = GEO_I;
    const maxC = I.region_dist.length ? I.region_dist[0][1] : 1;
    const bars = document.getElementById('geoBars');
    if (bars) bars.innerHTML = I.region_dist.map(function (e) {{
      const rg = e[0], cnt = e[1];
      return "<div class='bar-row'><span class='bar-label'>" + T('geo.region.' + rg, {{ defaultValue: rg }}) + "</span>"
        + "<span class='bar-track'><span class='bar-fill' style='width:" + (cnt / maxC * 100).toFixed(0) + "%'></span></span>"
        + "<span class='bar-num'>" + cnt + "</span></div>";
    }}).join('');
    const hl = document.getElementById('geoHl');
    if (hl) hl.innerHTML = T('geo.hlGc', {{ p: I.gc_share, d: I.gc, t: I.total }});
    const s2 = document.getElementById('geoSec2Note');
    if (s2) s2.innerHTML = T('geo.sec2Note', {{ n: I.n_key, s: I.single_region, m: I.multi_region }});
    const vg = document.getElementById('geoVg');
    if (vg) vg.innerHTML = Object.keys(I.verdict_geo).map(function (k) {{
      const v = I.verdict_geo[k];
      return "<div class='kv'><span>" + k + "</span><b>" + v[0].toFixed(2) + " " + T('geo.regionPerSupplier') + "</b><span class='sub'>(" + v[1] + " " + T('geo.unit.supplier') + ")</span></div>";
    }}).join('');
    document.querySelectorAll('#catFilter .fbtn[data-cat-key]').forEach(function (b) {{ b.textContent = T(b.dataset.catKey); }});
  }}
  function syncToggleLabels() {{
    const up = document.getElementById('upToggle'); if (up) up.textContent = T(upVisible ? 'geo.btn.hideUp' : 'geo.btn.showUp');
    const dn = document.getElementById('downToggle'); if (dn) dn.textContent = T(downVisible ? 'geo.btn.hideDown' : 'geo.btn.showDown');
    const fl = document.getElementById('flowToggle'); if (fl) fl.textContent = T(flowOn ? 'geo.btn.flowStop' : 'geo.btn.flow');
    const lb = document.getElementById('labelToggle'); if (lb) lb.textContent = T(labelsOn ? 'geo.btn.labelsHide' : 'geo.btn.labels');
  }}

  // 品类过滤（后端无关，仅更新 activeCats 后调用后端刷新）
  document.querySelectorAll('.fbtn[data-cat]').forEach(b => {{
    b.addEventListener('click', () => {{
      const c = b.dataset.cat;
      if (c === '__ALL__') {{ activeCats = new Set(ALL_CATS); }}
      else {{ if (activeCats.has(c)) activeCats.delete(c); else activeCats.add(c); }}
      document.querySelectorAll('.fbtn[data-cat]').forEach(x => {{
        const cc = x.dataset.cat;
        const on = cc === '__ALL__' ? activeCats.size === ALL_CATS.length : activeCats.has(cc);
        x.classList.toggle('on', on);
      }});
      if (window.__B) window.__B.filter();
    }});
  }});

  // 搜索框：输入即过滤 + 自动定位
  const searchEl = document.getElementById('supSearch');
  if (searchEl) searchEl.addEventListener('input', function () {{ doSearch(searchEl.value); }});

  // ---------- Leaflet 后端（默认，静态托管可用） ----------
  function initLeaflet() {{
    const map = L.map('map', {{ zoomControl: true }}).setView([28, 112], 3);
    L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}.png', {{ maxZoom: 19, attribution: '© OpenStreetMap © CARTO' }}).addTo(map);
    const supLayer = L.layerGroup().addTo(map);
    const upLayer = L.layerGroup().addTo(map);
    const downLayer = L.layerGroup().addTo(map);
    const arrowLayer = L.layerGroup().addTo(map);
    const marketLayer = L.layerGroup().addTo(map);
    const colorOf = (s) => __HEX[s] || '#64748b';
    function renderSuppliers() {{
      supLayer.clearLayers();
      GEOMS.forEach(g => {{
        if (!activeCats.has(g.cat)) return;
        if (searchTerm && !matchesSearch(g)) return;
        const isFocus = focusSid && g.sid === focusSid;
        const dim = focusSid && !isFocus;
        const m = L.circleMarker([g.lat, g.lng], {{
          radius: isFocus ? 10 : 7, color: isFocus ? '#111827' : '#fff', weight: isFocus ? 3 : 2,
          fillColor: colorOf(g.styleId), fillOpacity: dim ? 0.16 : 1
        }});
        m.bindPopup(supHtml(g));
        if (g.label) m.bindTooltip(g.label, {{ permanent: labelsOn, direction: 'right', className: 'poi-label', opacity: 0.92 }});
        if (!dim) m.on('click', function (e) {{ L.DomEvent.stopPropagation(e); setFocus(g.sid); }});
        supLayer.addLayer(m);
      }});
    }}
    function renderMarkets() {{
      marketLayer.clearLayers();
      MARKET_GEOMS.forEach(g => {{
        const m = L.circleMarker([g.lat, g.lng], {{ radius: 8, color: '#fff', weight: 2, fillColor: colorOf('market'), fillOpacity: 1 }});
        m.bindPopup(marketHtml(g)); marketLayer.addLayer(m);
      }});
    }}
    function renderLines() {{
      upLayer.clearLayers(); downLayer.clearLayers();
      if (upVisible) UP_LINES.forEach(l => {{
        const isFocus = focusSid && l.supplier === focusSid;
        const dim = focusSid && !isFocus;
        upLayer.addLayer(L.polyline([[l.plat, l.plng], [l.alat, l.alng]], {{ color: colorOf(l.styleId), weight: isFocus ? 3 : 1.5, opacity: dim ? 0.12 : 0.7 }}));
      }});
      if (downVisible) DOWN_LINES.forEach(l => {{
        const dim = !!focusSid;
        downLayer.addLayer(L.polyline([[l.plat, l.plng], [l.alat, l.alng]], {{ color: colorOf(l.styleId), weight: 1.5, opacity: dim ? 0.12 : 0.7 }}));
      }});
    }}
    function renderArrows() {{
      arrowLayer.clearLayers();
      ARROW_META.filter(a => ((a.tier==='up'&&upVisible) || (a.tier==='down'&&downVisible)) && (!focusSid || a.tier!=='up' || a.supplier===focusSid)).forEach(a => {{
        const lat = a.start[0] + (a.end[0]-a.start[0])*flowT;
        const lng = a.start[1] + (a.end[1]-a.start[1])*flowT;
        const ang = Math.atan2(a.end[0]-a.start[0], a.end[1]-a.start[1]) * 180 / Math.PI;
        const ic = L.divIcon({{ className:'', html: "<div style='transform:rotate("+ang.toFixed(1)+"deg);color:"+colorOf(a.styleId)+";font-size: var(--fs-md);line-height:1'>➤</div>", iconSize:[14,14], iconAnchor:[7,7] }});
        arrowLayer.addLayer(L.marker([lat, lng], {{ icon: ic }}));
      }});
    }}
    renderSuppliers(); renderMarkets(); renderLines(); renderArrows();
    map.on('click', function () {{ setFocus(null); }});
    window.__B = {{
      filter: renderSuppliers,
      applyUp: function() {{ renderLines(); renderArrows(); }},
      applyDown: function() {{ renderLines(); renderArrows(); }},
      refreshArrows: renderArrows,
      toggleLabels: function() {{ renderSuppliers(); }},
      relocalize: function() {{ renderSuppliers(); renderMarkets(); localizeGeo(); syncToggleLabels(); }},
      invalidate: function() {{ map.invalidateSize(); }},
      openSupplier: function(sid) {{
        const g = GEOMS.find(x => x.sid === sid) || GEOMS.find(x => String(x.id) === sid);
        if (!g) return;
        map.setView([g.lat, g.lng], 6);
        L.popup().setLatLng([g.lat, g.lng]).setContent(g.html).openOn(map);
      }},
      fitTo: function (ms) {{ map.fitBounds(L.latLngBounds(ms.map(m => [m.lat, m.lng])), {{ padding: [40, 40], maxZoom: 7 }}); }},
      resetView: function () {{ map.setView([28, 112], 3); }}
    }};
  }}

  // ---------- 腾讯地图后端（配置了真实代理 + Key 时） ----------
  function initTMap() {{
    const map = new TMap.Map('map', {{ zoom: 3, center: new TMap.LatLng(28, 112), mapStyleId: 'style1' }});
    const markers = new TMap.MultiMarker({{ map: map, styles: {{{styles_js}\n        , dim: new TMap.MarkerStyle({{ width: 22, height: 22, src: '{dim_marker_svg()}' }}) }}, geometries: GEOMS.map(g => ({{ id: g.id, styleId: (focusSid && g.sid !== focusSid) ? 'dim' : g.styleId, position: new TMap.LatLng(g.lat, g.lng), properties: {{ name: g.name, cat: g.cat }} }})) }});
    const info = new TMap.InfoWindow({{ map: map, position: new TMap.LatLng(28, 112), content: '', visible: false }});
    markers.on('click', (e) => {{ const g = GEOMS.find(x => x.id === e.geometry.id); if (!g) return; info.setPosition(e.geometry.position); info.setContent(supHtml(g)); info.open(); setFocus(g.sid); }});
    const labelLayer = new TMap.MultiLabel({{ map: map, styles: {{ label: new TMap.LabelStyle({{ color: '#e8ecf4', size: 12, offset: {{ x: 8, y: 0 }}, background: {{ color: '#1b2340', borderColor: '#2a3450', borderWidth: 1, borderRadius: 4 }}, alignment: 'left' }}) }}, geometries: (labelsOn ? GEOMS.filter(g => g.label && activeCats.has(g.cat)) : []).map(g => ({{ id: g.id, styleId: 'label', position: new TMap.LatLng(g.lat, g.lng), content: g.label }})) }});
    const marketLayer = new TMap.MultiMarker({{ map: map, styles: {{ market: new TMap.MarkerStyle({{ width: 24, height: 24, src: '{market_svg()}' }}) }}, geometries: MARKET_GEOMS.map(g => ({{ id: g.id, styleId: 'market', position: new TMap.LatLng(g.lat, g.lng), properties: {{ name: g.name }} }})) }});
    marketLayer.on('click', (e) => {{ const g = MARKET_GEOMS.find(x => x.id === e.geometry.id); if (!g) return; info.setPosition(e.geometry.position); info.setContent(marketHtml(g)); info.open(); }});
    const upLayer = new TMap.MultiPolyline({{ map: map, styles: {{{line_styles_js}\n      }}, geometries: UP_LINES.map(l => ({{ id: l.id, styleId: l.styleId, paths: [new TMap.LatLng(l.plat, l.plng), new TMap.LatLng(l.alat, l.alng)] }})) }});
    const downLayer = new TMap.MultiPolyline({{ map: map, styles: {{{line_styles_js}\n      }}, geometries: DOWN_LINES.map(l => ({{ id: l.id, styleId: l.styleId, paths: [new TMap.LatLng(l.plat, l.plng), new TMap.LatLng(l.alat, l.alng)] }})) }});
    const arrowLayer = new TMap.MultiMarker({{ map: map, styles: {{{arrow_styles_js}\n      }}, geometries: [] }});
    function arrowPosAt(a, t) {{ return {{ id: a.id, styleId: a.styleId, position: new TMap.LatLng(a.start[0]+(a.end[0]-a.start[0])*t, a.start[1]+(a.end[1]-a.start[1])*t) }}; }}
    function refreshArrows() {{ const arr = ARROW_META.filter(a => ((a.tier==='up'&&upVisible)||(a.tier==='down'&&downVisible)) && (!focusSid || a.tier!=='up' || a.supplier===focusSid)).map(a => arrowPosAt(a, flowT)); arrowLayer.setGeometries(arr); }}
    refreshArrows();
    map.on('click', () => setFocus(null));
    window.__B = {{
      filter: function() {{
        markers.setGeometries(GEOMS.filter(g => activeCats.has(g.cat) && (!searchTerm || matchesSearch(g))).map(g => ({{ id: g.id, styleId: (focusSid && g.sid !== focusSid) ? 'dim' : g.styleId, position: new TMap.LatLng(g.lat, g.lng), properties: {{ html: g.html, name: g.name, cat: g.cat }} }})));
        if (labelLayer) labelLayer.setGeometries((labelsOn ? GEOMS.filter(g => g.label && activeCats.has(g.cat)) : []).map(g => ({{ id: g.id, styleId: 'label', position: new TMap.LatLng(g.lat, g.lng), content: g.label }})));
      }},
      applyUp: function() {{ upLayer.setGeometries((upVisible ? UP_LINES.filter(l => !focusSid || l.supplier === focusSid) : []).map(l => ({{ id: l.id, styleId: l.styleId, paths: [new TMap.LatLng(l.plat, l.plng), new TMap.LatLng(l.alat, l.alng)] }}))); refreshArrows(); }},
      applyDown: function() {{ downLayer.setGeometries((downVisible && !focusSid ? DOWN_LINES : []).map(l => ({{ id: l.id, styleId: l.styleId, paths: [new TMap.LatLng(l.plat, l.plng), new TMap.LatLng(l.alat, l.alng)] }}))); refreshArrows(); }},
      refreshArrows: refreshArrows,
      toggleLabels: function() {{ if (labelLayer) labelLayer.setGeometries((labelsOn ? GEOMS.filter(g => g.label && activeCats.has(g.cat)) : []).map(g => ({{ id: g.id, styleId: 'label', position: new TMap.LatLng(g.lat, g.lng), content: g.label }}))); }},
      invalidate: function() {{}},
      openSupplier: function(sid) {{ const g = GEOMS.find(x => x.sid === sid) || GEOMS.find(x => String(x.id) === sid); if (!g) return; map.setCenter(new TMap.LatLng(g.lat, g.lng)); map.setZoom(6); info.setPosition(new TMap.LatLng(g.lat, g.lng)); info.setContent(supHtml(g)); info.open(); }},
      fitTo: function (ms) {{ try {{ const b = new TMap.LatLngBounds(); ms.forEach(m => b.extend(new TMap.LatLng(m.lat, m.lng))); map.fitBounds(b, {{ padding: 40 }}); }} catch (e) {{}} }},
      resetView: function () {{ map.setZoom(3); map.setCenter(new TMap.LatLng(28, 112)); }},
      relocalize: function() {{ filter(); localizeGeo(); syncToggleLabels(); }}
    }};
  }}

  if (__USE_TMAP) initTMap(); else initLeaflet();

  // 深链：带 ?supplier=<id> 时自动定位并弹出该供应商基地
  (function () {{
    const sid = new URLSearchParams(location.search).get('supplier');
    if (!sid) return;
    if (window.__B) window.__B.openSupplier(sid);
  }})();

  function flowStep() {{ flowT = (performance.now()/2500) % 1; if (window.__B) window.__B.refreshArrows(); flowRAF = requestAnimationFrame(flowStep); }}
  function toggleFlow(btn) {{ flowOn = !flowOn; btn.classList.toggle('on', flowOn); btn.textContent = T(flowOn ? 'geo.btn.flowStop' : 'geo.btn.flow'); if (flowOn) flowStep(); else {{ cancelAnimationFrame(flowRAF); if (window.__B) window.__B.refreshArrows(); }} }}
  function toggleUp(btn) {{ upVisible = !upVisible; if (window.__B) window.__B.applyUp(); btn.classList.toggle('on', upVisible); btn.textContent = T(upVisible ? 'geo.btn.hideUp' : 'geo.btn.showUp'); }}
  function toggleDown(btn) {{ downVisible = !downVisible; if (window.__B) window.__B.applyDown(); btn.classList.toggle('on', downVisible); btn.textContent = T(downVisible ? 'geo.btn.hideDown' : 'geo.btn.showDown'); }}
  function toggleLabels(btn) {{ labelsOn = !labelsOn; if (window.__B) window.__B.toggleLabels(); btn.classList.toggle('on', labelsOn); btn.textContent = T(labelsOn ? 'geo.btn.labelsHide' : 'geo.btn.labels'); }}

  // 初次本地化（i18n 未就绪时回退中文；就绪/切换语言/译文到达时由事件刷新）
  localizeGeo();
  syncToggleLabels();
  document.addEventListener('i18n:ready', function () {{ localizeGeo(); syncToggleLabels(); }});
  document.addEventListener('i18n:changed', function () {{ if (window.__B && window.__B.relocalize) window.__B.relocalize(); else {{ localizeGeo(); syncToggleLabels(); }} }});
  document.addEventListener('i18n:translated', function () {{ localizeGeo(); }});
</script>
</body>
</html>
"""
    os.makedirs(os.path.dirname(OUT_HTML), exist_ok=True)
    html = html.replace("__TOPNAV_CSS__", TOPNAV_CSS).replace("__TOPNAV__", topnav("../../", "map"))
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print("写出", OUT_HTML)


def main():
    recs, key_ids = build_records()
    write_csv(recs)
    insights = compute_insights(recs, key_ids)
    print("\n=== 洞察摘要 ===")
    print("区域分布:", [(REGION_LABEL.get(r, r), c) for r, c in insights["region_dist"]])
    print(f"大中华区暴露: {insights['gc_share']:.0f}% ({insights['gc']}/{insights['total']})")
    print(f"重点供应商 {insights['n_key']} 家: 单区域 {len(insights['single_region'])} 家={insights['single_region']}")
    print("              多区域", len(insights["multi_region"]), "家=", insights["multi_region"])
    print("估值×地理:", {k: round(v[0], 2) for k, v in insights["verdict_geo"].items()})
    build_html(recs, insights)
    print("完成。")


if __name__ == "__main__":
    main()
