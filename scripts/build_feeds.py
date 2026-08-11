#!/usr/bin/env python3
"""build_feeds.py —— 把 tools/output 下的分析产物规范化为「带信封的时效数据 feed」。

输出到 data/feeds/{risk,valuation,sentiment}.json，每个文件遵循统一信封契约：
    {
      "meta": { "dataset", "version", "schema_ref", "generated", "valid_until", "sources", "build" },
      "data": { ... 具体指标 ... }
    }

设计要点：
- 只做「格式归一 + 信封包装」，绝不篡改分析结论。
- generated 优先取源文件自身时间，缺失时回退到构建当天。
- valid_until = generated + ttl 天（默认 30，可用 --ttl-days 调整）。
- meta.build：构建版本戳（流派 B，由 git describe 派生），由 --build 显式传入、
  或继承 BUILD_VERSION 环境变量、或自动调用 scripts/version.py 派生。前端 DataLayer
  可用它显示「该 feed 基于数据集构建 vX.Y.Z-…」。
- 与前端 src/lib/data_layer.js 约定同一套字段，是「前后端清晰接口」的服务端事实来源。

用法：
    python3 scripts/build_feeds.py                # 默认 ttl=30，输出 data/feeds/
    python3 scripts/build_feeds.py --ttl-days 7   # 周级刷新
    python3 scripts/build_feeds.py --build v1.3.0-5-gabcdef0   # 显式构建版本
"""
import argparse
import importlib.util
import json
import os
import re
from datetime import date, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_version():
    """派生构建版本号（流派 B：git describe），失败回退 BUILD_VERSION 环境变量。"""
    try:
        spec = importlib.util.spec_from_file_location(
            "vmod", os.path.join(ROOT, "scripts", "version.py"))
        vmod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(vmod)
        return vmod.compute()
    except Exception:
        return os.environ.get("BUILD_VERSION") or ""


def load(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return json.load(f)


def write(out_dir, name, obj):
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, name + ".json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    print("wrote:", os.path.relpath(path, ROOT))


def envelope(dataset, data, generated, ttl, sources, build=""):
    valid = ""
    if generated:
        try:
            valid = (date.fromisoformat(generated[:10]) + timedelta(days=ttl)).isoformat()
        except ValueError:
            valid = ""
    return {
        "meta": {
            "dataset": dataset,
            "version": 2,
            "schema_ref": "data/schemas/%s.json" % dataset,
            "generated": generated[:10] if generated else "",
            "valid_until": valid,
            "sources": sources or [],
            "build": build,
        },
        "data": data,
    }


def build_risk(ttl, build):
    src = load("tools/output/supply_chain_risk.json")
    generated = src.get("generated") or ""
    # 风险来源：复用图谱 source_registry 的官方/分析类 id（见 data/apple_supply_chain.json）
    sources = []
    try:
        reg = load("data/apple_supply_chain.json").get("meta", {}).get("source_registry", {})
        sources = sorted(reg.keys())
    except Exception:
        sources = []
    data = {k: src[k] for k in ("product_lines", "products", "components") if k in src}
    return envelope("risk", data, generated, ttl, sources, build)


def build_valuation(ttl, build):
    src = load("tools/output/supplier_analysis.json")
    generated = (src.get("meta", {}) or {}).get("generated") or ""
    data = {"suppliers": src.get("suppliers", [])}
    # 财务/市场数据的通用来源 id（具体每家 as_of 见供应商字段）
    sources = ["stockanalysis", "apple_10k"]
    return envelope("valuation", data, generated, ttl, sources, build)


def build_sentiment(ttl, build):
    md_path = os.path.join(ROOT, "tools/output/supplier_sentiment.md")
    if not os.path.exists(md_path):
        # 舆情源缺失（run_sentiment 未跑/失败、或被 .dockerignore 排除）：退化为空 feed，
        # 不阻断整体构建。UI 当前仅拉取 risk feed，故不影响页面；Phase 2 接入舆情展示时需补源。
        print("WARN: 缺少 %s，sentiment feed 退化为空（markdown=''）。" % md_path)
        today = date.today().isoformat()
        return envelope("sentiment", {"snapshot_date": today, "coverage": None, "markdown": ""}, today, ttl, [], build)
    text = open(md_path, encoding="utf-8").read()
    m_date = re.search(r"快照日期[:：]\s*(\d{4}-\d{2}-\d{2})", text)
    m_cov = re.search(r"覆盖\s*(\d+)\s*家", text)
    snapshot = m_date.group(1) if m_date else date.today().isoformat()
    coverage = int(m_cov.group(1)) if m_cov else None
    data = {"snapshot_date": snapshot, "coverage": coverage, "markdown": text}
    sources = ["nikkei", "counterpoint"]
    return envelope("sentiment", data, snapshot, ttl, sources, build)


def main():
    ap = argparse.ArgumentParser(description="规范化生成时效数据 feed")
    ap.add_argument("--ttl-days", type=int, default=30, help="valid_until = generated + ttl 天（默认 30）")
    ap.add_argument("--out", default=os.path.join(ROOT, "data/feeds"), help="输出目录")
    ap.add_argument("--build", default=None,
                    help="构建版本戳（如 v1.3.0-5-gabcdef0）；缺省时读 BUILD_VERSION 环境变量，"
                         "再缺省时自动由 scripts/version.py 派生")
    args = ap.parse_args()

    build = args.build if args.build is not None else (os.environ.get("BUILD_VERSION") or load_version())
    if not build:
        print("WARN: 未能派生构建版本（无 git / 无 BUILD_VERSION），meta.build 置空。")

    write(args.out, "risk", build_risk(args.ttl_days, build))
    write(args.out, "valuation", build_valuation(args.ttl_days, build))
    write(args.out, "sentiment", build_sentiment(args.ttl_days, build))
    print("done. (ttl=%d days, build=%s)" % (args.ttl_days, build))


if __name__ == "__main__":
    main()
