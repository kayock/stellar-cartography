"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");
const DiscoveryPanel = require("../../app/static/lib/discovery_panel.js");
const ArchiveAvailability = require("../../app/static/lib/archive_availability.js");

test("panel separates items from query outcomes", () => {
  const view = DiscoveryPanel.buildPanelViewModel({
    items: [
      {
        result_type: "archive_observation",
        wavelength_domain: "visible",
        provider: "mast",
        source_or_mission: "Hubble",
        observation_id: "a1",
        match_basis: "exact_target_name",
        summary: "HST obs a1",
      },
    ],
    query_outcomes: [
      {
        query_status: "zero_results",
        provider: "mast",
        mission: "jwst_miri",
        result_type: null,
        message:
          "No matching observations were returned by this provider for this position and search radius.",
      },
    ],
    warnings: [],
    capability_notes: [],
  });
  assert.equal(view.itemCount, 1);
  assert.equal(view.domains.length, 1);
  assert.equal(view.domains[0].domain, "visible");
  assert.equal(view.statusOutcomes.length, 1);
  assert.equal(view.statusOutcomes[0].query_status, "zero_results");
  assert.ok(DiscoveryPanel.assertHonestText(view.statusOutcomes[0].message));
});

test("forbidden absence phrases rejected", () => {
  assert.equal(DiscoveryPanel.assertHonestText("No Hubble information exists"), false);
  assert.equal(
    DiscoveryPanel.assertHonestText(
      "No matching observations were returned by this provider for this position and search radius."
    ),
    true
  );
});

test("moving-object capability note surfaces in view model", () => {
  const note = "Historical archive coverage for this moving object was not evaluated.";
  const view = DiscoveryPanel.buildPanelViewModel({
    items: [],
    query_outcomes: [
      {
        query_status: "ephemeris_required",
        provider: "mast",
        message: note,
        result_type: null,
      },
    ],
    warnings: [],
    capability_notes: [note],
  });
  assert.ok(view.capabilityNotes.includes(note));
  assert.equal(view.statusOutcomes[0].query_status, "ephemeris_required");
});

test("cone candidate match basis label is non-proof wording", () => {
  const label = DiscoveryPanel.matchBasisLabel("cone_candidate");
  assert.match(label, /candidate/i);
  assert.match(label, /not proof/i);
});

test("discovery url builder does not use archive-availability path", () => {
  const url = ArchiveAvailability.buildDiscoveryApiUrl(
    { ra_deg: 10, dec_deg: 20, name: "M42" },
    ["hst"]
  );
  assert.match(url, /^\/api\/discovery\?/);
  assert.doesNotMatch(url, /archive-availability/);
});

test("badge adapter still maps discovery badge payloads", () => {
  const light = ArchiveAvailability.mapBadgePayloadToLight(
    { status: "confirmed", count: 2, observations: [] },
    "hst",
    null
  );
  assert.equal(light.state, ArchiveAvailability.STATE.CONFIRMED);
  const none = ArchiveAvailability.mapBadgePayloadToLight(
    { status: "no_coverage", count: 0 },
    "jwst_miri",
    null
  );
  assert.equal(none.state, ArchiveAvailability.STATE.NO_COVERAGE);
  const unavail = ArchiveAvailability.mapBadgePayloadToLight(
    { status: "unavailable" },
    "hst",
    null
  );
  assert.equal(unavail.state, ArchiveAvailability.STATE.UNAVAILABLE);
});
