# -*- coding: utf-8 -*-
"""色值令牌化（P1-6）测试设计文档。

背景
----
UI 审查报告 P1-6：全站 347 处硬编码颜色、0 个 CSS 变量（index.html 独占 197 处，
含 40 种唯一色）。dashboard 是唯一正面案例（10 个 `:root` 变量），报告建议
「把 dashboard 模式反向推广到其余文件」。

扫描结论（改造前）
------------------
CSS 侧（`<style>` 内、`:root` 定义除外）共 277 处硬编码色值 / 51 种唯一色；
其中 JS 与 Python 数据侧（geo 的 `__HEX` 字典、`COLORS` 字典、marker SVG、
Chart.js 配置）的色值属于数据色，用 var() 会失效，必须排除。

归并策略（谨慎归并，仅合并色差极小或语义完全相同的近义色）
----------------------------------------------------------
- 页面底：#0c1020 / #0f1320 / #15203a → --bg
- 卡片面：#131a2e / #161c2e / #1c2740 → --card
- 软底：  #1b2340 / #1b2742 → --soft
- 弱分隔：#1c2336 → --line-soft（9 处均为 border，不可并入更亮的 --line）
- 浅文字：#cfe0ff / #cdd8ee / #b9c6e0 / #9fc1ff / #c7d2ea / #cbd5e1 → --ink-soft
- 危险字：#ffb4b4 / #f3b4b4 / #c9b6b6 → --danger-ink
- 警告底：#2b2313 / #3a2e16 / #3a2f10 → --warn-bg
- 绿系：  #4ade80 / #10b981 / #67e0a3 → --green
- 焦点：  #5b8cff / #4f8cff → --focus

刻意保持硬编码（7 处）：#8b5cf6 / #ec4899 / #22d3ee（节点分类数据色）、
#5b8cff88（带 alpha 后缀，var 无法拼 alpha）、#1e3a8a（品牌渐变终点）、#9776。

测试用例设计（CT1–CT6）
-----------------------
CT1 五个样式源的 `:root` 色值令牌块（33 个）按序拼接后完全一致 —— 防漏同步。
CT2 每处均定义全部 33 个令牌且值正确。
CT3 CSS 侧（`<style>` 内且非 `:root` 定义）映射表覆盖的旧硬编码值彻底绝迹。
CT4 CSS 侧引用的色值 var() 全部属于已定义令牌集 —— 防引用未定义令牌。
CT5 CSS 侧色值 var() 引用总数恰为 292，防漏改 / 多改（口径见下）。
CT6 geo 的数据侧色值（JS `__HEX` 字典、Python `COLORS`、marker SVG）保持硬编码，
    未被误改成 var() —— 数据色一旦 var 化会在 JS 上下文失效。

CT5 计数口径（310 = 270 新增 + 22 存量 + 18 内联）
--------------------------------------------------
第一段 · `<style>` 块内的硬编码（以 PR #54 之后的 HEAD 为基线）：

    index.html      179     templates/table_page.html   32
    geo_build.py     41     topnav.py                   14
    supplier_dashboard_template.html                     4   ← 新增仅 4
                                                    合计 270

  dashboard 之所以只有 4 处，是因为 PR #53 已把它改造成正面案例（10 个 `:root`
  变量、22 处 var() 引用）。本轮为它补齐剩余 4 处并把 10 个变量扩充到 33 个。

第二段 · dashboard `<style>` 内 PR #53 遗留的存量 var()：22 处。

第三段 · DOM 内联 `style="..."` 属性（第一版 `_css_zone` 漏掉的盲区）：

    index.html 图例色点 11（--muted ×1、--primary ×2、--warn ×3、
                            --green ×2、--red ×2）
    geo_build.py      3（图例 --warn、弹窗 --muted-dim、弹窗链接 --blue）
    dashboard 象限边框 4（--blue / --amber / --green / --red，PR #53 已 var 化）

    新增 14 + 存量 4 = 18

    内联样式同样解析 `:root` 的 var()，因此可以安全令牌化；但 canvas 的
    `ctx.fillStyle`、Chart.js dataset、TMap API 属于数据侧，var() 会失效，
    必须保持字面量 —— 由 CT6 与 CT7 分别守住。

合计 270 + 22 + 18 = 310。

坑点记录（本轮踩到两次，测试必须按「词元」而非「子串」匹配）
------------------------------------------------------------
1. `#5b8cff`（--focus 的值）刻意保持硬编码的实例是 **8 位** `#5b8cff88`
   （box-shadow 带 alpha 后缀，var() 无法拼 alpha）。若用 `"#5b8cff" in css`
   这种子串判断会误报。必须用带负向前瞻的词元正则：
   `#[0-9a-fA-F]{8}(?![0-9a-fA-F])|#[0-9a-fA-F]{6}(?![0-9a-fA-F])|#[0-9a-fA-F]{3}(?![0-9a-fA-F])`
   即「8 位优先，其次 6 位，最后 3 位，且右侧不得再跟 hex 字符」。
2. 同理 `#fff` 是 `--bright` 的 3 位写法，不能与 `#ffffff` 混为一谈。

注：geo_build.py 的 HTML 为 f-string 内联模板（花括号写作 {{ }}），本测试按
源文件字面匹配；构建产物由 build_all 之后抽查验证。
"""
import re
import unittest

FILES = [
    "index.html",
    "templates/table_page.html",
    "templates/supplier_dashboard_template.html",
    "tools/geo_build.py",
    "topnav.py",
]

TOKENS = {
    # 底与面
    "--bg": "#0c1020", "--card": "#131a2e", "--soft": "#1b2340",
    "--line": "#2a3450", "--line-soft": "#1c2336",
    # 文字
    "--ink": "#e8ecf4", "--ink-soft": "#cfe0ff", "--muted": "#9fb0d0",
    "--muted-dim": "#7c8aa8", "--bright": "#ffffff", "--link": "#dbeafe",
    "--ink-inverse": "#111111",
    # 控件态
    "--control": "#33406a", "--control-hover": "#3a4a6e", "--control-border": "#3f4f7a",
    # 强调与品牌
    "--blue": "#6ea0ff", "--primary": "#2f6fed", "--primary-hover": "#3b82f6",
    "--focus": "#5b8cff", "--brand": "#0a2540", "--brand-2": "#0a66c2",
    # 语义色
    "--green": "#4ade80", "--success-ink": "#bbf7d0", "--success-bg": "#163a2a",
    "--red": "#f87171", "--danger-ink": "#ffb4b4", "--danger-bg": "#3b1520",
    "--danger-line": "#7f1d1d",
    "--amber": "#fbbf24", "--warn": "#f59e0b", "--warn-ink": "#fde68a",
    "--warn-bg": "#3a2e16", "--warn-line": "#7a5c14",
    # 节点分类色：画布经 src/engine/util.js 的 getComputedStyle 读取，与图例 var() 同源
    "--violet": "#8b5cf6", "--pink": "#ec4899", "--cyan": "#22d3ee",
}

# 改造前 CSS 侧实际硬编码、本次被令牌化的色值（CT3 断言其绝迹）
LEGACY = ["#0c1020", "#0f1320", "#131a2e", "#161c2e", "#15203a", "#1c2740",
          "#1b2340", "#1b2742", "#2a3450", "#1c2336",
          "#e8ecf4", "#cfe0ff", "#cdd8ee", "#b9c6e0", "#9fc1ff", "#c7d2ea",
          "#e8f6ff", "#fff", "#9fb0d0", "#7c8aa8", "#9aa7b5",
          "#dbeafe", "#111",
          "#33406a", "#3a4a6e", "#1b2b4d", "#3f4f7a",
          "#6ea0ff", "#2f6fed", "#3b82f6", "#5b8cff", "#4f8cff",
          "#0a2540", "#0a66c2", "#0f172a",
          "#4ade80", "#10b981", "#67e0a3", "#bbf7d0", "#163a2a",
          "#f87171", "#ef4444", "#ffb4b4", "#f3b4b4", "#c9b6b6",
          "#3b1520", "#7f1d1d",
          "#fbbf24", "#f59e0b", "#fde68a", "#f5c45e",
          "#2b2313", "#3a2e16", "#3a2f10", "#7a5c14", "#cbd5e1"]

# 刻意保持硬编码的白名单（3 个）
#   #7c3aed   —— geo 紫色连线数据色，与地图 JS 绘制同源，无对应令牌
#   #5b8cff88 —— 带 alpha 后缀的 8 位色，var() 无法拼 alpha
#   #1e3a8a   —— dashboard header 品牌渐变终点（非纯色语义）
# 注：#8b5cf6 / #ec4899 / #22d3ee 原在此名单，本轮已升格为 --violet/--pink/--cyan 令牌。
KEEP = {"#7c3aed", "#5b8cff88", "#1e3a8a"}

# 词元级 hex 正则：8 位优先，其次 6 位，最后 3 位；右侧不得再跟 hex 字符
HEX_RE = re.compile(
    r"#[0-9a-fA-F]{8}(?![0-9a-fA-F])"
    r"|#[0-9a-fA-F]{6}(?![0-9a-fA-F])"
    r"|#[0-9a-fA-F]{3}(?![0-9a-fA-F])"
)

TOTAL_REPLACEMENTS = 348  # 见模块 docstring 的五段口径：270 + 22 + 18 + 5 + 33
#                          ↑ +33 = ③ 舆情展开面板新增的色值引用（分类胶囊 / 企业卡片 /
#                            来源链接）。新增样式必须继续走令牌：CT3 拒收未登记的裸
#                            hex，CT4 拒收自定义属性（故面板里没有 --tab-color 之类）。


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _ranges(path, src):
    """返回 (CSS 上下文区间, root 块区间)。

    CSS 上下文 = `<style>` 块 + DOM 内联 `style="..."` 属性（含 JS 拼出的 HTML 串）。
    后者同样会解析 `:root` 的 var()，属于本测试必须覆盖的范围；第一版只取了
    `<style>`，漏掉 14 处内联硬编码，补上。
    topnav.py 的 TOPNAV_CSS 整个字符串都是 CSS。
    """
    if path == "topnav.py":
        style = [(0, len(src))]
    else:
        style = [(m.start(1), m.end(1))
                 for m in re.finditer(r"<style[^>]*>(.*?)</style>", src, re.S)]
        style += [(m.start(1), m.end(1))
                  for m in re.finditer(r"""style\s*=\s*["']([^"']*)["']""", src)]
    root = [(m.start(), m.end()) for m in re.finditer(r":root\s*\{[^}]*\}", src, re.S)]
    return style, root


def _css_zone(path, src):
    """CSS 使用区（`<style>` 内 + 内联 style 属性，均排除 :root 定义）的文本。

    各区间在原文中互不相邻，拼接时必须插入分隔符，否则会伪造出跨区间的词元。
    实例（真实踩到）：区间 A 以 `…COLORS[` 结尾、区间 B 为 `background:#7c3aed`、
    区间 C 以 `background:…` 开头，直接拼成 `#7c3aedba` —— 一个不存在的 8 位色，
    导致白名单里的 `#7c3aed` 反而「扫不到」，测试报假失败。
    """
    style, root = _ranges(path, src)
    out = []
    for a, b in style:
        pos = a
        for ra, rb in root:
            if a <= ra < b:
                out.append(src[pos:ra])
                pos = rb
        out.append(src[pos:b])
    return "\n".join(out)


def _token_block(src):
    # 令牌名清单与 TOKENS 保持一致；长名优先，避免 line 抢先匹配掉 line-soft
    names = "|".join(sorted((n[2:] for n in TOKENS), key=len, reverse=True))
    pairs = re.findall(r"(--(?:%s)):\s*(#[0-9a-fA-F]{3,8})" % names, src)
    block = {k: v.lower() for k, v in pairs}
    return block


class ColorTokenDefinitions(unittest.TestCase):
    """CT1–CT2：五处 :root 令牌定义完整且一致。"""

    def test_ct1_blocks_identical(self):
        blocks = []
        for f in FILES:
            b = _token_block(_read(f))
            blocks.append(tuple(sorted(b.items())))
        self.assertEqual(len(set(blocks)), 1,
                         f"五处令牌块不一致，出现 {len(set(blocks))} 种定义")

    def test_ct2_all_tokens_defined(self):
        for f in FILES:
            with self.subTest(file=f):
                block = _token_block(_read(f))
                missing = {k: v for k, v in TOKENS.items() if block.get(k) != v}
                self.assertEqual(missing, {}, f"{f} 令牌缺失或值不符：{missing}")


class ColorTokenUsage(unittest.TestCase):
    """CT3–CT6：使用侧全部走 var()，数据侧保持硬编码。"""

    def _css_join(self):
        return "\n".join(_css_zone(f, _read(f)) for f in FILES)

    def test_ct3_legacy_colors_gone(self):
        # 词元级匹配：避免 #5b8cff88 被误判为残留的 #5b8cff
        css_tokens = {t.lower() for t in HEX_RE.findall(self._css_join())}
        left = sorted(css_tokens - KEEP)
        self.assertEqual(left, [], f"CSS 侧仍残留旧硬编码色值 {len(left)} 种：{left}")

    def test_ct4_only_defined_tokens(self):
        css = self._css_join()
        used = set(re.findall(r"var\(\s*(--[a-z0-9-]+)\s*\)", css))
        # 字号令牌由 test_ui_type_scale 负责，此处只校验色值令牌
        color_used = {u for u in used if not u.startswith("--fs-")}
        undef = color_used - set(TOKENS)
        self.assertEqual(undef, set(), f"引用了未定义的色值令牌：{sorted(undef)}")

    def test_ct3b_keep_list_intact(self):
        """刻意保留的 5 个硬编码仍在原位，且未被 var 化。"""
        css_tokens = {t.lower() for t in HEX_RE.findall(self._css_join())}
        missing = sorted(KEEP - css_tokens)
        # #1e3a8a 仅 dashboard 有、其余仅 index 有，逐文件校验更准
        self.assertEqual(missing, [], f"刻意保留的硬编码色值消失了：{missing}")

    def test_ct5_total_replacements(self):
        css = self._css_join()
        uses = re.findall(r"var\((--[a-z0-9-]+)\)", css)
        color_uses = [u for u in uses if u in TOKENS]
        self.assertEqual(len(color_uses), TOTAL_REPLACEMENTS,
                         f"色值 var() 引用数应恰为 {TOTAL_REPLACEMENTS}，实际 {len(color_uses)}")

    def test_ct7_canvas_reads_tokens(self):
        """画布节点色必须从 :root 读取，不得再写死字面量。

        演变过程：起初图例改成了 var(--green)，画布 COLORS.Supplier 却是 #10b981，
        而 --green 的值是 #4ade80 —— 两者当场分叉（本用例的前身 CT7 抓到的）。
        修法是让 src/engine/util.js 在模块加载时用 getComputedStyle 读令牌，
        于是 :root 成为唯一真源，图例与画布结构上不可能再漂移。
        本用例守住这个结构：画布侧不得再出现分类色的裸 hex。
        """
        util = _read("src/engine/util.js")
        render = _read("src/engine/render.js")

        # 1) util.js 必须走 getComputedStyle 读取，且声明了令牌映射
        self.assertIn("getComputedStyle", util,
                      "util.js 应通过 getComputedStyle 从 :root 读取节点色")
        self.assertIn("document.documentElement", util)

        # 2) 分类色不得再以裸 hex 出现在画布侧（回退值除外）
        banned = ["#2f6fed", "#f59e0b", "#10b981", "#8b5cf6", "#ec4899",
                  "#4ade80", "#fbbf24", "#22d3ee", "#ef4444", "#f87171"]
        # cssColors(令牌映射, 回退值) 的第二参数允许写裸 hex —— 那是无 DOM 时的兜底。
        # 扫描前先整块剔除，避免把合法回退值误判成硬编码。
        call = re.compile(r"cssColors\(\s*\{[^}]*\}\s*,\s*\{[^}]*\}\s*\)", re.S)
        for src, name in ((util, "util.js"), (render, "render.js")):
            # 剔除注释行：注释里会写回退值与说明，允许出现 hex
            code = "\n".join(ln for ln in src.splitlines()
                             if not ln.strip().startswith(("//", "*", "/*")))
            code = call.sub("/* cssColors(...) */", code)
            left = [h for h in banned if h in code]
            self.assertEqual(left, [],
                             f"{name} 仍含分类色裸 hex {left}，应改用令牌读取")

        # 3) 画布引用的令牌名必须都已定义（防拼错令牌名导致静默回退）
        block = set(TOKENS)
        used = set(re.findall(r'"(--[a-z0-9-]+)"', util))
        self.assertTrue(used, "util.js 中未找到任何令牌名引用")
        undef = used - block
        self.assertEqual(undef, set(), f"util.js 引用了未定义的令牌：{sorted(undef)}")

    def test_ct7b_palette_tokens_defined_everywhere(self):
        """画布要读的 5+2 个令牌，五个样式源的 :root 都必须定义，否则回退值会静默生效。"""
        need = {"--primary", "--warn", "--green", "--violet", "--pink", "--amber", "--cyan"}
        for f in FILES:
            with self.subTest(file=f):
                block = _token_block(_read(f))
                missing = sorted(need - set(block))
                self.assertEqual(missing, [], f"{f} 缺少画布所需令牌 {missing}")

    def test_ct8_muted_dim_contrast_on_popup(self):
        """geo 弹窗次要文字：#6b7280 → var(--muted-dim) 后对比度不得低于原值。"""
        def lum(h):
            r, g, b = (int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
            f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
            return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)

        def cr(a, b):
            la, lb = lum(a), lum(b)
            hi, lo = max(la, lb), min(la, lb)
            return (hi + 0.05) / (lo + 0.05)

        old = cr("#6b7280", "#1b2340")   # 原值 vs geo 弹窗底色（--soft）
        new = cr(TOKENS["--muted-dim"], "#1b2340")
        self.assertGreaterEqual(new, 3.0,
                                f"var(--muted-dim) 在 --soft 上对比度仅 {new:.2f}:1")
        self.assertGreaterEqual(new, old - 0.05,
                                f"令牌化后对比度下降过多：{old:.2f} → {new:.2f}")

    def test_ct6_data_side_untouched(self):
        geo = _read("tools/geo_build.py")
        # JS __HEX 字典与 Python COLORS / marker SVG 必须保持硬编码
        self.assertIn("const __HEX = {{", geo)
        hex_line = re.search(r"const __HEX = \{{[^}}]*\}}", geo).group(0)
        self.assertNotIn("var(--", hex_line, "JS 数据字典被误改成了 var()，运行时会失效")
        self.assertIn("fill='#cbd5e1'", geo, "marker SVG 的图形色应保持硬编码")
        # Python 代码区（非 <style>）不应出现 var(
        style = [(m.start(1), m.end(1)) for m in re.finditer(r"<style[^>]*>(.*?)</style>", geo, re.S)]
        outside = "".join(geo[b:a] for (a, b) in
                          zip([0] + [e for _, e in style], [s for s, _ in style] + [len(geo)]))
        self.assertNotIn("var(--", outside, "Python 代码区不应出现 CSS var()")


if __name__ == "__main__":
    unittest.main(verbosity=2)
