(function () {
  "use strict";

  var ABM = {
    _config: null,
    _debug: false,
    _backendURL: null,
    _identified: false,

    init: function (config) {
      this._config = config;
      this._backendURL = config.backendURL.replace(/\/+$/, "");
      this._debug = config.debug || false;
      this._siteId = config.siteId || null;

      this._log("Initializing...");

      // Apply cached personalization immediately (avoids flash)
      var cached = this._getCachedComponents();
      if (cached) {
        this._log("Applying cached personalization");
        this._applyComponents(cached);
      }

      // Inject RB2B script if API key is provided
      if (config.rb2bApiKey) {
        this._injectRB2B(config.rb2bApiKey);
      }

      this._listenForIdentity();
    },

    _injectRB2B: function (apiKey) {
      var reb2b = (window.reb2b = window.reb2b || []);
      if (reb2b.invoked) return;
      reb2b.invoked = true;
      reb2b.methods = ["identify", "collect"];
      reb2b.factory = function (method) {
        return function () {
          var args = Array.prototype.slice.call(arguments);
          args.unshift(method);
          reb2b.push(args);
          return reb2b;
        };
      };
      for (var i = 0; i < reb2b.methods.length; i++) {
        reb2b[reb2b.methods[i]] = reb2b.factory(reb2b.methods[i]);
      }
      reb2b.load = function (key) {
        var s = document.createElement("script");
        s.type = "text/javascript";
        s.async = true;
        s.src =
          "https://s3-us-west-2.amazonaws.com/b2bjsstore/b/" +
          key +
          "/reb2b.js.gz";
        var first = document.getElementsByTagName("script")[0];
        first.parentNode.insertBefore(s, first);
      };
      reb2b.SNIPPET_VERSION = "1.0.1";
      reb2b.load(apiKey);
      this._log("RB2B script injected");
    },

    _listenForIdentity: function () {
      var self = this;

      // RB2B identification via postMessage
      window.addEventListener("message", function (e) {
        if (e.data && e.data.type === "rb2b_identify" && !self._identified) {
          self._identified = true;
          self._sendToBackend(e.data.payload);
        }
      });

      // Manual identification via forms with data-abm-trigger
      var forms = document.querySelectorAll("form[data-abm-trigger]");
      for (var i = 0; i < forms.length; i++) {
        (function (form) {
          form.addEventListener("submit", function (evt) {
            evt.preventDefault();
            var formData = new FormData(form);
            var payload = {};
            formData.forEach(function (val, key) {
              payload[key] = val;
            });
            self._identified = false;
            self._sendToBackend(payload);
          });
        })(forms[i]);
      }
    },

    /** Collect all dummy-ops-element nodes from the DOM. */
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

      this._log("Sending identity + " + elements.length + " elements to backend...");

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
          self._log("Received personalized components", data);
          if (data.components) {
            self._applyComponents(data.components);
            self._cacheComponents(data.components);
            window.dispatchEvent(
              new CustomEvent("abm:personalized", { detail: data })
            );
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
      } catch (e) {
        /* localStorage unavailable */
      }
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

  window.initABM = function (config) {
    if (!config || !config.backendURL) {
      console.error("[ABM] backendURL is required in config");
      return;
    }
    ABM.init(config);
    return ABM;
  };
})();
