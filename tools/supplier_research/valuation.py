# -*- coding: utf-8 -*-
"""
相对估值引擎 (Relative Valuation Engine)
方法：对单个供应商，用其当前估值倍数(P/E、P/B、EV/EBITDA) 与「同业组中位倍数」比较，
      取各倍数的比值(当前/同业中位)的均值作为 composite score：
        score < 0.85  -> 低估 (Undervalued)
        score > 1.15  -> 高估 (Overvalued)
        其余          -> 合理 (Fair)
缺失某倍数(如亏损导致 P/E 无效)或同业无可比数据时自动跳过该倍数。
这是透明的、可复现的同业相对估值，非 DCF 绝对估值；结论应结合趋势/近况定性判断。
"""

import statistics


def _median(xs):
    xs = [x for x in xs if isinstance(x, (int, float)) and x > 0]
    return statistics.median(xs) if xs else None


MULTIPLE_FIELDS = [
    ("pe", "P/E"),
    ("pb", "P/B"),
    ("ev_ebitda", "EV/EBITDA"),
]

# 阈值（可按需调参）
UNDER_THRESHOLD = 0.85
OVER_THRESHOLD = 1.15


def peer_medians(all_metrics, peer_group, exclude_id=None):
    """计算某同业组内各倍数的中位值。all_metrics: dict id->metrics(含 pe/pb/ev_ebitda/peer_group)。"""
    peers = [m for m in all_metrics.values()
             if m.get("peer_group") == peer_group and m.get("id") != exclude_id]
    out = {}
    for key, _ in MULTIPLE_FIELDS:
        out[key] = _median([p.get(key) for p in peers])
    return out


def universe_medians(all_metrics, exclude_id=None):
    """全样本（所有已上市且含倍数的供应商）各倍数的中位值，作为同业不足时的回退基准。"""
    peers = [m for m in all_metrics.values() if m.get("id") != exclude_id]
    out = {}
    for key, _ in MULTIPLE_FIELDS:
        out[key] = _median([p.get(key) for p in peers])
    return out


def evaluate(metrics, all_metrics):
    """
    metrics: 单个供应商的财务/估值 dict(含 id, peer_group, pe, pb, ev_ebitda, net_income_ttm_usd_b)
    返回: {verdict, score, detail[], peer_group, peer_count, fallback, distressed?}
    逻辑：优先用 sector 同业中位；若某倍数在 sector 内可比样本 < 2，则回退到
          全样本中位（fallback=True），保证每家上市供应商都能得到定量判定。
    亏损公司特殊处理：TTM 净利<=0 时，P/B、EV/EBITDA 为困境/周期底部倍数，
          不能据此判定低估，返回"困境（亏损）·倍数失真"；同时同业中位锚点会
          排除亏损同业，避免其失真倍数拉偏盈利同业（如 BOE 不应被 LGD 锚定）。
    """
    pg = metrics.get("peer_group")
    ni = metrics.get("net_income_ttm_usd_b")
    sector_peers = [m for m in all_metrics.values()
                    if m.get("peer_group") == pg and m.get("id") != metrics.get("id")]
    # 盈利同业：用于中位锚点（排除亏损同业，其倍数失真）
    profitable_peers = [m for m in sector_peers
                        if not (isinstance(m.get("net_income_ttm_usd_b"), (int, float)) and m["net_income_ttm_usd_b"] <= 0)]
    uni_meds = universe_medians(all_metrics, exclude_id=metrics.get("id"))

    # 亏损公司：倍数失真，不给出低估/高估定量判定
    if isinstance(ni, (int, float)) and ni <= 0:
        return {
            "verdict": "困境（亏损）·倍数失真",
            "score": None,
            "detail": ["该公司处于亏损（TTM 净利<=0），P/B、EV/EBITDA 为困境/周期底部倍数，"
                       "不能据此判定低估；应结合扭亏进度、现金状况与资产质量单独判断。"],
            "peer_group": pg,
            "peer_count": len(sector_peers),
            "fallback": False,
            "distressed": True,
        }

    ratios, detail = [], []
    used_fallback = False
    for key, label in MULTIPLE_FIELDS:
        v = metrics.get(key)
        if not isinstance(v, (int, float)) or v <= 0:
            continue
        s_med = _median([p.get(key) for p in profitable_peers])
        if s_med and s_med > 0:
            base, med = "同业中位", s_med
        else:
            # 同业不足 -> 回退全样本中位
            u_med = uni_meds.get(key)
            if not u_med or u_med <= 0:
                continue
            base, med, used_fallback = "全样本中位(同业不足回退)", u_med, True
        r = v / med
        ratios.append(r)
        detail.append(f"{label} {v:.1f} × vs {base} {med:.1f} × (比值 {r:.2f})")

    peer_count = len(sector_peers)
    if not ratios:
        return {
            "verdict": "N/A（缺倍数或无可比同业）",
            "score": None,
            "detail": ["缺少可用的正估值倍数或未找到上市同业，无法定量相对估值；详见定性结论。"],
            "peer_group": pg,
            "peer_count": peer_count,
            "fallback": used_fallback,
        }
    score = sum(ratios) / len(ratios)
    if score < UNDER_THRESHOLD:
        verdict = "低估"
    elif score > OVER_THRESHOLD:
        verdict = "高估"
    else:
        verdict = "合理"
    return {
        "verdict": verdict,
        "score": round(score, 2),
        "detail": detail,
        "peer_group": pg,
        "peer_count": peer_count,
        "fallback": used_fallback,
    }
