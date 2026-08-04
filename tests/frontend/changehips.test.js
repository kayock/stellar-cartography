"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");

const ChangeHips = require(path.join(__dirname, "..", "..", "app", "static", "lib", "changehips.js"));

test("changeHips failure is not shown as success (extras.message)", () => {
  const pending = { requestedName: "JWST NIRCam mosaic" };
  const message = {
    content: { hipsName: "JWST NIRCam mosaic", extras: { message: "Layer temporarily unavailable" } },
  };
  const result = ChangeHips.interpretChangeHipsMessage(pending, message);
  assert.equal(result.status, "error");
  assert.equal(result.message, "Layer temporarily unavailable");
});

test("explicit success:false is treated as an error, not success", () => {
  const pending = { requestedName: "DSS2 color" };
  const message = { content: { success: false } };
  const result = ChangeHips.interpretChangeHipsMessage(pending, message);
  assert.equal(result.status, "error");
});

test("acknowledgement containing the requested layer is confirmed", () => {
  const pending = { requestedName: "HST ACS" };
  const message = { content: { hipsName: "HST ACS", success: true } };
  const result = ChangeHips.interpretChangeHipsMessage(pending, message);
  assert.equal(result.status, "acknowledged");
  assert.equal(result.layerName, "HST ACS");
});

test("normalized layer name comparison accepts equivalent whitespace/case", () => {
  assert.equal(ChangeHips.layersCorrespond("HST ACS", "hst  acs"), true);
  assert.equal(ChangeHips.normalizeLayerName("  DSS2   color "), "dss2 color");
});

test("mismatched layer acknowledgement is rejected", () => {
  const pending = { requestedName: "HST ACS" };
  const message = { content: { hipsName: "AllWISE color", success: true } };
  const result = ChangeHips.interpretChangeHipsMessage(pending, message);
  assert.equal(result.status, "mismatch");
  assert.equal(result.layerName, "AllWISE color");
});

test("generic success without a layer name is not confirmation", () => {
  const pending = { requestedName: "DSS2 color" };
  const message = { content: { success: true } };
  const result = ChangeHips.interpretChangeHipsMessage(pending, message);
  assert.equal(result.status, "unrelated");
});

test("status-only message without layer name is not confirmation", () => {
  const pending = { requestedName: "DSS2 color" };
  const message = { content: { status: "OK" } };
  const result = ChangeHips.interpretChangeHipsMessage(pending, message);
  assert.equal(result.status, "unrelated");
});

test("a getAvailableHips-shaped listing is not mistaken for a changeHips result", () => {
  const pending = { requestedName: "AllWISE color" };
  const message = { content: { OPTICAL: [{ name: "DSS2 color" }] } };
  const result = ChangeHips.interpretChangeHipsMessage(pending, message);
  assert.equal(result.status, "unrelated");
});

test("an unrelated message with no name and no status is left unrelated", () => {
  const pending = { requestedName: "AllWISE color" };
  const result = ChangeHips.interpretChangeHipsMessage(pending, { content: { somethingElse: true } });
  assert.equal(result.status, "unrelated");
});
