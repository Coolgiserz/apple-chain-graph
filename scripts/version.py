#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""version.py —— 根据 git 元数据派生构建版本号（流派 B：最近 tag + commit 距离 + sha）。

业界把"根据 commit 自动计算版本号"分为两派：
  - 流派 A（Conventional Commits）：解析 commit message 推导语义版本（release-please / semantic-release）。
  - 流派 B（git 图元数据）：取最近版本 tag → 数距它的 commit 数 → 拼当前 sha（setuptools-scm / GitVersion）。
本脚本实现流派 B，作为所有"构建戳"的单一事实来源：
  - 资产缓存戳已由 build_viewer.asset_url() 走内容哈希自动处理；
  - 本脚本输出用于 feeds 信封 meta.build 与部署清单 build.json 的"构建版本"，
    它随每次提交唯一、可溯源到 git sha，且内容不变则戳不变（缓存友好）。

输出形如：
  v1.3.0              # 恰好在某个 tag 上
  v1.3.0-5-gabcdef0   # 距 tag 5 个 commit（5 = commit 距离，abcdef0 = 短 sha）
  v1.3.0-5-gabcdef0-dirty  # 工作区存在未提交改动

回退链：git describe 失败 → 环境变量 BUILD_VERSION → "0.0.0-unknown"。

用法：
  python3 scripts/version.py            # 仅打印构建版本（BUILD_VERSION）
  python3 scripts/version.py --date     # 仅打印构建时间（UTC，BUILD_DATE）
  python3 scripts/version.py --json     # 打印 {"version": ..., "date": ...}
"""
import os
import subprocess
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def git_describe():
    """调用 git describe 派生版本；无 tag / 非 git 仓库时返回 None。"""
    try:
        out = subprocess.check_output(
            ["git", "-C", ROOT, "describe", "--tags", "--dirty",
             "--always", "--match", "v[0-9]*"],
            stderr=subprocess.DEVNULL,
        ).decode().strip()
        return out or None
    except Exception:
        return None


def compute():
    """派生构建版本号，带回退链。"""
    v = git_describe()
    if not v:
        v = os.environ.get("BUILD_VERSION") or "0.0.0-unknown"
    return v


def build_date():
    """当前 UTC 时间，ISO-8601。"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main():
    if "--date" in sys.argv:
        print(build_date())
        return
    if "--json" in sys.argv:
        print('{"version": "%s", "date": "%s"}' % (compute(), build_date()))
        return
    print(compute())


if __name__ == "__main__":
    main()
