"""估值看板数据管道守卫（tests/test_dashboard_data.py）

测试设计文档
============

缺陷
----
看板的 15 家公司估值数据原先**手写死在模板里**（``const S = [...]``），没有任何脚本
会重生成它。查 ``git log -- templates/supplier_dashboard_template.html`` 可见该文件
只被 UI 轮次碰过（a11y / 断点 / 暗色 / 字号 / 色值），从未有过数据更新提交。

而 ``build_all.py`` 的第一步就是 ``tools/run_analysis.py``，它产出的
``tools/output/supplier_analysis.json`` 是新鲜的，估值看板脚本又排在它之后——
**数据在构建时本来就是现成的，只是看板没接**。

实测后果（快照 vs 管道，2026-09-01）：

- 3 家估值结论已翻转：SK海力士、京东方 高估→合理；LG显示 困境→困境（亏损）
- 7 家市值偏差 ≥5%：富士康 +19.6%、LG显示 −22.8%、日月光 −17.6%
- 三星电子 PE：快照 10.83，实际 22.4（差一倍多）

即**公开页面上的投资结论是错的**，不只是"旧了"。

修复思路
--------
把这块数据接回管道：每次构建从 ``tools/output/supplier_analysis.json`` 重新生成。
分工原则——凡是管道里有结构化来源的字段一律取自管道，不留手写副本。

（原先把 news / analyst 舆情留在模板的 ``MANUAL_SENTIMENT`` 里手写，理由是
"sentiment.json 只有 markdown、没有逐家结构化分"。这个理由不成立：
``tools/data/supplier_sentiment.csv`` 里一直有逐家打分，只是看板没接。两份数据
各改各的就是双源漂移，已改为从 CSV 派生，见 tests/test_sentiment_data.py。）

本文件要防的回归
----------------
1. **D7（核心，也是本 bug 本身）**：产物里的数值必须与上游 JSON 一致。只要有人
   手改了快照、或构建没跑生成器，这条就红。这是把"数据过时"这一类问题从
   「靠人记得更新」变成「结构上不可能」。
2. **D3 / D4（契约）**：``verdict`` 必须落在模板 ``C`` / ``VERDICT_KEY`` 认得的
   四种之内，``sector`` 必须落在 ``SECTOR_KEY`` 之内。管道将来新增文案
   （如「基准（终端厂，非供应商）」）时，这里先红，提示补映射——而不是让页面
   显示一个没颜色、没译文的裸值。
3. **D5（舆情不回流手写表）**：news / analyst 打分必须来自 ``supplier_sentiment.csv``
   的管道派生，模板里不得再出现手写打分表。手写那份的真正问题不是"会有僵尸条目"，
   而是**它不会随 CSV 刷新**——页面上的情绪结论会悄悄停在旧快照。
4. **D6（结构）**：模板里不能再有手写的快照数组，只能是占位符。

为什么 D1 不写死「15 家」
------------------------
公司家数会随研究管道的覆盖度变化（当前 60 家里 15 家有真实估值倍数，其余 44 家是
「未上市/无倍数」的定性条目）。写死数字会在数据正常增长时误报。故断言
「行数 == 上游有市值的供应商数」——自洽即可，不锁死绝对值。

产物相关用例（D7 / D8）在产物缺失时 skip：``tools/visualizations/`` 是 gitignore
的构建产物，全新克隆且未构建时不存在；CI 中 build_all 先于 Python 测试执行。
"""

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

SRC_JSON = ROOT / "tools" / "output" / "supplier_analysis.json"
TPL = ROOT / "templates" / "supplier_dashboard_template.html"
PRODUCT = ROOT / "tools" / "visualizations" / "supplier_dashboard.html"

# 模板里 C 与 VERDICT_KEY 只认这四种；多一个就会显示成没颜色、没译文的裸值
ALLOWED_VERDICTS = {"低估", "高估", "合理", "困境"}

REQUIRED_KEYS = [
    "id", "name", "sector", "mcap", "rev", "score", "verdict",
    "gm", "nm", "roe", "pe", "pb", "ev", "con",
]


def _sectors_from_template(tpl_src):
    """从模板的 SECTOR_KEY 解析出合法赛道集合（i18n 能翻译的那些）。"""
    m = re.search(r"const SECTOR_KEY\s*=\s*\{(.*?)\};", tpl_src, re.S)
    assert m, "模板中未找到 SECTOR_KEY"
    return set(re.findall(r"'([^']+)'\s*:", m.group(1)))


def _pipeline_from_product(product_src):
    """从构建产物里取出 S_PIPELINE 数组（生成器输出的是合法 JSON）。"""
    m = re.search(r"const S_PIPELINE\s*=\s*(\[.*?\n\]);", product_src, re.S)
    assert m, "产物中未找到 S_PIPELINE（生成器没跑？）"
    return json.loads(m.group(1))


class DashboardDataPipeline(unittest.TestCase):
    """看板数据必须来自管道，且形状符合模板契约。"""

    def test_d1_row_count_matches_upstream(self):
        """D1：行数与上游「有市值」的供应商数自洽，且 id 唯一。"""
        import build_dashboard_data as gen

        rows = gen.build_rows()
        upstream = [s for s in gen.load_suppliers() if gen._market_cap(s) is not None]
        self.assertEqual(len(rows), len(upstream),
                         "生成的行数与上游有市值的供应商数不一致")
        ids = [r["id"] for r in rows]
        self.assertEqual(len(ids), len(set(ids)), "生成的 id 有重复：%r" % ids)

    def test_d2_required_fields_present(self):
        """D2：必备字段齐全、名称非空、数值字段是数字或 null。"""
        import build_dashboard_data as gen

        for r in gen.build_rows():
            for k in REQUIRED_KEYS:
                self.assertIn(k, r, "%s 缺少字段 %s" % (r.get("id"), k))
            self.assertTrue(r["name"], "%s 的 name 为空" % r["id"])
            for k in ("mcap", "rev", "score", "gm", "nm", "roe", "pe", "pb", "ev"):
                self.assertTrue(r[k] is None or isinstance(r[k], (int, float)),
                                "%s.%s 应为数字或 null，实际 %r" % (r["id"], k, r[k]))

    def test_d3_verdicts_are_renderable(self):
        """D3：verdict 必须落在模板认得的四种之内（管道新增文案时这里先红）。"""
        import build_dashboard_data as gen

        bad = [(r["id"], r["verdict"]) for r in gen.build_rows()
               if r["verdict"] not in ALLOWED_VERDICTS]
        self.assertEqual(bad, [],
                         "以下 verdict 不在模板 C / VERDICT_KEY 认得的 %r 内。"
                         "请在 build_dashboard_data.VERDICT_ALIASES 补映射：%r"
                         % (sorted(ALLOWED_VERDICTS), bad))

    def test_d4_sectors_are_translatable(self):
        """D4：sector 必须在 SECTOR_KEY 内，否则页面会显示未翻译的裸值。"""
        import build_dashboard_data as gen

        allowed = _sectors_from_template(TPL.read_text(encoding="utf-8"))
        bad = [(r["id"], r["sector"]) for r in gen.build_rows() if r["sector"] not in allowed]
        self.assertEqual(bad, [],
                         "以下 sector 不在模板 SECTOR_KEY 内（会显示为未翻译裸值）。"
                         "请在 build_dashboard_data.SECTOR_BY_CATEGORY 补映射：%r" % bad)

    def test_d5_sentiment_comes_from_pipeline(self):
        """D5：舆情打分必须由 CSV 派生，模板里不得再有手写打分表。

        原先模板里有一张 ``MANUAL_SENTIMENT``，与 ``supplier_sentiment.csv`` 并存，
        两份各改各的（双源漂移）。手写那份不会随 CSV 刷新，页面上的情绪结论因此停在
        旧快照。现在改由 ``scripts/build_sentiment_data.py`` 从 CSV 派生，这里守住
        「不再回流」——逐家是否都有舆情条目由 tests/test_sentiment_data.py 的 S1 负责。
        """
        tpl = TPL.read_text(encoding="utf-8")
        self.assertNotIn("MANUAL_SENTIMENT", tpl,
                         "模板里又出现了手写打分表——舆情应全部由 build_sentiment_data "
                         "从 supplier_sentiment.csv 派生")
        self.assertIn("__SENTIMENT_DATA__", tpl,
                      "模板应有 __SENTIMENT_DATA__ 占位符（舆情明细注入点）")

    def test_d6_template_has_no_handwritten_snapshot(self):
        """D6：模板里不得再有手写的快照数组，只能是占位符。"""
        tpl = TPL.read_text(encoding="utf-8")
        self.assertIn("__DASHBOARD_DATA__", tpl, "模板应有 __DASHBOARD_DATA__ 占位符")
        self.assertNotRegex(tpl, r"const S\s*=\s*\[",
                            "模板里不应再有手写的 const S = [...]，数据应由生成器注入")


class DashboardProduct(unittest.TestCase):
    """构建产物校验（产物缺失时跳过——它是 gitignore 的）。"""

    def _product(self):
        if not SRC_JSON.is_file():
            self.skipTest("缺少上游数据 tools/output/supplier_analysis.json")
        if not PRODUCT.is_file():
            self.skipTest("产物尚未构建（tools/visualizations/ 为 gitignore 产物）")
        return PRODUCT.read_text(encoding="utf-8")

    def test_d7_product_matches_upstream(self):
        """D7（核心）：产物数值必须与上游 JSON 一致——这正是「数据过时」本身。

        任何人手改快照、或构建时没跑生成器，这条都会红。
        """
        src = json.loads(SRC_JSON.read_text(encoding="utf-8"))
        byid = {s["id"]: s for s in src.get("suppliers", [])}
        product = self._product()

        mismatches = []
        for row in _pipeline_from_product(product):
            s = byid.get(row["id"])
            if s is None:
                mismatches.append("%s：产物里有、上游没有" % row["id"])
                continue
            for key, getter in (("mcap", lambda x: x.get("market_cap_usd_b")),
                                ("pe", lambda x: x.get("pe")),
                                ("pb", lambda x: x.get("pb")),
                                ("ev", lambda x: x.get("ev_ebitda")),
                                ("rev", lambda x: x.get("revenue_ttm_usd_b"))):
                want, got = getter(s), row[key]
                if want is None and got is None:
                    continue
                if want is None or got is None or abs(float(want) - float(got)) > 1e-6:
                    mismatches.append("%s.%s：上游 %r ≠ 产物 %r" % (row["id"], key, want, got))

        self.assertEqual(mismatches, [],
                         "产物数据与上游 supplier_analysis.json 不一致（数据已过时或被手改）：\n  "
                         + "\n  ".join(mismatches))

    def test_d8_placeholder_replaced(self):
        """D8：占位符已被替换、声明只出现一次——双份注入会让整页 JS 解析失败。

        真实事故：模板注释里写了占位符字面量，``str.replace`` 不分代码还是注释，
        把整段 JSON 也换进了注释位置。产物于是有两份数据 + 一行
        ``const S_PIPELINE = const S_PIPELINE = [...]`` 语法错误——**整页脚本
        解析失败，看板全白**。D7 没抓到是因为它的正则恰好先匹配到第一份合法 JSON
        （两份数据内容相同）。产物抽查时「困境出现两次」才暴露。这里锁死两条。
        """
        product = self._product()
        self.assertNotIn("__DASHBOARD_DATA__", product,
                         "产物里仍残留 __DASHBOARD_DATA__ 占位符，说明生成器没注入")
        n = product.count("const S_PIPELINE")
        self.assertEqual(n, 1,
                         "产物里 const S_PIPELINE 应只声明 1 次，实际 %d 次"
                         "（多半是模板注释里写了占位符字面量，被整段替换了）" % n)

    def test_d9_product_scripts_parse(self):
        """D9：产物全部内联脚本必须是合法 JS——语法错误 = 整页白屏。

        D8 的事故里双重声明是语法错误，script 块整体解析失败，看板直接空白。
        计数检查（D8）防的是已知模式，这里用 node --check 做通用兜底：任何让
        script 块解析失败的注入问题都会被抓住。本机没有 node 时跳过（CI 里
        build_all 先跑 npm 构建，node 一定在）。
        """
        node = shutil.which("node")
        if not node:
            self.skipTest("本机无 node，跳过 JS 语法检查")
        product = self._product()
        blocks = [b for b in
                  re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>",
                             product, re.S) if b.strip()]
        self.assertTrue(blocks, "产物里没有内联脚本？")
        for i, code in enumerate(blocks):
            with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False,
                                             encoding="utf-8") as f:
                f.write(code)
                tmp = f.name
            try:
                r = subprocess.run([node, "--check", tmp],
                                   capture_output=True, text=True)
            finally:
                Path(tmp).unlink(missing_ok=True)
            self.assertEqual(r.returncode, 0,
                             "产物内联脚本块 %d 有语法错误（看板会整页白）：\n%s"
                             % (i, r.stderr[:600]))


if __name__ == "__main__":
    unittest.main()
