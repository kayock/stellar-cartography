"use strict";

/* Spectrum Gallery pure helpers. Image host allow-lists come from the local
 * registry API. Only the selected image src is assigned; no bulk preload. */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.SpectrumGallery = factory();
})(typeof self !== "undefined" ? self : this, function () {
  const MAX_URL_LEN = 2000;
  const UNSAFE_URL_CHARS = /[\x00-\x08\x0b\x0c\x0e-\x1f\s"'<>]/;

  function createRequestState() {
    return {
      generation: 0,
      viewGeneration: 0,
      inFlightKey: null,
      activeTargetKey: null,
      currentEntry: null,
    };
  }

  function beginRequest(state, targetKey) {
    state.generation += 1;
    state.viewGeneration += 1;
    state.inFlightKey = targetKey || null;
    state.activeTargetKey = targetKey || null;
    return state.generation;
  }

  function beginViewSelection(state) {
    state.viewGeneration += 1;
    return state.viewGeneration;
  }

  function isStaleResponse(state, generation) {
    return !state || generation !== state.generation;
  }

  function isStaleView(state, viewGeneration) {
    return !state || viewGeneration !== state.viewGeneration;
  }

  function resetRequestState(state) {
    state.generation += 1;
    state.viewGeneration += 1;
    state.inFlightKey = null;
    state.activeTargetKey = null;
    state.currentEntry = null;
    return state.generation;
  }

  function buildMatchUrl(name, altName, catalogueDesignations, allowAllSky) {
    const params = new URLSearchParams({
      name: name || "",
      alt_name: altName || "",
      catalogue_designations: catalogueDesignations || "",
      allow_all_sky: allowAllSky === false ? "0" : "1",
    });
    return "/api/spectrum-gallery-match?" + params.toString();
  }

  function isAllowedUrl(url, hostSet) {
    if (typeof url !== "string" || !url || url.length > MAX_URL_LEN || UNSAFE_URL_CHARS.test(url)) {
      return false;
    }
    try {
      const parsed = new URL(url);
      if (parsed.protocol !== "https:" || parsed.username || parsed.password) return false;
      const hosts = new Set(
        Array.from(hostSet || [])
          .filter((host) => typeof host === "string")
          .map((host) => host.toLowerCase())
      );
      return hosts.has(parsed.hostname.toLowerCase());
    } catch (_err) {
      return false;
    }
  }

  function relevanceLabel(relevance) {
    if (relevance === "exact_target") return "Exact target";
    if (relevance === "target_region") return "Target region";
    if (relevance === "all_sky_context") return "All-sky context";
    return "";
  }

  function exactViewsFromPayload(payload) {
    if (!payload) return [];
    if (Array.isArray(payload.available_views)) {
      return payload.available_views.filter((entry) => entry && entry.relevance === "exact_target");
    }
    const options = Array.isArray(payload.options) ? payload.options : [];
    return options.filter((entry) => entry && entry.relevance === "exact_target");
  }

  function viewButtonLabel(entry, siblings) {
    const wavelength = (entry && entry.wavelength) || "View";
    const peers = Array.isArray(siblings) ? siblings : [];
    const sameWave = peers.filter((peer) => peer && peer.wavelength === wavelength).length > 1;
    if (!sameWave) return wavelength;
    const observatory = String((entry && entry.observatory) || "")
      .split("/")[0]
      .trim();
    const shortObs = observatory.replace(/\s+X-ray Observatory$/i, "").replace(/\s+Space Telescope$/i, "");
    return shortObs ? shortObs + " " + wavelength : wavelength;
  }

  function buildEmptyView(payload) {
    return {
      title: (payload && payload.gallery_title) || "Spectrum Gallery",
      subtitle: (payload && payload.gallery_subtitle) || "See the universe in another light.",
      status:
        (payload && payload.empty_exact_message) ||
        "No curated spectrum image is available for this target.",
      primary: null,
      availableViews: [],
      options: (payload && payload.options) || [],
    };
  }

  function buildMatchView(payload) {
    if (!payload || !payload.primary) return buildEmptyView(payload || {});
    const availableViews = exactViewsFromPayload(payload);
    return {
      title: payload.gallery_title || "Spectrum Gallery",
      subtitle: payload.gallery_subtitle || "See the universe in another light.",
      status: payload.primary.title || "",
      primary: payload.primary,
      availableViews: availableViews,
      options: Array.isArray(payload.options) ? payload.options : [payload.primary],
    };
  }

  function findOption(options, entryId) {
    if (!Array.isArray(options)) return null;
    return options.find((entry) => entry && entry.id === entryId) || null;
  }

  return {
    createRequestState,
    beginRequest,
    beginViewSelection,
    isStaleResponse,
    isStaleView,
    resetRequestState,
    buildMatchUrl,
    isAllowedUrl,
    relevanceLabel,
    exactViewsFromPayload,
    viewButtonLabel,
    buildEmptyView,
    buildMatchView,
    findOption,
  };
});
