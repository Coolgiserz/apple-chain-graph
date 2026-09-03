# -*- coding: utf-8 -*-
"""字号收敛 + 令牌化（P2-3）测试设计文档。

背景
----
UI 审查报告 P2-3：全站字号共 18 档 / 137 处声明（index.html 独占 93 处），
同语义元素跨页字号不一致（如「小注」在 index 是 11.5px、dashboard 是 11.5px、
geo 是 11px；「正文」在 index 是 12.5/13px、table 是 13px、dashboard 是 12.3px）。
本次收敛为 7 档并令牌化。

档位映射（就近归并，绝大多数单处变动 ≤1px）
-------------------------------------------
--fs-xs      11px  ← 10 / 11 / 11.5    小注、表头、图例、徽标
--fs-sm      12px  ← 12 / 12.3         次要信息、label
--fs-base    13px  ← 12.5 / 13 / 13.5  正文、控件、表格
--fs-md      14px  ← 14 / 15           小标题、品牌名
--fs-lg      16px  ← 16 / 17           面板/分节标题
--fs-xl      18px  ← 18 / 19 / 20       关闭按钮、汉堡、卡片数值、页 h1
--fs-display 24px  ← 23 / 27           展示级（dashboard 主标题/卡片大数字）

令牌放置策略（重要设计决策）
----------------------------
index.html 内联了一份 topnav CSS 副本（无 __TOPNAV_CSS__ 注入占位符），
而 table/dashboard/geo 经 topnav.py 注入；且各产物层级不同（根目录 / dist/ /
tools/visualizations/），GitHub Pages 又是子路径部署 —— 独立 tokens.css 的
相对或绝对路径都不通用。因此采用「各文件 :root 各自定义 + 测试锁死 5 处
令牌块完全一致」的务实方案：语义单点由 TS2 保证，物理多份由测试兜底。

测试用例设计（TS1–TS6）
------------------------
TS1 五个样式源（index / table / dashboard / geo / topnav）的 :root 均定义了
    7 个 --fs-* 令牌且值正确。
TS2 五个文件的字号令牌块（按出现顺序拼接）完全一致 —— 防止某页漏同步。
TS3 全站 font-size 不再出现裸 px 值（:root 定义本身不含 font-size，故可全局断言）。
TS4 var(--fs-*) 使用总数恰为 138（改造前 137；as_of 透传为看板新增
    元信息行 header .meta 用 var(--fs-sm)，属合法新增，快照随之上调），
    防止漏改 / 多改。
TS5 旧档位值（10/11.5/12.3/12.5/12.8/13.5/15/17/19/20/23/27）在 font-size
    声明中彻底绝迹。
TS6 实际引用的令牌集合 ⊆ 七个令牌名，防止引用未定义令牌（如 var(--fs-xxl)）。

注：geo_build.py 的 HTML 为 f-string 内联模板，源码中 CSS 花括号写作 {{ }}；
本测试按源文件字面内容正则匹配。构建产物由 build_all 之后抽查验证。
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

SCALE = {
    "--fs-xs": "11px",
    "--fs-sm": "12px",
    "--fs-base": "13px",
    "--fs-md": "14px",
    "--fs-lg": "16px",
    "--fs-xl": "18px",
    "--fs-display": "24px",
}

LEGACY_SIZES = {"10", "11.5", "12.3", "12.5", "12.8", "13.5",
                "15", "17", "19", "20", "23", "27"}

TOTAL_DECLARATIONS = 149  # 改造前 137 处；+1 = as_of 透传新增的看板元信息行（header .meta，var(--fs-sm)）
#                          ↑ +11 = ③ 舆情展开面板（胶囊按钮 var(--fs-base/sm)、面板标题
#                            var(--fs-md)、企业名 var(--fs-md)、徽标 var(--fs-xs)、
#                            定义列表与来源链接 var(--fs-base)、来源元信息 var(--fs-sm)）


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _fs_block(src):
    """按出现顺序提取 --fs-* 定义，返回 (拼接字符串, {令牌: 值})。"""
    pairs = re.findall(r"(--fs-[a-z]+):\s*([\d.]+px)", src)
    return ";".join(f"{k}:{v}" for k, v in pairs), dict(pairs)


class TypeScaleTokens(unittest.TestCase):
    """TS1–TS2：五处 :root 令牌定义完整且彼此一致。"""

    def test_ts1_all_files_define_scale(self):
        for f in FILES:
            with self.subTest(file=f):
                block, mapping = _fs_block(_read(f))
                self.assertEqual(mapping, SCALE,
                                 f"{f} 的 --fs-* 令牌定义不完整或值不符：{block or '（未定义）'}")

    def test_ts2_blocks_identical(self):
        blocks = {f: _fs_block(_read(f))[0] for f in FILES}
        unique = set(blocks.values())
        self.assertEqual(len(unique), 1,
                         f"五处令牌块不一致，出现 {len(unique)} 种：{unique}")


class TypeScaleUsage(unittest.TestCase):
    """TS3–TS6：使用侧全部走 var()，无裸 px、无旧档位、无未定义令牌。"""

    def _all_sources(self):
        return "".join(_read(f) for f in FILES)

    def test_ts3_no_bare_px(self):
        joined = self._all_sources()
        bare = re.findall(r"font-size:\s*[\d.]+px", joined)
        self.assertEqual(bare, [], f"仍存在裸 px 字号声明 {len(bare)} 处：{bare[:5]}")

    def test_ts4_total_declarations(self):
        joined = self._all_sources()
        uses = re.findall(r"font-size:\s*var\(--fs-[a-z]+\)", joined)
        self.assertEqual(len(uses), TOTAL_DECLARATIONS,
                         f"var(--fs-*) 引用数应恰为 {TOTAL_DECLARATIONS}（改造前声明数），实际 {len(uses)}")

    def test_ts5_legacy_sizes_gone(self):
        joined = self._all_sources()
        for m in re.finditer(r"font-size:\s*([\d.]+)px", joined):
            self.assertNotIn(m.group(1), LEGACY_SIZES,
                             f"旧档位 {m.group(1)}px 仍出现在 font-size 声明中")
        # 兜底：旧档位的裸声明形式（含 inline style）绝迹
        for legacy in LEGACY_SIZES:
            self.assertNotIn(f"font-size:{legacy}px", joined.replace(" ", ""),
                             f"旧档位 {legacy}px 仍有裸声明")

    def test_ts6_only_defined_tokens(self):
        joined = self._all_sources()
        used = set(re.findall(r"var\((--fs-[a-z]+)\)", joined))
        self.assertTrue(used <= set(SCALE),
                        f"引用了未定义令牌：{used - set(SCALE)}")
        self.assertEqual(len(used), len(SCALE),
                         f"七个令牌应全部被用到，实际用到 {sorted(used)}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
