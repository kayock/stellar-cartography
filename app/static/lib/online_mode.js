/* online_mode.js
 *
 * Pure, DOM-free description of what must be reset when Online Archive
 * Mode is turned off, so "online mode off actually turns everything off"
 * is a testable contract rather than something only visible by clicking
 * around in a real browser.
 *
 * app.js calls buildShutdownState() and applies the DOM side effects
 * (clearing timers, blanking the iframe src, hiding it, clearing button
 * styling, etc.) based on the flags it returns.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.OnlineMode = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  /** Given the current app state (onlineMode, esaskyQueueState,
   * pendingHipsRequest, pendingChangeRequest, activeImageryButtonId),
   * return the new state fields after a full shutdown, plus a list of
   * timeout IDs the caller must clearTimeout() itself (this module
   * doesn't touch timers directly since it has no reference to the
   * timer APIs by design). */
  function buildShutdownState(state) {
    var timeoutIdsToClear = [];
    if (state.pendingHipsRequest && state.pendingHipsRequest.timeoutId) {
      timeoutIdsToClear.push(state.pendingHipsRequest.timeoutId);
    }
    if (state.pendingChangeRequest && state.pendingChangeRequest.timeoutId) {
      timeoutIdsToClear.push(state.pendingChangeRequest.timeoutId);
    }
    return {
      timeoutIdsToClear: timeoutIdsToClear,
      onlineMode: false,
      pendingHipsRequest: null,
      pendingChangeRequest: null,
      activeImageryButtonId: null,
      iframeSrc: "about:blank",
      iframeHidden: true,
      // Signals the esasky_queue state should be fully reset, including
      // the load-listener-attached flag, since the iframe src is being
      // blanked and any future "Open in ESASky" click must treat this as
      // a genuinely fresh load.
      esaskyQueueResetListenerFlag: true,
      viewerStatusText: "Online Archive Mode is off.",
      imageryStatusText: "",
    };
  }

  return {
    buildShutdownState: buildShutdownState,
  };
});
