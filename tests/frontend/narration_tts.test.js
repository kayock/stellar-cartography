"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const CartographyNarration = require("../../app/static/lib/narration_tts.js");

const html = fs.readFileSync(
  path.join(__dirname, "..", "..", "app", "static", "index.html"),
  "utf8"
);

test("Tell Me the Story and narrated tour controls exist", () => {
  assert.match(html, /id="btn-tell-story"/);
  assert.match(html, />Tell Me the Story</);
  assert.match(html, /id="btn-narrated-tour"/);
  assert.match(html, />Start Narrated Tour</);
  assert.match(html, /id="btn-narration-pause"/);
  assert.match(html, /id="btn-narration-resume"/);
  assert.match(html, /id="btn-narration-stop"/);
  assert.match(html, /id="tts-provider"/);
  assert.match(html, />Father Fox</);
  assert.match(html, />Kayock Voice</);
});

test("narration never autoplays and auto-advance is off by default", () => {
  assert.equal(CartographyNarration.noAutoplay, true);
  assert.equal(CartographyNarration.defaultAutoAdvance, false);
  assert.match(html, /id="tts-audio"[^>]*preload="none"/);
  assert.match(html, /data-autoplay="false"/);
  assert.match(html, /id="tts-auto-advance" type="checkbox"/);
  assert.doesNotMatch(html, /id="tts-auto-advance"[^>]*checked/);
  assert.doesNotMatch(html, /<audio[^>]*autoplay(?!=\"false\")/);
});

test("label is Cartography/Local narration, not NASA", () => {
  assert.equal(CartographyNarration.LABEL, "Cartography Narration");
  assert.match(html, /Cartography Narration/);
  assert.match(html, /LOCAL/);
  assert.doesNotMatch(html, /NASA Narration/);
  assert.doesNotMatch(html, /Chandra Narration/);
  assert.match(html, /not NASA or Chandra narration/);
});

test("story text remains visible and controls are labeled", () => {
  assert.match(html, /id="narration-script"/);
  assert.match(html, /id="constellation-story-body"/);
  assert.match(html, /aria-label="Narration voice provider"/);
  assert.match(html, /aria-label="Narration volume"/);
  assert.match(html, /role="status"/);
});

test("Cosmic Signal and Official Media remain manual", () => {
  assert.match(html, /Listen to the Universe|Cosmic Signal/);
  assert.match(html, /id="constellation-official-media"/);
  assert.doesNotMatch(html, /<(audio|video)[^>]*\sautoplay(?!=\"false\")/i);
});

test("module exposes tour and playback hooks without starting audio", () => {
  assert.equal(typeof CartographyNarration.tellStory, "function");
  assert.equal(typeof CartographyNarration.startNarratedTour, "function");
  assert.equal(typeof CartographyNarration.stopNarration, "function");
  assert.equal(CartographyNarration.isPlaying(), false);
  assert.equal(CartographyNarration.isNarratedTour(), false);
  assert.equal(CartographyNarration.autoAdvanceEnabled(), false);
});

test("manual next speaks the next tour step and does not overlap by default", () => {
  assert.equal(
    CartographyNarration.nextNarrationAction({ narratedTour: true, action: "step" }),
    "speak_tour_step"
  );
  assert.equal(
    CartographyNarration.nextNarrationAction({
      narratedTour: true,
      ended: true,
      autoAdvance: false,
    }),
    "wait"
  );
});

test("automatic advance waits for audio completion when enabled", () => {
  assert.equal(
    CartographyNarration.nextNarrationAction({
      narratedTour: true,
      ended: false,
      autoAdvance: true,
    }),
    "wait"
  );
  assert.equal(
    CartographyNarration.nextNarrationAction({
      narratedTour: true,
      ended: true,
      autoAdvance: true,
    }),
    "advance"
  );
});

test("stop restores normal tour behavior", () => {
  assert.equal(
    CartographyNarration.nextNarrationAction({ action: "stop", narratedTour: true }),
    "restore_tour"
  );
  assert.equal(
    CartographyNarration.nextNarrationAction({ narratedTour: false, ended: true, autoAdvance: true }),
    "idle"
  );
});

test("provider unavailable copy stays on the written story", () => {
  assert.match(html, /id="tts-provider-status"/);
  assert.match(html, /written story|story text remains readable|not NASA or Chandra narration/i);
});
