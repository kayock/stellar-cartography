/* changehips.js
 *
 * Pure, DOM-free logic for interpreting ESASky's response to a changeHips
 * postMessage command. Nothing here reports "Loaded" as soon as the
 * command is *sent* -- callers must wait for one of:
 *   - a confirmed success message naming the loaded layer
 *   - a documented failure (e.g. extras.message) naming the problem
 *   - a timeout, if ESASky never confirms either way
 *
 * DOM-free so it can be exercised directly by build-time Node tests
 * (tests/frontend/changehips.test.js).
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.ChangeHips = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  /** Does `message` look like it's about a HiPS/imagery change at all
   * (as opposed to an unrelated postMessage, e.g. a getAvailableHips
   * listing)? Heuristic: it carries a hipsName/name, or an explicit
   * status/success flag, or an extras.message failure -- and it is NOT
   * itself a HiPS *listing* (an object/array of many layer entries). */
  function looksLikeChangeHipsMessage(message) {
    if (!message || typeof message !== "object") return false;
    var payload = message.content !== undefined ? message.content : message.values !== undefined ? message.values : message;
    if (!payload || typeof payload !== "object" || Array.isArray(payload)) return false;
    if (payload.hipsName || payload.name) return true;
    if (typeof payload.success === "boolean") return true;
    if (payload.status !== undefined) return true;
    if (payload.extras && payload.extras.message) return true;
    if (payload.error) return true;
    return false;
  }

  /** Interpret a changeHips-shaped message against the pending request
   * ({ requestedName }). Returns:
   *   { status: "success", layerName }
   *   { status: "error", message }
   *   { status: "unrelated" }   -- caller should keep waiting
   */
  function interpretChangeHipsMessage(pending, message) {
    if (!looksLikeChangeHipsMessage(message)) {
      return { status: "unrelated" };
    }
    var payload = message.content !== undefined ? message.content : message.values !== undefined ? message.values : message;

    var failureText = null;
    if (payload.extras && typeof payload.extras.message === "string" && payload.extras.message.trim()) {
      failureText = payload.extras.message.trim();
    } else if (typeof payload.error === "string" && payload.error.trim()) {
      failureText = payload.error.trim();
    } else if (payload.success === false) {
      failureText = "ESASky reported the change was not successful.";
    } else if (typeof payload.status === "string" && /error|fail/i.test(payload.status)) {
      failureText = "ESASky reported the change failed (status: " + payload.status + ").";
    }

    if (failureText) {
      return { status: "error", message: failureText };
    }

    var confirmedName = payload.hipsName || payload.name || (pending && pending.requestedName) || null;
    if (confirmedName) {
      return { status: "success", layerName: confirmedName };
    }

    // Carries no name and no clear failure indicator -- not enough to
    // confidently confirm success; treat as unrelated so the caller keeps
    // waiting (or eventually times out) rather than guessing.
    return { status: "unrelated" };
  }

  return {
    looksLikeChangeHipsMessage: looksLikeChangeHipsMessage,
    interpretChangeHipsMessage: interpretChangeHipsMessage,
  };
});
