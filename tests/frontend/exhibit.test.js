"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const CartographyExhibit = require("../../app/static/lib/exhibit.js");
const ExhibitModel = require("../../app/static/lib/exhibit_model.js");
const CartographyNarration = require("../../app/static/lib/narration_tts.js");

const html = fs.readFileSync(path.join(__dirname, "..", "..", "app", "static", "index.html"), "utf8");

test("Exhibits entry and Southwestern Skies controls are present", () => {
  assert.match(html, />Exhibits</);
  assert.match(html, /id="exhibit-card"/);
  assert.match(html, /id="exhibit-list"/);
  assert.match(html, /id="exhibit-overview"/);
  assert.match(html, /id="exhibit-player"/);
  assert.match(html, /id="btn-exhibit-start"/);
  assert.match(html, />Start Exhibit</);
  assert.match(html, /id="btn-exhibit-prev"/);
  assert.match(html, /id="btn-exhibit-next"/);
  assert.match(html, />Pause Narration</);
  assert.match(html, />Stop Exhibit</);
  assert.match(html, />Exit and Restore</);
  assert.match(html, />Apply Historical Sky</);
  assert.match(html, /Sources for this Exhibit/);
  assert.match(html, /id="exhibit-auto-advance"/);
  assert.match(html, /static\/lib\/exhibit_model\.js/);
  assert.match(html, /static\/lib\/exhibit\.js/);
});

test("exhibit does not autoplay before start and auto-advance is off", () => {
  assert.equal(CartographyExhibit.noAutoplay, true);
  assert.equal(CartographyExhibit.started(), false);
  assert.equal(CartographyExhibit.autoAdvanceEnabled(), false);
  assert.equal(ExhibitModel.defaultAutoAdvance, false);
  assert.doesNotMatch(html, /id="exhibit-auto-advance"[^>]*checked/);
  assert.doesNotMatch(html, /<(audio|video)[^>]*\sautoplay(?!=\"false\")/i);
  assert.match(html, /Narration stays silent until Start Exhibit/);
});

test("exhibit player reuses existing narration and media systems", () => {
  assert.equal(typeof CartographyExhibit.startExhibit, "function");
  assert.equal(typeof CartographyExhibit.stopExhibit, "function");
  assert.equal(typeof CartographyNarration.speakExhibit, "function");
  assert.equal(CartographyNarration.isPlaying(), false);
  assert.match(html, /Official media remain manual|official media remain manual/);
  assert.match(html, /id="cosmic-signal-play"/);
  assert.match(html, /id="official-media-search-card"/);
});

test("historical reconstruction confirmation is explicit", () => {
  assert.match(html, /id="btn-exhibit-apply-historical"/);
  assert.match(html, /hidden/);
  const copy = ExhibitModel.historicalConfirmationCopy(1050);
  assert.match(copy.prompt, /AD 1050/);
  assert.match(copy.explanation, /not direct archaeological evidence/i);
});

test("resume prompt helper is available", () => {
  assert.equal(
    ExhibitModel.resumePrompt("Southwestern Skies", 2),
    "Resume Southwestern Skies at Step 3?"
  );
});

const exhibitJs = fs.readFileSync(path.join(__dirname, "..", "..", "app", "static", "lib", "exhibit.js"), "utf8");
const experienceUi = fs.readFileSync(path.join(__dirname, "..", "..", "app", "static", "lib", "experience_ui.js"), "utf8");

test("Hear the Universe exhibit UI stays manual and classifies audio", () => {
  assert.match(exhibitJs, /What Am I Hearing\?/);
  assert.match(exhibitJs, /Listen to the Universe/);
  assert.match(exhibitJs, /Open in Cosmic Signal Deck/);
  assert.match(exhibitJs, /Play Data Sonification/);
  assert.match(exhibitJs, /Can space make sound\?/);
  assert.match(exhibitJs, /Cartography is generating this Data Sonification/);
  assert.match(exhibitJs, /Official Media remains manual/);
  assert.doesNotMatch(exhibitJs, /autoplay\s*=\s*true/);
  assert.equal(CartographyExhibit.noAutoplay, true);
  assert.equal(ExhibitModel.mediaRemainsManual({ media: { autoplay: false } }), true);
});

test("exhibit play and stop hooks reuse Cosmic Signal Deck and Data Sonification", () => {
  assert.match(exhibitJs, /data-exhibit-cs-play/);
  assert.match(exhibitJs, /data-exhibit-cs-stop/);
  assert.match(exhibitJs, /CartographyDeck\.play/);
  assert.match(exhibitJs, /CartographyDeck\.stop/);
  assert.match(exhibitJs, /ExperienceLayer\.playSonify/);
  assert.match(exhibitJs, /ExperienceLayer\.stopSonify/);
  assert.match(experienceUi, /playSonify:\s*playSonify/);
  assert.match(experienceUi, /stopSonify:\s*stopSonify/);
});

test("resume stores hear the universe exhibit id", () => {
  const raw = ExhibitModel.serializeResume({
    exhibit_id: "hear_the_universe",
    last_completed_step: 4,
    provider: "kayock_voice",
    voice: "default",
    auto_advance: false,
  });
  const parsed = ExhibitModel.parseResume(raw);
  assert.equal(parsed.exhibit_id, "hear_the_universe");
  assert.equal(parsed.last_completed_step, 4);
  assert.equal(parsed.provider, "kayock_voice");
  assert.equal(parsed.auto_advance, false);
  assert.equal(ExhibitModel.resumePrompt("Hear the Universe", 4), "Resume Hear the Universe at Step 5?");
});

test("Ancient Skywatchers UI reuses teaching cards and stays manual", () => {
  assert.match(exhibitJs, /How Did They Know\?/);
  assert.match(exhibitJs, /Tools of the Sky/);
  assert.match(exhibitJs, /SCIENTIFIC VIEW/);
  assert.match(exhibitJs, /comparison_title/);
  assert.match(exhibitJs, /renderHowTheyKnew/);
  assert.match(html, /id="btn-exhibit-apply-historical"/);
  assert.equal(CartographyExhibit.noAutoplay, true);
  assert.equal(ExhibitModel.mediaRemainsManual({ media: { autoplay: false } }), true);
  const raw = ExhibitModel.serializeResume({
    exhibit_id: "ancient_skywatchers",
    last_completed_step: 6,
    provider: "father_fox",
    voice: "am_adam",
    auto_advance: false,
  });
  const parsed = ExhibitModel.parseResume(raw);
  assert.equal(parsed.exhibit_id, "ancient_skywatchers");
  assert.equal(parsed.last_completed_step, 6);
  assert.equal(ExhibitModel.resumePrompt("Ancient Skywatchers", 6), "Resume Ancient Skywatchers at Step 7?");
});
