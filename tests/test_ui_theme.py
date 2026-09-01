# -*- coding: utf-8 -*-
"""暗色主题统一（方案 A：全站统一暗色 + 腾讯地图 style1 墨渊）测试设计文档。

背景
----
ui-audit-report.md 主题债：index/table 已是暗色，dashboard 与 geo 页仍是浅色，
跨页跳转时亮暗突变。方案评估后确认「统一暗色 + TMap style1 + Leaflet CartoDB
dark_all」路线，暗色板对齐 index 现有令牌（bg #0c1020 / card #131a2e /
ink #e8ecf4 / muted #9fb0d0 / line #2a3450 / soft #1b2340），为未来加亮色
切换层（[data-theme="light"]）预留 CSS 变量化基础。

测试用例设计（T1–T10）
-----------------------
T1  dashboard :root 十个设计令牌全部翻为暗色值（逐令牌断言）。
T2  dashboard 浅色特征值绝迹：--bg:#f5f7fa / --card:#ffffff / --soft:#eef2f7 /
    --line:#e5e7eb 不再出现。
T3  dashboard Chart.js 暗色适配：Chart.defaults.color 为暗色可读色；#f0f0f0
    网格与 '#eee' 网格绝迹；verdict 颜色映射 C 使用暗底亮色变体
    （#6ea0ff/#f87171/#4ade80/#fbbf24）；环形图 borderColor 不再是白色。
T4  geo 页 TMap 初始化带 mapStyleId: 'style1'（墨渊深色官方样式）。
T5  geo 页 Leaflet 兜底瓦片换 CartoDB dark_all；openstreetmap 瓦片 URL 绝迹。
T6  geo 页浅色特征绝迹：#f8fafc / #fffbeb / #fef2f2 / #fff7ed / #fde68a /
    rgba(255,255,255,0.96)（面板白底）/ rgba(255,255,255,0.92)（poi 白底）。
T7  geo 页暗色特征存在：面板深底 rgba(19,26,46,0.96)、主文字 #e8ecf4、
    轨道/软底 #1b2340、TMap LabelStyle 深底 '#1b2340'。
T8  geo 页 Leaflet 弹窗暗色覆盖存在（leaflet-popup-content-wrapper 深底规则），
    弹窗内链接用亮蓝 #6ea0ff 而非 #2563eb。
T9  对比度达标（WCAG AA 正文 4.5:1）：dashboard --ink 对 --bg、--muted 对
    --card；geo 主文字 #e8ecf4 对面板深底；.fbtn 文字对软底。
T10 geo 页 .sup-search 输入框显式声明暗色 background 与 color（暗色面板中
    input 默认白底会刺眼，必须显式覆盖）。

注：geo_build.py 的 HTML 为 f-string 内联模板，源码中 CSS 花括号写作 {{ }}，
本测试按源文件字面内容匹配；构建产物（dist/）由 build_all 之后的抽查验证，
不在本文件覆盖范围。
"""
import re
import unittest

GEO = "tools/geo_build.py"
DASH = "templates/supplier_dashboard_template.html"

# 暗色板（对齐 index.html 现有暗色令牌）
DARK_TOKENS = {
    "--bg": "#0c1020",
    "--card": "#131a2e",
    "--ink": "#e8ecf4",
    "--muted": "#9fb0d0",
    "--blue": "#6ea0ff",
    "--red": "#f87171",
    "--green": "#4ade80",
    "--amber": "#fbbf24",
    "--line": "#2a3450",
    "--soft": "#1b2340",
}


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


# —— 令牌层适配（P1-6 色值令牌化后补）——
# 本文件最初写在「颜色全部硬编码」的年代，断言形如 `assertIn("--bg:#0c1020", root)`。
# 全站令牌化之后，使用侧一律写成 var(--bg)，定义侧也统一加了空格（--bg: #0c1020），
# 旧断言会大面积误报。这里补一层解析器：把 var(--x) 顺着本文件的 :root 解析成实际色值，
# 断言因此改为「语义校验」而非「字面匹配」，不再受排版与令牌化影响。
def _root_tokens(path):
    """解析文件的 :root 块 → {令牌名: 值}（值统一小写）。"""
    m = re.search(r":root\s*\{([^}]*)\}", _read(path))
    if not m:
        return {}
    return {k: v.strip().lower()
            for k, v in re.findall(r"(--[a-z0-9-]+):\s*([^;]+);", m.group(1))}


def _resolve(path, value):
    """把 var(--x) 解析成具体值；非 var 形式原样返回小写。解析不到返回空串。"""
    value = value.strip()
    m = re.fullmatch(r"var\(\s*(--[a-z0-9-]+)\s*\)", value)
    if not m:
        return value.lower()
    return _root_tokens(path).get(m.group(1), "")


def _without_root(path):
    """去掉 :root 定义块后的源码文本。

    T6 这类「浅色特征绝迹」的扫描必须排除 :root：令牌定义里合法地存着一批
    亮色（--warn-ink:#fde68a、--success-ink:#bbf7d0、--link:#dbeafe 等），
    它们是「深底上的亮字」，不是浅色主题残留。
    """
    return re.sub(r":root\s*\{[^}]*\}", "", _read(path))


def _luminance(hex_color):
    """WCAG 相对亮度。"""
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    def lin(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def _contrast(fg, bg):
    l1, l2 = sorted((_luminance(fg), _luminance(bg)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


class DashboardDarkTheme(unittest.TestCase):
    """T1–T3：dashboard 令牌翻转 + Chart.js 适配。"""

    def test_t1_root_tokens_dark(self):
        tokens = _root_tokens(DASH)
        self.assertTrue(tokens, "dashboard 应存在 :root 令牌块")
        for token, value in DARK_TOKENS.items():
            self.assertEqual(tokens.get(token), value,
                             f":root 中 {token} 应为暗色值 {value}，实际 {tokens.get(token)!r}")

    def test_t2_light_traits_gone(self):
        s = _read(DASH)
        for light in ("--bg:#f5f7fa", "--card:#ffffff", "--soft:#eef2f7",
                      "--line:#e5e7eb"):
            self.assertNotIn(light, s, f"浅色令牌 {light} 应已绝迹")

    def test_t3_chart_dark(self):
        s = _read(DASH)
        self.assertIn("Chart.defaults.color = '#9fb0d0'", s,
                      "Chart.js 全局默认文字色应为暗底可读色 #9fb0d0")
        self.assertNotIn("#f0f0f0", s, "浅色网格线 #f0f0f0 应绝迹")
        self.assertNotIn("'#eee'", s, "浅色网格线 '#eee' 应绝迹")
        for color in ("#6ea0ff", "#f87171", "#4ade80", "#fbbf24"):
            self.assertIn(color, s, f"verdict/舆情应使用暗底亮色变体 {color}")
        self.assertNotIn("borderColor:'#fff'", s,
                         "环形图描边不应再用白色（暗底应描卡片色）")


class GeoDarkTheme(unittest.TestCase):
    """T4–T8：geo 页地图样式 + 面板/控件暗色化。"""

    def test_t4_tmap_style1(self):
        s = _read(GEO)
        self.assertIn("mapStyleId: 'style1'", s,
                      "TMap 初始化应带 mapStyleId:'style1'（墨渊深色）")

    def test_t5_leaflet_dark_tiles(self):
        s = _read(GEO)
        self.assertIn("basemaps.cartocdn.com/dark_all", s,
                      "Leaflet 兜底瓦片应换 CartoDB dark_all")
        self.assertNotIn("tile.openstreetmap.org", s,
                         "OSM 标准瓦片 URL 应绝迹")

    def test_t6_light_traits_gone(self):
        # 排除 :root —— 令牌定义里合法地存着亮色（如 --warn-ink:#fde68a），
        # 它们是「深底亮字」而非浅色主题残留。
        s = _without_root(GEO)
        for light in ("#f8fafc", "#fffbeb", "#fef2f2", "#fff7ed", "#fde68a",
                      "rgba(255,255,255,0.96)", "rgba(255,255,255,0.92)"):
            self.assertNotIn(light, s, f"geo 浅色特征 {light} 应已绝迹")

    def test_t6b_light_token_values_are_ink_on_dark(self):
        """:root 里的亮色令牌必须只作「深底亮字」用，且对深底有足够的对比度。"""
        tokens = _root_tokens(GEO)
        soft = tokens.get("--soft", "#1b2340")
        for name in ("--warn-ink", "--success-ink", "--danger-ink", "--link",
                     "--ink", "--ink-soft", "--bright"):
            if name not in tokens:
                continue
            val = tokens[name]
            self.assertRegex(val, r"^#[0-9a-f]{3,8}$", f"{name} 应为 hex 色值")
            self.assertGreater(_luminance(val), 0.35,
                               f"{name}={val} 亮度过低，不像「深底上的亮字」")
            self.assertGreaterEqual(_contrast(val, soft), 4.5,
                                    f"{name}={val} 在 --soft 上未达 WCAG AA 4.5:1")

    def test_t7_dark_traits_present(self):
        s = _read(GEO)
        self.assertIn("rgba(19,26,46,0.96)", s, "面板应为深色半透底")
        self.assertIn("#e8ecf4", s, "主文字应为暗底可读色 #e8ecf4")
        self.assertIn("#1b2340", s, "轨道/软底应使用 #1b2340")
        self.assertIn("color: '#1b2340'", s,
                      "TMap LabelStyle 背景应为深色 #1b2340")

    def test_t8_popup_dark_override(self):
        s = _read(GEO)
        self.assertIn(".leaflet-popup-content-wrapper", s,
                      "应有 Leaflet 弹窗暗色覆盖规则")
        # 必须锁定「详情链接」这个 <a>：弹窗里还有供应商 ID（var(--muted-dim)）等
        # 别的显式颜色，宽泛匹配会抓错对象。
        m = re.search(r"""target=['"]_blank['"] style=['"]color:(var\(--[a-z0-9-]+\)|#[0-9a-fA-F]{3,8})['"]>""", s)
        self.assertIsNotNone(m, "弹窗内详情链接应显式声明颜色")
        self.assertEqual(_resolve(GEO, m.group(1)), "#6ea0ff",
                         "弹窗内链接应解析为暗底亮蓝 #6ea0ff")
        self.assertNotIn("style='color:#2563eb'", s,
                         "弹窗内链接不应再用浅底蓝 #2563eb")


class ContrastChecks(unittest.TestCase):
    """T9–T10：对比度与输入框显式暗色。"""

    def test_t9_contrast_aa(self):
        # dashboard 令牌对
        self.assertGreaterEqual(_contrast(DARK_TOKENS["--ink"], DARK_TOKENS["--bg"]), 4.5)
        self.assertGreaterEqual(_contrast(DARK_TOKENS["--muted"], DARK_TOKENS["--card"]), 4.5)
        # geo：主文字对面板深底（rgba(19,26,46,.96) 以 #131a2e 近似）
        self.assertGreaterEqual(_contrast("#e8ecf4", "#131a2e"), 4.5)
        # geo：.fbtn 文字 #c7d2ea 对软底 #1b2340
        self.assertGreaterEqual(_contrast("#c7d2ea", "#1b2340"), 4.5)

    def test_t10_sup_search_explicit_dark(self):
        s = _read(GEO)
        m = re.search(r"\.sup-search \{{[^}}]*\}}", s)
        self.assertIsNotNone(m, ".sup-search 规则应存在")
        rule = m.group(0)

        # 背景与文字都必须是「显式声明」，且解析后确实是深底亮字。
        # 接受 #hex 与 var(--x) 两种写法（令牌化后为后者）。
        def pick(prop):
            mm = re.search(prop + r":\s*(var\(--[a-z0-9-]+\)|#[0-9a-fA-F]{3,8})", rule)
            return _resolve(GEO, mm.group(1)) if mm else ""

        bg = pick("background")
        fg = pick("color")
        self.assertTrue(bg, ".sup-search 应显式声明 background（避免浏览器默认白底）")
        self.assertTrue(fg, ".sup-search 应显式声明 color")
        self.assertLess(_luminance(bg), 0.15,
                        f".sup-search 背景 {bg} 不够深，暗色面板里会刺眼")
        self.assertGreater(_luminance(fg), 0.5,
                           f".sup-search 文字 {fg} 不够亮，深底上读不清")
        self.assertGreaterEqual(_contrast(fg, bg), 4.5,
                                f".sup-search 文字/背景对比度未达 WCAG AA：{_contrast(fg, bg):.2f}:1")


if __name__ == "__main__":
    unittest.main(verbosity=2)
