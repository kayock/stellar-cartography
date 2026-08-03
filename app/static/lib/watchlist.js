/* watchlist.js
 *
 * Pure helpers for the local Tracked Objects watchlist.
 * Authoritative storage is server-side JSON; localStorage is optional cache only.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.Watchlist = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var SCHEMA_VERSION = 1;
  var LOCAL_CACHE_KEY = "foxai_stellar_cartography_watchlist_cache_v1";
  var TRACKED_EXPLAINER =
    "Tracked entries are stored locally on your machine and refreshed only when you request it " +
    "or when you select an entry while the app is open. This is not continuous background monitoring.";

  function sanitizeNote(value) {
    if (value === null || value === undefined) return "";
    return String(value).replace(/[\x00-\x08\x0b\x0c\x0e-\x1f]/g, "").trim().slice(0, 500);
  }

  function duplicateKey(entry) {
    if (entry.featured_kind === "apophis") return "featured:apophis";
    if (entry.source_identifier) return "id:" + String(entry.source_identifier).toLowerCase();
    var ra = Number(entry.saved_ra_deg).toFixed(4);
    var dec = Number(entry.saved_dec_deg).toFixed(4);
    var t = (entry.normalized_object_type || "unknown").toLowerCase();
    return "coord:" + t + ":" + ra + ":" + dec;
  }

  function entryFromTarget(target) {
    var now = new Date().toISOString();
    return {
      watchlist_id: "wl_" + Date.now(),
      display_name: target.name || "Unnamed target",
      normalized_object_type: target.object_type || target.object_category || "unknown",
      source_identifier: target.alt_name || null,
      saved_ra_deg: target.ra_deg,
      saved_dec_deg: target.dec_deg,
      coordinate_source: target.source || "unknown",
      date_added: now,
      last_refreshed: null,
      favorite: false,
      personal_note: "",
      featured_kind: null,
      provider_identifiers: {},
    };
  }

  function addEntry(document, entry) {
    var doc = document && typeof document === "object" ? document : { schema_version: SCHEMA_VERSION, entries: [] };
    var entries = Array.isArray(doc.entries) ? doc.entries.slice() : [];
    var key = duplicateKey(entry);
    var replaced = false;
    for (var i = 0; i < entries.length; i++) {
      if (duplicateKey(entries[i]) === key) {
        entries[i] = Object.assign({}, entries[i], entry, { watchlist_id: entries[i].watchlist_id });
        replaced = true;
        break;
      }
    }
    if (!replaced) entries.unshift(entry);
    return { schema_version: SCHEMA_VERSION, entries: entries };
  }

  function removeEntry(document, watchlistId) {
    var doc = document || { schema_version: SCHEMA_VERSION, entries: [] };
    var entries = (doc.entries || []).filter(function (e) {
      return e.watchlist_id !== watchlistId;
    });
    return { schema_version: SCHEMA_VERSION, entries: entries };
  }

  function updateEntry(document, watchlistId, patch) {
    var doc = document || { schema_version: SCHEMA_VERSION, entries: [] };
    var entries = (doc.entries || []).map(function (e) {
      if (e.watchlist_id !== watchlistId) return e;
      var next = Object.assign({}, e, patch || {});
      if (patch && patch.personal_note !== undefined) {
        next.personal_note = sanitizeNote(patch.personal_note);
      }
      if (patch && patch.tracker_cache !== undefined) {
        next.tracker_cache = patch.tracker_cache;
      }
      return next;
    });
    return { schema_version: SCHEMA_VERSION, entries: entries };
  }

  function targetFromEntry(entry) {
    return {
      name: entry.display_name,
      alt_name: entry.source_identifier,
      object_type: entry.normalized_object_type,
      ra_deg: entry.saved_ra_deg,
      dec_deg: entry.saved_dec_deg,
      source: "watchlist:" + (entry.coordinate_source || "saved"),
      fov_deg: null,
    };
  }

  function buildApophisSeedEntry() {
    return {
      watchlist_id: "wl_apophis",
      display_name: "99942 Apophis",
      normalized_object_type: "asteroid",
      source_identifier: "2004 MN4",
      saved_ra_deg: 0,
      saved_dec_deg: 0,
      coordinate_source: "featured_tracker",
      date_added: new Date().toISOString(),
      last_refreshed: null,
      favorite: false,
      personal_note: "",
      featured_kind: "apophis",
      provider_identifiers: { jpl_sbdb: "99942", designation: "99942", name: "Apophis" },
    };
  }

  function writeLocalCache(document) {
    try {
      if (typeof localStorage !== "undefined") {
        localStorage.setItem(LOCAL_CACHE_KEY, JSON.stringify(document));
      }
    } catch (_err) {
      /* ignore quota errors */
    }
  }

  function findApophisEntry(document) {
    var doc = document || { entries: [] };
    return (doc.entries || []).find(function (e) {
      return e && e.featured_kind === "apophis";
    }) || null;
  }

  function hasApophisEntry(document) {
    return !!findApophisEntry(document);
  }

  function buildApophisTrackerCache(apiSummary, retrievedAt) {
    return {
      kind: "apophis",
      retrieved_at: retrievedAt || (apiSummary && apiSummary.retrieved_at) || null,
      summary: apiSummary || null,
    };
  }

  function readLocalCache() {
    try {
      if (typeof localStorage === "undefined") return null;
      var raw = localStorage.getItem(LOCAL_CACHE_KEY);
      if (!raw) return null;
      return JSON.parse(raw);
    } catch (_err) {
      return null;
    }
  }

  function isApophisEntry(entry) {
    return entry && entry.featured_kind === "apophis";
  }

  function isFeaturedTrackerPlaceholder(entry) {
    if (!isApophisEntry(entry)) return false;
    return (
      entry.coordinate_source === "featured_tracker" &&
      Number(entry.saved_ra_deg) === 0 &&
      Number(entry.saved_dec_deg) === 0
    );
  }

  function extractValidatedEphemeris(entry, payload) {
    var summary = payload;
    if (!summary && entry && entry.tracker_cache && entry.tracker_cache.summary) {
      summary = entry.tracker_cache.summary;
    }
    if (!summary || !summary.ephemeris || !summary.ephemeris.ok) return null;
    var e = summary.ephemeris;
    if (typeof e.ra_deg !== "number" || typeof e.dec_deg !== "number") return null;
    if (!isFinite(e.ra_deg) || !isFinite(e.dec_deg)) return null;
    if (e.ra_deg < 0 || e.ra_deg > 360 || e.dec_deg < -90 || e.dec_deg > 90) return null;
    return {
      ra_deg: e.ra_deg,
      dec_deg: e.dec_deg,
      epoch: e.epoch || summary.ephemeris_epoch || summary.retrieved_at || null,
      distance_au: e.distance_au,
      observer_context: summary.observer_context || null,
      retrieved_at: summary.retrieved_at || (entry && entry.tracker_cache && entry.tracker_cache.retrieved_at) || null,
    };
  }

  function hasValidatedSkyPosition(entry, payload) {
    return !!extractValidatedEphemeris(entry, payload);
  }

  function apophisOpensWithoutTargetChange(entry) {
    return isApophisEntry(entry);
  }

  return {
    SCHEMA_VERSION: SCHEMA_VERSION,
    LOCAL_CACHE_KEY: LOCAL_CACHE_KEY,
    TRACKED_EXPLAINER: TRACKED_EXPLAINER,
    sanitizeNote: sanitizeNote,
    duplicateKey: duplicateKey,
    entryFromTarget: entryFromTarget,
    addEntry: addEntry,
    removeEntry: removeEntry,
    updateEntry: updateEntry,
    targetFromEntry: targetFromEntry,
    buildApophisSeedEntry: buildApophisSeedEntry,
    findApophisEntry: findApophisEntry,
    hasApophisEntry: hasApophisEntry,
    buildApophisTrackerCache: buildApophisTrackerCache,
    writeLocalCache: writeLocalCache,
    readLocalCache: readLocalCache,
    isApophisEntry: isApophisEntry,
    isFeaturedTrackerPlaceholder: isFeaturedTrackerPlaceholder,
    extractValidatedEphemeris: extractValidatedEphemeris,
    hasValidatedSkyPosition: hasValidatedSkyPosition,
    apophisOpensWithoutTargetChange: apophisOpensWithoutTargetChange,
  };
});
