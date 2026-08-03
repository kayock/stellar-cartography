/* imagery_matching.js
 *
 * Pure, DOM-free logic for matching ESASky HiPS layer names against the
 * app's telescope/wavelength buttons, using explicit alias groups instead
 * of a rigid "all keywords must match" rule.
 *
 * Deliberately has zero dependency on the DOM, fetch, or postMessage so it
 * can be exercised directly by build-time Node tests (see
 * tests/frontend/imagery_matching.test.js) as well as loaded as a plain
 * <script> tag in the browser. This is the ACTUAL matching logic used by
 * app.js -- not a parallel/unused implementation.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.ImageryMatching = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  // Each entry:
  //   id, label, waveTag, explain       - display metadata
  //   matchMode: "any" | "all"          - how `keywords` combine
  //   keywords: [string, ...]           - lowercase substrings to look for
  //     in a candidate HiPS layer name
  //   preferred: [string, ...]          - optional; when several layers
  //     match, prefer the first one whose name contains one of these
  //     substrings (checked in order)
  //   preferredExact: string            - optional; a well-known layer
  //     name this button should request directly via changeHips without
  //     first asking ESASky what's available (e.g. the default optical
  //     survey, which is always present)
  var IMAGERY_BUTTONS = [
    {
      id: "optical",
      label: "Default Optical",
      waveTag: "Visible light",
      matchMode: "any",
      keywords: ["dss2"],
      preferredExact: "DSS2 color",
      explain: "Ordinary visible light — close to what the human eye would see.",
    },
    {
      id: "hubble",
      label: "Hubble",
      waveTag: "Visible / UV",
      // Accept "HST" or "Hubble" -- do NOT require the word "Hubble",
      // since many ESASky layer names use only the "HST" abbreviation.
      matchMode: "any",
      keywords: ["hst", "hubble"],
      preferred: ["hst acs", "hst wfc3", "hubble"],
      explain: "Imagery associated with the Hubble Space Telescope, where ESASky has a matching all-sky layer.",
    },
    {
      id: "jwst_nircam",
      label: "JWST NIRCam",
      waveTag: "Near-infrared",
      matchMode: "all",
      keywords: ["jwst", "nircam"],
      explain: "Near-infrared imagery from JWST's NIRCam instrument, where a matching layer exists.",
    },
    {
      id: "jwst_miri",
      label: "JWST MIRI",
      waveTag: "Mid-infrared",
      matchMode: "all",
      keywords: ["jwst", "miri"],
      explain: "Mid-infrared imagery from JWST's MIRI instrument, where a matching layer exists.",
    },
    {
      id: "wise",
      label: "WISE Infrared",
      waveTag: "Infrared",
      // "wise" as a substring already covers both "WISE" and "AllWISE".
      matchMode: "any",
      keywords: ["wise"],
      explain: "All-sky infrared survey imagery from the WISE mission.",
    },
    {
      id: "spitzer",
      label: "Spitzer Infrared",
      waveTag: "Infrared",
      matchMode: "any",
      keywords: ["spitzer", "irac"],
      explain: "Infrared imagery from the Spitzer Space Telescope, where available.",
    },
    {
      id: "herschel",
      label: "Herschel Far-IR",
      waveTag: "Far-infrared",
      matchMode: "any",
      keywords: ["herschel"],
      preferred: ["pacs rgb", "herschel"],
      explain: "Far-infrared imagery from the Herschel Space Observatory, tracing cold dust.",
    },
    {
      id: "xray",
      label: "X-Ray",
      waveTag: "X-ray",
      // Accept any suitable X-ray survey -- do not require every
      // alternative name to appear together in one layer name.
      matchMode: "any",
      keywords: ["xmm-newton", "xmm", "erosita", "e-rosita", "rosat", "chandra", "x-ray", "xray"],
      preferred: ["xmm-newton epic color", "xmm-newton", "x-ray"],
      explain: "X-ray imagery, tracing extremely hot gas, shocks, and high-energy events.",
    },
    {
      id: "microwave",
      label: "Microwave",
      waveTag: "Microwave",
      matchMode: "any",
      keywords: ["planck"],
      explain: "Microwave / millimeter-wave imagery, e.g. cosmic background radiation or cold dust emission.",
    },
  ];

  function layerMatchesConfig(cfg, layerName) {
    if (typeof layerName !== "string" || !layerName) return false;
    var lower = layerName.toLowerCase();
    var keywords = cfg.keywords || [];
    if (keywords.length === 0) return false;
    if (cfg.matchMode === "all") {
      return keywords.every(function (kw) {
        return lower.indexOf(kw.toLowerCase()) !== -1;
      });
    }
    // default: "any"
    return keywords.some(function (kw) {
      return lower.indexOf(kw.toLowerCase()) !== -1;
    });
  }

  /** Given a button config and a flat list of candidate HiPS layer name
   * strings, return the matched layer name, or null if none match. When
   * several layers match, prefer one named in cfg.preferred (checked in
   * order); otherwise return the first match found. */
  function matchImageryLayer(cfg, layerNames) {
    if (!cfg || !Array.isArray(layerNames) || layerNames.length === 0) return null;
    var candidates = layerNames.filter(function (name) {
      return layerMatchesConfig(cfg, name);
    });
    if (candidates.length === 0) return null;
    if (cfg.preferred) {
      for (var i = 0; i < cfg.preferred.length; i++) {
        var pref = cfg.preferred[i].toLowerCase();
        var hit = candidates.find(function (name) {
          return name.toLowerCase().indexOf(pref) !== -1;
        });
        if (hit) return hit;
      }
    }
    return candidates[0];
  }

  /** Heuristic recognizer for an ESASky getAvailableHips response: shape
   * may vary by ESASky version -- tolerate objects/arrays and probe
   * common name-like fields. */
  function looksLikeHipsListing(data) {
    if (!data || typeof data !== "object") return false;
    var payload = data.content !== undefined ? data.content : data.values !== undefined ? data.values : data;
    if (!payload || typeof payload !== "object") return false;
    return (
      Array.isArray(payload) ||
      Object.keys(payload).some(function (k) {
        return Array.isArray(payload[k]);
      })
    );
  }

  /** Extract a flat list of candidate layer-name strings out of a
   * getAvailableHips-shaped response. */
  function extractHipsNames(data) {
    var payload = data.content !== undefined ? data.content : data.values !== undefined ? data.values : data;
    var names = [];
    function collect(list) {
      if (!Array.isArray(list)) return;
      for (var i = 0; i < list.length; i++) {
        var entry = list[i];
        if (typeof entry === "string") {
          names.push(entry);
        } else if (entry && typeof entry === "object") {
          var n = entry.name || entry.hipsName || entry.id || entry.label;
          if (n) names.push(n);
        }
      }
    }
    if (Array.isArray(payload)) {
      collect(payload);
    } else if (payload && typeof payload === "object") {
      Object.keys(payload).forEach(function (k) {
        collect(payload[k]);
      });
    }
    return names;
  }

  return {
    IMAGERY_BUTTONS: IMAGERY_BUTTONS,
    layerMatchesConfig: layerMatchesConfig,
    matchImageryLayer: matchImageryLayer,
    looksLikeHipsListing: looksLikeHipsListing,
    extractHipsNames: extractHipsNames,
  };
});
