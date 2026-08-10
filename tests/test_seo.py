#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SEO / 安全相关单元测试（构建期 + 可索引文本转义 + 内联 JSON 防注入）。

运行：python -m unittest tests.test_seo
前置：仓库根在 sys.path（本文件会自动把父目录加入 sys.path）。
"""
import os
import sys
import json
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
# build_viewer.py 位于 scripts/，其依赖 topnav 位于仓库根，二者都需加入 sys.path
for p in (SCRIPTS, ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

import build_viewer as bv  # noqa: E402  (导入会加载 topnav 与数据集，属正常前置)


class SeoEscapeTest(unittest.TestCase):
    def test_seo_text_html_escapes_data_driven_names(self):
        # 模拟「单点依赖部件」的组件名 / 供应商名含 HTML / 脚本注入字符
        bv.seo_single_points = lambda risk: [
            ("<script>alert(1)</script>", "Evil&Co", 0.99),
            ("正常部件", "A&B<c>", 0.5),
        ]
        html = bv.seo_text_html({"components": [], "product_lines": []})
        # 关键：原始注入片段绝不应出现在输出中
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertNotIn("Evil&Co", html)
        self.assertNotIn("A&B<c>", html)
        # 且应被转义为实体
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("Evil&amp;Co", html)
        self.assertIn("A&amp;B&lt;c&gt;", html)

    def test_inline_json_neutralizes_script_close(self):
        payload = {"x": "</script><script>alert(1)</script>", "name": "<b>A&B</b>"}
        out = bv.inline_json(payload)
        # 不应出现可闭合 <script> 的裸标签，< 必须转为 \u003c
        self.assertNotIn("</script>", out)
        self.assertIn("\\u003c", out)
        # 还原后语义与原文等价（合法 JSON 转义）
        self.assertEqual(json.loads(out), payload)

    def test_inline_json_preserves_unicode(self):
        out = bv.inline_json({"k": "苹果供应链"})
        self.assertIn("苹果供应链", out)
        self.assertEqual(json.loads(out)["k"], "苹果供应链")


if __name__ == "__main__":
    unittest.main()
