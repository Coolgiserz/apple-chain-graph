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
  var selected = null, hover = null, dragNode = null, panning = false, last = { x: 0, y: 0 };
  var downNode = null, downX = 0, downY = 0;   // mousedown 时的候选节点与起始位置
  var pointerDown = false;                     // 本次手势是否已按下鼠标（move 必须先按下才可能拖拽）
  var touchActive = false, pinching = false, pinchDist = 0, pinchScale = 1;  // 触摸手势状态（移动端）
  var DRAG_THRESH = 5;                         // 按下后位移超过该值(px)才视为拖拽/平移，否则按「点击」处理
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
  // 国际化：缺失 key 时回退到中文源（zh 为 fallbackLng），避免显示原始 key
  function i18nText(k) { return (window.i18n && window.i18n.ready) ? window.i18n.t(k) : k; }
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
  // 把鼠标事件的坐标（viewport 坐标）换算成画布内部坐标：必须减去画布自身的
  // 偏移（导航栏高度 52px、侧边面板打开时左侧 384px 等），否则点选/拖拽会整体偏移，
  // 表现为「点不到节点、一点就平移画布」。
  function localXY(px, py) { var r = cv.getBoundingClientRect(); return { x: px - r.left, y: py - r.top }; }
  function toWorld(px, py) { var l = localXY(px, py); return { x: (l.x - view.ox) / view.scale, y: (l.y - view.oy) / view.scale }; }
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
  // 数据集里的枚举值（region / category / country / tier / status / product_line / subcategory）
  // 经 i18n 翻译：raw -> <domain>.<key> -> 对应语言文本。映射（raw->键）单一来源是
  // window.I18N_ENUM_MAP（由 build_viewer.py 从 locales/enum_map.json 内联），译文在 locales/*.json，
  // 运行时由 i18n.js 解析——不在 JS 里硬编码任何译文。
  function i18nVal(domain, raw) {
    if (raw === undefined || raw === null || raw === "") return "";
    var key = (window.I18N_ENUM_MAP && window.I18N_ENUM_MAP[domain] && window.I18N_ENUM_MAP[domain][String(raw)]) || null;
    return key ? i18nText(domain + "." + key) : String(raw);
  }
  function renderPanel(n) {
    var p = document.getElementById("pbody"); if (!p) return;
    var col = COLORS[n.type];
    var h = "<h3>" + esc(n.name || n.id) + "</h3><div class='sub'>" + esc(n.english_name || "") + "</div>";
    h += "<span class='tag' style='background:" + col + "22;color:" + col + ";border:1px solid " + col + "'>" + n.type + "</span>";
    if (n.type === "Product" && n.product_line) h += "<span class='tag' style='background:#2a3450;color:#cfe0ff'>" + esc(i18nVal("product_line", n.product_line)) + "</span>";
    h += "<dl>";
    function fieldRow(k, v) {
      var val = v;
      if (k === "status") val = i18nVal("status", v);
      else if (k === "country") val = i18nVal("country", v);
      else if (k === "region") val = i18nVal("region", v);
      else if (k === "category") val = i18nVal("category", v);
      else if (k === "subcategory") val = i18nVal("subcategory", v);
      else if (k === "tier") val = i18nVal("tier", v);
      else if (k === "product_line") val = i18nVal("product_line", v);
      return [i18nText("field." + k), val];
    }
    var assemblyTxt = (n.assembly || []).map(function (id) { return nm("S", id); }).join("、");
    var fields = n.type === "Product"
      ? [fieldRow("release_date", n.release_date), fieldRow("status", n.status), fieldRow("price", n.price_usd ? ("$" + n.price_usd) : ""), fieldRow("soc", n.soc), fieldRow("display", n.display), fieldRow("alias", n.alias), fieldRow("assembly", assemblyTxt)]
      : n.type === "Component"
        ? [fieldRow("category", n.category), fieldRow("subcategory", n.subcategory)]
        : [fieldRow("short_name", n.short_name), fieldRow("country", n.country), fieldRow("region", n.region), fieldRow("category", n.category), fieldRow("tier", n.tier)];
    fields.forEach(function (kv) { if (kv[1]) h += "<dt>" + kv[0] + "</dt><dd>" + esc(String(kv[1])) + "</dd>"; });
    h += "</dl>";
    var out = [];
    adj[n._key].forEach(function (e) { if (e.dir === "out") out.push(e); });
    if (out.length) {
      // 「关联」邻居节点可点击：点击即聚焦该邻居（同步图谱高亮 + 右侧信息框）。
      h += "<dt style='margin-top:12px;color:#9fb0d0;font-size:11px'>" + i18nText("panel.rel") + "（" + out.length + " · " + i18nText("panel.relHint") + "）</dt><dd><ul>";
      out.forEach(function (e) {
        var extra = e.link.share ? " · 份额 " + e.link.share + "%" : "";
        h += "<li class='rel' data-key='" + esc(e.other._key) + "' title='点击聚焦：" + esc(label(e.other)) + "'>"
          + "<b>" + e.link.type + "</b> → " + esc(label(e.other)) + extra + "</li>";
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
      downX = e.clientX; downY = e.clientY;
      downNode = pick(e.clientX, e.clientY);   // 仅记录候选，不立即进入拖拽/平移
      pointerDown = true;
      kick();
    });
    cv.addEventListener("mousemove", function (e) {
      if (dragNode) {                            // 正在拖动节点
        var w = toWorld(e.clientX, e.clientY); dragNode.x = w.x; dragNode.y = w.y; dragNode.vx = 0; dragNode.vy = 0;
      } else if (panning) {                      // 正在平移画布
        view.ox += e.clientX - last.x; view.oy += e.clientY - last.y;
        last = { x: e.clientX, y: e.clientY };
      } else if (pointerDown) {                  // 已按下：越过阈值才进入拖拽，否则只是 hover 反馈
        var dx = e.clientX - downX, dy = e.clientY - downY;
        if (Math.abs(dx) + Math.abs(dy) > DRAG_THRESH) {
          if (downNode) { dragNode = downNode; dragNode.fixed = true; reheat(0.3);
            var w0 = toWorld(e.clientX, e.clientY); dragNode.x = w0.x; dragNode.y = w0.y; dragNode.vx = 0; dragNode.vy = 0; }
          else { panning = true; cv.classList.add("dragging"); }
          last = { x: e.clientX, y: e.clientY };
        } else {
          hover = pick(e.clientX, e.clientY); cv.style.cursor = hover ? "pointer" : "grab";
        }
      } else {                                   // 未按下：纯浏览，绝不拖拽/平移（只更新 hover 光标）
        hover = pick(e.clientX, e.clientY); cv.style.cursor = hover ? "pointer" : "grab";
      }
      kick();
    });
    global.addEventListener("mouseup", function (e) {
      var wasClick = !dragNode && !panning;      // 按下后全程未越界 → 这是一次点击，而非拖拽
      if (dragNode) { dragNode.fixed = false; dragNode = null; }
      if (panning) { panning = false; cv.classList.remove("dragging"); }
      if (wasClick) selectNode(downNode || null);   // 点击节点看详情；点击空白处取消选中
      downNode = null; pointerDown = false;
      kick();
    });
    cv.addEventListener("wheel", function (e) {
      e.preventDefault();
      var l = localXY(e.clientX, e.clientY);      // 同样需扣除画布偏移，缩放才以光标为锚点
      var factor = e.deltaY < 0 ? 1.1 : 0.9;
      var wx = (l.x - view.ox) / view.scale, wy = (l.y - view.oy) / view.scale;
      view.scale *= factor; view.ox = l.x - wx * view.scale; view.oy = l.y - wy * view.scale;
      kick();
    }, { passive: false });

    // —— 触摸支持（移动端）：单指拖拽/点击节点，双指 pinch 缩放 ——————————————————
    function touchDist(e) { var a = e.touches[0], b = e.touches[1]; return Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY); }
    function touchMid(e) { var a = e.touches[0], b = e.touches[1]; return { x: (a.clientX + b.clientX) / 2, y: (a.clientY + b.clientY) / 2 }; }
    cv.addEventListener("touchstart", function (e) {
      e.preventDefault();   // 接管手势：禁用页面滚动/双击缩放/长按菜单与合成鼠标事件
      if (e.touches.length === 1) {
        var t = e.touches[0];
        downX = t.clientX; downY = t.clientY;
        downNode = pick(t.clientX, t.clientY);
        touchActive = true; panning = false; dragNode = null;
        last = { x: t.clientX, y: t.clientY };
      } else if (e.touches.length >= 2) {
        pinching = true; touchActive = false; dragNode = null; panning = false;
        pinchDist = touchDist(e); pinchScale = view.scale;
      }
      kick();
    }, { passive: false });
    cv.addEventListener("touchmove", function (e) {
      if (pinching && e.touches.length >= 2) {
        e.preventDefault();
        var d = touchDist(e);
        if (pinchDist > 0) {
          var mid = touchMid(e), l = localXY(mid.x, mid.y);
          var factor = d / pinchDist;
          var wx = (l.x - view.ox) / view.scale, wy = (l.y - view.oy) / view.scale;
          view.scale = pinchScale * factor;
          view.ox = l.x - wx * view.scale; view.oy = l.y - wy * view.scale;
        }
        kick();
        return;
      }
      if (!touchActive || e.touches.length !== 1) return;
      e.preventDefault();
      var t = e.touches[0];
      var dx = t.clientX - downX, dy = t.clientY - downY;
      if (dragNode) {
        var w = toWorld(t.clientX, t.clientY); dragNode.x = w.x; dragNode.y = w.y; dragNode.vx = 0; dragNode.vy = 0;
      } else if (panning) {
        view.ox += t.clientX - last.x; view.oy += t.clientY - last.y; last = { x: t.clientX, y: t.clientY };
      } else if (Math.abs(dx) + Math.abs(dy) > DRAG_THRESH) {   // 越过阈值才进入拖拽/平移
        if (downNode) { dragNode = downNode; dragNode.fixed = true; reheat(0.3);
          var w0 = toWorld(t.clientX, t.clientY); dragNode.x = w0.x; dragNode.y = w0.y; dragNode.vx = 0; dragNode.vy = 0; }
        else { panning = true; }
        last = { x: t.clientX, y: t.clientY };
      }
      kick();
    }, { passive: false });
    function onTouchEnd(e) {
      if (pinching) { if (e.touches.length < 2) pinching = false; return; }
      if (e.touches.length > 0) return;               // 还有手指按着
      var wasClick = touchActive && !dragNode && !panning;
      if (dragNode) { dragNode.fixed = false; dragNode = null; }
      if (panning) panning = false;
      if (wasClick) selectNode(downNode || null);     // 轻点即点击：选中/取消
      downNode = null; touchActive = false;
      kick();
    }
    cv.addEventListener("touchend", onTouchEnd, { passive: false });
    cv.addEventListener("touchcancel", onTouchEnd, { passive: false });
    global.addEventListener("resize", resize);

    var pc = document.getElementById("pc"); if (pc) pc.onclick = function () { selectNode(null); kick(); };
    // 「关联」邻居可点击：点击右侧信息框里的关联节点 → 聚焦该邻居（图 + 框同步）。
    // 事件委托在 #pbody 上，renderPanel 反复替换 innerHTML 也不丢失监听。
    var pbody = document.getElementById("pbody");
    if (pbody) pbody.addEventListener("click", function (e) {
      var li = e.target.closest ? e.target.closest("li.rel") : null;
      if (!li) return;
      var key = li.getAttribute("data-key");
      if (key) focus(key);
    });
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
    // 语言切换时，若右侧信息框已打开则重渲染（同步翻译）；i18n:ready 也补一次（处理 ?focus= 深链早于加载完成的情况）
    document.addEventListener("i18n:ready", function () { if (selected) renderPanel(selected); });
    document.addEventListener("i18n:changed", function () { if (selected) renderPanel(selected); });
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
    selected = n;
    // 若目标节点因筛选被隐藏，自动开启其类型复选框，保证聚焦后能在图谱中看到
    // （与「点击关联 → 同步图谱高亮节点」的预期一致；只增可见性，不缩减其它类型）
    var cbId = n.type === "Product" ? "cbP" : n.type === "Component" ? "cbC" : "cbS";
    var cb = document.getElementById(cbId);
    if (cb && !cb.checked) cb.checked = true;
    reheat(1);
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
    visibleNodes: visibleNodes,
    getViewport: function () { return { ox: view.ox, oy: view.oy, scale: view.scale }; }
  };
  global.GraphEngine = api;
})(window);
