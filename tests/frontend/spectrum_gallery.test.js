"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");
const fs = require("node:fs");

const SpectrumGallery = require("../../app/static/lib/spectrum_gallery.js");
const { loadApp, fireAndFlush } = require("./app_loader");

const REGISTRY_JSON = path.join(__dirname, "..", "..", "app", "data", "spectrum_gallery_registry.json");
const JS_MIRROR = path.join(__dirname, "..", "..", "app", "static", "lib", "spectrum_gallery_registry.js");

const CRAB = {
  name: "Crab Nebula",
  object_category: "Nebula",
  object_type: "supernova remnant",
  ra_deg: 83.63,
  dec_deg: 22.01,
};

const PHOBOS = {
  name: "Phobos",
  object_category: "Planet",
  object_type: "moon",
  ra_deg: 1,
  dec_deg: 2,
};

function crabMatchPayload() {
  return {
    ok: true,
    gallery_title: "Spectrum Gallery",
    gallery_subtitle: "See the universe in another light.",
    relevance: "exact_target",
    empty_exact_message: "No curated spectrum image is available for this target.",
    primary: {
      id: "crab_2018_chandra_hubble_spitzer",
      title: "Crab Nebula Multiwavelength Composite",
      wavelength: "Multiwavelength",
      relevance: "exact_target",
      relevance_label: "Exact target",
      observatory: "Chandra / Hubble / Spitzer",
      instrument: "ACIS + HST + Spitzer",
      short_explanation: "Official multiwavelength Crab Nebula image.",
      image_url: "https://www.chandra.si.edu/photo/2018/crab/crab.jpg",
      source_page_url: "https://www.chandra.si.edu/photo/2018/crab/",
      credits: "NASA/CXC/SAO",
    },
    options: [
      {
        id: "crab_2018_chandra_hubble_spitzer",
        title: "Crab Nebula Multiwavelength Composite",
        wavelength: "Multiwavelength",
        relevance: "exact_target",
        relevance_label: "Exact target",
        observatory: "Chandra / Hubble / Spitzer",
        instrument: "ACIS + HST + Spitzer",
        short_explanation: "Official multiwavelength Crab Nebula image.",
        image_url: "https://www.chandra.si.edu/photo/2018/crab/crab.jpg",
        source_page_url: "https://www.chandra.si.edu/photo/2018/crab/",
        credits: "NASA/CXC/SAO",
      },
      {
        id: "planck_2013_cmb_allsky",
        title: "Planck Cosmic Microwave Background",
        wavelength: "Microwave",
        relevance: "all_sky_context",
        relevance_label: "All-sky context",
        observatory: "Planck / ESA",
        instrument: "Planck HFI/LFI",
        short_explanation: "All-sky microwave context — not a photo of Crab.",
        image_url: "https://www.esa.int/var/esa/storage/images/esa_multimedia/images/2013/03/planck_cmb/12583930-4-eng-GB/Planck_CMB_article.jpg",
        source_page_url: "https://www.esa.int/Science_Exploration/Space_Science/Planck/Planck_and_the_cosmic_microwave_background",
        credits: "ESA and the Planck Collaboration",
      },
    ],
    matched_count: 1,
    all_sky_count: 1,
  };
}

function registryPayload() {
  return {
    ok: true,
    registry: JSON.parse(fs.readFileSync(REGISTRY_JSON, "utf8")),
  };
}

test("spectrum gallery uses a single JSON registry source", () => {
  assert.equal(fs.existsSync(REGISTRY_JSON), true);
  assert.equal(fs.existsSync(JS_MIRROR), false);
  const registry = JSON.parse(fs.readFileSync(REGISTRY_JSON, "utf8"));
  assert.equal(registry.entries.filter((e) => e.enabled).length, 10);
});

test("Online Mode off creates zero spectrum gallery requests", async () => {
  let spectrumCalls = 0;
  const fetchImpl = async (url) => {
    if (String(url).includes("/api/spectrum-gallery")) spectrumCalls += 1;
    return { ok: true, json: async () => ({ connected: true }) };
  };
  const { exports: app } = loadApp(fetchImpl);
  app.state.onlineMode = false;
  await app.syncSpectrumGallery(CRAB);
  assert.equal(spectrumCalls, 0);
  assert.equal(app.el.spectrumGalleryImage.getAttribute("src"), null);
});

test("selected image loads once and options do not preload other images", async () => {
  const fetchImpl = async (url) => {
    const href = String(url);
    if (href.startsWith("/api/spectrum-gallery-registry")) {
      return { ok: true, json: async () => registryPayload() };
    }
    if (href.startsWith("/api/spectrum-gallery-match")) {
      return { ok: true, json: async () => crabMatchPayload() };
    }
    return { ok: true, json: async () => ({ connected: true }) };
  };
  const { exports: app } = loadApp(fetchImpl);
  app.state.onlineMode = true;
  await app.syncSpectrumGallery(CRAB);
  assert.equal(app.el.spectrumGalleryImage.getAttribute("src"), crabMatchPayload().primary.image_url);
  assert.match(app.el.spectrumGalleryRelevance.textContent, /Exact target/i);
  assert.match(app.el.spectrumGalleryWavelength.textContent, /Multiwavelength/);
  assert.equal(app.el.spectrumGallerySelectors.querySelectorAll("button").length, 2);
  // Selector buttons are local UI only; no second image src is assigned until clicked.
  assert.equal(app.el.spectrumGalleryImageWrap.hidden, false);
});

test("target change clears stale spectrum image", async () => {
  let releaseCrab;
  const crabGate = new Promise((resolve) => {
    releaseCrab = resolve;
  });
  const fetchImpl = async (url) => {
    const href = String(url);
    if (href.startsWith("/api/spectrum-gallery-registry")) {
      return { ok: true, json: async () => registryPayload() };
    }
    if (href.includes("name=Crab")) {
      await crabGate;
      return { ok: true, json: async () => crabMatchPayload() };
    }
    if (href.includes("name=Phobos")) {
      const payload = crabMatchPayload();
      payload.relevance = "all_sky_context";
      payload.primary = payload.options[1];
      payload.matched_count = 0;
      return { ok: true, json: async () => payload };
    }
    return { ok: true, json: async () => ({ connected: true }) };
  };
  const { exports: app } = loadApp(fetchImpl);
  app.state.onlineMode = true;
  const crabPromise = app.syncSpectrumGallery(CRAB);
  await new Promise((r) => setTimeout(r, 0));
  await app.syncSpectrumGallery(PHOBOS);
  assert.match(app.el.spectrumGalleryRelevance.textContent, /All-sky context/i);
  assert.doesNotMatch(app.el.spectrumGalleryStatus.textContent, /Crab Nebula Multiwavelength/);
  releaseCrab();
  await crabPromise;
  await new Promise((r) => setTimeout(r, 0));
  assert.match(app.el.spectrumGalleryRelevance.textContent, /All-sky context/i);
});

test("safe text rendering for spectrum credits and explanations", async () => {
  const fetchImpl = async (url) => {
    const href = String(url);
    if (href.startsWith("/api/spectrum-gallery-registry")) {
      return { ok: true, json: async () => registryPayload() };
    }
    if (href.startsWith("/api/spectrum-gallery-match")) {
      const payload = crabMatchPayload();
      payload.primary.credits = '<img src=x onerror="alert(1)">';
      payload.primary.short_explanation = '<script>alert(1)</script>';
      payload.options[0] = payload.primary;
      return { ok: true, json: async () => payload };
    }
    return { ok: true, json: async () => ({ connected: true }) };
  };
  const { exports: app } = loadApp(fetchImpl);
  app.state.onlineMode = true;
  await app.syncSpectrumGallery(CRAB);
  assert.match(app.el.spectrumGalleryCredits.textContent, /<img src=x/);
  assert.equal(app.el.spectrumGalleryCredits.querySelectorAll("img").length, 0);
  assert.equal(app.el.spectrumGalleryExplanation.querySelectorAll("script").length, 0);
});

test("spectrum gallery failure leaves cosmic signal and discovery untouched", async () => {
  let cosmicCalls = 0;
  let discoveryCalls = 0;
  const fetchImpl = async (url) => {
    const href = String(url);
    if (href.startsWith("/api/cosmic-signal")) {
      cosmicCalls += 1;
      return { ok: true, json: async () => ({ ok: true, primary: null, featured: [] }) };
    }
    if (href.startsWith("/api/discovery")) {
      discoveryCalls += 1;
      return { ok: true, json: async () => ({ ok: true, items: [], query_outcomes: [] }) };
    }
    if (href.startsWith("/api/spectrum-gallery")) {
      throw new Error("spectrum failure");
    }
    return { ok: true, json: async () => ({ connected: true }) };
  };
  const { exports: app } = loadApp(fetchImpl);
  app.state.onlineMode = true;
  await app.syncSpectrumGallery(CRAB);
  assert.match(app.el.spectrumGalleryStatus.textContent, /Could not reach the local server/i);
  assert.equal(cosmicCalls, 0);
  assert.equal(discoveryCalls, 0);
});

test("spectrum match URL forwards catalogue designations", () => {
  const url = SpectrumGallery.buildMatchUrl(
    "Virgo Galaxy",
    "Virgo Galaxy",
    "M 87 - NGC 4486",
    true
  );
  assert.match(url, /catalogue_designations=M\+87/);
  assert.match(url, /allow_all_sky=1/);
});
