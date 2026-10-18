"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const ExperienceModel = require("../../app/static/lib/experience_model.js");

test("time machine form requires an explicit apply", () => {
  const result = ExperienceModel.validateTimeMachineForm({});
  assert.equal(result.ok, false);
});

test("time machine form validates latitude", () => {
  const result = ExperienceModel.validateTimeMachineForm({
    apply_location: true,
    latitude: 120,
    longitude: 0,
  });
  assert.equal(result.ok, false);
});

test("time machine form accepts explicit UTC apply", () => {
  const result = ExperienceModel.validateTimeMachineForm({
    apply_time: true,
    utc: "2020-01-01T00:00:00Z",
  });
  assert.equal(result.ok, true);
});

test("postcard filename stays local and filesystem-safe", () => {
  const name = ExperienceModel.postcardFilename({
    selection: { name: "Crab Nebula" },
    sky: { utc: "2026-01-01T00:00:00Z" },
  });
  assert.match(name, /^sky-postcard-Crab_Nebula-/);
  assert.match(name, /\.json$/);
});

test("motion polyline is empty without points", () => {
  const poly = ExperienceModel.motionPolyline([]);
  assert.equal(poly.d, "");
});

test("motion polyline draws a path", () => {
  const poly = ExperienceModel.motionPolyline([
    { altitude_deg: -10 },
    { altitude_deg: 0 },
    { altitude_deg: 15 },
  ]);
  assert.match(poly.d, /^M /);
});

test("ui sounds default off", () => {
  const prefs = ExperienceModel.defaultAudioPrefs();
  assert.equal(prefs.uiSounds, false);
  const parsed = ExperienceModel.parseAudioPrefs(null);
  assert.equal(parsed.uiSounds, false);
});

test("compare changed count", () => {
  assert.equal(ExperienceModel.compareChangedCount([{ changed: true }, { changed: false }]), 1);
});

test("sonify frequencies pass through", () => {
  const freqs = ExperienceModel.sonifyFrequencies([{ t: 0, frequency_hz: 220, value: 0 }]);
  assert.equal(freqs[0].frequency_hz, 220);
});
