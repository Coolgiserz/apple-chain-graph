// ESLint 9 扁平配置（flat config）。
// 仅做「语法 + 未定义变量」门禁，不强制代码风格，便于团队渐进接入而不与既有代码冲突。
// 浏览器全局由 vendored i18next / 内联脚本提供，统一在此声明。
const browserGlobals = {
  window: "readonly",
  document: "readonly",
  // 画布配色从 :root 读令牌（src/engine/util.js），见 tests/test_js_lint.py 的 L2 契约锁
  getComputedStyle: "readonly",
  fetch: "readonly",
  Intl: "readonly",
  location: "readonly",
  history: "readonly",
  localStorage: "readonly",
  navigator: "readonly",
  console: "readonly",
  CustomEvent: "readonly",
  requestAnimationFrame: "readonly",
  cancelAnimationFrame: "readonly",
  setTimeout: "readonly",
  clearTimeout: "readonly",
  URL: "readonly",
  URLSearchParams: "readonly",
  Set: "readonly",
  Map: "readonly",
  WeakMap: "readonly",
  Math: "readonly",
  JSON: "readonly",
  Object: "readonly",
  Array: "readonly",
  String: "readonly",
  Number: "readonly",
  Boolean: "readonly",
  Symbol: "readonly",
  Promise: "readonly",
  parseFloat: "readonly",
  parseInt: "readonly",
  isNaN: "readonly",
};

export default [
  {
    files: ["src/**/*.js"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      globals: browserGlobals,
    },
    rules: {
      "no-undef": "error",
    },
  },
];
