"""舆情数据管道守卫（tests/test_sentiment_data.py）

测试设计文档
============

缺陷
----
估值看板「③ 市场舆情分布」的两个环形图（新闻情绪 / 卖方共识）只有计数、不可交互，
点不动、也看不到背后的企业与原文链接。要做「点正面/中性/负面 → 展开企业与来源链接」，
先得解决两件更基础的事：

1. **舆情数据是 2026-08-05 的旧快照**，比估值数据（as_of 2026-09-02）旧了 28 天。
   在这 28 天里 SK 海力士财报后目标价集体下修 27%–36%、京东方落选 iPhone 18 Pro
   OLED、立讯扣非增速掉到 6.47%——旧数据会把这些完全盖掉。
2. **双源漂移**：模板里硬编码了一份 ``MANUAL_SENTIMENT``（15 家 news/analyst 打分），
   ``tools/data/supplier_sentiment.csv`` 里另有一份结构化舆情。两份数据各改各的，
   没有任何机制保证一致。真要展开详情，就必须只有一个事实来源。

修复思路
--------
CSV 成为**唯一事实来源**：新增第 10 列 ``sources_detail``（JSON 数组，含
title/url/publisher/date），把「综述文本」和「可点击来源」放进同一行同一文件。
模板里的 ``MANUAL_SENTIMENT`` 删除，改为构建期由 ``scripts/build_sentiment_data.py``
从 CSV 派生并注入。

本文件要防的回归
----------------
1. **S1（僵尸 / 缺失）**：CSV 的 supplier_id 必须与看板管道的公司集合完全一致。
   公司进出研究范围时，这里先红——而不是让某家公司在环形图里永远算成「中性」。
2. **S2 / S3（字段与取值契约）**：情绪取值必须是枚举内的字符串；``sources`` 的 URL
   必须以 http(s) 开头、≥3 条、且**不含逗号**。逗号是硬性约束——
   ``tools/supplier_research/sentiment.py`` 用 ``split(",")`` 切这一列，一个含逗号的
   URL 会被切成两截，在舆情报告里变成两个坏链接。
3. **S4（核心·防双源漂移）**：``sources_detail`` 解析出的 URL 列表必须与 ``sources``
   列**逐条同序相等**。这两列服务的对象不同（前者给看板渲染链接卡片，后者给
   markdown 报告），内容却必须同源。测试把「记得同步改两处」变成「不同步就红」。
4. **S5（来源卡片可渲染）**：每条来源的 title / url / publisher / date 都必须非空，
   否则展开面板会出现空白标题或没有日期的链接。
5. **S6（生成器契约）**：产物必须是合法 JSON、news/analyst 落在 −1/0/1、
   且每条记录的文本与 CSV 逐字一致。
6. **S7 / S8（模板与产物）**：模板里不能再有手写打分表；``__SENTIMENT_DATA__``
   占位符在模板中恰好 1 次、在产物中 0 次——重演 D8 的占位符注释事故会让整页白屏。

为什么「≥3 条来源」而不是写死某个数
------------------------------------
来源条数取决于该公司的公开信息密度。写死 5 会在只有 4 条可靠来源时逼着凑数（凑数
就是引入内容农场链接的入口）。3 是「能让读者交叉验证」的下限。
"""

import csv
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

CSV_PATH = ROOT / "tools" / "data" / "supplier_sentiment.csv"
TPL = ROOT / "templates" / "supplier_dashboard_template.html"
PRODUCT = ROOT / "tools" / "visualizations" / "supplier_dashboard.html"

FIELDS = [
    "supplier_id", "as_of",
    "news_sentiment", "news_summary",
    "analyst_sentiment", "analyst_consensus",
    "key_catalysts", "key_risks",
    "sources", "sources_detail",
]
TEXT_FIELDS = ("news_summary", "analyst_consensus", "key_catalysts", "key_risks")
NEWS_ALLOWED = {"positive", "neutral", "negative"}
ANALYST_ALLOWED = {"bullish", "neutral", "bearish"}
MIN_SOURCES = 3


def _load_csv():
    """读取舆情 CSV（带 BOM），返回行列表。"""
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _urls(cell):
    """按 sentiment.py 的口径切分 sources 列。"""
    return [u.strip() for u in (cell or "").split(",") if u.strip()]


def _pipeline_ids():
    """看板管道里的公司 id 集合（估值数据的权威范围）。"""
    import build_dashboard_data as gen
    return {r["id"] for r in gen.build_rows()}


class SentimentCsvContract(unittest.TestCase):
    """CSV 本身的字段与取值契约。"""

    def test_s1_ids_match_pipeline(self):
        """S1：CSV 的 supplier_id 必须与看板管道完全一致（无僵尸、无缺失）。"""
        ids = [r["supplier_id"] for r in _load_csv()]
        self.assertEqual(len(ids), len(set(ids)), "CSV 里 supplier_id 有重复：%r" % ids)
        live = _pipeline_ids()
        self.assertEqual(set(ids) - live, set(),
                         "CSV 里有以下已不在看板数据中的公司（僵尸条目）：%r"
                         % sorted(set(ids) - live))
        self.assertEqual(live - set(ids), set(),
                         "看板里有公司缺少舆情数据（会永远按「中性」兜底）：%r"
                         % sorted(live - set(ids)))

    def test_s2_fields_and_enums(self):
        """S2：必备字段齐全、文本非空、情绪取值合法、as_of 统一。"""
        rows = _load_csv()
        self.assertTrue(rows, "CSV 为空")
        for r in rows:
            sid = r.get("supplier_id") or "<空 id>"
            for k in FIELDS:
                self.assertIn(k, r, "%s 缺少列 %s" % (sid, k))
                self.assertTrue((r[k] or "").strip(), "%s 的 %s 为空" % (sid, k))
            self.assertIn(r["news_sentiment"], NEWS_ALLOWED,
                          "%s.news_sentiment=%r 不在 %r 内"
                          % (sid, r["news_sentiment"], sorted(NEWS_ALLOWED)))
            self.assertIn(r["analyst_sentiment"], ANALYST_ALLOWED,
                          "%s.analyst_sentiment=%r 不在 %r 内"
                          % (sid, r["analyst_sentiment"], sorted(ANALYST_ALLOWED)))
            self.assertRegex(r["as_of"], r"^\d{4}-\d{2}-\d{2}$",
                             "%s.as_of 不是 YYYY-MM-DD：%r" % (sid, r["as_of"]))
        asofs = {r["as_of"] for r in rows}
        self.assertEqual(len(asofs), 1,
                         "CSV 里 as_of 不统一（数据分批刷新会让看板混用新旧口径）：%r"
                         % sorted(asofs))

    def test_s3_source_urls_are_safe_to_split(self):
        """S3：sources 列的 URL 必须可被 split(',') 安全切分。

        硬性约束来自 tools/supplier_research/sentiment.py：它用逗号切这一列渲染
        舆情报告的来源清单。URL 里出现一个逗号，就会在报告里被切成两个坏链接。
        """
        problems = []
        for r in _load_csv():
            sid = r["supplier_id"]
            urls = _urls(r["sources"])
            if len(urls) < MIN_SOURCES:
                problems.append("%s：来源仅 %d 条，少于下限 %d 条" % (sid, len(urls), MIN_SOURCES))
            for u in urls:
                if not u.startswith(("http://", "https://")):
                    problems.append("%s：来源 URL 未以 http(s):// 开头 -> %r" % (sid, u))
                if "," in u:
                    problems.append("%s：来源 URL 含逗号，会被 split(',') 切碎 -> %r" % (sid, u))
        self.assertEqual(problems, [], "sources 列有问题：\n  " + "\n  ".join(problems))

    def test_s4_sources_detail_matches_sources(self):
        """S4（核心·防双源漂移）：sources_detail 与 sources 必须同源同序。

        两列服务对象不同——``sources`` 给 markdown 报告（sentiment.py 按逗号切），
        ``sources_detail`` 给看板渲染可点击的链接卡片（带标题/媒体/日期）。放在
        同一行是为了只有一个事实来源；这条测试把「记得两边同步改」变成「不同步就红」。
        """
        problems = []
        for r in _load_csv():
            sid = r["supplier_id"]
            try:
                detail = json.loads(r["sources_detail"])
            except json.JSONDecodeError as e:
                problems.append("%s：sources_detail 不是合法 JSON -> %s" % (sid, e))
                continue
            if not isinstance(detail, list):
                problems.append("%s：sources_detail 应为数组，实际 %r" % (sid, type(detail)))
                continue
            want, got = _urls(r["sources"]), [d.get("url") for d in detail]
            if want != got:
                problems.append("%s：sources 与 sources_detail 的 URL 列表不一致\n"
                                "      sources=%r\n      detail =%r" % (sid, want, got))
        self.assertEqual(problems, [], "sources_detail 与 sources 漂移：\n  "
                         + "\n  ".join(problems))

    def test_s5_source_cards_are_renderable(self):
        """S5：每条来源的 title / url / publisher / date 必须齐全。

        展开面板要把这些渲染成「标题（媒体 · 日期）」的链接。缺任何一个，卡片上
        就会出现空白标题或没有日期的裸链接。
        """
        problems = []
        for r in _load_csv():
            sid = r["supplier_id"]
            for i, d in enumerate(json.loads(r["sources_detail"])):
                for k in ("title", "url", "publisher", "date"):
                    if not str(d.get(k) or "").strip():
                        problems.append("%s.sources[%d].%s 为空" % (sid, i, k))
                if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(d.get("date") or "")):
                    problems.append("%s.sources[%d].date 不是 YYYY-MM-DD：%r"
                                    % (sid, i, d.get("date")))
        self.assertEqual(problems, [], "来源卡片字段不完整：\n  " + "\n  ".join(problems))


class SentimentGenerator(unittest.TestCase):
    """scripts/build_sentiment_data.py 的输出契约。"""

    def test_s6_rows_come_from_csv(self):
        """S6：生成器的每一条都必须与 CSV 逐项一致（文本逐字、打分按映射表）。"""
        import build_sentiment_data as gen

        rows = gen.build_rows()
        self.assertEqual(gen.validate(rows), [],
                         "生成器自检未通过：%r" % gen.validate(rows))
        csv_by_id = {r["supplier_id"]: r for r in _load_csv()}
        self.assertEqual({r["id"] for r in rows}, set(csv_by_id),
                         "生成器输出的公司集合与 CSV 不一致")

        expect_news = {"positive": 1, "neutral": 0, "negative": -1}
        expect_an = {"bullish": 1, "neutral": 0, "bearish": -1}
        for r in rows:
            c = csv_by_id[r["id"]]
            self.assertEqual(r["news"], expect_news[c["news_sentiment"]],
                             "%s.news 映射错误" % r["id"])
            self.assertEqual(r["analyst"], expect_an[c["analyst_sentiment"]],
                             "%s.analyst 映射错误" % r["id"])
            for out_key, csv_key in (("newsSummary", "news_summary"),
                                     ("analystConsensus", "analyst_consensus"),
                                     ("catalysts", "key_catalysts"),
                                     ("risks", "key_risks")):
                self.assertEqual(r[out_key], c[csv_key].strip(),
                                 "%s.%s 与 CSV 不一致" % (r["id"], out_key))
            self.assertEqual([s["url"] for s in r["sources"]],
                             _urls(c["sources"]), "%s.sources 与 CSV 不一致" % r["id"])

    def test_s7_snippet_is_pure_json_value(self):
        """S7：render_snippet() 只能返回「值」，不能带声明。

        模板里写的是 ``const SENTIMENT_DETAIL = __SENTIMENT_DATA__;``，占位符标记的
        是等号右边的位置。生成器若连同声明一起吐出来，替换后会变成
        ``const X = const X = [...]``——整页脚本解析失败、看板全白。这是 D8 事故的
        同一模式，换了个数据块重演一次。
        """
        import build_sentiment_data as gen

        snippet = gen.render_snippet(gen.build_rows())
        self.assertFalse(snippet.lstrip().startswith("const"),
                         "render_snippet() 不应带 const 声明（模板里已有）")
        parsed = json.loads(snippet)          # 必须是合法 JSON，D7 式的逐项比对靠它
        self.assertEqual(len(parsed), len(gen.build_rows()))

    def test_s8_template_has_no_manual_sentiment(self):
        """S8：模板里不得再有手写打分表，只能是占位符。"""
        tpl = TPL.read_text(encoding="utf-8")
        self.assertNotIn("MANUAL_SENTIMENT", tpl,
                         "模板里仍有 MANUAL_SENTIMENT 手写打分表——舆情应全部由 CSV 派生，"
                         "否则又回到双源漂移")
        n = tpl.count("__SENTIMENT_DATA__")
        self.assertEqual(n, 1,
                         "模板中 __SENTIMENT_DATA__ 应恰好出现 1 次，实际 %d 次"
                         "（注释里写字面量也会被替换，会导致双份注入 + 语法错误）" % n)


class SentimentProduct(unittest.TestCase):
    """构建产物校验（产物缺失时跳过——它是 gitignore 的）。"""

    def _product(self):
        if not PRODUCT.is_file():
            self.skipTest("产物尚未构建（tools/visualizations/ 为 gitignore 产物）")
        return PRODUCT.read_text(encoding="utf-8")

    def test_s9_placeholder_replaced(self):
        """S9：产物里占位符已替换，且声明只出现一次。"""
        product = self._product()
        self.assertNotIn("__SENTIMENT_DATA__", product,
                         "产物里仍残留 __SENTIMENT_DATA__ 占位符，生成器没注入")
        n = product.count("const SENTIMENT_DETAIL")
        self.assertEqual(n, 1,
                         "产物里 const SENTIMENT_DETAIL 应只声明 1 次，实际 %d 次" % n)

    def test_s10_product_scripts_parse(self):
        """S10：产物内联脚本必须 node --check 通过（语法错误 = 整页白屏）。"""
        node = shutil.which("node")
        if not node:
            self.skipTest("本机无 node，跳过 JS 语法检查")
        blocks = [b for b in re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>",
                                        self._product(), re.S) if b.strip()]
        self.assertTrue(blocks, "产物里没有内联脚本？")
        for i, code in enumerate(blocks):
            with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False,
                                             encoding="utf-8") as f:
                f.write(code)
                tmp = f.name
            try:
                r = subprocess.run([node, "--check", tmp], capture_output=True, text=True)
            finally:
                Path(tmp).unlink(missing_ok=True)
            self.assertEqual(r.returncode, 0,
                             "产物内联脚本块 %d 有语法错误（看板会整页白）：\n%s"
                             % (i, r.stderr[:600]))


if __name__ == "__main__":
    unittest.main()
