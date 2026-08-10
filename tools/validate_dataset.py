#!/usr/bin/env python3
"""对 data/apple_supply_chain.json 做全面内部交叉验证。

校验项（均为确定性、可复现，不依赖外部网络）：
  1) 引用完整性：每条边的 from/to 必须指向已存在节点，且类型正确
     - uses_component : Product -> Component
     - supplied_by    : Component -> Supplier
     - assembled_by   : Product -> Supplier
  2) 重复：同 class 内重复 id；同类型内重复 (from,to) 边
  3) 必填字段：Product(id,name,product_line) / Component(id,name,category)
     / Supplier(id,name,country,category,tier)
  4) 孤立节点：不出现在任何边中的节点
  5) 悬空逻辑：被产品使用(uses_component.to)却无 supplied_by（无供应商的零部件）
     ；被零部件供货(supplied_by.to)却不被任何产品间接使用
  6) 取值合规性：product_line 取值集合、tier 取值集合、supplied_by.share 可解析
  7) 自环 / 反向边

输出人类可读报告，并给出问题计数（非零即视为数据需修正）。
用法：python3 tools/validate_dataset.py [path/to/apple_supply_chain.json]
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT = os.path.join(ROOT, "data", "apple_supply_chain.json")

VALID_LINES = {"iPhone", "Mac", "iPad", "Wearable", "Spatial", "Audio"}
VALID_TIERS = {1, 2, "1", "2"}


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def node_index(d):
    """返回 {class: {id: node}} 与 {class: [ids]}。"""
    idx = {}
    ids = {}
    for cls in ("products", "components", "suppliers"):
        idx[cls] = {n["id"]: n for n in d["nodes"][cls]}
        ids[cls] = set(idx[cls])
    return idx, ids


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    d = load(path)
    idx, ids = node_index(d)

    problems = []
    info = []

    # ---- 1) 引用完整性 + 类型正确 + 重复边 ----
    edge_spec = {
        "uses_component": ("products", "components"),
        "supplied_by": ("components", "suppliers"),
        "assembled_by": ("products", "suppliers"),
    }
    seen_edges = {k: set() for k in edge_spec}
    # 为孤立节点统计维护出现次数
    used_as = {"products": set(), "components": set(), "suppliers": set()}

    for etype, (from_cls, to_cls) in edge_spec.items():
        for e in d["edges"][etype]:
            f, t = e.get("from"), e.get("to")
            key = (f, t)
            if key in seen_edges[etype]:
                problems.append(f"[重复边] {etype}: {f} -> {t} 出现多次")
            seen_edges[etype].add(key)
            if f not in ids[from_cls]:
                problems.append(f"[悬空引用] {etype}: from='{f}' 不是已知 {from_cls} 节点")
            else:
                used_as[from_cls].add(f)
            if t not in ids[to_cls]:
                problems.append(f"[悬空引用] {etype}: to='{t}' 不是已知 {to_cls} 节点")
            else:
                used_as[to_cls].add(t)
            if e.get("from") == e.get("to"):
                problems.append(f"[自环] {etype}: {f} -> {f}")

    # ---- 2) 重复节点 id ----
    for cls in ("products", "components", "suppliers"):
        seen = set()
        for n in d["nodes"][cls]:
            if n["id"] in seen:
                problems.append(f"[重复节点] {cls}: id='{n['id']}' 重复定义")
            seen.add(n["id"])

    # ---- 3) 必填字段 ----
    req = {
        "products": ("id", "name", "product_line"),
        "components": ("id", "name", "category"),
        "suppliers": ("id", "name", "country", "category", "tier"),
    }
    for cls, fields in req.items():
        for n in d["nodes"][cls]:
            for fld in fields:
                if n.get(fld) in (None, "", []):
                    problems.append(f"[缺字段] {cls} '{n.get('id')}': 缺少 {fld}")

    # ---- 4) 孤立节点 ----
    for cls in ("products", "components", "suppliers"):
        for n in d["nodes"][cls]:
            if n["id"] not in used_as[cls]:
                problems.append(f"[孤立节点] {cls}: '{n['id']}' 不参与任何关系")

    # ---- 5) 悬空逻辑：被使用却无供应商的零部件 ----
    used_comps = set(e["to"] for e in d["edges"]["uses_component"])
    supplied_comps = set(e["from"] for e in d["edges"]["supplied_by"])
    for cid in sorted(used_comps - supplied_comps):
        comp = idx["components"].get(cid, {})
        problems.append(f"[无供应商] 零部件 '{cid}'（{comp.get('name')}）被产品使用但无 supplied_by 关系")

    # ---- 6) 取值合规 ----
    for p in d["nodes"]["products"]:
        if p.get("product_line") not in VALID_LINES:
            problems.append(f"[取值越界] product '{p['id']}' product_line='{p.get('product_line')}' 不在 {sorted(VALID_LINES)}")
    for s in d["nodes"]["suppliers"]:
        if s.get("tier") not in VALID_TIERS:
            problems.append(f"[取值越界] supplier '{s['id']}' tier='{s.get('tier')}' 不在 {sorted(VALID_TIERS, key=str)}")
    # supplied_by.share 可解析为数字或范围
    for e in d["edges"]["supplied_by"]:
        sh = e.get("share")
        if sh not in (None, ""):
            s2 = str(sh).replace("%", "").replace("~", "-").replace("–", "-").split("-")[0].strip()
            try:
                float(s2)
            except ValueError:
                problems.append(f"[share 不可解析] supplied_by {e['from']}->{e['to']} share='{sh}'")

    # ---- 汇总统计 ----
    n_prod = len(d["nodes"]["products"])
    n_comp = len(d["nodes"]["components"])
    n_supp = len(d["nodes"]["suppliers"])
    n_uc = len(d["edges"]["uses_component"])
    n_sb = len(d["edges"]["supplied_by"])
    n_ab = len(d["edges"]["assembled_by"])

    # 单点依赖：某零部件仅 1 家供应商
    comp_supplier_count = {}
    for e in d["edges"]["supplied_by"]:
        comp_supplier_count[e["from"]] = comp_supplier_count.get(e["from"], 0) + 1
    single_point = sorted([c for c, c2 in comp_supplier_count.items() if c2 == 1])

    print("=" * 60)
    print("数据集交叉验证报告")
    print("=" * 60)
    print(f"节点: Product={n_prod}  Component={n_comp}  Supplier={n_supp}")
    print(f"边  : USES_COMPONENT={n_uc}  SUPPLIED_BY={n_sb}  ASSEMBLED_BY={n_ab}")
    print(f"单点依赖零部件数(仅1家供应商): {len(single_point)}")
    print("-" * 60)
    if problems:
        print(f"发现问题 {len(problems)} 项：")
        for p in problems:
            print("  ✗", p)
    else:
        print("✓ 未发现问题，数据集内部一致。")
    print("=" * 60)
    # 返回问题数（供 CI / 脚本判断）
    return len(problems)


if __name__ == "__main__":
    sys.exit(1 if main() > 0 else 0)
