/* changehips.js
 *
 * Pure, DOM-free logic for interpreting ESASky's response to a changeHips
 * postMessage command. Nothing here reports acknowledgement as soon as the
 * command is *sent* -- callers must wait for one of:
 *   - a confirmed acknowledgement naming the loaded layer (from ESASky)
 *   - a documented failure (e.g. extras.message) naming the problem
 *   - a timeout, if ESASky never confirms either way
 *
 * A generic success-shaped message without an ESASky-supplied layer name
 * is NOT confirmation. The app must never substitute pending.requestedName.
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

  /** Normalize a HiPS layer name for comparison: trim, collapse whitespace,
   * case-fold. Does not invent correlation beyond string equality of the
   * normalized forms. */
  function normalizeLayerName(name) {
    if (typeof name !== "string") return "";
    return name.trim().replace(/\s+/g, " ").toLowerCase();
  }

  /** True when the ESASky-supplied acknowledged name corresponds to the
   * requested layer under normalized comparison. */
  function layersCorrespond(requestedName, acknowledgedName) {
    var a = normalizeLayerName(requestedName);
    var b = normalizeLayerName(acknowledgedName);
    if (!a || !b) return false;
    return a === b;
  }

  /** Extract a layer name that ESASky itself supplied in the message.
   * Never falls back to the pending requested name. */
  function extractEsaskyLayerName(payload) {
    if (!payload || typeof payload !== "object" || Array.isArray(payload)) return null;
    var name = payload.hipsName || payload.name;
    if (typeof name === "string" && name.trim()) return name.trim();
    return null;
  }

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
   * ({ requestedName, generation? }). Returns:
   *   { status: "acknowledged", layerName }
   *   { status: "error", message }
   *   { status: "mismatch", layerName, message }  -- ESASky named a different layer
   *   { status: "unrelated" }   -- caller should keep waiting
   *
   * Confirmation REQUIRES an ESASky-supplied layer name that corresponds
   * to pending.requestedName. Generic success without a layer name stays
   * unconfirmed (unrelated) so the bounded timeout can handle it.
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

    var esaskyName = extractEsaskyLayerName(payload);
    if (!esaskyName) {
      // No layer name from ESASky -- do not invent confirmation via
      // pending.requestedName. Keep waiting or eventually time out.
      return { status: "unrelated" };
    }

    var requested = pending && pending.requestedName;
    if (!layersCorrespond(requested, esaskyName)) {
      return {
        status: "mismatch",
        layerName: esaskyName,
        message:
          'ESASky named survey layer "' +
          esaskyName +
          '" which does not correspond to the requested layer' +
          (requested ? ' "' + requested + '"' : "") +
          ".",
      };
    }

    return { status: "acknowledged", layerName: esaskyName };
  }

  return {
    normalizeLayerName: normalizeLayerName,
    layersCorrespond: layersCorrespond,
    extractEsaskyLayerName: extractEsaskyLayerName,
    looksLikeChangeHipsMessage: looksLikeChangeHipsMessage,
    interpretChangeHipsMessage: interpretChangeHipsMessage,
  };
});
