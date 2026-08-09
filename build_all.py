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
# build_viewer 的「风险视图」依赖 run_risk 产出的 tools/output/supply_chain_risk.json，
# 故 run_analysis / run_risk 必须排在各自依赖它们的页面脚本之前；其余页面脚本互不依赖。
STEPS = [
    ("供应商估值  supplier_analysis.json",  "tools/run_analysis.py"),
    ("供应链风险  supply_chain_risk.json",  "tools/run_risk.py"),
    ("供应链图谱  index.html（首页）",      "scripts/build_viewer.py"),
    ("企业列表    supplier_table.html",     "scripts/build_table.py"),
    ("上下游报告  apple_supply_chain_report.html", "scripts/report.py"),
    ("供应商地图  supplier_geo.html",       "tools/geo_build.py"),
    ("估值看板    supplier_dashboard.html", "tools/build_dashboard.py"),
]


def load_local_env():
    """读取仓库根目录的 .env（若存在），把 KEY=VALUE 写入 os.environ（仅当该键尚未设置）。

    零三方依赖；用于本地 / CI 把 ANALYTICS_* 等配置注入构建环境。解析规则：
    忽略空行与 # 注释行，跳过不含 "=" 的行，值首尾的引号会被剥除。找不到文件或任何
    单行出错都不会中断构建。子进程会继承 os.environ，故所有页面脚本都能读到这些变量。
    """
    env_path = os.path.join(ROOT, ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key, val = key.strip(), val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val


def main():
    load_local_env()  # 必须在构建子进程启动前完成，使其继承 ANALYTICS_* 等环境变量
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
