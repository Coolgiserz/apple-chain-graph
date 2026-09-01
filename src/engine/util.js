// util.js — 纯函数工具与常量（无状态依赖，供 render / panels / interaction 复用）。
import { S, RISK_HIGH, RISK_MED } from "./state.js";

// —— 画布配色与 CSS 令牌同源（P1-6）——
// 背景：节点色原本是硬编码字面量，而图例色点用 var(--primary) 之类，两边只要改一处就会分叉。
// 实测已分叉过：图例 var(--green) 解析为 #4ade80，画布 COLORS.Supplier 却是 #10b981。
// 方案：模块加载时一次性从 :root 读取令牌值，让 :root 成为唯一真源，图例与画布永不漂移。
//
// 前提：<script src="dist/graph_engine.js"> 位于 body 末尾，<style> 已在 <head> 解析完毕，
//       因此 getComputedStyle 可以读到令牌值；此时尚未进入渲染循环，读取不构成布局抖动。
// 注意：panels.js 存在 `col + "22"` 拼接 alpha 的写法（col 来自 COLORS），故令牌值必须是
//       6 位 hex，不能写成 rgb() / hsl() / 8 位带 alpha 的形式，否则拼接结果是非法颜色。
//       回退值仅用于无 DOM 的极端场景（如 Node 下单测），必须与 :root 保持一致。
function cssToken(name, fallback) {
  try {
    var v = getComputedStyle(document.documentElement).getPropertyValue(name);
    if (v && v.trim()) return v.trim();
  } catch (e) { /* 无 DOM 环境，落到回退值 */ }
  return fallback;
}

// 批量读取：{ 语义键: CSS 令牌名 } + { 语义键: 回退值 } → { 语义键: 实际颜色 }
export function cssColors(tokenMap, fallback) {
  var out = {};
  Object.keys(fallback).forEach(function (k) {
    out[k] = cssToken(tokenMap[k], fallback[k]);
  });
  return out;
}

export const COLORS = cssColors(
  { Product: "--primary", Component: "--warn", Supplier: "--green", Line: "--violet", Base: "--pink" },
  { Product: "#2f6fed", Component: "#f59e0b", Supplier: "#4ade80", Line: "#8b5cf6", Base: "#ec4899" }
);

// 环色：单点依赖/关键洞察用琥珀，瓶颈下游聚焦用青
export const RING = cssColors(
  { active: "--amber", focus: "--cyan" },
  { active: "#fbbf24", focus: "#22d3ee" }
);

// 风险色：高 / 中 / 低。vulnColor 目前无调用方（死代码），一并令牌化以免将来有人
// 用到时又引入一套与图例不一致的字面量。
const RISK = cssColors(
  { high: "--red", mid: "--warn", low: "--green" },
  { high: "#f87171", mid: "#f59e0b", low: "#4ade80" }
);

export const BASE_R = { Product: 11, Component: 7, Supplier: 6, Line: 14, Base: 8 };

// 视口相关的节点半径缩放系数：小屏（手机/窄平板）放大世界半径，使节点更大、更易点中；
// 大屏略放大但不夸张。以 min(宽,高) 为基准（参考尺寸 880px），区间 [0.6, 1.15]。
// 注：节点半径以「世界单位」绘制（draw 已按 view.scale 变换），fitView 也会在小屏放大 view.scale，
// 二者叠加保证移动端首屏节点清晰可读、可点。
export function rScale() {
  var m = Math.min(W(), H());
  if (!m) return 1;
  return Math.max(0.6, Math.min(1.15, m / 880));
}

// 节点绘制/命中的世界半径（含度数加成，再乘视口系数）。render 与 interaction 统一走这里。
export function nodeRadius(n) {
  return (BASE_R[n.type] + Math.min(n.degree || 0, 12) * 0.35) * rScale();
}

// 画布可视尺寸（优先画布 CSS 尺寸，回退 window）
export function W() { return (S.cv ? S.cv.clientWidth : 0) || (typeof window !== "undefined" && window.innerWidth) || 0; }
export function H() { return (S.cv ? S.cv.clientHeight : 0) || (typeof window !== "undefined" && window.innerHeight) || 0; }

// HTML 转义：转义 & < > " ' 五类字符（OWASP 推荐全集）。
// 同时覆盖单/双引号属性与文本节点上下文，避免外链等数据含引号时破裂或注入。
export function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]); }); }

// 外链白名单：仅放行 http(s) 协议，阻断 javascript:/data:/vbscript: 等危险协议。
// 防御纵深——外链 URL 来自数据（source_registry），不可信，绝不原样进 href。
export function safeUrl(u) {
  try {
    var s = String(u == null ? "" : u);
    if (/^https?:\/\//i.test(s)) return s;
  } catch (e) {}
  return "";
}

export function label(n) { return n.name || n.english_name || n.id; }
export function nm(t, id) { var o = S.idMap[t + ":" + id]; return o ? label(o) : id; }

// 节点类型标签（用于信息面板 tag 等多语言展示）。Line 为展示层虚拟节点（产品线聚合），
// 不在数据文件里；其余三种与数据 schema 一致。
export function typeLabel(t) {
  if (t === "Line") return i18nText("home.line");
  if (t === "Product") return i18nText("home.prod");
  if (t === "Component") return i18nText("home.part");
  if (t === "Supplier") return i18nText("home.supp");
  if (t === "Base") return i18nText("home.base");
  return t;
}

export function vulnColor(v) {
  if (v >= RISK_HIGH) return RISK.high;   // 高 → 红
  if (v >= RISK_MED) return RISK.mid;     // 中 → 琥珀
  return RISK.low;                        // 低 → 绿
}

// 关键度 / 风险「热力环」：t∈[0,1] 越大，环越粗、越红。
// 设计要点：类型用「填充色」、权重用「红环」两个互相独立的视觉通道，
// 避免过去「填充=权重渐变」与类型色（绿/琥珀）撞色、且红同时表示高权重与选中的混乱。
export function heatRing(t) {
  if (t == null || isNaN(t)) t = 0;
  if (t < 0) t = 0; if (t > 1) t = 1;
  return {
    color: "rgba(239,68,68," + (0.22 + 0.7 * t).toFixed(3) + ")",
    width: (1.5 + 2.6 * t).toFixed(2)
  };
}

// 国际化：缺失 key 时回退到中文源（zh 为 fallbackLng），避免显示原始 key
export function i18nText(k) { return (window.i18n && window.i18n.ready) ? window.i18n.t(k) : k; }

// 枚举值（region / category / country / tier / status / product_line / subcategory）
// 经 i18n 翻译：raw -> <domain>.<key> -> 对应语言文本。映射（raw->键）单一来源是
// window.I18N_ENUM_MAP（由 build_viewer.py 从 locales/enum_map.json 内联），译文在 locales/*.json。
export function i18nVal(domain, raw) {
  if (raw === undefined || raw === null || raw === "") return "";
  var key = (window.I18N_ENUM_MAP && window.I18N_ENUM_MAP[domain] && window.I18N_ENUM_MAP[domain][String(raw)]) || null;
  return key ? i18nText(domain + "." + key) : String(raw);
}
