/* target_model.js
 *
 * Pure, DOM-free mapping from this app's own server JSON responses
 * (/api/selection, /api/manual/validate) into the frontend's in-memory
 * "current target" model. Kept separate from app.js so the mapping itself
 * -- in particular, that official numeric Stellarium coordinates reach
 * the frontend unchanged -- can be exercised directly by build-time Node
 * tests (tests/frontend/target_model.test.js).
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.TargetModel = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  /** Build the frontend target model from a /api/selection response body
   * (data.ok must be true). */
  function buildTargetFromSelection(data) {
    return {
      name: data.name,
      alt_name: data.alt_name,
      object_category: data.object_category,
      object_type: data.object_type,
      object_subtype: data.object_subtype,
      catalogue_designations: data.catalogue_designations,
      constellation: data.constellation,
      apparent_magnitude: data.apparent_magnitude,
      angular_size_deg: data.angular_size_deg,
      altitude_deg: data.altitude_deg,
      azimuth_deg: data.azimuth_deg,
      above_horizon: data.above_horizon,
      ra_deg: data.ra_deg,
      dec_deg: data.dec_deg,
      ra_sexagesimal: data.ra_sexagesimal,
      dec_sexagesimal: data.dec_sexagesimal,
      fov_deg: data.fov_deg,
      source: "Stellarium selection",
    };
  }

  /** Build the frontend target model from a /api/manual/validate response
   * body (data.ok must be true) plus the user-entered name. */
  function buildTargetFromManual(data, name) {
    return {
      name: name || "Manual target",
      alt_name: null,
      object_category: null,
      object_type: null,
      ra_deg: data.ra_deg,
      dec_deg: data.dec_deg,
      ra_sexagesimal: data.ra_sexagesimal,
      dec_sexagesimal: data.dec_sexagesimal,
      fov_deg: null,
      source: "Manual entry",
    };
  }

  /** Given the current app state (pendingHipsRequest, pendingChangeRequest),
   * return what must change after Stellarium reports a failed/empty
   * selection (/api/selection ok:false), so that no stale target is left
   * actionable. Pure/DOM-free -- mirrors online_mode.js's
   * buildShutdownState pattern: app.js applies the DOM side effects
   * (clearing the target/about-object cards, disabling "Open in ESASky",
   * clearing active imagery-button styling) and clears the returned
   * timeout IDs itself, since this module has no reference to timer APIs
   * by design.
   *
   * Deliberately does NOT touch onlineMode, the ESASky queue, or the
   * iframe: a failed selection must not silently close an already-open
   * ESASky viewer, it must only stop treating the *prior* target as
   * valid. */
  function buildFailedSelectionState(state) {
    var timeoutIdsToClear = [];
    if (state.pendingHipsRequest && state.pendingHipsRequest.timeoutId) {
      timeoutIdsToClear.push(state.pendingHipsRequest.timeoutId);
    }
    if (state.pendingChangeRequest && state.pendingChangeRequest.timeoutId) {
      timeoutIdsToClear.push(state.pendingChangeRequest.timeoutId);
    }
    return {
      timeoutIdsToClear: timeoutIdsToClear,
      currentTarget: null,
      pendingHipsRequest: null,
      pendingChangeRequest: null,
      activeImageryButtonId: null,
      aboutObjectCardHidden: true,
      openEsaskyDisabled: true,
    };
  }

  return {
    buildTargetFromSelection: buildTargetFromSelection,
    buildTargetFromManual: buildTargetFromManual,
    buildFailedSelectionState: buildFailedSelectionState,
  };
});
