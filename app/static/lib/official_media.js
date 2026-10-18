/* official_media.js
 *
 * Official Media Layer UI. Surfaces NASA / Chandra items without
 * replacing Cosmic Signal Deck or Spectrum Gallery. Nothing autoplays.
 */
(function (root) {
  "use strict";

  var lastSelection = null;
  var lastContext = null;
  var lastSearch = [];
  var featuredItem = null;

  function $(id) {
    return typeof document !== "undefined" && document && document.getElementById
      ? document.getElementById(id)
      : null;
  }

  function init() {
    bind();
  }

  function bind() {
    on("btn-media-search", "click", runManualSearch);
    on("official-media-query", "keydown", function (ev) {
      if (ev && ev.key === "Enter") {
        if (ev.preventDefault) ev.preventDefault();
        runManualSearch();
      }
    });
  }

  function on(id, type, fn) {
    var node = $(id);
    if (node) node.addEventListener(type, fn);
  }

  function onTargetChange(selection) {
    lastSelection = selection || null;
    refreshCard();
    refreshStory();
  }

  function objectName(selection, fallback) {
    selection = selection || lastSelection || {};
    return fallback || selection.name || selection.alt_name || "";
  }

  async function fetchContext(name) {
    var params = new URLSearchParams();
    if (name) params.set("object", name);
    var resp = await fetch("/api/media/context?" + params.toString(), { cache: "no-store" });
    return resp.json();
  }

  async function refreshCard() {
    var host = $("object-card-media");
    if (!host) return;
    var name = objectName();
    if (!name) {
      host.innerHTML = "";
      return;
    }
    try {
      var data = await fetchContext(name);
      lastContext = data;
      host.innerHTML = renderCardMedia(data);
      bindMediaActions(host);
    } catch (_err) {
      host.innerHTML = "<p class=\"hint\">Official media unavailable.</p>";
    }
  }

  async function refreshStory() {
    var host = $("constellation-official-media");
    if (!host) return;
    var name = objectName();
    if (!name) {
      host.innerHTML = "";
      return;
    }
    try {
      var data = await fetchContext(name);
      lastContext = data;
      host.innerHTML = renderStoryMedia(data);
      bindMediaActions(host);
    } catch (_err) {
      host.innerHTML = "<details class=\"constellation-section\" open><summary>Official Media</summary>" +
        "<p class=\"hint\">Official media unavailable.</p></details>";
    }
  }

  function renderCardMedia(data) {
    var exact = data && data.card_exact;
    var related = data && data.card_related;
    if (!exact && !related) {
      return "<p class=\"hint\">" + escapeHtml((data && data.empty_message) || "No official media for this object.") + "</p>";
    }
    var html = "";
    if (exact) html += compactItem(exact, true);
    if (related && (!exact || related.id !== exact.id)) html += compactItem(related, false);
    return html;
  }

  function compactItem(item, primary) {
    return "<div class=\"official-media-compact\">" +
      badges(item) +
      "<div><strong>" + escapeHtml(item.title) + "</strong></div>" +
      "<p class=\"hint\">" + escapeHtml(item.provider_label || item.provider || "") +
      (item.center ? " · " + escapeHtml(item.center) : "") + "</p>" +
      actionRow(item, primary) +
      "</div>";
  }

  function renderStoryMedia(data) {
    var featured = data && data.featured;
    var alternates = (data && data.alternates) || [];
    var body;
    if (!featured) {
      body = "<p class=\"hint\">" + escapeHtml((data && data.empty_message) || "No official media for this step.") + "</p>";
    } else {
      body = renderFeatured(featured) +
        (alternates.length ? "<div class=\"hint\">More official items</div>" +
          alternates.map(function (item) { return compactItem(item, false); }).join("") : "");
    }
    return "<details class=\"constellation-section\" open><summary>Official Media</summary>" + body + "</details>";
  }

  function renderFeatured(item) {
    featuredItem = item;
    var html = "<div class=\"official-media-feature\">";
    html += badges(item);
    html += "<div class=\"target-name\">" + escapeHtml(item.title) + "</div>";
    html += "<p class=\"hint\">" + escapeHtml(item.description || "") + "</p>";
    html += provenance(item);
    if (item.thumbnail_url && item.media_type === "image") {
      html += "<img class=\"official-media-thumb\" alt=\"\" src=\"" + escapeAttr(item.thumbnail_url) + "\">";
    }
    html += player(item);
    html += captionBlock(item);
    html += actionRow(item, true);
    html += "</div>";
    return html;
  }

  function player(item) {
    if (!item || !item.playable_inline || !item.media_url || item.reuse_cosmic_signal) {
      return "";
    }
    var poster = item.thumbnail_url || item.preview_url || "";
    if (item.media_type === "video" || /\.mp4|\.webm|\.m4v/i.test(item.media_url)) {
      return "<video class=\"official-media-player\" controls preload=\"metadata\"" +
        (poster ? " poster=\"" + escapeAttr(poster) + "\"" : "") +
        " data-autoplay=\"false\">" +
        "<source src=\"" + escapeAttr(item.media_url) + "\">" +
        (item.caption_url ? "<track kind=\"captions\" src=\"" + escapeAttr(item.caption_url) + "\" default>" : "") +
        "</video>";
    }
    if (item.media_type === "audio" || /\.mp3|\.m4a|\.wav/i.test(item.media_url)) {
      return "<audio class=\"official-media-player\" controls preload=\"metadata\" data-autoplay=\"false\">" +
        "<source src=\"" + escapeAttr(item.media_url) + "\"></audio>";
    }
    return "";
  }

  function captionBlock(item) {
    if (!item) return "";
    if (item.caption_available && item.caption_url) {
      return "<p class=\"hint\">Captions available from the official source.</p>";
    }
    if (item.description) {
      return "<details class=\"official-media-transcript\"><summary>Description / transcript note</summary>" +
        "<p class=\"hint\">" + escapeHtml(item.description) + "</p>" +
        "<p class=\"hint\">Full transcripts stay on the official source page when provided.</p></details>";
    }
    return "";
  }

  function provenance(item) {
    var bits = [
      item.provider_label || item.provider,
      item.media_type,
      item.relation,
      item.date_created,
      item.center,
    ].filter(Boolean);
    return "<p class=\"hint\">" + escapeHtml(bits.join(" · ")) +
      (item.provenance ? " — " + escapeHtml(item.provenance) : "") + "</p>" +
      (item.signal_category ? "<p class=\"hint\">What am I hearing / seeing? " +
        escapeHtml(signalLabel(item.signal_category)) + "</p>" : "");
  }

  function signalLabel(value) {
    if (value === "sonification") return "Sonification — a data translation, not a microphone recording.";
    if (value === "data_sonification") return "Sonification — a data translation, not a microphone recording.";
    if (value === "audification" || value === "data_audification") return "Audification of measured data.";
    if (value === "instrument_signal" || value === "direct_signal") return "Direct / measurement-derived signal.";
    if (value === "narrated_explainer") return "Narrated explainer. This is not the physical sound of the object.";
    if (value === "ordinary_video") return "Ordinary official video.";
    if (value === "ordinary_audio") return "Ordinary official audio.";
    return String(value || "").replace(/_/g, " ");
  }

  function badges(item) {
    return "<div class=\"official-media-badges\">" +
      "<span class=\"event-chip\">" + escapeHtml(item.provider_label || item.provider || "Official") + "</span>" +
      "<span class=\"event-chip\">" + escapeHtml(relationLabel(item.relation)) + "</span>" +
      "<span class=\"event-chip\">" + escapeHtml(item.media_type || "media") + "</span></div>";
  }

  function actionRow(item, primary) {
    var html = "<div class=\"button-row\">";
    if (item.reuse_cosmic_signal) {
      html += "<button type=\"button\" class=\"btn " + (primary ? "btn-primary" : "btn-secondary") +
        " btn-small\" data-om-cs=\"" + escapeAttr(item.cosmic_signal_id) + "\">Play Cosmic Signal</button>";
      html += "<button type=\"button\" class=\"btn btn-secondary btn-small\" data-om-cs-open=\"" +
        escapeAttr(item.cosmic_signal_id) + "\">Open in Cosmic Signal Deck</button>";
    } else if (item.playable_inline && item.media_url) {
      html += "<button type=\"button\" class=\"btn " + (primary ? "btn-primary" : "btn-secondary") +
        " btn-small\" data-om-view=\"" + escapeAttr(item.id) + "\">Play</button>";
    } else {
      html += "<button type=\"button\" class=\"btn " + (primary ? "btn-primary" : "btn-secondary") +
        " btn-small\" data-om-view=\"" + escapeAttr(item.id) + "\">View Media</button>";
    }
    if (item.spectrum_id) {
      html += "<button type=\"button\" class=\"btn btn-secondary btn-small\" data-om-spec=\"" +
        escapeAttr(item.spectrum_id) + "\">Open Spectrum Gallery</button>";
    }
    if (item.source_page_url) {
      html += "<a class=\"btn btn-secondary btn-small\" href=\"" + escapeAttr(item.source_page_url) +
        "\" target=\"_blank\" rel=\"noopener noreferrer\">Open Source</a>";
    }
    html += "</div>";
    return html;
  }

  function bindMediaActions(host) {
    if (!host) return;
    host.querySelectorAll("[data-om-cs]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        openCosmic(btn.getAttribute("data-om-cs"), true);
      });
    });
    host.querySelectorAll("[data-om-cs-open]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        openCosmic(btn.getAttribute("data-om-cs-open"), false);
      });
    });
    host.querySelectorAll("[data-om-spec]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        if (root.CartographyDeck && root.CartographyDeck.openSpectrum) {
          root.CartographyDeck.openSpectrum({ id: btn.getAttribute("data-om-spec") });
        }
      });
    });
    host.querySelectorAll("[data-om-view]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        showViewer(findItem(btn.getAttribute("data-om-view")));
      });
    });
  }

  function findItem(id) {
    if (featuredItem && featuredItem.id === id) return featuredItem;
    var pools = [];
    if (lastContext) {
      pools = pools.concat(lastContext.items || [], lastContext.alternates || [], [lastContext.featured, lastContext.card_exact, lastContext.card_related]);
    }
    pools = pools.concat(lastSearch);
    for (var i = 0; i < pools.length; i++) {
      if (pools[i] && pools[i].id === id) return pools[i];
    }
    return featuredItem;
  }

  function showViewer(item) {
    var viewer = $("official-media-viewer");
    if (!viewer || !item) return;
    viewer.hidden = false;
    viewer.innerHTML = renderFeatured(item);
    bindMediaActions(viewer);
    var media = viewer.querySelector("video, audio");
    if (media && typeof media.play === "function" && item.playable_inline && !item.reuse_cosmic_signal) {
      if (root.CartographyAudio) {
        root.CartographyAudio.acquire("official_media", {
          pause: function () { try { media.pause(); } catch (_err) { /* ignore */ } },
          stop: function () { try { media.pause(); media.currentTime = 0; } catch (_err) { /* ignore */ } },
        });
      }
      var playPromise = media.play();
      if (playPromise && playPromise.catch) playPromise.catch(function () {});
    }
  }

  async function openCosmic(signalId, play) {
    if (!root.CartographyDeck) return;
    var entry = { id: signalId };
    try {
      var name = objectName();
      if (name) {
        var resp = await fetch("/api/cosmic-signal-match?name=" + encodeURIComponent(name) + "&allow_featured=0", { cache: "no-store" });
        var data = await resp.json();
        var pool = [];
        if (data && data.primary) pool.push(data.primary);
        ["exact", "related_body", "related_mission", "featured", "available_signals", "ranked"].forEach(function (key) {
          pool = pool.concat((data && data[key]) || []);
        });
        var found = pool.find(function (item) { return item && item.id === signalId; });
        if (found) entry = found;
      }
    } catch (_err) {
      /* Deck open still proceeds with the curated id. */
    }
    if (root.CartographyDeck.openSignal) root.CartographyDeck.openSignal(entry, [entry]);
    if (play && root.CartographyDeck.play) {
      if (root.CartographyAudio) {
        root.CartographyAudio.acquire("cosmic_signal", {
          pause: function () { if (root.CartographyDeck.stop) root.CartographyDeck.stop(); },
          stop: function () { if (root.CartographyDeck.stop) root.CartographyDeck.stop(); },
        });
      }
      root.CartographyDeck.play();
    }
    if (root.CartographyDeck.scrollToDeck) root.CartographyDeck.scrollToDeck();
  }

  async function runManualSearch() {
    var input = $("official-media-query");
    var typeNode = $("official-media-type");
    var out = $("official-media-search-results");
    if (!input || !out) return;
    var query = String(input.value || "").trim();
    var mediaType = typeNode ? String(typeNode.value || "all") : "all";
    if (!query) {
      out.innerHTML = "<p class=\"hint\">Enter an object name. NASA media only — no web search.</p>";
      return;
    }
    try {
      var params = new URLSearchParams({ q: query, media_type: mediaType });
      var resp = await fetch("/api/media/search?" + params.toString(), { cache: "no-store" });
      var data = await resp.json();
      lastSearch = (data && data.items) || [];
      if (!lastSearch.length) {
        out.innerHTML = "<p class=\"hint\">" + escapeHtml((data && (data.empty_message || data.error)) || "No NASA results.") + "</p>";
        return;
      }
      out.innerHTML = lastSearch.map(function (item) { return compactItem(item, false); }).join("");
      bindMediaActions(out);
    } catch (_err) {
      out.innerHTML = "<p class=\"hint\">NASA media search is unavailable.</p>";
    }
  }

  function relationLabel(value) {
    if (value === "exact") return "Exact";
    if (value === "related") return "Related";
    if (value === "general") return "General";
    return "Official";
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function escapeAttr(value) {
    return escapeHtml(value);
  }

  root.OfficialMedia = {
    init: init,
    onTargetChange: onTargetChange,
    refreshCard: refreshCard,
    refreshStory: refreshStory,
    relationLabel: relationLabel,
    signalLabel: signalLabel,
    playerHtml: player,
    noAutoplay: true,
  };

  if (typeof module === "object" && module.exports) {
    module.exports = root.OfficialMedia;
  }

  if (typeof document !== "undefined" && document) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", init);
    } else if ($("object-card-media") || $("official-media-search-card")) {
      init();
    }
  }
})(typeof self !== "undefined" ? self : this);
