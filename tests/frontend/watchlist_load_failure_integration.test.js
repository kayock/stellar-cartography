"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const { loadApp, fireAndFlush } = require("./app_loader");

const SAVED_DOC = {
  schema_version: 1,
  entries: [
    {
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
    },
  ],
};

async function flushLoad() {
  for (let i = 0; i < 6; i++) {
    await new Promise((resolve) => setTimeout(resolve, 0));
  }
}

function listText(app) {
  return app.el.watchlistList.textContent || "";
}

test("GET network rejection sets load_failed and shows unavailable state", async () => {
  const { exports: app } = loadApp(async (url) => {
    if (String(url).startsWith("/api/status")) {
      return { ok: true, json: async () => ({ connected: false }) };
    }
    if (String(url) === "/api/watchlist") {
      throw new Error("network down");
    }
    return { ok: true, json: async () => ({}) };
  });
  await flushLoad();

  assert.equal(app.state.watchlistLoadStatus.status, "load_failed");
  assert.match(listText(app), /could not be loaded/i);
  assert.doesNotMatch(listText(app), /No tracked objects yet/i);
  assert.equal(app.el.btnWatchlistAdd.disabled, true);
});

test("GET unreadable JSON sets load_failed", async () => {
  const { exports: app } = loadApp(async (url) => {
    if (String(url).startsWith("/api/status")) {
      return { ok: true, json: async () => ({ connected: false }) };
    }
    if (String(url) === "/api/watchlist") {
      return { ok: true, json: async () => { throw new Error("bad json"); } };
    }
    return { ok: true, json: async () => ({}) };
  });
  await flushLoad();

  assert.equal(app.state.watchlistLoadStatus.status, "load_failed");
  assert.doesNotMatch(listText(app), /No tracked objects yet/i);
});

test("GET ok:false sets load_failed", async () => {
  const { exports: app } = loadApp(async (url) => {
    if (String(url).startsWith("/api/status")) {
      return { ok: true, json: async () => ({ connected: false }) };
    }
    if (String(url) === "/api/watchlist") {
      return {
        ok: true,
        json: async () => ({
          ok: false,
          status: "load_failed",
          document: null,
          entry_count: 0,
          error: "Could not load the watchlist file.",
        }),
      };
    }
    return { ok: true, json: async () => ({}) };
  });
  await flushLoad();

  assert.equal(app.state.watchlistLoadStatus.status, "load_failed");
  assert.doesNotMatch(listText(app), /No tracked objects yet/i);
});

test("authoritative writes blocked after failed initialization", async () => {
  const putCalls = [];
  const { exports: app } = loadApp(async (url, init) => {
    if (String(url).startsWith("/api/status")) {
      return { ok: true, json: async () => ({ connected: false }) };
    }
    if (String(url) === "/api/watchlist" && init && init.method === "PUT") {
      putCalls.push(init.body);
      return { ok: true, json: async () => ({ ok: true, document: { schema_version: 1, entries: [] } }) };
    }
    if (String(url) === "/api/watchlist") {
      throw new Error("network down");
    }
    return { ok: true, json: async () => ({}) };
  });
  await flushLoad();

  app.state.currentTarget = { name: "M31", ra_deg: 10, dec_deg: 41, source: "manual" };
  await fireAndFlush(app.el.btnWatchlistAdd, "click");
  assert.equal(putCalls.length, 0);
  assert.equal(app.watchlistWritesAllowed(), false);
});

test("successful retry restores saved entries without empty PUT", async () => {
  let failLoad = true;
  const putCalls = [];
  const { exports: app } = loadApp(async (url, init) => {
    if (String(url).startsWith("/api/status")) {
      return { ok: true, json: async () => ({ connected: false }) };
    }
    if (String(url) === "/api/watchlist" && init && init.method === "PUT") {
      putCalls.push(JSON.parse(init.body));
      return { ok: true, json: async () => ({ ok: true, document: init.body.document, entry_count: 0 }) };
    }
    if (String(url) === "/api/watchlist") {
      if (failLoad) throw new Error("network down");
      return {
        ok: true,
        json: async () => ({
          ok: true,
          status: "loaded",
          document: SAVED_DOC,
          entry_count: 1,
          storage_path_relative: "runtime_data/tracked_objects.json",
          recovered_from_backup: false,
          error: null,
        }),
      };
    }
    return { ok: true, json: async () => ({}) };
  });
  await flushLoad();
  assert.equal(app.state.watchlistLoadStatus.status, "load_failed");

  failLoad = false;
  const retryBtn = app.el.watchlistList._children.find((c) => c._text === "Retry Load");
  assert.ok(retryBtn);
  await fireAndFlush(retryBtn, "click");

  assert.equal(app.state.watchlistLoadStatus.status, "loaded");
  assert.equal(app.state.watchlistDocument.entries.length, 1);
  assert.equal(app.state.watchlistDocument.entries[0].display_name, "Moon");
  assert.equal(putCalls.length, 0);
  assert.equal(app.el.btnWatchlistAdd.disabled, false);
});
