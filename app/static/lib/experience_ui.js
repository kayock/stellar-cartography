/* experience_ui.js
 *
 * Optional experience layer. Missing DOM nodes are ignored so existing
 * Node DOM-integration tests keep working.
 */
(function (root) {
  "use strict";
  var model = root.ExperienceModel || {};
  var els = {};
  var lastSky = null;
  var lastSelection = null;
  var lastSnapshotA = null;
  var sonifyHandle = null;
  var audioCtx = null;
  var formSeeded = false;

  function $(id) {
    return document.getElementById(id);
  }

  function init() {
    els.timeUtc = $("tm-utc");
    els.timeLat = $("tm-lat");
    els.timeLon = $("tm-lon");
    els.timeAlt = $("tm-alt");
    els.timeName = $("tm-name");
    els.timeStatus = $("tm-status");
    els.timeActive = $("tm-active");
    els.cardExtras = $("object-card-extras");
    els.motionSvg = $("motion-svg");
    els.motionNote = $("motion-note");
    els.spectrumAxis = $("spectrum-axis");
    els.sonifyStatus = $("sonify-status");
    els.sonifyPlay = $("btn-sonify-play");
    els.sonifyStop = $("btn-sonify-stop");
    els.sonifyVol = $("sonify-volume");
    els.postcardPreview = $("postcard-preview");
    els.compareOut = $("compare-out");
    els.eventStrip = $("event-strip");
    els.narration = $("narration-summary");
    els.uiSoundToggle = $("ui-sound-toggle");
    els.uiSoundVol = $("ui-sound-volume");
    bind();
    applyAudioPrefs();
    refreshSkyState();
    setInterval(refreshSkyState, 8000);
  }

  function bind() {
    on("btn-tm-use-current", "click", fillFromCurrent);
    on("btn-tm-now", "click", function () { applyMachine({ preset: "now", apply_time: true }); });
    on("btn-tm-year", "click", function () { applyMachine({ preset: "year_ago", apply_time: true }); });
    on("btn-tm-decade", "click", function () { applyMachine({ preset: "decade_ago", apply_time: true }); });
    on("btn-tm-apply", "click", function () {
      applyMachine({
        utc: val(els.timeUtc),
        latitude: val(els.timeLat),
        longitude: val(els.timeLon),
        altitude: val(els.timeAlt),
        name: val(els.timeName),
        apply_time: true,
        apply_location: true,
      });
    });
    on("btn-tm-apply-time", "click", function () {
      applyMachine({ utc: val(els.timeUtc), apply_time: true, apply_location: false });
    });
    on("btn-postcard-save", "click", savePostcard);
    on("btn-compare-store-a", "click", storeSnapshotA);
    on("btn-compare-run", "click", runCompare);
    on("btn-sonify-play", "click", playSonify);
    on("btn-sonify-stop", "click", stopSonify);
    on("btn-listen-hook", "click", showNarration);
    if (els.uiSoundToggle) els.uiSoundToggle.addEventListener("change", persistAudioPrefs);
    if (els.uiSoundVol) els.uiSoundVol.addEventListener("input", persistAudioPrefs);
  }

  function on(id, type, fn) {
    var node = $(id);
    if (node) node.addEventListener(type, fn);
  }

  function val(node) {
    return node ? String(node.value || "").trim() : "";
  }

  function setText(node, text) {
    if (node) node.textContent = text || "";
  }

  async function refreshSkyState() {
    try {
      var resp = await fetch("/api/sky-state", { cache: "no-store" });
      var data = await resp.json();
      lastSky = data.sky || null;
      lastSelection = data.selection || null;
      renderActive(data);
      renderMotion(data.motion);
      renderCardExtras(data.card);
      renderSpectrumAxis(data.spectrum);
      renderEvents(data.events);
      updateSonifyAvailability(data.sonify);
      if (!formSeeded && data.sky) {
        seedForm(data.sky);
        formSeeded = true;
      }
    } catch (_err) {
      setText(els.timeStatus, "Sky state unavailable.");
    }
  }

  function renderActive(data) {
    if (!els.timeActive) return;
    var sky = data.sky || {};
    var sel = data.selection || {};
    var nowLabel = sky.is_time_now ? "live clock (Now)" : "historical/future simulation";
    els.timeActive.innerHTML =
      "<div><strong>Active time:</strong> " + escapeHtml(sky.utc || "unavailable") + " — " + escapeHtml(nowLabel) + "</div>" +
      "<div><strong>Location:</strong> " + escapeHtml(sky.location_name || "unavailable") +
      (sky.latitude != null ? " (" + Number(sky.latitude).toFixed(3) + ", " + Number(sky.longitude).toFixed(3) + ")" : "") + "</div>" +
      "<div><strong>FoV:</strong> " + (sky.fov_deg != null ? Number(sky.fov_deg).toFixed(2) + "°" : "unavailable") + "</div>" +
      "<div><strong>Selected:</strong> " + escapeHtml(sel.name || sky.selection_heading || "none") + "</div>";
  }

  function renderCardExtras(card) {
    if (!els.cardExtras) return;
    if (!card || !card.ok || !card.fields || !card.fields.length) {
      els.cardExtras.innerHTML = "<p class=\"hint\">No extra object fields are available yet.</p>";
      return;
    }
    var media = (card.media || []).map(function (hint) {
      return "<p class=\"hint\">" + escapeHtml(hint.note || hint.label || "") + " Source: " + escapeHtml(hint.source || "") + ".</p>";
    }).join("");
    els.cardExtras.innerHTML =
      "<p class=\"hint\">Family: " + escapeHtml(card.family || "other") + ". " + escapeHtml(card.unavailable_note || "") + "</p>" +
      card.fields.map(function (f) {
        return "<div class=\"about-field\"><span class=\"about-label\">" + escapeHtml(f.label) +
          "</span><span class=\"about-value\">" + escapeHtml(String(f.value)) + "</span></div>";
      }).join("") + media;
  }

  function renderMotion(motion) {
    if (!els.motionNote) return;
    if (!motion || !motion.available) {
      setText(els.motionNote, (motion && motion.reason) || "Motion track unavailable for this target.");
      if (els.motionSvg) els.motionSvg.innerHTML = "";
      return;
    }
    setText(els.motionNote, motion.axis + " — " + motion.window + ". " + motion.note);
    if (!els.motionSvg) return;
    var poly = model.motionPolyline(motion.points, 320, 84);
    var labels = (motion.points || []).map(function (p, i) {
      var x = 10 + (i / Math.max(motion.points.length - 1, 1)) * 300;
      return "<text x=\"" + x + "\" y=\"12\" fill=\"#c9c4e0\" font-size=\"10\">" + escapeHtml(p.label) + "</text>";
    }).join("");
    els.motionSvg.setAttribute("viewBox", "0 0 320 84");
    els.motionSvg.innerHTML = labels + "<path d=\"" + poly.d + "\" fill=\"none\" stroke=\"#a78bfa\" stroke-width=\"2\" />";
  }

  function renderSpectrumAxis(spectrum) {
    if (!els.spectrumAxis) return;
    if (!spectrum || !spectrum.available) {
      els.spectrumAxis.innerHTML = "<p class=\"hint\">" + escapeHtml((spectrum && spectrum.empty_reason) || "No curated spectrum views.") + "</p>";
      return;
    }
    var marks = spectrum.marks || [];
    els.spectrumAxis.innerHTML =
      "<p class=\"hint\">" + escapeHtml(spectrum.axis_label) + "</p>" +
      "<div id=\"spectrum-readout\" class=\"hint\">Hover a wavelength view for source details.</div>" +
      "<div class=\"spectrum-mark-row\">" +
      marks.map(function (m, i) {
        return "<button type=\"button\" class=\"spectrum-mark" + (m.active ? " is-active" : "") +
          "\" data-spec-i=\"" + i + "\">" + escapeHtml(m.label || "view") + "</button>";
      }).join("") + "</div>";
    els.spectrumAxis.querySelectorAll(".spectrum-mark").forEach(function (btn) {
      btn.addEventListener("mouseenter", function () {
        var mark = marks[Number(btn.getAttribute("data-spec-i"))];
        var readout = $("spectrum-readout");
        if (!readout || !mark) return;
        readout.textContent = [mark.label, mark.observatory, mark.credits].filter(Boolean).join(" · ");
      });
    });
  }

  function renderEvents(events) {
    if (!els.eventStrip) return;
    if (!events || !events.available) {
      els.eventStrip.innerHTML = "<p class=\"hint\">" + escapeHtml((events && events.note) || "Event strip foundation only.") + "</p>";
      return;
    }
    els.eventStrip.innerHTML = (events.events || []).map(function (ev) {
      return "<div class=\"event-chip\">" + escapeHtml(ev.name || ev.kind) + "</div>";
    }).join("");
  }

  function updateSonifyAvailability(plan) {
    var available = !!(plan && plan.available);
    if (els.sonifyPlay) els.sonifyPlay.disabled = !available;
    if (els.sonifyStop) els.sonifyStop.disabled = !available;
    setText(els.sonifyStatus, available
      ? plan.mapping.disclaimer
      : ((plan && plan.reason) || "Data Sonification is disabled until numeric altitude data exists."));
    root._lastSonify = plan;
  }

  function seedForm(sky) {
    if (!sky) return;
    if (els.timeUtc && sky.utc) els.timeUtc.value = String(sky.utc).replace(/\.\d+Z$/, "Z");
    if (els.timeLat && sky.latitude != null) els.timeLat.value = Number(sky.latitude).toFixed(5);
    if (els.timeLon && sky.longitude != null) els.timeLon.value = Number(sky.longitude).toFixed(5);
    if (els.timeAlt && sky.altitude != null) els.timeAlt.value = sky.altitude;
    if (els.timeName && sky.location_name) els.timeName.value = sky.location_name;
  }

  function fillFromCurrent() {
    seedForm(lastSky);
    refreshSkyState().then(function () { seedForm(lastSky); });
    setText(els.timeStatus, "Form filled from the current Stellarium state. Press Apply to send changes.");
  }

  async function applyMachine(payload) {
    var check = model.validateTimeMachineForm ? model.validateTimeMachineForm(payload) : { ok: true };
    if (!check.ok) {
      setText(els.timeStatus, check.error);
      return;
    }
    try {
      var resp = await fetch("/api/time-machine", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      var data = await resp.json();
      if (!data.ok) {
        setText(els.timeStatus, data.error || "Time Machine apply failed.");
        return;
      }
      setText(els.timeStatus, "Applied. Stellarium is now at " + (data.sky && data.sky.utc ? data.sky.utc : "the requested state") + ".");
      beep("ok");
      refreshSkyState();
    } catch (_err) {
      setText(els.timeStatus, "Could not reach the local Time Machine API.");
    }
  }

  async function savePostcard() {
    try {
      var resp = await fetch("/api/postcard", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
      var data = await resp.json();
      if (!data.ok) return;
      if (els.postcardPreview) {
        els.postcardPreview.textContent = JSON.stringify(data, null, 2);
      }
      var blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      var a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = (model.postcardFilename && model.postcardFilename(data)) || "sky-postcard.json";
      a.click();
      URL.revokeObjectURL(a.href);
      downloadPostcardPng(data);
      beep("save");
    } catch (_err) {
      if (els.postcardPreview) els.postcardPreview.textContent = "Postcard save failed.";
    }
  }

  function downloadPostcardPng(data) {
    var canvas = document.createElement("canvas");
    canvas.width = 720;
    canvas.height = 420;
    var ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.fillStyle = "#131120";
    ctx.fillRect(0, 0, 720, 420);
    ctx.fillStyle = "#a78bfa";
    ctx.font = "bold 28px sans-serif";
    ctx.fillText("FOXAI Sky Postcard", 32, 50);
    ctx.fillStyle = "#f2f0fb";
    ctx.font = "20px sans-serif";
    ctx.fillText((data.selection && data.selection.name) || "No selection", 32, 100);
    ctx.font = "14px sans-serif";
    ctx.fillStyle = "#c9c4e0";
    var lines = [
      "UTC: " + ((data.sky && data.sky.utc) || "unavailable"),
      "Location: " + ((data.sky && data.sky.location_name) || "unavailable"),
      "RA/Dec: " + ((data.selection && data.selection.ra_sexagesimal) || "—") + "  " + ((data.selection && data.selection.dec_sexagesimal) || ""),
      "FoV: " + ((data.sky && data.sky.fov_deg) || "unavailable"),
      "Note: locally rendered metadata card",
    ];
    lines.forEach(function (line, i) { ctx.fillText(line, 32, 150 + i * 28); });
    canvas.toBlob(function (blob) {
      if (!blob) return;
      var a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "sky-postcard.png";
      a.click();
      URL.revokeObjectURL(a.href);
    });
  }

  function storeSnapshotA() {
    lastSnapshotA = { selection: lastSelection, sky: lastSky };
    if (els.compareOut) els.compareOut.textContent = "Snapshot A stored. Change time/target, then Compare.";
  }

  async function runCompare() {
    if (!lastSnapshotA) {
      if (els.compareOut) els.compareOut.textContent = "Store snapshot A first.";
      return;
    }
    try {
      var resp = await fetch("/api/compare", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ a: lastSnapshotA, b: { selection: lastSelection, sky: lastSky } }),
      });
      var data = await resp.json();
      if (!data.ok) return;
      els.compareOut.innerHTML = (data.rows || []).map(function (row) {
        return "<div class=\"about-field\"><span class=\"about-label\">" + escapeHtml(row.field) +
          "</span><span class=\"about-value\">" + escapeHtml(String(row.a)) + " → " + escapeHtml(String(row.b)) +
          (row.delta != null ? " (Δ " + Number(row.delta).toFixed(3) + ")" : "") + "</span></div>";
      }).join("");
    } catch (_err) {
      if (els.compareOut) els.compareOut.textContent = "Compare failed.";
    }
  }

  function openSonifyCard() {
    var card = $("sonify-card");
    if (card) card.open = true;
    if (card && card.scrollIntoView) card.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function playSonify() {
    var plan = root._lastSonify;
    if (!plan || !plan.available) return;
    stopSonify();
    var Ctx = root.AudioContext || root.webkitAudioContext;
    if (!Ctx) {
      setText(els.sonifyStatus, "Web Audio is not available in this browser.");
      return;
    }
    audioCtx = new Ctx();
    var master = audioCtx.createGain();
    var vol = els.sonifyVol ? Number(els.sonifyVol.value) : 0.2;
    master.gain.value = Number.isFinite(vol) ? vol : 0.2;
    master.connect(audioCtx.destination);
    var samples = model.sonifyFrequencies ? model.sonifyFrequencies(plan.samples) : plan.samples;
    var start = audioCtx.currentTime + 0.05;
    samples.forEach(function (sample, i) {
      var osc = audioCtx.createOscillator();
      var g = audioCtx.createGain();
      osc.type = "sine";
      osc.frequency.value = sample.frequency_hz;
      g.gain.value = 0.08 + (sample.value || 0) * 0.12;
      osc.connect(g);
      g.connect(master);
      var t0 = start + (sample.t * (plan.duration_sec || 4));
      var t1 = start + (((samples[i + 1] && samples[i + 1].t) || 1) * (plan.duration_sec || 4));
      osc.start(t0);
      osc.stop(Math.max(t0 + 0.05, t1));
    });
    sonifyHandle = audioCtx;
    if (root.CartographyAudio) {
      root.CartographyAudio.acquire("data_sonification", {
        pause: stopSonify,
        stop: stopSonify,
      });
    }
    setText(els.sonifyStatus, plan.mapping.disclaimer + " Playing.");
  }

  function stopSonify() {
    if (audioCtx) {
      try { audioCtx.close(); } catch (_err) {}
      audioCtx = null;
    }
    sonifyHandle = null;
    var plan = root._lastSonify;
    setText(els.sonifyStatus, plan && plan.mapping
      ? plan.mapping.disclaimer
      : "Data Sonification stopped.");
  }

  async function showNarration() {
    try {
      var resp = await fetch("/api/narration", { cache: "no-store" });
      var data = await resp.json();
      if (els.narration) {
        els.narration.textContent = (data.label || "Cartography Narration") + ": " + data.summary;
      }
    } catch (_err) {
      if (els.narration) els.narration.textContent = "Narration hook unavailable.";
    }
  }

  function audioPrefs() {
    return model.parseAudioPrefs ? model.parseAudioPrefs(localStorage.getItem("sc-ui-audio")) : { uiSounds: false, volume: 0.25 };
  }

  function applyAudioPrefs() {
    var prefs = audioPrefs();
    if (els.uiSoundToggle) els.uiSoundToggle.checked = prefs.uiSounds;
    if (els.uiSoundVol) els.uiSoundVol.value = String(prefs.volume);
  }

  function persistAudioPrefs() {
    var prefs = {
      uiSounds: !!(els.uiSoundToggle && els.uiSoundToggle.checked),
      volume: els.uiSoundVol ? Number(els.uiSoundVol.value) : 0.25,
    };
    localStorage.setItem("sc-ui-audio", JSON.stringify(prefs));
  }

  function beep(kind) {
    var prefs = audioPrefs();
    if (!prefs.uiSounds) return;
    var Ctx = root.AudioContext || root.webkitAudioContext;
    if (!Ctx) return;
    var ctx = new Ctx();
    var osc = ctx.createOscillator();
    var g = ctx.createGain();
    osc.type = "sine";
    osc.frequency.value = kind === "save" ? 520 : kind === "select" ? 440 : 494;
    g.gain.value = Math.min(0.15, prefs.volume);
    osc.connect(g);
    g.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 0.09);
    osc.onended = function () { ctx.close(); };
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function onTargetChange() {
    beep("select");
    refreshSkyState();
  }

  root.ExperienceLayer = {
    init: init,
    onTargetChange: onTargetChange,
    refreshSkyState: refreshSkyState,
    applyTimeMachine: applyMachine,
    playSonify: playSonify,
    stopSonify: stopSonify,
    openSonifyCard: openSonifyCard,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else if ($("tm-status") || $("btn-tm-apply")) {
    init();
  }
})(typeof self !== "undefined" ? self : this);
