"""供应商舆情分析模块。

加载 tools/data/supplier_sentiment.csv（由 WebSearch + 分析师共识整理），
渲染为 Markdown 舆情报告小节。零外部依赖（仅标准库）。
"""
import csv
import json
import os
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "..", "data")
SENT_CSV = os.path.join(DATA_DIR, "supplier_sentiment.csv")
ANALYSIS_JSON = os.path.join(HERE, "..", "output", "supplier_analysis.json")

# 标签映射
NEWS_LABEL = {"positive": "正面", "neutral": "中性", "negative": "负面"}
NEWS_ICON = {"positive": "🟢", "neutral": "🟡", "negative": "🔴"}
ANALYST_LABEL = {"bullish": "看多", "neutral": "中性", "bearish": "看空"}
ANALYST_ICON = {"bullish": "🟢", "neutral": "🟡", "bearish": "🔴"}

# 估值结论标签（来自 supplier_analysis.json，可选合并）
VAL_LABEL = {
    "低估": "🔵低估", "合理": "⚪合理", "高估": "🔴高估",
    "基准（终端厂，非供应商）": "⚫基准",
}


def load_sentiment():
    """返回 {supplier_id: row_dict}。"""
    if not os.path.exists(SENT_CSV):
        return {}
    out = {}
    with open(SENT_CSV, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            out[r["supplier_id"]] = r
    return out


def load_names():
    """从 universe 获取供应商中文名（失败则回退空）。"""
    try:
        import universe
        names = {}
        for sid, rec in universe.UNIVERSE.items():
            names[sid] = rec.get("name") or rec.get("short_name") or sid
        return names
    except Exception:
        return {}


def load_valuation():
    """从已有分析报告 JSON 读取估值结论，返回 {id: verdict_label}。"""
    if not os.path.exists(ANALYSIS_JSON):
        return {}
    try:
        with open(ANALYSIS_JSON, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}
    out = {}
    for rec in data.get("suppliers", []):
        v = rec.get("valuation") or {}
        verdict = v.get("verdict")
        if verdict:
            out[rec["id"]] = verdict
    return out


def build_overview(sent, names=None, valuation=None):
    """舆情总览表。"""
    names = names or {}
    valuation = valuation or {}
    if not sent:
        return "_（暂无舆情数据）_"
    lines = []
    lines.append("| 供应商 | 新闻情绪 | 分析师情绪 | 估值结论 | 关键催化剂 | 关键风险 |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for sid, r in sent.items():
        n = names.get(sid, sid)
        nv = NEWS_ICON.get(r["news_sentiment"], "") + NEWS_LABEL.get(r["news_sentiment"], r["news_sentiment"])
        av = ANALYST_ICON.get(r["analyst_sentiment"], "") + ANALYST_LABEL.get(r["analyst_sentiment"], r["analyst_sentiment"])
        val = VAL_LABEL.get(valuation.get(sid), valuation.get(sid, "—"))
        lines.append(f"| {n} | {nv} | {av} | {val} | {r['key_catalysts']} | {r['key_risks']} |")
    return "\n".join(lines)


def build_detail(sent, names=None):
    """逐家舆情明细。"""
    names = names or {}
    if not sent:
        return "_（暂无舆情数据）_"
    blocks = []
    for sid, r in sent.items():
        n = names.get(sid, sid)
        nv = NEWS_LABEL.get(r["news_sentiment"], r["news_sentiment"])
        av = ANALYST_LABEL.get(r["analyst_sentiment"], r["analyst_sentiment"])
        srcs = ""
        if r.get("sources"):
            urls = [u.strip() for u in r["sources"].split(",") if u.strip()]
            srcs = "\n".join(f"  - {u}" for u in urls)
        block = (
            f"### {n}（`{sid}`）\n"
            f"- **新闻情绪**：{nv} ｜ **分析师情绪**：{av}\n"
            f"- **新闻综述**：{r['news_summary']}\n"
            f"- **分析师共识**：{r['analyst_consensus']}\n"
            f"- **关键催化剂**：{r['key_catalysts']}\n"
            f"- **关键风险**：{r['key_risks']}\n"
            f"- **来源**：\n{srcs}\n"
        )
        blocks.append(block)
    return "\n".join(blocks)


def build_summary_stats(sent):
    """舆情分布统计。"""
    if not sent:
        return "_（暂无舆情数据）_"
    nc = Counter(r["news_sentiment"] for r in sent.values())
    ac = Counter(r["analyst_sentiment"] for r in sent.values())
    total = len(sent)
    def fmt(c, key_map):
        return "、".join(f"{key_map.get(k, k)} {v} 家" for k, v in c.items()) or "—"
    return (f"覆盖 **{total}** 家供应商。\n"
            f"- 新闻情绪：{fmt(nc, NEWS_LABEL)}。\n"
            f"- 分析师情绪：{fmt(ac, ANALYST_LABEL)}。")


def build_full_report(sent, names=None, valuation=None):
    """生成完整舆情报告正文（不含文档头部/尾部）。"""
    names = names or {}
    valuation = valuation or {}
    out = []
    out.append("## 一、舆情总览\n")
    out.append(build_summary_stats(sent) + "\n")
    out.append(build_overview(sent, names, valuation) + "\n")
    out.append("## 二、逐家舆情明细\n")
    out.append(build_detail(sent, names) + "\n")
    return "\n".join(out)


if __name__ == "__main__":
    s = load_sentiment()
    print(build_full_report(s, load_names(), load_valuation()))
