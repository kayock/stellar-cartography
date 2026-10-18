"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const ArchaeoastronomyView = require("../../app/static/lib/archaeoastronomy.js");

const html = fs.readFileSync(path.join(__dirname, "..", "..", "app", "static", "index.html"), "utf8");

test("View Archaeoastronomy control is present and hidden by default", () => {
  assert.match(html, /id="btn-archaeoastronomy"/);
  assert.match(html, /View Archaeoastronomy/);
  assert.match(html, /id="archaeoastronomy-panel"/);
  assert.match(html, /hidden/);
  assert.match(html, /static\/lib\/archaeoastronomy\.js/);
});

test("primary badges exclude disputed and speculative", () => {
  assert.equal(ArchaeoastronomyView.badgeLabel("strong_evidence"), "STRONG EVIDENCE");
  assert.equal(ArchaeoastronomyView.badgeLabel("scholarly_interpretation"), "SCHOLARLY INTERPRETATION");
  assert.equal(ArchaeoastronomyView.badgeLabel("disputed"), "DISPUTED");
  assert.equal(ArchaeoastronomyView.badgeLabel("speculative"), "SPECULATIVE");
  assert.equal(ArchaeoastronomyView.primaryBadgeAllowed("strong_evidence"), true);
  assert.equal(ArchaeoastronomyView.primaryBadgeAllowed("scholarly_interpretation"), true);
  assert.equal(ArchaeoastronomyView.primaryBadgeAllowed("disputed"), false);
  assert.equal(ArchaeoastronomyView.primaryBadgeAllowed("speculative"), false);
});

test("visual mode is eligible only for archaeo story types", () => {
  assert.equal(ArchaeoastronomyView.isEligible({ story_type: "archaeoastronomy" }), true);
  assert.equal(ArchaeoastronomyView.isEligible({ story_type: "horizon_calendar" }), true);
  assert.equal(ArchaeoastronomyView.isEligible({ story_type: "solar_lunar_alignment" }), true);
  assert.equal(ArchaeoastronomyView.isEligible({ story_type: "calendrical_astronomy" }), false);
  assert.equal(ArchaeoastronomyView.isEligible({ story_type: "xingguan" }), false);
  assert.equal(ArchaeoastronomyView.isEligible({ archaeoastronomy_eligible: true }), true);
});

test("opening the panel never silently applies Stellarium time", () => {
  assert.equal(ArchaeoastronomyView.appliesTimeSilently(), false);
  assert.equal(typeof ArchaeoastronomyView.openVisual, "function");
});
