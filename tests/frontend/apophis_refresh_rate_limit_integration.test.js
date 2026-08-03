"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const { loadApp, fireAndFlush } = require("./app_loader");
const ApophisTracker = require("../../app/static/lib/apophis_tracker.js");

function apophisDoc() {
  return {
    schema_version: 1,
    entries: [
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
        favorite: false,
        personal_note: "",
        featured_kind: "apophis",
        provider_identifiers: { jpl_sbdb: "99942" },
      },
    ],
  };
}

async function flushLoad() {
  for (let i = 0; i < 6; i++) {
    await new Promise((resolve) => setTimeout(resolve, 0));
  }
}

test("initial manual refresh sends one Apophis request", async () => {
  let apophisCalls = 0;
  const doc = apophisDoc();
  const { exports: app } = loadApp(async (url, init) => {
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
          entry_count: 1,
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
          entry_count: 1,
          storage_path_relative: "runtime_data/tracked_objects.json",
        }),
      };
    }
    if (String(url).startsWith("/api/apophis-tracker")) {
      apophisCalls += 1;
      return {
        ok: true,
        json: async () => ({
          ok: true,
          designation: "99942",
          retrieved_at: "2026-07-31T16:00:00Z",
          risk_status_available: false,
        }),
      };
    }
    return { ok: true, json: async () => ({}) };
  });
  await flushLoad();

  app.selectWatchlistEntry("wl_apophis");
  await fireAndFlush(app.el.btnWatchlistRefresh, "click");

  assert.equal(apophisCalls, 1);
});

test("second click while in flight sends no second request", async () => {
  let apophisCalls = 0;
  let resolveFirst;
  const firstGate = new Promise((resolve) => {
    resolveFirst = resolve;
  });
  const doc = apophisDoc();
  const { exports: app } = loadApp(async (url, init) => {
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
          entry_count: 1,
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
          entry_count: 1,
          storage_path_relative: "runtime_data/tracked_objects.json",
        }),
      };
    }
    if (String(url).startsWith("/api/apophis-tracker")) {
      apophisCalls += 1;
      await firstGate;
      return { ok: true, json: async () => ({ ok: true, designation: "99942", retrieved_at: "2026-07-31T16:00:00Z" }) };
    }
    return { ok: true, json: async () => ({}) };
  });
  await flushLoad();

  app.selectWatchlistEntry("wl_apophis");
  const p1 = fireAndFlush(app.el.btnWatchlistRefresh, "click");
  await new Promise((resolve) => setTimeout(resolve, 0));
  await fireAndFlush(app.el.btnWatchlistRefresh, "click");
  resolveFirst({});
  await p1;

  assert.equal(apophisCalls, 1);
  assert.match(app.el.watchlistStatus.textContent, /in progress/i);
});

test("second click within 60 seconds after completion sends no new request", async () => {
  let apophisCalls = 0;
  const doc = apophisDoc();
  const { exports: app } = loadApp(async (url, init) => {
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
          entry_count: 1,
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
          entry_count: 1,
          storage_path_relative: "runtime_data/tracked_objects.json",
        }),
      };
    }
    if (String(url).startsWith("/api/apophis-tracker")) {
      apophisCalls += 1;
      return { ok: true, json: async () => ({ ok: true, designation: "99942", retrieved_at: "2026-07-31T16:00:00Z" }) };
    }
    return { ok: true, json: async () => ({}) };
  });
  await flushLoad();

  app.selectWatchlistEntry("wl_apophis");
  await fireAndFlush(app.el.btnWatchlistRefresh, "click");
  assert.equal(apophisCalls, 1);

  app.state.apophisRequest.lastFetchedAt = Date.now() - 1000;
  await fireAndFlush(app.el.btnWatchlistRefresh, "click");
  assert.equal(apophisCalls, 1);
  assert.match(app.el.watchlistStatus.textContent, /rate-limited/i);
});

test("click after interval sends a new request", async () => {
  let apophisCalls = 0;
  const doc = apophisDoc();
  const { exports: app } = loadApp(async (url, init) => {
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
          entry_count: 1,
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
          entry_count: 1,
          storage_path_relative: "runtime_data/tracked_objects.json",
        }),
      };
    }
    if (String(url).startsWith("/api/apophis-tracker")) {
      apophisCalls += 1;
      return { ok: true, json: async () => ({ ok: true, designation: "99942", retrieved_at: "2026-07-31T16:00:00Z" }) };
    }
    return { ok: true, json: async () => ({}) };
  });
  await flushLoad();

  app.selectWatchlistEntry("wl_apophis");
  await fireAndFlush(app.el.btnWatchlistRefresh, "click");
  app.state.apophisRequest.lastFetchedAt = Date.now() - ApophisTracker.MIN_REFRESH_INTERVAL_MS - 1000;
  await fireAndFlush(app.el.btnWatchlistRefresh, "click");

  assert.equal(apophisCalls, 2);
});

test("buildRateLimitMessage reports seconds until retry", () => {
  const state = ApophisTracker.createRequestState();
  state.lastFetchedAt = Date.now() - 1000;
  const msg = ApophisTracker.buildRateLimitMessage(state, Date.now());
  assert.match(msg, /rate-limited/i);
  assert.match(msg, /second/);
});
