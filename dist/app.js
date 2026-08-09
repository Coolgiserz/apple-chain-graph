/* app.js — 整合 SPA 的视图路由壳（由 build_app.py 注入到 dist/apple_supply_chain_app.html）
 *
 * 图谱渲染复用 templates/graph_engine.js（共享引擎），本文件只负责：
 *   - App 视图注册 / hash 路由（graph ↔ report 视图内切换，深链可分享）
 *   - 把报告 / 地图的跨页跳转链接注入共享引擎（reportLink / mapLink）
 *   - 图谱视图在激活时才启动引擎（隐藏 canvas 获得真实尺寸后再跑物理模拟）
 */
const App = (function () {
  const views = {};
  let current = null;
  function register(v) {
    views[v.id] = v;
    v.el = document.getElementById("view-" + v.id);
  }
  function show(id, params) {
    const v = views[id];
    if (!v) return;
    if (current && current.id !== id) {
      current.el.classList.remove("active");
      if (current.deactivate) current.deactivate();
    }
    v.el.classList.add("active");
    document.querySelectorAll(".tab").forEach(b => b.classList.toggle("active", b.dataset.view === id));
    current = v;
    if (v.activate) v.activate(params || null);
    const hash = "#/" + id + (params ? "/" + params : "");
    if (location.hash !== hash) history.replaceState(null, "", hash);
  }
  function resolve() {
    const raw = (location.hash || "#/graph").replace(/^#\//, "");
    const parts = raw.split("/");
    show(parts[0] || "graph", parts.slice(1).join("/") || null);
  }
  function init() {
    document.querySelectorAll("[data-view]").forEach(b =>
      b.addEventListener("click", () => show(b.dataset.view)));
    document.addEventListener("click", e => {
      const el = e.target.closest("[data-jump]");
      if (!el) return;
      const seg = el.dataset.jump.split(":");
      show(seg[0], seg.slice(1).join(":") || null);
    });
    window.addEventListener("hashchange", resolve);
    resolve();
  }
  return { register, show, init, get current() { return current; } };
})();

/* 复用共享图谱引擎：注入报告 / 地图跨页链接（SPA 内地图用真实相对路径 ../tools/...） */
const graphApi = window.GraphEngine.init({
  reportLink: function (n, sec) {
    const label = n.type === "Product" ? "型号" : n.type === "Component" ? "零部件" : "供应商";
    return "<a class='lk' data-jump='report:" + sec + "'>在报告中查看该" + label + " →</a>";
  },
  mapLink: function (n) {
    return "<a class='lk' href='../tools/visualizations/supplier_geo.html?supplier=" + window.GraphEngine.esc(n.id) + "' target='_blank' style='color:#6ea0ff'>在地图中查看 →</a>";
  }
});

const graphView = {
  id: "graph",
  activate(params) {
    graphApi.start();
    if (params) graphApi.focus(params);
  },
  deactivate() { graphApi.stop(); }
};

const reportView = {
  id: "report",
  activate(params) {
    if (params && params.indexOf("sec-") === 0) {
      const el = document.getElementById(params);
      if (el) setTimeout(() => el.scrollIntoView({ behavior: "smooth", block: "start" }), 30);
    }
  },
  deactivate() {}
};

App.register(graphView);
App.register(reportView);
App.init();
