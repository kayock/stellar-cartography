/* hips_layer_control.js
 *
 * Pure, DOM-free state machine for ESASky HiPS survey-layer switching.
 * Tracks requested vs acknowledged button ids, previous acknowledged layer,
 * and UI states that never claim tile coverage or "working" imagery.
 *
 * UI states: available | switching | acknowledged_unverified | failed |
 *            timed_out | restored
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.HipsLayerControl = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var DEFAULT_OPTICAL_LAYER = "DSS2 color";
  var DEFAULT_OPTICAL_BUTTON_ID = "optical";

  var UI = {
    AVAILABLE: "available",
    SWITCHING: "switching",
    ACKNOWLEDGED_UNVERIFIED: "acknowledged_unverified",
    FAILED: "failed",
    TIMED_OUT: "timed_out",
    RESTORED: "restored",
  };

  var KIND = {
    SWITCH: "switch",
    RESTORE_PREVIOUS: "restore_previous",
    RESTORE_DEFAULT: "restore_default",
  };

  function normalizeCompare(a, b) {
    function norm(s) {
      if (typeof s !== "string") return "";
      return s.trim().replace(/\s+/g, " ").toLowerCase();
    }
    var na = norm(a);
    var nb = norm(b);
    return !!na && !!nb && na === nb;
  }

  function createState() {
    return {
      generation: 0,
      uiState: UI.AVAILABLE,
      requestKind: null,
      requestedImageryButtonId: null,
      acknowledgedImageryButtonId: null,
      requestedSurveyName: null,
      acknowledgementSurveyName: null,
      failureReason: null,
      previousAcknowledgedLayer: null,
      currentAcknowledgedLayer: null,
      layerCommandSent: false,
    };
  }

  /** Invalidate in-flight HiPS listing/change work. Keeps acknowledged layer
   * memory. Callers must clearTimeout and null pendingHips/Change requests. */
  function invalidatePending(state) {
    state.generation += 1;
    state.uiState = state.currentAcknowledgedLayer ? UI.ACKNOWLEDGED_UNVERIFIED : UI.AVAILABLE;
    state.requestKind = null;
    state.requestedImageryButtonId = null;
    state.requestedSurveyName = null;
    state.acknowledgementSurveyName = state.currentAcknowledgedLayer
      ? state.currentAcknowledgedLayer.hipsName
      : null;
    state.failureReason = null;
    state.layerCommandSent = false;
    return state.generation;
  }

  function isStale(state, generation) {
    return generation !== state.generation;
  }

  /**
   * Begin a layer switch/restore request. Does NOT mark the button as
   * acknowledged. Returns { generation, pending }.
   */
  function beginSwitch(state, buttonId, layerName, kind) {
    // Stash the currently acknowledged layer as "previous" as soon as we leave it,
    // so Restore is available during switching/failure/timeout — not only after a
    // later acknowledgement.
    if (
      state.currentAcknowledgedLayer &&
      state.currentAcknowledgedLayer.hipsName &&
      !normalizeCompare(state.currentAcknowledgedLayer.hipsName, layerName)
    ) {
      state.previousAcknowledgedLayer = {
        hipsName: state.currentAcknowledgedLayer.hipsName,
        buttonId: state.currentAcknowledgedLayer.buttonId,
      };
    }

    state.generation += 1;
    state.uiState = UI.SWITCHING;
    state.requestKind = kind || KIND.SWITCH;
    state.requestedImageryButtonId = buttonId;
    state.requestedSurveyName = layerName;
    state.acknowledgementSurveyName = null;
    state.failureReason = null;
    state.layerCommandSent = true;
    return {
      generation: state.generation,
      pending: {
        buttonId: buttonId,
        requestedName: layerName,
        generation: state.generation,
        kind: state.requestKind,
      },
    };
  }

  function getRestoreAction(state) {
    var show =
      state.uiState === UI.SWITCHING ||
      state.uiState === UI.FAILED ||
      state.uiState === UI.TIMED_OUT ||
      state.uiState === UI.ACKNOWLEDGED_UNVERIFIED ||
      state.uiState === UI.RESTORED;
    if (!show && !state.layerCommandSent) return null;

    if (state.previousAcknowledgedLayer && state.previousAcknowledgedLayer.hipsName) {
      return {
        kind: KIND.RESTORE_PREVIOUS,
        buttonId: state.previousAcknowledgedLayer.buttonId,
        hipsName: state.previousAcknowledgedLayer.hipsName,
        label: 'Restore Previous Layer: "' + state.previousAcknowledgedLayer.hipsName + '"',
      };
    }

    // No previous acknowledged layer — offer default optical, unless we are
    // already requesting that default layer as the current switch target.
    if (
      state.layerCommandSent ||
      state.uiState === UI.FAILED ||
      state.uiState === UI.TIMED_OUT ||
      state.uiState === UI.ACKNOWLEDGED_UNVERIFIED
    ) {
      if (normalizeCompare(state.requestedSurveyName, DEFAULT_OPTICAL_LAYER)) {
        return null;
      }
      if (
        state.currentAcknowledgedLayer &&
        normalizeCompare(state.currentAcknowledgedLayer.hipsName, DEFAULT_OPTICAL_LAYER) &&
        state.uiState === UI.ACKNOWLEDGED_UNVERIFIED
      ) {
        return null;
      }
      return {
        kind: KIND.RESTORE_DEFAULT,
        buttonId: DEFAULT_OPTICAL_BUTTON_ID,
        hipsName: DEFAULT_OPTICAL_LAYER,
        label: 'Restore Default Optical: "' + DEFAULT_OPTICAL_LAYER + '"',
      };
    }
    return null;
  }

  function shouldShowRestoreAction(state) {
    if (
      state.uiState === UI.SWITCHING ||
      state.uiState === UI.FAILED ||
      state.uiState === UI.TIMED_OUT ||
      state.uiState === UI.ACKNOWLEDGED_UNVERIFIED
    ) {
      return !!getRestoreAction(state);
    }
    return false;
  }

  function applyAcknowledgement(state, acknowledgedName, pending) {
    if (!pending || isStale(state, pending.generation)) {
      return { applied: false, reason: "stale" };
    }
    var buttonId = pending.buttonId;
    var kind = pending.kind || KIND.SWITCH;

    if (
      state.currentAcknowledgedLayer &&
      state.currentAcknowledgedLayer.hipsName &&
      !normalizeCompare(state.currentAcknowledgedLayer.hipsName, acknowledgedName)
    ) {
      state.previousAcknowledgedLayer = {
        hipsName: state.currentAcknowledgedLayer.hipsName,
        buttonId: state.currentAcknowledgedLayer.buttonId,
      };
    }

    state.currentAcknowledgedLayer = { hipsName: acknowledgedName, buttonId: buttonId };
    state.acknowledgedImageryButtonId = buttonId;
    state.acknowledgementSurveyName = acknowledgedName;
    state.requestedImageryButtonId = null;
    state.failureReason = null;
    state.layerCommandSent = false;
    state.requestKind = null;
    state.uiState =
      kind === KIND.RESTORE_PREVIOUS || kind === KIND.RESTORE_DEFAULT
        ? UI.RESTORED
        : UI.ACKNOWLEDGED_UNVERIFIED;
    return { applied: true, uiState: state.uiState, acknowledgedLayer: state.currentAcknowledgedLayer };
  }

  function applyFailure(state, message, pending) {
    if (pending && isStale(state, pending.generation)) {
      return { applied: false, reason: "stale" };
    }
    state.uiState = UI.FAILED;
    state.failureReason =
      typeof message === "string" && message.trim()
        ? message.trim()
        : "ESASky reported the layer change failed.";
    state.acknowledgementSurveyName = null;
    state.layerCommandSent = true;
    return { applied: true, uiState: state.uiState };
  }

  function applyTimeout(state, pending) {
    if (pending && isStale(state, pending.generation)) {
      return { applied: false, reason: "stale" };
    }
    state.uiState = UI.TIMED_OUT;
    state.failureReason =
      "ESASky did not acknowledge the layer change within the time limit. " +
      "A timeout does not prove the switch failed.";
    state.acknowledgementSurveyName = null;
    state.layerCommandSent = true;
    return { applied: true, uiState: state.uiState, autoRestore: false };
  }

  function buttonPresentation(state, buttonId) {
    var requested = state.requestedImageryButtonId === buttonId;
    var acknowledged = state.acknowledgedImageryButtonId === buttonId;
    var pending = requested && state.uiState === UI.SWITCHING;
    var confirmedSelected =
      acknowledged &&
      (state.uiState === UI.ACKNOWLEDGED_UNVERIFIED || state.uiState === UI.RESTORED);
    return {
      pending: pending,
      confirmedSelected: confirmedSelected,
      // Explicit: never confirmed merely because requested.
      activeClass: confirmedSelected,
      switchingClass: pending,
    };
  }

  function buildStatusMessage(state) {
    var requested = state.requestedSurveyName;
    var acknowledged = state.acknowledgementSurveyName;
    if (state.uiState === UI.SWITCHING) {
      return {
        text:
          'Switching survey layer to "' +
          (requested || "unknown") +
          '"… Waiting for ESASky acknowledgement.',
        kind: "switching",
        uiState: UI.SWITCHING,
      };
    }
    if (state.uiState === UI.ACKNOWLEDGED_UNVERIFIED) {
      return {
        text:
          'ESASky acknowledged survey layer "' +
          (acknowledged || "unknown") +
          '". Useful image coverage at these coordinates cannot be verified through the current ESASky message API.',
        kind: "acknowledged_unverified",
        uiState: UI.ACKNOWLEDGED_UNVERIFIED,
      };
    }
    if (state.uiState === UI.RESTORED) {
      return {
        text:
          'ESASky acknowledged survey layer "' +
          (acknowledged || "unknown") +
          '" (restored). Useful image coverage at these coordinates cannot be verified through the current ESASky message API.',
        kind: "restored",
        uiState: UI.RESTORED,
      };
    }
    if (state.uiState === UI.FAILED) {
      return {
        text:
          "ESASky layer switch failed" +
          (requested ? ' for "' + requested + '"' : "") +
          (state.failureReason ? ": " + state.failureReason : "."),
        kind: "failed",
        uiState: UI.FAILED,
      };
    }
    if (state.uiState === UI.TIMED_OUT) {
      return {
        text:
          "ESASky did not acknowledge the layer change" +
          (requested ? ' for "' + requested + '"' : "") +
          ". A timeout does not prove ESASky failed to switch. Useful coverage cannot be verified through the current ESASky message API.",
        kind: "timed_out",
        uiState: UI.TIMED_OUT,
      };
    }
    return { text: "", kind: null, uiState: UI.AVAILABLE };
  }

  function diagnosticSnapshot(state) {
    return {
      uiState: state.uiState,
      requestKind: state.requestKind,
      requestedSurveyName: state.requestedSurveyName,
      acknowledgementSurveyName: state.acknowledgementSurveyName,
      requestedImageryButtonId: state.requestedImageryButtonId,
      acknowledgedImageryButtonId: state.acknowledgedImageryButtonId,
      failureReason: state.failureReason,
      previousAcknowledgedLayer: state.previousAcknowledgedLayer
        ? {
            hipsName: state.previousAcknowledgedLayer.hipsName,
            buttonId: state.previousAcknowledgedLayer.buttonId,
          }
        : null,
      currentAcknowledgedLayer: state.currentAcknowledgedLayer
        ? {
            hipsName: state.currentAcknowledgedLayer.hipsName,
            buttonId: state.currentAcknowledgedLayer.buttonId,
          }
        : null,
      generation: state.generation,
      layerCommandSent: state.layerCommandSent,
    };
  }

  function resetAll(state) {
    state.generation += 1;
    state.uiState = UI.AVAILABLE;
    state.requestKind = null;
    state.requestedImageryButtonId = null;
    state.acknowledgedImageryButtonId = null;
    state.requestedSurveyName = null;
    state.acknowledgementSurveyName = null;
    state.failureReason = null;
    state.previousAcknowledgedLayer = null;
    state.currentAcknowledgedLayer = null;
    state.layerCommandSent = false;
    return state.generation;
  }

  return {
    UI: UI,
    KIND: KIND,
    DEFAULT_OPTICAL_LAYER: DEFAULT_OPTICAL_LAYER,
    DEFAULT_OPTICAL_BUTTON_ID: DEFAULT_OPTICAL_BUTTON_ID,
    createState: createState,
    invalidatePending: invalidatePending,
    isStale: isStale,
    beginSwitch: beginSwitch,
    getRestoreAction: getRestoreAction,
    shouldShowRestoreAction: shouldShowRestoreAction,
    applyAcknowledgement: applyAcknowledgement,
    applyFailure: applyFailure,
    applyTimeout: applyTimeout,
    buttonPresentation: buttonPresentation,
    buildStatusMessage: buildStatusMessage,
    diagnosticSnapshot: diagnosticSnapshot,
    resetAll: resetAll,
    normalizeCompare: normalizeCompare,
  };
});
