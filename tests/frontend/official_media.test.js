"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const OfficialMedia = require("../../app/static/lib/official_media.js");

test("official media relation labels", () => {
  assert.equal(OfficialMedia.relationLabel("exact"), "Exact");
  assert.equal(OfficialMedia.relationLabel("related"), "Related");
  assert.equal(OfficialMedia.relationLabel("general"), "General");
});

test("sonification is not labeled as a microphone recording", () => {
  const label = OfficialMedia.signalLabel("sonification");
  assert.match(label, /not a microphone recording/i);
});

test("player markup never autoplays", () => {
  const html = OfficialMedia.playerHtml({
    playable_inline: true,
    reuse_cosmic_signal: false,
    media_type: "video",
    media_url: "https://images-assets.nasa.gov/video/x/x~orig.mp4",
    thumbnail_url: "https://images-assets.nasa.gov/video/x/x~thumb.jpg",
    caption_url: "https://images-assets.nasa.gov/video/x/x.vtt",
  });
  assert.match(html, /preload="metadata"/);
  assert.match(html, /data-autoplay="false"/);
  assert.doesNotMatch(html, /autoplay(?!=\"false\")/);
});

test("cosmic signal reuse does not emit a second player", () => {
  const html = OfficialMedia.playerHtml({
    playable_inline: false,
    reuse_cosmic_signal: true,
    media_type: "sonification",
    media_url: "https://www.chandra.si.edu/sound/sounds/casa_all.mp4",
  });
  assert.equal(html, "");
});

test("module does not create a second signal registry", () => {
  assert.equal(OfficialMedia.noAutoplay, true);
  assert.equal(typeof OfficialMedia.onTargetChange, "function");
});
