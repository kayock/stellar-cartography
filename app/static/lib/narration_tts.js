/* narration_tts.js
 *
 * Cartography Narration controls. Text comes from /api/narration.
 * Audio comes from /api/tts/synthesize. Nothing autoplays.
 */
(function (root) {
  "use strict";

  var STORAGE_PROVIDER = "sc-tts-provider";
  var STORAGE_VOICE = "sc-tts-voice";
  var LABEL = "Cartography Narration";
  var els = {};
  var state = {
    playing: false,
    paused: false,
    narratedTour: false,
    awaitingOverview: false,
    objectUrl: null,
    lastText: "",
    providers: [],
  };
  var autoAdvanceTimer = null;

  function $(id) {
    return typeof document !== "undefined" && document && document.getElementById
      ? document.getElementById(id)
      : null;
  }

  function init() {
    els.panel = $("constellation-story-card");
    els.status = $("tts-provider-status");
    els.script = $("narration-script");
    els.playStatus = $("narration-status");
    els.provider = $("tts-provider");
    els.voice = $("tts-voice");
    els.audio = $("tts-audio");
    els.volume = $("tts-volume");
    els.autoAdvance = $("tts-auto-advance");
    els.tell = $("btn-tell-story");
    els.narrated = $("btn-narrated-tour");
    els.pause = $("btn-narration-pause");
    els.resume = $("btn-narration-resume");
    els.stop = $("btn-narration-stop");
    if (els.autoAdvance) els.autoAdvance.checked = false;
    restorePrefs();
    bind();
    if (els.panel) refreshProviders();
    updateButtons();
  }

  function bind() {
    on("btn-tell-story", "click", tellStory);
    on("btn-narrated-tour", "click", startNarratedTour);
    on("btn-narration-pause", "click", pauseNarration);
    on("btn-narration-resume", "click", resumeNarration);
    on("btn-narration-stop", "click", function () { stopNarration(false); });
    if (els.provider) els.provider.addEventListener("change", onProviderChange);
    if (els.voice) els.voice.addEventListener("change", persistPrefs);
    if (els.volume && els.audio) {
      els.volume.addEventListener("input", function () {
        els.audio.volume = Number(els.volume.value);
      });
    }
    if (els.audio) {
      els.audio.autoplay = false;
      els.audio.addEventListener("ended", onAudioEnded);
    }
    if (els.panel) {
      els.panel.addEventListener("toggle", function () {
        if (els.panel.open) refreshProviders();
        else stopNarration(true);
      });
    }
  }

  function on(id, type, fn) {
    var node = $(id);
    if (node) node.addEventListener(type, fn);
  }

  function restorePrefs() {
    try {
      var provider = localStorage.getItem(STORAGE_PROVIDER);
      var voice = localStorage.getItem(STORAGE_VOICE);
      if (els.provider && provider) els.provider.value = provider;
      if (els.voice && voice) els.voice.value = voice;
    } catch (_err) { /* localStorage may be blocked */ }
  }

  function persistPrefs() {
    try {
      if (els.provider) localStorage.setItem(STORAGE_PROVIDER, els.provider.value);
      if (els.voice && els.voice.value) localStorage.setItem(STORAGE_VOICE, els.voice.value);
    } catch (_err) { /* localStorage may be blocked */ }
  }

  function onProviderChange() {
    persistPrefs();
    renderVoices();
    renderProviderStatus();
  }

  async function refreshProviders() {
    try {
      var resp = await fetch("/api/tts/providers", { cache: "no-store" });
      var data = await resp.json();
      state.providers = (data && data.providers) || [];
      renderVoices();
      renderProviderStatus();
    } catch (_err) {
      setStatus(els.status, "Voice provider status is unavailable. Story text remains readable.");
    }
  }

  function renderVoices() {
    if (!els.voice) return;
    var spec = currentProvider();
    var voices = (spec && spec.voices) || [];
    els.voice.innerHTML = "";
    if (voices.length <= 1) {
      els.voice.hidden = true;
      return;
    }
    els.voice.hidden = false;
    voices.forEach(function (voice) {
      var opt = document.createElement("option");
      opt.value = voice;
      opt.textContent = voice;
      els.voice.appendChild(opt);
    });
    try {
      var stored = localStorage.getItem(STORAGE_VOICE);
      if (stored && voices.indexOf(stored) !== -1) els.voice.value = stored;
    } catch (_err) { /* ignore */ }
  }

  function renderProviderStatus() {
    if (!els.status) return;
    if (!state.providers.length) {
      els.status.textContent = "";
      return;
    }
    els.status.textContent = state.providers.map(function (item) {
      return (item.label || item.id) + ": " + (item.available ? "Available" : "Unavailable");
    }).join(" · ");
  }

  function currentProvider() {
    var id = els.provider ? els.provider.value : "father_fox";
    return state.providers.filter(function (item) { return item.id === id; })[0] || { id: id, label: id, available: true, voices: [] };
  }

  async function tellStory() {
    state.narratedTour = false;
    state.awaitingOverview = false;
    await speakKind("constellation_overview");
  }

  async function startNarratedTour() {
    if (!root.ConstellationStory || !root.ConstellationStory.tour) return;
    state.narratedTour = true;
    state.awaitingOverview = true;
    await root.ConstellationStory.tour("start");
    await speakKind("constellation_overview");
  }

  async function speakKind(kind) {
    var story = root.ConstellationStory && root.ConstellationStory.currentStory
      ? root.ConstellationStory.currentStory()
      : null;
    var url = "/api/narration?kind=" + encodeURIComponent(kind);
    if (story && story.id) url += "&constellation=" + encodeURIComponent(story.id);
    var exhibit = root.CartographyExhibit && root.CartographyExhibit.current
      ? root.CartographyExhibit.current()
      : null;
    if (kind === "exhibit_step" && exhibit) {
      url += "&exhibit=" + encodeURIComponent(exhibit.exhibit_id || "");
      if (typeof exhibit.step_index === "number") url += "&step=" + encodeURIComponent(String(exhibit.step_index));
    }
    try {
      var resp = await fetch(url, { cache: "no-store" });
      var data = await resp.json();
      await speakText((data && data.text) || "", kind);
    } catch (_err) {
      setStatus(els.playStatus, "Could not load Cartography narration text. The story remains visible.");
    }
  }

  async function speakExhibit(text, meta) {
    state.narratedTour = false;
    state.awaitingOverview = false;
    await speakText(text || "", "exhibit_step");
    if (meta && meta.exhibitId) {
      state.lastExhibit = meta;
    }
  }

  async function speakText(text, context) {
    stopNarration(true);
    state.lastText = text || "";
    if (els.script) els.script.textContent = LABEL + "\n" + state.lastText;
    var spec = currentProvider();
    if (spec && spec.available === false) {
      setStatus(els.playStatus, (spec.label || spec.id) + " unavailable. Retry, switch voice, or continue with the written story.");
      updateButtons();
      return;
    }
    if (!text) {
      setStatus(els.playStatus, "No narration text is available.");
      return;
    }
    setStatus(els.playStatus, "Preparing " + LABEL + "…");
    try {
      var resp = await fetch("/api/tts/synthesize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: text,
          provider: spec.id || "father_fox",
          voice: els.voice && !els.voice.hidden ? els.voice.value : undefined,
          context: context || "constellation_overview",
        }),
      });
      var data = await resp.json();
      if (!data || !data.ok) {
        setStatus(els.playStatus, (data && data.error) || "Voice unavailable. The written story remains available.");
        updateButtons();
        return;
      }
      playAudio(data);
    } catch (_err) {
      setStatus(els.playStatus, "Voice unavailable. The written story remains available.");
      updateButtons();
    }
  }

  function playAudio(data) {
    if (!els.audio) return;
    clearObjectUrl();
    var binary = atob(data.audio_base64 || "");
    var bytes = new Uint8Array(binary.length);
    for (var i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
    var blob = new Blob([bytes], { type: data.mime_type || "audio/wav" });
    state.objectUrl = URL.createObjectURL(blob);
    els.audio.src = state.objectUrl;
    els.audio.autoplay = false;
    els.audio.volume = els.volume ? Number(els.volume.value) : 0.8;
    if (root.CartographyAudio) {
      root.CartographyAudio.acquire("narration", {
        pause: pauseNarration,
        stop: function () { stopNarration(true); },
        resume: resumeNarration,
      });
    }
    var playPromise = els.audio.play();
    if (playPromise && playPromise.catch) {
      playPromise.catch(function () {
        setStatus(els.playStatus, "Browser blocked audio playback. Press Tell Me the Story again.");
      });
    }
    state.playing = true;
    state.paused = false;
    setStatus(els.playStatus, LABEL + " · Voice: " + providerLabel());
    updateButtons();
  }

  function pauseNarration() {
    if (els.audio && !els.audio.paused) els.audio.pause();
    state.playing = false;
    state.paused = true;
    clearAdvance();
    setStatus(els.playStatus, LABEL + " paused.");
    updateButtons();
  }

  function resumeNarration() {
    if (!els.audio) return;
    var playPromise = els.audio.play();
    if (playPromise && playPromise.catch) playPromise.catch(function () {});
    state.playing = true;
    state.paused = false;
    setStatus(els.playStatus, LABEL + " · Voice: " + providerLabel());
    updateButtons();
  }

  function stopNarration(silent) {
    clearAdvance();
    if (els.audio) {
      try { els.audio.pause(); } catch (_err) { /* ignore */ }
      els.audio.removeAttribute("src");
      if (els.audio.load) els.audio.load();
    }
    clearObjectUrl();
    state.playing = false;
    state.paused = false;
    if (!silent) {
      state.narratedTour = false;
      state.awaitingOverview = false;
      setStatus(els.playStatus, LABEL + " stopped.");
    }
    updateButtons();
    fetch("/api/tts/stop", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" }).catch(function () {});
  }

  function onAudioEnded() {
    state.playing = false;
    state.paused = false;
    updateButtons();
    setStatus(els.playStatus, LABEL + " finished.");
    if (root.CartographyExhibit && root.CartographyExhibit.onNarrationEnded) {
      root.CartographyExhibit.onNarrationEnded();
    }
    if (!state.narratedTour) return;
    if (state.awaitingOverview) {
      state.awaitingOverview = false;
      if (!autoAdvanceEnabled()) return;
      advanceTour();
      return;
    }
    if (autoAdvanceEnabled()) {
      autoAdvanceTimer = setTimeout(advanceTour, 800);
    }
  }

  function advanceTour() {
    if (!root.ConstellationStory || !root.ConstellationStory.tour) return;
    if (!root.ConstellationStory.hasNext || !root.ConstellationStory.hasNext()) return;
    root.ConstellationStory.tour("step", "next");
  }

  function onTourResult(action, tour) {
    if (action === "stop") {
      state.narratedTour = false;
      state.awaitingOverview = false;
      stopNarration(true);
      return;
    }
    if (!state.narratedTour) return;
    if (action === "step") {
      stopNarration(true);
      speakKind("tour_step");
    }
  }

  function onConstellationChange() {
    stopNarration(true);
    state.narratedTour = false;
    state.awaitingOverview = false;
  }

  function autoAdvanceEnabled() {
    return !!(els.autoAdvance && els.autoAdvance.checked);
  }

  function nextNarrationAction(flags) {
    flags = flags || {};
    if (flags.action === "stop") return "restore_tour";
    if (!flags.narratedTour) return "idle";
    if (flags.action === "step") return "speak_tour_step";
    if (!flags.ended) return "wait";
    if (flags.awaitingOverview) return flags.autoAdvance ? "advance" : "wait";
    return flags.autoAdvance ? "advance" : "wait";
  }

  function providerLabel() {
    var spec = currentProvider();
    return spec.label || spec.id || "local voice";
  }

  function updateButtons() {
    if (els.pause) els.pause.disabled = !state.playing;
    if (els.resume) els.resume.disabled = !state.paused;
    if (els.stop) els.stop.disabled = !state.playing && !state.paused;
  }

  function setStatus(node, text) {
    if (node) node.textContent = text;
  }

  function clearAdvance() {
    if (autoAdvanceTimer) {
      clearTimeout(autoAdvanceTimer);
      autoAdvanceTimer = null;
    }
  }

  function clearObjectUrl() {
    if (state.objectUrl) {
      try { URL.revokeObjectURL(state.objectUrl); } catch (_err) { /* ignore */ }
      state.objectUrl = null;
    }
  }

  root.CartographyNarration = {
    LABEL: LABEL,
    noAutoplay: true,
    defaultAutoAdvance: false,
    init: init,
    tellStory: tellStory,
    startNarratedTour: startNarratedTour,
    refreshProviders: refreshProviders,
    pauseNarration: pauseNarration,
    resumeNarration: resumeNarration,
    stopNarration: stopNarration,
    onTourResult: onTourResult,
    onConstellationChange: onConstellationChange,
    speakKind: speakKind,
    speakExhibit: speakExhibit,
    autoAdvanceEnabled: autoAdvanceEnabled,
    nextNarrationAction: nextNarrationAction,
    isPlaying: function () { return state.playing; },
    isNarratedTour: function () { return state.narratedTour; },
    lastText: function () { return state.lastText; },
  };

  if (typeof module === "object" && module.exports) {
    module.exports = root.CartographyNarration;
  }

  if (typeof document !== "undefined" && document) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", init);
    } else if ($("constellation-narration-panel") || $("btn-tell-story")) {
      init();
    }
  }
})(typeof self !== "undefined" ? self : this);
