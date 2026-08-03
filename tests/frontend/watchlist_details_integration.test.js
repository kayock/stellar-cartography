"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const { loadApp, fireAndFlush } = require("./app_loader");

function moonEntry(note) {
  return {
    watchlist_id: "wl_moon",
    display_name: "Moon",
    normalized_object_type: "moon",
    source_identifier: "Moon",
    saved_ra_deg: 331.4842,
    saved_dec_deg: -11.9771,
    coordinate_source: "Stellarium selection",
    date_added: "2026-07-31T13:11:24.172Z",
    last_refreshed: null,
    favorite: true,
    personal_note: note || "moon test 1",
    featured_kind: null,
    provider_identifiers: {},
  };
}

function saturnEntry() {
  return {
    watchlist_id: "wl_saturn",
    display_name: "Saturn",
    normalized_object_type: "planet",
    source_identifier: "Saturn",
    saved_ra_deg: 22.5,
    saved_dec_deg: -12.3,
    coordinate_source: "Stellarium selection",
    date_added: "2026-07-31T14:00:00.000Z",
    last_refreshed: "2026-07-31T15:00:00.000Z",
    favorite: false,
    personal_note: "ring watch",
    featured_kind: null,
    provider_identifiers: {},
  };
}

function apophisEntry(overrides) {
  return Object.assign(
    {
      watchlist_id: "wl_apophis",
      display_name: "99942 Apophis",
      normalized_object_type: "asteroid",
      source_identifier: "2004 MN4",
      saved_ra_deg: 0,
      saved_dec_deg: 0,
      coordinate_source: "featured_tracker",
      date_added: "2026-07-31T13:02:54.410Z",
      last_refreshed: null,
      favorite: true,
      personal_note: "apophis note saved",
      featured_kind: "apophis",
      provider_identifiers: { jpl_sbdb: "99942", designation: "99942", name: "Apophis" },
      tracker_cache: null,
    },
    overrides || {}
  );
}

function makeWatchlistFetch(initialDoc, options) {
  options = options || {};
  let doc = JSON.parse(JSON.stringify(initialDoc));
  const calls = [];
  return {
    calls,
    fetchImpl: async function fetchImpl(url, init) {
      calls.push({ url: String(url), method: init && init.method });
      if (String(url).startsWith("/api/status")) {
        return { ok: true, json: async () => ({ connected: false }) };
      }
      if (String(url) === "/api/watchlist" && (!init || init.method !== "PUT")) {
        return {
          ok: true,
          json: async () => ({
            ok: true,
            status: "loaded",
            document: doc,
            entry_count: doc.entries.length,
            storage_path_relative: "runtime_data/tracked_objects.json",
            recovered_from_backup: false,
            error: null,
          }),
        };
      }
      if (String(url) === "/api/watchlist" && init && init.method === "PUT") {
        if (options.failPut) {
          return { ok: false, json: async () => ({ ok: false, error: "save rejected" }) };
        }
        const body = JSON.parse(init.body);
        doc = body.document;
        return {
          ok: true,
          json: async () => ({
            ok: true,
            document: doc,
            entry_count: doc.entries.length,
            storage_path_relative: "runtime_data/tracked_objects.json",
          }),
        };
      }
      if (String(url).startsWith("/api/apophis-tracker")) {
        return {
          ok: true,
          json: async () => ({
            ok: true,
            designation: "99942",
            name: "99942 Apophis",
            encounter_date: "2029-Apr-13 00:00",
            retrieved_at: "2026-07-31T16:00:00Z",
            risk_status_available: false,
          }),
        };
      }
      return { ok: true, json: async () => ({}) };
    },
  };
}

async function flushWatchlistLoad() {
  for (let i = 0; i < 6; i++) {
    await new Promise((resolve) => setTimeout(resolve, 0));
  }
}

function detailsText(app) {
  return app.el.trackedObjectDetailsBody.textContent || "";
}

function findRowByTitle(app, title) {
  for (const row of app.el.watchlistList._children || []) {
    if ((row.textContent || "").includes(title)) return row;
  }
  return null;
}

function findInTree(node, predicate) {
  if (!node) return null;
  if (predicate(node)) return node;
  for (const child of node._children || []) {
    const found = findInTree(child, predicate);
    if (found) return found;
  }
  return null;
}

function findButtonInRow(row, label) {
  return findInTree(row, (n) => n.tagName === "BUTTON" && n._text === label);
}

function findTextareaInRow(row) {
  return findInTree(row, (n) => n.tagName === "TEXTAREA");
}

test("Open Moon renders saved note, favorite, coordinates, and date added", async () => {
  const doc = { schema_version: 1, entries: [moonEntry(), saturnEntry()] };
  const { fetchImpl } = makeWatchlistFetch(doc);
  const { exports: app } = loadApp(fetchImpl);
  await flushWatchlistLoad();

  app.selectWatchlistEntry("wl_moon", { userInitiated: true });

  assert.equal(app.el.trackedObjectDetailsCard.hidden, false);
  assert.match(app.el.trackedObjectDetailsHeading.textContent, /Moon/);
  assert.match(detailsText(app), /moon test 1/);
  assert.match(detailsText(app), /Favorite.*Yes/);
  assert.match(detailsText(app), /331\.4842/);
  assert.match(detailsText(app), /2026-07-31T13:11:24/);
  assert.match(detailsText(app), /saved snapshot/i);
  assert.equal(app.state.currentTarget.name, "Moon");
});

test("Open Saturn renders Saturn details and not Moon details", async () => {
  const doc = { schema_version: 1, entries: [moonEntry(), saturnEntry()] };
  const { fetchImpl } = makeWatchlistFetch(doc);
  const { exports: app } = loadApp(fetchImpl);
  await flushWatchlistLoad();

  app.selectWatchlistEntry("wl_saturn", { userInitiated: true });

  assert.match(detailsText(app), /ring watch/);
  assert.match(detailsText(app), /Saturn/);
  assert.doesNotMatch(detailsText(app), /moon test 1/);
  assert.match(detailsText(app), /22\.5000/);
});

test("Save a new Moon note while Moon is open updates details immediately after success", async () => {
  const doc = { schema_version: 1, entries: [moonEntry("original note")] };
  const { fetchImpl } = makeWatchlistFetch(doc);
  const { exports: app } = loadApp(fetchImpl);
  await flushWatchlistLoad();

  app.selectWatchlistEntry("wl_moon");
  const row = findRowByTitle(app, "Moon");
  const textarea = findTextareaInRow(row);
  const saveBtn = findButtonInRow(row, "Save Note");
  textarea.value = "updated moon note";
  await fireAndFlush(saveBtn, "click");

  assert.match(detailsText(app), /updated moon note/);
  assert.doesNotMatch(detailsText(app), /Unsaved draft/);
});

test("Failed note save retains the previous saved note in details", async () => {
  const doc = { schema_version: 1, entries: [moonEntry("kept note")] };
  const { fetchImpl } = makeWatchlistFetch(doc, { failPut: true });
  const { exports: app } = loadApp(fetchImpl);
  await flushWatchlistLoad();

  app.selectWatchlistEntry("wl_moon");
  const row = findRowByTitle(app, "Moon");
  const textarea = findTextareaInRow(row);
  const saveBtn = findButtonInRow(row, "Save Note");
  textarea.value = "would have saved";
  await fireAndFlush(saveBtn, "click");

  assert.match(detailsText(app), /kept note/);
  assert.match(detailsText(app), /Save failed/);
  assert.doesNotMatch(detailsText(app), /would have saved/);
});

test("Reload persisted document, open Moon, and display its saved note", async () => {
  const doc = { schema_version: 1, entries: [moonEntry("persisted after reload")] };
  const { fetchImpl } = makeWatchlistFetch(doc);
  const { exports: app } = loadApp(fetchImpl);
  await flushWatchlistLoad();

  app.selectWatchlistEntry("wl_moon");
  assert.match(detailsText(app), /persisted after reload/);
});

test("Open Apophis displays saved personal note plus JPL tracker information", async () => {
  const entry = apophisEntry({
    tracker_cache: {
      kind: "apophis",
      retrieved_at: "2026-01-01T00:00:00Z",
      summary: {
        ok: true,
        designation: "99942",
        name: "99942 Apophis",
        encounter_date: "2029-Apr-13 00:00",
        retrieved_at: "2026-01-01T00:00:00Z",
        risk_status_available: false,
      },
    },
  });
  const doc = { schema_version: 1, entries: [entry] };
  const { fetchImpl } = makeWatchlistFetch(doc);
  const { exports: app } = loadApp(fetchImpl);
  await flushWatchlistLoad();

  app.selectWatchlistEntry("wl_apophis", { userInitiated: true });

  assert.match(detailsText(app), /apophis note saved/);
  assert.match(detailsText(app), /Cached summary from 2026-01-01T00:00:00Z/);
  assert.equal(app.el.apophisTrackerBody.hidden, false);
  assert.match(app.el.apophisTrackerBody.textContent, /JPL Apophis Tracker/);
  assert.match(app.el.apophisTrackerBody.textContent, /99942/);
});

test("Apophis with no tracker cache still displays note and common details", async () => {
  const doc = { schema_version: 1, entries: [apophisEntry({ tracker_cache: null })] };
  const { fetchImpl } = makeWatchlistFetch(doc);
  const { exports: app } = loadApp(fetchImpl);
  await flushWatchlistLoad();

  app.selectWatchlistEntry("wl_apophis");

  assert.match(detailsText(app), /apophis note saved/);
  assert.match(detailsText(app), /No cached tracker data yet/);
  assert.equal(app.el.apophisTrackerBody.hidden, false);
});

test("Open Apophis does not add a duplicate", async () => {
  const doc = { schema_version: 1, entries: [apophisEntry()] };
  const { fetchImpl } = makeWatchlistFetch(doc);
  const { exports: app } = loadApp(fetchImpl);
  await flushWatchlistLoad();

  await fireAndFlush(app.el.btnApophisAdd, "click");
  assert.equal(app.state.watchlistDocument.entries.length, 1);
  await fireAndFlush(app.el.btnApophisAdd, "click");
  assert.equal(app.state.watchlistDocument.entries.length, 1);
});

test("Switching Apophis to Moon removes Apophis-specific content", async () => {
  const doc = { schema_version: 1, entries: [apophisEntry(), moonEntry()] };
  const { fetchImpl } = makeWatchlistFetch(doc);
  const { exports: app } = loadApp(fetchImpl);
  await flushWatchlistLoad();

  app.selectWatchlistEntry("wl_apophis");
  assert.match(app.el.apophisTrackerBody.textContent, /JPL Apophis Tracker/);

  app.selectWatchlistEntry("wl_moon");
  assert.equal(app.el.apophisTrackerBody.hidden, true);
  assert.match(detailsText(app), /moon test 1/);
  assert.doesNotMatch(app.el.apophisTrackerBody.textContent || "", /JPL Apophis Tracker/);
});

test("Removing the selected entry clears the details panel", async () => {
  const doc = { schema_version: 1, entries: [moonEntry()] };
  const { fetchImpl } = makeWatchlistFetch(doc);
  const { exports: app } = loadApp(fetchImpl);
  await flushWatchlistLoad();

  app.selectWatchlistEntry("wl_moon");
  assert.equal(app.el.trackedObjectDetailsCard.hidden, false);

  const row = findRowByTitle(app, "Moon");
  const removeBtn = findButtonInRow(row, "Remove");
  await fireAndFlush(removeBtn, "click");

  assert.equal(app.el.trackedObjectDetailsCard.hidden, true);
  assert.equal(app.state.selectedWatchlistId, null);
});

test("Notes with quotes, punctuation, and multiline text remain plain text", async () => {
  const note = 'She said "hello"\nline two — watch!';
  const doc = { schema_version: 1, entries: [moonEntry(note)] };
  const { fetchImpl } = makeWatchlistFetch(doc);
  const { exports: app } = loadApp(fetchImpl);
  await flushWatchlistLoad();

  app.selectWatchlistEntry("wl_moon");
  assert.match(detailsText(app), /She said "hello"/);
  assert.match(detailsText(app), /line two — watch!/);
  assert.doesNotMatch(app.el.trackedObjectDetailsBody._innerHTML || "", /<script/i);
});

test("Opening entries causes no automatic external network calls", async () => {
  const doc = { schema_version: 1, entries: [moonEntry(), apophisEntry()] };
  const { fetchImpl, calls } = makeWatchlistFetch(doc);
  const { exports: app } = loadApp(fetchImpl);
  await flushWatchlistLoad();
  calls.length = 0;

  app.selectWatchlistEntry("wl_moon", { userInitiated: true });
  app.selectWatchlistEntry("wl_apophis", { userInitiated: true });

  assert.ok(!calls.some((c) => c.url.includes("/api/apophis-tracker")));
  assert.ok(!calls.some((c) => c.url.includes("jpl.nasa.gov")));
});

test("unsaved draft is distinguished from saved note in details", async () => {
  const doc = { schema_version: 1, entries: [moonEntry("saved baseline")] };
  const { fetchImpl } = makeWatchlistFetch(doc);
  const { exports: app } = loadApp(fetchImpl);
  await flushWatchlistLoad();

  app.selectWatchlistEntry("wl_moon");
  const row = findRowByTitle(app, "Moon");
  const textarea = findTextareaInRow(row);
  textarea.value = "draft only";
  textarea.dispatchEvent({ type: "input" });

  assert.match(detailsText(app), /saved baseline/);
  assert.match(detailsText(app), /Unsaved draft/);
  assert.match(detailsText(app), /draft only/);
});
