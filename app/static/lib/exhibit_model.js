/* exhibit_model.js
 *
 * Pure helpers for Curated Exhibit / Story Path Mode.
 * No fetch, no Stellarium, no audio playback.
 */
(function (root) {
  "use strict";

  var STORAGE_KEY = "sc-exhibit-resume";
  var SAFE_AUTO_ADVANCE = {
    intro: true,
    constellation_story: true,
    cultural_story: true,
    object_focus: true,
    archaeoastronomy: true,
    same_sky_comparison: true,
    outro: true,
  };

  function defaultPrefs() {
    return {
      autoAdvance: false,
      provider: "",
      voice: "",
    };
  }

  function parseResume(raw) {
    if (!raw) return null;
    var data = raw;
    if (typeof raw === "string") {
      try { data = JSON.parse(raw); } catch (_err) { return null; }
    }
    if (!data || typeof data !== "object") return null;
    if (!data.exhibit_id || typeof data.exhibit_id !== "string") return null;
    var step = Number(data.last_completed_step);
    if (!Number.isFinite(step) || step < 0) step = 0;
    return {
      exhibit_id: data.exhibit_id,
      last_completed_step: Math.floor(step),
      provider: data.provider || "",
      voice: data.voice || "",
      auto_advance: !!data.auto_advance,
    };
  }

  function serializeResume(state) {
    var parsed = parseResume(state);
    if (!parsed) return "";
    return JSON.stringify({
      exhibit_id: parsed.exhibit_id,
      last_completed_step: parsed.last_completed_step,
      provider: parsed.provider || "",
      voice: parsed.voice || "",
      auto_advance: !!parsed.auto_advance,
    });
  }

  function resumePrompt(exhibitTitle, stepIndex) {
    var n = Number(stepIndex);
    if (!Number.isFinite(n) || n < 0) n = 0;
    return "Resume " + (exhibitTitle || "exhibit") + " at Step " + (n + 1) + "?";
  }

  function progressLabel(index, total) {
    return "Step " + (Number(index) + 1) + " of " + Number(total);
  }

  function progressPercent(index, total) {
    var count = Number(total);
    if (!count || count <= 0) return 0;
    return Math.min(100, Math.round(((Number(index) + 1) / count) * 100));
  }

  function evidenceBadgeLabel(key) {
    if (key === "cultural_source") return "CULTURAL SOURCE";
    if (key === "historical_source") return "HISTORICAL SOURCE";
    if (key === "community_sourced") return "COMMUNITY-SOURCED";
    if (key === "archaeological_inference") return "ARCHAEOLOGICAL INFERENCE";
    if (key === "strong_evidence") return "STRONG EVIDENCE";
    if (key === "scholarly_interpretation") return "SCHOLARLY INTERPRETATION";
    if (key === "cultural_sky_knowledge") return "CULTURAL SKY KNOWLEDGE";
    if (key === "historical_astronomy") return "HISTORICAL ASTRONOMY";
    if (key === "measured_signal") return "MEASURED SIGNAL";
    if (key === "measurement_derived_audio") return "MEASUREMENT-DERIVED AUDIO";
    if (key === "audification") return "AUDIFICATION";
    if (key === "data_sonification") return "DATA SONIFICATION";
    if (key === "pulse_timing_data") return "PULSE / TIMING DATA";
    if (key === "generated_cartography_sonification") return "GENERATED CARTOGRAPHY SONIFICATION";
    return "";
  }

  function isSafeAutoAdvanceType(stepType) {
    return !!SAFE_AUTO_ADVANCE[stepType];
  }

  function shouldAutoAdvance(flags) {
    flags = flags || {};
    if (!flags.autoAdvance) return false;
    if (!flags.ended) return false;
    if (flags.historicalPending) return false;
    if (!isSafeAutoAdvanceType(flags.stepType)) return false;
    if (!flags.hasNext) return false;
    return true;
  }

  function historicalConfirmationCopy(year) {
    var label = year == null || year === "" ? "XXXX" : String(year);
    return {
      prompt: "View reconstructed sky for approximately AD " + label + "?",
      explanation: "This uses modern astronomical simulation. It is not direct archaeological evidence. This uses modern astronomical models to reconstruct the sky. It does not independently prove the archaeological or historical interpretation.",
      applyLabel: "Apply Historical Sky",
      reconstructionLabel: "astronomical reconstruction",
    };
  }

  function mediaRemainsManual(step) {
    if (!step) return true;
    return step.media_autoplay !== true && (step.media || {}).autoplay !== true;
  }

  var ExhibitModel = {
    STORAGE_KEY: STORAGE_KEY,
    defaultAutoAdvance: false,
    noAutoplay: true,
    defaultPrefs: defaultPrefs,
    parseResume: parseResume,
    serializeResume: serializeResume,
    resumePrompt: resumePrompt,
    progressLabel: progressLabel,
    progressPercent: progressPercent,
    evidenceBadgeLabel: evidenceBadgeLabel,
    isSafeAutoAdvanceType: isSafeAutoAdvanceType,
    shouldAutoAdvance: shouldAutoAdvance,
    historicalConfirmationCopy: historicalConfirmationCopy,
    mediaRemainsManual: mediaRemainsManual,
  };

  root.ExhibitModel = ExhibitModel;
  if (typeof module === "object" && module.exports) {
    module.exports = ExhibitModel;
  }
})(typeof self !== "undefined" ? self : this);
