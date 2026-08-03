"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");

const OnlineMode = require(path.join(__dirname, "..", "..", "app", "static", "lib", "online_mode.js"));

test("online-mode shutdown clears iframe state, pending requests, and active styling", () => {
  const state = {
    onlineMode: true,
    pendingHipsRequest: { buttonId: "hubble", timeoutId: 42 },
    pendingChangeRequest: { requestedName: "HST ACS", timeoutId: 43 },
    activeImageryButtonId: "hubble",
  };

  const next = OnlineMode.buildShutdownState(state);

  assert.equal(next.onlineMode, false);
  assert.equal(next.pendingHipsRequest, null);
  assert.equal(next.pendingChangeRequest, null);
  assert.equal(next.activeImageryButtonId, null);
  assert.equal(next.iframeSrc, "about:blank");
  assert.equal(next.iframeHidden, true);
  assert.equal(next.esaskyQueueResetListenerFlag, true);
  assert.deepEqual(next.timeoutIdsToClear.sort(), [42, 43]);
});

test("shutdown with nothing pending still fully resets and clears no timers", () => {
  const state = { onlineMode: true, pendingHipsRequest: null, pendingChangeRequest: null, activeImageryButtonId: null };
  const next = OnlineMode.buildShutdownState(state);
  assert.deepEqual(next.timeoutIdsToClear, []);
  assert.equal(next.iframeHidden, true);
});
