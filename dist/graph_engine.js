/* =============================================================================
 * graph_engine.js — 共享力导向供应链图谱引擎（单一事实来源）
 *
 * 被两个页面复用：
 *   - 首页图谱（根目录 index.html）
 *   - 整合 SPA（dist/apple_supply_chain_app.html）
 *
 * 设计要点：
 *   - 不自动启动：页面先设置 window.SUPPLY_DATA，再调用 GraphEngine.init(opts)
 *     拿到 api，随后调用 api.start()（首页立即启动；SPA 在视图激活时再启动，
 *     以保证隐藏 canvas 在可见时才测量真实尺寸）。
 *   - 跨页跳转链接（报告 / 地图）由 opts.reportLink(n) / opts.mapLink(n) 注入，
 *     让引擎保持页面无关，避免再次出现"同一段前端代码在两处硬编码"。
 *   - 暴露 init / start / focus / reheat / resize / stop / esc，便于单测与复用。
 * ===========================================================================*/
(function (global) {
  "use strict";

  var COLORS = { Product: "#2f6fed", Component: "#f59e0b", Supplier: "#10b981" };
  var BASE_R = { Product: 11, Component: 7, Supplier: 6 };

  // —— 模块级状态（init 时填充）————————————————————————————————————————————
  var nodes = [], links = [], adj = {}, idMap = {};
  var cv, ctx, view = { ox: 0, oy: 0, scale: 1 };
  var alpha = 1, running = false, animating = false, rafId = null, canvasReady = false;
  var selected = null, hover = null, dragNode = null, panning = false, last = { x: 0, y: 0 }, moved = false;
  var reportLink = null, mapLink = null;
  var pendingFocus = null;   // 布局未就绪时暂缓居中，待首帧自愈后再执行

  var ALPHA_MIN = 0.005, ALPHA_DEC = 0.008;
  function W() { return (cv ? cv.clientWidth : 0) || global.innerWidth; }
  function H() { return (cv ? cv.clientHeight : 0) || global.innerHeight; }

  // —— 数据装配 ————————————————————————————————————————————————————————————
  function addNode(n, type) {
    var o = Object.assign({ type: type, degree: 0 }, n);
    o.id = n.id; o._key = type[0] + ":" + n.id;
    idMap[o._key] = o; nodes.push(o);
  }
  function addLink(t, from, to, extra) {
    var a = idMap["P:" + from] || idMap["C:" + from] || idMap["S:" + from];
    var b = idMap["P:" + to] || idMap["C:" + to] || idMap["S:" + to];
    if (a && b) { var l = { type: t, a: a, b: b }; if (extra) Object.assign(l, extra); links.push(l); a.degree++; b.degree++; }
  }
  function build() {
    var DATA = global.SUPPLY_DATA;
    idMap = {}; nodes = []; links = [];
    DATA.nodes.products.forEach(function (p) { addNode(p, "Product"); });
    DATA.nodes.components.forEach(function (c) { addNode(c, "Component"); });
    DATA.nodes.suppliers.forEach(function (s) { addNode(s, "Supplier"); });
    DATA.edges.uses_component.forEach(function (e) { addLink("USES", e.from, e.to); });
    DATA.edges.supplied_by.forEach(function (e) { addLink("SUPPLIES", e.from, e.to, { share: e.share, note: e.note }); });
    DATA.edges.assembled_by.forEach(function (e) { addLink("ASSEMBLES", e.from, e.to); });
    adj = {}; nodes.forEach(function (n) { adj[n._key] = []; });
    links.forEach(function (l) {
      adj[l.a._key].push({ dir: "out", other: l.b, link: l });
      adj[l.b._key].push({ dir: "in", other: l.a, link: l });
    });
    // 初始环形布局
    nodes.forEach(function (n, i) {
      var ang = (i / nodes.length) * Math.PI * 2, r = 200 + (i % 7) * 40;
      n.x = W() / 2 + Math.cos(ang) * r + (Math.random() - 0.5) * 30;
      n.y = H() / 2 + Math.sin(ang) * r + (Math.random() - 0.5) * 30;
      n.vx = 0; n.vy = 0;
    });
    // 产品线下拉
    var lines = Array.from(new Set(DATA.nodes.products.map(function (p) { return p.product_line; })));
    var sel = document.getElementById("line");
    if (sel) lines.forEach(function (l) {
      var o = document.createElement("option"); o.value = l; o.textContent = l; sel.appendChild(o);
    });
  }

  // —— 可见集合 / 物理 / 渲染 ————————————————————————————————————————————————
  function visibleSet() {
    var q = document.getElementById("q").value.trim().toLowerCase();
    var cbP = document.getElementById("cbP").checked,
        cbC = document.getElementById("cbC").checked,
        cbS = document.getElementById("cbS").checked;
    var line = document.getElementById("line").value;
    var set = new Set();
    for (var i = 0; i < nodes.length; i++) {
      var n = nodes[i];
      if (n.type === "Product" && !cbP) continue;
      if (n.type === "Component" && !cbC) continue;
      if (n.type === "Supplier" && !cbS) continue;
      if (n.type === "Product" && line && n.product_line !== line) continue;
      set.add(n._key);
    }
    if (line) {
      var keep = new Set(set);
      for (var j = 0; j < nodes.length; j++) {
        var m = nodes[j]; if (m.type === "Product") continue;
        var touch = false;
        var es = adj[m._key];
        for (var k = 0; k < es.length; k++) { if (keep.has(es[k].other._key)) { touch = true; break; } }
        if (!touch) set.delete(m._key);
      }
    }
    if (q) {
      var match = new Set();
      for (var a = 0; a < nodes.length; a++) {
        var nn = nodes[a];
        if (!set.has(nn._key)) continue;
        var hay = (nn.name + " " + (nn.english_name || "") + " " + nn.id + " " + (nn.short_name || "") + " " + (nn.alias || "")).toLowerCase();
        if (hay.indexOf(q) !== -1) match.add(nn._key);
      }
      var keep2 = new Set(match);
      match.forEach(function (key) {
        adj[key].forEach(function (e) { keep2.add(e.other._key); });
      });
      return keep2;
    }
    return set;
  }

  // 返回当前筛选条件下「可见」的节点对象数组（与图谱渲染共用同一 visibleSet）。
  // 供首页侧边表格面板复用，实现「图 ↔ 表」联动：表格里看到的正是图谱当前筛出的企业。
  function visibleNodes() {
    var set = visibleSet();
    return nodes.filter(function (n) { return set.has(n._key); });
  }

  function physics(vis) {
    if (alpha < ALPHA_MIN) return;
    var arr = nodes.filter(function (n) { return vis.has(n._key); });
    arr.forEach(function (n) { n.fx = 0; n.fy = 0; });
    for (var i = 0; i < arr.length; i++) for (var j = i + 1; j < arr.length; j++) {
      var a = arr[i], b = arr[j];
      var dx = a.x - b.x, dy = a.y - b.y;
      var d2 = dx * dx + dy * dy + 0.01, d = Math.sqrt(d2);
      var f = 1800 / d2, fx = dx / d * f, fy = dy / d * f;
      a.fx += fx; a.fy += fy; b.fx -= fx; b.fy -= fy;
    }
    links.forEach(function (l) {
      if (!vis.has(l.a._key) || !vis.has(l.b._key)) return;
      var dx = l.b.x - l.a.x, dy = l.b.y - l.a.y;
      var d = Math.sqrt(dx * dx + dy * dy) + 0.01;
      var f = (d - 90) * 0.03, fx = dx / d * f, fy = dy / d * f;
      l.a.fx += fx; l.a.fy += fy; l.b.fx -= fx; l.b.fy -= fy;
    });
    arr.forEach(function (n) {
      n.fx += (W() / 2 - n.x) * 0.001; n.fy += (H() / 2 - n.y) * 0.001;
      n.vx = (n.vx + n.fx * alpha) * 0.9; n.vy = (n.vy + n.fy * alpha) * 0.9;
      var sp = Math.hypot(n.vx, n.vy);
      if (sp > 18) { n.vx *= 18 / sp; n.vy *= 18 / sp; }
      if (!n.fixed) { n.x += n.vx; n.y += n.vy; }
    });
    alpha = Math.max(0, alpha - ALPHA_DEC);
  }

  // 同步画布后备尺寸与元素实际 CSS 尺寸；尺寸无变化或布局未就绪时跳过。
  // 返回 true 表示本次确实改变了尺寸（用于触发重绘）。
  function syncSize() {
    if (!cv) return false;
    var dpr = global.devicePixelRatio || 1;
    var w = cv.clientWidth || (cv.parentNode && cv.parentNode.clientWidth) || global.innerWidth;
    var h = cv.clientHeight || (cv.parentNode && cv.parentNode.clientHeight) || global.innerHeight;
    if (!w || !h) return false;                       // 布局尚未就绪：保持原样，等下一帧自愈
    var bw = Math.round(w * dpr), bh = Math.round(h * dpr);
    if (cv.width === bw && cv.height === bh) return false;
    cv.width = bw; cv.height = bh;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    canvasReady = true;
    return true;
  }
  function resize() {
    var changed = syncSize();
    if (running) kick();                              // 尺寸变化后重启循环（或借已有循环重绘）
    else if (changed) draw(visibleSet());             // 已停止时至少重绘一次当前帧
  }

  function label(n) { return n.name || n.english_name || n.id; }
  function esc(s) { return String(s).replace(/[&<>]/g, function (c) { return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]); }); }
  function nm(t, id) { var o = idMap[t + ":" + id]; return o ? label(o) : id; }

  function draw(vis) {
    syncSize();                                      // 每次绘制前保证后备尺寸正确（首屏布局晚到 / 窗口缩放自愈）
    if (pendingFocus && W() && H()) { var nf = pendingFocus; pendingFocus = null; applyFocus(nf); }
    ctx.clearRect(0, 0, W(), H());
    var sel = selected ? selected._key : null;
    var nb = sel ? new Set([sel].concat(adj[sel].map(function (e) { return e.other._key; }))) : null;
    ctx.save(); ctx.translate(view.ox, view.oy); ctx.scale(view.scale, view.scale);
    links.forEach(function (l) {
      if (!vis.has(l.a._key) || !vis.has(l.b._key)) return;
      var hot = nb && nb.has(l.a._key) && nb.has(l.b._key);
      ctx.strokeStyle = hot ? "rgba(150,180,255,.9)" : (nb ? "rgba(120,135,170,.08)" : "rgba(120,135,170,.22)");
      ctx.lineWidth = hot ? 1.6 : 1;
      ctx.beginPath(); ctx.moveTo(l.a.x, l.a.y); ctx.lineTo(l.b.x, l.b.y); ctx.stroke();
    });
    nodes.forEach(function (n) {
      if (!vis.has(n._key)) return;
      var r = BASE_R[n.type] + Math.min(n.degree, 12) * 0.35;
      var dim = nb && !nb.has(n._key);
      ctx.globalAlpha = dim ? 0.18 : 1;
      ctx.beginPath(); ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
      ctx.fillStyle = COLORS[n.type]; ctx.fill();
      ctx.lineWidth = (selected === n) ? 3 : 1.2;
      ctx.strokeStyle = (selected === n) ? "#fff" : "rgba(255,255,255,.35)";
      ctx.stroke();
      if (view.scale > 0.7 || n.type === "Product" || selected === n || hover === n) {
        ctx.globalAlpha = dim ? 0.25 : 1;
        ctx.fillStyle = "#dfe7f7"; ctx.font = "11px sans-serif"; ctx.textAlign = "center";
        ctx.fillText(label(n), n.x, n.y + r + 12);
      }
      ctx.globalAlpha = 1;
    });
    ctx.restore();
  }

  // —— 交互 ————————————————————————————————————————————————————————————————
  function toWorld(px, py) { return { x: (px - view.ox) / view.scale, y: (py - view.oy) / view.scale }; }
  function pick(px, py) {
    var w = toWorld(px, py), best = null, bd = 1e9, vis = visibleSet();
    for (var i = 0; i < nodes.length; i++) {
      var n = nodes[i]; if (!vis.has(n._key)) continue;
      var dx = n.x - w.x, dy = n.y - w.y, d = dx * dx + dy * dy;
      var r = BASE_R[n.type] + Math.min(n.degree, 12) * 0.35 + 4;
      if (d < r * r && d < bd) { best = n; bd = d; }
    }
    return best;
  }
  function selectNode(n) {
    selected = n;
    var panel = document.getElementById("panel");
    if (!n) { if (panel) panel.style.display = "none"; return; }
    renderPanel(n);
    if (panel) panel.style.display = "block";
  }
  function renderPanel(n) {
    var p = document.getElementById("pbody"); if (!p) return;
    var col = COLORS[n.type];
    var h = "<h3>" + esc(n.name || n.id) + "</h3><div class='sub'>" + esc(n.english_name || "") + "</div>";
    h += "<span class='tag' style='background:" + col + "22;color:" + col + ";border:1px solid " + col + "'>" + n.type + "</span>";
    if (n.type === "Product" && n.product_line) h += "<span class='tag' style='background:#2a3450;color:#cfe0ff'>" + esc(n.product_line) + "</span>";
    h += "<dl>";
    var fields = n.type === "Product"
      ? [["发布时间", n.release_date], ["状态", n.status], ["起售价(USD)", n.price_usd ? ("$" + n.price_usd) : ""], ["SoC", n.soc], ["显示屏", n.display], ["别名", n.alias], ["代工", (n.assembly || []).map(function (id) { return nm("S", id); }).join("、")]]
      : n.type === "Component"
        ? [["类别", n.category], ["子类", n.subcategory]]
        : [["简称", n.short_name], ["国家/地区", n.country], ["区域", n.region], ["类别", n.category], ["层级", n.tier]];
    fields.forEach(function (kv) { if (kv[1]) h += "<dt>" + kv[0] + "</dt><dd>" + esc(String(kv[1])) + "</dd>"; });
    h += "</dl>";
    var out = [];
    adj[n._key].forEach(function (e) { if (e.dir === "out") out.push(e); });
    if (out.length) {
      h += "<dt style='margin-top:12px;color:#9fb0d0;font-size:11px'>关联（" + out.length + "）</dt><dd><ul>";
      out.forEach(function (e) {
        var extra = e.link.share ? " · 份额 " + e.link.share + "%" : "";
        h += "<li><b>" + e.link.type + "</b> → " + esc(label(e.other)) + extra + "</li>";
      });
      h += "</ul></dd>";
    }
    // 跨页跳转：报告 / 地图（由页面注入，保持引擎无关）
    var sec = n.type === "Product" ? "sec-products" : n.type === "Component" ? "sec-components" : "sec-suppliers";
    if (reportLink) h += "<p style='margin-top:10px'>" + reportLink(n, sec) + "</p>";
    if (mapLink && n.type === "Supplier") h += "<p style='margin-top:6px'>" + mapLink(n) + "</p>";
    p.innerHTML = h;
  }

  function bindEvents() {
    cv.addEventListener("mousedown", function (e) {
      moved = false; last = { x: e.clientX, y: e.clientY };
      var n = pick(e.clientX, e.clientY);
      if (n) { dragNode = n; n.fixed = true; reheat(0.3); }
      else { panning = true; cv.classList.add("dragging"); }
      kick();
    });
    cv.addEventListener("mousemove", function (e) {
      var dx = e.clientX - last.x, dy = e.clientY - last.y;
      if (Math.abs(dx) + Math.abs(dy) > 3) moved = true;
      if (dragNode) { var w = toWorld(e.clientX, e.clientY); dragNode.x = w.x; dragNode.y = w.y; dragNode.vx = 0; dragNode.vy = 0; }
      else if (panning) { view.ox += dx; view.oy += dy; }
      else { hover = pick(e.clientX, e.clientY); cv.style.cursor = hover ? "pointer" : "grab"; }
      last = { x: e.clientX, y: e.clientY };
      kick();
    });
    global.addEventListener("mouseup", function (e) {
      if (dragNode) { dragNode.fixed = false; dragNode = null; }
      panning = false; cv.classList.remove("dragging");
      if (!moved) { var n = pick(e.clientX, e.clientY); selectNode(n); }
      kick();
    });
    cv.addEventListener("wheel", function (e) {
      e.preventDefault();
      var factor = e.deltaY < 0 ? 1.1 : 0.9, mx = e.clientX, my = e.clientY;
      var wx = (mx - view.ox) / view.scale, wy = (my - view.oy) / view.scale;
      view.scale *= factor; view.ox = mx - wx * view.scale; view.oy = my - wy * view.scale;
      kick();
    }, { passive: false });
    global.addEventListener("resize", resize);

    var pc = document.getElementById("pc"); if (pc) pc.onclick = function () { selectNode(null); kick(); };
    var reset = document.getElementById("reset");
    if (reset) reset.onclick = function () {
      view = { ox: 0, oy: 0, scale: 1 }; selectNode(null);
      var q = document.getElementById("q"); if (q) q.value = "";
      document.getElementById("cbP").checked = document.getElementById("cbC").checked = document.getElementById("cbS").checked = true;
      var line = document.getElementById("line"); if (line) line.value = "";
      reheat(1);
    };
    ["q", "cbP", "cbC", "cbS", "line"].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.addEventListener("input", function () { if (id !== "q") selectNode(null); reheat(0.7); });
    });
  }

  // 仅在需要重绘时启动 rAF 循环；模拟静止且无交互时循环自动停止，
  // 避免对全屏（含 retina）画布做无谓的 60fps 持续重绘（这是此前"非常卡"的根因）。
  function kick() {
    if (!running || animating) return;
    animating = true;
    rafId = global.requestAnimationFrame(loop);
  }
  function loop() {
    if (!running) { animating = false; return; }
    var vis = visibleSet();                 // 每帧只算一次可见集，physics 与 draw 共用
    physics(vis);
    draw(vis);
    // 静止 + 无拖拽/平移 + 画布已就绪 -> 停止循环（画布保留最后一帧），等下次交互/resize 再 kick
    if (alpha < ALPHA_MIN && !dragNode && !panning && canvasReady) {
      animating = false;
      return;
    }
    rafId = global.requestAnimationFrame(loop);
  }
  function reheat(a) { alpha = Math.max(alpha, (a == null ? 0.5 : a)); kick(); }
  function applyFocus(n) {
    selected = n; reheat(1);
    view.ox = W() / 2 - n.x * view.scale; view.oy = H() / 2 - n.y * view.scale;
    renderPanel(n);
    var panel = document.getElementById("panel"); if (panel) panel.style.display = "block";
  }
  function focus(key) {
    var n = idMap[key]; if (!n) return;
    if (!W() || !H()) { pendingFocus = n; return; }   // 画布尚未量到尺寸，等 draw() 自愈后再居中
    applyFocus(n);
  }

  // —— 对外 API ————————————————————————————————————————————————————————————
  function init(opts) {
    opts = opts || {};
    reportLink = opts.reportLink || null;
    mapLink = opts.mapLink || null;
    cv = document.getElementById("cv");
    if (!cv) throw new Error("GraphEngine.init: #cv not found");
    ctx = cv.getContext("2d");
    build();
    bindEvents();
    return api;
  }
  var api = {
    init: init,
    start: function () { if (running) return; running = true; syncSize(); reheat(1); },
    stop: function () { running = false; animating = false; if (rafId) global.cancelAnimationFrame(rafId); },
    focus: focus,
    reheat: reheat,
    resize: resize,
    esc: esc,
    visibleNodes: visibleNodes
  };
  global.GraphEngine = api;
})(window);
