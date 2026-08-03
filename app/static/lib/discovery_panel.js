/* discovery_panel.js
 *
 * Pure helpers for the R0.5 Slice 1 discovery-panel skeleton.
 * Separates query_outcomes (provider status) from scientific items.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.DiscoveryPanel = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var FORBIDDEN_ABSENCE_PHRASES = [
    "no hubble",
    "no jwst",
    "no x-ray information exists",
    "information does not exist",
    "no infrared information exists",
    "no ultraviolet information exists",
  ];

  var DOMAIN_ORDER = [
    "visible",
    "infrared",
    "ultraviolet",
    "xray",
    "radio",
    "planetary_imagery",
    "catalogs_metadata",
    "contextual",
    "other",
  ];

  var DOMAIN_LABELS = {
    visible: "Visible",
    infrared: "Infrared",
    ultraviolet: "Ultraviolet",
    xray: "X-ray",
    radio: "Radio / other",
    planetary_imagery: "Planetary imagery",
    catalogs_metadata: "Catalogs and metadata",
    contextual: "Contextual information",
    other: "Other",
  };

  var MATCH_BASIS_LABELS = {
    exact_target_name: "Exact target name",
    alias_match: "Alias match",
    footprint_overlap: "Footprint overlap",
    resolved_position: "Resolved position",
    cone_candidate: "Positional cone candidate (not proof of target identity)",
  };

  function assertHonestText(text) {
    var lower = String(text || "").toLowerCase();
    for (var i = 0; i < FORBIDDEN_ABSENCE_PHRASES.length; i++) {
      if (lower.indexOf(FORBIDDEN_ABSENCE_PHRASES[i]) !== -1) return false;
    }
    return true;
  }

  function domainForItem(item) {
    var d = (item && item.wavelength_domain) || "other";
    return DOMAIN_LABELS[d] ? d : "other";
  }

  function groupItemsByDomain(items) {
    var groups = {};
    DOMAIN_ORDER.forEach(function (d) {
      groups[d] = [];
    });
    (items || []).forEach(function (item) {
      if (!item || !item.result_type) return;
      var d = domainForItem(item);
      groups[d].push(item);
    });
    return groups;
  }

  function outcomeSectionTitle(status) {
    if (status === "zero_results") return "No matching results from provider";
    if (status === "timeout") return "Provider timed out";
    if (status === "unavailable") return "Provider unavailable";
    if (status === "rate_limited") return "Provider rate-limited";
    if (status === "malformed_response") return "Malformed provider response";
    if (status === "unsupported") return "Target unsupported by provider";
    if (status === "ephemeris_required") return "Ephemeris required / moving target";
    if (status === "success") return "Successful queries";
    return status || "Query outcome";
  }

  function buildPanelViewModel(bundle) {
    bundle = bundle || {};
    var items = bundle.items || [];
    var outcomes = bundle.query_outcomes || [];
    var warnings = bundle.warnings || [];
    var notes = bundle.capability_notes || [];
    var groups = groupItemsByDomain(items);
    var domains = DOMAIN_ORDER.filter(function (d) {
      return groups[d].length > 0;
    }).map(function (d) {
      return {
        domain: d,
        label: DOMAIN_LABELS[d],
        items: groups[d],
      };
    });

    var statusOutcomes = outcomes.filter(function (o) {
      return o && o.query_status && o.query_status !== "success";
    });

    return {
      domains: domains,
      itemCount: items.length,
      statusOutcomes: statusOutcomes,
      warnings: warnings,
      capabilityNotes: notes,
      emptyMessage:
        items.length === 0
          ? "No scientific discovery items yet. Provider query outcomes are listed separately below."
          : null,
    };
  }

  function matchBasisLabel(basis) {
    return MATCH_BASIS_LABELS[basis] || basis || "unknown";
  }

  function summarizeItem(item) {
    if (!item) return "";
    var parts = [];
    if (item.summary) parts.push(item.summary);
    else {
      parts.push(item.source_or_mission || item.provider || "Provider");
      if (item.observation_id) parts.push("obs " + item.observation_id);
    }
    if (item.match_basis) parts.push("[" + matchBasisLabel(item.match_basis) + "]");
    return parts.join(" — ");
  }

  return {
    FORBIDDEN_ABSENCE_PHRASES: FORBIDDEN_ABSENCE_PHRASES,
    DOMAIN_ORDER: DOMAIN_ORDER,
    DOMAIN_LABELS: DOMAIN_LABELS,
    assertHonestText: assertHonestText,
    groupItemsByDomain: groupItemsByDomain,
    outcomeSectionTitle: outcomeSectionTitle,
    buildPanelViewModel: buildPanelViewModel,
    matchBasisLabel: matchBasisLabel,
    summarizeItem: summarizeItem,
  };
});
