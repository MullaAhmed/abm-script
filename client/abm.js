(function () {
  "use strict";

  var ABM = {
    _config: null,
    _debug: false,
    _backendURL: null,
    _personalized: false,

    init: function (config) {
      this._config = config;
      this._backendURL = config.backendURL.replace(/\/+$/, "");
      this._debug = config.debug || false;
      this._siteId = config.siteId || null;

      this._log("Initializing with backend:", this._backendURL);

      // Apply cached personalization immediately (avoids flash)
      var cached = this._getCachedComponents();
      if (cached) {
        this._log("Applying cached personalization");
        this._applyComponents(cached);
        this._personalized = true;
      }

      this._listenForForms();
    },

    _listenForForms: function () {
      var self = this;
      document.addEventListener("submit", function (evt) {
        var form = evt.target;
        if (!form || !form.hasAttribute("data-abm-trigger")) return;
        evt.preventDefault();
        var formData = new FormData(form);
        var payload = {};
        formData.forEach(function (val, key) {
          payload[key] = val;
        });
        self._log("Form submitted with payload:", payload);
        self._personalized = false;
        self._sendToBackend(payload);
      });
    },

    _collectElements: function () {
      var els = document.querySelectorAll("[dummy-ops-element]");
      var elements = [];
      for (var i = 0; i < els.length; i++) {
        var el = els[i];
        elements.push({
          id: el.getAttribute("dummy-ops-element"),
          tag: el.tagName.toLowerCase(),
          current_text: el.textContent.trim(),
        });
      }
      return elements;
    },

    _sendToBackend: function (payload) {
      var self = this;
      var url = this._backendURL + "/api/identify";
      var elements = this._collectElements();

      if (elements.length === 0) {
        this._log("No [dummy-ops-element] found on page, skipping.");
        return;
      }

      var body = JSON.stringify({
        payload: payload,
        elements: elements,
        site_id: this._siteId,
        page_url: window.location.href,
      });

      this._log("Sending to backend: " + Object.keys(payload).join(", "));

      fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: body,
      })
        .then(function (res) {
          if (!res.ok) throw new Error("ABM identify failed: " + res.status);
          return res.json();
        })
        .then(function (data) {
          self._log("Response:", data);
          if (data.visitor && data.components) {
            self._personalized = true;
            self._applyComponents(data.components);
            self._cacheComponents(data.components);
            window.dispatchEvent(
              new CustomEvent("abm:personalized", { detail: data })
            );
          } else {
            self._log("No visitor data yet");
          }
        })
        .catch(function (err) {
          self._log("Error:", err);
        });
    },

    _applyComponents: function (components) {
      for (var id in components) {
        if (!components.hasOwnProperty(id)) continue;
        var el = document.querySelector('[dummy-ops-element="' + id + '"]');
        if (el) {
          el.textContent = components[id];
          el.setAttribute("data-personalized", "true");
          this._log('Updated [dummy-ops-element="' + id + '"]');
        }
      }
    },

    _cacheComponents: function (components) {
      try {
        localStorage.setItem("abm_components", JSON.stringify(components));
        localStorage.setItem("abm_cached_at", String(Date.now()));
      } catch (e) {}
    },

    _getCachedComponents: function () {
      try {
        var cached = localStorage.getItem("abm_components");
        var cachedAt = localStorage.getItem("abm_cached_at");
        if (!cached || !cachedAt) return null;
        var ttl = (this._config && this._config.cacheTtl) || 3600000;
        if (Date.now() - parseInt(cachedAt, 10) > ttl) {
          localStorage.removeItem("abm_components");
          localStorage.removeItem("abm_cached_at");
          return null;
        }
        return JSON.parse(cached);
      } catch (e) {
        return null;
      }
    },

    _log: function () {
      if (this._debug && console && console.log) {
        var args = Array.prototype.slice.call(arguments);
        args.unshift("[ABM]");
        console.log.apply(console, args);
      }
    },
  };

  // Expose manual init
  window.initABM = function (config) {
    if (!config || !config.backendURL) {
      console.error("[ABM] backendURL is required in config");
      return;
    }
    ABM.init(config);
    return ABM;
  };

  // Auto-init: detect backend URL from script src, fetch config, and start
  (function autoInit() {
    var scripts = document.querySelectorAll("script[src]");
    var backendURL = null;

    for (var i = 0; i < scripts.length; i++) {
      var src = scripts[i].getAttribute("src") || "";
      if (src.indexOf("/api/snippet.js") !== -1) {
        if (src.indexOf("://") !== -1) {
          var parts = src.split("/api/snippet.js");
          backendURL = parts[0];
        } else {
          backendURL = window.location.origin;
        }
        break;
      }
    }

    if (!backendURL) return;

    fetch(backendURL.replace(/\/+$/, "") + "/api/config")
      .then(function (res) { return res.json(); })
      .then(function (cfg) {
        console.log("[ABM] Auto-init with config from", backendURL);
        ABM.init({
          backendURL: backendURL,
          siteId: cfg.site_id || null,
          debug: cfg.debug || false,
          cacheTtl: (cfg.cache_ttl || 3600) * 1000,
        });
      })
      .catch(function (err) {
        console.error("[ABM] Auto-init failed, call initABM() manually:", err);
      });
  })();
})();
