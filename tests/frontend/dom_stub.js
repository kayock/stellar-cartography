"use strict";

/* dom_stub.js
 *
 * A deliberately minimal, dependency-free fake DOM sufficient to load and
 * exercise the *real* app/static/app.js (plus its lib/*.js dependencies)
 * inside Node's built-in `vm` module, for browser-DOM integration tests
 * (tests/frontend/app_dom_integration.test.js, app_selection_failure.test.js).
 *
 * This intentionally does NOT pull in jsdom or any other package -- the
 * repair request scope forbids adding dependencies. It implements just
 * enough of Element/Document/Window for app.js's actual DOM glue
 * (getElementById, classList, addEventListener/dispatchEvent,
 * innerHTML/textContent, querySelector(All), document.createElement) to
 * run unmodified.
 */

const ELEMENT_IDS = [
  "stellarium-indicator",
  "archive-mode-indicator",
  "btn-refresh-selection",
  "target-card",
  "about-object-card",
  "about-object-body",
  "solar-system-notice-card",
  "solar-system-notice-body",
  "planetary-image-card",
  "planetary-image-body",
  "cosmic-signal-deck-card",
  "cosmic-signal-title",
  "cosmic-signal-subtitle",
  "cosmic-signal-body",
  "cosmic-signal-status",
  "cosmic-signal-available",
  "cosmic-signal-available-buttons",
  "cosmic-signal-relevance",
  "cosmic-signal-media-type",
  "cosmic-signal-player-wrap",
  "cosmic-signal-poster",
  "cosmic-signal-video",
  "cosmic-signal-audio",
  "cosmic-signal-play",
  "cosmic-signal-stop",
  "cosmic-signal-hearing",
  "cosmic-signal-credits",
  "cosmic-signal-source-link",
  "cosmic-signal-featured-wrap",
  "cosmic-signal-featured-toggle",
  "cosmic-signal-live",
  "spectrum-gallery-card",
  "spectrum-gallery-title",
  "spectrum-gallery-subtitle",
  "spectrum-gallery-body",
  "spectrum-gallery-status",
  "spectrum-gallery-relevance",
  "spectrum-gallery-image-wrap",
  "spectrum-gallery-image",
  "spectrum-gallery-available",
  "spectrum-gallery-selectors",
  "spectrum-gallery-wavelength",
  "spectrum-gallery-observatory",
  "spectrum-gallery-explanation",
  "spectrum-gallery-credits",
  "spectrum-gallery-source-link",
  "spectrum-gallery-live",
  "manual-form",
  "manual-name",
  "manual-ra",
  "manual-dec",
  "manual-form-error",
  "online-mode-toggle",
  "btn-open-esasky",
  "viewer-status",
  "esasky-frame-wrap",
  "esasky-frame",
  "imagery-grid",
  "imagery-status",
  "archive-observation-panel",
  "discovery-panel",
  "discovery-panel-body",
  "hips-survey-controls-label",
  "hips-restore-wrap",
  "btn-hips-restore",
  "hips-diagnostics",
  "wavelength-explainer",
  "watchlist-explainer",
  "watchlist-status",
  "btn-watchlist-add",
  "btn-apophis-add",
  "btn-watchlist-refresh",
  "watchlist-list",
  "tracked-object-details-card",
  "tracked-object-details-heading",
  "tracked-object-details-body",
  "apophis-tracker-body",
];

function makeClassList(el) {
  const set = new Set();
  return {
    add(...cls) {
      cls.forEach((c) => set.add(c));
    },
    remove(...cls) {
      cls.forEach((c) => set.delete(c));
    },
    contains(c) {
      return set.has(c);
    },
    toString() {
      return Array.from(set).join(" ");
    },
  };
}

function makeElement(tag) {
  const listeners = {};
  const el = {
    tagName: (tag || "div").toUpperCase(),
    id: "",
    className: "",
    _innerHTML: "",
    _text: "",
    _children: [],
    hidden: false,
    disabled: false,
    checked: false,
    controls: false,
    preload: "",
    value: "",
    title: "",
    src: "",
    alt: "",
    href: "",
    rel: "",
    target: "",
    dataset: {},
    style: {},
    // ESASky iframe glue expects a contentWindow.postMessage -- tests spy
    // on this to capture dispatched commands.
    contentWindow: { postMessage: () => {} },
    pause() {},
    play() { return Promise.resolve(); },
    load() {},
    removeAttribute(name) {
      if (name === "src") el.src = "";
      if (name === "href") el.href = "";
    },
    addEventListener(type, handler) {
      listeners[type] = listeners[type] || [];
      if (!listeners[type].includes(handler)) listeners[type].push(handler);
    },
    removeEventListener(type, handler) {
      if (!listeners[type]) return;
      listeners[type] = listeners[type].filter((h) => h !== handler);
    },
    dispatchEvent(evt) {
      const type = evt && evt.type;
      (listeners[type] || []).slice().forEach((h) => h.call(el, evt));
      return true;
    },
    appendChild(child) {
      if (child) el._children.push(child);
      return child;
    },
    querySelector(sel) {
      if (!sel) return null;
      const s = String(sel).trim();
      if (s.startsWith(".")) {
        const child = makeElement("span");
        child.className = s.slice(1);
        return child;
      }
      const tag = s.toUpperCase();
      if (el.tagName === tag) return el;
      for (const child of el._children) {
        const found = child.querySelector ? child.querySelector(sel) : null;
        if (found) return found;
      }
      return null;
    },
    querySelectorAll(sel) {
      const tag = String(sel).replace(/^\s*|\s*$/g, "").toUpperCase();
      const out = [];
      function walk(node) {
        if (node.tagName === tag) out.push(node);
        (node._children || []).forEach(walk);
      }
      walk(el);
      return out;
    },
    getAttribute(name) {
      if (name === "onerror" || name === "onclick") return null;
      if (name === "src") return el.src || null;
      if (name === "href") return el.href || null;
      if (name === "alt") return el.alt || null;
      if (Object.prototype.hasOwnProperty.call(el._attrs || {}, name)) return el._attrs[name];
      return null;
    },
    setAttribute(name, value) {
      el._attrs = el._attrs || {};
      el._attrs[String(name)] = String(value);
      if (name === "src") el.src = String(value);
      if (name === "href") el.href = String(value);
      if (name === "alt") el.alt = String(value);
    },
    focus() {},
  };
  el.classList = makeClassList(el);
  Object.defineProperty(el, "innerHTML", {
    get() {
      return el._innerHTML;
    },
    set(v) {
      el._innerHTML = String(v);
      if (String(v) === "") {
        el._children = [];
        el._text = "";
      }
    },
  });
  Object.defineProperty(el, "textContent", {
    get() {
      if (el._children && el._children.length > 0) {
        return el._children.map((child) => child.textContent || child._text || "").join("");
      }
      return el._text;
    },
    set(v) {
      el._text = String(v);
      el._children = [];
      // escapeHtml() in app.js relies on textContent -> innerHTML
      // producing an HTML-escaped string via document.createElement("div").
      el._innerHTML = el._text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
    },
  });
  return el;
}

/** Build a fresh `document`, `window`, and `el`-by-id map for one test. */
function createDom() {
  const elementsById = {};
  const tagById = {
    "cosmic-signal-video": "video",
    "cosmic-signal-audio": "audio",
    "cosmic-signal-play": "button",
    "cosmic-signal-stop": "button",
    "cosmic-signal-featured-toggle": "input",
    "cosmic-signal-poster": "img",
    "cosmic-signal-source-link": "a",
    "spectrum-gallery-image": "img",
    "spectrum-gallery-source-link": "a",
    "online-mode-toggle": "input",
    "manual-form": "form",
    "esasky-frame": "iframe",
  };
  ELEMENT_IDS.forEach((id) => {
    const e = makeElement(tagById[id] || "div");
    e.id = id;
    if (id === "cosmic-signal-video" || id === "cosmic-signal-audio") {
      e.controls = true;
      e.preload = "none";
    }
    if (id === "cosmic-signal-play" || id === "cosmic-signal-stop") {
      e.type = "button";
    }
    if (id === "cosmic-signal-featured-toggle" || id === "online-mode-toggle") {
      e.type = "checkbox";
      e.checked = true;
    }
    if (id === "cosmic-signal-hearing") {
      const content = makeElement("div");
      content.className = "cosmic-signal-hearing-content";
      e.appendChild(content);
      // Prefer real child lookup for this class.
      const originalQs = e.querySelector.bind(e);
      e.querySelector = (sel) => {
        if (String(sel).trim() === ".cosmic-signal-hearing-content") return content;
        return originalQs(sel);
      };
    }
    elementsById[id] = e;
  });

  const windowListeners = {};
  const window = {
    addEventListener(type, handler) {
      windowListeners[type] = windowListeners[type] || [];
      windowListeners[type].push(handler);
    },
    removeEventListener(type, handler) {
      if (!windowListeners[type]) return;
      windowListeners[type] = windowListeners[type].filter((h) => h !== handler);
    },
    dispatchEvent(evt) {
      (windowListeners[evt.type] || []).slice().forEach((h) => h.call(window, evt));
      return true;
    },
    // Test helper (not part of the real window API): lets a test simulate
    // an ESASky postMessage without going through actual cross-realm
    // postMessage plumbing.
    __simulateMessage(origin, data) {
      (windowListeners.message || []).slice().forEach((h) => h.call(window, { origin, data }));
    },
  };

  const document = {
    getElementById(id) {
      return elementsById[id] || null;
    },
    querySelectorAll() {
      return [];
    },
    createElement(tag) {
      return makeElement(tag);
    },
  };

  return { document, window, elementsById };
}

module.exports = { createDom, makeElement, ELEMENT_IDS };
