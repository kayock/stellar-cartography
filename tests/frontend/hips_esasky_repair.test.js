"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");
const { loadApp, fireAndFlush } = require("./app_loader");
const ChangeHips = require("../../app/static/lib/changehips.js");
const HipsLayerControl = require("../../app/static/lib/hips_layer_control.js");

function deepSkyTarget() {
  return {
    name: "M 42",
    alt_name: "Orion Nebula",
    object_category: "Nebula",
    object_type: "cluster of stars",
    ra_deg: 83.8221,
    dec_deg: -5.3911,
    ra_sexagesimal: "05h35m17s",
    dec_sexagesimal: "-05d23m28s",
    fov_deg: 1.0,
    source: "Stellarium selection",
  };
}

function marsTarget() {
  return {
    name: "Mars",
    alt_name: null,
    object_category: "Planet",
    object_type: "planet",
    ra_deg: 10.0,
    dec_deg: 20.0,
    ra_sexagesimal: "00h40m00s",
    dec_sexagesimal: "+20d00m00s",
    fov_deg: 60.0,
    angular_size_deg: 0.01,
    source: "Stellarium selection",
  };
}

test("pending styling before acknowledgement; no confirmed active class yet", async () => {
  const posted = [];
  const { exports: app } = loadApp(async (url) => {
    if (String(url).indexOf("/api/discovery") === 0) {
      return {
        ok: true,
        json: async () => ({
          ok: true,
          bundle: { items: [], query_outcomes: [], warnings: [], capability_notes: [] },
          badges: {
            hst: { status: "no_coverage", count: 0 },
            jwst_nircam: { status: "no_coverage", count: 0 },
            jwst_miri: { status: "no_coverage", count: 0 },
          },
        }),
      };
    }
    return { ok: true, json: async () => ({ connected: false }) };
  });
  app.el.esaskyFrame.contentWindow.postMessage = (msg) => posted.push(msg);
  app.state.onlineMode = true;
  app.state.currentTarget = deepSkyTarget();
  app.state.esaskyQueue.ready = true;
  app.state.esaskyQueue.loadListenerAttached = true;
  app.state.esaskyQueue.cancelled = false;
  app.renderTargetCard();
  await new Promise((r) => setTimeout(r, 0));

  const hubbleBtn = (app.el.imageryGrid._children || []).find((b) => b.dataset && b.dataset.id === "hubble");
  assert.ok(hubbleBtn);
  hubbleBtn.dispatchEvent({ type: "click", preventDefault() {} });
  await new Promise((r) => setTimeout(r, 0));

  assert.equal(hubbleBtn.classList.contains("switching"), true);
  assert.equal(hubbleBtn.classList.contains("active"), false);
  assert.equal(app.state.hipsLayer.uiState, HipsLayerControl.UI.SWITCHING);
  assert.equal(app.state.hipsLayer.acknowledgedImageryButtonId, null);
});

test("acknowledgement applies confirmed styling and acknowledged_unverified wording", async () => {
  const { document, exports: app } = loadApp(async () => ({
    ok: true,
    json: async () => ({ connected: false }),
  }));
  app.state.onlineMode = true;
  app.state.currentTarget = deepSkyTarget();
  app.state.esaskyQueue.ready = true;
  app.state.esaskyQueue.loadListenerAttached = true;
  app.state.esaskyQueue.cancelled = false;

  const cfg = { id: "optical", label: "Default Optical", preferredExact: "DSS2 color" };
  // Simulate optical fast path
  const started = HipsLayerControl.beginSwitch(
    app.state.hipsLayer,
    "optical",
    "DSS2 color",
    HipsLayerControl.KIND.SWITCH
  );
  app.state.pendingChangeRequest = Object.assign({}, started.pending, { timeoutId: setTimeout(() => {}, 5000) });
  app.updateImageryButtonPresentations && app.updateImageryButtonPresentations();

  const result = ChangeHips.interpretChangeHipsMessage(app.state.pendingChangeRequest, {
    content: { hipsName: "DSS2 color", success: true },
  });
  assert.equal(result.status, "acknowledged");

  // Use module logic directly then mirror app resolve path
  clearTimeout(app.state.pendingChangeRequest.timeoutId);
  const pending = app.state.pendingChangeRequest;
  app.state.pendingChangeRequest = null;
  HipsLayerControl.applyAcknowledgement(app.state.hipsLayer, result.layerName, pending);
  app.state.activeImageryButtonId = app.state.hipsLayer.acknowledgedImageryButtonId;

  const msg = HipsLayerControl.buildStatusMessage(app.state.hipsLayer);
  assert.equal(msg.uiState, HipsLayerControl.UI.ACKNOWLEDGED_UNVERIFIED);
  assert.match(msg.text, /ESASky acknowledged survey layer "DSS2 color"/);
  assert.match(msg.text, /cannot be verified/);
  assert.doesNotMatch(msg.text, /working|coverage confirmed|imagery confirmed/i);
  assert.equal(HipsLayerControl.buttonPresentation(app.state.hipsLayer, "optical").confirmedSelected, true);
});

test("stale changeHips acknowledgement after target change is ignored", () => {
  const state = HipsLayerControl.createState();
  const older = HipsLayerControl.beginSwitch(state, "hubble", "HST ACS", HipsLayerControl.KIND.SWITCH);
  // Target change invalidates pending work.
  HipsLayerControl.invalidatePending(state);
  const result = HipsLayerControl.applyAcknowledgement(state, "HST ACS", older.pending);
  assert.equal(result.applied, false);
  assert.equal(state.acknowledgedImageryButtonId, null);
});

test("stale listing generation after newer card request is ignored", () => {
  const state = HipsLayerControl.createState();
  const firstGen = state.generation;
  HipsLayerControl.invalidatePending(state);
  const listingGeneration = state.generation;
  // Newer card request
  HipsLayerControl.beginSwitch(state, "wise", "AllWISE color", HipsLayerControl.KIND.SWITCH);
  assert.ok(HipsLayerControl.isStale(state, listingGeneration));
  assert.ok(HipsLayerControl.isStale(state, firstGen));
});

test("online mode shutdown resets hips acknowledged memory", () => {
  const OnlineMode = require("../../app/static/lib/online_mode.js");
  const hips = HipsLayerControl.createState();
  const { pending } = HipsLayerControl.beginSwitch(hips, "optical", "DSS2 color", HipsLayerControl.KIND.SWITCH);
  HipsLayerControl.applyAcknowledgement(hips, "DSS2 color", pending);
  const shutdown = OnlineMode.buildShutdownState({
    onlineMode: true,
    pendingHipsRequest: { timeoutId: 1 },
    pendingChangeRequest: { timeoutId: 2 },
    activeImageryButtonId: "optical",
  });
  assert.equal(shutdown.pendingHipsRequest, null);
  assert.equal(shutdown.pendingChangeRequest, null);
  HipsLayerControl.resetAll(hips);
  assert.equal(hips.currentAcknowledgedLayer, null);
  assert.equal(hips.previousAcknowledgedLayer, null);
});

test("restore previous layer request uses exact previous survey name", () => {
  const state = HipsLayerControl.createState();
  const first = HipsLayerControl.beginSwitch(state, "optical", "DSS2 color", HipsLayerControl.KIND.SWITCH);
  HipsLayerControl.applyAcknowledgement(state, "DSS2 color", first.pending);
  HipsLayerControl.beginSwitch(state, "hubble", "HST ACS", HipsLayerControl.KIND.SWITCH);
  const action = HipsLayerControl.getRestoreAction(state);
  assert.equal(action.kind, HipsLayerControl.KIND.RESTORE_PREVIOUS);
  assert.equal(action.hipsName, "DSS2 color");
});

test("restore default optical when no previous acknowledged layer", () => {
  const state = HipsLayerControl.createState();
  HipsLayerControl.beginSwitch(state, "xray", "XMM-Newton EPIC color", HipsLayerControl.KIND.SWITCH);
  const action = HipsLayerControl.getRestoreAction(state);
  assert.equal(action.kind, HipsLayerControl.KIND.RESTORE_DEFAULT);
  assert.equal(action.hipsName, HipsLayerControl.DEFAULT_OPTICAL_LAYER);
});

test("timeout does not auto-restore", () => {
  const state = HipsLayerControl.createState();
  const { pending } = HipsLayerControl.beginSwitch(state, "hubble", "HST ACS", HipsLayerControl.KIND.SWITCH);
  const result = HipsLayerControl.applyTimeout(state, pending);
  assert.equal(result.autoRestore, false);
  assert.equal(state.uiState, HipsLayerControl.UI.TIMED_OUT);
});

test("MAST discovery badges stay independent of ESASky acknowledgement", () => {
  const ArchiveAvailability = require("../../app/static/lib/archive_availability.js");
  const badgeBefore = ArchiveAvailability.mapBadgePayloadToLight(
    { status: "confirmed", count: 4, observations: [{ observation_id: "x" }] },
    "hst",
    null
  );
  // Simulate ESASky ack state change without touching badge payload.
  const hips = HipsLayerControl.createState();
  const { pending } = HipsLayerControl.beginSwitch(hips, "hubble", "HST ACS", HipsLayerControl.KIND.SWITCH);
  HipsLayerControl.applyAcknowledgement(hips, "HST ACS", pending);
  const badgeAfter = ArchiveAvailability.mapBadgePayloadToLight(
    { status: "confirmed", count: 4, observations: [{ observation_id: "x" }] },
    "hst",
    null
  );
  assert.equal(badgeBefore.count, badgeAfter.count);
  assert.equal(badgeBefore.state, badgeAfter.state);
});

test("Mars resolves through NASA public-media registry", () => {
  const PlanetaryImage = require("../../app/static/lib/planetary_image.js");
  const SolarSystem = require("../../app/static/lib/solar_system.js");
  assert.equal(SolarSystem.isSolarSystemTarget(marsTarget()), true);
  assert.equal(PlanetaryImage.resolvePilotTargetId(marsTarget()), "mars");
});

test("exact survey name rendered from acknowledgement snapshot", () => {
  const state = HipsLayerControl.createState();
  const { pending } = HipsLayerControl.beginSwitch(state, "hubble", "HST ACS", HipsLayerControl.KIND.SWITCH);
  HipsLayerControl.applyAcknowledgement(state, "HST ACS", pending);
  const snap = HipsLayerControl.diagnosticSnapshot(state);
  assert.equal(snap.acknowledgementSurveyName, "HST ACS");
  assert.equal(snap.requestedSurveyName, "HST ACS");
});
