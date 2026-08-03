/* planetary_image.js
 *
 * Pure, DOM-free helpers for the R0.3 Planetary Image Pilot:
 *   - resolve pilot target ids (Moon, Jupiter, Saturn only)
 *   - request deduplication and stale-response guards
 *   - safe metadata handling and HTTPS image URL validation
 *   - panel view-model construction for app.js
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.PlanetaryImage = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var PILOT_TARGET_ALIASES = {
    moon: ["moon", "luna"],
    jupiter: ["jupiter"],
    saturn: ["saturn"],
  };

  var ALLOWED_IMAGE_HOSTS = {
    "images-assets.nasa.gov": true,
  };

  var ALLOWED_SOURCE_LINK_HOSTS = {
    "images.nasa.gov": true,
  };

  var ARCHIVE_NOTICE =
    "This is an archived NASA outreach image, not a live view. " +
    "It does not show the current date, phase, orientation, or appearance " +
    "at the Stellarium coordinates. It was not produced by Stellarium or ESASky.";

  function normalizeName(value) {
    if (typeof value !== "string") return "";
    return value.trim().toLowerCase();
  }

  /** Resolve a pilot id from Stellarium-reported names on a Solar System target. */
  function resolvePilotTargetId(target) {
    if (!target || typeof target !== "object") return null;
    var names = [target.name, target.alt_name].map(normalizeName).filter(Boolean);
    var pilotId;
    Object.keys(PILOT_TARGET_ALIASES).forEach(function (id) {
      if (pilotId) return;
      var aliases = PILOT_TARGET_ALIASES[id];
      for (var i = 0; i < names.length; i++) {
        if (aliases.indexOf(names[i]) !== -1) {
          pilotId = id;
          return;
        }
      }
    });
    return pilotId || null;
  }

  function hasUnsafeUrlCharacters(url) {
    return /[\s"'<>]/.test(url);
  }

  function isAllowedImageUrl(url) {
    if (typeof url !== "string" || !url) return false;
    if (hasUnsafeUrlCharacters(url)) return false;
    try {
      var parsed = new URL(url);
      if (parsed.protocol !== "https:") return false;
      if (parsed.username || parsed.password) return false;
      return !!ALLOWED_IMAGE_HOSTS[parsed.hostname.toLowerCase()];
    } catch (_err) {
      return false;
    }
  }

  function isAllowedSourceLink(url) {
    if (typeof url !== "string" || !url) return false;
    if (hasUnsafeUrlCharacters(url)) return false;
    try {
      var parsed = new URL(url);
      if (parsed.protocol !== "https:") return false;
      if (parsed.username || parsed.password) return false;
      if (!ALLOWED_SOURCE_LINK_HOSTS[parsed.hostname.toLowerCase()]) return false;
      return parsed.pathname.indexOf("/details/") === 0;
    } catch (_err) {
      return false;
    }
  }

  function sanitizeText(value, maxLen) {
    maxLen = maxLen || 500;
    if (value === null || value === undefined) return null;
    var text = String(value).replace(/[\x00-\x08\x0b\x0c\x0e-\x1f]/g, "").trim();
    if (!text) return null;
    if (text.length > maxLen) text = text.slice(0, maxLen - 1) + "…";
    return text;
  }

  function createRequestState() {
    return {
      generation: 0,
      lastFetchedPilotId: null,
      inFlightPilotId: null,
    };
  }

  function beginRequest(state, pilotId) {
    state.generation += 1;
    state.inFlightPilotId = pilotId;
    return state.generation;
  }

  function shouldSkipDuplicateFetch(state, pilotId) {
    return state.lastFetchedPilotId === pilotId && state.inFlightPilotId !== pilotId;
  }

  function shouldSkipInFlightDuplicate(state, pilotId) {
    return state.inFlightPilotId === pilotId;
  }

  function isStaleResponse(state, generation) {
    return generation !== state.generation;
  }

  function markFetchComplete(state, pilotId) {
    state.lastFetchedPilotId = pilotId;
    state.inFlightPilotId = null;
  }

  /** Invalidate in-flight responses without clearing a completed session cache. */
  function invalidateInFlightRequests(state) {
    state.generation += 1;
    state.inFlightPilotId = null;
  }

  /** Entering an unsupported Solar System target: drop stale in-flight work and
   * completed-target dedup so a return to a pilot target fetches again. */
  function prepareUnsupportedTargetSwitch(state) {
    state.generation += 1;
    state.inFlightPilotId = null;
    state.lastFetchedPilotId = null;
  }

  function resetRequestState(state) {
    state.generation += 1;
    state.lastFetchedPilotId = null;
    state.inFlightPilotId = null;
  }

  function buildApiUrl(pilotId) {
    return "/api/planetary-image?target=" + encodeURIComponent(pilotId);
  }

  /** Decide whether the planetary panel should be visible (before fetch completes). */
  function shouldShowPlanetaryPanel(target, onlineMode) {
    if (!onlineMode || !target) return false;
    if (typeof SolarSystem !== "undefined" && !SolarSystem.isSolarSystemTarget(target)) {
      return false;
    }
    return true;
  }

  function buildUnsupportedView(target) {
    var label = sanitizeText(target && target.name, 80) || "this Solar System object";
    return {
      mode: "unsupported",
      headline: "Planetary archive image not available for this target",
      message:
        "The R0.3 pilot supports Moon, Jupiter, and Saturn only. " +
        label +
        " is outside the supported pilot set.",
      archiveNotice: ARCHIVE_NOTICE,
    };
  }

  function buildLoadingView(pilotId) {
    var names = { moon: "Moon", jupiter: "Jupiter", saturn: "Saturn" };
    return {
      mode: "loading",
      headline: "Planetary Archive Image",
      message: "Searching NASA's official image archive for " + (names[pilotId] || pilotId) + "…",
      archiveNotice: ARCHIVE_NOTICE,
    };
  }

  function buildResultView(apiBody) {
    var body = apiBody && typeof apiBody === "object" ? apiBody : {};
    var status = body.status || "error";
    var imageUrl = isAllowedImageUrl(body.image_url) ? body.image_url : null;

    if (status === "found" && imageUrl) {
      return {
        mode: "found",
        headline: "Planetary Archive Image",
        imageUrl: imageUrl,
        targetName: sanitizeText(body.target_name),
        title: sanitizeText(body.title),
        description: sanitizeText(body.description),
        mission: sanitizeText(body.mission),
        nasaCenter: sanitizeText(body.nasa_center),
        keywords: sanitizeText(body.keywords),
        instrument: sanitizeText(body.instrument),
        imageDate: sanitizeText(body.image_date, 40),
        sourceAgency: sanitizeText(body.source_agency, 40) || "NASA",
        credit: sanitizeText(body.credit),
        sourceLink: isAllowedSourceLink(body.source_link) ? body.source_link : null,
        archiveNotice: sanitizeText(body.archive_notice) || ARCHIVE_NOTICE,
      };
    }

    var fallbackMessage = sanitizeText(body.error) ||
      "No suitable official NASA archive image is available for this pilot target right now.";

    return {
      mode: status === "timeout" || status === "http_error" ? "error" : "unavailable",
      headline: "Planetary Archive Image",
      message: fallbackMessage,
      archiveNotice: sanitizeText(body.archive_notice) || ARCHIVE_NOTICE,
    };
  }

  return {
    PILOT_TARGET_ALIASES: PILOT_TARGET_ALIASES,
    ALLOWED_IMAGE_HOSTS: ALLOWED_IMAGE_HOSTS,
    ALLOWED_SOURCE_LINK_HOSTS: ALLOWED_SOURCE_LINK_HOSTS,
    ARCHIVE_NOTICE: ARCHIVE_NOTICE,
    resolvePilotTargetId: resolvePilotTargetId,
    isAllowedImageUrl: isAllowedImageUrl,
    isAllowedSourceLink: isAllowedSourceLink,
    sanitizeText: sanitizeText,
    createRequestState: createRequestState,
    beginRequest: beginRequest,
    shouldSkipDuplicateFetch: shouldSkipDuplicateFetch,
    shouldSkipInFlightDuplicate: shouldSkipInFlightDuplicate,
    isStaleResponse: isStaleResponse,
    markFetchComplete: markFetchComplete,
    invalidateInFlightRequests: invalidateInFlightRequests,
    prepareUnsupportedTargetSwitch: prepareUnsupportedTargetSwitch,
    resetRequestState: resetRequestState,
    buildApiUrl: buildApiUrl,
    shouldShowPlanetaryPanel: shouldShowPlanetaryPanel,
    buildUnsupportedView: buildUnsupportedView,
    buildLoadingView: buildLoadingView,
    buildResultView: buildResultView,
  };
});
