#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据规模一致性测试：防止「数据改了、页面文案没改」的硬编码漂移。

背景（2026-09-10 事故复盘）：
    首页 index.html 自 Plan C 起是**静态页、手工维护**（build_viewer.py 不再生成它，
    见该文件 L3-7 注释）。而 SEO 元信息与正文里写死了「28 款产品 / 27 类零部件 /
    60 家供应商 / 571 条边 / 115 节点」这类规模数字。数据一变，这些数字就 silently
    失真——且对外是 SEO 直接可见的错误信息。

    更糟的是，同一「边数」指标在仓库里曾同时存在 510 / 521 / 571 三个版本
    （README、UX_REVIEW、index.html 各说各话），说明这类数字从未被统一治理过。

本测试的做法：
    从 data/apple_supply_chain.json **实算**当前规模，再断言页面文案里必须出现这些
    数字。数据一变，测试立刻变红，强制同步文案——而不是等被人肉发现。

    「数字 + 量词」的组合式断言（如 "34 款" 而非裸 "34"）是为了避免误伤 CSS 里的
    860px、28px 之类无关数值。

运行：python -m unittest tests.test_data_scale_consistency
"""
import json
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRAPH_JSON = os.path.join(ROOT, "data", "apple_supply_chain.json")


def load_graph_scale():
    """从图谱 JSON 实算规模。返回 (数值字典, 中文量词短语集合)。

    返回两类结果：
    - scale: 纯数字，供「数字+量词」组合断言使用
    - phrases: 已拼好的「数字+量词」短语，直接断言其是否出现在文案中
    """
    with open(GRAPH_JSON, encoding="utf-8") as f:
        d = json.load(f)
    nodes, edges = d["nodes"], d["edges"]
    n_prod = len(nodes["products"])
    n_comp = len(nodes["components"])
    n_supp = len(nodes["suppliers"])
    n_base = len(nodes["bases"])
    edge_keys = [
        "uses_component",
        "supplied_by",
        "assembled_by",
        "manufactured_at",
        "operated_by",
    ]
    n_edge = sum(len(edges.get(k, [])) for k in edge_keys)

    scale = {
        "n_products": n_prod,
        "n_components": n_comp,
        "n_suppliers": n_supp,
        "n_bases": n_base,
        "n_nodes": n_prod + n_comp + n_supp + n_base,
        "n_edges": n_edge,
        # 「供应商」在文案里也常写作「企业」（如 templates/table_page.html 的 title）
        "phr_suppliers_jia": "%d 家" % n_supp,
        "phr_products_kuan": "%d 款" % n_prod,
        "phr_components_lei": "%d 类" % n_comp,
        "phr_components_ge": "%d 个" % n_comp,
        "phr_edges": "%d 条" % n_edge,
        "phr_nodes": "%d 节点" % (n_prod + n_comp + n_supp + n_base),
    }
    return scale


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def meta_contents(html):
    """提取 index.html 里所有 <title> 与 meta 的可见文案（title/og/twitter/description）。"""
    out = []
    m = re.search(r"<title>([^<]*)</title>", html)
    if m:
        out.append(("title", m.group(1)))
    for m in re.finditer(r"<meta\s[^>]*>", html, re.I):
        tag = m.group(0)
        cm = re.search(r'content="([^"]*)"', tag)
        if not cm:
            continue
        # 只关心对 SEO / 社交卡片可见的几类
        if re.search(r'property="(og:|twitter:)|name="(description|twitter:)', tag):
            key = "meta"
            nm = re.search(r'(?:property|name)="([^"]+)"', tag)
            if nm:
                key = nm.group(1)
            out.append((key, cm.group(1)))
    return out


def seo_text(html):
    """提取 <div class="seo-text">…</div> 的正文（首页 SEO 主体段落）。"""
    m = re.search(r'<div[^>]*\bclass="seo-text"[^>]*>(.*?)</div>', html, re.S)
    return m.group(1) if m else ""


class IndexHtmlScaleTest(unittest.TestCase):
    """首页 index.html 的 SEO 文案必须与图谱实际规模一致。"""

    @classmethod
    def setUpClass(cls):
        cls.scale = load_graph_scale()
        cls.html = read(os.path.join(ROOT, "index.html"))

    def test_meta_title_and_description_use_current_scale(self):
        # SEO 元信息里不应残留旧的数量短语（只要出现过就说明文案没跟上数据）
        stale = [
            "28 款",
            "27 类",
            "60 家",
            "60家",
            "571 条",
            "115 节点",
        ]
        for key, text in meta_contents(self.html):
            for s in stale:
                self.assertNotIn(
                    s,
                    text,
                    "index.html 的 <%s> 仍写着过期的「%s」，与图谱当前规模不符" % (key, s),
                )

    def test_meta_description_states_current_scale(self):
        # 正向断言：description 必须写出当前真实规模，而不只是「没有旧数字」
        desc = ""
        for key, text in meta_contents(self.html):
            if key in ("description", "og:description", "twitter:description"):
                desc = text
                break
        self.assertTrue(desc, "index.html 找不到 description / og:description")
        s = self.scale
        self.assertIn("%d 款" % s["n_products"], desc)
        self.assertIn("%d 家" % s["n_suppliers"], desc)
        self.assertIn("%d 条" % s["n_edges"], desc)

    def test_seo_text_states_current_scale(self):
        body = seo_text(self.html)
        self.assertTrue(body, "index.html 找不到 <div class='seo-text'> 正文")
        s = self.scale
        self.assertIn("%d 款产品型号" % s["n_products"], body)
        self.assertIn("%d 个核心零部件" % s["n_components"], body)
        self.assertIn("%d 家供应商" % s["n_suppliers"], body)
        self.assertIn("%d 条上下游关系边" % s["n_edges"], body)
        self.assertIn("%d 节点" % s["n_nodes"], body)

    def test_seo_text_lists_every_single_point_component(self):
        """单点依赖清单必须完整——新增的单点件若漏写，这里会变红。

        2026-09-10 的教训：新增 esim_module 后它成为第二个单点依赖部件，
        但 SEO 正文的 <ul> 里仍只列了 audio_codec，属「内容漏项」而非「数字过期」，
        普通数字断言抓不到，故单独一条。
        """
        with open(GRAPH_JSON, encoding="utf-8") as f:
            d = json.load(f)
        nsup = {}
        for e in d["edges"]["supplied_by"]:
            nsup[e["from"]] = nsup.get(e["from"], 0) + 1
        singles = [cid for cid, n in nsup.items() if n == 1]
        self.assertTrue(singles, "图谱里应当至少有一个单点依赖部件，否则断言失去意义")

        name_of = {c["id"]: c["name"] for c in d["nodes"]["components"]}
        body = seo_text(self.html)
        for cid in singles:
            nm = name_of.get(cid, cid)
            self.assertIn(
                nm,
                body,
                "SEO 正文的单点依赖清单漏了「%s」（%s）——它是 n=1 的独家供应部件" % (nm, cid),
            )

    def test_seo_text_has_no_stale_scale_numbers(self):
        body = seo_text(self.html)
        for s in ("28 款", "27 个", "27 类", "60 家", "571 条", "115 节点"):
            self.assertNotIn(s, body, "SEO 正文仍残留过期规模描述「%s」" % s)


class LocalesScaleTest(unittest.TestCase):
    """locales/*.json 的报告头部说明必须与图谱规模一致（四语都要改）。"""

    @classmethod
    def setUpClass(cls):
        cls.scale = load_graph_scale()

    def test_report_header_source_matches_scale(self):
        s = self.scale
        for lng in ("zh", "en", "fr", "ja"):
            path = os.path.join(ROOT, "locales", lng + ".json")
            if not os.path.exists(path):
                continue
            data = json.loads(read(path))
            src = data.get("report.header.source", "")
            self.assertTrue(src, "locales/%s.json 缺 report.header.source" % lng)
            # 正向：必须写出当前规模
            for num in (s["n_suppliers"], s["n_components"], s["n_products"]):
                self.assertIn(
                    str(num),
                    src,
                    "locales/%s.json 的 report.header.source 未体现当前规模（缺 %d）" % (lng, num),
                )
            # 反向：不得残留旧规模
            for old in (60, 27, 28):
                self.assertNotIn(
                    str(old),
                    src,
                    "locales/%s.json 的 report.header.source 仍写着过期数字 %d" % (lng, old),
                )


class ReadmeScaleTest(unittest.TestCase):
    """README 里的供应商数量表述必须与实际供应商数一致。"""

    @classmethod
    def setUpClass(cls):
        cls.scale = load_graph_scale()

    def test_readme_supplier_count_matches(self):
        s = self.scale
        for name in ("README.md", "README_en.md"):
            path = os.path.join(ROOT, name)
            if not os.path.exists(path):
                continue
            text = read(path)
            self.assertNotIn(
                "60 家",
                text,
                "%s 仍写着「60 家」供应商，实际为 %d 家" % (name, s["n_suppliers"]),
            )
            if name == "README.md":
                self.assertIn(
                    "%d 家" % s["n_suppliers"],
                    text,
                    "README.md 未写明当前供应商数 %d" % s["n_suppliers"],
                )

    def test_readme_graph_size_matches(self):
        """README 里「约 N 节点 / M 关系」的规模描述必须与图谱一致。

        历史上这里出现过 510 / 521 两个与 index.html 的 571 互不相同的数字，
        属长期未治理的漂移，故单列一条。
        """
        s = self.scale
        path = os.path.join(ROOT, "README.md")
        if not os.path.exists(path):
            self.skipTest("README.md 不存在")
        text = read(path)
        for m in re.finditer(r"约?\s*(\d+)\s*节点\s*/\s*(\d+)\s*(?:关系|条|边)", text):
            self.assertEqual(
                int(m.group(1)),
                s["n_nodes"],
                "README.md 写「%s 节点」，图谱实为 %d 节点" % (m.group(1), s["n_nodes"]),
            )
            self.assertEqual(
                int(m.group(2)),
                s["n_edges"],
                "README.md 写「%s 关系」，图谱实为 %d 条边" % (m.group(2), s["n_edges"]),
            )

    def test_table_page_title_matches(self):
        s = self.scale
        path = os.path.join(ROOT, "templates", "table_page.html")
        if not os.path.exists(path):
            self.skipTest("templates/table_page.html 不存在")
        text = read(path)
        self.assertNotIn(
            "60 家企业",
            text,
            "templates/table_page.html 的 title 仍写着「60 家企业」，实际为 %d 家" % s["n_suppliers"],
        )


class GraphScaleSanityTest(unittest.TestCase):
    """规模实算本身的自检：防止上面的断言建立在错误的基数上。"""

    def test_scale_is_consistent_with_neo4j_csv(self):
        """JSON 与导出的 Neo4j CSV 行数必须一致（两处同源，数量应相同）。"""
        import csv

        s = load_graph_scale()
        cases = [
            ("products.csv", s["n_products"]),
            ("components.csv", s["n_components"]),
            ("suppliers.csv", s["n_suppliers"]),
        ]
        for fname, expected in cases:
            path = os.path.join(ROOT, "data", "neo4j", fname)
            if not os.path.exists(path):
                continue
            with open(path, newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(
                len(rows),
                expected,
                "data/neo4j/%s 有 %d 行，但图谱 JSON 里是 %d 个" % (fname, len(rows), expected),
            )


if __name__ == "__main__":
    unittest.main()
