// util.js — 纯函数工具与常量（无状态依赖，供 render / panels / interaction 复用）。
import { S, RISK_HIGH, RISK_MED } from "./state.js";

export const COLORS = { Product: "#2f6fed", Component: "#f59e0b", Supplier: "#10b981", Line: "#8b5cf6", Base: "#ec4899" };
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
  if (t === "Base") return i18nText("home.base");
  return t;
}

export function vulnColor(v) {
  if (v >= RISK_HIGH) return "#ef4444";   // 高 → 红
  if (v >= RISK_MED) return "#f59e0b";     // 中 → 琥珀
  return "#10b981";                        // 低 → 绿
}

// 瓶颈指标热力色：t∈[0,1]（越大越关键/越集中），绿(低)→琥珀→红(高)。
// 用于「权重→填充」的旧映射；现改为「权重→红环」(heatRing)，此处保留以兼容潜在调用。
export function metricColor(t) {
  if (t == null || isNaN(t)) t = 0;
  if (t < 0) t = 0; if (t > 1) t = 1;
  var lo = [16, 185, 129], mid = [245, 158, 11], hi = [239, 68, 68];
  var c, a = t * 2;
  if (a <= 1) { c = [lo[0] + (mid[0] - lo[0]) * a, lo[1] + (mid[1] - lo[1]) * a, lo[2] + (mid[2] - lo[2]) * a]; }
  else { a -= 1; c = [mid[0] + (hi[0] - mid[0]) * a, mid[1] + (hi[1] - mid[1]) * a, mid[2] + (hi[2] - mid[2]) * a]; }
  return "rgb(" + Math.round(c[0]) + "," + Math.round(c[1]) + "," + Math.round(c[2]) + ")";
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
