/* solar_system.js
 *
 * Pure, DOM-free helpers for Solar System Awareness (R0.2):
 *   - detect Solar System targets from Stellarium-reported fields
 *   - derive a bounded ESASky viewer FoV (never blindly pass wide
 *     Stellarium FoV such as 60° for a tiny planet)
 *   - supply honest explanatory copy for the Solar System notice panel
 *
 * Detection follows Stellarium's documented getInfoMap shape:
 *   - "type"            -> object_category (broad class, e.g. "Planet")
 *   - "object-type"     -> object_type (refined type, e.g. "planet", "moon")
 * See Stellarium Remote Control API / StelObject::getInfoMap documentation.
 * We never guess from object names alone.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.SolarSystem = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  /** Stellarium object-type values that clearly identify Solar System bodies.
   * Kept as an explicit allow-list so "planetary nebula" and other deep-sky
   * strings are never matched by substring heuristics. */
  var SOLAR_SYSTEM_OBJECT_TYPES = {
    planet: true,
    moon: true,
    comet: true,
    asteroid: true,
    "minor planet": true,
    "dwarf planet": true,
    satellite: true,
  };

  /** FoV bounds for ESASky when viewing Solar System coordinates.
   * Rationale documented in deriveEsaskyFovDeg() below. */
  var FOV_MIN_DEG = 0.15;
  var FOV_MAX_DEG = 2.0;
  var FOV_DEFAULT_DEG = 0.5;
  var FOV_ANGULAR_SIZE_MARGIN = 4;

  function normalizeField(value) {
    if (typeof value !== "string") return "";
    return value.trim().toLowerCase();
  }

  /** Return true when Stellarium's reported fields identify a Solar System
   * target. `target` is the frontend in-memory model (from TargetModel). */
  function isSolarSystemTarget(target) {
    if (!target || typeof target !== "object") return false;

    var objectType = normalizeField(target.object_type);
    var objectCategory = normalizeField(target.object_category);

    if (objectType && SOLAR_SYSTEM_OBJECT_TYPES[objectType]) {
      return true;
    }

    // Stellarium's "Planet" class covers planets, moons, and the Sun.
    // The Sun reports object-type "star" per StelObject documentation.
    if (objectCategory === "planet") {
      if (!objectType) return true;
      if (objectType === "star") return true;
      if (SOLAR_SYSTEM_OBJECT_TYPES[objectType]) return true;
    }

    return false;
  }

  /** FoV sent to ESASky for the current target.
   *
   * Non-Solar-System: returns Stellarium's fov_deg unchanged (existing
   * R0.1.x behaviour — may be null).
   *
   * Solar System: never forwards an extremely wide Stellarium FoV (e.g.
   * 60° while the whole sky is visible). Instead:
   *   1. Start from angular_size_deg * FOV_ANGULAR_SIZE_MARGIN when
   *      Stellarium reported a finite angular size, else FOV_DEFAULT_DEG
   *      (~half a degree, similar to the Moon's apparent diameter).
   *   2. Clamp to [FOV_MIN_DEG, FOV_MAX_DEG].
   *   3. If Stellarium FoV is already within that band, prefer the
   *      tighter of Stellarium and the derived value (respects user zoom).
   *   4. If Stellarium FoV exceeds FOV_MAX_DEG, ignore it and use derived.
   */
  function deriveEsaskyFovDeg(target) {
    if (!isSolarSystemTarget(target)) {
      return target && typeof target.fov_deg === "number" ? target.fov_deg : null;
    }

    var derived = FOV_DEFAULT_DEG;
    if (typeof target.angular_size_deg === "number" && target.angular_size_deg > 0) {
      derived = target.angular_size_deg * FOV_ANGULAR_SIZE_MARGIN;
    }
    derived = Math.min(FOV_MAX_DEG, Math.max(FOV_MIN_DEG, derived));

    var stellariumFov = target.fov_deg;
    if (typeof stellariumFov === "number" && Number.isFinite(stellariumFov)) {
      if (stellariumFov > FOV_MAX_DEG) {
        return derived;
      }
      if (stellariumFov >= FOV_MIN_DEG) {
        return Math.min(stellariumFov, derived);
      }
    }
    return derived;
  }

  /** Paragraphs shown in the Solar System notice panel. Static, truthful copy. */
  function buildSolarSystemNoticeParagraphs() {
    return [
      "ESASky is displaying the sky-survey background at this object's reported coordinates — not a dedicated close-up planetary photograph.",
      "The active HiPS survey layer may have no imagery intended for Solar System bodies at these coordinates; a blank or generic star-field view is normal.",
      "Even when survey tiles appear, they show archival all-sky mosaics and are not necessarily this object's current visual appearance.",
      "Stellar Cartography has still navigated ESASky to the correct RA/Dec reported by Stellarium.",
    ];
  }

  return {
    SOLAR_SYSTEM_OBJECT_TYPES: SOLAR_SYSTEM_OBJECT_TYPES,
    FOV_MIN_DEG: FOV_MIN_DEG,
    FOV_MAX_DEG: FOV_MAX_DEG,
    FOV_DEFAULT_DEG: FOV_DEFAULT_DEG,
    FOV_ANGULAR_SIZE_MARGIN: FOV_ANGULAR_SIZE_MARGIN,
    isSolarSystemTarget: isSolarSystemTarget,
    deriveEsaskyFovDeg: deriveEsaskyFovDeg,
    buildSolarSystemNoticeParagraphs: buildSolarSystemNoticeParagraphs,
  };
});
