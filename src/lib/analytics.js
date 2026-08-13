// analytics.js — 供应链瓶颈分析的纯函数计算（无 DOM、无渲染依赖，便于前端实时计算与单测）。
// 在浏览器/Node 中从 S.adj（已建好的类型化邻接表）推导三类结构指标：
//   1) 类型感知度中心性：分节点类型统计入/出度（复用率 / 供应广度 / 组装广度）。
//   2) 反向可达 / 断供影响传播（BFS 式下游遍历）：某供应商失效会波及多少产品、其中多少无替代。
//   3) PageRank / 网络核心度：有向图上的迭代排名，衡量节点在供应链网络中的「枢纽」程度。
// 产出统一挂到 S.metrics，下游（面板 / 图谱着色）直接消费；首次调用惰性计算并缓存。
import { S } from "../engine/state.js";

function label(n) { return (n && (n.name || n.english_name || n.id)) || ""; }

// 溯源注册表（缺失时返回空表，保证纯函数可单测 / 无 window 环境不崩溃）。
function sourceRegistry() {
  return (typeof window !== "undefined" && window.SUPPLY_DATA && window.SUPPLY_DATA.meta && window.SUPPLY_DATA.meta.source_registry) || {};
}
// 一条边的溯源置信度：有 ≥1 个非 generic（有实证文章）来源 = 1，全为 generic 主页 / 无来源 = 0；-1 表示无溯源边。
function edgeConfidence(sources, reg) {
  if (!sources || !sources.length) return -1;
  var good = 0;
  sources.forEach(function (sid) { var m = reg[sid]; if (m && !m.generic) good++; });
  return good / sources.length;
}

// 取某节点的出方向邻居 key 列表（供应链「流出」方向）。
function outNeighbors(key) {
  var es = S.adj[key] || [], out = [];
  for (var i = 0; i < es.length; i++) if (es[i].dir === "out") out.push(es[i].other._key);
  return out;
}

// 某节点（供应商 / 零部件）断供后的下游受影响产品集合 + 无替代计数。
// 供应商路径：供应商 →(SUPPLIES 入边) 零部件 →(USES 入边) 产品。
// 零部件路径：该零部件自身 →(USES 入边) 产品（即「被多少产品共用」）。
// single = 该零部件仅有 1 家供应商（由 compSup 集合从边推导，不依赖节点字段是否已填充）。
function impactReach(key, compSup) {
  var n = S.idMap[key];
  if (!n || (n.type !== "Supplier" && n.type !== "Component"))
    return { comps: [], suppliedComps: [], affected: [], noAlt: 0 };
  var comps = [];
  if (n.type === "Supplier") {
    (S.adj[key] || []).forEach(function (e) {
      if (e.dir === "in" && e.other.type === "Component" && e.link.type === "SUPPLIES") comps.push(e.other);
    });
  } else {
    comps.push(n);   // 零部件：自身即被产品使用的「组件」
  }
  var seen = {}, affected = [];
  comps.forEach(function (c) {
    var single = compSup[c._key] && compSup[c._key].size === 1;
    (S.adj[c._key] || []).forEach(function (e) {
      if (e.dir === "in" && e.other.type === "Product" && e.link.type === "USES") {
        var pk = e.other._key;
        if (!seen[pk]) { seen[pk] = { key: pk, single: false }; affected.push(seen[pk]); }
        if (single) seen[pk].single = true;
      }
    });
  });
  return {
    comps: comps,
    suppliedComps: n.type === "Supplier" ? comps.map(function (c) { return c._key; }) : [],
    affected: affected,
    noAlt: affected.filter(function (a) { return a.single; }).length,
  };
}

// PageRank（有向图，d=0.85，60 次迭代，sink 均匀回灌）。返回 key→score。
function pageRank() {
  var nodes = S.nodes || [], N = nodes.length || 1, d = 0.85;
  var pr = {};
  nodes.forEach(function (n) { pr[n._key] = 1 / N; });
  for (var it = 0; it < 60; it++) {
    var next = {};
    nodes.forEach(function (n) { next[n._key] = (1 - d) / N; });
    nodes.forEach(function (n) {
      var outs = outNeighbors(n._key);
      if (!outs.length) {
        nodes.forEach(function (m) { next[m._key] += d * pr[n._key] / N; });   // 汇聚节点：rank 均匀回流
      } else {
        var share = d * pr[n._key] / outs.length;
        outs.forEach(function (k) { next[k] += share; });
      }
    });
    pr = next;
  }
  return pr;
}

export function computeMetrics() {
  if (S.metrics) return S.metrics;
  var nodes = S.nodes || [];
  if (!nodes.length || !(S.adj && Object.keys(S.adj).length)) {
    S.metrics = { empty: true };
    return S.metrics;
  }

  // —— 1) PageRank ——
  var pagerank = pageRank();

  // —— 2) 断供影响（reach） + 逐节点明细 ——
  // 先由边推导每个零部件的供应商集合（不依赖 model 是否填充 n_suppliers，更稳健）。
  // 同时收集供应商国家，用于「单国供应集中度」判断（相关失效风险，比裸 n_c≥2 更贴合物理）。
  var compSup = {}, compCountries = {};
  nodes.forEach(function (n) { if (n.type === "Component") { compSup[n._key] = new Set(); compCountries[n._key] = { set: new Set(), known: 0, total: 0 }; } });
  (S.links || []).forEach(function (l) {
    if (l.type === "SUPPLIES" && compSup[l.a._key]) {
      compSup[l.a._key].add(l.b._key);   // 零部件 → 供应商
      var cc = compCountries[l.a._key]; cc.total++;
      if (l.b && l.b.country) { cc.set.add(l.b.country); cc.known++; }
    }
  });

  var info = {};
  nodes.forEach(function (n) { info[n._key] = { reach: 0, noAlt: 0, affected: [], suppliedComps: [], reuseProducts: [], spComps: [], compCount: 0, singleCountry: false, supplyCountry: "", nSupplyCountries: 0, confidence: -1 }; });
  nodes.forEach(function (n) {
    if (n.type === "Supplier" || n.type === "Component") {
      var d = impactReach(n._key, compSup);
      info[n._key].suppliedComps = d.suppliedComps;
      info[n._key].affected = d.affected;
      info[n._key].reach = d.affected.length;
      info[n._key].noAlt = d.noAlt;
    }
  });
  // 零部件「被多少产品共用」；产品「含多少零部件 / 单点依赖零部件」（类型感知度）。
  nodes.forEach(function (n) {
    if (n.type === "Component") {
      (S.adj[n._key] || []).forEach(function (e) {
        if (e.dir === "in" && e.other.type === "Product" && e.link.type === "USES")
          info[n._key].reuseProducts.push(e.other._key);
      });
    } else if (n.type === "Product") {
      (S.adj[n._key] || []).forEach(function (e) {
        if (e.dir === "out" && e.other.type === "Component" && e.link.type === "USES") {
          info[n._key].compCount++;
          if (compSup[e.other._key] && compSup[e.other._key].size === 1) info[n._key].spComps.push(e.other._key);
        }
      });
    }
  });

  // —— 单国供应集中度：零部件供应商是否全部位于同一国家 ——
  // 物理意义：同国多源 ≠ 真冗余（地震 / 出口管制等属地冲击会同时打掉所有货源）。
  // 仅在「全部供应商国家已知且同属一国」时判定为集中，避免把未知国家误判。
  var singleCountryComps = [];
  nodes.forEach(function (n) {
    if (n.type !== "Component") return;
    var cc = compCountries[n._key];
    var single = cc && cc.total > 0 && cc.known === cc.total && cc.set.size === 1;
    info[n._key].singleCountry = single;
    info[n._key].supplyCountry = single ? cc.set.values().next().value : "";
    info[n._key].nSupplyCountries = cc ? cc.set.size : 0;
    if (single) singleCountryComps.push(n._key);
  });

  // —— 溯源置信度：节点相关边的「有实证来源」占比（generic 出版商主页不计入）——
  var reg = sourceRegistry();
  nodes.forEach(function (n) {
    var edges = [];
    (S.links || []).forEach(function (l) {
      if (l.type === "SUPPLIES" && (l.a._key === n._key || l.b._key === n._key)) edges.push(l);
      else if (l.type === "USES" && l.a._key === n._key) edges.push(l);
    });
    if (!edges.length) { info[n._key].confidence = -1; return; }
    var sum = 0;
    edges.forEach(function (l) { var c = edgeConfidence(l.source, reg); sum += (c < 0 ? 0 : c); });
    info[n._key].confidence = sum / edges.length;
  });

  // —— 汇总：range / 排行 / 单点 / 地理集中度 ——
  var prMin = Infinity, prMax = -Infinity, rMin = Infinity, rMax = -Infinity;
  nodes.forEach(function (n) {
    var pr = pagerank[n._key] || 0;
    if (pr < prMin) prMin = pr; if (pr > prMax) prMax = pr;
    var r = info[n._key].reach;
    if (r < rMin) rMin = r; if (r > rMax) rMax = r;
  });

  var singleSourced = [];
  var eastCount = 0, supTotal = 0;
  nodes.forEach(function (n) {
    if (n.type === "Component" && compSup[n._key] && compSup[n._key].size === 1) singleSourced.push(n._key);
    if (n.type === "Supplier") {
      supTotal++;
      if (n.region === "East Asia") eastCount++;   // 地缘集中度：东亚供应占比（数据以 East Asia / Europe / NA 区分）
    }
  });

  var reachCands = nodes.filter(function (n) {
    return (n.type === "Supplier" || n.type === "Component") && info[n._key].reach > 0;
  }).map(function (n) {
    return { key: n._key, label: label(n), reach: info[n._key].reach, noAlt: info[n._key].noAlt, type: n.type };
  }).sort(function (a, b) { return (b.reach - a.reach) || (b.noAlt - a.noAlt) || a.label.localeCompare(b.label); });

  var prCands = nodes.map(function (n) {
    return { key: n._key, label: label(n), score: +(pagerank[n._key] || 0).toFixed(5), type: n.type };
  }).sort(function (a, b) { return b.score - a.score; });

  S.metrics = {
    pagerank: pagerank,
    info: info,
    range: {
      pagerank: { min: prMin, max: prMax },
      reach: { min: rMin === Infinity ? 0 : rMin, max: rMax === -Infinity ? 0 : rMax },
    },
    singleSourced: singleSourced,
    singleCountryComps: singleCountryComps,
    geoCN: supTotal ? +(eastCount / supTotal).toFixed(3) : 0,
    suppliersTotal: supTotal,
    topByReach: reachCands.slice(0, 15),
    topByPagerank: prCands.slice(0, 15),
    worstSingle: singleSourced.length ? singleSourced.map(function (k) { return label(S.idMap[k]); }).join("、") : "",
  };
  return S.metrics;
}

// 供测试 / 外部读取（返回缓存或即时计算的结果）。
export function getMetrics() { return computeMetrics(); }
