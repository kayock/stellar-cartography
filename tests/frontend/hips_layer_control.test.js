"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");
const HipsLayerControl = require("../../app/static/lib/hips_layer_control.js");

test("pending styling before acknowledgement; no confirmed styling yet", () => {
  const state = HipsLayerControl.createState();
  const { pending } = HipsLayerControl.beginSwitch(state, "hubble", "HST ACS", HipsLayerControl.KIND.SWITCH);
  assert.equal(state.uiState, HipsLayerControl.UI.SWITCHING);
  assert.equal(state.requestedImageryButtonId, "hubble");
  assert.equal(state.acknowledgedImageryButtonId, null);
  const hubble = HipsLayerControl.buttonPresentation(state, "hubble");
  assert.equal(hubble.pending, true);
  assert.equal(hubble.confirmedSelected, false);
  assert.equal(hubble.activeClass, false);
  assert.equal(hubble.switchingClass, true);
  assert.ok(pending);
});

test("confirmed styling only after acknowledgement", () => {
  const state = HipsLayerControl.createState();
  const { pending } = HipsLayerControl.beginSwitch(state, "hubble", "HST ACS", HipsLayerControl.KIND.SWITCH);
  HipsLayerControl.applyAcknowledgement(state, "HST ACS", pending);
  assert.equal(state.uiState, HipsLayerControl.UI.ACKNOWLEDGED_UNVERIFIED);
  assert.equal(state.acknowledgedImageryButtonId, "hubble");
  assert.equal(state.requestedImageryButtonId, null);
  const hubble = HipsLayerControl.buttonPresentation(state, "hubble");
  assert.equal(hubble.confirmedSelected, true);
  assert.equal(hubble.pending, false);
  assert.equal(hubble.activeClass, true);
});

test("acknowledged_unverified wording never claims working coverage", () => {
  const state = HipsLayerControl.createState();
  const { pending } = HipsLayerControl.beginSwitch(state, "optical", "DSS2 color", HipsLayerControl.KIND.SWITCH);
  HipsLayerControl.applyAcknowledgement(state, "DSS2 color", pending);
  const msg = HipsLayerControl.buildStatusMessage(state);
  assert.equal(msg.uiState, HipsLayerControl.UI.ACKNOWLEDGED_UNVERIFIED);
  assert.match(msg.text, /ESASky acknowledged survey layer "DSS2 color"/);
  assert.match(msg.text, /cannot be verified/);
  assert.doesNotMatch(msg.text, /working/i);
  assert.doesNotMatch(msg.text, /coverage confirmed/i);
  assert.doesNotMatch(msg.text, /imagery confirmed/i);
  assert.doesNotMatch(msg.text, /image available at this target/i);
});

test("stores previous acknowledged layer on switch to a new layer", () => {
  const state = HipsLayerControl.createState();
  const first = HipsLayerControl.beginSwitch(state, "optical", "DSS2 color", HipsLayerControl.KIND.SWITCH);
  HipsLayerControl.applyAcknowledgement(state, "DSS2 color", first.pending);
  const second = HipsLayerControl.beginSwitch(state, "hubble", "HST ACS", HipsLayerControl.KIND.SWITCH);
  HipsLayerControl.applyAcknowledgement(state, "HST ACS", second.pending);
  assert.deepEqual(state.previousAcknowledgedLayer, { hipsName: "DSS2 color", buttonId: "optical" });
  assert.deepEqual(state.currentAcknowledgedLayer, { hipsName: "HST ACS", buttonId: "hubble" });
});

test("restore previous layer action names exact survey", () => {
  const state = HipsLayerControl.createState();
  const first = HipsLayerControl.beginSwitch(state, "optical", "DSS2 color", HipsLayerControl.KIND.SWITCH);
  HipsLayerControl.applyAcknowledgement(state, "DSS2 color", first.pending);
  HipsLayerControl.beginSwitch(state, "xray", "XMM-Newton EPIC color", HipsLayerControl.KIND.SWITCH);
  assert.equal(HipsLayerControl.shouldShowRestoreAction(state), true);
  const action = HipsLayerControl.getRestoreAction(state);
  assert.equal(action.kind, HipsLayerControl.KIND.RESTORE_PREVIOUS);
  assert.equal(action.hipsName, "DSS2 color");
  assert.match(action.label, /DSS2 color/);
});

test("restore default optical when no previous acknowledged layer", () => {
  const state = HipsLayerControl.createState();
  HipsLayerControl.beginSwitch(state, "hubble", "HST ACS", HipsLayerControl.KIND.SWITCH);
  const action = HipsLayerControl.getRestoreAction(state);
  assert.equal(action.kind, HipsLayerControl.KIND.RESTORE_DEFAULT);
  assert.equal(action.hipsName, "DSS2 color");
  assert.match(action.label, /Restore Default Optical/);
});

test("timeout does not auto-restore", () => {
  const state = HipsLayerControl.createState();
  const { pending } = HipsLayerControl.beginSwitch(state, "hubble", "HST ACS", HipsLayerControl.KIND.SWITCH);
  const result = HipsLayerControl.applyTimeout(state, pending);
  assert.equal(result.autoRestore, false);
  assert.equal(state.uiState, HipsLayerControl.UI.TIMED_OUT);
  assert.equal(HipsLayerControl.shouldShowRestoreAction(state), true);
});

test("explicit failure keeps restore available", () => {
  const state = HipsLayerControl.createState();
  const first = HipsLayerControl.beginSwitch(state, "optical", "DSS2 color", HipsLayerControl.KIND.SWITCH);
  HipsLayerControl.applyAcknowledgement(state, "DSS2 color", first.pending);
  const second = HipsLayerControl.beginSwitch(state, "hubble", "HST ACS", HipsLayerControl.KIND.SWITCH);
  HipsLayerControl.applyFailure(state, "Layer temporarily unavailable", second.pending);
  assert.equal(state.uiState, HipsLayerControl.UI.FAILED);
  const action = HipsLayerControl.getRestoreAction(state);
  assert.equal(action.hipsName, "DSS2 color");
});

test("restore acknowledgement sets restored state and confirmed styling", () => {
  const state = HipsLayerControl.createState();
  const first = HipsLayerControl.beginSwitch(state, "optical", "DSS2 color", HipsLayerControl.KIND.SWITCH);
  HipsLayerControl.applyAcknowledgement(state, "DSS2 color", first.pending);
  const second = HipsLayerControl.beginSwitch(state, "hubble", "HST ACS", HipsLayerControl.KIND.SWITCH);
  HipsLayerControl.applyAcknowledgement(state, "HST ACS", second.pending);
  const restore = HipsLayerControl.beginSwitch(
    state,
    "optical",
    "DSS2 color",
    HipsLayerControl.KIND.RESTORE_PREVIOUS
  );
  HipsLayerControl.applyAcknowledgement(state, "DSS2 color", restore.pending);
  assert.equal(state.uiState, HipsLayerControl.UI.RESTORED);
  assert.equal(HipsLayerControl.buttonPresentation(state, "optical").confirmedSelected, true);
  assert.equal(HipsLayerControl.buttonPresentation(state, "hubble").confirmedSelected, false);
});

test("stale acknowledgement after invalidate is ignored", () => {
  const state = HipsLayerControl.createState();
  const { pending } = HipsLayerControl.beginSwitch(state, "hubble", "HST ACS", HipsLayerControl.KIND.SWITCH);
  HipsLayerControl.invalidatePending(state);
  const result = HipsLayerControl.applyAcknowledgement(state, "HST ACS", pending);
  assert.equal(result.applied, false);
  assert.equal(result.reason, "stale");
  assert.equal(state.acknowledgedImageryButtonId, null);
});

test("newer beginSwitch supersedes older pending generation", () => {
  const state = HipsLayerControl.createState();
  const older = HipsLayerControl.beginSwitch(state, "hubble", "HST ACS", HipsLayerControl.KIND.SWITCH);
  const newer = HipsLayerControl.beginSwitch(state, "wise", "AllWISE color", HipsLayerControl.KIND.SWITCH);
  assert.ok(HipsLayerControl.isStale(state, older.generation));
  assert.equal(HipsLayerControl.isStale(state, newer.generation), false);
  assert.equal(state.requestedImageryButtonId, "wise");
});

test("resetAll clears acknowledged layer memory on shutdown", () => {
  const state = HipsLayerControl.createState();
  const { pending } = HipsLayerControl.beginSwitch(state, "optical", "DSS2 color", HipsLayerControl.KIND.SWITCH);
  HipsLayerControl.applyAcknowledgement(state, "DSS2 color", pending);
  HipsLayerControl.resetAll(state);
  assert.equal(state.acknowledgedImageryButtonId, null);
  assert.equal(state.previousAcknowledgedLayer, null);
  assert.equal(state.currentAcknowledgedLayer, null);
  assert.equal(state.uiState, HipsLayerControl.UI.AVAILABLE);
});

test("diagnostic snapshot exposes requested and acknowledgement names safely", () => {
  const state = HipsLayerControl.createState();
  const { pending } = HipsLayerControl.beginSwitch(state, "hubble", "HST ACS", HipsLayerControl.KIND.SWITCH);
  HipsLayerControl.applyAcknowledgement(state, "HST ACS", pending);
  const snap = HipsLayerControl.diagnosticSnapshot(state);
  assert.equal(snap.acknowledgementSurveyName, "HST ACS");
  assert.equal(snap.requestedImageryButtonId, null);
  assert.equal(snap.acknowledgedImageryButtonId, "hubble");
});
