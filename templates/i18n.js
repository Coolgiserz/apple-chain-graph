/*! 站点国际化引导（基于 i18next + i18next-http-backend，零构建、纯静态）
 *  约定：
 *   - 语言包放在仓库根 locales/<lng>.json（zh 源，en/fr/ja 待填/已部分）
 *   - 静态文本：元素加 data-i18n="key"（textContent）或 data-i18n-attr="placeholder:key"（属性）
 *   - JS 动态文本：调用 window.i18n.t("key")
 *   - 切换语言：window.i18n.changeLanguage("en") —— 记忆到 localStorage + ?lang=
 *   - 语言加载完成/切换后会派发 document 事件：i18n:ready / i18n:changed（供动态面板重渲染）
 *
 *  默认语言策略：显式选择（?lang= 或 localStorage）优先；否则一律中文（不按浏览器
 *  语言自动切换，避免英文浏览器默认显示英文让用户困惑）。
 */
(function () {
  var SUPPORTED = ["zh", "en", "fr", "ja"];
  var DEFAULT = "zh";
  var ASSET_VERSION = "20260809b"; // 资源版本号：改动语言包/引导脚本后递增，破除浏览器缓存

  function detect() {
    var p = new URLSearchParams(location.search).get("lang");
    if (p && SUPPORTED.indexOf(p) >= 0) return p;
    var s = localStorage.getItem("site_lang");
    if (s && SUPPORTED.indexOf(s) >= 0) return s;
    return DEFAULT; // 默认中文
  }

  // 语言包相对路径：按当前页面深度推导（首页/ dist/ / tools/ 三种 root）
  function basePath() {
    var p = location.pathname;
    if (p.indexOf("/tools/") >= 0) return "../../";
    if (p.indexOf("/dist/") >= 0) return "../";
    return "";
  }

  var current = detect();
  var pendingLng = null; // i18n 未就绪时用户已切换的语言，就绪后补应用

  var api = {
    lng: current,
    ready: false,
    t: function (k, opts) { return (opts && opts.defaultValue) || k; }, // 预初始化兜底
    changeLanguage: function (lng) { lng = lng; }                       // 预初始化占位
  };
  window.i18n = api;

  function applyDOM() {
    if (!window.i18next) return;
    document.querySelectorAll("[data-i18n]").forEach(function (el) {
      el.textContent = window.i18next.t(el.getAttribute("data-i18n"));
    });
    document.querySelectorAll("[data-i18n-attr]").forEach(function (el) {
      el.getAttribute("data-i18n-attr").split(";").forEach(function (pair) {
        var kv = pair.split(":");
        if (kv.length === 2) el.setAttribute(kv[0], window.i18next.t(kv[1]));
      });
    });
  }

  function init() {
    if (!window.i18next || !window.i18nextHttpBackend) {
      console.warn("[i18n] 库未加载，跳过国际化");
      return;
    }
    window.i18next.use(window.i18nextHttpBackend).init({
      lng: current,
      fallbackLng: DEFAULT,
      supportedLngs: SUPPORTED,
      backend: { loadPath: basePath() + "locales/{{lng}}.json?v=" + ASSET_VERSION },
      interpolation: { escapeValue: false },
      returnEmptyString: false
    }, function () {
      api.ready = true;
      api.t = function (k, opts) { return window.i18next.t(k, opts); };
      applyDOM();
      var sel = document.getElementById("langSwitch");
      if (sel) sel.value = current;
      // 若未就绪期间用户已切换语言，这里补应用
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
