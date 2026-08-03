/* archive_availability.js
 *
 * Pure helpers for Hubble/JWST archive-availability lights (MAST CAOM).
 * Gated by Online Archive Mode; zero network when offline.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.ArchiveAvailability = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var ARCHIVE_MISSIONS = ["hst", "jwst_nircam", "jwst_miri"];

  var STATE = {
    NOT_CHECKED: "not_checked",
    CHECKING: "checking",
    CONFIRMED: "confirmed",
    NO_COVERAGE: "no_coverage",
    UNAVAILABLE: "unavailable",
    SELECTED_LAYER: "selected_layer",
  };

  var MIN_REPEAT_INTERVAL_MS = 30000;
  var CACHE_TTL_MS = 300000;

  function normalizeCoordKey(raDeg, decDeg) {
    var ra = Number(raDeg);
    var dec = Number(decDeg);
    if (!isFinite(ra) || !isFinite(dec)) return null;
    return (ra % 360).toFixed(5) + ":" + dec.toFixed(5);
  }

  function cacheKey(raDeg, decDeg, mission) {
    var coord = normalizeCoordKey(raDeg, decDeg);
    if (!coord) return null;
    return coord + "|" + mission;
  }

  function createState() {
    return {
      generation: 0,
      coordKey: null,
      inFlight: {},
      cache: {},
      lastRequestAt: {},
      activeImageryButtonId: null,
    };
  }

  function bumpGeneration(state) {
    state.generation += 1;
    state.inFlight = {};
  }

  function isStale(state, generation) {
    return generation !== state.generation;
  }

  function shouldSkipInFlight(state, key) {
    return !!state.inFlight[key];
  }

  function shouldUseCache(state, key, nowMs) {
    var entry = state.cache[key];
    if (!entry) return false;
    return nowMs - entry.cachedAt < CACHE_TTL_MS;
  }

  function shouldRateLimit(state, key, nowMs) {
    var last = state.lastRequestAt[key];
    if (!last) return false;
    return nowMs - last < MIN_REPEAT_INTERVAL_MS;
  }

  function markInFlight(state, key) {
    state.inFlight[key] = true;
  }

  function clearInFlight(state, key) {
    delete state.inFlight[key];
  }

  function storeCache(state, key, payload, nowMs) {
    state.cache[key] = { payload: payload, cachedAt: nowMs };
  }

  function buildApiUrl(raDeg, decDeg, mission, includeObservations) {
    var url =
      "/api/archive-availability?ra=" +
      encodeURIComponent(String(raDeg)) +
      "&dec=" +
      encodeURIComponent(String(decDeg)) +
      "&mission=" +
      encodeURIComponent(mission);
    if (includeObservations) url += "&include_observations=1";
    return url;
  }

  function missionLabel(mission) {
    var labels = {
      hst: "Hubble",
      jwst_nircam: "JWST NIRCam",
      jwst_miri: "JWST MIRI",
    };
    return labels[mission] || mission;
  }

  function accessibleText(stateName, mission, count) {
    var label = missionLabel(mission);
    if (stateName === STATE.NOT_CHECKED) return label + ": not checked";
    if (stateName === STATE.CHECKING) return label + ": checking archive";
    if (stateName === STATE.CONFIRMED) {
      return label + ": " + String(count) + " archive observations";
    }
    if (stateName === STATE.NO_COVERAGE) {
      return label + ": no confirmed observations near this position";
    }
    if (stateName === STATE.UNAVAILABLE) return label + ": archive check unavailable";
    if (stateName === STATE.SELECTED_LAYER) return label + ": currently selected ESASky layer";
    return label + ": unknown state";
  }

  function mapApiToLight(apiBody, mission, activeButtonId) {
    if (activeButtonId === mission) {
      return {
        state: STATE.SELECTED_LAYER,
        count: apiBody && apiBody.count,
        accessibleText: accessibleText(STATE.SELECTED_LAYER, mission),
        observations: (apiBody && apiBody.observations) || [],
      };
    }
    if (!apiBody) {
      return {
        state: STATE.UNAVAILABLE,
        accessibleText: accessibleText(STATE.UNAVAILABLE, mission),
        observations: [],
      };
    }
    if (apiBody.status === "confirmed" && apiBody.count > 0) {
      return {
        state: STATE.CONFIRMED,
        count: apiBody.count,
        accessibleText: accessibleText(STATE.CONFIRMED, mission, apiBody.count),
        observations: apiBody.observations || [],
      };
    }
    if (apiBody.status === "no_coverage") {
      return {
        state: STATE.NO_COVERAGE,
        accessibleText: accessibleText(STATE.NO_COVERAGE, mission),
        observations: [],
      };
    }
    return {
      state: STATE.UNAVAILABLE,
      accessibleText: accessibleText(STATE.UNAVAILABLE, mission),
      observations: [],
    };
  }

  function resetForOffline(state) {
    bumpGeneration(state);
    state.coordKey = null;
    state.activeImageryButtonId = null;
  }

  function resetForTargetChange(state, raDeg, decDeg) {
    bumpGeneration(state);
    state.coordKey = normalizeCoordKey(raDeg, decDeg);
    state.inFlight = {};
  }

  return {
    ARCHIVE_MISSIONS: ARCHIVE_MISSIONS,
    STATE: STATE,
    MIN_REPEAT_INTERVAL_MS: MIN_REPEAT_INTERVAL_MS,
    CACHE_TTL_MS: CACHE_TTL_MS,
    normalizeCoordKey: normalizeCoordKey,
    cacheKey: cacheKey,
    createState: createState,
    bumpGeneration: bumpGeneration,
    isStale: isStale,
    shouldSkipInFlight: shouldSkipInFlight,
    shouldUseCache: shouldUseCache,
    shouldRateLimit: shouldRateLimit,
    markInFlight: markInFlight,
    clearInFlight: clearInFlight,
    storeCache: storeCache,
    buildApiUrl: buildApiUrl,
    missionLabel: missionLabel,
    accessibleText: accessibleText,
    mapApiToLight: mapApiToLight,
    resetForOffline: resetForOffline,
    resetForTargetChange: resetForTargetChange,
  };
});
