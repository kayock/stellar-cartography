/* gravitational_waves.js — interactive GW labs + event cards */
(function (root) {
  "use strict";

  var state = {
    payload: null,
    eventId: null,
    event: null,
    polarization: "plus",
    phase: 0,
    amplitude: 0.35,
    chirpProgress: 0,
    audioCtx: null,
    anim: null,
  };
  var els = {};

  function $(id) { return document.getElementById(id); }
  function escapeHtml(t) {
    return String(t == null ? "" : t)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
  function setStatus(m) { if (els.status) els.status.textContent = m || ""; }
  function on(id, evt, fn) { var n = $(id); if (n) n.addEventListener(evt, fn); }
  async function fetchJson(url, options) {
    var resp = await fetch(url, options || { cache: "no-store" });
    var data = await resp.json().catch(function () { return null; });
    return { ok: resp.ok, data: data };
  }
  function badge(cls) {
    return "<span class=\"archaeo-badge gw-class gw-class-" + escapeHtml(cls || "illustration") + "\">" +
      escapeHtml(String(cls || "illustration").replace(/_/g, " ").toUpperCase()) + "</span>";
  }

  async function init() {
    els.card = $("gravitational-waves-card");
    if (!els.card) return;
    els.status = $("gw-status");
    els.science = $("gw-science");
    els.legend = $("gw-legend");
    els.waveSvg = $("gw-wave-svg");
    els.ifoSvg = $("gw-ifo-svg");
    els.chirpSvg = $("gw-chirp-svg");
    els.waveCaption = $("gw-wave-caption");
    els.ifoCaption = $("gw-ifo-caption");
    els.chirpCaption = $("gw-chirp-caption");
    els.chirpAudioLabel = $("gw-chirp-audio-label");
    els.events = $("gw-events");
    els.detail = $("gw-detail");
    els.media = $("gw-media");
    els.network = $("gw-network");
    els.phase = $("gw-phase");
    els.amp = $("gw-amplitude");
    els.chirp = $("gw-chirp-time");
    els.ifo = $("gw-ifo-time");

    on("gw-pol-plus", "change", function () { if ($("gw-pol-plus").checked) { state.polarization = "plus"; refreshWave(); } });
    on("gw-pol-cross", "change", function () { if ($("gw-pol-cross").checked) { state.polarization = "cross"; refreshWave(); } });
    if (els.phase) els.phase.addEventListener("input", function () { state.phase = Number(els.phase.value) * Math.PI * 2 / 100; refreshWave(); });
    if (els.amp) els.amp.addEventListener("input", function () { state.amplitude = Number(els.amp.value) / 100; refreshWave(); });
    if (els.chirp) els.chirp.addEventListener("input", function () { state.chirpProgress = Number(els.chirp.value) / 100; refreshChirp(); });
    if (els.ifo) els.ifo.addEventListener("input", function () { refreshIfo(Number(els.ifo.value) / 100); });
    on("btn-gw-play-chirp", "click", playChirpTone);
    on("btn-gw-animate", "click", toggleAnimate);
    on("btn-gw-focus", "click", focusSelected);
    ["spacetime","interferometer","inspiral","chirp","gw150914","gw170817","network","multimessenger","closing"].forEach(function (seg) {
      on("btn-gw-" + seg, "click", function () { speakSegment(seg); });
    });
    on("btn-gw-stop-narration", "click", function () {
      if (root.CartographyNarration && root.CartographyNarration.stopNarration) root.CartographyNarration.stopNarration(false);
      setStatus("Narration stopped.");
    });

    try {
      var res = await fetchJson("/api/gravitational-waves");
      if (!res.ok || !res.data || !res.data.ok) { setStatus("Gravitational Waves data unavailable."); return; }
      state.payload = res.data;
      renderShell(res.data);
      await refreshWave();
      await refreshIfo(0);
      await refreshChirp();
      if ((res.data.events || []).length) await selectEvent(res.data.events[0].id);
      setStatus("Gravitational Waves ready. Narration and chirp tones stay silent until you press Listen / Play.");
    } catch (_e) {
      setStatus("Could not load Gravitational Waves.");
    }
  }

  function renderShell(data) {
    if (els.legend) {
      var legend = data.classification_legend || {};
      els.legend.innerHTML = Object.keys(legend).map(function (k) {
        return "<p class=\"hint\">" + badge(k) + " " + escapeHtml(legend[k]) + "</p>";
      }).join("");
    }
    if (els.science) {
      var s = data.science || {};
      els.science.innerHTML =
        "<p class=\"hint\"><strong>What are gravitational waves?</strong> " + escapeHtml(s.what_is || "") + "</p>" +
        "<p class=\"hint\"><strong>Not a rubber sheet:</strong> " + escapeHtml(s.not_rubber_sheet || "") + "</p>" +
        "<p class=\"hint\"><strong>Detection:</strong> " + escapeHtml(s.detection || "") + "</p>" +
        "<p class=\"hint\"><strong>Chirp:</strong> " + escapeHtml(s.chirp || "") + "</p>" +
        "<p class=\"hint\"><strong>Networks:</strong> " + escapeHtml(s.network || "") + "</p>" +
        "<p class=\"hint\"><strong>Multi-messenger:</strong> " + escapeHtml(s.multimessenger || "") + "</p>" +
        "<p class=\"hint\">" + badge("illustration") + " " + escapeHtml(data.illustrative_disclaimer || "") + "</p>";
    }
    if (els.network) {
      els.network.innerHTML = "<div class=\"narration-label\">Detector network</div>" +
        (data.detectors || []).map(function (d) {
          return "<span class=\"event-chip\">" + escapeHtml(d.name) + "</span>";
        }).join("") +
        "<p class=\"hint\">Timing and antenna patterns constrain a sky <em>region</em>, not always a single point.</p>";
    }
    if (els.events) {
      els.events.innerHTML = (data.events || []).map(function (ev) {
        return "<button type=\"button\" class=\"event-chip\" data-gw-event=\"" + escapeHtml(ev.id) + "\">" +
          escapeHtml(ev.short_name || ev.name) + " " + badge(ev.media_classification || "real_detector_data") + "</button>";
      }).join("");
      els.events.querySelectorAll("[data-gw-event]").forEach(function (btn) {
        btn.addEventListener("click", function () { selectEvent(btn.getAttribute("data-gw-event")); });
      });
    }
    if (els.chirpAudioLabel && data.chirp_lab) {
      els.chirpAudioLabel.innerHTML = badge("sonification") + " " + escapeHtml(data.chirp_lab.audio_label || "");
    }
  }

  async function refreshWave() {
    var res = await fetchJson("/api/gravitational-waves/wave?polarization=" +
      encodeURIComponent(state.polarization) + "&phase=" + encodeURIComponent(state.phase) +
      "&amplitude=" + encodeURIComponent(state.amplitude));
    if (!res.ok || !res.data || !res.data.ok || !els.waveSvg) return;
    var d = res.data;
    var html = "<rect class=\"gw-sky\" x=\"0\" y=\"0\" width=\"100\" height=\"100\"/>";
    html += "<text class=\"gw-badge\" x=\"3\" y=\"7\">" + escapeHtml(d.label || "ILLUSTRATIVE") + "</text>";
    (d.grid || []).forEach(function (p) {
      html += "<circle class=\"gw-grid\" cx=\"" + p.x + "\" cy=\"" + p.y + "\" r=\"0.7\"/>";
    });
    if ((d.points || []).length) {
      var path = d.points.map(function (p, i) { return (i ? "L" : "M") + p.x + " " + p.y; }).join(" ") + " Z";
      html += "<path class=\"gw-ring\" d=\"" + path + "\"/>";
    }
    els.waveSvg.innerHTML = html;
    if (els.waveCaption) {
      els.waveCaption.textContent = (d.polarization === "cross" ? "Cross polarization" : "Plus polarization") +
        " — deformations greatly exaggerated.";
    }
  }

  async function refreshIfo(progress) {
    var res = await fetchJson("/api/gravitational-waves/interferometer?progress=" + encodeURIComponent(progress || 0));
    if (!res.ok || !res.data || !res.data.ok || !els.ifoSvg) return;
    var phase = res.data.phase || {};
    var stretch = phase.id === "plus_stretch" ? 1.12 : (phase.id === "plus_squeeze" ? 0.9 : 1);
    var stretchY = phase.id === "plus_squeeze" ? 1.12 : (phase.id === "plus_stretch" ? 0.9 : 1);
    var html = "<rect class=\"gw-sky\" width=\"100\" height=\"100\"/>";
    html += "<text class=\"gw-badge\" x=\"3\" y=\"7\">" + escapeHtml(res.data.label || "") + "</text>";
    html += "<circle class=\"gw-laser\" cx=\"20\" cy=\"50\" r=\"2.2\"/>";
    html += "<text class=\"gw-label\" x=\"20\" y=\"44\">Laser</text>";
    html += "<rect class=\"gw-splitter\" x=\"38\" y=\"46\" width=\"6\" height=\"8\"/>";
    html += "<line class=\"gw-arm\" x1=\"44\" y1=\"50\" x2=\"" + (44 + 30 * stretch) + "\" y2=\"50\"/>";
    html += "<line class=\"gw-arm\" x1=\"41\" y1=\"46\" x2=\"41\" y2=\"" + (46 - 28 * stretchY) + "\"/>";
    html += "<rect class=\"gw-mirror\" x=\"" + (44 + 30 * stretch) + "\" y=\"47\" width=\"2\" height=\"6\"/>";
    html += "<rect class=\"gw-mirror\" x=\"38\" y=\"" + (46 - 28 * stretchY - 2) + "\" width=\"6\" height=\"2\"/>";
    html += "<circle class=\"gw-detector\" cx=\"20\" cy=\"68\" r=\"2.5\"/>";
    html += "<text class=\"gw-label\" x=\"20\" y=\"76\">Detector</text>";
    els.ifoSvg.innerHTML = html;
    if (els.ifoCaption) els.ifoCaption.textContent = phase.caption || "";
  }

  async function refreshChirp() {
    var res = await fetchJson("/api/gravitational-waves/chirp?progress=" + encodeURIComponent(state.chirpProgress || 0));
    if (!res.ok || !res.data || !res.data.ok || !els.chirpSvg) return;
    var samples = res.data.waveform_samples || [];
    var d = "";
    samples.forEach(function (v, i) {
      var x = 5 + (90 * i) / Math.max(1, samples.length - 1);
      var y = 50 - v * 40;
      d += (i ? " L" : "M") + x + " " + y;
    });
    var html = "<rect class=\"gw-sky\" width=\"100\" height=\"100\"/>";
    html += "<text class=\"gw-badge\" x=\"3\" y=\"7\">" + escapeHtml(res.data.label || "") + "</text>";
    html += "<path class=\"gw-wave-line\" d=\"" + d + "\"/>";
    els.chirpSvg.innerHTML = html;
    var stage = res.data.stage || {};
    if (els.chirpCaption) {
      els.chirpCaption.textContent = (stage.label || "") + " — ~" + (stage.freq_hz || "?") + " Hz illustrative tone. " + (stage.caption || "");
    }
    state._chirpTone = res.data.playable_tone;
  }

  function playChirpTone() {
    var tone = state._chirpTone;
    if (!tone) { setStatus("Chirp tone not ready."); return; }
    try {
      var Ctx = window.AudioContext || window.webkitAudioContext;
      if (!Ctx) { setStatus("Web Audio unavailable in this browser."); return; }
      if (!state.audioCtx) state.audioCtx = new Ctx();
      var ctx = state.audioCtx;
      var osc = ctx.createOscillator();
      var gain = ctx.createGain();
      osc.type = "sine";
      osc.frequency.value = Number(tone.freq_hz) || 220;
      gain.gain.value = Math.min(0.2, Number(tone.amp) || 0.1);
      osc.connect(gain); gain.connect(ctx.destination);
      osc.start();
      var dur = Number(tone.duration_sec) || 0.35;
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + dur);
      osc.stop(ctx.currentTime + dur + 0.02);
      setStatus("Played ILLUSTRATIVE SONIFICATION tone (not detector-band audio).");
    } catch (_e) {
      setStatus("Could not play illustrative tone.");
    }
  }

  function toggleAnimate() {
    if (state.anim) { cancelAnimationFrame(state.anim); state.anim = null; setStatus("Wave animation paused."); return; }
    function tick() {
      state.phase = (state.phase + 0.08) % (Math.PI * 2);
      if (els.phase) els.phase.value = String(Math.round(state.phase / (Math.PI * 2) * 100));
      refreshWave();
      state.anim = requestAnimationFrame(tick);
    }
    setStatus("Animating illustrative polarization (exaggerated).");
    tick();
  }

  async function selectEvent(eventId) {
    var res = await fetchJson("/api/gravitational-waves/event/" + encodeURIComponent(eventId));
    if (!res.ok || !res.data || !res.data.ok) { setStatus((res.data && res.data.error) || "Event unavailable."); return; }
    state.eventId = eventId;
    state.event = res.data.event;
    renderEvent(res.data.event);
    if (els.events) {
      els.events.querySelectorAll("[data-gw-event]").forEach(function (btn) {
        btn.classList.toggle("is-active", btn.getAttribute("data-gw-event") === eventId);
      });
    }
  }

  function renderEvent(ev) {
    if (!els.detail) return;
    var points = (ev.teaching_points || []).map(function (p) { return "<li>" + escapeHtml(p) + "</li>"; }).join("");
    var sources = (ev.sources || []).map(function (s) {
      return "<li>" + badge(s.classification || "real_detector_data") +
        " <a href=\"" + escapeHtml(s.url) + "\" target=\"_blank\" rel=\"noopener noreferrer\">" +
        escapeHtml(s.title) + "</a></li>";
    }).join("");
    els.detail.innerHTML =
      "<div class=\"target-name\">" + escapeHtml(ev.name) + "</div>" +
      "<p class=\"hint\">" + escapeHtml(ev.summary || "") + "</p>" +
      "<p class=\"hint\">Type: " + escapeHtml(ev.source_type || "") + " · Detected " + escapeHtml(ev.detection_date || "") + "</p>" +
      "<p class=\"hint\">Detectors: " + escapeHtml((ev.detectors || []).join(", ")) + "</p>" +
      "<p class=\"hint\"><strong>Localization:</strong> " + escapeHtml(ev.localization_note || "") + "</p>" +
      (points ? "<ul class=\"gw-points\">" + points + "</ul>" : "") +
      "<p class=\"hint\">Stellarium: " + (ev.stellarium_search
        ? ("<code>" + escapeHtml(ev.stellarium_search) + "</code>")
        : "no precise host (honest localization-only treatment)") + "</p>" +
      (ev.stellarium_note ? "<p class=\"hint\">" + escapeHtml(ev.stellarium_note) + "</p>" : "") +
      "<details open><summary>Sources</summary><ul>" + sources + "</ul></details>";
    var media = ev.media || {};
    if (els.media) {
      els.media.innerHTML = media.image_url
        ? ("<figure class=\"gw-figure\">" + badge(media.classification || "observation") +
          "<img src=\"" + escapeHtml(media.image_url) + "\" alt=\"" + escapeHtml(media.title || "") +
          "\" loading=\"lazy\" referrerpolicy=\"no-referrer\">" +
          "<figcaption class=\"hint\">" + escapeHtml(media.title || "") + " — " + escapeHtml(media.credit || "") +
          ". <a href=\"" + escapeHtml(media.source_page_url || "#") + "\" target=\"_blank\" rel=\"noopener noreferrer\">Source</a>. " +
          escapeHtml(media.license_note || "") + (media.note ? " " + escapeHtml(media.note) : "") +
          "</figcaption></figure>")
        : "<p class=\"hint\">No curated image.</p>";
    }
  }

  async function focusSelected() {
    if (!state.eventId) { setStatus("Select an event first."); return; }
    var res = await fetchJson("/api/gravitational-waves/focus", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ event_id: state.eventId, object_id: state.eventId }),
      cache: "no-store",
    });
    var data = res.data || {};
    setStatus(data.message || (data.focused ? "Focused." : "No Stellarium host / unavailable."));
    if (data.focused && root.ExperienceLayer && root.ExperienceLayer.refreshSkyState) root.ExperienceLayer.refreshSkyState();
  }

  async function speakSegment(segment) {
    var res = await fetchJson("/api/gravitational-waves/narration?segment=" + encodeURIComponent(segment));
    if (!res.ok || !res.data || !res.data.ok) { setStatus((res.data && res.data.error) || "Narration unavailable."); return; }
    setStatus("Narration ready: " + (res.data.title || segment) + ". Autoplay off.");
    if (root.CartographyNarration && root.CartographyNarration.speakExhibit) {
      root.CartographyNarration.speakExhibit(res.data.text || "", { title: res.data.title, kind: "gravitational_waves", segment: segment });
    }
  }

  function showFromExhibitStep(step) {
    if (!step) return;
    if (step.gravitational_waves_event_id) selectEvent(step.gravitational_waves_event_id);
    var card = $("gravitational-waves-card");
    if (card && typeof card.open === "boolean") card.open = true;
    if (card && card.scrollIntoView) card.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  root.GravitationalWaves = { init: init, showFromExhibitStep: showFromExhibitStep, selectEvent: selectEvent };
  if (typeof module !== "undefined" && module.exports) module.exports = root.GravitationalWaves;
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})(typeof window !== "undefined" ? window : globalThis);
