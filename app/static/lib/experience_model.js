/* experience_model.js
 *
 * DOM-free helpers for Sky Time Machine validation, postcard filenames,
 * metadata comparison display, motion SVG path, and sonification mapping.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.ExperienceModel = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  function validateTimeMachineForm(form) {
    form = form || {};
    var applyTime = !!form.apply_time;
    var applyLocation = !!form.apply_location;
    if (!applyTime && !applyLocation) {
      return { ok: false, error: "Choose Apply for time and/or location." };
    }
    if (applyTime && !form.preset && !String(form.utc || "").trim()) {
      return { ok: false, error: "Enter a UTC date/time or choose a preset." };
    }
    if (applyLocation) {
      var lat = Number(form.latitude);
      var lon = Number(form.longitude);
      if (!Number.isFinite(lat) || lat < -90 || lat > 90) {
        return { ok: false, error: "Latitude must be between -90 and 90." };
      }
      if (!Number.isFinite(lon) || lon < -180 || lon > 180) {
        return { ok: false, error: "Longitude must be between -180 and 180." };
      }
    }
    return { ok: true, error: null };
  }

  function postcardFilename(meta) {
    var name = ((meta && meta.selection && meta.selection.name) || "sky").replace(/[^\w.-]+/g, "_");
    var utc = ((meta && meta.sky && meta.sky.utc) || "now").replace(/[:]/g, "").replace(/\.\d+Z$/, "Z");
    return "sky-postcard-" + name + "-" + utc + ".json";
  }

  function motionPolyline(points, width, height) {
    width = width || 280;
    height = height || 80;
    var pad = 10;
    if (!points || !points.length) return { d: "", width: width, height: height };
    var alts = points.map(function (p) { return p.altitude_deg; });
    var min = Math.min.apply(null, alts);
    var max = Math.max.apply(null, alts);
    var span = max - min || 1;
    var coords = points.map(function (p, i) {
      var x = pad + (i / Math.max(points.length - 1, 1)) * (width - pad * 2);
      var y = height - pad - ((p.altitude_deg - min) / span) * (height - pad * 2);
      return x.toFixed(1) + "," + y.toFixed(1);
    });
    return { d: "M " + coords.join(" L "), width: width, height: height };
  }

  function sonifyFrequencies(samples) {
    if (!samples || !samples.length) return [];
    return samples.map(function (s) {
      return { t: s.t, frequency_hz: s.frequency_hz, value: s.value };
    });
  }

  function defaultAudioPrefs() {
    return { uiSounds: false, volume: 0.25 };
  }

  function parseAudioPrefs(raw) {
    var defaults = defaultAudioPrefs();
    if (!raw) return defaults;
    try {
      var parsed = typeof raw === "string" ? JSON.parse(raw) : raw;
      return {
        uiSounds: parsed.uiSounds === true,
        volume: Number.isFinite(Number(parsed.volume)) ? Math.min(1, Math.max(0, Number(parsed.volume))) : defaults.volume,
      };
    } catch (_err) {
      return defaults;
    }
  }

  function compareChangedCount(rows) {
    if (!rows) return 0;
    return rows.filter(function (row) { return row.changed; }).length;
  }

  return {
    validateTimeMachineForm: validateTimeMachineForm,
    postcardFilename: postcardFilename,
    motionPolyline: motionPolyline,
    sonifyFrequencies: sonifyFrequencies,
    defaultAudioPrefs: defaultAudioPrefs,
    parseAudioPrefs: parseAudioPrefs,
    compareChangedCount: compareChangedCount,
  };
});
