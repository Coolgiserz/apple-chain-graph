// util.js — 纯函数工具与常量（无状态依赖，供 render / panels / interaction 复用）。
import { S, RISK_HIGH, RISK_MED } from "./state.js";

export const COLORS = { Product: "#2f6fed", Component: "#f59e0b", Supplier: "#10b981" };
export const BASE_R = { Product: 11, Component: 7, Supplier: 6 };

// 画布可视尺寸（优先画布 CSS 尺寸，回退 window）
export function W() { return (S.cv ? S.cv.clientWidth : 0) || (typeof window !== "undefined" && window.innerWidth) || 0; }
export function H() { return (S.cv ? S.cv.clientHeight : 0) || (typeof window !== "undefined" && window.innerHeight) || 0; }

// HTML 转义：仅转义 & < >（属性值由调用方保证不含引号，或改用引号转义）
export function esc(s) { return String(s).replace(/[&<>]/g, function (c) { return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]); }); }

export function label(n) { return n.name || n.english_name || n.id; }
export function nm(t, id) { var o = S.idMap[t + ":" + id]; return o ? label(o) : id; }

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
