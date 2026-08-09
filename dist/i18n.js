/*! 站点国际化引导（基于 i18next + i18next-http-backend，零构建、纯静态）
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
 */
(function () {
  var SUPPORTED = ["zh", "en", "fr", "ja"];
  var DEFAULT = "zh";
  var ASSET_VERSION = "20260809f"; // 资源版本号：改动语言包/引导脚本后递增，破除浏览器缓存

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
    "field.country": "国家/地区", "field.region": "区域", "field.tier": "层级"
  };

  function detect() {
    var p = new URLSearchParams(location.search).get("lang");
    if (p && SUPPORTED.indexOf(p) >= 0) return p;
    var s = localStorage.getItem("site_lang");
    if (s && SUPPORTED.indexOf(s) >= 0) return s;
    return DEFAULT; // 默认中文
  }

  var current = detect();
  var pendingLng = null;

  var api = {
    lng: current,
    ready: false,
    t: function (k, opts) { return ZH[k] || (opts && opts.defaultValue) || k; }, // 预初始化兜底（中文）
    changeLanguage: function (lng) { lng = lng; }                              // 预初始化占位
  };
  window.i18n = api;

  function applyDOM() {
    if (!window.i18next) return;
    document.querySelectorAll("[data-i18n]").forEach(function (el) {
      var k = el.getAttribute("data-i18n");
      var tr = window.i18next.t(k);
      if (tr && tr !== k) el.textContent = tr; // 仅在有真实译文时覆盖，缺失则保留原始中文
    });
    document.querySelectorAll("[data-i18n-attr]").forEach(function (el) {
      el.getAttribute("data-i18n-attr").split(";").forEach(function (pair) {
        var kv = pair.split(":");
        if (kv.length === 2) { var tr = window.i18next.t(kv[1]); if (tr && tr !== kv[1]) el.setAttribute(kv[0], tr); }
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
    var resources = { zh: { translation: ZH } }; // zh 始终有内联兜底
    SUPPORTED.forEach(function (l) {
      if (l !== DEFAULT && bundles[l]) resources[l] = { translation: bundles[l] };
    });
    window.i18next.init({
      lng: current,
      fallbackLng: DEFAULT,
      supportedLngs: SUPPORTED,
      resources: resources,
      interpolation: { escapeValue: false },
      returnEmptyString: false,
      // 关键：语言包使用「扁平点分 key」（如 "home.resetView"），
      // 必须关闭 i18next 默认的 '.' 嵌套分隔与 ':' 命名空间分隔，
      // 否则 t('home.resetView') 会被当成 home→resetView 嵌套查找而找不到，
      // 进而返回 key 本身，导致「切换语言无效 / 显示 key」。
      keySeparator: false,
      nsSeparator: false
    }, function () {
      api.ready = true;
      api.t = function (k, opts) { return window.i18next.t(k, opts); };
      applyDOM();
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
    localStorage.setItem("site_lang", lng);
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
})();
