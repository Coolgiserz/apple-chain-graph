#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""UI 响应式断点收敛测试（P2-4）。

将全站 5 种断点（480/600/820/860/880）收敛为两档：
  - 480px：小屏微调（仅 index，原有保留）
  - 860px：桌面/窄屏分界（与共享导航 topnav 的 min-width: 860 对齐）

测试设计（B1-B5）：
  B1 index.html：4 个 max-820 块全部改为 max-860；480 与 reduced-motion 保留；
     不再出现 820/600/880 旧断点。
  B2 table_page.html：max-600 改为 max-860；不再出现 600。
  B3 dashboard 模板：max-880 改为 max-860；不再出现 880。
  B4 topnav.py：min-860 锚点保持不变（分界基准，不随页面改动）。
  B5 geo_build.py：页面自身不引入断点（其 860 来自注入的 topnav CSS）。

运行：python -m unittest tests.test_ui_breakpoints
"""
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def _breakpoints(src):
    """返回源码中所有 @media 断点值的集合（忽略 reduced-motion 等非宽度查询）。"""
    vals = set()
    for m in re.finditer(r"@media[^{]+", src):
        q = m.group(0)
        for w in re.findall(r"(?:min|max)-width:\s*([\d.]+)px", q):
            vals.add(w)
    return vals


class BreakpointConvergenceTest(unittest.TestCase):
    """B1-B5：全站断点收敛为 {480, 860} 两档"""

    def test_b1_index_converged(self):
        src = _read("index.html")
        bp = _breakpoints(src)
        self.assertIn("860", bp, "index 缺少 860 断点")
        self.assertIn("480", bp, "index 的 480 小屏断点应保留")
        for old in ("820", "600", "880"):
            self.assertNotIn(old, bp, "index 仍含旧断点 %s" % old)
        self.assertEqual(src.count("@media (max-width: 860px)"), 4,
                         "index 应有 4 个 max-860 块（原 820×4）")

    def test_b2_table_page_converged(self):
        src = _read("templates", "table_page.html")
        bp = _breakpoints(src)
        self.assertEqual(bp, {"860"}, "table 断点应恰为 {860}，实际 %s" % bp)

    def test_b3_dashboard_converged(self):
        src = _read("templates", "supplier_dashboard_template.html")
        bp = _breakpoints(src)
        self.assertEqual(bp, {"860"}, "dashboard 断点应恰为 {860}，实际 %s" % bp)

    def test_b4_topnav_anchor_unchanged(self):
        src = _read("topnav.py")
        bp = _breakpoints(src)
        self.assertEqual(bp, {"860"}, "topnav 的 860 分界锚点不应变动，实际 %s" % bp)

    def test_b5_geo_page_has_no_own_breakpoint(self):
        src = _read("tools", "geo_build.py")
        self.assertEqual(_breakpoints(src), set(),
                         "geo 页自身不应引入宽度断点（其 860 来自注入的 topnav CSS）")


if __name__ == "__main__":
    unittest.main()
