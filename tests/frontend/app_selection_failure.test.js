"use strict";

/* app_selection_failure.test.js
 *
 * Browser-DOM integration test for repair request item 2: a
 * /api/selection request that throws (network error, or resp.json()
 * throwing on unparseable JSON) -- not just an {ok:false} response -- must
 * clear the stale prior target exactly like the ok:false branch does.
 * Runs the real app.js "Use Stellarium Selection" click handler via the
 * Node vm harness in app_loader.js.
 */

const test = require("node:test");
const assert = require("node:assert/strict");

const { loadApp, fireAndFlush } = require("./app_loader");

const TARGET_A = {
  ok: true,
  connected: true,
  name: "M 31",
  ra_deg: 10.6847,
  dec_deg: 41.26875,
  fov_deg: 3.5,
  ra_sexagesimal: null,
  dec_sexagesimal: null,
};

test("a failed selection request (fetch/JSON exception) clears the stale target", async () => {
  let selectionCall = 0;
  const fetchImpl = async (url) => {
    if (String(url).startsWith("/api/selection")) {
      selectionCall += 1;
      if (selectionCall === 1) {
        return { ok: true, json: async () => TARGET_A };
      }
      // Second call: simulate a network failure (fetch rejects).
      throw new TypeError("network error");
    }
    return { ok: true, json: async () => ({ connected: true }) };
  };

  const { exports: app } = loadApp(fetchImpl);

  // Selection A succeeds first.
  await fireAndFlush(app.el.btnRefreshSelection, "click");
  assert.equal(app.state.currentTarget.name, "M 31");
  assert.equal(app.el.btnOpenEsasky.disabled, false);

  // The next /api/selection request rejects.
  await fireAndFlush(app.el.btnRefreshSelection, "click");

  assert.equal(app.state.currentTarget, null, "currentTarget must be cleared, not left as A");
  assert.equal(app.el.aboutObjectCard.hidden, true, "About This Object must be hidden");
  assert.equal(app.el.btnOpenEsasky.disabled, true, "Open in ESASky must be disabled");
  assert.match(
    app.el.targetCard.innerHTML,
    /Could not reach the local bridge server/,
    "the error message must be shown"
  );
  assert.equal(app.el.targetCard.className, "target-card target-card-empty");
});

test("a failed selection request also cancels a pending imagery request for the stale target", async () => {
  let selectionCall = 0;
  const fetchImpl = async (url) => {
    if (String(url).startsWith("/api/selection")) {
      selectionCall += 1;
      if (selectionCall === 1) return { ok: true, json: async () => TARGET_A };
      throw new TypeError("network error");
    }
    return { ok: true, json: async () => ({ connected: true }) };
  };
  const { exports: app } = loadApp(fetchImpl);

  await fireAndFlush(app.el.btnRefreshSelection, "click");

  // Simulate a pending imagery request left over from target A (as if the
  // user had clicked an imagery button while A was current).
  const fakeTimeoutId = setTimeout(() => {}, 60000);
  app.state.pendingHipsRequest = { buttonId: "optical", timeoutId: fakeTimeoutId };
  app.state.activeImageryButtonId = "optical";

  await fireAndFlush(app.el.btnRefreshSelection, "click");

  assert.equal(app.state.pendingHipsRequest, null, "the pending imagery request must be cancelled");
  assert.equal(app.state.activeImageryButtonId, null);
  clearTimeout(fakeTimeoutId);
});
