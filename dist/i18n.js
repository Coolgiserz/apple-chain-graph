/*! 站点国际化引导（基于 i18next + i18next-http-backend，零构建、纯静态）
 *  约定：
 *   - 语言包放在仓库根 locales/<lng>.json（zh 源，en/fr/ja 待填/已部分）
 *   - 静态文本：元素加 data-i18n="key"（textContent）或 data-i18n-attr="placeholder:key"（属性）
 *   - JS 动态文本：调用 window.i18n.t("key")
 *   - 切换语言：window.i18n.changeLanguage("en") —— 记忆到 localStorage + ?lang=
 *   - 语言加载完成/切换后会派发 document 事件：i18n:ready / i18n:changed（供动态面板重渲染）
 */
(function () {
  var SUPPORTED = ["zh", "en", "fr", "ja"];
  var DEFAULT = "zh";

  function detect() {
    var p = new URLSearchParams(location.search).get("lang");
    if (p && SUPPORTED.indexOf(p) >= 0) return p;
    var s = localStorage.getItem("site_lang");
    if (s && SUPPORTED.indexOf(s) >= 0) return s;
    var nav = (navigator.language || "zh").slice(0, 2);
    return SUPPORTED.indexOf(nav) >= 0 ? nav : DEFAULT;
  }

  // 语言包相对路径：按当前页面深度推导（首页/ dist/ / tools/ 三种 root）
  function basePath() {
    var p = location.pathname;
    if (p.indexOf("/tools/") >= 0) return "../../";
    if (p.indexOf("/dist/") >= 0) return "../";
    return "";
  }

  var current = detect();

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
      backend: { loadPath: basePath() + "locales/{{lng}}.json" },
      interpolation: { escapeValue: false },
      returnEmptyString: false
    }, function () {
      api.ready = true;
      api.t = function (k, opts) { return window.i18next.t(k, opts); };
      applyDOM();
      var sel = document.getElementById("langSwitch");
      if (sel) sel.value = current;
      document.dispatchEvent(new CustomEvent("i18n:ready"));
    });
  }

  api.changeLanguage = function (lng) {
    if (SUPPORTED.indexOf(lng) < 0) lng = DEFAULT;
    current = lng;
    localStorage.setItem("site_lang", lng);
    var u = new URL(location.href);
    u.searchParams.set("lang", lng);
    history.replaceState(null, "", u);
    var sel = document.getElementById("langSwitch");
    if (sel) sel.value = lng;
    if (window.i18next && api.ready) {
      window.i18next.changeLanguage(lng, function () {
        applyDOM();
        document.dispatchEvent(new CustomEvent("i18n:changed", { detail: { lng: lng } }));
      });
    }
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
