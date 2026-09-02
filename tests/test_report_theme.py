#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""上下游报告页「浅色主题被共享导航污染」回归测试。

背景（真实事故）
----------------
报告页（dist/apple_supply_chain_report.html）是全站唯一的**浅色**页面：
白底 + 深色字（--ink:#1c2430），为长文档/表格阅读设计。

共享导航 topnav.py 的 TOPNAV_CSS 在**全局 :root** 上定义了一整套**暗色**令牌
（--bg:#0c1020 / --ink:#e8ecf4 / --card:#131a2e …）。scripts/report.py 按
``CSS + TOPNAV_CSS`` 顺序拼接，两个 :root 同名变量由后定义的暗色值胜出，于是：

    body{background:var(--bg);color:var(--ink)}   ← --ink 被覆盖成亮色 #e8ecf4
    tr:nth-child(even) td{background:#fafcff}     ← 斑马纹是**硬编码白色**

亮色文字压在白色斑马纹上，对比度约 1.06:1 —— 表格「根本看不清楚有什么字」。

根因不是某条规则写错，而是**共享组件把主题变量抛到全局作用域**，与宿主页面
主题同名冲突。修复方向因此是「作用域收窄」而非「改某个颜色值」：

    报告页的主题变量从 :root 收敛到 body 作用域。
    CSS 自定义属性就近继承 —— body 上定义的值优先于从 :root 继承来的值，
    因此**不依赖拼接顺序**（比把 CSS 挪到 TOPNAV_CSS 之后更稳，挪顺序一改就坏）。
    topnav 自身只用 --brand/--bright/--link/--fs-* 等品牌与字号令牌，与报告页
    覆盖的 10 个浅色令牌不相交，导航条样式不受影响。

为何不动 topnav.py
------------------
它的 :root 令牌块是 tests/test_ui_color_tokens.py CT1/CT2 认定的「五样式源」
之一（与 index / table_page / dashboard 模板 / geo_build 逐字比对防漏同步），
属于全站共享契约；且除报告页外 4 个页面都是暗色主题，覆盖后无感知差异。
为唯一一个浅色页面去改共享契约，收益小、回归面大。

测试设计（RT1-RT6）
-------------------
RT1 报告页 CSS 常量里不得再出现 :root{ —— 主题变量不再进全局作用域（防复发）。
RT2 10 个浅色令牌在 body 作用域声明且值正确（这是「不被 :root 覆盖」的结构保证）。
RT3 body 定义的令牌 ⊇ CSS 里 var() 引用的令牌 —— 防漏声明导致回落暗色值。
RT4 语义断言（直接锁事故现象）：表格文字色 --ink 与两种表格背景（--card #fff
    与斑马纹 #fafcff）的 WCAG 对比度均 ≥ 4.5:1（AA 正文标准）。
RT5 body 覆盖的令牌 ∩ topnav 实际使用的令牌 = ∅ —— 防修复动作误伤导航条
    （topnav 令牌从 TOPNAV_CSS 动态提取，避免手写清单过期）。
RT6 产物抽查：dist/apple_supply_chain_report.html 里 body 作用域带浅色令牌、
    且不含报告页自己的 :root{ 残留；产物未构建时 skipTest（CI 全量构建会覆盖）。

运行：python -m unittest tests.test_report_theme
"""
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def _css_const(src):
    """取出 scripts/report.py 里的 CSS 常量（三引号字符串）。"""
    m = re.search(r'^CSS = """(.*?)^"""', src, re.S | re.M)
    assert m, "未在 scripts/report.py 中找到 CSS 常量"
    return m.group(1)


def _strip_comments(css):
    """移除 /* ... */ 注释块后再做结构断言。

    说明性注释里为了讲清事故成因，会写出 `body{color:var(--ink)}` 这类示例片段；
    若不剥离，正则会把注释里的示例当成真实规则命中（报告页 body 规则因此被「抢」走，
    RT2 拿到空字典）。测试断言的是 CSS 结构，不该被注释文字左右。
    """
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def _vars_in(block):
    """返回块内声明的 {变量名: 值}。"""
    return dict(re.findall(r"(--[\w-]+)\s*:\s*([^;{}]+);", block))


def _refs(block):
    """返回块内 var() 引用的变量名集合。"""
    return set(re.findall(r"var\((--[\w-]+)", block))


def _lum(hex_color):
    """WCAG 相对亮度。"""
    h = hex_color.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))

    def lin(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def _contrast(a, b):
    """WCAG 对比度（1:1 ~ 21:1）。"""
    la, lb = _lum(a), _lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


# 报告页原本定义的浅色主题令牌（事故中被 topnav 暗色值覆盖的那一批）
LIGHT_TOKENS = {
    "--bg": "#f5f7fa", "--card": "#fff", "--ink": "#1c2430",
    "--muted": "#5b6b7d", "--line": "#e3e8ef", "--blue": "#0a66c2",
    "--blue2": "#e8f1fb", "--green": "#0e7c4f", "--amber": "#b06a00",
    "--red": "#b3261e",
}
# 表格的两种实际背景：卡片白 与 斑马纹（CSS 里硬编码，不随主题变）
TABLE_BG = ["#fff", "#fafcff"]


class ReportThemeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = _read("scripts", "report.py")
        cls.css = _strip_comments(_css_const(cls.src))

    def test_rt1_no_root_scope(self):
        """RT1 报告页 CSS 常量里不得再有 :root 变量声明块（防主题变量进全局作用域）。

        只认「根作用域选择器 + 块内确实声明了变量」的情形，而不是出现 :root 四个字符
        就报错 —— 本文件与 report.py 的说明注释里都会提到 :root，字符串级判断会误报。
        """
        hits = re.findall(r":root\s*\{[^}]*--[\w-]+\s*:", self.css, re.S)
        self.assertEqual([], hits,
                         "报告页主题变量不应定义在根作用域（会被 topnav 的暗色令牌覆盖）")

    def test_rt2_light_tokens_on_body(self):
        """RT2 10 个浅色令牌在 body 作用域声明且值正确。"""
        m = re.search(r"\bbody\s*\{([^}]*)\}", self.css, re.S)
        self.assertTrue(m, "CSS 常量里未找到 body 规则")
        declared = _vars_in(m.group(1))
        for name, val in LIGHT_TOKENS.items():
            self.assertIn(name, declared, "body 作用域缺少令牌 %s" % name)
            self.assertEqual(declared[name].strip(), val,
                             "令牌 %s 的值应为 %s，实际 %s" % (name, val, declared[name]))

    def test_rt3_body_covers_all_refs(self):
        """RT3 body 声明的令牌必须覆盖 CSS 里所有 var() 引用，防回落暗色。"""
        m = re.search(r"\bbody\s*\{([^}]*)\}", self.css, re.S)
        declared = set(_vars_in(m.group(1))) if m else set()
        # CSS 常量自身的引用（topnav CSS 不在其中，其引用由 :root 提供）
        missing = _refs(self.css) - declared
        self.assertEqual(set(), missing,
                         "CSS 引用了 body 未声明的令牌，会回落到 :root 的暗色值：%s"
                         % sorted(missing))

    def test_rt4_table_text_contrast(self):
        """RT4 表格文字色 vs 表格背景，对比度须达 WCAG AA（≥4.5:1）。"""
        m = re.search(r"\bbody\s*\{([^}]*)\}", self.css, re.S)
        declared = _vars_in(m.group(1)) if m else {}
        ink = declared.get("--ink", "").strip()
        self.assertTrue(ink, "body 未声明 --ink")
        for bg in TABLE_BG:
            ratio = _contrast(ink, bg)
            self.assertGreaterEqual(
                ratio, 4.5,
                "表格文字 %s 与背景 %s 的对比度仅 %.2f:1（<4.5，看不清）" % (ink, bg, ratio))

    def test_rt5_no_bleed_into_topnav(self):
        """RT5 body 覆盖的令牌不得与 topnav 使用的令牌相交，防误伤导航条。"""
        from topnav import TOPNAV_CSS
        m = re.search(r"\bbody\s*\{([^}]*)\}", self.css, re.S)
        declared = set(_vars_in(m.group(1))) if m else set()
        overlap = declared & _refs(TOPNAV_CSS)
        self.assertEqual(set(), overlap,
                         "body 覆盖了 topnav 也在用的令牌，会改动导航条样式：%s" % sorted(overlap))

    def test_rt6_built_output(self):
        """RT6 产物抽查：body 作用域带浅色令牌、无报告页 :root{ 残留。"""
        out = os.path.join(ROOT, "dist", "apple_supply_chain_report.html")
        if not os.path.exists(out):
            self.skipTest("报告产物尚未构建（跑 build_all.py 后会覆盖本用例）")
        html = _strip_comments(_read("dist", "apple_supply_chain_report.html"))
        roots = re.findall(r":root\s*\{[^}]*--[\w-]+\s*:", html, re.S)
        # 产物里应当只剩 topnav 注入的那一个 :root（报告页自己的已移除）
        self.assertEqual(1, len(roots),
                         "产物中的 :root 块应只剩 topnav 注入的 1 个，实际 %d 个" % len(roots))
        self.assertIn("--ink:#1c2430", html.replace(" ", ""),
                      "产物 body 作用域未携带浅色 --ink")


if __name__ == "__main__":
    unittest.main()
