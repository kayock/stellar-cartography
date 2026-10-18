/* constellation_story.js
 *
 * Constellation Story Deck UI. Missing DOM nodes are ignored so existing
 * Node DOM-integration tests keep working. Audio never autoplays.
 */
(function (root) {
  "use strict";

  var els = {};
  var lastSelection = null;
  var lastStory = null;
  var lastTour = null;
  var lastSignals = [];
  var lastSpectra = [];
  var lastStoryId = null;

  function $(id) {
    return typeof document !== "undefined" && document && document.getElementById
      ? document.getElementById(id)
      : null;
  }

  function init() {
    els.openBtn = $("btn-open-constellation-story");
    els.context = $("constellation-context");
    els.panel = $("constellation-story-card");
    els.body = $("constellation-story-body");
    els.tourStatus = $("constellation-tour-status");
    els.listen = $("constellation-listen-body");
    els.cultureSelect = $("story-culture-select");
    els.storyBrowser = $("story-browser");
    els.compare = $("story-compare");
    els.stelCulture = $("stellarium-sky-culture");
    bind();
    refreshStoryBrowser();
  }

  function bind() {
    on("btn-open-constellation-story", "click", function () { openStory(); });
    if (els.cultureSelect) {
      els.cultureSelect.addEventListener("change", function () {
        refreshStoryBrowser();
        refreshContext();
      });
    }
    on("btn-constellation-tour-start", "click", function () { tour("start"); });
    on("btn-constellation-tour-prev", "click", function () { tour("step", "prev"); });
    on("btn-constellation-tour-next", "click", function () { tour("step", "next"); });
    on("btn-constellation-tour-stop", "click", function () { tour("stop"); });
    on("btn-constellation-return", "click", function () { tour("stop"); });
    ["lines", "labels", "boundaries", "artwork", "isolate"].forEach(function (key) {
      on("constellation-ctrl-" + key, "change", function (ev) {
        var payload = {};
        payload[key] = !!(ev.target && ev.target.checked);
        postJson("/api/constellation-controls", payload);
      });
    });
  }

  function on(id, type, fn) {
    var node = $(id);
    if (node) node.addEventListener(type, fn);
  }

  function onTargetChange(selection) {
    lastSelection = selection || null;
    var nextId = selection && (selection.constellation || selection.name);
    if (lastStoryId && nextId && lastStoryId !== nextId && root.CartographyNarration && root.CartographyNarration.onConstellationChange) {
      root.CartographyNarration.onConstellationChange();
    }
    refreshContext();
  }

  async function refreshContext() {
    try {
      var culture = selectedCulture();
      var resp = await fetch("/api/constellation-context?culture=" + encodeURIComponent(culture || ""), { cache: "no-store" });
      var data = await resp.json();
      renderContext(data && data.context, data);
    } catch (_err) {
      renderContext(null, null);
    }
  }

  function selectedCulture() {
    return els.cultureSelect ? String(els.cultureSelect.value || "modern") : "modern";
  }

  function renderContext(context, payload) {
    if (els.openBtn) {
      els.openBtn.hidden = false;
      els.openBtn.disabled = false;
    }
    if (els.stelCulture) {
      var live = payload && payload.stellarium_sky_culture;
      els.stelCulture.textContent = live && live.id
        ? "Stellarium rendering culture: " + live.id + " — shown separately from the Cartography story selector."
        : "Stellarium rendering culture: not reported.";
    }
    if (els.context) {
      if (!context || !context.detected) {
        els.context.textContent = "No IAU constellation is attached to this selection. You can still browse Stories of the Sky.";
      } else if (context.story_available) {
        els.context.textContent = "IAU area: " + (context.canonical_name || context.iau_abbreviation) +
          (context.iau_abbreviation ? " (" + context.iau_abbreviation + ")" : "");
      } else {
        els.context.textContent = context.empty_reason || "No constellation story for this IAU area.";
      }
    }
    renderCompare((context && context.matching_stories) || []);
  }

  async function refreshStoryBrowser() {
    if (!els.storyBrowser) return;
    try {
      var resp = await fetch("/api/stories?culture=" + encodeURIComponent(selectedCulture()), { cache: "no-store" });
      var data = await resp.json();
      var stories = (data && (data.stories || data.constellations)) || [];
      if (!stories.length) {
        els.storyBrowser.innerHTML = "<p class=\"hint\">No enabled stories in this culture.</p>";
        return;
      }
      els.storyBrowser.innerHTML = stories.map(function (story) {
        return "<button type=\"button\" class=\"event-chip\" data-story-id=\"" + escapeHtml(story.id) + "\">" +
          escapeHtml(story.native_name || story.canonical_name) + "</button>";
      }).join("");
      els.storyBrowser.querySelectorAll("[data-story-id]").forEach(function (btn) {
        btn.addEventListener("click", function () { openStory(btn.getAttribute("data-story-id")); });
      });
    } catch (_err) {
      els.storyBrowser.innerHTML = "<p class=\"hint\">Could not load the story list.</p>";
    }
  }

  function renderCompare(items) {
    if (!els.compare) return;
    if (!items || items.length < 2) {
      els.compare.hidden = true;
      els.compare.innerHTML = "";
      return;
    }
    els.compare.hidden = false;
    els.compare.innerHTML = "<div class=\"narration-label\">Same sky — different stories</div>" +
      "<p class=\"hint\">These traditions share astronomical objects or a similar observational function. They are not merged into one mythology.</p>" +
      items.map(function (item) {
        return "<button type=\"button\" class=\"event-chip\" data-story-id=\"" + escapeHtml(item.id) + "\">" +
          escapeHtml(item.culture_name || item.culture_id) + ": " +
          escapeHtml(item.native_name || item.canonical_name) + "</button>";
      }).join("");
    els.compare.querySelectorAll("[data-story-id]").forEach(function (btn) {
      btn.addEventListener("click", function () { openStory(btn.getAttribute("data-story-id")); });
    });
  }

  async function openStory(storyId) {
    if (els.panel) els.panel.open = true;
    try {
      var url;
      if (storyId) {
        url = "/api/constellation/" + encodeURIComponent(storyId);
      } else {
        url = "/api/constellation-context?include_story=1&culture=" + encodeURIComponent(selectedCulture());
      }
      var resp = await fetch(url, { cache: "no-store" });
      var data = await resp.json();
      var story = data && (data.story && data.story.ok ? data.story : data);
      if (!story || story.ok === false) {
        setBody("<p class=\"hint\">No curated sky story is available.</p>");
        return;
      }
      lastStory = story;
      lastStoryId = story.id || lastStoryId;
      renderStory(story, null);
      refreshControls();
      if (root.CartographyNarration && root.CartographyNarration.refreshProviders) {
        root.CartographyNarration.refreshProviders();
      }
    } catch (_err) {
      setBody("<p class=\"hint\">Could not load the sky story.</p>");
    }
  }

  function renderStory(story, tour) {
    lastStory = story;
    lastTour = tour;
    lastSignals = ((tour && tour.signals) || story.signals || {}).ranked || [];
    lastSpectra = ((tour && tour.spectra) || story.spectra || {}).ranked || [];
    var cultureNote = story.sky_culture_synchronized
      ? "Stellarium sky culture: " + escapeHtml(story.sky_culture_live || story.sky_culture)
      : "Story culture: " + escapeHtml(story.sky_culture_display || story.sky_culture) +
        " (not synchronized with Stellarium)";
    var step = tour && tour.step;
    var progress = tour && tour.active
      ? "Step " + (tour.step_index + 1) + " / " + tour.total_steps
      : "Tour not started — Stellarium will not move until you press Start Guided Tour.";
    var html = "";
    html += "<div class=\"constellation-header\">";
    html += "<div class=\"target-name\">" + escapeHtml(story.native_name || story.culture_specific_name || story.canonical_name) + "</div>";
    html += "<div class=\"hint\">" + escapeHtml(story.culture_name || "Modern IAU") +
      (story.tradition_name ? " · " + escapeHtml(story.tradition_name) : "") + "</div>";
    if (story.translated_name && story.translated_name !== story.native_name) {
      html += "<div class=\"hint\">" + escapeHtml(story.translated_name) + "</div>";
    }
    html += "<div class=\"hint\">" + escapeHtml(story.abbreviation || (story.iau_overlap || []).join(", ")) +
      " · Cartography story culture: " + escapeHtml(story.sky_culture || "") +
      " · Stellarium rendering: " + escapeHtml(story.sky_culture_live || "unknown") +
      (story.stellarium_culture_is_distinct ? " (not synchronized)" : " (ids match)") + "</div>";
    html += "<div class=\"constellation-progress\">" + escapeHtml(progress) + "</div>";
    html += "</div>";
    if (step) {
      html += "<div class=\"constellation-step-card\">";
      html += "<strong>" + escapeHtml(step.name || "Tour step") + "</strong>";
      html += "<p class=\"hint\">" + escapeHtml(step.notes || "") + "</p>";
      html += "</div>";
    }
    var labels = story.section_labels || {};
    html += section(labels.story || "Story", story.mythology_summary);
    html += section(labels.science || "Scientific View", story.science_summary);
    if (root.ArchaeoastronomyView && root.ArchaeoastronomyView.onStory) {
      root.ArchaeoastronomyView.onStory(story);
    }
    html += renderSourceContext(story);
    html += renderProvenance(story);
    html += objectList("Major stars", story.major_objects);
    html += objectList("Notable deep-sky objects", story.notable_deep_sky_objects);
    html += renderSignals((tour && tour.signals) || story.signals);
    html += renderSpectra((tour && tour.spectra) || story.spectra);
    html += renderMedia(story.media);
    setBody(html);
    bindStoryActions();
    updateTourButtons(tour);
    if (els.tourStatus) {
      els.tourStatus.textContent = progress;
    }
    if (root.OfficialMedia && root.OfficialMedia.refreshStory) {
      if (step && step.name) lastSelection = Object.assign({}, lastSelection || {}, { name: step.name });
      root.OfficialMedia.refreshStory();
    }
  }

  function renderSourceContext(story) {
    var ctx = story.source_context || {};
    if (!ctx.people && !ctx.evidence_type && !ctx.title) return "";
    var compact = "<p class=\"hint\"><strong>People / tradition:</strong> " +
      escapeHtml(ctx.people || story.source_people || "") +
      (ctx.tradition ? " · " + escapeHtml(ctx.tradition) : "") + "</p>";
    if (ctx.evidence_type) {
      compact += "<p class=\"hint\"><strong>Evidence type:</strong> " + escapeHtml(ctx.evidence_type) + "</p>";
    }
    if (ctx.institution || ctx.title) {
      compact += "<p class=\"hint\"><strong>Source:</strong> " +
        escapeHtml(ctx.title || "") +
        (ctx.institution ? " — " + escapeHtml(ctx.institution) : "") +
        (ctx.date ? " (" + escapeHtml(ctx.date) + ")" : "") + "</p>";
    }
    if (ctx.note) {
      compact += "<p class=\"hint\">" + escapeHtml(ctx.note) + "</p>";
    }
    return "<details class=\"constellation-section\" open><summary>" +
      escapeHtml((story.section_labels || {}).sources || "Sources & Context") +
      "</summary>" + compact + "</details>";
  }

  function renderProvenance(story) {
    var sources = story.source_urls || [];
    var notes = story.source_notes || [];
    if (!sources.length && !notes.length) return "";
    var body = "";
    if (story.source_people || story.source_region) {
      body += "<p class=\"hint\">People / region: " +
        escapeHtml([story.source_people, story.source_region].filter(Boolean).join(" · ")) + "</p>";
    }
    if (story.source_quality) {
      body += "<p class=\"hint\">Source quality: " + escapeHtml(story.source_quality) + "</p>";
    }
    body += sources.map(function (src) {
      return "<p class=\"story-provenance\"><strong>" + escapeHtml(src.title) + "</strong> — " +
        escapeHtml(src.institution || "") + "<br>" + escapeHtml(src.supports || "") + "</p>";
    }).join("");
    if (notes.length) {
      body += "<ul class=\"hint\">" + notes.map(function (note) {
        return "<li>" + escapeHtml(note) + "</li>";
      }).join("") + "</ul>";
    }
    return "<details class=\"constellation-section\" open><summary>Source / provenance</summary>" + body + "</details>";
  }

  function section(title, text) {
    if (!text) return "";
    return "<details class=\"constellation-section\" open><summary>" + escapeHtml(title) +
      "</summary><p class=\"hint\">" + escapeHtml(text) + "</p></details>";
  }

  function objectList(title, items) {
    var rows = (items || []).map(function (obj) {
      return "<span class=\"event-chip\" title=\"" + escapeHtml(obj.notes || "") + "\">" +
        escapeHtml(obj.name) + "</span>";
    }).join("");
    if (!rows) rows = "<p class=\"hint\">None listed.</p>";
    return "<details class=\"constellation-section\"><summary>" + escapeHtml(title) +
      "</summary><div class=\"constellation-chip-row\">" + rows + "</div></details>";
  }

  function renderSignals(signals) {
    signals = signals || {};
    var ranked = signals.ranked || [];
    var body;
    if (!ranked.length) {
      body = "<p class=\"hint\">" + escapeHtml(signals.empty_message || "No curated Cosmic Signal for this story.") + "</p>";
    } else {
      body = "<p class=\"hint\">Listen to the Universe — nothing plays until you press Play.</p>" +
        ranked.map(function (entry, i) {
          return "<div class=\"constellation-signal\">" +
            "<div><strong>" + escapeHtml(entry.title) + "</strong> " +
            "<span class=\"event-chip\">" + escapeHtml(entry.relation_label || "Related") + "</span></div>" +
            "<p class=\"hint\">" + escapeHtml(entry.short_explanation || "") + "</p>" +
            "<p class=\"hint\">" + escapeHtml(entry.media_type || "") +
            (entry.conversion_method ? " · " + escapeHtml(entry.conversion_method) : "") + "</p>" +
            "<div class=\"button-row\">" +
            "<button type=\"button\" class=\"btn btn-primary btn-small\" data-cs-play=\"" + i + "\">Play Cosmic Signal</button>" +
            "<button type=\"button\" class=\"btn btn-secondary btn-small\" data-cs-stop=\"" + i + "\">Stop</button>" +
            "<button type=\"button\" class=\"btn btn-secondary btn-small\" data-cs-open=\"" + i + "\">Open in Cosmic Signal Deck</button>" +
            "</div></div>";
        }).join("");
    }
    return "<details class=\"constellation-section\" open><summary>Cosmic Signal</summary>" + body + "</details>";
  }

  function renderSpectra(spectra) {
    spectra = spectra || {};
    var ranked = spectra.ranked || [];
    var body = ranked.length
      ?         ranked.slice(0, 4).map(function (item, i) {
          return "<button type=\"button\" class=\"event-chip\" data-spec-open=\"" + i + "\">" +
            escapeHtml(item.title || item.id) + "</button>";
        }).join("")
      : "<p class=\"hint\">" + escapeHtml(spectra.empty_message || "No curated spectrum image for this story.") + "</p>";
    return "<details class=\"constellation-section\"><summary>Spectrum &amp; imagery</summary>" +
      "<div class=\"constellation-chip-row\">" + body + "</div>" +
      "<p class=\"hint\">Opens the existing Spectrum Gallery. Full NASA / MAST / ESASky tools stay in their panels.</p></details>";
  }

  function renderMedia(media) {
    media = media || {};
    var body = media.empty
      ? "<p class=\"hint\">" + escapeHtml(media.empty_message || "No local Solar System media for this constellation.") + "</p>"
      : (media.items || []).map(function (item) {
          return "<span class=\"event-chip\">" + escapeHtml(item.title || item.id) + "</span>";
        }).join("");
    return "<details class=\"constellation-section\"><summary>Local media</summary>" + body + "</details>";
  }

  function bindStoryActions() {
    if (!els.body) return;
    els.body.querySelectorAll("[data-cs-play]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var entry = lastSignals[Number(btn.getAttribute("data-cs-play"))];
        openDeck(entry, false);
        if (root.CartographyAudio) {
          root.CartographyAudio.acquire("cosmic_signal", {
            pause: function () { if (root.CartographyDeck && root.CartographyDeck.stop) root.CartographyDeck.stop(); },
            stop: function () { if (root.CartographyDeck && root.CartographyDeck.stop) root.CartographyDeck.stop(); },
          });
        }
        if (root.CartographyDeck && root.CartographyDeck.play) root.CartographyDeck.play();
      });
    });
    els.body.querySelectorAll("[data-cs-stop]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        if (root.CartographyDeck && root.CartographyDeck.stop) root.CartographyDeck.stop();
      });
    });
    els.body.querySelectorAll("[data-cs-open]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        openDeck(lastSignals[Number(btn.getAttribute("data-cs-open"))], true);
      });
    });
    els.body.querySelectorAll("[data-spec-open]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        if (root.CartographyDeck && root.CartographyDeck.openSpectrum) {
          root.CartographyDeck.openSpectrum(lastSpectra[Number(btn.getAttribute("data-spec-open"))]);
        }
      });
    });
  }

  function openDeck(entry, scroll) {
    if (!entry || !root.CartographyDeck || !root.CartographyDeck.openSignal) return;
    root.CartographyDeck.openSignal(entry, lastSignals);
    if (scroll && root.CartographyDeck.scrollToDeck) root.CartographyDeck.scrollToDeck();
  }

  function updateTourButtons(tour) {
    var active = !!(tour && tour.active);
    var start = $("btn-constellation-tour-start");
    var prev = $("btn-constellation-tour-prev");
    var next = $("btn-constellation-tour-next");
    var stop = $("btn-constellation-tour-stop");
    var ret = $("btn-constellation-return");
    if (start) start.disabled = active;
    if (prev) prev.disabled = !active || !tour.has_previous;
    if (next) next.disabled = !active || !tour.has_next;
    if (stop) stop.disabled = !active;
    if (ret) ret.disabled = !active;
  }

  async function tour(action, direction) {
    var url = "/api/constellation-tour/" + (action === "step" ? "step" : action);
    var payload = {};
    if (action === "start" && lastStory) payload.id = lastStory.id;
    if (action === "step") payload.direction = direction || "next";
    try {
      var data = await postJson(url, payload);
      if (!data) return;
      if (data.ok === false) {
        if (els.tourStatus) els.tourStatus.textContent = data.error || "Tour action failed.";
        return;
      }
      lastTour = data;
      if (lastStory) renderStory(lastStory, data.active ? data : null);
      if (data.selection && root.CartographySelection && root.CartographySelection.apply) {
        root.CartographySelection.apply(data.selection);
      }
      if (root.CartographyNarration && root.CartographyNarration.onTourResult) {
        root.CartographyNarration.onTourResult(action, data);
      }
    } catch (_err) {
      if (els.tourStatus) els.tourStatus.textContent = "Could not reach the constellation tour API.";
    }
  }

  async function refreshControls() {
    try {
      var resp = await fetch("/api/constellation-controls", { cache: "no-store" });
      var data = await resp.json();
      var controls = (data && data.controls) || {};
      Object.keys(controls).forEach(function (key) {
        var node = $("constellation-ctrl-" + key);
        if (node && typeof controls[key].value === "boolean") node.checked = controls[key].value;
      });
    } catch (_err) {
      /* Controls are optional when Remote Control properties are unavailable. */
    }
  }

  async function postJson(url, payload) {
    var resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload || {}),
    });
    return resp.json();
  }

  function setBody(html) {
    if (els.body) els.body.innerHTML = html;
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  root.ConstellationStory = {
    init: init,
    onTargetChange: onTargetChange,
    refreshContext: refreshContext,
    tour: tour,
    currentStory: function () { return lastStory; },
    hasNext: function () { return !!(lastTour && lastTour.active && lastTour.has_next); },
    relationLabel: function (value) {
      if (value === "exact") return "Exact";
      if (value === "related") return "Related";
      if (value === "general") return "General";
      return "";
    },
  };

  if (typeof module === "object" && module.exports) {
    module.exports = root.ConstellationStory;
  }

  if (typeof document !== "undefined" && document) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", init);
    } else if ($("constellation-story-card") || $("btn-open-constellation-story")) {
      init();
    }
  }
})(typeof self !== "undefined" ? self : this);
