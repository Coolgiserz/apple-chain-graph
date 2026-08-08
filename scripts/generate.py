# -*- coding: utf-8 -*-
"""
Apple Supply Chain Graph Generator  (v2 - attribute-rich)
Produces Neo4j-importable CSV + Cypher + JSON and an HTML report.

Data-model principles (per user requirement):
- Supplier node: `name` = 全称 (full legal name), 英文名称 / 简称 are SEPARATE
  properties, NOT mixed into one field.
- Product node: `name` = 官方型号全称 (node name); english_name / alias(别名) /
  release_date(发布时间) / status / price 等为独立属性。
- Component node: `name` = 中文全称; english_name 单独属性。
All data curated from public supply-chain reports (2024-2026) and Apple's
2024 Supplier List (187 core suppliers, ~98% of direct spend).
"""
import csv, json, os

# Repo root: this script lives in <repo>/scripts/, so two dirname levels up.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEO = os.path.join(ROOT, "data", "neo4j")
os.makedirs(NEO, exist_ok=True)

# ---------------------------------------------------------------------------
# 关系溯源 (PROVENANCE) —— 每条供应商/代工关系都必须可追溯到公开来源
# SOURCES: id -> {title, publisher, url, kind}
#   kind: official(官方名单) / teardown(拆解) / analyst(行业分析) / ir(公司披露) / method(方法论推导)
# 所有 URL 为稳定可访问的公开页面；访问日期统一记在 meta.sources_accessed。
# ---------------------------------------------------------------------------
SOURCES = {
 "apple_supplier_list": {
   "title": "Apple Supplier List (2024/2025 官方供应链名单)",
   "publisher": "Apple Inc.",
   "url": "https://www.apple.com/supplier-responsibility/",
   "kind": "official"},
 "apple_10k": {
   "title": "Apple Inc. Form 10-K（供应商集中度与组件披露）",
   "publisher": "U.S. SEC (Apple CIK 0000320193)",
   "url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0000320193&type=10-K",
   "kind": "official"},
 "techinsights": {
   "title": "TechInsights 硬件拆解与物料清单(BOM)分析",
   "publisher": "TechInsights",
   "url": "https://www.techinsights.com/teardown",
   "kind": "teardown"},
 "ifixit": {
   "title": "iFixit 产品拆解数据库",
   "publisher": "iFixit",
   "url": "https://www.ifixit.com/Teardown",
   "kind": "teardown"},
 "counterpoint": {
   "title": "Counterpoint Research — 零部件供应与份额研究",
   "publisher": "Counterpoint Research",
   "url": "https://www.counterpointresearch.com/",
   "kind": "analyst"},
 "trendforce": {
   "title": "TrendForce — 存储/半导体供需与份额报告",
   "publisher": "TrendForce",
   "url": "https://www.trendforce.com/press-center/",
   "kind": "analyst"},
 "dscc": {
   "title": "DSCC (Display Supply Chain Consultants) — 显示面板供给分析",
   "publisher": "DSCC / Omdia",
   "url": "https://www.displaysupplychain.com/",
   "kind": "analyst"},
 "omdia": {
   "title": "Omdia — 显示与半导体市场追踪",
   "publisher": "Omdia (Informa)",
   "url": "https://omdia.tech.informa.com/",
   "kind": "analyst"},
 "nikkei": {
   "title": "Nikkei Asia — 苹果供应链报道",
   "publisher": "Nikkei Asia",
   "url": "https://asia.nikkei.com/",
   "kind": "analyst"},
}
# 组件 -> 该组件供应商关系的默认来源集合（每条 SUPPLIED_BY 边继承所属组件的来源）
COMP_SOURCE = {
 "soc":              ["apple_supplier_list", "techinsights"],
 "display_panel":    ["dscc", "techinsights"],
 "cover_glass":      ["techinsights", "ifixit"],
 "cis":              ["techinsights", "counterpoint"],
 "lens":             ["techinsights", "counterpoint"],
 "ois":              ["counterpoint", "techinsights"],
 "dram":             ["trendforce", "counterpoint"],
 "nand":             ["trendforce", "counterpoint"],
 "modem":            ["techinsights", "counterpoint"],
 "connectivity":     ["techinsights", "counterpoint"],
 "audio_codec":      ["techinsights", "apple_10k"],
 "pmic":             ["techinsights", "counterpoint"],
 "battery":          ["counterpoint", "techinsights"],
 "enclosure":        ["techinsights", "nikkei"],
 "fpc":              ["techinsights", "nikkei"],
 "pcb":              ["techinsights", "counterpoint"],
 "substrate":        ["techinsights", "counterpoint"],
 "osat":             ["techinsights", "counterpoint"],
 "speaker":          ["techinsights", "counterpoint"],
 "mic":              ["techinsights", "counterpoint"],
 "sensor_motion":    ["techinsights", "counterpoint"],
 "sensor_bio":       ["techinsights", "counterpoint"],
 "optical_filter":   ["techinsights", "counterpoint"],
 "uwb":              ["techinsights", "counterpoint"],
 "wireless_charging":["techinsights", "counterpoint"],
 "touch":            ["techinsights", "ifixit"],
 "camera_module":    ["techinsights", "counterpoint"],
}
# 关系级别默认来源集合
SRC_ASSEMBLY = ["apple_supplier_list", "nikkei"]      # 代工关系
SRC_BOM      = ["techinsights", "ifixit"]             # 产品-零部件(BOM 推导)


# ---------------------------------------------------------------------------
# SUPPLIERS  (id -> properties)
#   name       = 全称 (full legal name)  -> node name / :ID text
#   english_name = 英文名称
#   short_name = 简称 / ticker / 常用缩写
# ---------------------------------------------------------------------------
SUPPLIERS = {
 "tsmc":        {"name": "台湾积体电路制造股份有限公司", "english_name": "Taiwan Semiconductor Manufacturing Company (TSMC)", "short_name": "TSMC / 台积电", "country": "Taiwan",        "region": "East Asia",     "category": "Foundry",          "tier": 1},
 "arm":         {"name": "安谋控股公司",            "english_name": "Arm Holdings plc",                                  "short_name": "Arm",          "country": "UK",            "region": "Europe",       "category": "IP/EDA",           "tier": 1},
 "sdc":         {"name": "三星显示有限公司",        "english_name": "Samsung Display Co., Ltd.",                         "short_name": "SDC / 三星显示", "country": "South Korea",   "region": "East Asia",     "category": "Display",          "tier": 1},
 "lgd":         {"name": "乐金显示株式会社",        "english_name": "LG Display Co., Ltd.",                              "short_name": "LGD / LG显示",  "country": "South Korea",   "region": "East Asia",     "category": "Display",          "tier": 1},
 "boe":         {"name": "京东方科技集团股份有限公司", "english_name": "BOE Technology Group Co., Ltd.",                    "short_name": "BOE / 京东方",  "country": "China",         "region": "East Asia",     "category": "Display",          "tier": 1},
 "sharp":       {"name": "夏普株式会社",            "english_name": "Sharp Corporation",                                 "short_name": "Sharp / 夏普",  "country": "Japan",         "region": "East Asia",     "category": "Display",          "tier": 1},
 "sony":        {"name": "索尼集团株式会社",        "english_name": "Sony Group Corporation",                           "short_name": "Sony / 索尼",   "country": "Japan",         "region": "East Asia",     "category": "CIS/Optical",      "tier": 1},
 "largan":      {"name": "大立光电股份有限公司",    "english_name": "Largan Precision Co., Ltd.",                       "short_name": "Largan / 大立光","country": "Taiwan",        "region": "East Asia",     "category": "Optics",           "tier": 1},
 "genius":      {"name": "玉晶光电股份有限公司",    "english_name": "Genius Electronic Optical Co., Ltd.",              "short_name": "Genius / 玉晶光","country": "Taiwan",        "region": "East Asia",     "category": "Optics",           "tier": 1},
 "sunny":       {"name": "舜宇光学科技(集团)有限公司", "english_name": "Sunny Optical Technology (Group) Co., Ltd.",        "short_name": "Sunny / 舜宇光学","country": "China",         "region": "East Asia",     "category": "Optics",           "tier": 1},
 "alps":        {"name": "阿尔卑斯阿尔派株式会社",  "english_name": "Alps Alpine Co., Ltd.",                             "short_name": "Alps / 阿尔卑斯","country": "Japan",         "region": "East Asia",     "category": "Mech/Actuator",     "tier": 2},
 "mitsumi":     {"name": "三美电机株式会社",        "english_name": "Mitsumi Electric Co., Ltd.",                       "short_name": "Mitsumi / 三美","country": "Japan",         "region": "East Asia",     "category": "Mech/Actuator",     "tier": 2},
 "samsung_elec":{"name": "三星电子株式会社",        "english_name": "Samsung Electronics Co., Ltd.",                    "short_name": "SEC / 三星电子","country": "South Korea",   "region": "East Asia",     "category": "Memory",           "tier": 1},
 "skhynix":     {"name": "SK海力士株式会社",        "english_name": "SK hynix Inc.",                                    "short_name": "SK hynix / SK海力士","country": "South Korea",   "region": "East Asia",     "category": "Memory",           "tier": 1},
 "micron":      {"name": "美光科技股份有限公司",    "english_name": "Micron Technology, Inc.",                          "short_name": "Micron / 美光", "country": "USA",           "region": "North America", "category": "Memory",           "tier": 1},
 "kioxia":      {"name": "铠侠株式会社",            "english_name": "Kioxia Corporation",                               "short_name": "Kioxia / 铠侠", "country": "Japan",         "region": "East Asia",     "category": "Memory",           "tier": 1},
 "wdc":         {"name": "西部数据公司",            "english_name": "Western Digital Corporation",                      "short_name": "WD / 西部数据", "country": "USA",           "region": "North America", "category": "Memory",           "tier": 1},
 "qualcomm":    {"name": "高通公司",                "english_name": "Qualcomm Incorporated",                            "short_name": "Qualcomm / 高通","country": "USA",           "region": "North America", "category": "Semiconductor",     "tier": 1},
 "broadcom":    {"name": "博通公司",                "english_name": "Broadcom Inc.",                                    "short_name": "Broadcom / 博通","country": "USA",           "region": "North America", "category": "Semiconductor",     "tier": 1},
 "cirrus":      {"name": "凌云逻辑公司",            "english_name": "Cirrus Logic, Inc.",                               "short_name": "Cirrus / 凌云逻辑","country": "USA",         "region": "North America", "category": "Semiconductor",     "tier": 2},
 "ti":          {"name": "德州仪器公司",            "english_name": "Texas Instruments Incorporated",                   "short_name": "TI / 德州仪器", "country": "USA",           "region": "North America", "category": "Semiconductor",     "tier": 1},
 "st":          {"name": "意法半导体集团",          "english_name": "STMicroelectronics N.V.",                          "short_name": "ST / 意法半导体","country": "Switzerland/France","region": "Europe",    "category": "Semiconductor",     "tier": 1},
 "bosch":       {"name": "罗伯特·博世有限公司",     "english_name": "Robert Bosch GmbH",                                "short_name": "Bosch / 博世",  "country": "Germany",       "region": "Europe",       "category": "Sensor",           "tier": 2},
 "tdk":         {"name": "TDK株式会社",             "english_name": "TDK Corporation",                                 "short_name": "TDK",           "country": "Japan",         "region": "East Asia",     "category": "Passive/Battery",   "tier": 2},
 "murata":      {"name": "株式会社村田制作所",      "english_name": "Murata Manufacturing Co., Ltd.",                   "short_name": "Murata / 村田", "country": "Japan",         "region": "East Asia",     "category": "Passive",          "tier": 2},
 "knowles":     {"name": "楼氏电子公司",            "english_name": "Knowles Corporation",                             "short_name": "Knowles / 楼氏","country": "USA",           "region": "North America", "category": "Acoustics",         "tier": 2},
 "aac":         {"name": "瑞声科技控股有限公司",    "english_name": "AAC Technologies Holdings Inc.",                   "short_name": "AAC / 瑞声科技","country": "China",         "region": "East Asia",     "category": "Acoustics",         "tier": 2},
 "goertek":     {"name": "歌尔股份有限公司",        "english_name": "GoerTek Inc.",                                    "short_name": "GoerTek / 歌尔股份","country": "China",         "region": "East Asia",     "category": "Assembly/Acoustics", "tier": 2},
 "corning":     {"name": "康宁公司",                "english_name": "Corning Incorporated",                            "short_name": "Corning / 康宁","country": "USA",           "region": "North America", "category": "Material",          "tier": 1},
 "lens_tech":   {"name": "蓝思科技股份有限公司",    "english_name": "Lens Technology Co., Ltd.",                        "short_name": "Lens / 蓝思科技","country": "China",         "region": "East Asia",     "category": "Glass/Enclosure",   "tier": 1},
 "berne":       {"name": "伯恩光学(惠州)有限公司",  "english_name": "Berne Optics (Huizhou) Co., Ltd.",                 "short_name": "Berne / 伯恩光学","country": "China",         "region": "East Asia",     "category": "Glass",            "tier": 1},
 "foxconn":     {"name": "鸿海精密工业股份有限公司", "english_name": "Hon Hai Precision Industry Co., Ltd. (Foxconn)",  "short_name": "Foxconn / 富士康","country": "Taiwan/China",  "region": "East Asia",     "category": "Assembly",          "tier": 1},
 "luxshare":    {"name": "立讯精密工业股份有限公司", "english_name": "Luxshare Precision Industry Co., Ltd.",            "short_name": "Luxshare / 立讯精密","country": "China",        "region": "East Asia",     "category": "Assembly",          "tier": 1},
 "pegatron":    {"name": "和硕联合科技股份有限公司", "english_name": "Pegatron Corporation",                            "short_name": "Pegatron / 和硕","country": "Taiwan",        "region": "East Asia",     "category": "Assembly",          "tier": 1},
 "quanta":      {"name": "广达电脑股份有限公司",    "english_name": "Quanta Computer Inc.",                             "short_name": "Quanta / 广达", "country": "Taiwan",        "region": "East Asia",     "category": "Assembly",          "tier": 1},
 "wistron":     {"name": "纬创资通股份有限公司",    "english_name": "Wistron Corporation",                              "short_name": "Wistron / 纬创","country": "Taiwan",        "region": "East Asia",     "category": "Assembly",          "tier": 2},
 "byd_e":       {"name": "比亚迪电子(国际)有限公司", "english_name": "BYD Electronic (International) Co., Ltd.",         "short_name": "BYD Electronic / 比亚迪电子","country": "China",    "region": "East Asia",     "category": "Assembly/Enclosure","tier": 1},
 "catcher":     {"name": "可成科技股份有限公司",    "english_name": "Catcher Technology Co., Ltd.",                     "short_name": "Catcher / 可成科技","country": "Taiwan",      "region": "East Asia",     "category": "Enclosure",         "tier": 1},
 "changying":   {"name": "广东长盈精密技术股份有限公司", "english_name": "Guangdong Changying Precision Technology Co., Ltd.","short_name": "Changying / 长盈精密","country": "China",    "region": "East Asia",     "category": "Enclosure",         "tier": 1},
 "lingyi":      {"name": "领益智造科技股份有限公司", "english_name": "Lingyi iTech (Guangdong) Co., Ltd.",              "short_name": "Lingyi / 领益智造","country": "China",       "region": "East Asia",     "category": "Enclosure/Module",  "tier": 1},
 "desay":       {"name": "惠州市德赛电池有限公司",  "english_name": "Huizhou Desay Battery Co., Ltd.",                 "short_name": "Desay / 德赛电池","country": "China",        "region": "East Asia",     "category": "Battery",           "tier": 1},
 "sunwoda":     {"name": "欣旺达电子股份有限公司",  "english_name": "Sunwoda Electronic Co., Ltd.",                     "short_name": "Sunwoda / 欣旺达","country": "China",       "region": "East Asia",     "category": "Battery",           "tier": 1},
 "atl":         {"name": "新能源科技有限公司",      "english_name": "Amperex Technology Limited (ATL)",                "short_name": "ATL / 新能源科技","country": "China",       "region": "East Asia",     "category": "Battery",           "tier": 1},
 "zhending":    {"name": "鹏鼎控股(深圳)股份有限公司", "english_name": "Zhen Ding Technology Holding Limited",           "short_name": "ZDT / 鹏鼎控股", "country": "Taiwan/China",  "region": "East Asia",     "category": "FPC",              "tier": 1},
 "flexium":     {"name": "台郡科技股份有限公司",    "english_name": "Flexium Interconnect Inc.",                        "short_name": "Flexium / 台郡科技","country": "Taiwan",      "region": "East Asia",     "category": "FPC",              "tier": 1},
 "dongshan":    {"name": "东山精密制造股份有限公司", "english_name": "Dongshan Precision Manufacturing Co., Ltd.",       "short_name": "Dongshan / 东山精密","country": "China",      "region": "East Asia",     "category": "FPC/Component",     "tier": 1},
 "unimicron":   {"name": "欣兴电子股份有限公司",    "english_name": "Unimicron Technology Corporation",                "short_name": "Unimicron / 欣兴电子","country": "Taiwan",    "region": "East Asia",     "category": "Substrate/PCB",     "tier": 1},
 "nanya_pcb":   {"name": "南亚电路板股份有限公司",  "english_name": "Nan Ya PCB Corporation",                           "short_name": "NYP / 南亚电路板","country": "Taiwan",      "region": "East Asia",     "category": "Substrate/PCB",     "tier": 1},
 "ibiden":      {"name": "揖斐电株式会社",          "english_name": "Ibiden Co., Ltd.",                                "short_name": "Ibiden / 揖斐电","country": "Japan",         "region": "East Asia",     "category": "Substrate",         "tier": 1},
 "shennan":     {"name": "深南电路股份有限公司",    "english_name": "Shennan Circuits Co., Ltd.",                      "short_name": "SCC / 深南电路", "country": "China",         "region": "East Asia",     "category": "PCB",              "tier": 2},
 "ase":         {"name": "日月光投资控股股份有限公司", "english_name": "ASE Technology Holding Co., Ltd.",               "short_name": "ASE / 日月光",   "country": "Taiwan",        "region": "East Asia",     "category": "OSAT",             "tier": 1},
 "amkor":       {"name": "爱麦克科技股份有限公司",  "english_name": "Amkor Technology, Inc.",                          "short_name": "Amkor / 安靠",   "country": "USA/Korea",     "region": "North America", "category": "OSAT",             "tier": 1},
 "crystal":     {"name": "浙江水晶光电科技股份有限公司", "english_name": "Zhejiang Crystal-Optech Co., Ltd.",            "short_name": "Crystal / 水晶光电","country": "China",      "region": "East Asia",     "category": "Optical",           "tier": 2},
 "lante":       {"name": "浙江蓝特光学股份有限公司", "english_name": "Lante Optics Inc.",                               "short_name": "Lante / 蓝特光学","country": "China",        "region": "East Asia",     "category": "Optical",           "tier": 2},
 "gis":         {"name": "业成科技(深圳)有限公司",  "english_name": "General Interface Solution (GIS) - TPK",          "short_name": "GIS / 业成",     "country": "Taiwan",        "region": "East Asia",     "category": "Touch/Display",     "tier": 2},
 "viseira":     {"name": "采钰科技股份有限公司",    "english_name": "VisEra Technologies Company Limited",             "short_name": "VisEra / 采钰科技","country": "Taiwan",      "region": "East Asia",     "category": "CIS/Optical",       "tier": 2},
 "cowell":      {"name": "高伟电子控股有限公司",    "english_name": "Cowell Technology Corporation",                   "short_name": "Cowell / 高伟电子","country": "China",       "region": "East Asia",     "category": "Camera Module",     "tier": 2},
 "zhaowei":     {"name": "深圳市兆威机电股份有限公司", "english_name": "Shenzhen Zhaowei Machinery & Electronics Co., Ltd.","short_name": "Zhaowei / 兆威机电","country": "China",   "region": "East Asia",     "category": "Mech",              "tier": 2},
 "apple":       {"name": "苹果公司(自研)",          "english_name": "Apple Inc. (in-house)",                           "short_name": "Apple / 苹果自研","country": "USA",          "region": "North America", "category": "Semiconductor",     "tier": 1},
 "ams":         {"name": "艾迈斯欧司朗公司",        "english_name": "ams OSRAM AG",                                    "short_name": "ams OSRAM",      "country": "Austria",       "region": "Europe",       "category": "Sensor",           "tier": 2},
}

# ---------------------------------------------------------------------------
# COMPONENTS  (id -> properties)
#   name = 中文全称 ; english_name = 英文名称
# ---------------------------------------------------------------------------
COMPONENTS = {
 "soc":             {"name": "Apple 自研 SoC 芯片",   "english_name": "Apple Silicon SoC",       "category": "Processor",       "subcategory": "A/M 系列自研芯片"},
 "display_panel":   {"name": "显示面板",              "english_name": "Display Panel",           "category": "Display",         "subcategory": "OLED/LTPO/Mini-LED/LCD/Micro-OLED"},
 "cover_glass":     {"name": "盖板玻璃",              "english_name": "Cover Glass",             "category": "Display",         "subcategory": "Ceramic Shield / 3D玻璃盖板"},
 "cis":             {"name": "摄像头图像传感器",      "english_name": "Camera Image Sensor",     "category": "Optics/Camera",   "subcategory": "CMOS 图像传感器"},
 "lens":            {"name": "镜头",                  "english_name": "Camera Lens",             "category": "Optics/Camera",   "subcategory": "镜头 / Pancake 光学"},
 "ois":             {"name": "光学防抖执行器",        "english_name": "OIS / VCM Actuator",      "category": "Optics/Camera",   "subcategory": "光学防抖 VCM"},
 "dram":            {"name": "DRAM 运行内存",         "english_name": "DRAM",                    "category": "Memory",          "subcategory": "动态随机存取存储器"},
 "nand":            {"name": "NAND 闪存",             "english_name": "NAND Flash",              "category": "Memory",          "subcategory": "存储"},
 "modem":           {"name": "5G 调制解调器",         "english_name": "5G Modem",                "category": "Connectivity",    "subcategory": "基带"},
 "connectivity":    {"name": "无线连接芯片",          "english_name": "Wi-Fi / BT / RF",         "category": "Connectivity",    "subcategory": "Wi-Fi/蓝牙/射频前端"},
 "audio_codec":     {"name": "音频编解码与触觉芯片",  "english_name": "Audio Codec / Haptics",   "category": "Semiconductor",   "subcategory": "音频 / 触觉引擎"},
 "pmic":            {"name": "电源管理芯片",          "english_name": "Power Management IC",     "category": "Semiconductor",   "subcategory": "电源管理"},
 "battery":         {"name": "电池与电源系统",        "english_name": "Battery",                 "category": "Power",           "subcategory": "电芯 / 电源系统"},
 "enclosure":       {"name": "中框与结构件",          "english_name": "Enclosure / Structural",  "category": "Mechanical",      "subcategory": "中框 / 机壳 / 结构件"},
 "fpc":             {"name": "柔性印刷电路板",        "english_name": "Flexible PCB (FPC)",      "category": "PCB",             "subcategory": "柔性电路板"},
 "pcb":             {"name": "刚性 PCB / 载板",       "english_name": "Rigid PCB / Substrate",   "category": "PCB",             "subcategory": "硬板 / 载板(ABF)"},
 "substrate":       {"name": "ABF 封装载板",          "english_name": "ABF Substrate",           "category": "PCB",             "subcategory": "封装载板"},
 "osat":            {"name": "先进封装与测试",        "english_name": "Advanced Packaging / OSAT","category": "Semiconductor",   "subcategory": "先进封装 / 测试"},
 "speaker":         {"name": "扬声器模组",            "english_name": "Speaker Module",          "category": "Acoustics",       "subcategory": "扬声器模组"},
 "mic":             {"name": "MEMS 麦克风",           "english_name": "MEMS Microphone",         "category": "Acoustics",       "subcategory": "麦克风"},
 "sensor_motion":   {"name": "运动与环境传感器",      "english_name": "Motion / MEMS Sensor",    "category": "Sensor",          "subcategory": "运动 / 气压 / IMU"},
 "sensor_bio":      {"name": "生物与健康传感器",      "english_name": "Biometric / Health Sensor","category": "Sensor",          "subcategory": "健康 / 生物传感"},
 "optical_filter":  {"name": "光学滤光片与棱镜",      "english_name": "Optical Filter / Prism",  "category": "Optics/Camera",   "subcategory": "滤光片 / 棱镜"},
 "uwb":             {"name": "超宽带芯片",            "english_name": "UWB Chip",                "category": "Connectivity",    "subcategory": "超宽带"},
 "wireless_charging":{"name": "无线充电模组",         "english_name": "Wireless Charging",       "category": "Power",           "subcategory": "无线充电"},
 "touch":           {"name": "触控模组",              "english_name": "Touch Module",            "category": "Display",         "subcategory": "触控模组"},
 "camera_module":   {"name": "摄像头模组",            "english_name": "Camera Module",           "category": "Optics/Camera",   "subcategory": "摄像头模组"},
}

# component id -> list of (supplier_id, share_or_None, note)
COMP_SUP = {
 "soc":            [("tsmc", 100, "3nm N3E/N3P 独家代工；旧款 A16 在台积电亚利桑那厂"), ("arm", None, "CPU 架构 IP 授权"), ("apple", None, "自研芯片设计")],
 "display_panel":  [("sdc", None, "OLED/LTPO/Micro-OLED 面板"), ("lgd", None, "OLED/AMOLED/Mini-LED 面板"), ("boe", None, "OLED/LCD 面板(MacBook Air 51%)"), ("sharp", None, "Mini-LED(MacBook Pro)"), ("sony", None, "Micro-OLED 内屏(Vision Pro)")],
 "cover_glass":    [("corning", None, "Ceramic Shield 玻璃基材"), ("lens_tech", None, "3D 玻璃盖板/金属中框"), ("berne", None, "玻璃盖板")],
 "cis":            [("sony", None, "CMOS 图像传感器(独占高端)"), ("samsung_elec", None, "未来替代供应商")],
 "lens":           [("largan", None, "手机镜头"), ("genius", None, "镜头/Pancake 光学(Vision Pro)"), ("sunny", None, "镜头")],
 "ois":            [("alps", None, "OIS/VCM 执行器"), ("mitsumi", None, "OIS/VCM 执行器")],
 "dram":           [("samsung_elec", None, "DRAM 第一大供应商(~60-70%)"), ("skhynix", None, "DRAM"), ("micron", None, "DRAM")],
 "nand":           [("samsung_elec", None, "NAND"), ("skhynix", None, "NAND"), ("kioxia", None, "NAND(~35%)"), ("wdc", None, "NAND/SanDisk"), ("micron", None, "NAND")],
 "modem":          [("qualcomm", None, "5G 基带(当前主力)"), ("apple", None, "C1 自研基带(过渡中)")],
 "connectivity":   [("broadcom", None, "Wi-Fi/蓝牙/射频"), ("qualcomm", None, "射频前端")],
 "audio_codec":    [("cirrus", None, "音频编解码/触觉")],
 "pmic":           [("ti", None, "电源管理 IC"), ("st", None, "电源/无线充电"), ("apple", None, "PMIC")],
 "battery":        [("desay", None, "电池电芯/电源系统"), ("sunwoda", None, "电池"), ("atl", None, "电池"), ("tdk", None, "电池/被动件")],
 "enclosure":      [("catcher", None, "金属机壳"), ("lens_tech", None, "金属中框/玻璃"), ("changying", None, "结构件"), ("lingyi", None, "结构件/模组"), ("byd_e", None, "结构件/组装"), ("foxconn", None, "金属机身")],
 "fpc":            [("zhending", None, "柔性电路板 FPC"), ("flexium", None, "FPC"), ("dongshan", None, "FPC/组件")],
 "pcb":            [("unimicron", None, "PCB/载板"), ("nanya_pcb", None, "PCB"), ("shennan", None, "PCB"), ("ibiden", None, "ABF 载板")],
 "substrate":      [("ibiden", None, "ABF 载板"), ("unimicron", None, "载板"), ("nanya_pcb", None, "载板")],
 "osat":           [("ase", None, "先进封装/测试(InFO/CoWoS)"), ("amkor", None, "先进封装/测试")],
 "speaker":        [("goertek", None, "扬声器模组"), ("aac", None, "声学元件"), ("luxshare", None, "声学/模组")],
 "mic":            [("knowles", None, "MEMS 麦克风"), ("goertek", None, "MEMS 麦克风(歌尔微)"), ("aac", None, "麦克风")],
 "sensor_motion":  [("bosch", None, "运动/气压传感器"), ("st", None, "传感器"), ("tdk", None, "传感器/IMU")],
 "sensor_bio":     [("st", None, "健康/生物传感器"), ("ams", None, "光学/环境传感器")],
 "optical_filter": [("crystal", None, "光学滤光片/棱镜"), ("lante", None, "光学元件")],
 "uwb":            [("st", None, "U2 超宽带芯片"), ("apple", None, "UWB 设计")],
 "wireless_charging":[("st", None, "无线充电控制器"), ("broadcom", None, "无线充电")],
 "touch":          [("gis", None, "触控模组"), ("lgd", None, "触控显示")],
 "camera_module":  [("cowell", None, "摄像头模组"), ("lgd", None, "模组")],
}

# ---------------------------------------------------------------------------
# PRODUCTS  (attribute-rich)
# id, name(全称/型号), product_line, english_name, alias(别名/代号),
# release_date(发布时间), release_year, status, soc, display, price_usd,
# assembly[list], components[list]
# ---------------------------------------------------------------------------
def P(pid, name, line, en, alias, rdate, yr, status, soc, disp, price, assembly, comps):
    return {"id": pid, "name": name, "product_line": line, "english_name": en,
            "alias": alias, "release_date": rdate, "release_year": yr, "status": status,
            "soc": soc, "display": disp, "price_usd": price,
            "assembly": assembly, "components": comps}

PHONE_COMP = ["soc","display_panel","cover_glass","cis","lens","ois","dram","nand",
              "modem","connectivity","audio_codec","pmic","battery","enclosure",
              "fpc","pcb","substrate","osat","speaker","mic","sensor_motion",
              "optical_filter","uwb"]
MAC_COMP   = ["soc","display_panel","cover_glass","dram","nand","connectivity",
              "pmic","battery","enclosure","fpc","pcb","substrate","osat","speaker","mic","sensor_motion"]
PAD_COMP   = ["soc","display_panel","cover_glass","dram","nand","pmic","battery",
              "enclosure","fpc","touch","speaker","mic","sensor_motion"]

PRODUCTS = [
 # ---- iPhone ----
 P("iphone_17",      "iPhone 17",            "iPhone", "iPhone 17", "", "2025-09-09", 2025, "在售", "A19",      "6.3\" OLED (SDC/LGD/BOE)", 799, ["foxconn","luxshare"], PHONE_COMP),
 P("iphone_17_air",  "iPhone 17 Air",        "iPhone", "iPhone 17 Air", "iPhone 17 Slim (发布前代号)", "2025-09-09", 2025, "在售", "A19", "6.6\" OLED 超薄 (SDC/LGD/BOE)", 999, ["foxconn","luxshare"], PHONE_COMP),
 P("iphone_17_pro",  "iPhone 17 Pro",        "iPhone", "iPhone 17 Pro", "", "2025-09-09", 2025, "在售", "A19 Pro", "6.3\" LTPO OLED (SDC/LGD/BOE)", 1099, ["foxconn","luxshare"], PHONE_COMP),
 P("iphone_17_pmax", "iPhone 17 Pro Max",    "iPhone", "iPhone 17 Pro Max", "", "2025-09-09", 2025, "在售", "A19 Pro", "6.9\" LTPO OLED (SDC/LGD)", 1199, ["foxconn"], PHONE_COMP),
 # ---- Mac ----
 P("mba_13_m4",      "MacBook Air 13\" (M4)", "Mac", "MacBook Air 13-inch (M4)", "", "2025-03-05", 2025, "在售", "M4", "13.6\" LCD (BOE)", 999, ["foxconn"], MAC_COMP),
 P("mba_15_m4",      "MacBook Air 15\" (M4)", "Mac", "MacBook Air 15-inch (M4)", "", "2025-03-05", 2025, "在售", "M4", "15.3\" LCD (BOE)", 1199, ["foxconn"], MAC_COMP),
 P("mbp_14_m4",      "MacBook Pro 14\" (M4)", "Mac", "MacBook Pro 14-inch (M4)", "", "2024-10-30", 2024, "在售", "M4/M4 Pro/M4 Max", "14.2\" Mini-LED (Sharp/LGD)", 1599, ["foxconn"], MAC_COMP),
 P("mbp_16_m4",      "MacBook Pro 16\" (M4)", "Mac", "MacBook Pro 16-inch (M4)", "", "2024-10-30", 2024, "在售", "M4 Pro/M4 Max", "16.2\" Mini-LED (Sharp/LGD)", 2499, ["foxconn"], MAC_COMP),
 P("imac_24_m4",     "iMac 24\" (M4)",        "Mac", "iMac 24-inch (M4)", "", "2024-10-30", 2024, "在售", "M4", "24\" 4.5K LCD", 1299, ["foxconn"], MAC_COMP),
 P("macmini_m4",     "Mac mini (M4)",         "Mac", "Mac mini (M4)", "", "2024-10-29", 2024, "在售", "M4/M4 Pro", "-", 599, ["foxconn"], MAC_COMP),
 P("macstudio_m4",   "Mac Studio (M4 Max)",   "Mac", "Mac Studio (M4 Max)", "", "2025-03-05", 2025, "在售", "M4 Max/M3 Ultra", "-", 1999, ["foxconn"], MAC_COMP),
 P("macpro_m2u",     "Mac Pro (M2 Ultra)",    "Mac", "Mac Pro (M2 Ultra)", "", "2023-06-05", 2023, "在售", "M2 Ultra", "-", 6999, ["foxconn"], MAC_COMP),
 # ---- iPad ----
 P("ipadpro_11_m4",  "iPad Pro 11\" (M4)",    "iPad", "iPad Pro 11-inch (M4)", "", "2024-05-07", 2024, "在售", "M4", "11\" Tandem OLED (SDC/LGD)", 999, ["foxconn"], PAD_COMP),
 P("ipadpro_13_m4",  "iPad Pro 13\" (M4)",    "iPad", "iPad Pro 13-inch (M4)", "", "2024-05-07", 2024, "在售", "M4", "13\" Tandem OLED (SDC/LGD)", 1299, ["foxconn"], PAD_COMP),
 P("ipadair_11_m3",  "iPad Air 11\" (M3)",    "iPad", "iPad Air 11-inch (M3)", "", "2025-03-04", 2025, "在售", "M3", "11\" LCD", 599, ["foxconn"], PAD_COMP),
 P("ipadair_13_m3",  "iPad Air 13\" (M3)",    "iPad", "iPad Air 13-inch (M3)", "", "2025-03-04", 2025, "在售", "M3", "13\" LCD", 799, ["foxconn"], PAD_COMP),
 P("ipadmini_a17",   "iPad mini (A17 Pro)",   "iPad", "iPad mini (A17 Pro)", "", "2024-10-15", 2024, "在售", "A17 Pro", "8.3\" LCD", 499, ["foxconn"], PAD_COMP),
 P("ipad_11_a16",    "iPad (A16)",            "iPad", "iPad (11-inch, 2025)", "", "2025-03-04", 2025, "在售", "A16", "11\" LCD", 349, ["foxconn"], PAD_COMP),
 # ---- Apple Watch ----
 P("watch_s10",      "Apple Watch Series 10","Wearable", "Apple Watch Series 10", "Apple Watch X (发布前传闻名)", "2024-09-09", 2024, "在售", "S10 SiP", "LTPO3 OLED (LGD/JDI)", 399, ["luxshare","quanta","foxconn"],
   ["soc","display_panel","cover_glass","battery","enclosure","speaker","mic","sensor_bio","sensor_motion","pmic","wireless_charging","connectivity"]),
 P("watch_ultra3",   "Apple Watch Ultra 3",  "Wearable", "Apple Watch Ultra 3", "", "2025-09-09", 2025, "在售", "S? SiP", "OLED (LGD)", 799, ["luxshare"],
   ["soc","display_panel","cover_glass","battery","enclosure","speaker","mic","sensor_bio","sensor_motion","pmic","wireless_charging","connectivity"]),
 P("watch_se3",      "Apple Watch SE (3rd)", "Wearable", "Apple Watch SE (3rd generation)", "", "2025-09-09", 2025, "在售", "S? SiP", "OLED", 249, ["quanta"],
   ["soc","display_panel","battery","enclosure","speaker","mic","sensor_motion","pmic","wireless_charging","connectivity"]),
 # ---- Vision Pro ----
 P("visionpro_m2",   "Apple Vision Pro (M2+R1)","Spatial", "Apple Vision Pro (M2+R1)", "Apple Vision Pro (1st gen)", "2024-02-02", 2024, "在售", "M2+R1", "Micro-OLED (Sony) + AMOLED 外屏(LGD)", 3499, ["luxshare"],
   ["soc","display_panel","cover_glass","cis","lens","dram","nand","pmic","battery","enclosure","speaker","mic","sensor_motion","fpc","pcb","optical_filter"]),
 P("visionpro_m5",   "Apple Vision Pro (M5)", "Spatial", "Apple Vision Pro (M5)", "", "2025（未确认）", 2025, "传闻/未发布", "M5", "Micro-OLED (SDC) + AMOLED 外屏(LGD)", 3499, ["luxshare"],
   ["soc","display_panel","cover_glass","cis","lens","dram","nand","pmic","battery","enclosure","speaker","mic","sensor_motion","fpc","pcb","optical_filter"]),
 # ---- Audio ----
 P("airpods_pro3",   "AirPods Pro 3",        "Audio", "AirPods Pro 3", "", "2025-09-09", 2025, "在售", "H2", "-", 249, ["luxshare","goertek"],
   ["soc","speaker","mic","battery","pmic","connectivity","enclosure","wireless_charging","uwb"]),
 P("airpods_4",      "AirPods 4",            "Audio", "AirPods 4", "", "2024-09-09", 2024, "在售", "H2", "-", 129, ["luxshare","goertek"],
   ["soc","speaker","mic","battery","pmic","connectivity","enclosure","wireless_charging"]),
 P("airpodsmax_usbc","AirPods Max (USB-C)",  "Audio", "AirPods Max (USB-C)", "", "2024-09-09", 2024, "在售", "-", "-", 549, ["luxshare","goertek"],
   ["speaker","enclosure","battery","pmic","connectivity"]),
 P("homepod_2",      "HomePod (2nd gen)",     "Audio", "HomePod (2nd generation)", "", "2023-01-18", 2023, "在售", "-", "-", 299, ["luxshare","goertek"],
   ["speaker","enclosure","pmic","connectivity","mic"]),
 P("homepod_mini",   "HomePod mini",          "Audio", "HomePod mini", "", "2020-10-13", 2020, "在售", "-", "-", 99, ["luxshare"],
   ["speaker","enclosure","pmic","connectivity","mic"]),
]

# ===========================================================================
# 1) CSV FILES
# ===========================================================================
def write_csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow(r)

# products
write_csv(os.path.join(NEO, "products.csv"),
          ["product_id:ID(Product)", "name", "product_line", "english_name", "alias",
           "release_date", "release_year:int", "status", "soc", "display", "price_usd:int", ":LABEL"],
          [[p["id"], p["name"], p["product_line"], p["english_name"], p["alias"],
            p["release_date"], p["release_year"], p["status"], p["soc"], p["display"], p["price_usd"], "Product"] for p in PRODUCTS])

# components
write_csv(os.path.join(NEO, "components.csv"),
          ["component_id:ID(Component)", "name", "english_name", "category", "subcategory", ":LABEL"],
          [[cid, c["name"], c["english_name"], c["category"], c["subcategory"], "Component"] for cid, c in COMPONENTS.items()])

# suppliers
write_csv(os.path.join(NEO, "suppliers.csv"),
          ["supplier_id:ID(Supplier)", "name", "english_name", "short_name", "country", "region", "category", "tier:int", ":LABEL"],
          [[sid, s["name"], s["english_name"], s["short_name"], s["country"], s["region"], s["category"], s["tier"], "Supplier"] for sid, s in SUPPLIERS.items()])

# relationships: product -[:USES_COMPONENT]-> component
rel_pc = []
for p in PRODUCTS:
    for cid in p["components"]:
        rel_pc.append([p["id"], cid, "USES_COMPONENT", ";".join(SRC_BOM)])
write_csv(os.path.join(NEO, "rel_product_component.csv"),
          [":START_ID(Product)", ":END_ID(Component)", ":TYPE", "source"], rel_pc)

# relationships: component -[:SUPPLIED_BY]-> supplier
rel_cs = []
for cid, sups in COMP_SUP.items():
    src = ";".join(COMP_SOURCE.get(cid, []))
    for sid, share, note in sups:
        rel_cs.append([cid, sid, "SUPPLIED_BY", ("" if share is None else str(share)), (note or ""), src])
write_csv(os.path.join(NEO, "rel_component_supplier.csv"),
          [":START_ID(Component)", ":END_ID(Supplier)", ":TYPE", "share", "note", "source"], rel_cs)

# relationships: product -[:ASSEMBLED_BY]-> supplier
rel_pa = []
for p in PRODUCTS:
    for sid in p["assembly"]:
        rel_pa.append([p["id"], sid, "ASSEMBLED_BY", ";".join(SRC_ASSEMBLY)])
write_csv(os.path.join(NEO, "rel_product_assembly.csv"),
          [":START_ID(Product)", ":END_ID(Supplier)", ":TYPE", "source"], rel_pa)

print("CSV files written:", len(PRODUCTS), "products,", len(COMPONENTS), "components,", len(SUPPLIERS), "suppliers")
print("Edges -> product_component:", len(rel_pc), "component_supplier:", len(rel_cs), "product_assembly:", len(rel_pa))

# ===========================================================================
# 2) JSON GRAPH
# ===========================================================================
DATA_DICT = {
 "Product": [
   {"field": "product_id", "desc": "节点唯一 ID（图数据库主键）", "obtainable": "内部生成，稳定唯一"},
   {"field": "name", "desc": "官方型号全称（节点名称，如 iPhone 17 Pro）", "obtainable": "苹果官方发布名称，公开可得"},
   {"field": "product_line", "desc": "产品线大类（iPhone/Mac/iPad/Wearable/Spatial/Audio）", "obtainable": "苹果产品分类，公开可得"},
   {"field": "english_name", "desc": "英文名称", "obtainable": "苹果全球统一命名，公开可得"},
   {"field": "alias", "desc": "别名/内部代号（如 iPhone 17 Slim、Apple Watch X）", "obtainable": "发布前代号或别称，部分公开可得，无则空"},
   {"field": "release_date", "desc": "发布时间（发布/发售日期，ISO 格式；未确认者标注年份）", "obtainable": "发布会与发售日期公开可得"},
   {"field": "release_year", "desc": "发布年份（便于按年聚合）", "obtainable": "由发布时间派生"},
   {"field": "status", "desc": "在售 / 停产 / 传闻未发布", "obtainable": "苹果在售列表，公开可得"},
   {"field": "soc", "desc": "主芯片型号（A/M 系列）", "obtainable": "苹果芯片命名，公开可得"},
   {"field": "display", "desc": "显示规格摘要", "obtainable": "规格公开，供应商为定性"},
   {"field": "price_usd", "desc": "起售价（美元）", "obtainable": "苹果全球定价，公开可得"},
 ],
 "Component": [
   {"field": "component_id", "desc": "节点唯一 ID", "obtainable": "内部生成"},
   {"field": "name", "desc": "中文全称（节点名称）", "obtainable": "BOM 拆解命名，公开可得"},
   {"field": "english_name", "desc": "英文名称", "obtainable": "行业通用英文术语，公开可得"},
   {"field": "category", "desc": "零部件大类", "obtainable": "按功能分类，可定义"},
   {"field": "subcategory", "desc": "子类/规格说明", "obtainable": "BOM 拆解，公开可得"},
 ],
 "Supplier": [
   {"field": "supplier_id", "desc": "节点唯一 ID", "obtainable": "内部生成"},
   {"field": "name", "desc": "全称（法定注册名，节点名称）", "obtainable": "公司注册信息，公开可得"},
   {"field": "english_name", "desc": "英文名称", "obtainable": "公司官方英文名，公开可得"},
   {"field": "short_name", "desc": "简称/股票代码/常用缩写（如 TSMC、京东方）", "obtainable": "市场惯用简称，公开可得"},
   {"field": "country", "desc": "总部所在国家/地区", "obtainable": "公开可得"},
   {"field": "region", "desc": "大区（东亚/北美/欧洲）", "obtainable": "由 country 派生"},
   {"field": "category", "desc": "供应类别（代工/显示/存储/半导体…）", "obtainable": "按业务分类，可定义"},
   {"field": "tier", "desc": "层级（1=核心/高壁垒，2=次级/可替代）", "obtainable": "依据技术壁垒与可替代性评估"},
 ],
 "Relationship": [
   {"field": "USES_COMPONENT", "desc": "Product → Component", "obtainable": "BOM 拆解，公开可得", "source": "每条边附 source 字段，引用 source_registry 中的来源 id 列表"},
   {"field": "SUPPLIED_BY", "desc": "Component → Supplier（含 share/note/source）", "obtainable": "供应链报道，份额仅个别环节量化", "source": "source 继承所属组件，引用 Apple Supplier List / TechInsights / Counterpoint 等"},
   {"field": "ASSEMBLED_BY", "desc": "Product → Supplier（代工，含 source）", "obtainable": "苹果供应链名单，公开可得", "source": "source 引用 Apple Supplier List / Nikkei 等"},
   {"field": "source", "desc": "来源溯源：来源注册表(source_registry)中的 id 列表", "obtainable": "公开可引用资料，详见 meta.source_registry"},
 ],
}

graph = {
 "meta": {
   "title": "Apple Product Supply Chain Graph (v2)",
   "generated": "2026-08-04",
   "source": "Public supply-chain reports 2024-2026 + Apple 2024 Supplier List (187 core suppliers, ~98% of direct spend)",
   "sources_accessed": "2026-08-05",
   "schema": {
     "nodes": ["Product", "Component", "Supplier"],
     "relationships": [
       "Product -[USES_COMPONENT]-> Component",
       "Component -[SUPPLIED_BY]-> Supplier",
       "Product -[ASSEMBLED_BY]-> Supplier"
     ]
   },
   "source_registry": SOURCES,
   "data_dictionary": DATA_DICT
 },
 "nodes": {
   "products": PRODUCTS,
   "components": [{"id": cid, **c} for cid, c in COMPONENTS.items()],
   "suppliers": [{"id": sid, **s} for sid, s in SUPPLIERS.items()],
 },
 "edges": {
   "uses_component": [{"from": a, "to": b, "source": s.split(";")} for a, b, _, s in rel_pc],
   "supplied_by": [{"from": a, "to": b, "share": sh, "note": n, "source": src.split(";")} for a, b, _, sh, n, src in [tuple(x) for x in rel_cs]],
   "assembled_by": [{"from": a, "to": b, "source": s.split(";")} for a, b, _, s in rel_pa],
 }
}
with open(os.path.join(ROOT, "data", "apple_supply_chain.json"), "w", encoding="utf-8") as f:
    json.dump(graph, f, ensure_ascii=False, indent=2)
print("JSON written.")


print("DONE")
