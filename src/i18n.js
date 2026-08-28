/*! 站点国际化引导（ES Module 源；由 esbuild 打包为 dist/i18n.js，IIFE）
 *  约定：
 *   - 语言包放在仓库根 locales/<lng>.json（zh 源，en/fr/ja 待填/已部分）
 *   - 静态文本：元素加 data-i18n="key"（textContent）或 data-i18n-attr="placeholder:key"（属性）
 *   - JS 动态文本：调用 window.i18n.t("key")
 *   - 切换语言：window.i18n.changeLanguage("en") —— 记忆到 localStorage + ?lang=
 *
 *  健壮性设计（关键）：
 *   - 中文源 ZH 内联兜底：即使 locales/*.json 因 file:// / 404 / 网络失败而加载不到，
 *     页面也始终显示中文，绝不把翻译 key（如 home.resetView）当文本渲染出来。
 *   - applyDOM 仅在拿到「真实译文」时才覆盖元素，缺失翻译时保留原始中文。
 *   - 默认中文（?lang= / localStorage 显式选择优先，否则中文）。
 *  ZH 需与 locales/zh.json 保持同步。
 *
 *  注：i18next 运行时由 dist/vendor/i18next.min.js 以全局 window.i18next 提供
 *  （vendored，离线可用，不依赖 CDN）；本文件仅作引导层，读取该全局。
 *  打包后对外暴露 window.i18n（API：ready / t / changeLanguage / 事件 i18n:ready / i18n:changed）。
 */
var SUPPORTED = ["zh", "en", "fr", "ja"];
var DEFAULT = "zh";

// 中文源内联兜底（镜像 locales/zh.json）
var ZH = {
  "nav.graph": "供应链图谱", "nav.table": "企业列表", "nav.report": "上下游报告",
  "nav.map": "供应商地图", "nav.dash": "估值看板",
  "home.search": "搜索产品/零部件/供应商…", "home.prod": "产品", "home.part": "零部件",
  "home.supp": "供应商", "home.line": "产品线", "home.all": "全部",
  "home.tableBtn": "企业表格", "home.resetView": "重置视图",
  "home.hint": "滚轮缩放 · 拖拽画布平移 · 拖动节点 · 单击节点看详情",
  "home.sideTitle": "企业表格", "panel.rel": "关联", "panel.relHint": "点击可聚焦",
  "table.name": "名称", "table.country": "国家/地区", "table.category": "类别", "table.tier": "层级",
  "field.release_date": "发布时间", "field.status": "状态", "field.price": "起售价(USD)",
  "field.soc": "SoC", "field.display": "显示屏", "field.alias": "别名", "field.assembly": "代工",
  "field.category": "类别", "field.subcategory": "子类", "field.short_name": "简称",
  "field.country": "国家/地区", "field.region": "区域", "field.tier": "层级",
  "status.onsale": "在售", "status.rumor": "传闻/未发布",
  "link.report": "在报告中查看 →", "link.map": "在地图中查看 →",
  "brand": "Apple 供应链"
};

// 自动同步：把 locales.js 注入的 zh 官方包并入 ZH 兜底常量。
// ZH 是「未就绪 / locales 加载失败」时的兜底，且是 zh 语言包的基底（init 里 base = ZH 再并入 bundle）。
// 若只把新增 key 写进 locales/*.json 而忘了同步这里的 ZH，未就绪/失败时会把原始 key 当文本渲染
// （本分支曾出现「关键洞察」显示 home.insightLineHas 等原始 key 的回归）。
// locales.js 在 i18n.js 之前加载，此处可直接并入，确保 ZH 始终与 locales/zh.json 一致，无需手工维护。
if (typeof window !== "undefined" && window.I18N_LOCALES && window.I18N_LOCALES.zh) {
  Object.assign(ZH, window.I18N_LOCALES.zh);
}

// 安全读写 localStorage：在沙箱 iframe（无 allow-same-origin）、隐私模式等环境
// 下 localStorage 会抛错，必须 try/catch，否则会中断整段 i18n 初始化，导致「插件」
// 嵌入后整页脚本崩溃。读不到时回退到默认语言即可。
function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }

function detect() {
  var p = new URLSearchParams(location.search).get("lang");
  if (p && SUPPORTED.indexOf(p) >= 0) return p;
  var s = lsGet("site_lang");
  if (s && SUPPORTED.indexOf(s) >= 0) return s;
  return DEFAULT; // 默认中文
}

var current = detect();
var pendingLng = null;

var api = {
  lng: current,
  ready: false,
  t: resolvedT,                                                          // 预初始化即用「ZH 兜底 + 异步自动翻译」
  changeLanguage: function (lng) { lng = lng; }                          // 预初始化占位
};
window.i18n = api;

// ---- 运行时自动翻译：缺 key 时按需调用翻译后端（默认 MyMemory，免密钥 / CORS 开放） ----
// 配置（可选，写在 i18n.js 之前）：window.I18N_TRANSLATE = { backend:'mymemory'|'libretranslate'|'deepl', url?, key?, email? }
// 离线 / 请求失败 / 无网络 → 回退 ZH 兜底（绝不显示裸 key）。译文缓存于 localStorage，避免重复请求。
var TCFG = (typeof window !== "undefined" && window.I18N_TRANSLATE) || { backend: "mymemory" };
var RUNTIME = {};   // RUNTIME[lng] = { key: text }
var PENDING = {};   // PENDING[lng][key] = true 去重，防止并发重复请求

function _rtKeyOf(lng) { return "i18n_rt_" + lng; }
function _rtLoad(lng) { if (!RUNTIME[lng]) { try { RUNTIME[lng] = JSON.parse(lsGet(_rtKeyOf(lng)) || "{}"); } catch (e) { RUNTIME[lng] = {}; } } }
function _rtSave(lng) { try { lsSet(_rtKeyOf(lng), JSON.stringify(RUNTIME[lng] || {})); } catch (e) {} }
function _rtGet(lng, k) { _rtLoad(lng); return RUNTIME[lng][k]; }
function _rtSet(lng, k, t) { _rtLoad(lng); RUNTIME[lng][k] = t; _rtSave(lng); }

async function _fetchTranslation(lng, text) {
  try {
    if (TCFG.backend === "libretranslate") {
      var lu = TCFG.url || "https://libretranslate.com/translate";
      var lr = await fetch(lu, { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ q: text, source: "zh", target: lng }) });
      if (!lr.ok) return null;
      var ld = await lr.json(); return ld.translatedText || null;
    }
    if (TCFG.backend === "deepl") {
      var dr = await fetch("https://api-free.deepl.com/v2/translate", {
        method: "POST", headers: { "Content-Type": "application/json", "Authorization": "DeepL-Auth-Key " + (TCFG.key || "") },
        body: JSON.stringify({ text: [text], target_lang: lng.toUpperCase() }) });
      if (!dr.ok) return null;
      var dd = await dr.json();
      return (dd.translations && dd.translations[0] && dd.translations[0].text) || null;
    }
    // 默认 MyMemory：免密钥、CORS 开放、单次请求上限 500 字节
    var p = new URLSearchParams({ q: text.slice(0, 500), langpair: "zh|" + lng });
    if (TCFG.email) p.set("de", TCFG.email);
    var mr = await fetch("https://api.mymemory.translated.net/get?" + p.toString());
    if (!mr.ok) return null;
    var md = await mr.json();
    if (md.responseStatus === 200 && md.responseData && md.responseData.translatedText) return md.responseData.translatedText;
    return null;
  } catch (e) { return null; }
}

function _ensureTranslated(key, lng, zh) {
  if (lng === DEFAULT || !zh) return;
  if (_rtGet(lng, key)) return;
  PENDING[lng] = PENDING[lng] || {};
  if (PENDING[lng][key]) return;
  PENDING[lng][key] = true;
  _fetchTranslation(lng, zh).then(function (t) {
    if (t && t !== zh) {
      _rtSet(lng, key, t);
      if (window.i18next && window.i18next.addResource) {
        try { window.i18next.addResource(lng, "translation", key, t); } catch (e) {}
      }
      document.dispatchEvent(new CustomEvent("i18n:translated", { detail: { key: key, lng: lng, text: t } }));
    }
    PENDING[lng][key] = false;
  }).catch(function () { PENDING[lng][key] = false; });
}

// 统一翻译入口：同步返回「最佳可用文本」，并（非中文且缺失时）触发异步翻译。
function resolvedT(k, opts) {
  var zh = ZH[k];
  var src = (zh !== undefined) ? zh : ((opts && opts.defaultValue) || k);
  if (current === DEFAULT) return src;                 // 中文直接返回源
  var rt = _rtGet(current, k);                          // 运行时缓存译文
  if (rt) return rt;
  if (window.i18next && api.ready) {                   // i18next 资源（含已注入译文）
    var tr = window.i18next.t(k, opts);
    if (tr && tr !== k) return tr;
  }
  _ensureTranslated(k, current, zh);                   // 异步取译文，先返回 ZH 兜底
  return src;
}

function applyDOM() {
  if (!window.i18next) return;
  document.querySelectorAll("[data-i18n]").forEach(function (el) {
    var k = el.getAttribute("data-i18n");
    var tr = resolvedT(k);                  // 同步返回 ZH 兜底，缺失时触发异步自动翻译
    if (tr && tr !== k) el.textContent = tr;
  });
  document.querySelectorAll("[data-i18n-attr]").forEach(function (el) {
    el.getAttribute("data-i18n-attr").split(";").forEach(function (pair) {
      var kv = pair.split(":");
      if (kv.length === 2) { var tr = resolvedT(kv[1]); if (tr && tr !== kv[1]) el.setAttribute(kv[0], tr); }
    });
  });
}

// 语言包通过 dist/locales.js（window.I18N_LOCALES）内联提供，无需运行时 fetch/XHR。
// 这样在 GitHub Pages、本地 file://、任意子路径部署下都能加载，且不会因
// 部署遗漏 locales/ 目录或 file:// 的 CORS 限制而 404 / 切换失效。
function init() {
  if (!window.i18next) {
    console.warn("[i18n] i18next 未加载，跳过国际化（保留中文）");
    return;
  }
  var bundles = window.I18N_LOCALES || {};
  var resources = {};
  SUPPORTED.forEach(function (l) {
    var base = (l === DEFAULT) ? Object.assign({}, ZH) : {};
    if (bundles[l]) Object.assign(base, bundles[l]); // 完整包覆盖兜底子集
    resources[l] = { translation: base };
  });
  window.i18next.init({
    lng: current,
    fallbackLng: DEFAULT,
    supportedLngs: SUPPORTED,
    resources: resources,
    interpolation: { escapeValue: false },
    returnEmptyString: false,
    keySeparator: false,
    nsSeparator: false
  }, function () {
    api.ready = true;
    // 注意：api.t 保持 resolvedT（同步 ZH 兜底 + 异步自动翻译），不覆盖为裸 i18next.t
    applyDOM();
    document.addEventListener("i18n:translated", function () { if (window.i18next) applyDOM(); });
    var sel = document.getElementById("langSwitch");
    if (sel) sel.value = current;
    if (pendingLng) { var pl = pendingLng; pendingLng = null; api.changeLanguage(pl); }
    document.dispatchEvent(new CustomEvent("i18n:ready"));
  });
}

api.changeLanguage = function (lng) {
  if (SUPPORTED.indexOf(lng) < 0) lng = DEFAULT;
  current = lng;
  api.lng = lng;
  lsSet("site_lang", lng);
  try {
    var u = new URL(location.href);
    u.searchParams.set("lang", lng);
    history.replaceState(null, "", u);
  } catch (e) {}
  var sel = document.getElementById("langSwitch");
  if (sel) sel.value = lng;
  if (window.i18next && api.ready) {
    window.i18next.changeLanguage(lng, function () {
      applyDOM();
      document.dispatchEvent(new CustomEvent("i18n:changed", { detail: { lng: lng } }));
    });
  } else {
    pendingLng = lng; // 尚未就绪：等 i18n:ready 后补应用
  }
};

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
