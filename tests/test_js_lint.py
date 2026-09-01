"""JS 静态检查门禁（tests/test_js_lint.py）

测试设计文档
============

背景（真实事故）
---------------
色值令牌化那一轮（P1-6）让 ``src/engine/util.js`` 在模块加载时用
``getComputedStyle`` 从 ``:root`` 读取节点配色，使图例与画布同源。本地
``python -m unittest`` 51/51 全绿、build_all 通过、产物抽查也全过——但 CI
的 ``npm run lint`` 步骤挂了::

    src/engine/util.js
      16:13  error  'getComputedStyle' is not defined  no-undef

根因是本项目的 ESLint 采用**手写浏览器全局白名单**（``eslint.config.js`` 的
``browserGlobals``，未启用 ``env: browser``），``getComputedStyle`` 不在名单里。
这个约束并非没人知道——``src/engine/panels.js`` 早在注释里记录过，当初为了绕开它
才改用 ``offsetParent`` 判可见性。

事故暴露的结构性问题：**Python 与 JS 两套门禁互不可见**。Python 全绿并不代表
CI 会通过，本地缺少一个能覆盖 JS lint 的单一入口。

本文件要防的两类回归
--------------------
1. **L1（主闸门）**：``src/`` 下任何 ESLint 报错（当前只有 ``no-undef`` 一条规则，
   但未来加规则同样被此闸门覆盖）。直接执行仓库内的 eslint 二进制，与 CI 的
   ``npm run lint`` 完全同参（``eslint src``），不存在「本地写的规则与 CI 不一致」。
2. **L2（契约锁）**：白名单与源码用法的契约。白名单是手写的，删掉一项不会有任何
   告警，直到 CI 变红。此用例反向锁住：源码里以**裸标识符**形式出现的 DOM API，
   必须在 ``browserGlobals`` 中登记。

关于 L2 的「裸标识符」
----------------------
``window.getComputedStyle(...)`` 这种成员访问不会触发 ``no-undef``（``window``
已在白名单内），因此**不在**检查范围内，不算违规。只有写成裸的
``getComputedStyle(...)`` 才需要登记。正则用 ``(?<![\\w.])`` 排除 ``foo.bar`` /
``window.bar`` 形式。

设计取舍
--------
- **为什么不把规则抄进 Python？** 重实现 ESLint 的变量作用域分析既脆弱又必然
  落后于真实规则。直接调用真身，零漂移。
- **环境缺失怎么办？** 无 node 或 ``node_modules`` 未安装时 ``skipTest`` 而非失败。
  这是刻意的：本机没装前端依赖不该让 Python 测试变红，但代价是「静默跳过」，
  因此 L2 这条**不依赖 node** 的用例必须存在，保证最坏情况下仍有一层保护。
- **WATCH 清单需要人工维护**：只列「容易忘记登记」的 DOM API。它不追求穷尽——
  穷尽是 L1 的职责；L2 只是白名单被改坏时的兜底警报。

验证方式
--------
::

    python -m unittest tests.test_js_lint -v          # 正常
    # 制造红灯：从 eslint.config.js 删掉 getComputedStyle 一行，重跑应失败
    node node_modules/eslint/bin/eslint.js src        # L1 复现命令
"""

import os
import re
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
ESLINT_CONFIG = ROOT / "eslint.config.js"
ESLINT_BIN = ROOT / "node_modules" / "eslint" / "bin" / "eslint.js"

# 容易忘记在 browserGlobals 里登记的 DOM / BOM API。
# 只用于 L2 兜底，不必穷尽；新增 DOM API 用法时顺手补进这里即可。
WATCH = [
    "getComputedStyle", "matchMedia", "getSelection", "scrollTo",
    "requestAnimationFrame", "cancelAnimationFrame",
    "addEventListener", "removeEventListener", "dispatchEvent",
    "Element", "HTMLElement", "Node", "Event", "CustomEvent",
    "MouseEvent", "KeyboardEvent", "TouchEvent", "FocusEvent", "WheelEvent",
    "DOMParser", "Image", "SVGElement", "IntersectionObserver",
    "ResizeObserver", "MutationObserver",
]


def _browser_globals():
    """从 eslint.config.js 解析手写的 browserGlobals 键名集合。

    只解析 ``const browserGlobals = { ... }`` 这一段，避免把配置里其它
    对象字面量的键误收进来。
    """
    text = ESLINT_CONFIG.read_text(encoding="utf-8")
    m = re.search(r"const\s+browserGlobals\s*=\s*\{(.*?)\n\};", text, re.S)
    if not m:
        return set()
    return set(re.findall(r"^\s*['\"]?([A-Za-z_$][\w$]*)['\"]?\s*:", m.group(1), re.M))


def _src_files():
    return sorted(p for p in SRC.rglob("*.js") if p.is_file())


class JsLintGate(unittest.TestCase):
    """把 JS 静态检查纳入 Python 单测，避免「本地全绿、CI 变红」。"""

    def test_l1_eslint_clean(self):
        """L1：ESLint 对 src/ 的扫描必须零报错（与 CI 的 npm run lint 同参）。"""
        node = shutil.which("node")
        if not node:
            self.skipTest("未找到 node，跳过 ESLint 执行")
        if not ESLINT_BIN.is_file():
            self.skipTest("node_modules/eslint 未安装，请先 npm ci")

        proc = subprocess.run(
            [node, str(ESLINT_BIN), "src"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=180,
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(
            proc.returncode, 0,
            "ESLint 扫描 src/ 未通过（等价于 CI 的 npm run lint 会失败）：\n" + output,
        )

    def test_l2_bare_dom_globals_are_declared(self):
        """L2：源码里裸调用的 DOM API，必须在 eslint.config.js 的白名单里登记。

        不依赖 node，是 node 缺失时的最后一层保护。
        """
        self.assertTrue(ESLINT_CONFIG.is_file(), "缺少 eslint.config.js")
        declared = _browser_globals()
        self.assertTrue(declared, "未能从 eslint.config.js 解析出 browserGlobals")

        # 按长度倒序拼接，避免 `Event` 抢先匹配掉 `CustomEvent` 之类。
        alt = "|".join(re.escape(w) for w in sorted(WATCH, key=len, reverse=True))
        # (?<![\w.]) —— 排除 window.foo / obj.foo 这类成员访问（不触发 no-undef）
        pattern = re.compile(r"(?<![\w.])(" + alt + r")\b")

        violations = {}
        for path in _src_files():
            code = path.read_text(encoding="utf-8")
            # 剥掉注释再扫，避免把说明文字里的 API 名当成真实用法
            code = re.sub(r"/\*.*?\*/", "", code, flags=re.S)
            code = re.sub(r"(?m)//.*$", "", code)
            for name in sorted(set(pattern.findall(code))):
                if name not in declared:
                    rel = os.path.relpath(path, ROOT)
                    violations.setdefault(name, []).append(rel)

        self.assertEqual(
            violations, {},
            "以下 DOM API 以裸标识符形式使用，但未登记进 eslint.config.js 的 "
            "browserGlobals（会触发 no-undef）。请登记该全局，或改写为 window.xxx 成员访问：\n"
            + "\n".join("  - %s → %s" % (k, ", ".join(v)) for k, v in sorted(violations.items())),
        )

    def test_l2_watch_list_covers_known_usage(self):
        """L2 自检：白名单里已登记的 WATCH 项，源码中确实有人在用。

        防止 WATCH 清单与 browserGlobals 各说各话、配置漂移后无人察觉。
        """
        declared = _browser_globals()
        used = set()
        for path in _src_files():
            code = path.read_text(encoding="utf-8")
            for w in WATCH:
                if re.search(r"(?<![\w.])" + re.escape(w) + r"\b", code):
                    used.add(w)

        # 只对「既在 WATCH 又已登记」的项做正向断言：它们应当真的出现在源码里
        both = used & {w for w in WATCH if w in declared}
        self.assertTrue(
            both,
            "WATCH 清单与源码用法已脱节：白名单登记了 %s，但 src/ 里一个都没用到。"
            "请同步更新 tests/test_js_lint.py 的 WATCH 或清理白名单。"
            % sorted(w for w in WATCH if w in declared),
        )


if __name__ == "__main__":
    unittest.main()
