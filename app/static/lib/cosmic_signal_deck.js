"use strict";

/* Cosmic Signal Deck pure helpers. Runtime URL host allow-lists come from
 * the local registry API; this client validates only the initial URL and
 * deliberately does not attempt to enforce redirect chains. */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.CosmicSignalDeck = factory();
})(typeof self !== "undefined" ? self : this, function () {
  const FEATURED_PREF_KEY = "cosmicSignalAllowFeatured";
  const MAX_URL_LEN = 2000;
  const UNSAFE_URL_CHARS = /[\x00-\x08\x0b\x0c\x0e-\x1f\s"'<>]/;

  function createRequestState() {
    return { generation: 0, inFlightKey: null, activeTargetKey: null, currentEntry: null };
  }

  function beginRequest(state, targetKey) {
    state.generation += 1;
    state.inFlightKey = targetKey || null;
    state.activeTargetKey = targetKey || null;
    return state.generation;
  }

  function isStaleResponse(state, generation) {
    return !state || generation !== state.generation;
  }

  function resetRequestState(state) {
    state.generation += 1;
    state.inFlightKey = null;
    state.activeTargetKey = null;
    state.currentEntry = null;
    return state.generation;
  }

  function getAllowFeatured(storage) {
    try {
      const value = (storage || (typeof localStorage !== "undefined" ? localStorage : null)).getItem(FEATURED_PREF_KEY);
      return value !== "false";
    } catch (_err) {
      return true;
    }
  }

  function setAllowFeatured(allowFeatured, storage) {
    try {
      (storage || (typeof localStorage !== "undefined" ? localStorage : null)).setItem(
        FEATURED_PREF_KEY,
        allowFeatured ? "true" : "false"
      );
    } catch (_err) {
      /* Preference persistence is optional. */
    }
  }

  function buildMatchUrl(name, altName, allowFeatured) {
    const params = new URLSearchParams({
      name: name || "",
      alt_name: altName || "",
      allow_featured: allowFeatured ? "1" : "0",
    });
    return "/api/cosmic-signal-match?" + params.toString();
  }

  function isAllowedUrl(url, hostSet) {
    if (typeof url !== "string" || !url || url.length > MAX_URL_LEN || UNSAFE_URL_CHARS.test(url)) return false;
    try {
      const parsed = new URL(url);
      if (parsed.protocol !== "https:" || parsed.username || parsed.password) return false;
      const hosts = new Set(Array.from(hostSet || []).filter((host) => typeof host === "string").map((host) => host.toLowerCase()));
      return hosts.has(parsed.hostname.toLowerCase());
    } catch (_err) {
      return false;
    }
  }

  function mediaTypeLabel(mediaType) {
    const labels = {
      instrument_signal: "Instrument signal",
      data_audification: "Data audification",
      data_sonification: "Data sonification",
      mission_audio: "Mission audio",
      historical_recording: "Historical recording",
      contextual_audio: "Contextual audio",
    };
    return labels[mediaType] || "Curated signal";
  }

  function relevanceLabel(relevance) {
    const labels = {
      exact_target: "Exact target",
      related_body: "Related body",
      related_mission: "Related mission",
      general_featured: "Featured signal",
    };
    return labels[relevance] || "Curated signal";
  }

  function buildLoadingView(target) {
    return {
      mode: "loading",
      title: "Cosmic Signal Deck",
      subtitle: target && target.name ? "Finding a curated signal for " + target.name + "…" : "Finding a curated signal…",
    };
  }

  function buildEmptyView(payload) {
    return {
      mode: "empty",
      title: (payload && payload.deck_title) || "Cosmic Signal Deck",
      subtitle: (payload && payload.deck_subtitle) || "Listen to the data. See how we know.",
      message: (payload && payload.empty_exact_message) || "No curated signal is available for this target.",
    };
  }

  function buildMatchView(payload) {
    const entry = payload && payload.primary;
    if (!entry) return buildEmptyView(payload);
    return {
      mode: "match",
      title: payload.deck_title || "Cosmic Signal Deck",
      subtitle: payload.deck_subtitle || "Listen to the data. See how we know.",
      entry: entry,
      relevance: entry.relevance || payload.relevance,
      featured: (entry.relevance || payload.relevance) === "general_featured",
      emptyExactMessage: payload.empty_exact_message || "",
      redirectNotice: payload.redirect_limitation_notice || "",
    };
  }

  function clearMediaElement(el) {
    if (!el) return;
    try { el.pause(); } catch (_err) { /* media may not be initialized */ }
    el.removeAttribute("src");
    try { el.load(); } catch (_err) { /* ignored */ }
  }

  function shouldAssignMediaSrc(state) {
    return !!(
      state &&
      state.onlineMode &&
      state.currentEntry &&
      state.userRequestedPlayback &&
      state.mediaUrlAllowed &&
      state.requestGeneration === state.request.generation
    );
  }

  return {
    FEATURED_PREF_KEY,
    createRequestState,
    beginRequest,
    isStaleResponse,
    resetRequestState,
    getAllowFeatured,
    setAllowFeatured,
    buildMatchUrl,
    isAllowedUrl,
    mediaTypeLabel,
    relevanceLabel,
    buildLoadingView,
    buildEmptyView,
    buildMatchView,
    clearMediaElement,
    shouldAssignMediaSrc,
  };
});
