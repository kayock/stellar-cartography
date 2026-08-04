/* planetary_image.js
 *
 * Pure, DOM-free helpers for Solar System NASA public-media:
 *   - resolve media target ids from the Solar System media registry
 *   - request deduplication and stale-response guards
 *   - safe metadata handling and HTTPS image URL validation
 *   - panel view-model construction for app.js
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory(
      typeof SolarSystemMediaRegistry !== "undefined"
        ? SolarSystemMediaRegistry
        : require("./solar_system_media_registry.js")
    );
  } else {
    root.PlanetaryImage = factory(root.SolarSystemMediaRegistry);
  }
})(typeof self !== "undefined" ? self : this, function (Registry) {
  "use strict";

  if (!Registry) {
    throw new Error("SolarSystemMediaRegistry is required for PlanetaryImage.");
  }

  var ALLOWED_IMAGE_HOSTS = {
    "images-assets.nasa.gov": true,
  };

  var ALLOWED_SOURCE_LINK_HOSTS = {
    "images.nasa.gov": true,
  };

  var ARCHIVE_NOTICE =
    "NASA public archive media — outreach imagery from NASA's Image and Video " +
    "Library, not a calibrated science product and not proof of current " +
    "appearance, phase, orientation, or position at the Stellarium coordinates. " +
    "It was not produced by Stellarium or ESASky.";

  var MEDIA_LABEL = Registry.mediaLabel();
  var RESULT_TYPE = Registry.resultType();
  var EMPTY_MEDIA_MESSAGE = Registry.emptyResultMessage();

  function normalizeName(value) {
    if (typeof value !== "string") return "";
    return value.trim().toLowerCase();
  }

  /** Resolve a registry media id from Stellarium-reported names. */
  function resolvePilotTargetId(target) {
    if (!target || typeof target !== "object") return null;
    var names = [target.name, target.alt_name].map(normalizeName).filter(Boolean);
    for (var i = 0; i < names.length; i++) {
      var resolved = Registry.normalizeMediaTargetId(names[i]);
      if (resolved) return resolved;
    }
    return null;
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
   * completed-target dedup so a return to a media target fetches again. */
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
      headline: "NASA Public Media",
      message:
        "This Solar System target is not in the NASA public-media registry. " +
        "(" +
        label +
        ")",
      archiveNotice: ARCHIVE_NOTICE,
      mediaLabel: MEDIA_LABEL,
    };
  }

  function buildLoadingView(pilotId) {
    var name = Registry.displayNameForId(pilotId) || pilotId;
    return {
      mode: "loading",
      headline: "NASA Public Media",
      message: "Searching NASA's official image archive for " + name + "…",
      archiveNotice: ARCHIVE_NOTICE,
      mediaLabel: MEDIA_LABEL,
      searchedTarget: name,
    };
  }

  function buildResultView(apiBody) {
    var body = apiBody && typeof apiBody === "object" ? apiBody : {};
    var status = body.status || "error";
    var imageUrl = isAllowedImageUrl(body.image_url) ? body.image_url : null;

    if (status === "found" && imageUrl) {
      return {
        mode: "found",
        headline: "NASA Public Media",
        imageUrl: imageUrl,
        targetName: sanitizeText(body.target_name),
        searchedTarget: sanitizeText(body.searched_target) || sanitizeText(body.target_name),
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
        mediaLabel: sanitizeText(body.media_label, 80) || MEDIA_LABEL,
        resultType: body.result_type === RESULT_TYPE ? RESULT_TYPE : RESULT_TYPE,
      };
    }

    var fallbackMessage =
      sanitizeText(body.error) || EMPTY_MEDIA_MESSAGE;

    return {
      mode: status === "timeout" || status === "http_error" ? "error" : "unavailable",
      headline: "NASA Public Media",
      message: fallbackMessage,
      archiveNotice: sanitizeText(body.archive_notice) || ARCHIVE_NOTICE,
      mediaLabel: sanitizeText(body.media_label, 80) || MEDIA_LABEL,
      searchedTarget: sanitizeText(body.searched_target) || sanitizeText(body.target_name),
      resultType: null,
    };
  }

  return {
    ALLOWED_IMAGE_HOSTS: ALLOWED_IMAGE_HOSTS,
    ALLOWED_SOURCE_LINK_HOSTS: ALLOWED_SOURCE_LINK_HOSTS,
    ARCHIVE_NOTICE: ARCHIVE_NOTICE,
    MEDIA_LABEL: MEDIA_LABEL,
    RESULT_TYPE: RESULT_TYPE,
    EMPTY_MEDIA_MESSAGE: EMPTY_MEDIA_MESSAGE,
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
