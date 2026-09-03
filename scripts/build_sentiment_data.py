#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""舆情看板数据源：把 tools/data/supplier_sentiment.csv 翻译成模板用的舆情明细。

背景（为什么要这个文件）
------------------------
估值看板「③ 市场舆情分布」原先只有两个环形图 + 计数，**点不动**。要让读者点
「正面/中性/负面」就能展开该分类下的企业与来源链接，得先把两件更基础的事解决：

1. **数据是旧快照**。CSV 的 ``as_of`` 停在 2026-08-05，比估值数据（2026-09-02）
   旧 28 天。这 28 天里 SK 海力士财报后目标价被集体下修 27%–36%、京东方落选
   iPhone 18 Pro OLED、立讯扣非增速掉到 6.47%——旧数据会把这些完全盖掉。
2. **双源漂移**。模板里硬编码了一份 ``MANUAL_SENTIMENT``（15 家 news/analyst 打分），
   CSV 里另有一份结构化舆情。两份各改各的，没有任何机制保证一致。手写那份的注释
   理由是「管道里没有结构化来源」，但 CSV 里其实一直都有——只是没人接。

分工原则（改动后）
------------------
**CSV 是唯一事实来源**。所有舆情字段——打分、综述、催化剂、风险、来源链接——
都在 ``tools/data/supplier_sentiment.csv`` 一行里，本文件只做纯函数转换、不写文件，
每次构建刷新。模板里的手写打分表删除。

CSV 字段（10 列）
-----------------
=====================  ==========================================================
``supplier_id``        公司 id，必须与估值管道（supplier_analysis.json）一致
``as_of``              该行舆情的数据截止日（YYYY-MM-DD）
``news_sentiment``     positive / neutral / negative
``news_summary``       新闻与事件综述（一段话）
``analyst_sentiment``  bullish / neutral / bearish
``analyst_consensus``  卖方共识（评级分布、目标价区间）
``key_catalysts``      关键催化剂
``key_risks``          关键风险
``sources``            逗号分隔的 URL 列表，给 markdown 舆情报告用
``sources_detail``     JSON 数组 ``[{title,url,publisher,date}]``，给看板渲染链接卡片
=====================  ==========================================================

为什么 sources 有两列、却不算是双源
------------------------------------
两列**服务的消费方不同**，但内容必须同源：

- ``sources`` 被 ``tools/supplier_research/sentiment.py`` 用 ``split(",")`` 切成
  URL 列表，渲染进 ``tools/output/supplier_sentiment.md``。这条路径已存在，不动。
- ``sources_detail`` 带标题/媒体/日期，看板的展开面板要靠它渲染成「标题（媒体 · 日期）」
  的可点击链接。没有标题的裸 URL 在卡片里基本没法用。

放在同一行同一文件，是为了让「改一处」就是「改全部」；再用
``tests/test_sentiment_data.py`` 的 S4 用例锁死两列的 URL 列表逐条同序相等——
把「记得两边同步改」变成「不同步就红」。

由此还带出一条硬约束：**URL 里不能出现逗号**，否则会被 sentiment.py 切成两截。
S3 用例守着这一点。

用法
----
被 import（正常路径）::

    # tools/build_dashboard.py
    import build_sentiment_data as sgen
    rows = sgen.build_rows()
    problems = sgen.validate(rows)           # 契约校验，非空即构建失败
    html = html.replace("__SENTIMENT_DATA__", sgen.render_snippet(rows))

命令行（自检 / 预览）::

    python3 scripts/build_sentiment_data.py  # 校验通过后把 JS 字面量打到 stdout

把关
----
``tests/test_sentiment_data.py`` 的 S1–S10 锁死 CSV、生成器、模板、产物四者的契约。
改字段映射或 CSV 表头前先看那个文件头部的测试设计文档。
"""

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SENT_CSV = ROOT / "tools" / "data" / "supplier_sentiment.csv"
# 估值管道的上游（可选存在）：只在文件在时才做 id 交叉校验，
# 全新克隆且未跑 run_analysis 时不该因此构建失败。
ANALYSIS_JSON = ROOT / "tools" / "output" / "supplier_analysis.json"

# CSV 字符串枚举 → 模板里用的 -1/0/1（与旧 MANUAL_SENTIMENT 的取值口径一致）
NEWS_SCORE = {"positive": 1, "neutral": 0, "negative": -1}
ANALYST_SCORE = {"bullish": 1, "neutral": 0, "bearish": -1}

# 文本字段：CSV 列名 → 产物里的驼峰键
TEXT_FIELDS = (
    ("newsSummary", "news_summary"),
    ("analystConsensus", "analyst_consensus"),
    ("catalysts", "key_catalysts"),
    ("risks", "key_risks"),
)

MIN_SOURCES = 3


def load_rows():
    """读取 CSV，返回原始行列表（DictReader）。

    用 ``utf-8-sig`` 是因为这个文件带 BOM——Excel / _numbers 之类的工具编辑后会
    保留它，而 BOM 会让第一列的 key 变成 ``\\ufeffsupplier_id``，取值为 None。
    """
    with SENT_CSV.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def build_rows():
    """把 CSV 行翻译成模板用的舆情明细数组。

    翻译只做三件事：字符串枚举转数字打分、文本字段改驼峰键、解析来源 JSON。
    不做任何业务判断——比如不校验目标价区间是否合理，那属于人工核改 CSV 的范畴。
    """
    out = []
    for r in load_rows():
        row = {
            "id": (r.get("supplier_id") or "").strip(),
            "asOf": (r.get("as_of") or "").strip(),
            "news": NEWS_SCORE.get((r.get("news_sentiment") or "").strip()),
            "analyst": ANALYST_SCORE.get((r.get("analyst_sentiment") or "").strip()),
            "sources": json.loads(r.get("sources_detail") or "[]"),
        }
        for out_key, csv_key in TEXT_FIELDS:
            row[out_key] = (r.get(csv_key) or "").strip()
        out.append(row)
    return out


def validate(rows):
    """契约校验，返回问题清单（空列表表示通过）。

    只查「会让页面出错或误导读者」的情况：打分落空会让某家公司在环形图里悄悄
    算成中性、来源解析失败会让展开面板空白、来源过少则读者无法交叉验证。
    数据本身的准确性由 refresh 时的口径核对负责，不在这里重复。
    """
    problems = []
    if not rows:
        return ["supplier_sentiment.csv 为空，看板舆情区会是空的"]

    seen = set()
    for r in rows:
        rid = r.get("id") or "<空 id>"
        if rid in seen:
            problems.append("supplier_id 重复：%r" % rid)
        seen.add(rid)

        if r.get("news") is None:
            problems.append("%s 的 news 打分落空（news_sentiment 不在 %s 内）"
                            % (rid, sorted(NEWS_SCORE)))
        if r.get("analyst") is None:
            problems.append("%s 的 analyst 打分落空（analyst_sentiment 不在 %s 内）"
                            % (rid, sorted(ANALYST_SCORE)))

        for out_key, csv_key in TEXT_FIELDS:
            if not r.get(out_key):
                problems.append("%s 的 %s 为空（面板会出现空白段落）" % (rid, csv_key))

        srcs = r.get("sources") or []
        if not isinstance(srcs, list) or len(srcs) < MIN_SOURCES:
            problems.append("%s 的来源仅 %s 条，少于下限 %d 条（读者无法交叉验证）"
                            % (rid, len(srcs) if isinstance(srcs, list) else "?", MIN_SOURCES))
            continue
        for i, s in enumerate(srcs):
            for k in ("title", "url", "publisher", "date"):
                if not str(s.get(k) or "").strip():
                    problems.append("%s.sources[%d].%s 为空（卡片会缺字）" % (rid, i, k))

    # 与估值管道的 id 交叉校验：缺失会让公司永远按中性兜底，多余则是僵尸条目。
    # 上游文件不在时跳过——那是「还没跑 run_analysis」，不是数据错。
    if ANALYSIS_JSON.is_file():
        try:
            upstream = json.loads(ANALYSIS_JSON.read_text(encoding="utf-8"))
            live = {s.get("id") for s in upstream.get("suppliers", []) if s.get("market_cap_usd_b")}
            csv_ids = {r.get("id") for r in rows}
            for missing in sorted(live - csv_ids):
                problems.append("%s 在估值管道里有市值，但舆情 CSV 缺这一行（会按中性兜底）" % missing)
            for zombie in sorted(csv_ids - live):
                problems.append("%s 在舆情 CSV 里，但已不在估值管道中（僵尸条目）" % zombie)
        except (json.JSONDecodeError, OSError) as e:
            problems.append("读取 %s 失败，跳过 id 交叉校验：%s" % (ANALYSIS_JSON.name, e))

    return problems


def render_snippet(rows):
    """渲染成 JS 数组字面量（**只有值，不含声明**）。

    模板里写的是 ``const SENTIMENT_DETAIL = __SENTIMENT_DATA__;``——占位符标记的
    是「值的位置」，所以这里只返回 ``[...]``。若连同声明一起吐出来，替换后会变成
    ``const X = const X = [...]`` 双重声明的语法错误，整页脚本解析失败、看板全白。
    这是 tests/test_dashboard_data.py D8 事故的同一模式，只是换了个数据块重演。

    用 json.dumps 而不是手写拼接：任何一家公司的综述里出现引号、反斜杠或换行都不会
    把页面搞崩。ensure_ascii=False 让中文直接落地（页面本身是 UTF-8），产物也更易读。
    输出保持合法 JSON，tests/test_sentiment_data.py 的 S7 用例靠这一点解析比对。
    """
    return json.dumps(rows, ensure_ascii=False, indent=2)


def main():
    rows = build_rows()
    problems = validate(rows)
    if problems:
        sys.stderr.write("✗ 舆情数据校验失败：\n")
        for p in problems:
            sys.stderr.write("  - %s\n" % p)
        return 1
    sys.stdout.write(render_snippet(rows) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
