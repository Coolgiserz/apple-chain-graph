# -*- coding: utf-8 -*-
"""
供应商宇宙 (Supplier Universe)
在本项目中，每个供应商在 generate.py 的 SUPPLIERS 里已有基础属性
(全称/英文名/简称/国家/类别/tier)。本模块补充「资本市场视角」所需的字段：
  - ticker / exchange / currency : 上市代码、交易所、财报币种
  - peer_group : 估值同业分组（默认等于 SUPPLIERS.category，可单独覆盖）
  - listed : 是否公开上市（私有/未上市公司无 ticker，仅做定性分析）

设计原则：
  - 仅记录事实性映射（代码、交易所），不在此写入财务数据。
  - ticker 留空("")表示非公开上市或代码不确定 -> 工具会自动跳过定量估值，只给定性结论。
  - 若你接入行情 API，可在 fetcher 中按 (exchange, ticker) 拉取实时倍数。
"""

# supplier_id -> {ticker, exchange, currency, listed, note}
UNIVERSE = {
 "tsmc":        {"ticker": "2330.TW", "exchange": "TWSE", "currency": "TWD", "listed": True,  "note": "台积电；美股 ADR: TSM"},
 "arm":         {"ticker": "ARM", "exchange": "NASDAQ", "currency": "USD", "listed": True,  "note": "Arm Holdings"},
 "sdc":         {"ticker": "", "exchange": "", "currency": "KRW", "listed": False, "note": "三星显示(私有，三星电子子公司)；财务并入三星电子披露"},
 "lgd":         {"ticker": "034220.KS", "exchange": "KRX", "currency": "KRW", "listed": True,  "note": "LG Display"},
 "boe":         {"ticker": "000725.SZ", "exchange": "SZSE", "currency": "CNY", "listed": True,  "note": "京东方 A"},
 "sharp":       {"ticker": "6753.T", "exchange": "TSE", "currency": "JPY", "listed": True,  "note": "夏普(鸿海体系)"},
 "sony":        {"ticker": "6758.T", "exchange": "TSE", "currency": "JPY", "listed": True,  "note": "索尼集团；美股 ADR: SONY"},
 "largan":      {"ticker": "3008.TW", "exchange": "TWSE", "currency": "TWD", "listed": True,  "note": "大立光电"},
 "genius":      {"ticker": "3406.TW", "exchange": "TWSE", "currency": "TWD", "listed": True,  "note": "玉晶光电"},
 "sunny":       {"ticker": "2382.HK", "exchange": "HKEX", "currency": "HKD", "listed": True,  "note": "舜宇光学"},
 "alps":        {"ticker": "6770.T", "exchange": "TSE", "currency": "JPY", "listed": True,  "note": "阿尔卑斯阿尔派"},
 "mitsumi":     {"ticker": "6767.T", "exchange": "TSE", "currency": "JPY", "listed": True,  "note": "三美电机"},
 "samsung_elec":{"ticker": "005930.KS", "exchange": "KRX", "currency": "KRW", "listed": True,  "note": "三星电子"},
 "skhynix":     {"ticker": "000660.KS", "exchange": "KRX", "currency": "KRW", "listed": True,  "note": "SK hynix"},
 "micron":      {"ticker": "MU", "exchange": "NASDAQ", "currency": "USD", "listed": True,  "note": "美光"},
 "kioxia":      {"ticker": "", "exchange": "", "currency": "JPY", "listed": False, "note": "铠侠(私有；曾计划 IPO)"},
 "wdc":         {"ticker": "WDC", "exchange": "NASDAQ", "currency": "USD", "listed": True,  "note": "西部数据"},
 "qualcomm":    {"ticker": "QCOM", "exchange": "NASDAQ", "currency": "USD", "listed": True,  "note": "高通"},
 "broadcom":    {"ticker": "AVGO", "exchange": "NASDAQ", "currency": "USD", "listed": True,  "note": "博通"},
 "cirrus":      {"ticker": "CRUS", "exchange": "NASDAQ", "currency": "USD", "listed": True,  "note": "凌云逻辑"},
 "ti":          {"ticker": "TXN", "exchange": "NASDAQ", "currency": "USD", "listed": True,  "note": "德州仪器"},
 "st":          {"ticker": "STMPA.PA", "exchange": "Euronext", "currency": "EUR", "listed": True,  "note": "意法半导体；美股 ADR: STM"},
 "bosch":       {"ticker": "", "exchange": "", "currency": "EUR", "listed": False, "note": "罗伯特·博世(私有)"},
 "tdk":         {"ticker": "6762.T", "exchange": "TSE", "currency": "JPY", "listed": True,  "note": "TDK"},
 "murata":      {"ticker": "6981.T", "exchange": "TSE", "currency": "JPY", "listed": True,  "note": "村田制作所"},
 "knowles":     {"ticker": "KN", "exchange": "NYSE", "currency": "USD", "listed": True,  "note": "楼氏电子"},
 "aac":         {"ticker": "2018.HK", "exchange": "HKEX", "currency": "HKD", "listed": True,  "note": "瑞声科技"},
 "goertek":     {"ticker": "002241.SZ", "exchange": "SZSE", "currency": "CNY", "listed": True,  "note": "歌尔股份"},
 "corning":      {"ticker": "GLW", "exchange": "NASDAQ", "currency": "USD", "listed": True,  "note": "康宁"},
 "lens_tech":   {"ticker": "300433.SZ", "exchange": "SZSE", "currency": "CNY", "listed": True,  "note": "蓝思科技"},
 "berne":       {"ticker": "", "exchange": "", "currency": "CNY", "listed": False, "note": "伯恩光学(私有)"},
 "foxconn":     {"ticker": "2317.TW", "exchange": "TWSE", "currency": "TWD", "listed": True,  "note": "鸿海精密；美股 ADR: HNHPF"},
 "luxshare":    {"ticker": "002475.SZ", "exchange": "SZSE", "currency": "CNY", "listed": True,  "note": "立讯精密"},
 "pegatron":    {"ticker": "4938.TW", "exchange": "TWSE", "currency": "TWD", "listed": True,  "note": "和硕"},
 "quanta":      {"ticker": "2382.TW", "exchange": "TWSE", "currency": "TWD", "listed": True,  "note": "广达电脑"},
 "wistron":     {"ticker": "3231.TW", "exchange": "TWSE", "currency": "TWD", "listed": True,  "note": "纬创资通"},
 "byd_e":       {"ticker": "00285.HK", "exchange": "HKEX", "currency": "HKD", "listed": True,  "note": "比亚迪电子"},
 "catcher":     {"ticker": "2474.TW", "exchange": "TWSE", "currency": "TWD", "listed": True,  "note": "可成科技"},
 "changying":   {"ticker": "300115.SZ", "exchange": "SZSE", "currency": "CNY", "listed": True,  "note": "长盈精密"},
 "lingyi":      {"ticker": "002600.SZ", "exchange": "SZSE", "currency": "CNY", "listed": True,  "note": "领益智造"},
 "desay":       {"ticker": "000049.SZ", "exchange": "SZSE", "currency": "CNY", "listed": True,  "note": "德赛电池"},
 "sunwoda":     {"ticker": "300207.SZ", "exchange": "SZSE", "currency": "CNY", "listed": True,  "note": "欣旺达"},
 "atl":         {"ticker": "", "exchange": "", "currency": "CNY", "listed": False, "note": "新能源科技(ATL，TDK 体系私有)"},
 "zhending":    {"ticker": "4958.TW", "exchange": "TWSE", "currency": "TWD", "listed": True,  "note": "鹏鼎控股"},
 "flexium":     {"ticker": "6269.TW", "exchange": "TWSE", "currency": "TWD", "listed": True,  "note": "台郡科技"},
 "dongshan":    {"ticker": "002384.SZ", "exchange": "SZSE", "currency": "CNY", "listed": True,  "note": "东山精密"},
 "unimicron":   {"ticker": "3037.TW", "exchange": "TWSE", "currency": "TWD", "listed": True,  "note": "欣兴电子"},
 "nanya_pcb":   {"ticker": "8046.TW", "exchange": "TWSE", "currency": "TWD", "listed": True,  "note": "南亚电路板"},
 "ibiden":      {"ticker": "4062.T", "exchange": "TSE", "currency": "JPY", "listed": True,  "note": "揖斐电"},
 "shennan":     {"ticker": "002916.SZ", "exchange": "SZSE", "currency": "CNY", "listed": True,  "note": "深南电路"},
 "ase":         {"ticker": "3711.TW", "exchange": "TWSE", "currency": "TWD", "listed": True,  "note": "日月光投控"},
 "amkor":       {"ticker": "AMKR", "exchange": "NASDAQ", "currency": "USD", "listed": True,  "note": "安靠"},
 "crystal":     {"ticker": "002273.SZ", "exchange": "SZSE", "currency": "CNY", "listed": True,  "note": "水晶光电"},
 "lante":       {"ticker": "688127.SS", "exchange": "SSE(STAR)", "currency": "CNY", "listed": True,  "note": "蓝特光学"},
 "gis":         {"ticker": "6456.TW", "exchange": "TWSE", "currency": "TWD", "listed": True,  "note": "业成(GIS)"},
 "viseira":     {"ticker": "6488.TW", "exchange": "TWSE", "currency": "TWD", "listed": True,  "note": "采钰科技"},
 "cowell":      {"ticker": "1415.HK", "exchange": "HKEX", "currency": "HKD", "listed": True,  "note": "高伟电子"},
 "zhaowei":     {"ticker": "003021.SZ", "exchange": "SZSE", "currency": "CNY", "listed": True,  "note": "兆威机电"},
 "apple":       {"ticker": "AAPL", "exchange": "NASDAQ", "currency": "USD", "listed": True,  "note": "苹果(终端厂，此处作对照基准)"},
 "ams":         {"ticker": "AMS.SW", "exchange": "SIX", "currency": "CHF", "listed": True,  "note": "ams OSRAM"},
}

SUPPLIER_IDS = list(UNIVERSE.keys())

# ---------------------------------------------------------------------------
# 估值同业分组 (Sector / peer group)
# 设计：category 太细（多数只有 1 家），直接做相对估值会全部 N/A。
#       这里用更宽、业务可比性更强的 sector 分组；valuation 引擎在 sector
#       同业不足时，会自动回退到「全样本中位」(见 valuation.py)。
# 规则：
#   - 同 sector 内至少有 2 家上市同业，才用 sector 中位；否则回退全样本。
#   - apple 作为终端厂/客户，单独列为 OEM(Benchmark)，不参与供应商同业比较。
# ---------------------------------------------------------------------------
SECTOR = {
    # 晶圆代工
    "tsmc": "Foundry",
    # 存储
    "samsung_elec": "Memory", "skhynix": "Memory", "micron": "Memory",
    "kioxia": "Memory", "wdc": "Memory",
    # 逻辑芯片 / 设计 / IP
    "qualcomm": "Logic Semi", "broadcom": "Logic Semi", "cirrus": "Logic Semi",
    "ti": "Logic Semi", "st": "Logic Semi", "arm": "Logic Semi",
    # 显示
    "sdc": "Display", "lgd": "Display", "boe": "Display", "sharp": "Display",
    # 封测 OSAT
    "ase": "OSAT", "amkor": "OSAT",
    # 光学 / 镜头
    "largan": "Optics", "genius": "Optics", "sunny": "Optics",
    "crystal": "Optics", "lante": "Optics",
    # 图像传感器 / 摄像头模组 / 触控
    "sony": "CIS/Camera", "viseira": "CIS/Camera", "cowell": "CIS/Camera",
    "gis": "CIS/Camera",
    # 组装 / 代工
    "foxconn": "Assembly", "luxshare": "Assembly", "pegatron": "Assembly",
    "quanta": "Assembly", "wistron": "Assembly", "byd_e": "Assembly",
    "goertek": "Assembly",
    # 金属/结构件外壳
    "catcher": "Enclosure", "changying": "Enclosure", "lingyi": "Enclosure",
    "lens_tech": "Glass/Enclosure", "berne": "Glass/Enclosure",
    # 电池
    "desay": "Battery", "sunwoda": "Battery", "atl": "Battery",
    # PCB / FPC / 载板
    "zhending": "PCB/FPC", "flexium": "PCB/FPC", "dongshan": "PCB/FPC",
    "shennan": "PCB/FPC", "ibiden": "PCB/FPC", "unimicron": "PCB/FPC",
    "nanya_pcb": "PCB/FPC",
    # 元器件（被动/传感器/声学/机电/材料，统一作电子元器件组）
    "murata": "Components", "tdk": "Components", "corning": "Components",
    "bosch": "Components", "ams": "Components", "knowles": "Components",
    "aac": "Components", "alps": "Components", "mitsumi": "Components",
    "zhaowei": "Components",
    # 终端厂基准（不参与供应商比较）
    "apple": "OEM(Benchmark)",
}


def get(supplier_id):
    return UNIVERSE.get(supplier_id)


def sector_of(supplier_id):
    return SECTOR.get(supplier_id)


def summary_line(supplier_id):
    u = UNIVERSE.get(supplier_id, {})
    if not u:
        return "(未知供应商)"
    code = u["ticker"] or "未上市"
    return f"{code} · {u['exchange'] or '-'} · {u['currency']}"
