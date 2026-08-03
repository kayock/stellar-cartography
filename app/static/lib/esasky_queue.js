/* esasky_queue.js
 *
 * Pure, DOM-free command-queue logic that gates ESASky postMessage
 * commands (getAvailableHips, changeHips, goToRaDec, setFov) until the
 * ESASky iframe has actually finished loading. Commands issued before
 * readiness are queued and flushed, in order, exactly once when the
 * iframe's load event fires -- they are never silently dropped on the
 * first click.
 *
 * Session-generation tokens
 * -------------------------
 * An iframe's `load` event can fire more than once conceptually tied to
 * "the wrong session" -- most notably when Online Archive Mode is turned
 * off (which sets the iframe src to about:blank) while an ESASky
 * navigation is still in flight. Setting src to about:blank triggers its
 * own `load` event; if the *original*, now-stale load handler for the
 * ESASky navigation is still attached, that stale about:blank load can
 * incorrectly flip the queue to "ready" while the UI/state say offline.
 *
 * To make that impossible, every fresh ESASky navigation gets a new
 * "generation" number (beginSession()). A load handler captures the
 * generation it belongs to and must call markReadyIfActive() with that
 * captured value; markReadyIfActive() is a no-op unless the session
 * hasn't been cancelled (see reset()) and the generation is still the
 * current one. This is deterministic and doesn't depend on event timing.
 *
 * DOM-free by design so it can be exercised directly by build-time Node
 * tests (tests/frontend/esasky_queue.test.js). app.js wires this to the
 * real iframe's `load` event and postMessage.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.EsaskyQueue = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  function createState() {
    return {
      ready: false,
      // True once the iframe src has been set for the current session --
      // used to guard against attaching more than one `load` listener.
      loadListenerAttached: false,
      queue: [],
      // Bumped by beginSession() for every fresh ESASky navigation. A
      // load handler must compare against this before acting.
      generation: 0,
      // True whenever there is no live session a load handler may act
      // for (e.g. right after Online Archive Mode is turned off). Reset
      // to false by beginSession() when a new session actually begins.
      cancelled: true,
    };
  }

  /** Send `cmd` ({event, content, replaceKey?}) immediately via sendFn if
   * the queue is ready; otherwise append it to the queue for later
   * flushing. Returns "sent" or "queued" so callers/tests can assert on
   * the outcome without needing to inspect sendFn's call log.
   *
   * If `cmd.replaceKey` is set and the queue is not yet ready, any
   * previously queued command with the same replaceKey is dropped before
   * the new one is appended. This lets navigation commands (goToRaDec /
   * setFov) represent "go to the latest target" -- selecting target B
   * while target A's load is still pending replaces A's queued
   * navigation rather than piling both up -- while commands without a
   * replaceKey (e.g. getAvailableHips, changeHips) are left untouched and
   * keep their place in the deterministic flush order.
   */
  function enqueueOrSend(state, sendFn, cmd) {
    if (state.ready) {
      sendFn(cmd);
      return "sent";
    }
    if (cmd && cmd.replaceKey) {
      state.queue = state.queue.filter(function (queued) {
        return queued.replaceKey !== cmd.replaceKey;
      });
    }
    state.queue.push(cmd);
    return "queued";
  }

  /** Mark the queue ready unconditionally and flush any queued commands,
   * in the order they were enqueued. Prefer markReadyIfActive() from a
   * real iframe `load` handler; this lower-level function is kept for
   * direct/manual use and as the mechanism markReadyIfActive() itself
   * uses once it has confirmed the session is still current. */
  function markReady(state, sendFn) {
    state.ready = true;
    var pending = state.queue;
    state.queue = [];
    pending.forEach(function (cmd) {
      sendFn(cmd);
    });
  }

  /** Returns true if `generation` is still the state's current,
   * non-cancelled session. Use this to guard any work a load handler is
   * about to do (not just markReadyIfActive itself). */
  function isActive(state, generation) {
    return !state.cancelled && state.generation === generation;
  }

  /** Call this from the ESASky iframe's `load` handler, passing the
   * generation number the handler captured when it was created (from
   * beginSession()'s return value). Does nothing -- does NOT mark ready,
   * does NOT flush the queue -- unless that generation is still the
   * current, non-cancelled session. Returns true if the queue was
   * actually marked ready, false if the callback was stale and ignored.
   *
   * This is what makes a stale about:blank load (fired after Online
   * Archive Mode was turned off and reset() cancelled the session) unable
   * to mark the queue ready: reset() sets cancelled=true, so this returns
   * false for any generation captured before that point. */
  function markReadyIfActive(state, generation, sendFn) {
    if (!isActive(state, generation)) {
      return false;
    }
    markReady(state, sendFn);
    return true;
  }

  /** Begin a fresh ESASky load session: bump the generation counter,
   * reset ready to false (a fresh navigation is never immediately ready),
   * clear cancelled, and clear the queue (a brand new session has nothing
   * pending from a previous one). Returns the new generation number --
   * callers must capture this and pass it to markReadyIfActive(). */
  function beginSession(state) {
    state.generation += 1;
    state.ready = false;
    state.cancelled = false;
    state.queue = [];
    return state.generation;
  }

  /** Reset the queue to its initial, not-ready state (used when Online
   * Archive Mode is turned off, or before loading a fresh iframe). This
   * also invalidates (cancels) whatever generation is currently active,
   * so that a stale load callback captured before this call -- including
   * one triggered by setting the iframe src to about:blank right after --
   * can never mark the queue ready (see markReadyIfActive). Does NOT
   * reset loadListenerAttached by default, since the caller is
   * responsible for tearing down / replacing the iframe element itself
   * when it wants a fresh listener; pass resetListenerFlag=true if the
   * iframe element itself is being replaced or reset. */
  function reset(state, resetListenerFlag) {
    state.cancelled = true;
    state.ready = false;
    state.queue = [];
    if (resetListenerFlag) {
      state.loadListenerAttached = false;
    }
  }

  return {
    createState: createState,
    enqueueOrSend: enqueueOrSend,
    markReady: markReady,
    markReadyIfActive: markReadyIfActive,
    isActive: isActive,
    beginSession: beginSession,
    reset: reset,
  };
});
