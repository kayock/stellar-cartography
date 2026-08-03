"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");

const ImageryMatching = require(path.join(__dirname, "..", "..", "app", "static", "lib", "imagery_matching.js"));

function cfgFor(id) {
  const cfg = ImageryMatching.IMAGERY_BUTTONS.find((c) => c.id === id);
  assert.ok(cfg, `no button config for id=${id}`);
  return cfg;
}

test("HST ACS matches Hubble (accepts HST without requiring the word Hubble)", () => {
  const match = ImageryMatching.matchImageryLayer(cfgFor("hubble"), ["HST ACS", "DSS2 color"]);
  assert.equal(match, "HST ACS");
});

test("Hubble alias also accepts the literal word Hubble", () => {
  const match = ImageryMatching.matchImageryLayer(cfgFor("hubble"), ["Hubble Legacy Archive"]);
  assert.equal(match, "Hubble Legacy Archive");
});

test("Hubble prefers HST ACS when multiple HST layers exist", () => {
  const match = ImageryMatching.matchImageryLayer(cfgFor("hubble"), ["HST WFC3", "HST ACS", "Hubble outreach"]);
  assert.equal(match, "HST ACS");
});

test("XMM-Newton EPIC color matches X-ray, and is preferred among X-ray options", () => {
  const match = ImageryMatching.matchImageryLayer(cfgFor("xray"), ["ROSAT all-sky", "XMM-Newton EPIC color", "Chandra survey"]);
  assert.equal(match, "XMM-Newton EPIC color");
});

test("X-ray accepts any suitable option without requiring all alternatives together", () => {
  assert.equal(ImageryMatching.matchImageryLayer(cfgFor("xray"), ["Chandra deep field"]), "Chandra deep field");
  assert.equal(ImageryMatching.matchImageryLayer(cfgFor("xray"), ["eROSITA all-sky"]), "eROSITA all-sky");
});

test("AllWISE color matches WISE", () => {
  const match = ImageryMatching.matchImageryLayer(cfgFor("wise"), ["AllWISE color"]);
  assert.equal(match, "AllWISE color");
});

test("unrelated optical layers do not match JWST NIRCam", () => {
  const match = ImageryMatching.matchImageryLayer(cfgFor("jwst_nircam"), ["DSS2 color", "HST ACS", "AllWISE color"]);
  assert.equal(match, null);
});

test("JWST NIRCam requires both jwst and nircam tokens together", () => {
  assert.equal(ImageryMatching.matchImageryLayer(cfgFor("jwst_nircam"), ["JWST NIRCam mosaic"]), "JWST NIRCam mosaic");
  assert.equal(ImageryMatching.matchImageryLayer(cfgFor("jwst_nircam"), ["JWST MIRI mosaic"]), null);
});

test("an empty list returns no match", () => {
  assert.equal(ImageryMatching.matchImageryLayer(cfgFor("hubble"), []), null);
});

test("Herschel prefers a PACS RGB layer when present", () => {
  const match = ImageryMatching.matchImageryLayer(cfgFor("herschel"), ["Herschel SPIRE", "Herschel PACS RGB"]);
  assert.equal(match, "Herschel PACS RGB");
});

test("Spitzer accepts Spitzer or IRAC", () => {
  assert.equal(ImageryMatching.matchImageryLayer(cfgFor("spitzer"), ["Spitzer IRAC mosaic"]), "Spitzer IRAC mosaic");
  assert.equal(ImageryMatching.matchImageryLayer(cfgFor("spitzer"), ["IRAC 3.6um"]), "IRAC 3.6um");
});

test("Microwave accepts Planck", () => {
  assert.equal(ImageryMatching.matchImageryLayer(cfgFor("microwave"), ["Planck HFI 857GHz"]), "Planck HFI 857GHz");
});

test("looksLikeHipsListing recognizes array-shaped and per-category responses", () => {
  assert.equal(ImageryMatching.looksLikeHipsListing({ content: [{ name: "DSS2 color" }] }), true);
  assert.equal(ImageryMatching.looksLikeHipsListing({ content: { OPTICAL: [{ name: "DSS2 color" }] } }), true);
  assert.equal(ImageryMatching.looksLikeHipsListing({ content: { hipsName: "DSS2 color" } }), false);
  assert.equal(ImageryMatching.looksLikeHipsListing(null), false);
});

test("extractHipsNames pulls names out of string entries, object entries, and per-category maps", () => {
  const names = ImageryMatching.extractHipsNames({
    content: {
      OPTICAL: ["DSS2 color", { name: "HST ACS" }],
      XRAY: [{ hipsName: "XMM-Newton EPIC color" }],
    },
  });
  assert.deepEqual(names.sort(), ["DSS2 color", "HST ACS", "XMM-Newton EPIC color"].sort());
});
