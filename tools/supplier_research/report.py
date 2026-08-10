# -*- coding: utf-8 -*-
"""渲染供应商分析报告：markdown 全文 + 结构化 JSON。"""

import json
import os
from . import universe

VERDICT_EMOJI = {"低估": "🔵", "高估": "🔴", "合理": "🟢", "困境": "⚠️"}


def _md_escape(s):
    return (s or "").replace("|", "\\|").replace("\n", " ")


def render_markdown(records, meta=None):
    meta = meta or {}
    lines = []
    lines.append("# 苹果供应商基本面与估值分析\n")
    lines.append(f"> 生成时间：{meta.get('generated','')} ｜ 数据截至(as_of)：{meta.get('as_of','')}  ")
    lines.append(f"> 方法：同业相对估值（当前倍数 vs 同业组中位，见 `valuation.py`）\n")

    # 概览表
    from .analysis import verdict_counts
    vc = verdict_counts(records)
    lines.append("## 一、估值结论概览\n")
    lines.append("| 判定 | 数量 |")
    lines.append("| --- | --- |")
    for k in ["低估", "合理", "高估", "困境（亏损）·倍数失真", "基准（终端厂，非供应商）", "定性（未上市/无倍数）", "N/A（缺倍数或无可比同业）"]:
        if k in vc:
            lines.append(f"| {VERDICT_EMOJI.get(k.split('（')[0],'')} {k} | {vc[k]} |")
    lines.append("")

    # 明细表（按 verdict 排序：低估→合理→高估）
    order = {"低估": 0, "合理": 1, "高估": 2}
    def sortkey(r):
        v = r["valuation"]["verdict"]
        return (order.get(v, 9), r["short_name"] or r["name"])
    rows = sorted(records, key=sortkey)

    lines.append("## 二、全部供应商估值速览\n")
    lines.append("| 供应商 | 代码 | 类别 | 市值(USDbn) | P/E | P/B | EV/EBITDA | 判定 |")
    lines.append("| --- | --- | --- | ---: | ---: | ---: | ---: | --- |")
    for r in rows:
        v = r["valuation"]
        code = r["ticker"] or "未上市"
        mc = f"{r['market_cap_usd_b']:.1f}" if isinstance(r["market_cap_usd_b"], (int, float)) else "-"
        pe = f"{r['pe']:.1f}" if isinstance(r["pe"], (int, float)) else "-"
        pb = f"{r['pb']:.1f}" if isinstance(r["pb"], (int, float)) else "-"
        ev = f"{r['ev_ebitda']:.1f}" if isinstance(r["ev_ebitda"], (int, float)) else "-"
        lines.append(f"| {_md_escape(r['short_name'] or r['name'])} | {code} | {_md_escape(r['category'])} | {mc} | {pe} | {pb} | {ev} | {VERDICT_EMOJI.get(v['verdict'],'')} {v['verdict']} |")
    lines.append("")

    # 重点供应商逐家分析（仅对含基本面的做展开）
    lines.append("## 三、重点供应商逐家分析（含基本面/趋势/近况/来源）\n")
    detailed = [r for r in rows if r.get("has_fundamentals")]
    if not detailed:
        lines.append("_尚未填充基本面数据（见 `tools/data/supplier_fundamentals.csv`），以下仅列定性结论。_\n")
    for r in detailed:
        v = r["valuation"]
        lines.append(f"### {r['short_name'] or r['name']}（{_md_escape(r['english_name'] or '')}）\n")
        lines.append(f"- **代码**：{r['ticker'] or '未上市'} ｜ **交易所**：{r['exchange'] or '-'} ｜ **类别**：{r['category']} ｜ **层级**：T{r['tier']} ｜ **总部**：{r['country']}")
        if isinstance(r["market_cap_usd_b"], (int, float)):
            lines.append(f"- **市值**：{r['market_cap_usd_b']:.1f} 十亿美元 ｜ **营收(TTM)**：{r['revenue_ttm_usd_b']:.1f} 十亿美元 ｜ **净利(TTM)**：{r['net_income_ttm_usd_b']:.1f} 十亿美元")
        if isinstance(r["gross_margin_pct"], (int, float)):
            gm = f"{r['gross_margin_pct']:.1f}%" if isinstance(r["gross_margin_pct"], (int, float)) else "-"
            nm = f"{r['net_margin_pct']:.1f}%" if isinstance(r["net_margin_pct"], (int, float)) else "-"
            roe = f"{r['roe_pct']:.1f}%" if isinstance(r["roe_pct"], (int, float)) else "-"
            de = f"{r['debt_to_equity']:.2f}" if isinstance(r["debt_to_equity"], (int, float)) else "-"
            lines.append(f"- **毛利率**：{gm} ｜ **净利率**：{nm} ｜ **ROE**：{roe} ｜ **负债权益比**：{de}")
        lines.append(f"- **估值倍数**：P/E {r['pe'] if isinstance(r['pe'],(int,float)) else '-'} ｜ P/B {r['pb'] if isinstance(r['pb'],(int,float)) else '-'} ｜ EV/EBITDA {r['ev_ebitda'] if isinstance(r['ev_ebitda'],(int,float)) else '-'}")
        lines.append(f"- **估值判定**：{VERDICT_EMOJI.get(v['verdict'],'')} **{v['verdict']}**（score={v['score']}）")
        for d in v.get("detail", []):
            lines.append(f"  - {d}")
        if r.get("trend"):
            lines.append(f"- **发展趋势**：{r['trend']}")
        if r.get("recent"):
            lines.append(f"- **近况**：{r['recent']}")
        if r.get("source"):
            lines.append(f"- **数据来源**：{r['source']}")
        lines.append("")

    lines.append("## 四、方法与局限性\n")
    lines.append("- 估值为**同业相对估值**（当前倍数 / 同业组中位），非 DCF 绝对估值；结论需结合趋势与近况定性修正。")
    lines.append("- 同业组取更宽的 **sector** 分组（见 `universe.py` 的 `SECTOR`）：存储 / 逻辑芯片 / 显示 / 封测 / 光学 / 摄像头 / 组装 / 结构件 / 电池 / PCB / 元器件。若某 sector 内可比样本 < 2 家，则**自动回退到全样本中位**并标注，保证每家上市供应商都能得到定量判定。")
    lines.append("- 苹果为终端厂/客户，单独列为 `OEM(Benchmark)` 基准，不参与供应商同业比较。")
    lines.append("- 财务与倍数来自 `tools/data/supplier_fundamentals.csv`，由各供应商公开资料(财报/行情/行业研究，主要为 stockanalysis.com / Yahoo Finance)整理，**含来源链接，人工可核**；跨市场比较已统一换算为 USD（TWD≈32、KRW≈1400、JPY≈155、CNY≈7.2、HKD≈7.8 粗略汇率），但汇率与宏观波动仍会带来偏差。各数值为 2026 年 7–8 月近一个月行情快照，价格随市波动，结论应视为某一时点的相对判断。")
    lines.append("- 由于本次仅对 15 家重点供应商填充了基本面，部分 sector 组内仅有 2 家可比（如 Logic Semi、Display、Components、Assembly 为两两相对；Foundry/CIS·Camera/Optics/OSAT 仅 1 家则回退全样本中位）。判定方向通常合理，但幅度敏感，务必结合趋势/近况定性修正。")
    lines.append("- 未上市公司（如三星显示、博世、ATL、伯恩、铠侠）无公开倍数，仅作定性分析。")
    return "\n".join(lines)


def render_json(records, meta=None):
    return {
        "meta": meta or {},
        "suppliers": [
            {
                "id": r["id"],
                "name": r["name"],
                "short_name": r["short_name"],
                "ticker": r["ticker"],
                "category": r["category"],
                "peer_group": r["peer_group"],
                "market_cap_usd_b": r["market_cap_usd_b"],
                "revenue_ttm_usd_b": r["revenue_ttm_usd_b"],
                "net_income_ttm_usd_b": r["net_income_ttm_usd_b"],
                "gross_margin_pct": r["gross_margin_pct"],
                "net_margin_pct": r["net_margin_pct"],
                "roe_pct": r["roe_pct"],
                "pe": r["pe"], "pb": r["pb"], "ev_ebitda": r["ev_ebitda"],
                "valuation": r["valuation"],
                "trend": r["trend"], "recent": r["recent"], "source": r["source"],
            }
            for r in records
        ],
    }
