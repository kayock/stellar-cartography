/* archaeoastronomy.js
 *
 * Archaeoastronomy Visual Mode. Missing DOM nodes are ignored.
 * Stellarium time is never changed unless the user clicks a date button.
 */
(function (root) {
  "use strict";

  var lastVisual = null;
  var lastStoryId = null;
  var panelOpen = false;

  function $(id) {
    return typeof document !== "undefined" && document && document.getElementById
      ? document.getElementById(id)
      : null;
  }

  function init() {
    on("btn-archaeoastronomy", "click", function () {
      if (panelOpen) {
        closePanel();
        return;
      }
      var story = root.ConstellationStory && root.ConstellationStory.currentStory
        ? root.ConstellationStory.currentStory()
        : null;
      if (story && story.id) openVisual(story.id);
    });
    syncButton(null);
  }

  function on(id, type, fn) {
    var node = $(id);
    if (node) node.addEventListener(type, fn);
  }

  function eligibleStoryTypes() {
    return {
      archaeoastronomy: true,
      solar_alignment: true,
      lunar_alignment: true,
      architectural_alignment: true,
      horizon_calendar: true,
      solar_lunar_alignment: true,
    };
  }

  function isEligible(story) {
    if (!story) return false;
    if (story.archaeoastronomy_eligible === true) return true;
    return !!eligibleStoryTypes()[story.story_type];
  }

  function badgeLabel(level) {
    if (level === "strong_evidence") return "STRONG EVIDENCE";
    if (level === "scholarly_interpretation") return "SCHOLARLY INTERPRETATION";
    if (level === "disputed") return "DISPUTED";
    if (level === "speculative") return "SPECULATIVE";
    return "";
  }

  function primaryBadgeAllowed(level) {
    return level === "strong_evidence" || level === "scholarly_interpretation";
  }

  function syncButton(story) {
    var btn = $("btn-archaeoastronomy");
    if (!btn) return;
    var show = isEligible(story);
    btn.hidden = !show;
    btn.textContent = panelOpen ? "Hide Archaeoastronomy" : "View Archaeoastronomy";
    if (!show) closePanel();
  }

  function closePanel() {
    panelOpen = false;
    lastVisual = null;
    var panel = $("archaeoastronomy-panel");
    if (panel) panel.hidden = true;
    var body = $("archaeoastronomy-body");
    if (body) body.innerHTML = "";
    var btn = $("btn-archaeoastronomy");
    if (btn) btn.textContent = "View Archaeoastronomy";
  }

  async function openVisual(storyId) {
    lastStoryId = storyId;
    var panel = $("archaeoastronomy-panel");
    var status = $("archaeoastronomy-status");
    var body = $("archaeoastronomy-body");
    if (panel) panel.hidden = false;
    panelOpen = true;
    var btn = $("btn-archaeoastronomy");
    if (btn) btn.textContent = "Hide Archaeoastronomy";
    if (status) status.textContent = "Loading visual mode…";
    try {
      var resp = await fetch("/api/archaeoastronomy?id=" + encodeURIComponent(storyId), { cache: "no-store" });
      var data = await resp.json();
      lastVisual = data;
      if (!data || data.ok === false) {
        if (status) status.textContent = (data && data.error) || "No archaeoastronomy visual for this story.";
        if (body) body.innerHTML = "";
        return;
      }
      if (status) status.textContent = "";
      if (body) {
        body.innerHTML = renderPanel(data);
        bindPanel(data);
      }
    } catch (_err) {
      if (status) status.textContent = "Could not load archaeoastronomy visual mode.";
    }
  }

  function renderPanel(visual) {
    var html = "";
    html += "<p><span class=\"archaeo-badge\">" + escapeHtml(visual.confidence_label || badgeLabel(visual.confidence)) + "</span>";
    html += "<span class=\"archaeo-badge\">" + escapeHtml(visual.schematic_label || "interpretive schematic") + "</span></p>";
    html += renderSite(visual.site_context);
    html += renderSvg(visual);
    html += "<p class=\"hint\">" + escapeHtml(visual.precision_note || "") + "</p>";
    html += "<p class=\"hint\">" + escapeHtml(visual.horizon_note || "Idealized horizon. Local terrain elevation is not modeled.") + "</p>";
    html += renderClaims("Visual claims", visual.primary_claims || [], false);
    html += renderSources(visual.evidence_sources || []);
    if ((visual.research_context || []).length) {
      html += "<details class=\"constellation-section\"><summary>Research context (not settled conclusions)</summary>";
      html += renderClaims("", visual.research_context, true);
      html += "</details>";
    }
    html += renderTimeMachine(visual);
    return html;
  }

  function renderSite(site) {
    site = site || {};
    var rows = [
      ["Site", site.site],
      ["Culture", site.culture_label],
      ["Region", site.region],
      ["Date range", site.date_range],
      ["Evidence type", site.evidence_type],
      ["Institution", site.source_institution],
      ["Interpretation", site.interpretation_label || badgeLabel(site.interpretation_status)],
    ];
    if (site.coordinates) {
      rows.push([
        "Public coordinates",
        site.coordinates.latitude + ", " + site.coordinates.longitude +
          " (" + (site.coordinates.precision || "public_park_vicinity") + ")",
      ]);
      if (site.coordinates.note) rows.push(["Coordinate note", site.coordinates.note]);
    }
    var body = rows.filter(function (row) { return row[1]; }).map(function (row) {
      return "<dt>" + escapeHtml(row[0]) + "</dt><dd>" + escapeHtml(row[1]) + "</dd>";
    }).join("");
    return "<dl class=\"archaeo-site\">" + body + "</dl>";
  }

  function renderClaims(title, claims, research) {
    if (!claims || !claims.length) return "";
    var items = claims.map(function (claim) {
      var badgeClass = research || !primaryBadgeAllowed(claim.confidence) ? "archaeo-badge research" : "archaeo-badge";
      var sources = (claim.sources || []).map(function (src) {
        return escapeHtml(src.title) + " — " + escapeHtml(src.institution || "");
      }).join("; ");
      return "<p class=\"hint\"><span class=\"" + badgeClass + "\">" +
        escapeHtml(claim.confidence_label || badgeLabel(claim.confidence)) +
        "</span>" + escapeHtml(claim.label || "") +
        (sources ? "<br>Source: " + sources : "") + "</p>";
    }).join("");
    if (!title) return items;
    return "<div class=\"narration-label\">" + escapeHtml(title) + "</div>" + items;
  }

  function renderSources(sources) {
    if (!sources || !sources.length) return "";
    var body = sources.map(function (src) {
      return "<p class=\"story-provenance\"><strong>" + escapeHtml(src.title || "") + "</strong> — " +
        escapeHtml(src.institution || "") +
        (src.evidence_type ? "<br>Evidence: " + escapeHtml(src.evidence_type) : "") +
        (src.interpretation_label ? " · " + escapeHtml(src.interpretation_label) : "") + "</p>";
    }).join("");
    return "<div class=\"narration-label\">Evidence &amp; Sources</div>" + body;
  }

  function renderTimeMachine(visual) {
    var dates = visual.historical_dates || [];
    if (!dates.length) return "";
    var buttons = dates.map(function (date, i) {
      return "<button type=\"button\" class=\"btn btn-secondary\" data-archaeo-date=\"" + i + "\">View sky at historical date — " +
        escapeHtml(date.label || date.utc) + "</button>";
    }).join("");
    return "<div class=\"narration-label\">Sky Time Machine</div>" +
      "<p class=\"hint\">" + escapeHtml(visual.reconstruction_note || "astronomical reconstruction") + "</p>" +
      "<p class=\"hint\">Label: astronomical reconstruction. Stellarium changes only after you press a button.</p>" +
      "<div class=\"button-row\">" + buttons +
      "<button type=\"button\" class=\"btn btn-secondary\" id=\"btn-archaeo-now\">Restore Now</button></div>" +
      "<p class=\"hint\" id=\"archaeo-tm-status\"></p>";
  }

  function renderSvg(visual) {
    var mode = visual.visual_mode;
    if (mode === "fajada_schematic") return fajadaSvg(visual);
    if (mode === "cardinal_architecture") return chacoSvg(visual);
    if (mode === "horizon_calendar") return hollySvg(visual);
    return horizonSvg(visual);
  }

  function svgWrap(inner, label) {
    return "<svg class=\"archaeo-svg\" viewBox=\"0 0 520 220\" role=\"img\" aria-label=\"" +
      escapeHtml(label || "interpretive schematic") + "\">" + inner + "</svg>";
  }

  function fajadaSvg(visual) {
    var inner = "";
    inner += "<text x=\"16\" y=\"22\" fill=\"#c9c4e0\" font-size=\"13\">Fajada Butte — interpretive schematic</text>";
    inner += "<rect x=\"70\" y=\"50\" width=\"18\" height=\"130\" fill=\"#6b6288\"/>";
    inner += "<rect x=\"118\" y=\"40\" width=\"20\" height=\"150\" fill=\"#7c7399\"/>";
    inner += "<rect x=\"168\" y=\"56\" width=\"16\" height=\"124\" fill=\"#6b6288\"/>";
    inner += "<rect x=\"250\" y=\"70\" width=\"150\" height=\"120\" fill=\"#2a2540\" stroke=\"#8f89ad\"/>";
    inner += "<circle cx=\"310\" cy=\"120\" r=\"28\" fill=\"none\" stroke=\"#fbbf24\" stroke-width=\"2\"/>";
    inner += "<circle cx=\"310\" cy=\"120\" r=\"14\" fill=\"none\" stroke=\"#fbbf24\"/>";
    inner += "<circle cx=\"360\" cy=\"155\" r=\"12\" fill=\"none\" stroke=\"#fbbf24\"/>";
    inner += "<path d=\"M128 40 L300 118\" stroke=\"#fbbf24\" stroke-width=\"3\"/>";
    inner += "<text x=\"16\" y=\"208\" fill=\"#8f89ad\" font-size=\"11\">slabs · spirals · midday light path — not a measured reconstruction</text>";
    inner += solarTicks(visual, 16, 190);
    return svgWrap(inner, "Fajada Butte interpretive schematic");
  }

  function chacoSvg(visual) {
    var inner = "";
    inner += "<text x=\"16\" y=\"22\" fill=\"#c9c4e0\" font-size=\"13\">Chaco cardinal architecture — interpretive schematic</text>";
    inner += "<path d=\"M150 50 H370 Q410 50 410 90 V150 Q410 175 300 175 H150 Q110 175 110 130 V90 Q110 50 150 50 Z\" fill=\"#2a2540\" stroke=\"#a78bfa\"/>";
    inner += "<line x1=\"260\" y1=\"40\" x2=\"260\" y2=\"190\" stroke=\"#34d399\" stroke-width=\"2\"/>";
    inner += "<line x1=\"100\" y1=\"112\" x2=\"420\" y2=\"112\" stroke=\"#34d399\" stroke-width=\"2\"/>";
    inner += "<text x=\"248\" y=\"36\" fill=\"#34d399\" font-size=\"12\">N</text>";
    inner += "<text x=\"248\" y=\"208\" fill=\"#34d399\" font-size=\"12\">S</text>";
    inner += "<text x=\"424\" y=\"116\" fill=\"#34d399\" font-size=\"12\">E</text>";
    inner += "<text x=\"78\" y=\"116\" fill=\"#34d399\" font-size=\"12\">W</text>";
    inner += "<text x=\"16\" y=\"208\" fill=\"#8f89ad\" font-size=\"11\">sourced N/S and E/W axes only — lunar and niche-light claims omitted</text>";
    return svgWrap(inner, "Chaco cardinal orientation diagram");
  }

  function hollySvg(visual) {
    var inner = "";
    inner += "<text x=\"16\" y=\"22\" fill=\"#c9c4e0\" font-size=\"13\">Holly solstice panel — interpretive schematic</text>";
    inner += "<ellipse cx=\"150\" cy=\"120\" rx=\"55\" ry=\"70\" fill=\"#6b6288\"/>";
    inner += "<ellipse cx=\"230\" cy=\"118\" rx=\"50\" ry=\"68\" fill=\"#7c7399\"/>";
    inner += "<rect x=\"188\" y=\"55\" width=\"10\" height=\"120\" fill=\"#0b0912\"/>";
    inner += "<rect x=\"320\" y=\"80\" width=\"140\" height=\"90\" fill=\"#2a2540\" stroke=\"#8f89ad\"/>";
    inner += "<circle cx=\"370\" cy=\"125\" r=\"22\" fill=\"none\" stroke=\"#fbbf24\"/>";
    inner += "<circle cx=\"420\" cy=\"140\" r=\"12\" fill=\"none\" stroke=\"#fbbf24\"/>";
    inner += "<path d=\"M193 70 L370 125\" stroke=\"#fbbf24\" stroke-width=\"3\"/>";
    inner += "<text x=\"16\" y=\"208\" fill=\"#8f89ad\" font-size=\"11\">boulder gap · solstice beam · spirals — interpretive schematic</text>";
    inner += solarTicks(visual, 16, 190);
    return svgWrap(inner, "Holly solstice panel interpretive schematic");
  }

  function horizonSvg(visual) {
    var events = ((visual.solar_path || {}).events) || {};
    var inner = "";
    inner += "<text x=\"16\" y=\"22\" fill=\"#c9c4e0\" font-size=\"13\">Idealized solar / horizon diagram</text>";
    inner += "<path d=\"M30 160 Q260 40 490 160\" fill=\"none\" stroke=\"#8f89ad\" stroke-width=\"2\"/>";
    inner += "<line x1=\"30\" y1=\"170\" x2=\"490\" y2=\"170\" stroke=\"#2c2748\"/>";
    inner += "<text x=\"24\" y=\"188\" fill=\"#8f89ad\" font-size=\"11\">W</text>";
    inner += "<text x=\"248\" y=\"188\" fill=\"#8f89ad\" font-size=\"11\">S</text>";
    inner += "<text x=\"478\" y=\"188\" fill=\"#8f89ad\" font-size=\"11\">E</text>";
    inner += marker(events.summer_solstice, "summer solstice", "#fbbf24");
    inner += marker(events.equinox, "equinox", "#a78bfa");
    inner += marker(events.winter_solstice, "winter solstice", "#34d399");
    inner += "<circle cx=\"260\" cy=\"168\" r=\"4\" fill=\"#f2f0fb\"/>";
    inner += "<text x=\"16\" y=\"212\" fill=\"#8f89ad\" font-size=\"11\">idealized horizon — observer / site at center</text>";
    return svgWrap(inner, "Idealized horizon solar diagram");
  }

  function marker(event, label, color) {
    if (!event) return "";
    var az = Number(event.sunrise_azimuth_deg);
    if (!Number.isFinite(az)) return "";
    var x = 30 + ((az - 45) / 90) * 460;
    if (x < 40) x = 40;
    if (x > 480) x = 480;
    return "<circle cx=\"" + x.toFixed(1) + "\" cy=\"150\" r=\"5\" fill=\"" + color + "\"/>" +
      "<text x=\"" + (x - 28).toFixed(1) + "\" y=\"140\" fill=\"" + color + "\" font-size=\"10\">" + label + "</text>";
  }

  function solarTicks(visual, x, y) {
    var events = ((visual.solar_path || {}).events) || {};
    var bits = [];
    if (events.summer_solstice) bits.push("SS rise " + events.summer_solstice.sunrise_azimuth_deg + "°");
    if (events.equinox) bits.push("Eq " + events.equinox.sunrise_azimuth_deg + "°");
    if (events.winter_solstice) bits.push("WS rise " + events.winter_solstice.sunrise_azimuth_deg + "°");
    if (!bits.length) return "";
    return "<text x=\"" + x + "\" y=\"" + y + "\" fill=\"#8f89ad\" font-size=\"10\">idealized sunrise az: " +
      bits.join(" · ") + "</text>";
  }

  function bindPanel(visual) {
    var body = $("archaeoastronomy-body");
    if (!body) return;
    body.querySelectorAll("[data-archaeo-date]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var date = (visual.historical_dates || [])[Number(btn.getAttribute("data-archaeo-date"))];
        applyHistorical(date);
      });
    });
    var nowBtn = $("btn-archaeo-now");
    if (nowBtn) {
      nowBtn.addEventListener("click", function () {
        applyHistorical({ preset: "now", label: "Now" });
      });
    }
  }

  async function applyHistorical(date) {
    var status = $("archaeo-tm-status") || $("archaeoastronomy-status");
    if (!date) return;
    if (status) status.textContent = "Sending explicit Time Machine request…";
    var payload = date.preset === "now"
      ? { apply_time: true, preset: "now" }
      : { apply_time: true, apply_location: false, reconstruction: true, utc: date.utc };
    try {
      var resp = await fetch("/api/time-machine", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      var data = await resp.json();
      if (!data || data.ok === false) {
        if (status) status.textContent = (data && data.error) || "Time Machine rejected the request.";
        return;
      }
      var label = date.preset === "now"
        ? "Restored Now."
        : "Astronomical reconstruction applied. Modern planetarium simulation only.";
      if (status) status.textContent = label;
      if (root.ExperienceLayer && root.ExperienceLayer.refreshSkyState) {
        root.ExperienceLayer.refreshSkyState();
      }
    } catch (_err) {
      if (status) status.textContent = "Could not reach the local Time Machine API.";
    }
  }

  function onStory(story) {
    if (!story || story.id !== lastStoryId) closePanel();
    syncButton(story);
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  root.ArchaeoastronomyView = {
    init: init,
    onStory: onStory,
    openVisual: openVisual,
    closePanel: closePanel,
    isEligible: isEligible,
    badgeLabel: badgeLabel,
    primaryBadgeAllowed: primaryBadgeAllowed,
    currentVisual: function () { return lastVisual; },
    appliesTimeSilently: function () { return false; },
  };

  if (typeof module === "object" && module.exports) {
    module.exports = root.ArchaeoastronomyView;
  }

  if (typeof document !== "undefined" && document) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", init);
    } else if ($("btn-archaeoastronomy") || $("archaeoastronomy-panel")) {
      init();
    }
  }
})(typeof self !== "undefined" ? self : this);
