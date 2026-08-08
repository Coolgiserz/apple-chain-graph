# -*- coding: utf-8 -*-
"""
供应商分析编排 (Analysis Orchestrator)
把三块信息合并成一个可分析的数据集，并跑估值引擎：
  1) universe.py     -> 代码/交易所/币种/是否上市
  2) graph JSON      -> 名称/类别(tier)/国家（来自 generate.py 产出）
  3) fundamentals.csv-> 基本面与估值倍数 + 趋势/近况 + 来源（由 Web 研究填充，人工可核）
合并后对每个供应商调用 valuation.evaluate() 得到 高估/低估/合理 判定。
"""
import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))           # <repo>/
DATA = os.path.join(REPO, "data")
FUND_CSV = os.path.join(HERE, "..", "data", "supplier_fundamentals.csv")
GRAPH_JSON = os.path.join(DATA, "apple_supply_chain.json")

from . import universe
from . import valuation


def load_graph_suppliers():
    with open(GRAPH_JSON, encoding="utf-8") as f:
        g = json.load(f)
    out = {}
    for s in g["nodes"]["suppliers"]:
        out[s["id"]] = s
    return out


def load_fundamentals():
    """返回 dict: supplier_id -> {as_of, market_cap_usd_b, ...}；空文件/缺列时给空 dict。"""
    if not os.path.exists(FUND_CSV):
        return {}
    out = {}
    with open(FUND_CSV, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            sid = row.get("supplier_id", "").strip()
            if not sid:
                continue
            out[sid] = row
    return out


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def build_dataset():
    """合并三源，返回 list[dict]，含估值判定。"""
    graph_sups = load_graph_suppliers()
    funds = load_fundamentals()

    # 先收集所有 metrics（用于同业中位计算）
    metrics_by_id = {}
    records = []
    for sid, g in graph_sups.items():
        u = universe.get(sid) or {}
        f = funds.get(sid, {})
        rec = {
            "id": sid,
            "name": g.get("name"),
            "short_name": g.get("short_name"),
            "english_name": g.get("english_name"),
            "category": g.get("category"),
            "tier": g.get("tier"),
            "country": g.get("country"),
            "ticker": u.get("ticker", ""),
            "exchange": u.get("exchange", ""),
            "currency": u.get("currency", ""),
            "listed": u.get("listed", False),
            "peer_group": universe.sector_of(sid) or g.get("category"),  # 估值同业组 = sector
            "as_of": f.get("as_of", ""),
            "market_cap_usd_b": _num(f.get("market_cap_usd_b")),
            "revenue_ttm_usd_b": _num(f.get("revenue_ttm_usd_b")),
            "net_income_ttm_usd_b": _num(f.get("net_income_ttm_usd_b")),
            "gross_margin_pct": _num(f.get("gross_margin_pct")),
            "net_margin_pct": _num(f.get("net_margin_pct")),
            "roe_pct": _num(f.get("roe_pct")),
            "pe": _num(f.get("pe")),
            "pb": _num(f.get("pb")),
            "ev_ebitda": _num(f.get("ev_ebitda")),
            "debt_to_equity": _num(f.get("debt_to_equity")),
            "trend": f.get("trend", ""),
            "recent": f.get("recent", ""),
            "source": f.get("source", ""),
            "has_fundamentals": bool(f),
        }
        metrics_by_id[sid] = rec
        records.append(rec)

    # 跑估值（需要全体 metrics 才能算同业中位）
    for rec in records:
        # 苹果是终端厂/客户，仅作估值基准对照，不参与供应商同业比较
        if rec["id"] == "apple":
            rec["valuation"] = {
                "verdict": "基准（终端厂，非供应商）",
                "score": None,
                "detail": ["苹果为终端厂/客户，此处仅作估值基准对照，不参与供应商同业比较。"],
                "peer_group": rec["peer_group"],
                "peer_count": 0,
                "benchmark": True,
            }
            continue
        if rec["listed"] and rec["has_fundamentals"]:
            rec["valuation"] = valuation.evaluate(rec, metrics_by_id)
        else:
            rec["valuation"] = {
                "verdict": "定性（未上市/无倍数）",
                "score": None,
                "detail": ["非公开上市或缺少估值倍数，仅作定性判断。"],
                "peer_group": rec["peer_group"],
                "peer_count": 0,
            }
    return records


def verdict_counts(records):
    from collections import Counter
    c = Counter(r["valuation"]["verdict"] for r in records)
    return dict(c)
