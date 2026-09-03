# -*- coding: utf-8 -*-
"""生成估值看板页面（tools/visualizations/supplier_dashboard.html）。

与 tools/geo_build.py 一致：从 templates/supplier_dashboard_template.html 读取模板，
用统一的 topnav() 注入顶部导航（含「企业列表」与 GitHub 按钮），避免再手写一份
陈旧、缺项的导航条。

数据注入
--------
看板数值不再是模板里手写的快照：scripts/build_dashboard_data.py 在构建期从
tools/output/supplier_analysis.json 重新生成（S_PIPELINE），本脚本把它的输出填进
模板的 __DASHBOARD_DATA__ 占位符。因此这个脚本必须在 run_analysis 之后运行——
build_all.py 的 STEPS 顺序已保证（run_analysis 排第一，本脚本排其后）。

舆情明细同理：scripts/build_sentiment_data.py 从 tools/data/supplier_sentiment.csv
生成（SENTIMENT_DETAIL → __SENTIMENT_DATA__），供「③ 市场舆情分布」点击分类后展开
企业与来源链接。它不依赖 run_analysis（CSV 是人工核改的数据文件），但仍走同一套
validate() + 占位符计数防御。

注入前先过 validate()：verdict / sector 映射不上就构建失败（exit 1），而不是把
一个没颜色、没译文的裸值发布上线。数值与上游的一致性由
tests/test_dashboard_data.py 的 D7 用例在测试层再守一道。

页面仍是纯静态内嵌数据，零运行时 fetch，file:// 直接打开也能看。
"""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from topnav import topnav, TOPNAV_CSS, analytics_js  # noqa: E402
import build_dashboard_data as gen  # noqa: E402
import build_sentiment_data as sgen  # noqa: E402

TPL = os.path.join(ROOT, "templates", "supplier_dashboard_template.html")
OUT = os.path.join(ROOT, "tools", "visualizations", "supplier_dashboard.html")


def main():
    rows = gen.build_rows()
    problems = gen.validate(rows)
    if problems:
        sys.stderr.write("✗ 看板数据校验失败，中止构建：\n")
        for p in problems:
            sys.stderr.write("  - %s\n" % p)
        return 1

    # 舆情明细（③ 市场舆情分布点分类展开用）。与估值数据同源同理：构建期从
    # tools/data/supplier_sentiment.csv 生成，不落中间文件。
    sent_rows = sgen.build_rows()
    sent_problems = sgen.validate(sent_rows)
    if sent_problems:
        sys.stderr.write("✗ 舆情数据校验失败，中止构建：\n")
        for p in sent_problems:
            sys.stderr.write("  - %s\n" % p)
        return 1

    html = open(TPL, encoding="utf-8").read()

    # 占位符必须恰好 1 处。str.replace 不区分代码与注释——若有人在注释里也提到
    # 占位符字面量，整段 JSON 会被换进注释位置，造成数据双份注入 + JS 语法错误
    # （const S_PIPELINE = const S_PIPELINE = ...，整页脚本解析失败）。宁可构建失败。
    for ph in ("__DASHBOARD_DATA__", "__AS_OF__", "__SUPPLIER_COUNT__",
               "__SENTIMENT_DATA__"):
        n = html.count(ph)
        if n != 1:
            sys.stderr.write("✗ 模板中 %s 占位符应恰好出现 1 次，"
                             "实际 %d 次（注释里写它的字面量也会被替换，请改用文字描述）。\n"
                             % (ph, n))
            return 1

    meta = gen.load_meta()
    as_of = meta["as_of"] or "—"

    # topnav() 本身已附带 analytics_js()，故 __ANALYTICS__ 占位用空串移除重复统计脚本
    html = (html
            .replace("__DASHBOARD_DATA__", gen.render_snippet(rows))
            .replace("__SENTIMENT_DATA__", sgen.render_snippet(sent_rows))
            .replace("__AS_OF__", as_of)
            .replace("__SUPPLIER_COUNT__", str(meta["count"]))
            .replace("__TOPNAV_CSS__", TOPNAV_CSS)
            .replace("__TOPNAV__", topnav("../../", "dash"))
            .replace("__ANALYTICS__", ""))
    for ph in ("__DASHBOARD_DATA__", "__AS_OF__", "__SUPPLIER_COUNT__",
               "__SENTIMENT_DATA__"):
        if ph in html:
            sys.stderr.write("✗ 模板中的 %s 占位符未被替换（模板被改坏？）\n" % ph)
            return 1
    for decl in ("const S_PIPELINE", "const SENTIMENT_DETAIL"):
        if html.count(decl) != 1:
            sys.stderr.write("✗ 产物中 %s 应只声明 1 次，实际 %d 次。\n"
                             % (decl, html.count(decl)))
            return 1
    open(OUT, "w", encoding="utf-8").write(html)
    print("Dashboard written:", OUT, "bytes:", len(html),
          "(suppliers: %d, sentiment: %d, as_of: %s)"
          % (len(rows), len(sent_rows), as_of))
    return 0


if __name__ == "__main__":
    sys.exit(main())
