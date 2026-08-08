#!/usr/bin/env python3
"""生成供应商舆情分析报告。

用法:
    python tools/run_sentiment.py [--md PATH] [--json]

输出:
    tools/output/supplier_sentiment.md  (默认)
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "supplier_research"))

import sentiment as S  # noqa: E402

OUT_DIR = os.path.join(HERE, "output")
DEFAULT_MD = os.path.join(OUT_DIR, "supplier_sentiment.md")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", default=DEFAULT_MD, help="输出 Markdown 路径")
    ap.add_argument("--id", help="仅输出指定 supplier_id（调试用）")
    args = ap.parse_args()

    sent = S.load_sentiment()
    if args.id:
        sent = {k: v for k, v in sent.items() if k == args.id}
    names = S.load_names()
    valuation = S.load_valuation()

    as_of = sorted({r["as_of"] for r in sent.values()}, reverse=True)[0] if sent else "—"

    md = []
    md.append(f"# 苹果供应链关键供应商 · 舆情分析报告\n")
    md.append(f"> 快照日期：{as_of} ｜ 覆盖 {len(sent)} 家（重点供应商） ｜ 数据来源：公开新闻与卖方研报（见各条来源链接）\n")
    md.append("---\n")
    md.append(S.build_full_report(sent, names, valuation))
    md.append("\n---\n")
    md.append("## 三、方法与局限\n")
    md.append("- **新闻情绪**：基于 2026 年近期（近数月）主流财经媒体/新闻的报道基调综合判断，分为正面 / 中性 / 负面。\n")
    md.append("- **分析师情绪**：基于卖方的评级分布与共识方向（看多 / 中性 / 看空），并给出平均目标价与上行空间（若有）。\n")
    md.append("- **数据来源**：每条均附可点击的来源链接（stockanalysis.com 分析师共识页、Reuters/Bloomberg/Nikkei/Yahoo Finance/券商研报等），可人工核验。\n")
    md.append("- **局限**：① 舆情为**定性+共识**判断，非量化模型；② 跨市场（美/台/韩/日/中）分析师覆盖密度差异大，A 股/台股部分以本地券商与中文财经媒体为主；③ 快照时点敏感，目标价与情绪会随股价与财报快速变化；④ 本分析仅用于产业链研究/教学，**不构成任何投资或采购建议**。\n")

    text = "\n".join(md)
    os.makedirs(os.path.dirname(args.md), exist_ok=True)
    with open(args.md, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"已写入舆情报告: {args.md}  (供应商 {len(sent)} 家)")


if __name__ == "__main__":
    main()
