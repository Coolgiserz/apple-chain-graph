#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""统一构建入口：一条命令重生成全部页面。

用法：
    python3 build_all.py            # 用当前解释器构建（推荐仓库自带的 Python 3.13）
    python3 build_all.py --check    # 仅做语法检查，不写文件

各生成脚本使用同一个解释器（sys.executable）以 subprocess 调用，确保与
build_all.py 自身运行环境一致；任一脚本失败则立即中止（exit code 1）。
"""
import os
import sys
import subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))

# (步骤名, 脚本相对仓库根的路径)
# 注意顺序有依赖：geo_build 依赖 run_analysis 产出的 tools/output/supplier_analysis.json，
# 故 run_analysis 必须排在 geo_build 之前；其余页面脚本互不依赖，可按页面逻辑排列。
STEPS = [
    ("供应链图谱  index.html（首页）",      "scripts/build_viewer.py"),
    ("企业列表    supplier_table.html",     "scripts/build_table.py"),
    ("上下游报告  apple_supply_chain_report.html", "scripts/report.py"),
    ("供应商估值  supplier_analysis.json",  "tools/run_analysis.py"),
    ("供应商地图  supplier_geo.html",       "tools/geo_build.py"),
]


def main():
    check_only = "--check" in sys.argv[1:]
    for name, rel in STEPS:
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            print("✗ 缺少脚本：%s" % path, file=sys.stderr)
            sys.exit(1)
        if check_only:
            cmd = [sys.executable, "-m", "py_compile", path]
            tag = "check"
        else:
            cmd = [sys.executable, path]
            tag = "build"
        print("[%s] %s  ->  %s" % (tag, name, rel))
        rc = subprocess.run(cmd, cwd=ROOT).returncode
        if rc != 0:
            print("✗ 失败（exit %d）：%s" % (rc, rel), file=sys.stderr)
            sys.exit(rc)
    if check_only:
        print("\n✓ 全部脚本语法检查通过。")
    else:
        print("\n✓ 全部页面构建完成。产物在 dist/ 与 tools/visualizations/ 下。")


if __name__ == "__main__":
    main()
