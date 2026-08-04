"use strict";

/* app_loader.js
 *
 * Loads the REAL app/static/app.js, together with its real
 * app/static/lib/*.js dependencies, into a single Node `vm` context that
 * shares the fake DOM from dom_stub.js. This is what lets
 * tests/frontend/app_dom_integration.test.js and
 * app_selection_failure.test.js exercise app.js's actual click handlers,
 * renderTargetCard(), syncEsaskyToCurrentTarget(), and ESASky load-handler
 * logic -- not a re-implementation of them.
 *
 * app.js's own bottom-of-file test hook (`if (typeof module === "object"
 * && module.exports) { module.exports = {...} }`) is what exposes its
 * internals back out of the vm context.
 */

const vm = require("node:vm");
const fs = require("node:fs");
const path = require("node:path");

const { createDom } = require("./dom_stub");

const LIB_DIR = path.join(__dirname, "..", "..", "app", "static", "lib");
const APP_JS = path.join(__dirname, "..", "..", "app", "static", "app.js");

const LIB_FILES = [
  "solar_system.js",
  "solar_system_media_registry.js",
  "planetary_image.js",
  "cosmic_signal_deck.js",
  "archive_availability.js",
  "discovery_panel.js",
  "hips_layer_control.js",
  "watchlist.js",
  "apophis_tracker.js",
  "esasky_queue.js",
  "target_model.js",
  "changehips.js",
  "imagery_matching.js",
  "online_mode.js",
];

/** Load app.js (+ libs) fresh into a new vm context/fake DOM.
 *
 * `fetchImpl` lets a test control what `fetch(...)` resolves/rejects with
 * inside app.js's real handlers (e.g. the "Use Stellarium Selection" click
 * handler's `await fetch("/api/selection", ...)`).
 *
 * Returns { document, window, exports } where `exports` is exactly what
 * app.js's bottom-of-file test hook assigned to module.exports (state, el,
 * syncEsaskyToCurrentTarget, openOrUpdateEsasky, renderTargetCard,
 * clearStaleTargetAfterFailedSelection, turnOnlineModeOn/Off).
 */
function loadApp(fetchImpl) {
  const { document, window } = createDom();

  const sandbox = {
    document,
    window,
    console,
    setTimeout,
    clearTimeout,
    localStorage: {
      _data: {},
      getItem(key) {
        return Object.prototype.hasOwnProperty.call(this._data, key) ? this._data[key] : null;
      },
      setItem(key, value) {
        this._data[key] = String(value);
      },
      removeItem(key) {
        delete this._data[key];
      },
    },
    // Overridden as a no-op: app.js's init code calls
    // setInterval(pollStellariumStatus, 6000) at load time. A real
    // interval would otherwise keep the Node test process's event loop
    // alive well past the test finishing.
    setInterval: () => 0,
    clearInterval: () => {},
    fetch: fetchImpl || (async () => ({ ok: true, json: async () => ({}) })),
    URLSearchParams,
    URL,
    Math,
    Event: function Event(type) {
      this.type = type;
    },
  };
  sandbox.self = sandbox; // lib/*.js UMD wrapper: `typeof self !== "undefined" ? self : this`
  sandbox.window.fetch = sandbox.fetch;

  const context = vm.createContext(sandbox);

  // Loaded with no `module` global defined, exactly like real <script>
  // tags in the browser -- each lib's UMD wrapper falls through to
  // `root.<Name> = factory()`, attaching itself as a context global
  // (EsaskyQueue, TargetModel, ChangeHips, ImageryMatching, OnlineMode).
  for (const file of LIB_FILES) {
    const code = fs.readFileSync(path.join(LIB_DIR, file), "utf8");
    vm.runInContext(code, context, { filename: file });
  }

  // Only now define `module`, so app.js's own bottom-of-file test hook
  // (`if (typeof module === "object" && module.exports) {...}`) fires and
  // exposes its internals -- app.js is the one file in this project meant
  // to be loaded both as a <script> tag and (here) as a CommonJS module.
  sandbox.module = { exports: {} };

  const appCode = fs.readFileSync(APP_JS, "utf8");
  vm.runInContext(appCode, context, { filename: "app.js" });

  return { document, window, exports: sandbox.module.exports, sandbox };
}

/** Fire a DOM event on a fake element and flush any pending microtasks
 * (app.js's click/change/submit handlers are `async` functions). */
async function fireAndFlush(el, type) {
  el.dispatchEvent({ type, preventDefault() {} });
  // The real handlers are `async` functions with multiple `await`s
  // (fetch(), then resp.json()), and fetchImpl itself may be async too --
  // each hop is its own microtask turn. A few macrotask ticks
  // (setTimeout(0)) reliably drains all of that, which plain
  // Promise.resolve() chaining doesn't guarantee across vm-context
  // promises.
  for (let i = 0; i < 5; i++) {
    await new Promise((resolve) => setTimeout(resolve, 0));
  }
}

module.exports = { loadApp, fireAndFlush };
