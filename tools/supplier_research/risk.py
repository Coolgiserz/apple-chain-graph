# -*- coding: utf-8 -*-
"""
供应链脆弱性分析引擎 (Supply Chain Vulnerability Engine)
=========================================================

模型（朴素 / 基础口径，对齐「零部件 → 产品 → 产品线」自下而上聚合）：

  1) 零部件脆弱性
     V_comp(c) = 1 / n_c
       n_c = 组件 c 的供应商数量（来自 SUPPLIED_BY 边）
       · n_c == 1  → V = 1.0  单点依赖（单点失效即断供）
       · n_c == 0  → 视作单点（缺供应数据，按最脆弱处理），V = 1.0
       · n_c 越大  → 越可替代，V 越小
     直觉：一个部件越少供应商，潜在越脆弱（单点依赖风险）。

  2) 产品脆弱性（零部件脆弱性聚合）
     product_vuln = w_mean * mean_v   （整体暴露：零部件脆弱性均值）
                  + w_weak * weakest  （最弱环节：零部件中最大脆弱性）
                  + w_sp   * sp_rate  （单点占比：单点部件数 / 部件总数）
     三项均落在 [0,1]，加权求和 → 产品脆弱性亦在 [0,1]。

  3) 产品线脆弱性（产品脆弱性上卷）
     按 product_line 取产品脆弱性的均值，并汇总最弱环节与单点总数，
     用于回答「哪条产品线整体最脆弱」。

可选的次级信号（仅展示、不计入主分数，便于后续扩展）：
   · 地理分散度：组件供应商覆盖的不同国家数 distinct_countries。
     同国多源 ≠ 真冗余，故在组件详情中给出，供人工判断。

依赖：仅 Python 标准库。
数据：data/apple_supply_chain.json（图谱单一来源）。
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))            # <repo>/
DATA = os.path.join(REPO, "data")
GRAPH_JSON = os.path.join(DATA, "apple_supply_chain.json")

# 产品脆弱性综合权重（权重和=1，各项自身在 [0,1]）
W_MEAN = 0.5     # 零部件脆弱性均值（整体暴露）
W_WEAK = 0.3     # 最弱环节（最大单部件脆弱性）
W_SP = 0.2       # 单点部件占比

# 脆弱性分档阈值（用于风险等级标注）
HIGH_THRESHOLD = 0.6
MEDIUM_THRESHOLD = 0.3


def load_graph(path=None):
    with open(path or GRAPH_JSON, encoding="utf-8") as f:
        return json.load(f)


def build_component_supplier_map(graph):
    """component_id -> [supplier_id, ...]（来自 SUPPLIED_BY 边）。"""
    m = {}
    for e in graph["edges"].get("supplied_by", []):
        m.setdefault(e["from"], []).append(e["to"])
    return m


def build_product_component_map(graph):
    """product_id -> [component_id, ...]（来自 USES_COMPONENT 边）。"""
    m = {}
    for e in graph["edges"].get("uses_component", []):
        m.setdefault(e["from"], []).append(e["to"])
    return m


def _supplier_countries(graph):
    out = {}
    for s in graph["nodes"].get("suppliers", []):
        out[s["id"]] = s.get("country", "")
    return out


def component_vulnerability(graph):
    """计算每个组件的脆弱性。

    返回 dict: component_id -> {
        n_suppliers, vuln, single_point, missing_data,
        suppliers:[id], distinct_countries, countries:[...]
    }
    """
    c2s = build_component_supplier_map(graph)
    country_of = _supplier_countries(graph)
    comps = {c["id"]: c for c in graph["nodes"].get("components", [])}

    out = {}
    for cid in comps:
        suppliers = c2s.get(cid, [])
        n = len(suppliers)
        missing = (n == 0)
        # 单点定义：恰好 1 个供应商，或完全缺供应数据
        single_point = (n <= 1)
        vuln = 1.0 / n if n > 0 else 1.0
        countries = sorted({country_of.get(s, "") for s in suppliers if country_of.get(s)})
        out[cid] = {
            "component_id": cid,
            "name": comps[cid].get("name", cid),
            "category": comps[cid].get("category", ""),
            "n_suppliers": n,
            "vuln": vuln,
            "single_point": single_point,
            "missing_data": missing,
            "suppliers": suppliers,
            "distinct_countries": len(countries),
            "countries": countries,
        }
    return out


def product_vulnerability(graph):
    """计算每个产品的脆弱性（零部件脆弱性自下而上聚合）。"""
    p2c = build_product_component_map(graph)
    comp_vuln = component_vulnerability(graph)
    prods = {p["id"]: p for p in graph["nodes"].get("products", [])}

    out = {}
    for pid in prods:
        comp_ids = p2c.get(pid, [])
        if not comp_ids:
            out[pid] = {
                "product_id": pid,
                "name": prods[pid].get("name", pid),
                "product_line": prods[pid].get("product_line", ""),
                "n_components": 0,
                "mean_v": 0.0, "weakest": 0.0, "weakest_component": None,
                "sp_count": 0, "sp_rate": 0.0,
                "product_vuln": 0.0, "tier": "低",
                "components": [],
            }
            continue
        vs = [comp_vuln[c]["vuln"] for c in comp_ids]
        sp = [c for c in comp_ids if comp_vuln[c]["single_point"]]
        mean_v = sum(vs) / len(vs)
        weakest = max(vs)
        weakest_cid = comp_ids[vs.index(weakest)]
        sp_rate = len(sp) / len(comp_ids)
        pv = W_MEAN * mean_v + W_WEAK * weakest + W_SP * sp_rate
        out[pid] = {
            "product_id": pid,
            "name": prods[pid].get("name", pid),
            "product_line": prods[pid].get("product_line", ""),
            "n_components": len(comp_ids),
            "mean_v": mean_v,
            "weakest": weakest,
            "weakest_component": weakest_cid,
            "sp_count": len(sp),
            "sp_rate": sp_rate,
            "product_vuln": pv,
            "tier": tier_of(pv),
            "components": [
                {
                    "component_id": c,
                    "name": comp_vuln[c]["name"],
                    "vuln": comp_vuln[c]["vuln"],
                    "n_suppliers": comp_vuln[c]["n_suppliers"],
                    "single_point": comp_vuln[c]["single_point"],
                }
                for c in comp_ids
            ],
        }
    return out


def product_line_vulnerability(graph):
    """按产品线汇总（产品脆弱性上卷）。"""
    p_vuln = product_vulnerability(graph)
    lines = {}
    for pid, rec in p_vuln.items():
        line = rec["product_line"] or "未分类"
        lines.setdefault(line, []).append(rec)

    out = {}
    for line, recs in lines.items():
        n_prods = len(recs)
        mean_pv = sum(r["product_vuln"] for r in recs) / n_prods
        mean_weak = sum(r["weakest"] for r in recs) / n_prods
        total_sp = sum(r["sp_count"] for r in recs)
        total_comps = sum(r["n_components"] for r in recs)
        sp_rate = total_sp / total_comps if total_comps else 0.0
        # 最脆弱产品与最脆弱单部件
        worst_prod = max(recs, key=lambda r: r["product_vuln"])
        out[line] = {
            "product_line": line,
            "n_products": n_prods,
            "mean_product_vuln": mean_pv,
            "tier": tier_of(mean_pv),
            "mean_weakest": mean_weak,
            "single_point_total": total_sp,
            "single_point_rate": sp_rate,
            "worst_product": {
                "product_id": worst_prod["product_id"],
                "name": worst_prod["name"],
                "product_vuln": worst_prod["product_vuln"],
            },
        }
    return out


def tier_of(v):
    if v >= HIGH_THRESHOLD:
        return "高"
    if v >= MEDIUM_THRESHOLD:
        return "中"
    return "低"


def analyze(graph=None):
    """一次性计算全部层级，返回结构化结果（含 meta）。"""
    g = graph if graph is not None else load_graph()
    comp = component_vulnerability(g)
    prod = product_vulnerability(g)
    line = product_line_vulnerability(g)
    return {
        "meta": {
            "model": "component_supplier_count_v1",
            "weights": {"mean": W_MEAN, "weakest": W_WEAK, "single_point_rate": W_SP},
            "thresholds": {"high": HIGH_THRESHOLD, "medium": MEDIUM_THRESHOLD},
            "n_products": len(g["nodes"].get("products", [])),
            "n_components": len(g["nodes"].get("components", [])),
            "n_suppliers": len(g["nodes"].get("suppliers", [])),
        },
        "components": comp,
        "products": prod,
        "product_lines": line,
    }
