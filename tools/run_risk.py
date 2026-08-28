# -*- coding: utf-8 -*-
"""
供应链脆弱性分析 CLI
用法：
  python tools/run_risk.py                  # 全量分析，输出到 tools/output/
  python tools/run_risk.py --top 5          # 仅打印 Top5 最脆弱产品线/产品/部件
  python tools/run_risk.py --md out.md --json out.json

依赖：仅 Python 标准库。
模型：零部件脆弱性 = 1 / 供应商数；产品 = 均值+最弱+单点率；产品线 = 产品均值上卷。
详见 tools/supplier_research/risk.py。
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from supplier_research import risk  # noqa: E402

OUT_DIR = os.path.join(HERE, "output")


def render_markdown(result, generated):
    meta = result["meta"]
    lines = []
    lines.append("# 供应链脆弱性分析报告")
    lines.append("")
    lines.append(f"- 生成时间：{generated}")
    lines.append(f"- 模型：`{meta['model']}`（零部件供应商数量口径）")
    lines.append(f"- 数据规模：{meta['n_products']} 产品 / "
                 f"{meta['n_components']} 组件 / {meta['n_suppliers']} 供应商")
    lines.append(f"- 产品综合权重：均值 {meta['weights']['mean']} / "
                 f"最弱 {meta['weights']['weakest']} / "
                 f"单点率 {meta['weights']['single_point_rate']}")
    lines.append("")

    # 1) 产品线排名
    lines.append("## 一、产品线脆弱性排名（最脆弱在前）")
    lines.append("")
    lines.append("| 排名 | 产品线 | 产品数 | 平均脆弱性 | 风险等级 | "
                 "最弱环节均值 | 单点部件总数 | 单点占比 | 最脆弱产品 |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    ranked_lines = sorted(
        result["product_lines"].values(),
        key=lambda r: r["mean_product_vuln"], reverse=True)
    for i, r in enumerate(ranked_lines, 1):
        wp = r["worst_product"]
        lines.append(
            f"| {i} | {r['product_line']} | {r['n_products']} | "
            f"{r['mean_product_vuln']:.3f} | {r['tier']} | "
            f"{r['mean_weakest']:.3f} | {r['single_point_total']} | "
            f"{r['single_point_rate']*100:.1f}% | {wp['name']} ({wp['product_vuln']:.3f}) |")
    lines.append("")

    # 2) 单点依赖部件 Top（最脆弱零部件）
    lines.append("## 二、最脆弱零部件 Top（单点依赖优先）")
    lines.append("")
    comps = list(result["components"].values())
    comps.sort(key=lambda c: (c["vuln"], c["n_suppliers"]), reverse=True)
    top_comps = comps[:15]
    lines.append("| 零部件 | 类别 | 供应商数 | 脆弱性 | 单点 | 覆盖国家 |")
    lines.append("|---|---|---|---|---|---|")
    for c in top_comps:
        flag = "✓" if c["single_point"] else ""
        note = "（缺供应数据）" if c["missing_data"] else ""
        lines.append(
            f"| {c['name']}{note} | {c['category']} | {c['n_suppliers']} | "
            f"{c['vuln']:.3f} | {flag} | {c['distinct_countries']} |")
    lines.append("")

    # 3) 最脆弱产品 Top
    lines.append("## 三、最脆弱产品 Top")
    lines.append("")
    prods = list(result["products"].values())
    prods.sort(key=lambda p: p["product_vuln"], reverse=True)
    lines.append("| 产品 | 产品线 | 部件数 | 脆弱性 | 风险等级 | "
                 "最弱环节 | 单点部件数 |")
    lines.append("|---|---|---|---|---|---|---|")
    for p in prods[:15]:
        wc = result["components"].get(p["weakest_component"], {})
        wc_name = wc.get("name", p["weakest_component"] or "-")
        lines.append(
            f"| {p['name']} | {p['product_line']} | {p['n_components']} | "
            f"{p['product_vuln']:.3f} | {p['tier']} | "
            f"{wc_name} ({p['weakest']:.3f}) | {p['sp_count']} |")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("**方法说明**：零部件脆弱性 `V = 1 / 供应商数`，供应商越少越脆弱；"
                 "产品脆弱性 = 零部件脆弱性均值(整体暴露) + 最弱环节(最大单部件脆弱性) "
                 "+ 单点部件占比，按权重综合；产品线取产品脆弱性均值上卷。"
                 "地理分散度仅作参考字段，未计入主分数。")
    lines.append("")
    return "\n".join(lines)


def render_json(result, generated):
    return {
        "generated": generated,
        "meta": result["meta"],
        "product_lines": sorted(
            result["product_lines"].values(),
            key=lambda r: r["mean_product_vuln"], reverse=True),
        "products": sorted(
            result["products"].values(),
            key=lambda p: p["product_vuln"], reverse=True),
        "components": sorted(
            result["components"].values(),
            key=lambda c: (c["vuln"], c["n_suppliers"]), reverse=True),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=0,
                    help="仅打印 Top N 最脆弱产品线/产品/部件（0=全量文件输出）")
    ap.add_argument("--md", help="markdown 输出路径")
    ap.add_argument("--json", help="json 输出路径")
    ap.add_argument("--as_of", default="", help="数据截止日期标注")
    args = ap.parse_args()

    # P1-#6：生成时间戳动态化（曾硬编码 "2026-08-09"，重跑旧产物会误导读者以为数据未更新）
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    as_of = args.as_of or "见图谱 meta.source"
    result = risk.analyze()

    md = render_markdown(result, generated)
    js = render_json(result, generated)
    js["meta"]["as_of"] = as_of

    if args.top:
        # 精简打印模式
        ranked_lines = sorted(
            result["product_lines"].values(),
            key=lambda r: r["mean_product_vuln"], reverse=True)[:args.top]
        print(f"Top {args.top} 最脆弱产品线：")
        for i, r in enumerate(ranked_lines, 1):
            print(f"  {i}. {r['product_line']}  脆弱性={r['mean_product_vuln']:.3f} "
                  f"({r['tier']})  单点部件={r['single_point_total']}")
        prods = sorted(result["products"].values(),
                       key=lambda p: p["product_vuln"], reverse=True)[:args.top]
        print(f"\nTop {args.top} 最脆弱产品：")
        for i, p in enumerate(prods, 1):
            print(f"  {i}. {p['name']}  脆弱性={p['product_vuln']:.3f} "
                  f"({p['tier']})  单点={p['sp_count']}")
        comps = sorted(result["components"].values(),
                       key=lambda c: (c["vuln"], c["n_suppliers"]),
                       reverse=True)[:args.top]
        print(f"\nTop {args.top} 最脆弱零部件：")
        for i, c in enumerate(comps, 1):
            print(f"  {i}. {c['name']}  脆弱性={c['vuln']:.3f} "
                  f"供应商数={c['n_suppliers']}  单点={'是' if c['single_point'] else '否'}")
        return 0

    out_md = args.md or os.path.join(OUT_DIR, "supply_chain_risk.md")
    out_json = args.json or os.path.join(OUT_DIR, "supply_chain_risk.json")
    os.makedirs(os.path.dirname(out_md), exist_ok=True)
    with open(out_md, "w", encoding="utf-8") as f:
        f.write(md)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(js, f, ensure_ascii=False, indent=2)

    n_sp = sum(1 for c in result["components"].values() if c["single_point"])
    print(f"已写出：\n  {out_md}\n  {out_json}")
    print(f"单点依赖部件：{n_sp}/{len(result['components'])}")
    worst = sorted(result["product_lines"].values(),
                   key=lambda r: r["mean_product_vuln"], reverse=True)[0]
    print(f"最脆弱产品线：{worst['product_line']} "
          f"(脆弱性={worst['mean_product_vuln']:.3f}, {worst['tier']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
