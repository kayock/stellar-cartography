/* solar_system_media_registry.js
 *
 * Browser/Node export of the Solar System NASA public-media registry.
 * Keep in sync with app/data/solar_system_media_registry.json (parity tested).
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.SolarSystemMediaRegistry = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var REGISTRY = {
  "version": 1,
  "result_type": "public_media_asset",
  "media_label": "NASA public archive media",
  "entries": [
    {
      "id": "sun",
      "display_name": "Sun",
      "aliases": [
        "sun",
        "sol",
        "the sun"
      ],
      "parent_body": null,
      "target_class": "star",
      "moving_object": true,
      "search_terms": [
        "Sun solar photosphere",
        "SDO Sun"
      ],
      "relevance_terms": [
        "sun",
        "solar"
      ],
      "context_terms": [
        "solar",
        "photosphere",
        "corona",
        "heliosphere",
        "sdo",
        "soho",
        "stereo",
        "parker"
      ],
      "generic_guard": true
    },
    {
      "id": "mercury",
      "display_name": "Mercury",
      "aliases": [
        "mercury"
      ],
      "parent_body": null,
      "target_class": "planet",
      "moving_object": true,
      "search_terms": [
        "Mercury planet",
        "Mercury MESSENGER"
      ],
      "relevance_terms": [
        "mercury"
      ],
      "context_terms": [
        "planet",
        "messenger",
        "bepi",
        "mariner"
      ],
      "generic_guard": false
    },
    {
      "id": "venus",
      "display_name": "Venus",
      "aliases": [
        "venus"
      ],
      "parent_body": null,
      "target_class": "planet",
      "moving_object": true,
      "search_terms": [
        "Venus planet",
        "Venus Magellan"
      ],
      "relevance_terms": [
        "venus"
      ],
      "context_terms": [],
      "generic_guard": false
    },
    {
      "id": "earth",
      "display_name": "Earth",
      "aliases": [
        "earth",
        "terra"
      ],
      "parent_body": null,
      "target_class": "planet",
      "moving_object": true,
      "search_terms": [
        "Earth planet from space",
        "Earth Terra"
      ],
      "relevance_terms": [
        "earth",
        "terra"
      ],
      "context_terms": [
        "planet",
        "terra",
        "terrestrial",
        "from space",
        "apollo",
        "goes",
        "dscovr"
      ],
      "generic_guard": true
    },
    {
      "id": "moon",
      "display_name": "Moon",
      "aliases": [
        "moon",
        "luna",
        "the moon"
      ],
      "parent_body": "earth",
      "target_class": "moon",
      "moving_object": true,
      "search_terms": [
        "Moon Luna LRO",
        "Moon nearside"
      ],
      "relevance_terms": [
        "moon",
        "luna",
        "lunar"
      ],
      "context_terms": [
        "lunar",
        "luna",
        "apollo",
        "lro",
        "crater",
        "nearside",
        "mare",
        "selen"
      ],
      "generic_guard": true
    },
    {
      "id": "mars",
      "display_name": "Mars",
      "aliases": [
        "mars"
      ],
      "parent_body": null,
      "target_class": "planet",
      "moving_object": true,
      "search_terms": [
        "Mars planet",
        "Mars rover"
      ],
      "relevance_terms": [
        "mars"
      ],
      "context_terms": [],
      "generic_guard": false
    },
    {
      "id": "jupiter",
      "display_name": "Jupiter",
      "aliases": [
        "jupiter"
      ],
      "parent_body": null,
      "target_class": "planet",
      "moving_object": true,
      "search_terms": [
        "Jupiter planet",
        "Jupiter"
      ],
      "relevance_terms": [
        "jupiter"
      ],
      "context_terms": [],
      "generic_guard": false
    },
    {
      "id": "saturn",
      "display_name": "Saturn",
      "aliases": [
        "saturn"
      ],
      "parent_body": null,
      "target_class": "planet",
      "moving_object": true,
      "search_terms": [
        "Saturn planet",
        "Saturn"
      ],
      "relevance_terms": [
        "saturn"
      ],
      "context_terms": [],
      "generic_guard": false
    },
    {
      "id": "uranus",
      "display_name": "Uranus",
      "aliases": [
        "uranus"
      ],
      "parent_body": null,
      "target_class": "planet",
      "moving_object": true,
      "search_terms": [
        "Uranus planet",
        "Uranus Voyager"
      ],
      "relevance_terms": [
        "uranus"
      ],
      "context_terms": [],
      "generic_guard": false
    },
    {
      "id": "neptune",
      "display_name": "Neptune",
      "aliases": [
        "neptune"
      ],
      "parent_body": null,
      "target_class": "planet",
      "moving_object": true,
      "search_terms": [
        "Neptune planet",
        "Neptune Voyager"
      ],
      "relevance_terms": [
        "neptune"
      ],
      "context_terms": [],
      "generic_guard": false
    },
    {
      "id": "pluto",
      "display_name": "Pluto",
      "aliases": [
        "pluto"
      ],
      "parent_body": null,
      "target_class": "dwarf_planet",
      "moving_object": true,
      "search_terms": [
        "Pluto New Horizons",
        "Pluto dwarf planet"
      ],
      "relevance_terms": [
        "pluto"
      ],
      "context_terms": [],
      "generic_guard": false
    },
    {
      "id": "ceres",
      "display_name": "Ceres",
      "aliases": [
        "ceres",
        "1 ceres"
      ],
      "parent_body": null,
      "target_class": "dwarf_planet",
      "moving_object": true,
      "search_terms": [
        "Ceres dwarf planet",
        "Ceres Dawn"
      ],
      "relevance_terms": [
        "ceres"
      ],
      "context_terms": [],
      "generic_guard": false
    },
    {
      "id": "eris",
      "display_name": "Eris",
      "aliases": [
        "eris",
        "136199 eris"
      ],
      "parent_body": null,
      "target_class": "dwarf_planet",
      "moving_object": true,
      "search_terms": [
        "Eris dwarf planet",
        "Eris Kuiper"
      ],
      "relevance_terms": [
        "eris"
      ],
      "context_terms": [
        "dwarf",
        "kuiper",
        "dysnomia"
      ],
      "generic_guard": false
    },
    {
      "id": "haumea",
      "display_name": "Haumea",
      "aliases": [
        "haumea",
        "136108 haumea"
      ],
      "parent_body": null,
      "target_class": "dwarf_planet",
      "moving_object": true,
      "search_terms": [
        "Haumea dwarf planet",
        "Haumea Kuiper"
      ],
      "relevance_terms": [
        "haumea"
      ],
      "context_terms": [],
      "generic_guard": false
    },
    {
      "id": "makemake",
      "display_name": "Makemake",
      "aliases": [
        "makemake",
        "136472 makemake"
      ],
      "parent_body": null,
      "target_class": "dwarf_planet",
      "moving_object": true,
      "search_terms": [
        "Makemake dwarf planet",
        "Makemake Kuiper"
      ],
      "relevance_terms": [
        "makemake"
      ],
      "context_terms": [],
      "generic_guard": false
    },
    {
      "id": "phobos",
      "display_name": "Phobos",
      "aliases": [
        "phobos"
      ],
      "parent_body": "mars",
      "target_class": "moon",
      "moving_object": true,
      "search_terms": [
        "Phobos moon Mars",
        "Phobos Mars"
      ],
      "relevance_terms": [
        "phobos"
      ],
      "context_terms": [
        "mars",
        "moon",
        "satellite"
      ],
      "generic_guard": false
    },
    {
      "id": "deimos",
      "display_name": "Deimos",
      "aliases": [
        "deimos"
      ],
      "parent_body": "mars",
      "target_class": "moon",
      "moving_object": true,
      "search_terms": [
        "Deimos moon Mars",
        "Deimos Mars"
      ],
      "relevance_terms": [
        "deimos"
      ],
      "context_terms": [
        "mars",
        "moon",
        "satellite"
      ],
      "generic_guard": false
    },
    {
      "id": "io",
      "display_name": "Io",
      "aliases": [
        "io"
      ],
      "parent_body": "jupiter",
      "target_class": "moon",
      "moving_object": true,
      "search_terms": [
        "Io moon Jupiter",
        "Io Galileo"
      ],
      "relevance_terms": [
        "io"
      ],
      "context_terms": [
        "jupiter",
        "moon",
        "galilean",
        "satellite",
        "volcan"
      ],
      "generic_guard": false
    },
    {
      "id": "europa",
      "display_name": "Europa",
      "aliases": [
        "europa"
      ],
      "parent_body": "jupiter",
      "target_class": "moon",
      "moving_object": true,
      "search_terms": [
        "Europa moon Jupiter",
        "Europa Galileo"
      ],
      "relevance_terms": [
        "europa"
      ],
      "context_terms": [
        "jupiter",
        "moon",
        "galilean",
        "satellite"
      ],
      "generic_guard": false
    },
    {
      "id": "ganymede",
      "display_name": "Ganymede",
      "aliases": [
        "ganymede"
      ],
      "parent_body": "jupiter",
      "target_class": "moon",
      "moving_object": true,
      "search_terms": [
        "Ganymede moon Jupiter",
        "Ganymede Galileo"
      ],
      "relevance_terms": [
        "ganymede"
      ],
      "context_terms": [
        "jupiter",
        "moon",
        "galilean",
        "satellite"
      ],
      "generic_guard": false
    },
    {
      "id": "callisto",
      "display_name": "Callisto",
      "aliases": [
        "callisto"
      ],
      "parent_body": "jupiter",
      "target_class": "moon",
      "moving_object": true,
      "search_terms": [
        "Callisto moon Jupiter",
        "Callisto Galileo"
      ],
      "relevance_terms": [
        "callisto"
      ],
      "context_terms": [
        "jupiter",
        "moon",
        "galilean",
        "satellite"
      ],
      "generic_guard": false
    },
    {
      "id": "titan",
      "display_name": "Titan",
      "aliases": [
        "titan"
      ],
      "parent_body": "saturn",
      "target_class": "moon",
      "moving_object": true,
      "search_terms": [
        "Titan moon Saturn",
        "Titan Cassini"
      ],
      "relevance_terms": [
        "titan"
      ],
      "context_terms": [
        "saturn",
        "moon",
        "cassini",
        "satellite"
      ],
      "generic_guard": false
    },
    {
      "id": "enceladus",
      "display_name": "Enceladus",
      "aliases": [
        "enceladus"
      ],
      "parent_body": "saturn",
      "target_class": "moon",
      "moving_object": true,
      "search_terms": [
        "Enceladus moon Saturn",
        "Enceladus Cassini"
      ],
      "relevance_terms": [
        "enceladus"
      ],
      "context_terms": [
        "saturn",
        "moon",
        "cassini",
        "satellite"
      ],
      "generic_guard": false
    },
    {
      "id": "rhea",
      "display_name": "Rhea",
      "aliases": [
        "rhea"
      ],
      "parent_body": "saturn",
      "target_class": "moon",
      "moving_object": true,
      "search_terms": [
        "Rhea moon Saturn",
        "Rhea Cassini"
      ],
      "relevance_terms": [
        "rhea"
      ],
      "context_terms": [
        "saturn",
        "moon",
        "cassini",
        "satellite"
      ],
      "generic_guard": false
    },
    {
      "id": "iapetus",
      "display_name": "Iapetus",
      "aliases": [
        "iapetus"
      ],
      "parent_body": "saturn",
      "target_class": "moon",
      "moving_object": true,
      "search_terms": [
        "Iapetus moon Saturn",
        "Iapetus Cassini"
      ],
      "relevance_terms": [
        "iapetus"
      ],
      "context_terms": [
        "saturn",
        "moon",
        "cassini",
        "satellite"
      ],
      "generic_guard": false
    },
    {
      "id": "mimas",
      "display_name": "Mimas",
      "aliases": [
        "mimas"
      ],
      "parent_body": "saturn",
      "target_class": "moon",
      "moving_object": true,
      "search_terms": [
        "Mimas moon Saturn",
        "Mimas Cassini"
      ],
      "relevance_terms": [
        "mimas"
      ],
      "context_terms": [
        "saturn",
        "moon",
        "cassini",
        "satellite"
      ],
      "generic_guard": false
    },
    {
      "id": "miranda",
      "display_name": "Miranda",
      "aliases": [
        "miranda"
      ],
      "parent_body": "uranus",
      "target_class": "moon",
      "moving_object": true,
      "search_terms": [
        "Miranda moon Uranus",
        "Miranda Voyager"
      ],
      "relevance_terms": [
        "miranda"
      ],
      "context_terms": [
        "uranus",
        "moon",
        "voyager",
        "satellite"
      ],
      "generic_guard": false
    },
    {
      "id": "ariel",
      "display_name": "Ariel",
      "aliases": [
        "ariel"
      ],
      "parent_body": "uranus",
      "target_class": "moon",
      "moving_object": true,
      "search_terms": [
        "Ariel moon Uranus",
        "Ariel Voyager"
      ],
      "relevance_terms": [
        "ariel"
      ],
      "context_terms": [
        "uranus",
        "moon",
        "voyager",
        "satellite"
      ],
      "generic_guard": false
    },
    {
      "id": "umbriel",
      "display_name": "Umbriel",
      "aliases": [
        "umbriel"
      ],
      "parent_body": "uranus",
      "target_class": "moon",
      "moving_object": true,
      "search_terms": [
        "Umbriel moon Uranus",
        "Umbriel Voyager"
      ],
      "relevance_terms": [
        "umbriel"
      ],
      "context_terms": [
        "uranus",
        "moon",
        "voyager",
        "satellite"
      ],
      "generic_guard": false
    },
    {
      "id": "titania",
      "display_name": "Titania",
      "aliases": [
        "titania"
      ],
      "parent_body": "uranus",
      "target_class": "moon",
      "moving_object": true,
      "search_terms": [
        "Titania moon Uranus",
        "Titania Voyager"
      ],
      "relevance_terms": [
        "titania"
      ],
      "context_terms": [
        "uranus",
        "moon",
        "voyager",
        "satellite"
      ],
      "generic_guard": false
    },
    {
      "id": "oberon",
      "display_name": "Oberon",
      "aliases": [
        "oberon"
      ],
      "parent_body": "uranus",
      "target_class": "moon",
      "moving_object": true,
      "search_terms": [
        "Oberon moon Uranus",
        "Oberon Voyager"
      ],
      "relevance_terms": [
        "oberon"
      ],
      "context_terms": [
        "uranus",
        "moon",
        "voyager",
        "satellite"
      ],
      "generic_guard": false
    },
    {
      "id": "triton",
      "display_name": "Triton",
      "aliases": [
        "triton"
      ],
      "parent_body": "neptune",
      "target_class": "moon",
      "moving_object": true,
      "search_terms": [
        "Triton moon Neptune",
        "Triton Voyager"
      ],
      "relevance_terms": [
        "triton"
      ],
      "context_terms": [
        "neptune",
        "moon",
        "voyager",
        "satellite"
      ],
      "generic_guard": false
    },
    {
      "id": "charon",
      "display_name": "Charon",
      "aliases": [
        "charon"
      ],
      "parent_body": "pluto",
      "target_class": "moon",
      "moving_object": true,
      "search_terms": [
        "Charon moon Pluto",
        "Charon New Horizons"
      ],
      "relevance_terms": [
        "charon"
      ],
      "context_terms": [
        "pluto",
        "moon",
        "satellite",
        "new horizons"
      ],
      "generic_guard": false
    }
  ]
};

  function loadRegistry() {
    return REGISTRY;
  }

  function entriesById() {
    var map = {};
    (REGISTRY.entries || []).forEach(function (entry) {
      if (entry && entry.id) map[entry.id] = entry;
    });
    return map;
  }

  function getEntry(targetId) {
    if (typeof targetId !== "string" || !targetId) return null;
    return entriesById()[targetId.trim().toLowerCase()] || null;
  }

  function normalizeMediaTargetId(raw) {
    if (typeof raw !== "string" || !raw) return null;
    var key = raw.trim().toLowerCase();
    var byId = entriesById();
    if (byId[key]) return key;
    var candidates = [];
    Object.keys(byId).sort().forEach(function (entryId) {
      var aliases = byId[entryId].aliases || [];
      aliases.forEach(function (alias) {
        if (typeof alias !== "string") return;
        var aliasKey = alias.trim().toLowerCase();
        if (aliasKey === key) {
          candidates.push({ len: aliasKey.length, id: entryId });
        }
      });
    });
    if (!candidates.length) return null;
    candidates.sort(function (a, b) {
      if (b.len !== a.len) return b.len - a.len;
      return a.id < b.id ? -1 : a.id > b.id ? 1 : 0;
    });
    return candidates[0].id;
  }

  function displayNameForId(id) {
    var entry = getEntry(id);
    return entry ? entry.display_name : id;
  }

  function mediaLabel() {
    return REGISTRY.media_label || "NASA public archive media";
  }

  function resultType() {
    return REGISTRY.result_type || "public_media_asset";
  }

  function emptyResultMessage() {
    return "No relevant NASA public-media result was returned for this target.";
  }

  return {
    REGISTRY: REGISTRY,
    loadRegistry: loadRegistry,
    entriesById: entriesById,
    getEntry: getEntry,
    normalizeMediaTargetId: normalizeMediaTargetId,
    displayNameForId: displayNameForId,
    mediaLabel: mediaLabel,
    resultType: resultType,
    emptyResultMessage: emptyResultMessage,
  };
});
