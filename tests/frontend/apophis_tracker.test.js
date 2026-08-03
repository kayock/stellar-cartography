"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");
const ApophisTracker = require("../../app/static/lib/apophis_tracker.js");

test("countdown calculation", () => {
  const days = ApophisTracker.computeCountdownDays(new Date("2026-01-01T00:00:00Z"));
  assert.ok(typeof days === "number");
});

test("official data normalization view model", () => {
  const vm = ApophisTracker.buildViewModel({
    ok: true,
    designation: "99942",
    name: "99942 Apophis",
    countdown_days: 1000,
    retrieved_at: "2026-07-31T00:00:00Z",
    source_agency: "NASA/JPL CNEOS",
    risk_status_available: false,
  });
  assert.equal(vm.designation, "99942");
  assert.equal(vm.sourceAgency, "NASA/JPL CNEOS");
});

test("risk status omitted when unavailable", () => {
  const vm = ApophisTracker.buildViewModel({ ok: true, risk_status_available: false });
  assert.equal(vm.riskStatusAvailable, false);
  assert.match(vm.riskNotice, /not retrieved automatically/i);
});

test("duplicate refresh suppressed in-flight", () => {
  const state = ApophisTracker.createRequestState();
  ApophisTracker.beginRequest(state);
  assert.ok(ApophisTracker.shouldSkipInFlight(state));
});

test("stale refresh ignored", () => {
  const state = ApophisTracker.createRequestState();
  const gen = ApophisTracker.beginRequest(state);
  state.generation += 1;
  assert.ok(ApophisTracker.isStale(state, gen));
});

test("is apophis entry", () => {
  assert.ok(ApophisTracker.isApophisEntry({ featured_kind: "apophis" }));
});

test("non-alarmist fallback wording", () => {
  const vm = ApophisTracker.buildViewModel({});
  assert.match(vm.riskNotice, /Check the official source/i);
});

test("cached view model labels stale data", () => {
  const vm = ApophisTracker.buildViewModel(
    { ok: true, designation: "99942", retrieved_at: "2026-01-01T00:00:00Z" },
    { fromCache: true, cacheRetrievedAt: "2026-01-01T00:00:00Z" }
  );
  assert.equal(vm.fromCache, true);
  assert.equal(vm.cacheRetrievedAt, "2026-01-01T00:00:00Z");
});

test("encounter unavailable when april 2029 missing", () => {
  const vm = ApophisTracker.buildViewModel({ ok: true, encounter_date_unavailable: true });
  assert.equal(vm.encounterDateUnavailable, true);
  assert.equal(vm.encounterDate, null);
});
