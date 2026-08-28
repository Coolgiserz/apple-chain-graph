# -*- coding: utf-8 -*-
"""
Geo 双源漂移审计：比对 data/production_bases.draft.json 与 data/geo_hubs.json

问题背景：tools/geo_build.py 的地图坐标（组装厂 hub + 终端市场）此前硬编码在脚本里，
与 data/production_bases.draft.json（组装基地研究草案）构成「双源」。本脚本在 CI / 本地
校验两者在「重叠 operator + 城市」上的坐标是否一致，避免两处各自改、彼此漂移。

判定规则：
- 仅当 (operator, city) 同时出现在 geo_hubs 与 draft（重叠子集）时，要求坐标一致（容差 0.01°）。
- operator 命中 hub 但城市不同（如 draft 列出该 operator 的其它城市基地）仅作信息提示，不算漂移。
- draft 缺少 coordinates 字段时视为漂移（应当补全）。

退出码：发现坐标冲突返回 1，否则 0。
"""
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HUBS = os.path.join(REPO, "data", "geo_hubs.json")
DRAFT = os.path.join(REPO, "data", "production_bases.draft.json")
TOL = 0.01  # 度


def main():
    hubs = json.load(open(HUBS, encoding="utf-8"))
    draft = json.load(open(DRAFT, encoding="utf-8"))
    asm = hubs["assembly_hubs"]  # operator -> {city, region, lng, lat}

    # hub 坐标按 (operator, city) 建索引
    hub_keys = {(op, h["city"]): (h["lng"], h["lat"]) for op, h in asm.items()}

    conflicts = 0
    checked = 0
    for b in draft["production_bases"]:
        op = b.get("operator")
        city = b.get("city", "")
        coord = b.get("coordinates")
        if op not in asm:
            continue  # draft 专有的 operator（如 apple）不参与 hub 比对
        if coord is None:
            print(f"[DRIFT] {b['id']} (operator={op}, city={city}) 缺少 coordinates 字段")
            conflicts += 1
            continue
        key = (op, city)
        if key in hub_keys:
            checked += 1
            hlng, hlat = hub_keys[key]
            if abs(coord["lng"] - hlng) > TOL or abs(coord["lat"] - hlat) > TOL:
                print(f"[CONFLICT] {b['id']} (operator={op}, city={city}) "
                      f"draft=({coord['lng']},{coord['lat']}) hub=({hlng},{hlat})")
                conflicts += 1
        else:
            print(f"[INFO] {b['id']} (operator={op}, city={city}) 与 hub 主基地城市不同，属补充基地")

    print(f"\n重叠子集比对：{checked} 处坐标逐一核对，{conflicts} 处冲突/缺失。")
    if conflicts:
        print("结论：存在双源漂移，请同步 data/geo_hubs.json 与 draft 的坐标。")
        sys.exit(1)
    print("结论：重叠子集坐标一致，无漂移。")
    sys.exit(0)


if __name__ == "__main__":
    main()
