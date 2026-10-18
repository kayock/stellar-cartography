"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const CartographyAudio = require("../../app/static/lib/audio_coordinator.js");

function handle() {
  return {
    paused: 0,
    stopped: 0,
    pause() { this.paused += 1; },
    stop() { this.stopped += 1; },
  };
}

test("narration acquire stops prior narration and pauses long-form audio", () => {
  const first = handle();
  const cosmic = handle();
  CartographyAudio.acquire("narration", first);
  CartographyAudio.acquire("cosmic_signal", cosmic);
  const next = handle();
  CartographyAudio.acquire("narration", next);
  assert.equal(first.stopped, 1);
  assert.ok(cosmic.paused + cosmic.stopped >= 1);
  assert.equal(CartographyAudio.current("narration"), next);
});

test("cosmic signal and official media pause narration", () => {
  const narration = handle();
  CartographyAudio.acquire("narration", narration);
  CartographyAudio.acquire("cosmic_signal", handle());
  assert.equal(narration.paused, 1);
  CartographyAudio.acquire("narration", handle());
  const official = handle();
  const current = handle();
  CartographyAudio.acquire("narration", current);
  CartographyAudio.acquire("official_media", official);
  assert.equal(current.paused, 1);
});

test("UI sounds do not stop narration", () => {
  const narration = handle();
  CartographyAudio.acquire("narration", narration);
  CartographyAudio.acquire("ui", handle());
  assert.equal(narration.paused, 0);
  assert.equal(narration.stopped, 0);
});

test("coordinator stays lightweight", () => {
  assert.equal(CartographyAudio.noOverlap, true);
  assert.ok(CartographyAudio.CATEGORIES.includes("narration"));
  assert.ok(CartographyAudio.CATEGORIES.includes("cosmic_signal"));
});

test("data sonification pauses narration and other long-form audio", () => {
  const narration = handle();
  const cosmic = handle();
  CartographyAudio.acquire("narration", narration);
  CartographyAudio.acquire("cosmic_signal", cosmic);
  const sonify = handle();
  CartographyAudio.acquire("data_sonification", sonify);
  assert.ok(narration.paused >= 1);
  assert.ok(cosmic.paused >= 1);
  assert.equal(CartographyAudio.current("data_sonification"), sonify);
});
