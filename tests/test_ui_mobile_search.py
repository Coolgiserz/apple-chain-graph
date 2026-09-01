"""移动端搜索框可用性守卫（tests/test_ui_mobile_search.py）

测试设计文档
============

缺陷描述
--------
移动端（≤860px）控制栏默认只显示汉堡按钮，点开才展开全部控件。展开后，页面上有
一个「点击控件后自动收起」的处理器，意图是：点按钮/复选框这类「点完即生效」的控件
后收起控制栏，避免它遮挡图谱。

但该处理器把所有位于 ``.top-controls`` 内的点击一视同仁，**搜索框 ``#q`` 和下拉
选择器也在其中**。于是在手机上：

    点汉堡 → 控制栏展开 → 点搜索框 → click 事件触发收起
    → ``.top-controls { display: none }`` → 输入框连同焦点一起被抹掉
    → 软键盘收起、无法输入

结果是**移动端搜索功能完全不可用**——不是体验问题，是功能丧失。

正确行为
--------
按控件「点完之后还要不要继续用」来分：

- **需保持展开**：文本输入类（唤起软键盘）与 ``<select>``（弹原生选择器）。
  点在它们上面时收起，等于把用户正在用的控件抽走。
- **应自动收起**：``button`` / ``a.tlink`` / ``input[type=checkbox]``。
  点完即生效，收起反而能立刻看到图谱变化。

本文件锁住的三件事
------------------
1. **M3（语义覆盖，核心）**：从 ``.top-controls`` 里**实际解析**出所有控件，凡属
   「需保持展开」类别的，都必须被源码里的 ``KEEP_OPEN`` 选择器命中。
   这是最有价值的一条——将来谁往工具栏加一个新输入框/下拉框，测试会立刻提醒他
   补进豁免名单，而不是等用户在手机上发现又搜不了。
2. **M2（源码契约）**：收起处理器里 ``KEEP_OPEN`` 的豁免判断必须**早于**
   ``classList.remove("top-expanded")`` 并提前 ``return``。顺序写反等于没写。
3. **M4（反向）**：``KEEP_OPEN`` 不得把 button / 链接 / 复选框也豁免掉——
   只修 bug 而把「点完自动收起」整个废掉，是另一种回归。

外加 M5：JS 注释里的断点数值必须与 CSS 媒体查询一致（当前注释写 820px、CSS 是
860px——上一轮断点收敛后漏改的说明文字）。

为什么是静态分析而不是跑真浏览器
--------------------------------
这段逻辑是 index.html 里的内联脚本，且强依赖真实布局与触摸事件；仓库既有的
JS 测试（tests/engine.test.mjs）也只覆盖 src/ 下的模块。用静态解析锁住
「选择器覆盖关系」这一决策，比搭一套 DOM 模拟更稳、更贴近要防的回归。
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"

# 「点完即生效」的控件——点它们应该保持原有的自动收起行为
CLICK_AND_DONE_INPUT_TYPES = {"checkbox", "radio", "button", "submit", "reset", "hidden"}

CTRL_TAG = re.compile(r"<(input|select|textarea)\b([^>]*)>", re.I)
KEEP_OPEN_DECL = re.compile(r'var\s+KEEP_OPEN\s*=\s*"([^"]+)"')


def _read():
    return INDEX.read_text(encoding="utf-8")


def _balanced(src, start, open_ch="{", close_ch="}"):
    """从 start 处（已跳过开头的 `{`）做括号配对，返回块内容。"""
    pattern = "[" + re.escape(open_ch) + re.escape(close_ch) + "]"
    depth = 1
    for m in re.finditer(pattern, src[start:]):
        depth += 1 if m.group(0) == open_ch else -1
        if depth == 0:
            return src[start:start + m.start()]
    raise AssertionError("括号未闭合，无法解析代码块")


def _top_controls(src):
    """取出 <div class="top-controls"> 的内部 HTML（按 div 深度配对，不用脆弱的行号）。"""
    m = re.search(r'<div class="top-controls"[^>]*>', src)
    assert m, "index.html 中未找到 .top-controls 容器"
    i, depth = m.end(), 1
    for mm in re.finditer(r"<(/?)div\b", src[i:]):
        depth += -1 if mm.group(1) else 1
        if depth == 0:
            return src[i:i + mm.start()]
    raise AssertionError(".top-controls 的 div 未闭合，无法解析工具栏控件")


def _controls(inner):
    """解析出工具栏内所有 input / select / textarea，返回 [(tag, type, attrs)]。"""
    out = []
    for tag, attrs in CTRL_TAG.findall(inner):
        am = re.search(r"""type\s*=\s*["']?([^"'\s>]+)""", attrs, re.I)
        out.append((tag.lower(), (am.group(1).lower() if am else ""), attrs))
    return out


def _required_token(tag, typ):
    """该控件要「保持展开」，KEEP_OPEN 里必须包含哪个选择器片段。

    返回 None 表示它属于「点完即生效」，应当照旧自动收起。
    """
    if tag == "select":
        return "select"
    if tag == "textarea":
        return "textarea"
    if tag == "input":
        if typ in CLICK_AND_DONE_INPUT_TYPES:
            return None
        if typ == "search":
            return "input[type=search]"
        if typ == "text":
            return "input[type=text]"
        if typ == "":
            return "input:not([type])"
        return "input[type=%s]" % typ
    return None


def _collapse_handler(src):
    """取出 bar 上那个 click 处理器的函数体。"""
    m = re.search(r'bar\.addEventListener\(\s*"click"\s*,\s*function\s*\([^)]*\)\s*\{', src)
    assert m, "未找到控制栏的 click 收起处理器（结构变了？）"
    return _balanced(src, m.end())


def _css_breakpoint(src):
    """找到隐藏 .top-controls 的那个 @media 断点值。"""
    for m in re.finditer(r"@media\s*\(max-width:\s*(\d+)px\)\s*\{", src):
        block = _balanced(src, m.end())
        if re.search(r"\.top-controls\s*\{\s*display:\s*none", block):
            return int(m.group(1))
    raise AssertionError("未找到隐藏 .top-controls 的 @media (max-width: …) 断点")


def _js_comment_breakpoint(src):
    """从「移动端控制栏折叠」那段注释里取出它声称的断点值。"""
    # 逐条遍历注释再筛选。两个坑都踩过：
    # ① 直接写 /\*.*?控制栏折叠.*?\*/ 会从文件里第一个 /* 一路吞到目标注释，
    #    把整个 <style> 块当成一条注释匹配进来；
    # ② 只筛「控制栏折叠」会先命中 @media 里那条 CSS 注释（它不含断点数值）。
    #    故再加 topToggle 锁定 JS 那段——CSS 注释不会提到这个按钮。
    m = None
    for cand in re.finditer(r"/\*.*?\*/", src, re.S):
        if "控制栏折叠" in cand.group(0) and "topToggle" in cand.group(0):
            m = cand
            break
    assert m, "未找到控制栏折叠 JS 的说明注释"
    nums = re.findall(r"(\d+)px", m.group(0))
    assert len(nums) == 1, "注释里的 px 数值应恰好一个，实际：%r" % nums
    return int(nums[0])


class MobileToolbarCollapse(unittest.TestCase):
    """移动端控制栏：「点完即生效」的收起，输入类控件保持展开。"""

    def test_m1_search_input_lives_inside_top_controls(self):
        """M1：搜索框确实在 .top-controls 内——这正是它会被收起逻辑误伤的原因。"""
        inner = _top_controls(_read())
        hits = [c for c in _controls(inner) if c[0] == "input" and c[1] == "search"]
        self.assertEqual(len(hits), 1,
                         "预期 .top-controls 内恰好一个 input[type=search]，实际 %d 个" % len(hits))
        self.assertIn('id="q"', hits[0][2], "搜索框应仍是 #q")

    def test_m2_handler_exempts_keep_open_before_collapsing(self):
        """M2：豁免判断必须早于收起动作并提前 return（顺序写反等于没写）。"""
        src = _read()
        self.assertRegex(src, KEEP_OPEN_DECL, "源码中应声明 KEEP_OPEN 豁免选择器")

        body = _collapse_handler(src)
        guard = re.search(r"KEEP_OPEN\s*\)\s*\)?\s*return", body)
        remove = re.search(r'classList\.remove\(\s*"top-expanded"\s*\)', body)
        self.assertTrue(remove, "收起处理器里应有移除 top-expanded 的动作")
        self.assertTrue(guard, "收起处理器应在移除 top-expanded 之前对 KEEP_OPEN 控件 return")
        self.assertLess(guard.start(), remove.start(),
                        "KEEP_OPEN 豁免必须出现在 classList.remove 之前")

    def test_m3_every_input_like_control_is_exempted(self):
        """M3（核心）：工具栏里所有「还要继续用」的控件都必须被 KEEP_OPEN 覆盖。

        将来新增输入框/下拉框却忘记补豁免名单时，这条会先红。
        """
        src = _read()
        m = KEEP_OPEN_DECL.search(src)
        self.assertTrue(m, "源码中应声明 KEEP_OPEN 豁免选择器")
        selector = m.group(1)

        missing = []
        for tag, typ, attrs in _controls(_top_controls(src)):
            token = _required_token(tag, typ)
            if token and token not in selector:
                missing.append("<%s%s> → 需要 %r" % (
                    tag, (' type=' + typ) if typ else '', token))

        self.assertEqual(
            missing, [],
            "以下控件点了还要继续用（唤起键盘/原生选择器），收起会让它们连同焦点消失，"
            "但未登记进 KEEP_OPEN（当前为 %r）：\n  " % selector + "\n  ".join(missing))

    def test_m4_click_and_done_controls_still_collapse(self):
        """M4（反向）：按钮/链接/复选框仍需自动收起——别把功能整个废掉。"""
        src = _read()
        m = KEEP_OPEN_DECL.search(src)
        self.assertTrue(m, "源码中应声明 KEEP_OPEN 豁免选择器")
        # 按逗号拆成独立选择器片段再判定。整串做子串匹配会误伤：
        # 裸 "a" 会被 search / textarea 里的字母命中。
        tokens = [t.strip() for t in m.group(1).split(",") if t.strip()]
        self.assertTrue(tokens, "KEEP_OPEN 选择器为空")
        for t in tokens:
            for banned in ("button", "checkbox", "radio"):
                self.assertNotIn(banned, t,
                                 "KEEP_OPEN 的片段 %r 不应豁免 %r——它属于「点完即生效」，"
                                 "照旧该自动收起" % (t, banned))
            self.assertNotRegex(t, r"^a\b",
                                "KEEP_OPEN 的片段 %r 不应豁免链接 <a>，"
                                "否则「点击后自动收起」就失效了" % t)

    def test_m5_comment_breakpoint_matches_css(self):
        """M5：JS 注释声称的断点必须与 CSS 媒体查询一致（避免说明文字误导）。"""
        src = _read()
        self.assertEqual(
            _js_comment_breakpoint(src), _css_breakpoint(src),
            "控制栏折叠注释里的断点与 CSS @media 断点不一致——断点收敛后说明文字没跟着改")


if __name__ == "__main__":
    unittest.main()
