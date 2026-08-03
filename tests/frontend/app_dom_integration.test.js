"use strict";

/* app_dom_integration.test.js
 *
 * Browser-DOM integration test for the repair request's item 1 & 4: the
 * target-change-during-load defect must be fixed in the REAL app.js
 * workflow (renderTargetCard() / the "Use Stellarium Selection" click
 * handler / syncEsaskyToCurrentTarget()), not only in the pure
 * esasky_queue.js module. This test runs the actual app.js file (via
 * app_loader.js's Node vm harness) and drives it exactly the way a real
 * page would: dispatching a real click event on the real button element,
 * with a real fetch() response, and a real ESASky iframe `load` event.
 *
 * It reproduces the exact defect scenario from the repair request:
 *   1. target A is loaded
 *   2. ESASky begins loading with A
 *   3. target changes to B before iframe readiness
 *   4. B's goToRaDec and setFov are queued
 *   5. load completes
 *   6. the dispatched final position and FoV are B's
 *   7. no A navigation command survives in the queue
 *
 * If renderTargetCard() or the selection/manual paths ever stop routing
 * through syncEsaskyToCurrentTarget() while the iframe is still loading,
 * this test fails: B's commands are never queued, and step 7's postMessage
 * capture would show no goToRaDec at all (or A's, from the initial iframe
 * URL) rather than B's.
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

const TARGET_B = {
  ok: true,
  connected: true,
  name: "M 42",
  ra_deg: 83.82208,
  dec_deg: -5.39111,
  fov_deg: 1.2,
  ra_sexagesimal: null,
  dec_sexagesimal: null,
};

function makeSelectionFetch(sequence) {
  let call = 0;
  return async function fetchImpl(url) {
    if (String(url).startsWith("/api/selection")) {
      const body = sequence[Math.min(call, sequence.length - 1)];
      call += 1;
      return { ok: true, json: async () => body };
    }
    // /api/status polling, etc: harmless default.
    return { ok: true, json: async () => ({ connected: true }) };
  };
}

test("target change during ESASky load is queued and wins over the stale target (real app.js)", async () => {
  const fetchImpl = makeSelectionFetch([TARGET_A, TARGET_B]);
  const { exports: app } = loadApp(fetchImpl);

  // Capture every postMessage sent to the (fake) ESASky iframe.
  const dispatched = [];
  app.el.esaskyFrame.contentWindow.postMessage = (msg) => dispatched.push(msg);

  // 1. Target A is loaded via the real "Use Stellarium Selection" click handler.
  await fireAndFlush(app.el.btnRefreshSelection, "click");
  assert.equal(app.state.currentTarget.name, "M 31");

  // Turn Online Archive Mode on via the real toggle's change handler.
  app.el.onlineModeToggle.checked = true;
  await fireAndFlush(app.el.onlineModeToggle, "change");
  assert.equal(app.state.onlineMode, true);

  // 2. ESASky begins loading with A (real openOrUpdateEsasky(), via the
  // real "Open in ESASky" button).
  await fireAndFlush(app.el.btnOpenEsasky, "click");
  assert.equal(app.state.esaskyQueue.loadListenerAttached, true);
  assert.equal(app.state.esaskyQueue.ready, false, "iframe must not be ready yet");
  assert.match(app.el.esaskyFrame.src, /target=10\.6847/, "initial URL carries A's target");

  // 3. Target changes to B *before* the iframe fires its load event --
  // again via the real click handler, not a direct state mutation.
  await fireAndFlush(app.el.btnRefreshSelection, "click");
  assert.equal(app.state.currentTarget.name, "M 42");

  // 4. B's goToRaDec/setFov must now be queued (not dropped, not sent).
  // Note: app.state.esaskyQueue.queue is an Array from the vm context's
  // own realm (a different Array constructor than this file's), which
  // trips up assert.deepEqual's strict cross-realm check -- Array.from()
  // here normalizes it into a plain, this-realm array first.
  const queueSnapshot = Array.from(app.state.esaskyQueue.queue, (c) => ({
    event: c.event,
    content: { ...c.content },
  }));
  assert.equal(dispatched.length, 0, "nothing should be dispatched before load fires");
  const queuedEvents = queueSnapshot.map((c) => c.event).sort();
  assert.deepEqual(
    queuedEvents,
    ["goToRaDec", "setFov"],
    "B's navigation commands must be queued while the iframe is still loading"
  );
  const queuedGoTo = queueSnapshot.find((c) => c.event === "goToRaDec");
  assert.equal(queuedGoTo.content.ra, TARGET_B.ra_deg);
  assert.equal(queuedGoTo.content.dec, TARGET_B.dec_deg);
  // 7 (partial, pre-flush): no A coordinates anywhere in the queue.
  const queuedRas = queueSnapshot.map((c) => c.content && c.content.ra).filter((v) => v != null);
  assert.ok(!queuedRas.includes(TARGET_A.ra_deg), "A's RA must not survive in the queue");

  // 5. The iframe load completes (real `load` event -> real
  // attachEsaskyLoadHandler()/markReadyIfActive() path).
  app.el.esaskyFrame.dispatchEvent({ type: "load" });

  // 6. The dispatched final position and FoV are B's.
  assert.equal(app.state.esaskyQueue.ready, true);
  assert.equal(app.state.esaskyQueue.queue.length, 0);
  const goToRaDecCalls = dispatched.filter((m) => m.event === "goToRaDec");
  const setFovCalls = dispatched.filter((m) => m.event === "setFov");
  assert.equal(goToRaDecCalls.length, 1, "exactly one goToRaDec must be flushed");
  assert.equal(setFovCalls.length, 1, "exactly one setFov must be flushed");
  assert.equal(goToRaDecCalls[0].content.ra, TARGET_B.ra_deg);
  assert.equal(goToRaDecCalls[0].content.dec, TARGET_B.dec_deg);
  assert.equal(setFovCalls[0].content.fov, TARGET_B.fov_deg);

  // 7. No A navigation command survives anywhere in what was dispatched
  // via the queue (A only ever appeared in the initial iframe URL, never
  // as a postMessage).
  assert.ok(
    !dispatched.some((m) => m.content && m.content.ra === TARGET_A.ra_deg),
    "A's coordinates must never be dispatched via postMessage"
  );
});

test("toggling Online Archive Mode on does not by itself start an ESASky session", async () => {
  const fetchImpl = makeSelectionFetch([TARGET_A]);
  const { exports: app } = loadApp(fetchImpl);

  await fireAndFlush(app.el.btnRefreshSelection, "click");

  app.el.onlineModeToggle.checked = true;
  await fireAndFlush(app.el.onlineModeToggle, "change");

  assert.equal(app.state.esaskyQueue.loadListenerAttached, false);
  assert.equal(app.el.esaskyFrame.src, "", "no navigation should have been kicked off");
});

test("post-load target switch dispatches B navigation when ESASky is already ready (real app.js)", async () => {
  const fetchImpl = makeSelectionFetch([TARGET_A, TARGET_B]);
  const { exports: app } = loadApp(fetchImpl);

  const dispatched = [];
  app.el.esaskyFrame.contentWindow.postMessage = (msg) => dispatched.push(msg);

  await fireAndFlush(app.el.btnRefreshSelection, "click");
  assert.equal(app.state.currentTarget.name, "M 31");

  app.el.onlineModeToggle.checked = true;
  await fireAndFlush(app.el.onlineModeToggle, "change");

  await fireAndFlush(app.el.btnOpenEsasky, "click");
  app.el.esaskyFrame.dispatchEvent({ type: "load" });
  assert.equal(app.state.esaskyQueue.ready, true, "ESASky must be ready before the post-load switch");
  dispatched.length = 0;

  await fireAndFlush(app.el.btnRefreshSelection, "click");
  assert.equal(app.state.currentTarget.name, "M 42");

  const goToRaDecCalls = dispatched.filter((m) => m.event === "goToRaDec");
  const setFovCalls = dispatched.filter((m) => m.event === "setFov");
  assert.equal(goToRaDecCalls.length, 1, "exactly one goToRaDec must be sent after post-load target switch");
  assert.equal(setFovCalls.length, 1, "exactly one setFov must be sent after post-load target switch");
  assert.equal(goToRaDecCalls[0].content.ra, TARGET_B.ra_deg);
  assert.equal(goToRaDecCalls[0].content.dec, TARGET_B.dec_deg);
  assert.equal(setFovCalls[0].content.fov, TARGET_B.fov_deg);
  assert.ok(
    !dispatched.some((m) => m.content && m.content.ra === TARGET_A.ra_deg),
    "A's coordinates must not be dispatched for the post-load switch"
  );
});

test("zombie queue: target switch still reaches ESASky when first load never marked ready (real app.js)", async () => {
  const fetchImpl = makeSelectionFetch([TARGET_A, TARGET_B]);
  const { exports: app, sandbox } = loadApp(fetchImpl);

  const dispatched = [];
  app.el.esaskyFrame.contentWindow.postMessage = (msg) => dispatched.push(msg);

  await fireAndFlush(app.el.btnRefreshSelection, "click");
  app.el.onlineModeToggle.checked = true;
  await fireAndFlush(app.el.onlineModeToggle, "change");
  await fireAndFlush(app.el.btnOpenEsasky, "click");
  assert.equal(app.state.esaskyQueue.loadListenerAttached, true);
  assert.equal(app.state.esaskyQueue.ready, false);

  // Simulate the load handler detaching without marking ready — e.g. the
  // session was cancelled (reset) before the iframe load fired, so
  // markReadyIfActive() is a no-op but attachEsaskyLoadHandler() still
  // removes its one-shot listener. loadListenerAttached stays true while
  // ready stays false: the "zombie queue" that leaves later targets queued
  // forever with no handler left to flush them.
  sandbox.EsaskyQueue.reset(app.state.esaskyQueue, false);
  app.el.esaskyFrame.dispatchEvent({ type: "load" });

  assert.equal(app.state.esaskyQueue.ready, false, "queue must remain not-ready (zombie state)");
  assert.equal(app.state.esaskyQueue.loadListenerAttached, true, "session flag must still be set");
  dispatched.length = 0;

  await fireAndFlush(app.el.btnRefreshSelection, "click");
  assert.equal(app.state.currentTarget.name, "M 42");

  const goToRaDecCalls = dispatched.filter((m) => m.event === "goToRaDec");
  const setFovCalls = dispatched.filter((m) => m.event === "setFov");
  assert.equal(goToRaDecCalls.length, 1, "goToRaDec must be dispatched despite zombie queue");
  assert.equal(setFovCalls.length, 1, "setFov must be dispatched despite zombie queue");
  assert.equal(goToRaDecCalls[0].content.ra, TARGET_B.ra_deg);
  assert.equal(goToRaDecCalls[0].content.dec, TARGET_B.dec_deg);
  assert.equal(setFovCalls[0].content.fov, TARGET_B.fov_deg);
});
