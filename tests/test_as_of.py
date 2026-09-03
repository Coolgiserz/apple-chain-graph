"""as_of 透传链路守卫（tests/test_as_of.py）

测试设计文档
============

缺陷
----
CSV 里本来就有 as_of 列（supplier_id -> as_of），analysis.py 的每条 record 也
带 as_of，但链路在三个地方断掉，页面显示的是**硬编码的 2026-08-10**：

1. ``report.py`` 的 ``render_json()`` 不输出 as_of -> 上游 JSON 里根本没有，
   下游无处可读；
2. ``run_analysis.py`` 的 ``meta.as_of`` 默认是占位串「见各供应商 as_of 字段」，
   不是 CSV 里的真实日期；
3. 模板第 69 行 + 4 个 locale 文件都硬编码 ``2026-08-10``。

后果：CSV 一刷新（as_of 已到 2026-09-02），页面日期纹丝不动——「数据已更新」
的信号丢失，读者会以为页面还是 8 月的数据。这正是上轮「刷新 15 家估值」做完后
用户指出的缺口：数据新了，但页面没说它新。

修复思路
--------
- 上游：``analysis.latest_as_of()`` 从 CSV 收集 as_of 去重；**≥2 个不同值就
  raise ValueError**（各供应商数据日期不一致时不允许静默选一个）；run_analysis
  用它填 ``meta.as_of`` 默认值；``render_json`` 给每个 supplier 补 as_of 字段。
- 看板：``build_dashboard_data.load_meta()`` 读 JSON 的 meta.as_of + 家数；
  ``build_dashboard.py`` 注入 ``__AS_OF__`` / ``__SUPPLIER_COUNT__`` 占位符
  （各恰好 1 次，0 或 2 次都 exit 1）；模板 subtitle 拆成两行：
  i18n 行（家数 + 定性描述，不含日期）+ 元信息行（「数据截至 …」，
  **不带 data-i18n** —— 因为 applyDOM() 用 textContent 整体覆盖 data-i18n
  元素，构建期注入的日期会被 i18n ready/changed 冲掉）。

本文件要防的回归
----------------
E1  上游单一数据日期：CSV 所有 as_of 去重后必须恰好 1 个（当前 2026-09-02）。
    将来若某家供应商的数据日期与其余不同，这里先红，逼你决定怎么标注，
    而不是页面悄悄显示一个谁都不代表的日期。
E2  新函数 ``analysis.latest_as_of()`` 返回该单一日期。
E3  meta.as_of 默认取 CSV：不传 --as_of 跑 run_analysis，输出 JSON 的
    ``meta.as_of`` 必须等于 CSV 单一日期，而不是占位串。
E4  看板生成器读 meta：``build_dashboard_data.load_meta()`` 返回
    ``{"as_of": ..., "count": ...}``，as_of 与 CSV 一致、count 为正整数。
E5  产物日期真实：看板产物里必须含 ``2026-09-02``，不得含硬编码
    ``2026-08-10``，也不得残留 ``__AS_OF__`` / ``__SUPPLIER_COUNT__`` 占位符。
E6  模板占位符防御：模板里 ``__AS_OF__`` 与 ``__SUPPLIER_COUNT__`` 必须各恰好
    1 次（build_dashboard.py 的「0 或 2 次即 exit 1」守卫依赖这个前提）。

产物相关用例（E5）在产物缺失时 skip：tools/visualizations/ 是 gitignore 的
构建产物，全新克隆且未构建时不存在；CI 中 build_all 先于 Python 测试执行。
"""

import csv
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tools"))

CSV_PATH = ROOT / "tools" / "data" / "supplier_fundamentals.csv"
OUT_JSON = ROOT / "tools" / "output" / "supplier_analysis.json"
TPL = ROOT / "templates" / "supplier_dashboard_template.html"
PRODUCT = ROOT / "tools" / "visualizations" / "supplier_dashboard.html"

# 当前 CSV 的统一数据日期；数据刷新后统一改这里即可，测试不写死「15 家」
CURRENT_AS_OF = "2026-09-02"


def _csv_as_ofs():
    """CSV 里所有 as_of 值（跳过空行与缺列）。"""
    if not CSV_PATH.is_file():
        return []
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        return [
            row.get("as_of", "").strip()
            for row in csv.DictReader(f)
            if row.get("supplier_id", "").strip()
        ]


class AsOfUpstream(unittest.TestCase):
    """E1–E3：上游（CSV / analysis / run_analysis / report）。"""

    def test_e1_csv_single_as_of(self):
        """E1：CSV 的 as_of 去重后必须恰好 1 个值（各供应商数据日期必须一致）。"""
        dates = {a for a in _csv_as_ofs() if a}
        self.assertEqual(
            len(dates), 1,
            "CSV 的 as_of 应只有 1 个不同值（各供应商数据日期必须一致），实际 %r；"
            "若某家数据日期确实不同，请先决定页面如何标注，再更新本测试的 CURRENT_AS_OF。" % sorted(dates))
        self.assertEqual(dates.pop(), CURRENT_AS_OF)

    def test_e2_analysis_latest_as_of(self):
        """E2：analysis.latest_as_of() 返回 CSV 的单一数据日期。"""
        from supplier_research import analysis

        self.assertEqual(analysis.latest_as_of(), CURRENT_AS_OF)

    def test_e3_run_analysis_meta_default(self):
        """E3：不传 --as_of 时，run_analysis 输出 JSON 的 meta.as_of = CSV 单一日期。"""
        with tempfile.TemporaryDirectory() as td:
            out_md = os.path.join(td, "a.md")
            out_json = os.path.join(td, "a.json")
            r = subprocess.run(
                [sys.executable, str(ROOT / "tools" / "run_analysis.py"),
                 "--md", out_md, "--json", out_json],
                capture_output=True, text=True, cwd=str(ROOT))
            self.assertEqual(r.returncode, 0,
                             "run_analysis 失败：\n%s" % r.stderr)
            with open(out_json, encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(data["meta"]["as_of"], CURRENT_AS_OF,
                             "meta.as_of 应默认取 CSV 的 as_of，而不是占位串")

    def test_e4_render_json_per_supplier_as_of(self):
        """E4（上游侧补充）：render_json 输出的每个**有基本面**的 supplier 都带 as_of。

        判据与看板一致：market_cap_usd_b 非空 = 有真实估值数据（当前 15 家）。
        未上市/无倍数的供应商没有 CSV 行，as_of 为空是合理的——它们没有数据日期。
        """
        from supplier_research import analysis, report

        records = analysis.build_dataset()
        js = report.render_json(records, {"as_of": CURRENT_AS_OF, "generated": "2026-09-02"})
        funded = [s for s in js["suppliers"] if s.get("market_cap_usd_b") is not None]
        missing = [s.get("id") for s in funded if s.get("as_of") != CURRENT_AS_OF]
        self.assertEqual(missing, [],
                         "render_json 应给每个有数据的 supplier 透传 as_of；缺失/不符：%r" % missing)


class AsOfDashboard(unittest.TestCase):
    """E4(看板)–E6：生成器 / 构建 / 模板 / 产物。"""

    def test_e4_load_meta(self):
        """E4：build_dashboard_data.load_meta() 返回 as_of 与家数。"""
        import build_dashboard_data as gen

        meta = gen.load_meta()
        self.assertEqual(meta["as_of"], CURRENT_AS_OF)
        self.assertIsInstance(meta["count"], int)
        self.assertGreater(meta["count"], 0, "家数应 > 0（上游没有带市值的供应商？）")

    def test_e5_product_shows_real_as_of(self):
        """E5：产物含真实日期，无硬编码旧日期、无残留占位符。"""
        if not PRODUCT.is_file():
            self.skipTest("构建产物不存在（先跑 build_all）")
        src = PRODUCT.read_text(encoding="utf-8")
        self.assertIn(CURRENT_AS_OF, src,
                      "产物应显示数据日期 %s（as_of 未透传？）" % CURRENT_AS_OF)

        # 从「数据截至」元素取值比对，而不是断言全文不出现旧日期串。
        # 全文子串匹配原本够用（旧日期只可能来自写死的 as_of），但接进舆情明细后
        # 来源链接自带真实的发布日期，恰好也有一天是 2026-08-10——再按全文匹配
        # 会把一条合法的新闻日期当成回归。真正要保证的是**展示出来的那个日期**，
        # 取值比对同时也比「旧串不存在」更严：写死成任何别的日期都会红。
        m = re.search(r'<span class="as-of">([^<]*)</span>', src)
        self.assertTrue(m, '产物里找不到数据日期元素 <span class="as-of">')
        self.assertEqual(m.group(1).strip(), CURRENT_AS_OF,
                         "产物显示的数据日期应为 %s，实际 %r（又写死了旧日期？）"
                         % (CURRENT_AS_OF, m.group(1).strip()))
        for ph in ("__AS_OF__", "__SUPPLIER_COUNT__"):
            self.assertNotIn(ph, src,
                             "产物不应残留占位符 %s（构建没替换它？）" % ph)

    def test_e6_template_placeholders_exactly_once(self):
        """E6：模板里两个占位符各恰好 1 次（0 次 = 没接线；>1 次 = 注释里写串了）。"""
        src = TPL.read_text(encoding="utf-8")
        for ph in ("__AS_OF__", "__SUPPLIER_COUNT__"):
            n = src.count(ph)
            self.assertEqual(
                n, 1,
                "模板中 %s 应恰好出现 1 次，实际 %d 次"
                "（注释里写它的字面量也会被 replace 命中，请改用文字描述）。" % (ph, n))


if __name__ == "__main__":
    unittest.main(verbosity=2)
