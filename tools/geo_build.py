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
OUT_COMBINED = os.path.join(REPO, "tools", "visualizations", "supplier_combined.html")
DASH_FILE = os.path.join(REPO, "tools", "visualizations", "supplier_dashboard.html")

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


# ---------------------------------------------------------------------------
# 苹果组装厂代表据点（用于绘制「供应商基地 → 组装厂」物流连线）
# 坐标 WGS84，转换 GCJ-02
# ---------------------------------------------------------------------------
ASM_HUBS_WGS = {
    "foxconn": ("郑州(iPhone主力组装)", 113.62604, 34.74882),
    "quanta":   ("桃园( Mac/iPad 组装)", 121.22, 24.99),
    "luxshare": ("东莞( AirPods 组装)", 113.75, 23.02),
    "goertek":  ("潍坊( 声学/ AirPods)", 119.16, 36.71),
}

# 终端市场代表据点（组装厂出货的汇聚点）
MARKETS = [
    ("美国市场", "US", -122.0090, 37.3349, "苹果总部所在地，北美终端市场代表"),
    ("中国市场", "CN", 121.4737, 31.2304, "苹果最大单一消费市场"),
    ("欧洲市场", "DE", 11.5820, 48.1351, "欧洲终端市场代表（慕尼黑）"),
]

def make_arrow_metas(line_geoms, tier, start=0):
    """为每条连线生成一枚带朝向的箭头标记元数据。start 保证 styleId 全局唯一。"""
    metas = []
    for g in line_geoms:
        idx = start + len(metas)
        brg = bearing(g["plat"], g["plng"], g["alat"], g["alng"])
        color = COLORS.get(g["styleId"], "#94a3b8") if tier == "up" else "#7c3aed"
        mid = [(g["plat"] + g["alat"]) / 2.0, (g["plng"] + g["alng"]) / 2.0]
        metas.append({
            "id": f"A{idx}", "styleId": f"A{idx}", "tier": tier,
            "start": [g["plat"], g["plng"]], "end": [g["alat"], g["alng"]],
            "mid": mid, "src": arrow_svg(color, brg),
        })
    return metas

# 品类粗分组（用于地图过滤 UI）
def coarse_cat(c):
    c = c or ""
    if c == "Memory": return "存储"
    if c in ("Foundry", "Semiconductor"): return "半导体/代工"
    if "Display" in c or "Glass" in c or "Touch" in c: return "显示"
    if "Optics" in c or "Optical" in c or "Camera" in c or "CIS" in c: return "光学/影像"
    if c == "OSAT": return "封测"
    if c.startswith("Assembly"): return "组装"
    if "Acoustics" in c: return "声学"
    if "Battery" in c or "Passive" in c: return "电池/被动件"
    if "Enclosure" in c or "Mech" in c: return "结构件"
    if "FPC" in c or "PCB" in c or "Substrate" in c: return "连接器/PCB"
    if "Sensor" in c: return "传感器"
    if "IP" in c or "EDA" in c: return "IP/EDA"
    if "Material" in c: return "材料"
    return "其他"

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
    hubs = {}
    for a, (city, lng, lat) in ASM_HUBS_WGS.items():
        glng, glat = to_gcj02(lng, lat, "CN")
        hubs[a] = (city, glat, glng)
    return sup_to_asms, hubs


def build_records():
    val = load_valuation()
    cat = load_category()
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
            "key": (sid == "apple"),
        })
    return recs, KEY_IDS


def write_csv(recs):
    os.makedirs(os.path.dirname(OUT_DATA), exist_ok=True)
    cols = ["supplier_id", "city", "region", "region_label", "lng_gcj02", "lat_gcj02",
            "produces", "verdict", "market_cap_usd_b", "category", "is_key_supplier"]
    with open(OUT_DATA, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in recs:
            w.writerow([r["supplier_id"], r["city"], r["region"], REGION_LABEL.get(r["region"], r["region"]),
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
    key_recs = [r for r in recs if r["supplier_id"] in key_ids]
    by_sup = {}
    for r in key_recs:
        by_sup.setdefault(r["supplier_id"], set()).add(r["region"])
    single_region = [s for s, regs in by_sup.items() if len(regs) == 1]
    multi_region = [s for s, regs in by_sup.items() if len(regs) >= 2]

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
        "multi_region": sorted(multi_region),
        "verdict_geo": verdict_geo, "cat_region": cat_region,
    }


# ---------------------------------------------------------------------------
# HTML 生成（腾讯地图 GL JS，代理模式，合规）
# ---------------------------------------------------------------------------
COLORS = {"低估": "#2563eb", "高估": "#dc2626", "困境": "#d97706",
          "基准": "#111827", "其他": "#94a3b8"}
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

def build_geo_data(recs, insights):
    """构建地图所需的全部数据（标记 / 连线 / 箭头 / 侧栏面板），供 build_html 与 build_combined 复用。"""
    styles = {}
    for name, color in COLORS.items():
        styles[name] = marker_svg(color)

    geometries = []
    for i, r in enumerate(recs):
        st = style_for(r)
        vshort = st
        mcap = r["mcap"]
        mcap_s = f"{mcap:.0f}" if isinstance(mcap, (int, float)) else "-"
        html = (f"<div style='font-size:13px;line-height:1.5'>"
                f"<b>{r['supplier_id']}</b> · {r['city']}<br>"
                f"区域：{REGION_LABEL.get(r['region'], r['region'])}<br>"
                f"内容：{r['produces']}<br>"
                f"判定：{EMOJI.get(vshort,'')} {r['verdict']}<br>"
                f"市值：{mcap_s} 十亿美元</div>"
                f"<div style='margin-top:6px'>"
                f"<a href='../../index.html?focus=S:{r['supplier_id']}' target='_blank' style='color:#2563eb'>在图谱中查看 →</a>"
                f" &nbsp; <a href='../../dist/apple_supply_chain_report.html#sec-suppliers' target='_blank' style='color:#2563eb'>在报告中查看 →</a>"
                f"</div>")
        geometries.append({
            "id": str(i), "styleId": st, "sid": r["supplier_id"],
            "lat": r["lat"], "lng": r["lng"],
            "html": html, "name": f"{r['supplier_id']} · {r['city']}",
            "cat": r["coarse"],
        })

    # 侧栏洞察 HTML
    rd = "".join(
        f"<div class='bar-row'><span class='bar-label'>{REGION_LABEL.get(rg, rg)}</span>"
        f"<span class='bar-track'><span class='bar-fill' style='width:{cnt/insights['region_dist'][0][1]*100:.0f}%'></span></span>"
        f"<span class='bar-num'>{cnt}</span></div>"
        for rg, cnt in insights["region_dist"]
    )
    vg = "".join(
        f"<div class='kv'><span>{k}</span><b>{v[0]:.2f} 区域/家</b><span class='sub'>({v[1]} 家)</span></div>"
        for k, v in sorted(insights["verdict_geo"].items(), key=lambda x: -x[1][0])
    )
    cr = "".join(f"<span class='chip'>{c}</span>" for c in insights["single_region"])

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
    market_coords = []
    for mname, mregion, mlng, mlat, mdesc in MARKETS:
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
    for i, (mname, mregion, mlng, mlat, mdesc) in enumerate(MARKETS):
        glng, glat = to_gcj02(mlng, mlat, mregion)
        html = (f"<div style='font-size:13px;line-height:1.5'>"
                f"<b>{mname}</b><br>区域：{REGION_LABEL.get(mregion, mregion)}<br>{mdesc}</div>")
        market_geoms.append({"id": f"M{i}", "lat": round(glat, 5), "lng": round(glng, 5),
                             "html": html, "name": mname})
    arrow_metas = make_arrow_metas(line_geoms, "up", start=0) + make_arrow_metas(down_geoms, "down", start=len(line_geoms))

    # ---- 品类过滤 ----
    all_cats = sorted({r["coarse"] for r in recs})
    cat_chips = "".join(f"<button class='fbtn on' data-cat='{c}'>{c}</button>" for c in all_cats)
    line_styles_js = ",\n".join(
        f"        {name}: new TMap.PolylineStyle({{ color: 0x{h}, width: 1.5 }})"
        for name, h in [("低估", "2563eb"), ("高估", "dc2626"), ("困境", "d97706"),
                        ("其他", "94a3b8"), ("downstream", "7c3aed")]
    )
    arrow_styles_js = ",\n".join(
        f"        {m['id']}: new TMap.MarkerStyle({{ width: 16, height: 16, src: '{m['src']}' }})"
        for m in arrow_metas
    )
    arrow_meta_list = [{'id': m['id'], 'styleId': m['styleId'], 'tier': m['tier'],
                        'start': m['start'], 'end': m['end'], 'mid': m['mid']} for m in arrow_metas]

    panel = f"""
    <div id="panel">
      <h1>苹果供应商 · 生产基地地理洞察</h1>
      <p class="muted">数据：各供应商公开资料整理的生产基地/总部（城市级近似坐标，GCJ-02）。标记按估值判定着色。</p>

      <h2>① 生产基地区域分布（共 {insights['total']} 个点）</h2>
      <div class="bars">{rd}</div>
      <div class="hl">大中华区（中国大陆 + 中国台湾）生产基地占比 <b>{insights['gc_share']:.0f}%</b>（{insights['gc']}/{insights['total']}）— 地缘/关税/物流集中风险的关键指标。</div>

      <h2>② 重点供应商区域覆盖与集中度风险</h2>
      <p>在 {insights['n_key']} 家重点供应商中，<b>{len(insights['single_region'])} 家</b>所有基地集中在单一区域（抗风险弱），<b>{len(insights['multi_region'])} 家</b>跨多区域布局（分散）：</p>
      <div class="chips"><span class="chip-h">单区域：</span>{cr}</div>

      <h2>③ 估值 × 地理（平均覆盖区域数/家）</h2>
      <div class="kvs">{vg}</div>
      <p class="muted">说明：覆盖区域越多通常意味着产能分散、地缘韧性更强；可结合估值判定观察“被低估是否伴随更强的地理韧性”。</p>

      <h2>④ 图例</h2>
      <div class="legend">
        <span><i style="background:{COLORS['低估']}"></i>低估</span>
        <span><i style="background:{COLORS['高估']}"></i>高估</span>
        <span><i style="background:{COLORS['困境']}"></i>困境(亏损)</span>
        <span><i style="background:{COLORS['基准']}"></i>苹果(基准)</span>
        <span><i style="background:{COLORS['其他']}"></i>其他供应商</span>
        <span><i style="background:#7c3aed"></i>下游(组装→市场)</span>
        <span><i style="background:#f59e0b"></i>终端市场</span>
      </div>
      <p class="muted">点击地图标记查看生产基地 / 市场详情。</p>

      <h2>⑤ 供应链物流连线</h2>
      <p class="muted">蓝/红/橙线 = 供应商基地 → 苹果组装厂（按估值着色）；紫色线 = 组装厂 → 终端市场（美/中/欧）。连线依据图谱 edge 链推导，箭头指示流动方向。</p>
      <div class="chips">
        <button id="upToggle" class="fbtn on" onclick="toggleUp(this)">隐藏供应连线</button>
        <button id="downToggle" class="fbtn on" onclick="toggleDown(this)">隐藏下游连线</button>
        <button id="flowToggle" class="fbtn" onclick="toggleFlow(this)">▶ 流动动画</button>
      </div>

      <h2>⑥ 按品类过滤</h2>
      <div class="chips" id="catFilter">{cat_chips}<button class="fbtn on" data-cat="__ALL__">全部</button></div>
      <p class="muted">点击品类标签可显示/隐藏对应生产基地（含其余供应商）。</p>

      <h2>⑦ 终端市场（汇聚点）</h2>
      <div class="chips"><span class="chip gold">美国 · 库比蒂诺</span><span class="chip gold">中国 · 上海</span><span class="chip gold">欧洲 · 慕尼黑</span></div>
      <p class="muted">组装厂经紫色下游连线向三大终端市场出货，形成「供应商→组装→市场」全链路视图。</p>
    </div>
    """

    return {
        "styles": styles, "geometries": geometries, "panel": panel,
        "all_cats": all_cats, "line_styles_js": line_styles_js,
        "arrow_styles_js": arrow_styles_js, "arrow_meta_list": arrow_meta_list,
        "market_geoms": market_geoms, "line_geoms": line_geoms, "down_geoms": down_geoms,
    }


def build_html(recs, insights):
    G = build_geo_data(recs, insights)
    styles = G["styles"]; geometries = G["geometries"]; panel = G["panel"]
    all_cats = G["all_cats"]; line_styles_js = G["line_styles_js"]
    arrow_styles_js = G["arrow_styles_js"]; arrow_meta_list = G["arrow_meta_list"]
    market_geoms = G["market_geoms"]; line_geoms = G["line_geoms"]; down_geoms = G["down_geoms"]
    styles_js = ",\n".join(f"        {name}: new TMap.MarkerStyle({{ width: 22, height: 22, src: '{styles[name]}' }})" for name in COLORS)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>苹果供应商生产基地地理洞察</title>
<style>
  html, body {{ margin: 0; padding: 0; height: 100%; font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif; }}
  #map {{ position: absolute; top: 52px; left: 0; right: 0; bottom: 0; }}
__TOPNAV_CSS__
  #panel {{
    position: absolute; top: 64px; right: 12px; width: 340px; max-height: calc(100vh - 76px);
    overflow-y: auto; background: rgba(255,255,255,0.96); border-radius: 12px;
    box-shadow: 0 8px 30px rgba(0,0,0,0.18); padding: 16px 18px; font-size: 13px; color: #1f2937; z-index: 1000;
  }}
  #panel h1 {{ font-size: 16px; margin: 0 0 4px; }}
  #panel h2 {{ font-size: 13px; margin: 16px 0 6px; color: #111827; }}
  .muted {{ color: #6b7280; font-size: 11px; line-height: 1.5; }}
  .bars {{ display: flex; flex-direction: column; gap: 4px; }}
  .bar-row {{ display: flex; align-items: center; gap: 6px; }}
  .bar-label {{ width: 64px; flex: none; font-size: 12px; }}
  .bar-track {{ flex: 1; background: #eef2f7; border-radius: 4px; height: 14px; overflow: hidden; }}
  .bar-fill {{ display: block; height: 100%; background: linear-gradient(90deg,#3b82f6,#2563eb); }}
  .bar-num {{ width: 24px; text-align: right; font-size: 12px; }}
  .hl {{ margin-top: 8px; padding: 8px 10px; background: #fff7ed; border-left: 3px solid #f59e0b; border-radius: 6px; font-size: 12px; }}
  .hl b {{ font-size: 14px; color: #b45309; }}
  .chips {{ display: flex; flex-wrap: wrap; gap: 4px; margin-top: 6px; }}
  .chip {{ background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; border-radius: 999px; padding: 2px 8px; font-size: 11px; }}
  .chip-h {{ color: #6b7280; align-self: center; }}
  .kvs {{ display: flex; flex-direction: column; gap: 3px; }}
  .kv {{ display: flex; align-items: baseline; gap: 6px; font-size: 12px; }}
  .kv b {{ color: #1d4ed8; }}
  .kv .sub {{ color: #9ca3af; font-size: 11px; }}
  .legend {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 6px; font-size: 12px; }}
  .legend span {{ display: flex; align-items: center; gap: 4px; }}
  .legend i {{ width: 12px; height: 12px; border-radius: 50%; display: inline-block; }}
  .fbtn {{ cursor: pointer; border: 1px solid #cbd5e1; background: #f8fafc; color: #475569; border-radius: 999px; padding: 3px 10px; font-size: 11px; margin: 2px 0; }}
  .fbtn.on {{ background: #2563eb; color: #fff; border-color: #2563eb; }}
  .chip.gold {{ background: #fffbeb; color: #b45309; border: 1px solid #fde68a; }}
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
  const __HEX = {{ '低估':'#2563eb', '高估':'#dc2626', '困境':'#d97706', '基准':'#111827', '其他':'#94a3b8', 'market':'#f59e0b', 'downstream':'#7c3aed' }};

  const RAW = {json.dumps(geometries, ensure_ascii=False)};
  const GEOMS = RAW.map(r => ({{ id: r.id, styleId: r.styleId, sid: r.sid, lat: r.lat, lng: r.lng, html: r.html, name: r.name, cat: r.cat }}));
  const ALL_CATS = {json.dumps(all_cats, ensure_ascii=False)};
  let activeCats = new Set(ALL_CATS);
  let upVisible = true, downVisible = true, flowOn = false, flowRAF = null, flowT = 0.5;

  const MARKET_RAW = {json.dumps(market_geoms, ensure_ascii=False)};
  const MARKET_GEOMS = MARKET_RAW.map(r => ({{ id: r.id, lat: r.lat, lng: r.lng, html: r.html, name: r.name }}));
  const UP_RAW = {json.dumps(line_geoms, ensure_ascii=False)};
  const UP_LINES = UP_RAW.map(r => ({{ id: r.id, styleId: r.styleId, plat: r.plat, plng: r.plng, alat: r.alat, alng: r.alng }}));
  const DOWN_RAW = {json.dumps(down_geoms, ensure_ascii=False)};
  const DOWN_LINES = DOWN_RAW.map(r => ({{ id: r.id, styleId: r.styleId, plat: r.plat, plng: r.plng, alat: r.alat, alng: r.alng }}));
  const ARROW_META = {json.dumps(arrow_meta_list, ensure_ascii=False)};

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

  // ---------- Leaflet 后端（默认，静态托管可用） ----------
  function initLeaflet() {{
    const map = L.map('map', {{ zoomControl: true }}).setView([28, 112], 3);
    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{ maxZoom: 19, attribution: '© OpenStreetMap' }}).addTo(map);
    const supLayer = L.layerGroup().addTo(map);
    const upLayer = L.layerGroup().addTo(map);
    const downLayer = L.layerGroup().addTo(map);
    const arrowLayer = L.layerGroup().addTo(map);
    const marketLayer = L.layerGroup().addTo(map);
    const colorOf = (s) => __HEX[s] || '#94a3b8';
    function renderSuppliers() {{
      supLayer.clearLayers();
      GEOMS.filter(g => activeCats.has(g.cat)).forEach(g => {{
        const m = L.circleMarker([g.lat, g.lng], {{ radius: 7, color: '#fff', weight: 2, fillColor: colorOf(g.styleId), fillOpacity: 1 }});
        m.bindPopup(g.html); supLayer.addLayer(m);
      }});
    }}
    function renderMarkets() {{
      marketLayer.clearLayers();
      MARKET_GEOMS.forEach(g => {{
        const m = L.circleMarker([g.lat, g.lng], {{ radius: 8, color: '#fff', weight: 2, fillColor: colorOf('market'), fillOpacity: 1 }});
        m.bindPopup(g.html); marketLayer.addLayer(m);
      }});
    }}
    function renderLines() {{
      upLayer.clearLayers(); downLayer.clearLayers();
      if (upVisible) UP_LINES.forEach(l => upLayer.addLayer(L.polyline([[l.plat, l.plng], [l.alat, l.alng]], {{ color: colorOf(l.styleId), weight: 1.5, opacity: 0.7 }})));
      if (downVisible) DOWN_LINES.forEach(l => downLayer.addLayer(L.polyline([[l.plat, l.plng], [l.alat, l.alng]], {{ color: colorOf(l.styleId), weight: 1.5, opacity: 0.7 }})));
    }}
    function renderArrows() {{
      arrowLayer.clearLayers();
      ARROW_META.filter(a => (a.tier==='up'&&upVisible) || (a.tier==='down'&&downVisible)).forEach(a => {{
        const lat = a.start[0] + (a.end[0]-a.start[0])*flowT;
        const lng = a.start[1] + (a.end[1]-a.start[1])*flowT;
        const ang = Math.atan2(a.end[0]-a.start[0], a.end[1]-a.start[1]) * 180 / Math.PI;
        const ic = L.divIcon({{ className:'', html: "<div style='transform:rotate("+ang.toFixed(1)+"deg);color:"+colorOf(a.styleId)+";font-size:14px;line-height:1'>➤</div>", iconSize:[14,14], iconAnchor:[7,7] }});
        arrowLayer.addLayer(L.marker([lat, lng], {{ icon: ic }}));
      }});
    }}
    renderSuppliers(); renderMarkets(); renderLines(); renderArrows();
    window.__B = {{
      filter: renderSuppliers,
      applyUp: function() {{ renderLines(); renderArrows(); }},
      applyDown: function() {{ renderLines(); renderArrows(); }},
      refreshArrows: renderArrows,
      invalidate: function() {{ map.invalidateSize(); }},
      openSupplier: function(sid) {{
        const g = GEOMS.find(x => x.sid === sid) || GEOMS.find(x => String(x.id) === sid);
        if (!g) return;
        map.setView([g.lat, g.lng], 6);
        L.popup().setLatLng([g.lat, g.lng]).setContent(g.html).openOn(map);
      }}
    }};
  }}

  // ---------- 腾讯地图后端（配置了真实代理 + Key 时） ----------
  function initTMap() {{
    const map = new TMap.Map('map', {{ zoom: 3, center: new TMap.LatLng(28, 112) }});
    const markers = new TMap.MultiMarker({{ map: map, styles: {{{styles_js}\n      }}, geometries: GEOMS.map(g => ({{ id: g.id, styleId: g.styleId, position: new TMap.LatLng(g.lat, g.lng), properties: {{ html: g.html, name: g.name, cat: g.cat }} }})) }});
    const info = new TMap.InfoWindow({{ map: map, position: new TMap.LatLng(28, 112), content: '', visible: false }});
    markers.on('click', (e) => {{ const g = GEOMS.find(x => x.id === e.geometry.id); if (!g) return; info.setPosition(e.geometry.position); info.setContent(g.properties.html); info.open(); }});
    const marketLayer = new TMap.MultiMarker({{ map: map, styles: {{ market: new TMap.MarkerStyle({{ width: 24, height: 24, src: '{market_svg()}' }}) }}, geometries: MARKET_GEOMS.map(g => ({{ id: g.id, styleId: 'market', position: new TMap.LatLng(g.lat, g.lng), properties: {{ html: g.html, name: g.name }} }})) }});
    marketLayer.on('click', (e) => {{ const g = MARKET_GEOMS.find(x => x.id === e.geometry.id); if (!g) return; info.setPosition(e.geometry.position); info.setContent(g.properties.html); info.open(); }});
    const upLayer = new TMap.MultiPolyline({{ map: map, styles: {{{line_styles_js}\n      }}, geometries: UP_LINES.map(l => ({{ id: l.id, styleId: l.styleId, paths: [new TMap.LatLng(l.plat, l.plng), new TMap.LatLng(l.alat, l.alng)] }})) }});
    const downLayer = new TMap.MultiPolyline({{ map: map, styles: {{{line_styles_js}\n      }}, geometries: DOWN_LINES.map(l => ({{ id: l.id, styleId: l.styleId, paths: [new TMap.LatLng(l.plat, l.plng), new TMap.LatLng(l.alat, l.alng)] }})) }});
    const arrowLayer = new TMap.MultiMarker({{ map: map, styles: {{{arrow_styles_js}\n      }}, geometries: [] }});
    function arrowPosAt(a, t) {{ return {{ id: a.id, styleId: a.styleId, position: new TMap.LatLng(a.start[0]+(a.end[0]-a.start[0])*t, a.start[1]+(a.end[1]-a.start[1])*t) }}; }}
    function refreshArrows() {{ const arr = ARROW_META.filter(a => (a.tier==='up'&&upVisible)||(a.tier==='down'&&downVisible)).map(a => arrowPosAt(a, flowT)); arrowLayer.setGeometries(arr); }}
    refreshArrows();
    window.__B = {{
      filter: function() {{ markers.setGeometries(GEOMS.filter(g => activeCats.has(g.cat)).map(g => ({{ id: g.id, styleId: g.styleId, position: new TMap.LatLng(g.lat, g.lng), properties: {{ html: g.html, name: g.name, cat: g.cat }} }}))); }},
      applyUp: function() {{ upLayer.setGeometries(upVisible ? UP_LINES.map(l => ({{ id: l.id, styleId: l.styleId, paths: [new TMap.LatLng(l.plat, l.plng), new TMap.LatLng(l.alat, l.alng)] }})) : []); refreshArrows(); }},
      applyDown: function() {{ downLayer.setGeometries(downVisible ? DOWN_LINES.map(l => ({{ id: l.id, styleId: l.styleId, paths: [new TMap.LatLng(l.plat, l.plng), new TMap.LatLng(l.alat, l.alng)] }})) : []); refreshArrows(); }},
      refreshArrows: refreshArrows,
      invalidate: function() {{}},
      openSupplier: function(sid) {{ const g = GEOMS.find(x => x.sid === sid) || GEOMS.find(x => String(x.id) === sid); if (!g) return; map.setCenter(new TMap.LatLng(g.lat, g.lng)); map.setZoom(6); info.setPosition(new TMap.LatLng(g.lat, g.lng)); info.setContent(g.html); info.open(); }}
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
  function toggleFlow(btn) {{ flowOn = !flowOn; btn.classList.toggle('on', flowOn); btn.textContent = flowOn ? '⏸ 停止动画' : '▶ 流动动画'; if (flowOn) flowStep(); else {{ cancelAnimationFrame(flowRAF); flowT = 0.5; if (window.__B) window.__B.refreshArrows(); }} }}
  function toggleUp(btn) {{ upVisible = !upVisible; if (window.__B) window.__B.applyUp(); btn.classList.toggle('on', upVisible); btn.textContent = upVisible ? '隐藏供应连线' : '显示供应连线'; }}
  function toggleDown(btn) {{ downVisible = !downVisible; if (window.__B) window.__B.applyDown(); btn.classList.toggle('on', downVisible); btn.textContent = downVisible ? '隐藏下游连线' : '显示下游连线'; }}
</script>
</body>
</html>
"""
    os.makedirs(os.path.dirname(OUT_HTML), exist_ok=True)
    html = html.replace("__TOPNAV_CSS__", TOPNAV_CSS).replace("__TOPNAV__", topnav("../../", "map"))
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print("写出", OUT_HTML)


def build_combined(recs, insights):
    """生成「融合版」单页：顶部导航在【基本面看板】与【地理供应链地图】间切换。
    地图懒加载——仅首次切到地图页才 new TMap.Map，避免隐藏容器 0 尺寸导致静默失败。"""
    G = build_geo_data(recs, insights)

    dash = open(DASH_FILE, encoding="utf-8").read()
    dash_markup = dash.split("<body>", 1)[1].rsplit("<script>", 1)[0]
    # 看板文件自带统一导航条；嵌入融合页后由融合页自身的导航接管，移除避免重复
    dash_markup = re.sub(r"<nav class='wb-topnav'>.*?</nav>", "", dash_markup, flags=re.S)
    # 移除看板自带的 Umami 统计片段及其注释（避免与融合页统一注入的 analytics_js() 重复计数）
    dash_markup = re.sub(r"<!--.*?访问统计.*?-->", "", dash_markup, flags=re.S)
    dash_markup = re.sub(r"<script>.*?websiteId.*?</script>", "", dash_markup, flags=re.S)
    # 只取看板里【最后一个】<script> 块（即数据脚本），避免把自带的 Umami 片段一并抓进来
    _scripts = re.findall(r"<script>(.*?)</script>", dash, re.S)
    dash_script = _scripts[-1] if _scripts else ""

    marker_styles_js = ",\n".join(
        "        %s: new TMap.MarkerStyle({ width: 22, height: 22, src: '%s' })" % (name, G["styles"][name])
        for name in COLORS
    )

    COMBINED = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>苹果供应链全景 · 基本面 + 地理</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<script type="text/javascript">
  window._TMapSecurityConfig = {
    serviceHost: 'http://127.0.0.1:__WB_HTTP_PORT__/_TMapService/_wbt/__WB_TMAP_SECRET__',
  };
</script>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://map.qq.com/api/gljs?v=1.exp"></script>
<style>
  :root{ --bg:#f5f7fa; --card:#fff; --ink:#1f2937; --muted:#6b7280; --blue:#2563eb; --red:#dc2626; --green:#16a34a; --amber:#d97706; --line:#e5e7eb; --soft:#eef2f7; }
  html,body{margin:0;padding:0;height:100%;font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;background:var(--bg);color:var(--ink);line-height:1.5;}
  __TOPNAV_CSS__
  /* 融合页的二级标签栏：位于统一顶部导航之下，负责看板 / 地图视图内切换 */
  #appsub{position:fixed;top:52px;left:0;right:0;height:46px;display:flex;align-items:center;gap:10px;padding:0 18px;background:rgba(15,23,42,.96);color:#fff;z-index:2900;box-shadow:0 1px 6px rgba(0,0,0,.2);}
  #appsub button{background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.25);color:#e5e7eb;border-radius:8px;padding:7px 16px;font-size:13.5px;cursor:pointer;transition:.15s;}
  #appsub button:hover{background:rgba(255,255,255,.22);}
  #appsub button.active{background:#fff;color:#1e3a8a;font-weight:700;border-color:#fff;}
  #appsub .hint{margin-left:auto;font-size:12px;color:#cbd5e1;}
  #view-dash{display:block;position:absolute;top:98px;left:0;right:0;bottom:0;overflow:auto;}
  #view-geo{display:none;position:absolute;top:98px;left:0;right:0;bottom:0;overflow:hidden;}
  .wrap{max-width:1180px;margin:0 auto;padding:24px 20px 60px;}
  .cards{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:22px 0 8px;}
  .card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px;box-shadow:0 1px 3px rgba(0,0,0,.04);}
  .card .v{font-size:27px;font-weight:800;line-height:1.1;}
  .card .l{font-size:12.5px;color:var(--muted);margin-top:4px;}
  .card.blue .v{color:var(--blue);} .card.red .v{color:var(--red);} .card.green .v{color:var(--green);} .card.amber .v{color:var(--amber);}
  section{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:20px 22px;margin:18px 0;box-shadow:0 1px 3px rgba(0,0,0,.04);}
  section h2{margin:0 0 4px;font-size:17px;}
  section .sub{color:var(--muted);font-size:13px;margin:0 0 14px;}
  .chart-box{position:relative;width:100%;}
  .h-440{height:440px;} .h-380{height:380px;} .h-360{height:360px;}
  .grid2{display:grid;grid-template-columns:1fr 1fr;gap:18px;}
  .quad{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:14px;}
  .quad div{border-left:4px solid;padding:8px 12px;background:var(--soft);border-radius:0 8px 8px 0;font-size:12.8px;}
  table{width:100%;border-collapse:collapse;font-size:12.3px;margin-top:6px;}
  th,td{padding:7px 9px;border-bottom:1px solid var(--line);text-align:right;}
  th:first-child,td:first-child{text-align:left;}
  thead th{background:var(--soft);color:var(--muted);font-weight:600;position:sticky;top:0;}
  .tag{display:inline-block;padding:2px 9px;border-radius:20px;font-size:11.5px;font-weight:700;color:#fff;}
  .t-under{background:var(--blue);} .t-over{background:var(--red);} .t-fair{background:var(--green);} .t-warn{background:var(--amber);}
  .note{font-size:11.5px;color:var(--muted);margin-top:10px;}
  .legend{display:flex;flex-wrap:wrap;gap:14px;margin-top:10px;font-size:12.5px;color:var(--muted);}
  .legend span{display:inline-flex;align-items:center;gap:6px;}
  @media(max-width:880px){.cards{grid-template-columns:repeat(2,1fr);}.grid2{grid-template-columns:1fr;}}
  #view-geo{display:none;}
  .geo-view{position:relative;height:100%;}
  #map{width:100%;height:100%;}
  #panel{position:absolute;top:12px;right:12px;width:340px;max-height:calc(100vh - 78px);overflow-y:auto;background:rgba(255,255,255,0.96);border-radius:12px;box-shadow:0 8px 30px rgba(0,0,0,0.18);padding:16px 18px;font-size:13px;color:#1f2937;z-index:1000;}
  #panel h1{font-size:16px;margin:0 0 4px;}
  #panel h2{font-size:13px;margin:16px 0 6px;color:#111827;}
  .muted{color:#6b7280;font-size:11px;line-height:1.5;}
  .bars{display:flex;flex-direction:column;gap:4px;}
  .bar-row{display:flex;align-items:center;gap:6px;}
  .bar-label{width:64px;flex:none;font-size:12px;}
  .bar-track{flex:1;background:#eef2f7;border-radius:4px;height:14px;overflow:hidden;}
  .bar-fill{display:block;height:100%;background:linear-gradient(90deg,#3b82f6,#2563eb);}
  .bar-num{width:24px;text-align:right;font-size:12px;}
  .hl{margin-top:8px;padding:8px 10px;background:#fff7ed;border-left:3px solid #f59e0b;border-radius:6px;font-size:12px;}
  .hl b{font-size:14px;color:#b45309;}
  .chips{display:flex;flex-wrap:wrap;gap:4px;margin-top:6px;}
  .chip{background:#fef2f2;color:#b91c1c;border:1px solid #fecaca;border-radius:999px;padding:2px 8px;font-size:11px;}
  .chip-h{color:#6b7280;align-self:center;}
  .kvs{display:flex;flex-direction:column;gap:3px;}
  .kv{display:flex;align-items:baseline;gap:6px;font-size:12px;}
  .kv b{color:#1d4ed8;}
  .kv .sub{color:#9ca3af;font-size:11px;}
  .legend{display:flex;flex-wrap:wrap;gap:10px;margin-top:6px;font-size:12px;}
  .legend span{display:flex;align-items:center;gap:4px;}
  .legend i{width:12px;height:12px;border-radius:50%;display:inline-block;}
  .fbtn{cursor:pointer;border:1px solid #cbd5e1;background:#f8fafc;color:#475569;border-radius:999px;padding:3px 10px;font-size:11px;margin:2px 0;}
  .fbtn.on{background:#2563eb;color:#fff;border-color:#2563eb;}
  .chip.gold{background:#fffbeb;color:#b45309;border:1px solid #fde68a;}
</style>
</head>
<body>
__TOPNAV__
<div id="appsub">
  <button data-tab="dash" class="active" onclick="switchTab('dash')">📊 基本面看板</button>
  <button data-tab="geo" onclick="switchTab('geo')">🗺️ 地理供应链地图</button>
  <span class="hint">估值 × 舆情 × 生产基地 × 物流全链路</span>
</div>
__ANALYTICS__

<div id="view-dash">
__DASH_MARKUP__
</div>

<div id="view-geo">
  <div class="geo-view">
    <div id="map"></div>
__PANEL__
  </div>
</div>

<script>
__DASH_SCRIPT__
</script>

<script>
/* ===== 地理供应链地图（懒加载：首次切到地图页才初始化，避免 0 尺寸静默失败）===== */
// 后端选择：serviceHost 仍为本地 127.0.0.1（未配腾讯代理）时用 Leaflet（免 Key、静态托管可用），
// 配了真实代理 + Key 时保留腾讯地图 GL 原样式。
const __SH2 = 'http://127.0.0.1:__WB_HTTP_PORT__/_TMapService/_wbt/__WB_TMAP_SECRET__';
const __USE_TMAP2 = !__SH2.includes('127.0.0.1') && typeof TMap !== 'undefined';
const __HEX2 = { '低估':'#2563eb', '高估':'#dc2626', '困境':'#d97706', '基准':'#111827', '其他':'#94a3b8', 'market':'#f59e0b', 'downstream':'#7c3aed' };

const RAW = __RAW__;
const GEOMS = RAW.map(r => ({ id: r.id, styleId: r.styleId, sid: r.sid, lat: r.lat, lng: r.lng, html: r.html, name: r.name, cat: r.cat }));
const ALL_CATS = __ALL_CATS__;
let activeCats = new Set(ALL_CATS);
let upVisible = true, downVisible = true, flowOn = false, flowRAF = null, flowT = 0.5;
function applyFilter(){ if(window.__B) window.__B.filter(); }
document.querySelectorAll('.fbtn[data-cat]').forEach(b => {
  b.addEventListener('click', () => {
    const c = b.dataset.cat;
    if (c === '__ALL__') { activeCats = new Set(ALL_CATS); }
    else { if (activeCats.has(c)) activeCats.delete(c); else activeCats.add(c); }
    document.querySelectorAll('.fbtn[data-cat]').forEach(x => {
      const cc = x.dataset.cat;
      const on = cc === '__ALL__' ? activeCats.size === ALL_CATS.length : activeCats.has(cc);
      x.classList.toggle('on', on);
    });
    applyFilter();
  });
});
const MARKET_RAW = __MARKET_RAW__;
const MARKET_GEOMS = MARKET_RAW.map(r => ({ id: r.id, lat: r.lat, lng: r.lng, html: r.html, name: r.name }));
const UP_RAW = __UP_RAW__;
const UP_LINES = UP_RAW.map(r => ({ id: r.id, styleId: r.styleId, plat: r.plat, plng: r.plng, alat: r.alat, alng: r.alng }));
const DOWN_RAW = __DOWN_RAW__;
const DOWN_LINES = DOWN_RAW.map(r => ({ id: r.id, styleId: r.styleId, plat: r.plat, plng: r.plng, alat: r.alat, alng: r.alng }));
const ARROW_META = __ARROW_META__;

// ---------- Leaflet 后端（默认，静态托管可用） ----------
function initLeaflet2() {
  const map = L.map('map', { zoomControl: true }).setView([28, 112], 3);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '© OpenStreetMap' }).addTo(map);
  const supLayer = L.layerGroup().addTo(map);
  const upLayer = L.layerGroup().addTo(map);
  const downLayer = L.layerGroup().addTo(map);
  const arrowLayer = L.layerGroup().addTo(map);
  const marketLayer = L.layerGroup().addTo(map);
  const colorOf = (s) => __HEX2[s] || '#94a3b8';
  function renderSuppliers() {
    supLayer.clearLayers();
    GEOMS.filter(g => activeCats.has(g.cat)).forEach(g => {
      const m = L.circleMarker([g.lat, g.lng], { radius: 7, color: '#fff', weight: 2, fillColor: colorOf(g.styleId), fillOpacity: 1 });
      m.bindPopup(g.html); supLayer.addLayer(m);
    });
  }
  function renderMarkets() {
    marketLayer.clearLayers();
    MARKET_GEOMS.forEach(g => {
      const m = L.circleMarker([g.lat, g.lng], { radius: 8, color: '#fff', weight: 2, fillColor: colorOf('market'), fillOpacity: 1 });
      m.bindPopup(g.html); marketLayer.addLayer(m);
    });
  }
  function renderLines() {
    upLayer.clearLayers(); downLayer.clearLayers();
    if (upVisible) UP_LINES.forEach(l => upLayer.addLayer(L.polyline([[l.plat, l.plng], [l.alat, l.alng]], { color: colorOf(l.styleId), weight: 1.5, opacity: 0.7 })));
    if (downVisible) DOWN_LINES.forEach(l => downLayer.addLayer(L.polyline([[l.plat, l.plng], [l.alat, l.alng]], { color: colorOf(l.styleId), weight: 1.5, opacity: 0.7 })));
  }
  function renderArrows() {
    arrowLayer.clearLayers();
    ARROW_META.filter(a => (a.tier==='up'&&upVisible) || (a.tier==='down'&&downVisible)).forEach(a => {
      const lat = a.start[0] + (a.end[0]-a.start[0])*flowT;
      const lng = a.start[1] + (a.end[1]-a.start[1])*flowT;
      const ang = Math.atan2(a.end[0]-a.start[0], a.end[1]-a.start[1]) * 180 / Math.PI;
      const ic = L.divIcon({ className:'', html: "<div style='transform:rotate("+ang.toFixed(1)+"deg);color:"+colorOf(a.styleId)+";font-size:14px;line-height:1'>➤</div>", iconSize:[14,14], iconAnchor:[7,7] });
      arrowLayer.addLayer(L.marker([lat, lng], { icon: ic }));
    });
  }
  renderSuppliers(); renderMarkets(); renderLines(); renderArrows();
  window.__B = {
    filter: renderSuppliers,
    applyUp: function() { renderLines(); renderArrows(); },
    applyDown: function() { renderLines(); renderArrows(); },
    refreshArrows: renderArrows,
    invalidate: function() { map.invalidateSize(); },
    openSupplier: function(sid) {
      const g = GEOMS.find(x => x.sid === sid) || GEOMS.find(x => String(x.id) === sid);
      if (!g) return;
      map.setView([g.lat, g.lng], 6);
      L.popup().setLatLng([g.lat, g.lng]).setContent(g.html).openOn(map);
    }
  };
}

// ---------- 腾讯地图后端（配置了真实代理 + Key 时） ----------
function initTMap2() {
  const map = new TMap.Map('map', { zoom: 3, center: new TMap.LatLng(28, 112) });
  const markers = new TMap.MultiMarker({ map: map, styles: { __MARKER_STYLES__ }, geometries: GEOMS.map(g => ({ id: g.id, styleId: g.styleId, position: new TMap.LatLng(g.lat, g.lng), properties: { html: g.html, name: g.name, cat: g.cat } })) });
  const info = new TMap.InfoWindow({ map: map, position: new TMap.LatLng(28, 112), content: '', visible: false });
  markers.on('click', (e) => { const g = GEOMS.find(x => x.id === e.geometry.id); if (!g) return; info.setPosition(e.geometry.position); info.setContent(g.properties.html); info.open(); });
  const marketLayer = new TMap.MultiMarker({ map: map, styles: { market: new TMap.MarkerStyle({ width: 24, height: 24, src: '__MARKET_SVG__' }) }, geometries: MARKET_GEOMS.map(g => ({ id: g.id, styleId: 'market', position: new TMap.LatLng(g.lat, g.lng), properties: { html: g.html, name: g.name } })) });
  marketLayer.on('click', (e) => { const g = MARKET_GEOMS.find(x => x.id === e.geometry.id); if (!g) return; info.setPosition(e.geometry.position); info.setContent(g.properties.html); info.open(); });
  const upLayer = new TMap.MultiPolyline({ map: map, styles: { __LINE_STYLES__ }, geometries: UP_LINES.map(l => ({ id: l.id, styleId: l.styleId, paths: [new TMap.LatLng(l.plat, l.plng), new TMap.LatLng(l.alat, l.alng)] })) });
  const downLayer = new TMap.MultiPolyline({ map: map, styles: { __LINE_STYLES__ }, geometries: DOWN_LINES.map(l => ({ id: l.id, styleId: l.styleId, paths: [new TMap.LatLng(l.plat, l.plng), new TMap.LatLng(l.alat, l.alng)] })) });
  const arrowLayer = new TMap.MultiMarker({ map: map, styles: { __ARROW_STYLES__ }, geometries: [] });
  function arrowPosAt(a, t){ return { id: a.id, styleId: a.styleId, position: new TMap.LatLng(a.start[0]+(a.end[0]-a.start[0])*t, a.start[1]+(a.end[1]-a.start[1])*t) }; }
  function refreshArrows(){ const arr = ARROW_META.filter(a => (a.tier==='up'&&upVisible)||(a.tier==='down'&&downVisible)).map(a => arrowPosAt(a, flowT)); arrowLayer.setGeometries(arr); }
  refreshArrows();
  window.__B = {
    filter: function() { markers.setGeometries(GEOMS.filter(g => activeCats.has(g.cat)).map(g => ({ id: g.id, styleId: g.styleId, position: new TMap.LatLng(g.lat, g.lng), properties: { html: g.html, name: g.name, cat: g.cat } }))); },
    applyUp: function() { upLayer.setGeometries(upVisible ? UP_LINES.map(l => ({ id: l.id, styleId: l.styleId, paths: [new TMap.LatLng(l.plat, l.plng), new TMap.LatLng(l.alat, l.alng)] })) : []); refreshArrows(); },
    applyDown: function() { downLayer.setGeometries(downVisible ? DOWN_LINES.map(l => ({ id: l.id, styleId: l.styleId, paths: [new TMap.LatLng(l.plat, l.plng), new TMap.LatLng(l.alat, l.alng)] })) : []); refreshArrows(); },
    refreshArrows: refreshArrows,
    invalidate: function() {},
    openSupplier: function(sid) { const g = GEOMS.find(x => x.sid === sid) || GEOMS.find(x => String(x.id) === sid); if (!g) return; map.setCenter(new TMap.LatLng(g.lat, g.lng)); map.setZoom(6); info.setPosition(new TMap.LatLng(g.lat, g.lng)); info.setContent(g.html); info.open(); }
  };
}

function initGeo(){
  if (__USE_TMAP2) initTMap2(); else initLeaflet2();
  // 深链：带 ?supplier=<id> 进入融合页时，自动定位并弹出该供应商基地
  const _sid = new URLSearchParams(location.search).get('supplier');
  if (_sid && window.__B) window.__B.openSupplier(_sid);
}
window.__geoReady = false;
</script>

<script>
function switchTab(tab){
  var dash = document.getElementById('view-dash'), geo = document.getElementById('view-geo');
  if (tab === 'dash'){
    dash.style.display = 'block'; geo.style.display = 'none';
    if (window.Chart) ['valChart','quadChart','newsChart','analystChart','profitChart','sectorChart'].forEach(function(id){
      try{ var c = Chart.getChart(id); if(c) c.resize(); }catch(e){}
    });
  } else {
    geo.style.display = 'block'; dash.style.display = 'none';
    void geo.offsetWidth; /* 强制回流，确保地图容器拿到真实尺寸 */
    if (!window.__geoReady){ initGeo(); window.__geoReady = true; }
    if (window.__B) window.__B.invalidate();
  }
  document.querySelectorAll('#appsub button[data-tab]').forEach(function(b){ b.classList.toggle('active', b.dataset.tab === tab); });
}
// 带 ?supplier=<id> 进入融合页时，自动切到地图页以触发上面的深链定位
if (new URLSearchParams(location.search).get('supplier')) switchTab('geo');
</script>
</body>
</html>
"""
    html = (COMBINED
            .replace("__TOPNAV_CSS__", TOPNAV_CSS)
            .replace("__TOPNAV__", topnav("../../", "combined"))
            .replace("__DASH_MARKUP__", dash_markup)
            .replace("__DASH_SCRIPT__", dash_script)
            .replace("__ANALYTICS__", analytics_js())
            .replace("__RAW__", json.dumps(G["geometries"], ensure_ascii=False))
            .replace("__ALL_CATS__", json.dumps(G["all_cats"], ensure_ascii=False))
            .replace("__MARKET_RAW__", json.dumps(G["market_geoms"], ensure_ascii=False))
            .replace("__UP_RAW__", json.dumps(G["line_geoms"], ensure_ascii=False))
            .replace("__DOWN_RAW__", json.dumps(G["down_geoms"], ensure_ascii=False))
            .replace("__ARROW_META__", json.dumps(G["arrow_meta_list"], ensure_ascii=False))
            .replace("__MARKER_STYLES__", marker_styles_js)
            .replace("__LINE_STYLES__", G["line_styles_js"])
            .replace("__ARROW_STYLES__", G["arrow_styles_js"])
            .replace("__MARKET_SVG__", market_svg())
            .replace("__PANEL__", G["panel"]))
    os.makedirs(os.path.dirname(OUT_COMBINED), exist_ok=True)
    with open(OUT_COMBINED, "w", encoding="utf-8") as f:
        f.write(html)
    print("写出", OUT_COMBINED)


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
    build_combined(recs, insights)
    print("完成。")


if __name__ == "__main__":
    main()
