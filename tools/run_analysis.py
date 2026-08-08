# -*- coding: utf-8 -*-
"""
供应商分析 CLI
用法：
  python tools/run_analysis.py                 # 分析全部供应商，输出到 tools/output/
  python tools/run_analysis.py --id tsmc       # 仅分析某一家，打印到 stdout
  python tools/run_analysis.py --md out.md --json out.json

依赖：仅 Python 标准库。
数据：tools/data/supplier_fundamentals.csv（基本面与倍数，由公开资料整理，含来源）。
      若某供应商未在该 CSV 中，则仅做定性（未上市/缺数据）结论。
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from supplier_research import analysis, report  # noqa: E402

REPO = os.path.dirname(HERE)
OUT_DIR = os.path.join(HERE, "output")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", help="仅分析指定 supplier_id（如 tsmc）")
    ap.add_argument("--md", help="markdown 输出路径")
    ap.add_argument("--json", help="json 输出路径")
    ap.add_argument("--as_of", default="", help="数据截止日期标注")
    args = ap.parse_args()

    records = analysis.build_dataset()
    meta = {"generated": "2026-08-05", "as_of": args.as_of or "见各供应商 as_of 字段"}

    if args.id:
        rec = next((r for r in records if r["id"] == args.id), None)
        if not rec:
            print(f"未找到 supplier_id={args.id}")
            return 1
        print(report.render_markdown([rec], meta))
        return 0

    md = report.render_markdown(records, meta)
    js = report.render_json(records, meta)

    out_md = args.md or os.path.join(OUT_DIR, "supplier_analysis.md")
    out_json = args.json or os.path.join(OUT_DIR, "supplier_analysis.json")
    os.makedirs(os.path.dirname(out_md), exist_ok=True)
    with open(out_md, "w", encoding="utf-8") as f:
        f.write(md)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(js, f, ensure_ascii=False, indent=2)

    from collections import Counter
    vc = Counter(r["valuation"]["verdict"] for r in records)
    print(f"已写出：\n  {out_md}\n  {out_json}")
    print("估值分布：", dict(vc))
    covered = sum(1 for r in records if r.get("has_fundamentals"))
    print(f"已填充基本面：{covered}/{len(records)} 家")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
