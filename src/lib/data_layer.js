/*
 * data_layer.js —— 时效数据适配层（阶段1：FileFeedProvider）
 *
 * 职责：在前端（消费侧）与数据生产侧之间建立「清晰、可切换」的接口。
 *   - 前端只依赖 window.DataLayer 的方法，绝不直接 fetch 文件路径；
 *   - 数据来源通过 Provider 抽象：当前用 FileFeedProvider（拉取仓库内 data/feeds/*.json），
 *     将来接真实 API 只需 new ApiFeedProvider(url) 并 DataLayer.setProvider(...)，UI 零改动。
 *
 * 统一契约（每个 feed 文件）：
 *   { meta:{dataset,version,schema_ref,generated,valid_until,sources}, data:{...} }
 *
 * 该文件为 IIFE，经 esbuild 打包为 dist/data_layer.js（无外部依赖，直接挂到 window.DataLayer）。
 */
(function () {
  "use strict";

  var DEFAULT_BASE = "data/feeds/";
  var TTL_FALLBACK_DAYS = 30; // feed 未给 valid_until 时，按 generated + 30 天判定
  var LS_PREFIX = "feed:";

  function parseDate(s) {
    if (!s) return null;
    var t = Date.parse(s);
    return isNaN(t) ? null : t;
  }

  // 新鲜度：比较 valid_until（或 generated+兜底）与当前时间
  function freshnessOf(meta) {
    if (!meta || !meta.generated) return "unknown";
    var exp = parseDate(meta.valid_until);
    if (exp == null) {
      var gen = parseDate(meta.generated);
      if (gen == null) return "unknown";
      exp = gen + TTL_FALLBACK_DAYS * 86400000;
    }
    return Date.now() <= exp ? "fresh" : "stale";
  }

  // 本地降级缓存（网络失败时回退）
  function cacheGet(name) {
    try {
      var v = localStorage.getItem(LS_PREFIX + name);
      return v ? JSON.parse(v) : null;
    } catch (e) {
      return null;
    }
  }
  function cacheSet(name, obj) {
    try {
      localStorage.setItem(LS_PREFIX + name, JSON.stringify(obj));
    } catch (e) {
      /* 隐私模式 / 配额满：静默忽略 */
    }
  }

  function escAttr(s) {
    return String(s).replace(/[<>&]/g, function (c) {
      return c === "<" ? "&lt;" : c === ">" ? "&gt;" : "&amp;";
    });
  }

  // ===== Provider：从文件拉取（当前实现） =====
  function FileFeedProvider(base) {
    this.base = base || DEFAULT_BASE;
  }
  FileFeedProvider.prototype.url = function (name, cacheBust) {
    var u = this.base + name + ".json";
    if (cacheBust) {
      u += (u.indexOf("?") >= 0 ? "&" : "?") + "v=" + (cacheBust === true ? Date.now() : cacheBust);
    }
    return u;
  };
  FileFeedProvider.prototype.fetch = function (name, opts) {
    var self = this;
    return fetch(self.url(name, opts && opts.cacheBust), { cache: "no-store" }).then(function (res) {
      if (!res.ok) throw new Error("feed " + name + " HTTP " + res.status);
      return res.json();
    }).then(function (json) {
      if (!json || !json.meta) throw new Error("feed " + name + " 缺少 meta 信封");
      return json;
    });
  };

  // ===== Provider：从外部 API 拉取（未来实现，接口一致） =====
  function ApiFeedProvider(endpoint) {
    this.endpoint = endpoint; // 形如 "https://api.example.com/feeds/{name}.json"
  }
  ApiFeedProvider.prototype.url = function (name) {
    return this.endpoint.replace("{name}", name);
  };
  ApiFeedProvider.prototype.fetch = function (name, opts) {
    var self = this;
    return fetch(self.url(name), { cache: "no-store" }).then(function (res) {
      if (!res.ok) throw new Error("api " + name + " HTTP " + res.status);
      return res.json();
    });
  };

  var _mem = {}; // 内存缓存，避免重复 fetch

  var DataLayer = {
    provider: new FileFeedProvider(),
    _cacheBust: true, // 每次部署后文件名带哈希，但加 v= 进一步防 CDN 缓存

    setProvider: function (p) {
      this.provider = p;
    },

    load: function (name, opts) {
      opts = opts || {};
      if (_mem[name] && !opts.force) return Promise.resolve(_mem[name]);
      var self = this;
      return this.provider.fetch(name, { cacheBust: this._cacheBust }).then(function (feed) {
        _mem[name] = feed;
        cacheSet(name, feed);
        return feed;
      }).catch(function (err) {
        // 网络/解析失败：回退到上次成功的本地缓存（标记可能过期）
        var cached = cacheGet(name);
        if (cached) {
          cached._stale_cache = true;
          _mem[name] = cached;
          return cached;
        }
        throw err;
      });
    },

    meta: function (name) {
      var f = _mem[name];
      return f ? f.meta : null;
    },
    freshness: function (name) {
      return freshnessOf(this.meta(name));
    },
    freshnessMeta: function (meta) {
      return freshnessOf(meta);
    },

    getRisk: function (opts) {
      return this.load("risk", opts).then(function (f) {
        return f ? f.data : null;
      });
    },
    getValuation: function (opts) {
      return this.load("valuation", opts).then(function (f) {
        return f ? f.data : null;
      });
    },
    getSentiment: function (opts) {
      return this.load("sentiment", opts).then(function (f) {
        return f ? f.data : null;
      });
    },

    formatDate: function (s, lang) {
      var t = parseDate(s);
      if (t == null) return s || "";
      try {
        return new Intl.DateTimeFormat(lang || "zh", {
          year: "numeric",
          month: "2-digit",
          day: "2-digit"
        }).format(t);
      } catch (e) {
        return s;
      }
    },

    _lang: function () {
      return window.i18n && window.i18n.language ? window.i18n.language : "zh";
    },

    // 把某个 feed 的新鲜度渲染进容器元素（UI 调用）
    renderFreshness: function (el, name) {
      if (!el) return;
      var f = _mem[name];
      if (!f) {
        el.innerHTML = "";
        return;
      }
      var self = this;
      var L = function (k) {
        return window.i18n && window.i18n.t ? window.i18n.t(k) : k;
      };
      var meta = f.meta || {};
      var fr = this.freshnessMeta(meta);
      var cls = fr === "stale" ? "stale" : fr === "unknown" ? "unknown" : "fresh";
      var parts = [];
      parts.push(L("feed.updated") + ": " + this.formatDate(meta.generated, self._lang()));
      if (meta.valid_until) {
        parts.push(L("feed.nextUpdate") + ": " + this.formatDate(meta.valid_until, self._lang()));
      }
      if (fr === "stale") parts.push(L("feed.stale"));
      if (f._stale_cache) parts.push(L("feed.mayBeStale"));
      el.innerHTML =
        "<span class='feed-badge " + cls + "'><span class='dot'></span>" +
        escAttr(parts.join(" · ")) + "</span>";
    }
  };

  window.DataLayer = DataLayer;
  window.DataLayer.FileFeedProvider = FileFeedProvider;
  window.DataLayer.ApiFeedProvider = ApiFeedProvider;
})();
