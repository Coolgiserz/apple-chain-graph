#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""UI 可访问性（a11y）静态断言测试。

对应审查报告（ui-audit-report.md v1.0）P1-1/P1-2/P1-3/P1-4 与 P2-1/P2-6/P2-7/P2-8
的修复验证。静态断言针对**源文件**（模板/静态页/生成器），不针对 dist 构建产物。

测试设计（T1-T9）：
  T1 焦点可见（P1-1）：index.html 与 table_page.html 均需声明 :focus-visible
     outline 规则，覆盖此前 outline:none 的控件。
  T2 label 绑定（P1-2）：table 四个筛选 select 的 <label> 必须带 for 且与
     控件 id 成对；index 产品线 label 绑 #line。
  T3 搜索框可访问名（P1-2）：两个页面的搜索 input 需有 aria-label
     （placeholder 不算可访问名）。
  T4 表头语义与键盘排序（P1-3/P2-2）：<th> 需 scope="col" + tabindex="0"；
     JS 需含 keydown 处理与 aria-sort 更新。
  T5 canvas 替代文本（P1-4）：首页主 canvas 需 role="img" + aria-label。
  T6 触控目标（P2-7）：geo .fbtn 上下 padding ≥ 5px（总高 ≥ 24px）；
     index .td-close 需有 padding。
  T7 fbtn hover（P2-6）：geo 模板需含 .fbtn:hover 规则。
  T8 非文本对比度（P2-1）：geo 模板 #94a3b8 绝迹、替换色 #64748b 对白底
     ≥ 3:1；dashboard 模板 #9ca3af 绝迹、替换色 #71717a 对白底 ≥ 3:1。
  T9 减少动效（P2-8）：index/table 需含 prefers-reduced-motion 媒体查询。

运行：python -m unittest tests.test_ui_a11y
"""
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def _contrast(fg, bg):
    """WCAG 相对亮度对比度（fg/bg 为 #rrggbb）。"""
    def lum(h):
        h = h.lstrip("#")
        r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
        f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
        return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)
    la, lb = lum(fg), lum(bg)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


class FocusVisibleTest(unittest.TestCase):
    """T1 焦点可见（P1-1）"""

    def test_index_has_focus_visible(self):
        src = _read("index.html")
        self.assertIn(":focus-visible", src)
        # 焦点规则必须带非零 outline（而非仅声明伪类）
        m = re.search(r":focus-visible[^}]*outline\s*:\s*2px", src)
        self.assertIsNotNone(m, "index.html 缺少 :focus-visible + 2px outline 规则")

    def test_table_page_has_focus_visible(self):
        src = _read("templates", "table_page.html")
        self.assertRegex(src, r":focus-visible[^}]*outline\s*:\s*2px")


class LabelBindingTest(unittest.TestCase):
    """T2/T3 label 绑定与搜索框可访问名（P1-2）"""

    def test_table_filter_labels_bound(self):
        src = _read("templates", "table_page.html")
        for ctl in ("fRegion", "fCountry", "fCategory", "fTier"):
            self.assertIn('for="%s"' % ctl, src, "缺少 label for=%s" % ctl)
            self.assertIn('id="%s"' % ctl, src)

    def test_index_line_label_bound(self):
        src = _read("index.html")
        self.assertIn('for="line"', src)
        self.assertIn('id="line"', src)

    def test_search_inputs_have_aria_label(self):
        for path in (("index.html",), ("templates", "table_page.html")):
            src = _read(*path)
            self.assertRegex(src, r'type="search"[^>]*aria-label=',
                             "%s 搜索框缺少 aria-label" % "/".join(path))


class TableHeaderSemanticsTest(unittest.TestCase):
    """T4 表头语义与键盘排序（P1-3 / P2-2）"""

    def setUp(self):
        self.src = _read("templates", "table_page.html")

    def test_th_scope_and_tabindex(self):
        n_scope = len(re.findall(r'<th[^>]*scope="col"', self.src))
        n_tab = len(re.findall(r'<th[^>]*tabindex="0"', self.src))
        self.assertGreaterEqual(n_scope, 7, "th 缺 scope=col（7 个排序列）")
        self.assertGreaterEqual(n_tab, 7, "th 缺 tabindex=0")

    def test_keyboard_sort_and_aria_sort(self):
        self.assertIn("keydown", self.src, "排序缺 keydown 键盘事件")
        self.assertIn("aria-sort", self.src, "排序缺 aria-sort 更新")


class CanvasAriaTest(unittest.TestCase):
    """T5 canvas 替代文本（P1-4）"""

    def test_main_canvas_has_role_and_label(self):
        src = _read("index.html")
        m = re.search(r'<canvas id="cv"[^>]*>', src)
        self.assertIsNotNone(m, "未找到主 canvas")
        self.assertIn('role="img"', m.group(0))
        self.assertRegex(m.group(0), r'aria-label="[^"]+"' )


class TouchTargetTest(unittest.TestCase):
    """T6 触控目标（P2-7）"""

    def test_geo_fbtn_vertical_padding(self):
        src = _read("tools", "geo_build.py")
        m = re.search(r"\.fbtn \{\{[^}]*padding:\s*(\d+)px\s+(\d+)px", src)
        self.assertIsNotNone(m, "geo_build.py 中未找到 .fbtn padding")
        self.assertGreaterEqual(int(m.group(1)), 5, ".fbtn 上下 padding 需 ≥5px")

    def test_index_td_close_has_padding(self):
        src = _read("index.html")
        m = re.search(r"\.td-close\s*\{[^}]*padding", src)
        self.assertIsNotNone(m, ".td-close 缺 padding（触控目标过小）")


class InteractionFeedbackTest(unittest.TestCase):
    """T7 fbtn hover（P2-6）"""

    def test_geo_fbtn_hover_rule(self):
        src = _read("tools", "geo_build.py")
        self.assertRegex(src, r"\.fbtn:hover\s*\{\{")


class NonTextContrastTest(unittest.TestCase):
    """T8 非文本对比度（P2-1，WCAG 1.4.11 要求 ≥3:1）"""

    def test_geo_legacy_gray_removed(self):
        src = _read("tools", "geo_build.py")
        self.assertNotIn("#94a3b8", src, "geo 模板仍含 2.56:1 的 #94a3b8")
        self.assertIn("#64748b", src, "geo 模板应使用 #64748b 替换")

    def test_geo_replacement_meets_3_to_1(self):
        # 暗色主题（见 test_ui_theme.py）：标记渲染在暗色瓦片/页面底 #0c1020 上
        self.assertGreaterEqual(_contrast("#64748b", "#0c1020"), 3.0)

    def test_dashboard_legacy_gray_removed(self):
        src = _read("templates", "supplier_dashboard_template.html")
        self.assertNotIn("#9ca3af", src, "dashboard 模板仍含 2.54:1 的 #9ca3af")
        self.assertNotIn("#71717a", src, "暗色主题后 #71717a 在暗底偏闷，应升级为 #7a8bb0/#4a5878")
        self.assertIn("#7a8bb0", src, "dashboard 图表中性色应使用 #7a8bb0")

    def test_dashboard_replacement_meets_3_to_1(self):
        # 暗色主题（见 test_ui_theme.py）：底色由白底换为卡片色 #131a2e
        self.assertGreaterEqual(_contrast("#7a8bb0", "#131a2e"), 3.0)


class ReducedMotionTest(unittest.TestCase):
    """T9 减少动效（P2-8）"""

    def test_reduced_motion_media_query(self):
        for path in (("index.html",), ("templates", "table_page.html")):
            src = _read(*path)
            self.assertIn("prefers-reduced-motion", src,
                          "%s 缺 prefers-reduced-motion" % "/".join(path))


if __name__ == "__main__":
    unittest.main()
