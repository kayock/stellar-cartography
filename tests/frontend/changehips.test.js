"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");

const ChangeHips = require(path.join(__dirname, "..", "..", "app", "static", "lib", "changehips.js"));

test("changeHips failure is not shown as success (extras.message)", () => {
  const pending = { requestedName: "JWST NIRCam mosaic" };
  const message = { content: { hipsName: "JWST NIRCam mosaic", extras: { message: "Layer temporarily unavailable" } } };
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

test("a confirmed hipsName with no failure indicator is reported as success", () => {
  const pending = { requestedName: "HST ACS" };
  const message = { content: { hipsName: "HST ACS", success: true } };
  const result = ChangeHips.interpretChangeHipsMessage(pending, message);
  assert.equal(result.status, "success");
  assert.equal(result.layerName, "HST ACS");
});

test("a getAvailableHips-shaped listing is not mistaken for a changeHips result", () => {
  const pending = { requestedName: "AllWISE color" };
  const message = { content: { OPTICAL: [{ name: "DSS2 color" }] } };
  const result = ChangeHips.interpretChangeHipsMessage(pending, message);
  assert.equal(result.status, "unrelated");
});

test("an unrelated message with no name and no status is left unrelated (caller keeps waiting)", () => {
  const pending = { requestedName: "AllWISE color" };
  const result = ChangeHips.interpretChangeHipsMessage(pending, { content: { somethingElse: true } });
  assert.equal(result.status, "unrelated");
});
