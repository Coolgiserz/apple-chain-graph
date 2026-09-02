#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""估值看板数据源：把 tools/output/supplier_analysis.json 翻译成模板用的 S_PIPELINE。

背景（为什么要这个文件）
------------------------
看板原先的 15 家公司估值是**手写死在模板里的**（``const S = [...]``），没有任何脚本
会重生成它。``git log -- templates/supplier_dashboard_template.html`` 显示该文件只被
UI 轮次碰过（a11y / 断点 / 暗色 / 字号 / 色值），从未有过数据更新提交。

可 ``build_all.py`` 的第一步就是 ``tools/run_analysis.py``，它产出的
``tools/output/supplier_analysis.json`` 是新鲜的，估值看板脚本又排在它之后——
**数据在构建时本来就是现成的，只是看板没接**。

实测后果（快照 vs 管道，2026-09-01）：

- 3 家估值结论已翻转：SK海力士、京东方 高估→合理；LG显示 困境→困境（亏损）
- 7 家市值偏差 ≥5%：富士康 +19.6%、LG显示 −22.8%、日月光 −17.6%
- 三星电子 PE：快照 10.83，实际 22.4

也就是**公开页面上的投资结论是错的**，不只是"旧了"。

分工原则
--------
管道里有的字段一律取自管道；管道没有结构化来源的字段留在模板里人工维护：

- **管道字段**：id / name / sector / mcap / rev / score / verdict / gm / nm / roe /
  pe / pb / ev / con —— 本文件生成，每次构建刷新。
- **人工字段**：news / analyst（新闻情绪、卖方共识）—— 留在模板的
  ``MANUAL_SENTIMENT`` 里，因为 ``sentiment.json`` 只有 markdown 综述、没有逐家
  结构化打分。见模板里「人工维护·非管道数据」注释。

用法
----
被 import（正常路径）::

    # tools/build_dashboard.py
    import build_dashboard_data as gen
    rows = gen.build_rows()
    problems = gen.validate(rows)          # 契约校验，非空即构建失败
    html = html.replace("__DASHBOARD_DATA__", gen.render_snippet(rows))

命令行（自检 / 预览）::

    python3 scripts/build_dashboard_data.py    # 校验通过后把 JS 字面量打到 stdout

为什么不在 build_all.py 里单开一步
----------------------------------
``tools/build_dashboard.py`` **已经在** build_all 的 STEPS 里，且排在
``tools/run_analysis.py`` 之后。它 import 本模块即可拿到新鲜数据，因此无需
再引入一个"先落盘中间 JSON、再由页面脚本读回"的步骤——那会多出一份可能过期的
中间产物，反而制造新的双源问题。本模块只做纯函数转换，不写任何文件。

把关
----
``tests/test_dashboard_data.py`` 的 D1–D8 用例锁死本文件与模板、产物的契约：
数值必须与上游一致（D7）、verdict/sector 必须落在模板认得的枚举内（D3/D4）、
人工条目不得有僵尸（D5）。改映射表前先看那个文件头部的测试设计文档。
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_JSON = ROOT / "tools" / "output" / "supplier_analysis.json"

# 模板里 C 与 VERDICT_KEY 只认这四种；多一个就显示成没颜色、没译文的裸值。
# 与 tests/test_dashboard_data.py 的 ALLOWED_VERDICTS 保持一致。
ALLOWED_VERDICTS = frozenset({"低估", "高估", "合理", "困境"})

# 模板 SECTOR_KEY 的 9 个赛道（i18n 有译文的那些）。
ALLOWED_SECTORS = frozenset({
    "晶圆代工", "代工", "存储", "摄像头", "逻辑芯片",
    "显示面板", "元器件", "光学", "封测",
})

# 上游 category → 看板赛道。31 个 category 全量映射，不只是当前带市值的那几家：
# 看板展示范围会随研究覆盖度变化（今天 60 家里 15 家有倍数），漏映射将来会以
# "页面显示未翻译裸值"的形式冒出来，届时改起来比现在补一行麻烦得多。
SECTOR_BY_CATEGORY = {
    # 晶圆 / 逻辑
    "Foundry": "晶圆代工",
    "Semiconductor": "逻辑芯片",
    "IP/EDA": "逻辑芯片",
    # 存储
    "Memory": "存储",
    # 显示
    "Display": "显示面板",
    "Touch/Display": "显示面板",
    # 光学 / 摄像
    "Optics": "光学",
    "Optical": "光学",
    "CIS/Optical": "摄像头",
    "Camera Module": "摄像头",
    # 封测 / 板级
    "OSAT": "封测",
    "Substrate/PCB": "元器件",
    "Substrate": "元器件",
    "PCB": "元器件",
    "FPC": "元器件",
    "FPC/Component": "元器件",
    # 组装 / 结构件
    "Assembly": "代工",
    "Assembly/Acoustics": "代工",
    "Assembly/Enclosure": "代工",
    "Enclosure": "代工",
    "Enclosure/Module": "代工",
    "Glass/Enclosure": "代工",
    # 元器件
    "Passive": "元器件",
    "Passive/Battery": "元器件",
    "Battery": "元器件",
    "Acoustics": "元器件",
    "Sensor": "元器件",
    "Mech/Actuator": "元器件",
    "Mech": "元器件",
    "Material": "元器件",
    "Glass": "元器件",
}

# 上游 valuation.verdict → 看板结论。
#
# 上游会给出比看板更细的文案，这里做归一化。刻意**不**收录下面两种：
#   - 「定性（未上市/无倍数）」
#   - 「基准（终端厂，非供应商）」
# 它们不是估值结论，且这两类公司上游都没有 market_cap_usd_b，会被 _market_cap()
# 先过滤掉。不收录是故意的：若将来某家带市值的公司落到这两类，validate() 会直接
# 报错并点名，而不是让页面默默显示一个没颜色的裸值。
VERDICT_ALIASES = {
    "低估": "低估",
    "高估": "高估",
    "合理": "合理",
    "困境（亏损）·倍数失真": "困境",
}


def load_suppliers():
    """读取上游 suppliers 列表。文件缺失时给出可执行的提示而非裸 KeyError。"""
    if not SRC_JSON.is_file():
        raise SystemExit(
            "缺少 %s\n请在仓库根执行 python3 build_all.py"
            "（或先 python3 tools/run_analysis.py）生成它。" % SRC_JSON)
    return json.loads(SRC_JSON.read_text(encoding="utf-8")).get("suppliers", [])


def _num(v):
    """上游数值字段统一成 float 或 None（未上市/缺失时上游是 null）。"""
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _market_cap(s):
    """「有真实估值倍数」的判据：市值非空。

    上游 60 家里只有一小撮带 market_cap_usd_b，其余是「未上市/无倍数」的定性条目。
    看板只画有倍数的——这是数据可得性的自然结果，不是人为挑出来的 15 家。所以家数
    会随管道推进变化，任何写死"15"的断言都是错的（见 D1 用例的说明）。
    """
    v = s.get("market_cap_usd_b")
    return None if v is None else float(v)


def _name(s):
    """显示名取 short_name 的中文部分（'TSMC / 台积电' → '台积电'）。"""
    short = (s.get("short_name") or "").strip()
    if " / " in short:
        return short.split(" / ")[-1].strip()
    return short or (s.get("name") or s.get("id") or "").strip()


def _verdict(s):
    """归一化估值结论；未在 VERDICT_ALIASES 里的一律原样返回，交给 validate() 报错。"""
    raw = (s.get("valuation") or {}).get("verdict")
    return VERDICT_ALIASES.get(raw, raw)


def _sector(s):
    """category → 看板赛道；未收录的 category 原样返回，交给 validate() 报错。"""
    cat = s.get("category")
    return SECTOR_BY_CATEGORY.get(cat, cat)


def build_rows():
    """把上游供应商列表转成看板行（只含有真实估值倍数的那些）。"""
    rows = []
    for s in load_suppliers():
        if _market_cap(s) is None:
            continue
        val = s.get("valuation") or {}
        rows.append({
            "id": s.get("id"),
            "name": _name(s),
            "sector": _sector(s),
            "mcap": _market_cap(s),
            "rev": _num(s.get("revenue_ttm_usd_b")),
            "score": _num(val.get("score")),
            "verdict": _verdict(s),
            "gm": _num(s.get("gross_margin_pct")),
            "nm": _num(s.get("net_margin_pct")),
            "roe": _num(s.get("roe_pct")),
            "pe": _num(s.get("pe")),
            "pb": _num(s.get("pb")),
            "ev": _num(s.get("ev_ebitda")),
            # 沿用旧键名 con，但内容来自上游 recent（近期动态），**不是**原快照里那句
            # 机构共识——管道里没有逐家的结构化共识打分。模板当前不渲染这个字段；
            # 将来若要加「最新动态」列，请按 recent 的语义写表头，别沿用「机构共识」。
            "con": (s.get("recent") or "").strip(),
        })
    return rows


def validate(rows):
    """契约校验，返回问题清单（空列表表示通过）。

    这里只做「会让页面出错」的检查——verdict 没颜色、sector 没译文、id 撞车。
    数值本身的合理性（比如 PE 是不是离谱）由上游 run_analysis.py 负责，不在这里
    重复一遍口径。
    """
    problems = []
    if not rows:
        return ["上游没有带市值的供应商，看板会是空的（run_analysis 的数据有问题？）"]

    cat_by_id = {s.get("id"): s.get("category") for s in load_suppliers()}
    seen = set()
    for r in rows:
        rid = r.get("id")
        if rid in seen:
            problems.append("id 重复：%r" % rid)
        seen.add(rid)

        if r["verdict"] not in ALLOWED_VERDICTS:
            problems.append(
                "%s 的 verdict %r 不在 %s 内（页面会显示成没颜色、没译文的裸值）。"
                "请在 scripts/build_dashboard_data.py 的 VERDICT_ALIASES 补映射。"
                % (rid, r["verdict"], sorted(ALLOWED_VERDICTS)))

        if r["sector"] not in ALLOWED_SECTORS:
            problems.append(
                "%s 的 sector %r（来自上游 category %r）不在模板 SECTOR_KEY 内。"
                "请在 scripts/build_dashboard_data.py 的 SECTOR_BY_CATEGORY 补映射。"
                % (rid, r["sector"], cat_by_id.get(rid)))
    return problems


def render_snippet(rows):
    """渲染成 JS 数组字面量（**只有值，不含声明**）。

    模板里写的是 ``const S_PIPELINE = __DASHBOARD_DATA__;``——占位符标记的是
    「值的位置」，所以这里只返回 ``[...]``。第一版返回过完整声明
    ``const S_PIPELINE = [...];``，替换后变成 ``const S_PIPELINE = const
    S_PIPELINE = [...]`` 双重声明的语法错误，整页脚本解析失败；教训记在
    tests/test_dashboard_data.py 的 D8 用例里。

    用 json.dumps 而不是手写拼接：将来任何一家公司名字里出现引号或换行都不会把页面
    搞崩。ensure_ascii=False 让中文直接落地（页面本身是 UTF-8），产物也更易读。
    输出保持合法 JSON，tests/test_dashboard_data.py 的 D7 用例靠这一点把产物里的
    数值与上游逐项比对。
    """
    return json.dumps(rows, ensure_ascii=False, indent=2)


def main():
    rows = build_rows()
    problems = validate(rows)
    if problems:
        sys.stderr.write("✗ 看板数据校验失败：\n")
        for p in problems:
            sys.stderr.write("  - %s\n" % p)
        return 1
    sys.stdout.write(render_snippet(rows) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
