"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");

const TargetModel = require(path.join(__dirname, "..", "..", "app", "static", "lib", "target_model.js"));

test("official numeric Stellarium coordinates reach the frontend target model", () => {
  // Shape mirrors exactly what GET /api/selection returns for the
  // documented M 31 getInfoMap payload from the R0.1.1 audit findings.
  const apiResponse = {
    ok: true,
    connected: true,
    name: "M 31",
    alt_name: "Andromeda Galaxy",
    object_category: "Nebula",
    object_type: "galaxy",
    object_subtype: null,
    catalogue_designations: null,
    constellation: "And",
    apparent_magnitude: 3.44,
    angular_size_deg: 3.167,
    altitude_deg: 35.2,
    azimuth_deg: 122.8,
    above_horizon: true,
    ra_deg: 10.6847,
    dec_deg: 41.26875,
    ra_sexagesimal: "00h42m44.28s",
    dec_sexagesimal: "+41d16m07.50s",
    fov_deg: 5.2,
    error: null,
  };

  const target = TargetModel.buildTargetFromSelection(apiResponse);

  assert.equal(target.name, "M 31");
  assert.equal(target.ra_deg, 10.6847);
  assert.equal(target.dec_deg, 41.26875);
  assert.equal(target.object_category, "Nebula");
  assert.equal(target.object_type, "galaxy");
  assert.equal(target.constellation, "And");
  assert.equal(target.apparent_magnitude, 3.44);
  assert.equal(target.angular_size_deg, 3.167);
  assert.equal(target.altitude_deg, 35.2);
  assert.equal(target.azimuth_deg, 122.8);
  assert.equal(target.above_horizon, true);
  assert.equal(target.fov_deg, 5.2);
  assert.equal(target.source, "Stellarium selection");
});

test("manual entry target model carries decimal coordinates through untouched", () => {
  const apiResponse = {
    ok: true,
    ra_deg: 83.63,
    dec_deg: -5.39,
    ra_sexagesimal: "05h34m31.20s",
    dec_sexagesimal: "-05d23m24.00s",
  };
  const target = TargetModel.buildTargetFromManual(apiResponse, "Orion Nebula");
  assert.equal(target.name, "Orion Nebula");
  assert.equal(target.ra_deg, 83.63);
  assert.equal(target.dec_deg, -5.39);
  assert.equal(target.source, "Manual entry");
});

test("manual entry without a name falls back to a generic label", () => {
  const target = TargetModel.buildTargetFromManual({ ra_deg: 10, dec_deg: 10 }, "");
  assert.equal(target.name, "Manual target");
});

// --- Contract: failed selection after a successful one leaves no stale,
// actionable target (Requirement 3 in the R0.1.2 repair request). Mirrors
// online_mode.test.js's approach: this proves the pure state-transition
// contract that app.js's clearStaleTargetAfterFailedSelection() applies
// as DOM side effects; it doesn't itself touch the DOM.
test("a successful selection followed by an empty/failed selection clears currentTarget and all target-dependent pending state", () => {
  // A successful selection first, as app.js would apply it.
  const appState = {
    currentTarget: TargetModel.buildTargetFromSelection({
      ok: true,
      name: "M 31",
      ra_deg: 10.6847,
      dec_deg: 41.26875,
    }),
    pendingHipsRequest: { buttonId: "hst", timeoutId: 111 },
    pendingChangeRequest: { buttonId: "hst", requestedName: "HST ACS", timeoutId: 222 },
    activeImageryButtonId: "hst",
  };
  assert.ok(appState.currentTarget, "sanity check: the successful selection did produce a target");

  // Now Stellarium reports an empty/failed selection (ok:false).
  const cleared = TargetModel.buildFailedSelectionState(appState);

  assert.equal(cleared.currentTarget, null, "the prior target must not remain the current target");
  assert.equal(cleared.pendingHipsRequest, null, "no imagery listing request tied to the prior target may resolve later");
  assert.equal(cleared.pendingChangeRequest, null, "no changeHips request tied to the prior target may resolve later");
  assert.equal(cleared.activeImageryButtonId, null, "no imagery button should still read as active for a target that's gone");
  assert.equal(cleared.aboutObjectCardHidden, true);
  assert.equal(cleared.openEsaskyDisabled, true);
  assert.deepEqual(
    cleared.timeoutIdsToClear.slice().sort(),
    [111, 222],
    "both in-flight request timers must be surfaced for the caller to clearTimeout()"
  );
});

test("failed selection state is still well-formed when there was nothing pending", () => {
  const cleared = TargetModel.buildFailedSelectionState({
    currentTarget: null,
    pendingHipsRequest: null,
    pendingChangeRequest: null,
    activeImageryButtonId: null,
  });
  assert.equal(cleared.currentTarget, null);
  assert.deepEqual(cleared.timeoutIdsToClear, []);
});
