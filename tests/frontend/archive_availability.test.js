"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");
const ArchiveAvailability = require("../../app/static/lib/archive_availability.js");

test("accessible text not dependent on color", () => {
  const text = ArchiveAvailability.accessibleText(ArchiveAvailability.STATE.CONFIRMED, "hst", 14);
  assert.match(text, /Hubble: 14 archive observations/);
});

test("cache key and stale generation", () => {
  const state = ArchiveAvailability.createState();
  const gen = state.generation;
  ArchiveAvailability.bumpGeneration(state);
  assert.ok(ArchiveAvailability.isStale(state, gen));
});

test("same-target in-flight suppression", () => {
  const state = ArchiveAvailability.createState();
  const key = ArchiveAvailability.cacheKey(10, 20, "hst");
  ArchiveAvailability.markInFlight(state, key);
  assert.ok(ArchiveAvailability.shouldSkipInFlight(state, key));
});

test("cached result reuse", () => {
  const state = ArchiveAvailability.createState();
  const key = ArchiveAvailability.cacheKey(10, 20, "hst");
  const now = Date.now();
  ArchiveAvailability.storeCache(state, key, { status: "confirmed", count: 2 }, now);
  assert.ok(ArchiveAvailability.shouldUseCache(state, key, now + 1000));
});

test("rate limit repeated checks", () => {
  const state = ArchiveAvailability.createState();
  const key = ArchiveAvailability.cacheKey(10, 20, "hst");
  const now = Date.now();
  state.lastRequestAt[key] = now;
  assert.ok(ArchiveAvailability.shouldRateLimit(state, key, now + 1000));
});

test("map api states", () => {
  const confirmed = ArchiveAvailability.mapApiToLight({ status: "confirmed", count: 5 }, "hst", null);
  assert.equal(confirmed.state, ArchiveAvailability.STATE.CONFIRMED);
  const none = ArchiveAvailability.mapApiToLight({ status: "no_coverage", count: 0 }, "jwst_miri", null);
  assert.equal(none.state, ArchiveAvailability.STATE.NO_COVERAGE);
});

test("discovery badge mapping remains compatible", () => {
  const light = ArchiveAvailability.mapBadgePayloadToLight(
    { status: "confirmed", count: 3 },
    "hst",
    null
  );
  assert.equal(light.state, ArchiveAvailability.STATE.CONFIRMED);
});

test("online mode off makes zero requests at app layer", () => {
  const state = ArchiveAvailability.createState();
  ArchiveAvailability.resetForOffline(state);
  assert.equal(Object.keys(state.inFlight).length, 0);
});
