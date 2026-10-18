/* audio_coordinator.js
 *
 * Lightweight mutual exclusion for Cartography audio. UI click sounds stay
 * independent. Only one Cartography narration stream plays at a time.
 */
(function (root) {
  "use strict";

  var CATEGORIES = ["narration", "cosmic_signal", "official_media", "data_sonification", "ui"];
  var handles = {};

  function acquire(category, handle) {
    if (CATEGORIES.indexOf(category) === -1) return;
    if (category === "narration") {
      stop("narration");
      pause("cosmic_signal");
      pause("official_media");
      pause("data_sonification");
    } else if (category === "cosmic_signal" || category === "official_media" || category === "data_sonification") {
      pause("narration");
      if (category !== "cosmic_signal") pause("cosmic_signal");
      if (category !== "official_media") pause("official_media");
      if (category !== "data_sonification") pause("data_sonification");
    }
    handles[category] = handle || null;
  }

  function pause(category) {
    var handle = handles[category];
    if (!handle) return;
    try {
      if (typeof handle.pause === "function") handle.pause();
    } catch (_err) { /* media element may already be gone */ }
  }

  function stop(category) {
    var handle = handles[category];
    if (!handle) return;
    try {
      if (typeof handle.stop === "function") handle.stop();
      else if (typeof handle.pause === "function") handle.pause();
    } catch (_err) { /* media element may already be gone */ }
    handles[category] = null;
  }

  function stopAll() {
    CATEGORIES.forEach(function (category) {
      if (category !== "ui") stop(category);
    });
  }

  function current(category) {
    return handles[category] || null;
  }

  root.CartographyAudio = {
    CATEGORIES: CATEGORIES,
    acquire: acquire,
    pause: pause,
    stop: stop,
    stopAll: stopAll,
    current: current,
    noOverlap: true,
  };

  if (typeof module === "object" && module.exports) {
    module.exports = root.CartographyAudio;
  }
})(typeof self !== "undefined" ? self : this);
