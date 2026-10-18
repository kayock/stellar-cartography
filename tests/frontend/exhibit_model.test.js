"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const ExhibitModel = require("../../app/static/lib/exhibit_model.js");

test("auto-advance is off by default and media stays manual", () => {
  assert.equal(ExhibitModel.defaultAutoAdvance, false);
  assert.equal(ExhibitModel.noAutoplay, true);
  assert.equal(ExhibitModel.defaultPrefs().autoAdvance, false);
  assert.equal(ExhibitModel.mediaRemainsManual({ media: { autoplay: false } }), true);
});

test("resume payload stores exhibit step and voice prefs only", () => {
  const raw = ExhibitModel.serializeResume({
    exhibit_id: "southwestern_skies",
    last_completed_step: 3,
    provider: "father_fox",
    voice: "default",
    auto_advance: true,
  });
  const parsed = ExhibitModel.parseResume(raw);
  assert.equal(parsed.exhibit_id, "southwestern_skies");
  assert.equal(parsed.last_completed_step, 3);
  assert.equal(parsed.provider, "father_fox");
  assert.equal(parsed.auto_advance, true);
  assert.equal(ExhibitModel.resumePrompt("Southwestern Skies", 3), "Resume Southwestern Skies at Step 4?");
});

test("progress count is one-based", () => {
  assert.equal(ExhibitModel.progressLabel(0, 10), "Step 1 of 10");
  assert.equal(ExhibitModel.progressPercent(4, 10), 50);
});

test("auto-advance stays off unless a safe non-media step ends", () => {
  assert.equal(ExhibitModel.shouldAutoAdvance({ autoAdvance: false, ended: true, hasNext: true, stepType: "intro" }), false);
  assert.equal(ExhibitModel.shouldAutoAdvance({ autoAdvance: true, ended: true, hasNext: true, stepType: "intro" }), true);
  assert.equal(ExhibitModel.shouldAutoAdvance({ autoAdvance: true, ended: true, hasNext: true, stepType: "cosmic_signal" }), false);
  assert.equal(ExhibitModel.shouldAutoAdvance({ autoAdvance: true, ended: true, hasNext: true, stepType: "official_media" }), false);
  assert.equal(ExhibitModel.shouldAutoAdvance({ autoAdvance: true, ended: true, hasNext: true, stepType: "historical_reconstruction", historicalPending: true }), false);
  assert.equal(ExhibitModel.isSafeAutoAdvanceType("archaeoastronomy"), true);
});

test("historical confirmation copy requires explicit apply", () => {
  const copy = ExhibitModel.historicalConfirmationCopy(1050);
  assert.equal(copy.prompt, "View reconstructed sky for approximately AD 1050?");
  assert.match(copy.explanation, /modern astronomical simulation/i);
  assert.equal(copy.applyLabel, "Apply Historical Sky");
  assert.equal(copy.reconstructionLabel, "astronomical reconstruction");
});

test("evidence badge labels match exhibit vocabulary", () => {
  assert.equal(ExhibitModel.evidenceBadgeLabel("cultural_source"), "CULTURAL SOURCE");
  assert.equal(ExhibitModel.evidenceBadgeLabel("historical_source"), "HISTORICAL SOURCE");
  assert.equal(ExhibitModel.evidenceBadgeLabel("community_sourced"), "COMMUNITY-SOURCED");
  assert.equal(ExhibitModel.evidenceBadgeLabel("archaeological_inference"), "ARCHAEOLOGICAL INFERENCE");
  assert.equal(ExhibitModel.evidenceBadgeLabel("strong_evidence"), "STRONG EVIDENCE");
  assert.equal(ExhibitModel.evidenceBadgeLabel("scholarly_interpretation"), "SCHOLARLY INTERPRETATION");
  assert.equal(ExhibitModel.evidenceBadgeLabel("cultural_sky_knowledge"), "CULTURAL SKY KNOWLEDGE");
  assert.equal(ExhibitModel.evidenceBadgeLabel("historical_astronomy"), "HISTORICAL ASTRONOMY");
  assert.equal(ExhibitModel.evidenceBadgeLabel("measured_signal"), "MEASURED SIGNAL");
  assert.equal(ExhibitModel.evidenceBadgeLabel("measurement_derived_audio"), "MEASUREMENT-DERIVED AUDIO");
  assert.equal(ExhibitModel.evidenceBadgeLabel("audification"), "AUDIFICATION");
  assert.equal(ExhibitModel.evidenceBadgeLabel("data_sonification"), "DATA SONIFICATION");
  assert.equal(ExhibitModel.evidenceBadgeLabel("pulse_timing_data"), "PULSE / TIMING DATA");
  assert.equal(ExhibitModel.evidenceBadgeLabel("generated_cartography_sonification"), "GENERATED CARTOGRAPHY SONIFICATION");
});

test("data sonification steps do not auto-advance", () => {
  assert.equal(ExhibitModel.shouldAutoAdvance({ autoAdvance: true, ended: true, hasNext: true, stepType: "data_sonification" }), false);
  assert.equal(ExhibitModel.isSafeAutoAdvanceType("data_sonification"), false);
  assert.equal(ExhibitModel.progressLabel(0, 11), "Step 1 of 11");
  assert.equal(ExhibitModel.progressPercent(10, 11), 100);
});
