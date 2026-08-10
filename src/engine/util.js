// util.js — 纯函数工具与常量（无状态依赖，供 render / panels / interaction 复用）。
import { S, RISK_HIGH, RISK_MED } from "./state.js";

export const COLORS = { Product: "#2f6fed", Component: "#f59e0b", Supplier: "#10b981", Line: "#8b5cf6" };
export const BASE_R = { Product: 11, Component: 7, Supplier: 6, Line: 14 };

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

// HTML 转义：仅转义 & < >（属性值由调用方保证不含引号，或改用引号转义）
export function esc(s) { return String(s).replace(/[&<>]/g, function (c) { return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]); }); }

export function label(n) { return n.name || n.english_name || n.id; }
export function nm(t, id) { var o = S.idMap[t + ":" + id]; return o ? label(o) : id; }

// 节点类型标签（用于信息面板 tag 等多语言展示）。Line 为展示层虚拟节点（产品线聚合），
// 不在数据文件里；其余三种与数据 schema 一致。
export function typeLabel(t) {
  if (t === "Line") return i18nText("home.line");
  if (t === "Product") return i18nText("home.prod");
  if (t === "Component") return i18nText("home.part");
  if (t === "Supplier") return i18nText("home.supp");
  return t;
}

export function vulnColor(v) {
  if (v >= RISK_HIGH) return "#ef4444";   // 高 → 红
  if (v >= RISK_MED) return "#f59e0b";     // 中 → 琥珀
  return "#10b981";                        // 低 → 绿
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
