"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const { loadApp, fireAndFlush } = require("./app_loader");
const Watchlist = require("../../app/static/lib/watchlist.js");

function moonEntry() {
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
    personal_note: "moon test 1",
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

function makeFetch(doc) {
  const calls = [];
  return {
    calls,
    fetchImpl: async (url, init) => {
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
        return {
          ok: true,
          json: async () => ({
            ok: true,
            document: JSON.parse(init.body).document,
            entry_count: JSON.parse(init.body).document.entries.length,
            storage_path_relative: "runtime_data/tracked_objects.json",
          }),
        };
      }
      return { ok: true, json: async () => ({}) };
    },
  };
}

async function flushLoad() {
  for (let i = 0; i < 6; i++) {
    await new Promise((resolve) => setTimeout(resolve, 0));
  }
}

function detailsText(app) {
  return app.el.trackedObjectDetailsBody.textContent || "";
}

test("Open Apophis without cache leaves prior current target unchanged", async () => {
  const doc = { schema_version: 1, entries: [moonEntry(), apophisEntry()] };
  const { fetchImpl } = makeFetch(doc);
  const { exports: app } = loadApp(fetchImpl);
  await flushLoad();

  app.selectWatchlistEntry("wl_moon");
  assert.equal(app.state.currentTarget.name, "Moon");
  assert.equal(app.state.currentTarget.ra_deg, 331.4842);

  app.selectWatchlistEntry("wl_apophis", { userInitiated: true });

  assert.equal(app.state.currentTarget.name, "Moon");
  assert.equal(app.state.currentTarget.ra_deg, 331.4842);
  assert.equal(app.el.trackedObjectDetailsCard.hidden, false);
  assert.match(detailsText(app), /apophis note saved/);
  assert.match(detailsText(app), /No validated sky position/i);
  assert.equal(app.el.apophisTrackerBody.hidden, false);
});

test("Open Apophis does not trigger ESASky MAST or planetary-image requests", async () => {
  const doc = { schema_version: 1, entries: [apophisEntry()] };
  const { fetchImpl, calls } = makeFetch(doc);
  const { exports: app } = loadApp(fetchImpl);
  await flushLoad();
  calls.length = 0;

  app.state.onlineMode = true;
  app.state.esaskyQueue.loadListenerAttached = true;
  const dispatched = [];
  app.el.esaskyFrame.contentWindow.postMessage = (msg) => dispatched.push(msg);

  app.selectWatchlistEntry("wl_apophis", { userInitiated: true });

  assert.ok(!calls.some((c) => c.url.includes("/api/apophis-tracker")));
  assert.ok(!calls.some((c) => c.url.includes("/api/archive-availability")));
  assert.ok(!calls.some((c) => c.url.includes("/api/planetary-image")));
  assert.equal(dispatched.length, 0);
});

test("placeholder 0,0 is not displayed as valid saved position", async () => {
  const doc = { schema_version: 1, entries: [apophisEntry()] };
  const { fetchImpl } = makeFetch(doc);
  const { exports: app } = loadApp(fetchImpl);
  await flushLoad();

  app.selectWatchlistEntry("wl_apophis");
  assert.doesNotMatch(detailsText(app), /Saved RA.*0\.0000/);
  assert.match(detailsText(app), /No validated sky position/i);
});

test("old-format Apophis 0,0 entry remains loadable", async () => {
  const doc = { schema_version: 1, entries: [apophisEntry()] };
  assert.ok(Watchlist.isFeaturedTrackerPlaceholder(doc.entries[0]));
  const { fetchImpl } = makeFetch(doc);
  const { exports: app } = loadApp(fetchImpl);
  await flushLoad();

  assert.equal(app.state.watchlistDocument.entries.length, 1);
  assert.equal(app.state.watchlistDocument.entries[0].watchlist_id, "wl_apophis");
});

test("cached ephemeris displayed with context but does not auto-navigate", async () => {
  const entry = apophisEntry({
    tracker_cache: {
      kind: "apophis",
      retrieved_at: "2026-01-01T00:00:00Z",
      summary: {
        ok: true,
        designation: "99942",
        retrieved_at: "2026-01-01T00:00:00Z",
        observer_context: { source: "geocentric_fallback", center: "500@399" },
        ephemeris: {
          ok: true,
          ra_deg: 180.123456,
          dec_deg: 45.654321,
          distance_au: 1.23,
          epoch: "2026-Jul-31 12:00",
        },
      },
    },
  });
  const doc = { schema_version: 1, entries: [moonEntry(), entry] };
  const { fetchImpl } = makeFetch(doc);
  const { exports: app } = loadApp(fetchImpl);
  await flushLoad();

  app.selectWatchlistEntry("wl_moon");
  app.selectWatchlistEntry("wl_apophis");

  assert.equal(app.state.currentTarget.name, "Moon");
  assert.match(detailsText(app), /180\.1235/);
  assert.match(detailsText(app), /45\.6543/);
  assert.match(detailsText(app), /2026-Jul-31 12:00/);
  assert.match(detailsText(app), /geocentric_fallback/);

  app.applyApophisEphemerisToTarget(entry);
  assert.equal(app.state.currentTarget.ra_deg, 180.123456);
  assert.match(app.state.currentTarget.source, /apophis_ephemeris/);
});
