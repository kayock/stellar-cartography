/* apophis_tracker.js
 *
 * Pure helpers for the featured Apophis (99942) tracker panel.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.ApophisTracker = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var MIN_REFRESH_INTERVAL_MS = 60000;
  var APOPHIS_ENCOUNTER_ISO = "2029-04-13T00:00:00Z";

  function createRequestState() {
    return {
      generation: 0,
      inFlight: false,
      lastFetchedAt: 0,
      lastPayload: null,
    };
  }

  function shouldRateLimit(state, nowMs) {
    if (!state.lastFetchedAt) return false;
    return nowMs - state.lastFetchedAt < MIN_REFRESH_INTERVAL_MS;
  }

  function beginRequest(state) {
    state.generation += 1;
    state.inFlight = true;
    return state.generation;
  }

  function isStale(state, generation) {
    return generation !== state.generation;
  }

  function markComplete(state, payload, nowMs) {
    state.inFlight = false;
    state.lastFetchedAt = nowMs;
    state.lastPayload = payload;
  }

  function shouldSkipInFlight(state) {
    return state.inFlight;
  }

  function buildApiUrl(observer) {
    var url = "/api/apophis-tracker";
    if (!observer) return url;
    var params = [];
    if (observer.latitude_deg != null) params.push("observer_lat=" + encodeURIComponent(String(observer.latitude_deg)));
    if (observer.longitude_deg != null) params.push("observer_lon=" + encodeURIComponent(String(observer.longitude_deg)));
    if (observer.altitude_m != null) params.push("observer_alt=" + encodeURIComponent(String(observer.altitude_m)));
    if (params.length) url += "?" + params.join("&");
    return url;
  }

  function computeCountdownDays(nowDate, encounterIso) {
    var encounter = new Date(encounterIso || APOPHIS_ENCOUNTER_ISO);
    var now = nowDate || new Date();
    var ms = encounter.setHours(0, 0, 0, 0) - now.setHours(0, 0, 0, 0);
    return Math.round(ms / 86400000);
  }

  function buildViewModel(apiBody, options) {
    options = options || {};
    var body = apiBody && typeof apiBody === "object" ? apiBody : {};
    return {
      ok: !!body.ok,
      fromCache: !!options.fromCache,
      cacheRetrievedAt: options.cacheRetrievedAt || body.retrieved_at || null,
      designation: body.designation || "99942",
      name: body.name || "99942 Apophis",
      countdownDays: body.countdown_days != null ? body.countdown_days : computeCountdownDays(),
      encounterDate: body.encounter_date_unavailable
        ? null
        : body.encounter_date || body.encounter_date_documented || APOPHIS_ENCOUNTER_ISO,
      encounterDateUnavailable: !!body.encounter_date_unavailable,
      nominalDistanceAu: body.nominal_close_approach_distance_au,
      retrievedAt: body.retrieved_at,
      sourceAgency: body.source_agency || "NASA/JPL CNEOS",
      riskStatus: body.risk_status,
      riskStatusAvailable: !!body.risk_status_available,
      riskNotice: body.risk_status_notice ||
        "Current official risk status was not retrieved automatically. Check the official source.",
      ephemeris: body.ephemeris || null,
      ephemerisEpoch: body.ephemeris_epoch,
      observerContext: body.observer_context,
      observerPrivacyNotice: body.observer_privacy_notice,
      countdownNotice: body.countdown_notice,
      sourceLinks: body.source_links || {},
      error: body.error,
    };
  }

  function isApophisEntry(entry) {
    return entry && entry.featured_kind === "apophis";
  }

  function secondsUntilRefreshAllowed(state, nowMs) {
    if (!state.lastFetchedAt) return 0;
    var remaining = MIN_REFRESH_INTERVAL_MS - (nowMs - state.lastFetchedAt);
    return remaining > 0 ? Math.ceil(remaining / 1000) : 0;
  }

  function buildRateLimitMessage(state, nowMs) {
    var seconds = secondsUntilRefreshAllowed(state, nowMs);
    if (seconds <= 0) return null;
    return "Apophis refresh rate-limited. Try again in about " + seconds + " second" + (seconds === 1 ? "" : "s") + ".";
  }

  return {
    MIN_REFRESH_INTERVAL_MS: MIN_REFRESH_INTERVAL_MS,
    APOPHIS_ENCOUNTER_ISO: APOPHIS_ENCOUNTER_ISO,
    createRequestState: createRequestState,
    shouldRateLimit: shouldRateLimit,
    beginRequest: beginRequest,
    isStale: isStale,
    markComplete: markComplete,
    shouldSkipInFlight: shouldSkipInFlight,
    buildApiUrl: buildApiUrl,
    computeCountdownDays: computeCountdownDays,
    buildViewModel: buildViewModel,
    isApophisEntry: isApophisEntry,
    secondsUntilRefreshAllowed: secondsUntilRefreshAllowed,
    buildRateLimitMessage: buildRateLimitMessage,
  };
});
