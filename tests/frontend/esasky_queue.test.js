"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");

const EsaskyQueue = require(path.join(__dirname, "..", "..", "app", "static", "lib", "esasky_queue.js"));

test("first imagery action waits for iframe readiness (queued, not dropped)", () => {
  const state = EsaskyQueue.createState();
  const sent = [];
  const outcome = EsaskyQueue.enqueueOrSend(state, (cmd) => sent.push(cmd), { event: "getAvailableHips", content: {} });
  assert.equal(outcome, "queued");
  assert.equal(sent.length, 0);
  assert.equal(state.queue.length, 1);
});

test("commands flush in deterministic order once the iframe becomes ready", () => {
  const state = EsaskyQueue.createState();
  const sent = [];
  const sendFn = (cmd) => sent.push(cmd.event);

  EsaskyQueue.enqueueOrSend(state, sendFn, { event: "goToRaDec", content: {} });
  EsaskyQueue.enqueueOrSend(state, sendFn, { event: "setFov", content: {} });
  EsaskyQueue.enqueueOrSend(state, sendFn, { event: "getAvailableHips", content: {} });
  assert.equal(sent.length, 0, "nothing should be sent before readiness");

  EsaskyQueue.markReady(state, sendFn);
  assert.deepEqual(sent, ["goToRaDec", "setFov", "getAvailableHips"]);
  assert.equal(state.queue.length, 0);
});

test("commands sent after readiness go straight through, not queued", () => {
  const state = EsaskyQueue.createState();
  const sent = [];
  EsaskyQueue.markReady(state, (cmd) => sent.push(cmd.event));

  const outcome = EsaskyQueue.enqueueOrSend(state, (cmd) => sent.push(cmd.event), { event: "changeHips", content: {} });
  assert.equal(outcome, "sent");
  assert.deepEqual(sent, ["changeHips"]);
});

test("reset returns the queue to not-ready and clears pending commands", () => {
  const state = EsaskyQueue.createState();
  EsaskyQueue.enqueueOrSend(state, () => {}, { event: "goToRaDec", content: {} });
  EsaskyQueue.markReady(state, () => {});
  state.loadListenerAttached = true;

  EsaskyQueue.reset(state, true);
  assert.equal(state.ready, false);
  assert.equal(state.queue.length, 0);
  assert.equal(state.loadListenerAttached, false);
});

test("reset without resetListenerFlag preserves loadListenerAttached", () => {
  const state = EsaskyQueue.createState();
  state.loadListenerAttached = true;
  EsaskyQueue.reset(state, false);
  assert.equal(state.loadListenerAttached, true);
});

// --- Browser-state contract: stale generation load callbacks ------------
//
// 1. begin ESASky load;
// 2. turn online mode off before load completion;
// 3. fire the stale load callback;
// 4. state remains offline and not ready;
// 5. start a new session;
// 6. commands remain queued until the new session's valid load callback
//    fires.
test("browser-state contract: a stale generation's load callback can never mark the queue ready, and a fresh session starts clean", () => {
  const state = EsaskyQueue.createState();
  const sent = [];
  const sendFn = (cmd) => sent.push(cmd.event);

  // 1. begin ESASky load (session/generation 1) and queue a command while
  // it's still in flight.
  const gen1 = EsaskyQueue.beginSession(state);
  assert.equal(state.ready, false, "a fresh session must not start ready");
  EsaskyQueue.enqueueOrSend(state, sendFn, { event: "goToRaDec", content: {} });
  assert.equal(state.queue.length, 1);

  // 2. turn online mode off before load completion -- this is what
  // app.js's turnOnlineModeOff() does to the queue state (reset()),
  // before it ever sets the iframe src to about:blank.
  EsaskyQueue.reset(state, true);
  assert.equal(state.cancelled, true);
  assert.equal(state.ready, false);
  assert.equal(state.queue.length, 0);

  // 3. fire the stale load callback -- e.g. the about:blank navigation
  // that setting iframe.src triggered completing, invoking whatever load
  // handler happened to still be attached, captured with generation 1.
  const activatedStale = EsaskyQueue.markReadyIfActive(state, gen1, sendFn);

  // 4. state remains offline and not ready -- the stale callback was a
  // no-op: it did not mark the queue ready and sent nothing.
  assert.equal(activatedStale, false);
  assert.equal(state.ready, false);
  assert.equal(sent.length, 0);

  // 5. start a new session (generation 2, distinct from generation 1).
  const gen2 = EsaskyQueue.beginSession(state);
  assert.notEqual(gen2, gen1);
  assert.equal(state.cancelled, false);

  // 6. commands remain queued until the new session's valid load callback
  // fires -- not sent early, and not lost.
  const outcome = EsaskyQueue.enqueueOrSend(state, sendFn, { event: "goToRaDec", content: {} });
  assert.equal(outcome, "queued");
  assert.equal(sent.length, 0, "nothing should be sent while the new session is still loading");

  const activatedFresh = EsaskyQueue.markReadyIfActive(state, gen2, sendFn);
  assert.equal(activatedFresh, true);
  assert.equal(state.ready, true);
  assert.deepEqual(sent, ["goToRaDec"], "the new session's valid load callback flushes the queue");
});

test("markReadyIfActive is a no-op for a generation that never matched (e.g. 0, or a generation from a different state object)", () => {
  const state = EsaskyQueue.createState();
  const sent = [];
  EsaskyQueue.beginSession(state);
  const activated = EsaskyQueue.markReadyIfActive(state, 999, (cmd) => sent.push(cmd));
  assert.equal(activated, false);
  assert.equal(state.ready, false);
  assert.equal(sent.length, 0);
});

// --- Replacing pending navigation commands with the newest target -------

test("a newer target's queued goToRaDec/setFov replace an older target's, instead of accumulating both", () => {
  const state = EsaskyQueue.createState();
  const sent = [];
  const sendFn = (cmd) => sent.push(cmd);

  EsaskyQueue.beginSession(state);

  // Target A starts navigating while the iframe is still loading.
  EsaskyQueue.enqueueOrSend(state, sendFn, { event: "goToRaDec", content: { ra: 1, dec: 1 }, replaceKey: "goToRaDec" });
  EsaskyQueue.enqueueOrSend(state, sendFn, { event: "setFov", content: { fov: 5 }, replaceKey: "setFov" });
  assert.equal(state.queue.length, 2);

  // Target changes to B before the load completes -- B's commands should
  // replace A's, not sit alongside them.
  EsaskyQueue.enqueueOrSend(state, sendFn, { event: "goToRaDec", content: { ra: 2, dec: 2 }, replaceKey: "goToRaDec" });
  EsaskyQueue.enqueueOrSend(state, sendFn, { event: "setFov", content: { fov: 9 }, replaceKey: "setFov" });
  assert.equal(state.queue.length, 2, "queue must not grow with stale commands from target A");

  // Load completes -- flush.
  EsaskyQueue.markReady(state, sendFn);

  const goToRaDecCmds = sent.filter((c) => c.event === "goToRaDec");
  const setFovCmds = sent.filter((c) => c.event === "setFov");
  assert.equal(goToRaDecCmds.length, 1, "only B's goToRaDec should have been dispatched");
  assert.deepEqual(goToRaDecCmds[0].content, { ra: 2, dec: 2 }, "the final dispatched position must be B, not A");
  assert.equal(setFovCmds.length, 1);
  assert.deepEqual(setFovCmds[0].content, { fov: 9 }, "the newest FoV must be used");
});

test("commands without a replaceKey (e.g. getAvailableHips) are never deduped against each other or against navigation commands", () => {
  const state = EsaskyQueue.createState();
  const sent = [];
  const sendFn = (cmd) => sent.push(cmd.event);

  EsaskyQueue.enqueueOrSend(state, sendFn, { event: "goToRaDec", content: {}, replaceKey: "goToRaDec" });
  EsaskyQueue.enqueueOrSend(state, sendFn, { event: "getAvailableHips", content: {} });
  EsaskyQueue.enqueueOrSend(state, sendFn, { event: "goToRaDec", content: {}, replaceKey: "goToRaDec" });

  assert.equal(state.queue.length, 2, "the getAvailableHips command must be preserved alongside the deduped goToRaDec");
  EsaskyQueue.markReady(state, sendFn);
  assert.deepEqual(sent, ["getAvailableHips", "goToRaDec"], "deterministic order preserved for non-navigation commands");
});
