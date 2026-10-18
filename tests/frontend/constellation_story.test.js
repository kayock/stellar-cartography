"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const ConstellationStory = require("../../app/static/lib/constellation_story.js");

test("constellation story relation labels stay exact/related/general", () => {
  assert.equal(ConstellationStory.relationLabel("exact"), "Exact");
  assert.equal(ConstellationStory.relationLabel("related"), "Related");
  assert.equal(ConstellationStory.relationLabel("general"), "General");
  assert.equal(ConstellationStory.relationLabel("mystery"), "");
});

test("constellation story module does not create a second signal registry", () => {
  assert.equal(typeof ConstellationStory.onTargetChange, "function");
  assert.equal(typeof ConstellationStory.init, "function");
});

const fs = require("node:fs");
const path = require("node:path");
const html = fs.readFileSync(path.join(__dirname, "..", "..", "app", "static", "index.html"), "utf8");

test("Stories of the Sky culture selector is present", () => {
  assert.match(html, /Stories of the Sky/);
  assert.match(html, /id="story-culture-select"/);
  assert.match(html, />Modern IAU</);
  assert.match(html, />Chinese</);
  assert.match(html, /Arabian Peninsula tradition/);
  assert.match(html, /al-Ṣūfī|al-Sufi|Ṣūfī/);
  assert.match(html, />Māori</);
  assert.match(html, />Ancestral Puebloan</);
  assert.match(html, /Mexica \(historical\)/);
  assert.doesNotMatch(html, />Anasazi</);
  assert.match(html, /id="stellarium-sky-culture"/);
  assert.match(html, /id="story-compare"/);
  assert.match(html, /id="btn-archaeoastronomy"/);
  assert.doesNotMatch(html, /<(audio|video)[^>]*\sautoplay(?!=\"false\")/i);
});
