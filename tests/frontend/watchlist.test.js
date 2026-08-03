"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");
const Watchlist = require("../../app/static/lib/watchlist.js");

test("add current target and duplicate handling", () => {
  let doc = { schema_version: 1, entries: [] };
  const entry = Watchlist.entryFromTarget({ name: "M31", ra_deg: 10, dec_deg: 41, object_type: "galaxy", source: "manual" });
  doc = Watchlist.addEntry(doc, entry);
  assert.equal(doc.entries.length, 1);
  const dup = Watchlist.entryFromTarget({ name: "Andromeda", ra_deg: 10.00001, dec_deg: 41.00001, object_type: "galaxy", source: "manual" });
  doc = Watchlist.addEntry(doc, dup);
  assert.equal(doc.entries.length, 1);
});

test("remove favorite note persistence", () => {
  let doc = { schema_version: 1, entries: [Watchlist.entryFromTarget({ name: "A", ra_deg: 1, dec_deg: 2, source: "manual" })] };
  const id = doc.entries[0].watchlist_id;
  doc = Watchlist.updateEntry(doc, id, { favorite: true, personal_note: "hello" });
  assert.equal(doc.entries[0].personal_note, "hello");
  doc = Watchlist.removeEntry(doc, id);
  assert.equal(doc.entries.length, 0);
});

test("plain-text note sanitization", () => {
  assert.equal(Watchlist.sanitizeNote("a\x00b"), "ab");
});

test("apophis seed entry", () => {
  const entry = Watchlist.buildApophisSeedEntry();
  assert.equal(entry.featured_kind, "apophis");
  assert.equal(entry.provider_identifiers.designation, "99942");
});

test("100 entries remain local-only without network", () => {
  let doc = { schema_version: 1, entries: [] };
  for (let i = 0; i < 100; i++) {
    doc = Watchlist.addEntry(
      doc,
      Watchlist.entryFromTarget({ name: "Star" + i, ra_deg: i, dec_deg: i, object_type: "star", source: "manual" })
    );
  }
  assert.equal(doc.entries.length, 100);
});

test("tracked explainer present", () => {
  assert.match(Watchlist.TRACKED_EXPLAINER, /not continuous background monitoring/i);
});

test("apophis duplicate key uses featured kind not source id", () => {
  const entry = Watchlist.buildApophisSeedEntry();
  assert.equal(Watchlist.duplicateKey(entry), "featured:apophis");
  let doc = { schema_version: 1, entries: [entry] };
  const dup = Watchlist.buildApophisSeedEntry();
  doc = Watchlist.addEntry(doc, dup);
  assert.equal(doc.entries.length, 1);
});

test("hasApophisEntry and findApophisEntry", () => {
  const entry = Watchlist.buildApophisSeedEntry();
  const doc = { schema_version: 1, entries: [entry] };
  assert.ok(Watchlist.hasApophisEntry(doc));
  assert.equal(Watchlist.findApophisEntry(doc).watchlist_id, "wl_apophis");
});

test("multiline note with quotes persists through updateEntry", () => {
  let doc = { schema_version: 1, entries: [Watchlist.entryFromTarget({ name: "A", ra_deg: 1, dec_deg: 2, source: "manual" })] };
  const id = doc.entries[0].watchlist_id;
  const note = 'She said "hello"\nline two';
  doc = Watchlist.updateEntry(doc, id, { personal_note: note });
  assert.equal(doc.entries[0].personal_note, note);
});

test("buildApophisTrackerCache stores summary", () => {
  const summary = { ok: true, designation: "99942", retrieved_at: "2026-01-01T00:00:00Z" };
  const cache = Watchlist.buildApophisTrackerCache(summary, "2026-01-01T00:00:00Z");
  assert.equal(cache.kind, "apophis");
  assert.equal(cache.summary.designation, "99942");
});

test("featured tracker placeholder detection", () => {
  const entry = Watchlist.buildApophisSeedEntry();
  assert.ok(Watchlist.isFeaturedTrackerPlaceholder(entry));
});

test("extractValidatedEphemeris rejects invalid and accepts valid ephemeris", () => {
  const entry = Watchlist.buildApophisSeedEntry();
  assert.equal(Watchlist.extractValidatedEphemeris(entry, null), null);
  const payload = {
    ok: true,
    retrieved_at: "2026-01-01T00:00:00Z",
    ephemeris: { ok: true, ra_deg: 180.1, dec_deg: 45.2, epoch: "2026-Jul-31 12:00" },
  };
  const ephem = Watchlist.extractValidatedEphemeris(entry, payload);
  assert.equal(ephem.ra_deg, 180.1);
  assert.equal(ephem.epoch, "2026-Jul-31 12:00");
});
