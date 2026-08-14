"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");
const fs = require("node:fs");

const SpectrumGallery = require("../../app/static/lib/spectrum_gallery.js");
const { loadApp } = require("./app_loader");

const REGISTRY_JSON = path.join(__dirname, "..", "..", "app", "data", "spectrum_gallery_registry.json");
const JS_MIRROR = path.join(__dirname, "..", "..", "app", "static", "lib", "spectrum_gallery_registry.js");

const CRAB = {
  name: "Crab Nebula",
  object_category: "Nebula",
  object_type: "supernova remnant",
  ra_deg: 83.63,
  dec_deg: 22.01,
};

const JUPITER = {
  name: "Jupiter",
  object_category: "Planet",
  object_type: "planet",
  ra_deg: 10,
  dec_deg: 5,
};

const PHOBOS = {
  name: "Phobos",
  object_category: "Planet",
  object_type: "moon",
  ra_deg: 1,
  dec_deg: 2,
};

function crabViews() {
  return [
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
      id: "crab_2018_chandra_xray",
      title: "Crab Nebula in X-rays",
      wavelength: "X-ray",
      relevance: "exact_target",
      relevance_label: "Exact target",
      observatory: "Chandra X-ray Observatory",
      instrument: "ACIS",
      short_explanation: "False-color Chandra X-ray layer of the Crab.",
      image_url: "https://www.chandra.si.edu/photo/2018/crab/crab_xray.jpg",
      source_page_url: "https://www.chandra.si.edu/photo/2018/crab/",
      credits: "NASA/CXC/SAO",
    },
    {
      id: "crab_2018_hubble_optical",
      title: "Crab Nebula Optical (Hubble)",
      wavelength: "Visible",
      relevance: "exact_target",
      relevance_label: "Exact target",
      observatory: "Hubble Space Telescope",
      instrument: "HST",
      short_explanation: "Hubble optical layer of the Crab.",
      image_url: "https://www.chandra.si.edu/photo/2018/crab/crab_optical.jpg",
      source_page_url: "https://www.chandra.si.edu/photo/2018/crab/",
      credits: "NASA/STScI",
    },
  ];
}

function crabMatchPayload() {
  const views = crabViews();
  const planck = {
    id: "planck_2013_cmb_allsky",
    title: "Planck Cosmic Microwave Background",
    wavelength: "Microwave",
    relevance: "all_sky_context",
    relevance_label: "All-sky context",
    observatory: "Planck / ESA",
    instrument: "Planck HFI/LFI",
    short_explanation: "All-sky microwave context — not a photo of Crab.",
    image_url:
      "https://www.esa.int/var/esa/storage/images/esa_multimedia/images/2013/03/planck_cmb/12583930-4-eng-GB/Planck_CMB_article.jpg",
    source_page_url:
      "https://www.esa.int/Science_Exploration/Space_Science/Planck/Planck_and_the_cosmic_microwave_background",
    credits: "ESA and the Planck Collaboration",
  };
  return {
    ok: true,
    gallery_title: "Spectrum Gallery",
    gallery_subtitle: "See the universe in another light.",
    relevance: "exact_target",
    empty_exact_message: "No curated spectrum image is available for this target.",
    primary: views[0],
    available_views: views,
    options: [...views, planck],
    matched_count: views.length,
    all_sky_count: 1,
  };
}

function jupiterMatchPayload() {
  const primary = {
    id: "jupiter_2005_chandra_xray",
    title: "Jupiter in X-rays",
    wavelength: "X-ray",
    relevance: "exact_target",
    relevance_label: "Exact target",
    observatory: "Chandra X-ray Observatory",
    instrument: "ACIS",
    short_explanation: "Chandra X-ray image of Jupiter.",
    image_url: "https://www.chandra.si.edu/photo/2005/jupiter/jupiter_xray.jpg",
    source_page_url: "https://www.chandra.si.edu/photo/2005/jupiter/",
    credits: "NASA/CXC/SwRI",
  };
  return {
    ok: true,
    gallery_title: "Spectrum Gallery",
    gallery_subtitle: "See the universe in another light.",
    relevance: "exact_target",
    empty_exact_message: "No curated spectrum image is available for this target.",
    primary,
    available_views: [primary],
    options: [
      primary,
      {
        id: "planck_2013_cmb_allsky",
        title: "Planck Cosmic Microwave Background",
        wavelength: "Microwave",
        relevance: "all_sky_context",
        relevance_label: "All-sky context",
        observatory: "Planck / ESA",
        instrument: "Planck HFI/LFI",
        short_explanation: "All-sky microwave context.",
        image_url:
          "https://www.esa.int/var/esa/storage/images/esa_multimedia/images/2013/03/planck_cmb/12583930-4-eng-GB/Planck_CMB_article.jpg",
        source_page_url:
          "https://www.esa.int/Science_Exploration/Space_Science/Planck/Planck_and_the_cosmic_microwave_background",
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
  assert.equal(registry.entries.filter((e) => e.enabled).length, 23);
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

test("multi-view selector appears only for multiple exact views and excludes Planck", async () => {
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
  const buttons = app.el.spectrumGallerySelectors.querySelectorAll("button");
  assert.equal(buttons.length, 3);
  assert.equal(app.el.spectrumGalleryAvailable.hidden, false);
  const labels = Array.from(buttons).map((btn) => btn.textContent);
  assert.deepEqual(labels, ["Multiwavelength", "X-ray", "Visible"]);
  assert.equal(labels.includes("Microwave"), false);
});

test("single-view exact target does not show Available views selector", async () => {
  const fetchImpl = async (url) => {
    const href = String(url);
    if (href.startsWith("/api/spectrum-gallery-registry")) {
      return { ok: true, json: async () => registryPayload() };
    }
    if (href.startsWith("/api/spectrum-gallery-match")) {
      return { ok: true, json: async () => jupiterMatchPayload() };
    }
    return { ok: true, json: async () => ({ connected: true }) };
  };
  const { exports: app } = loadApp(fetchImpl);
  app.state.onlineMode = true;
  await app.syncSpectrumGallery(JUPITER);
  assert.equal(app.el.spectrumGalleryAvailable.hidden, true);
  assert.equal(app.el.spectrumGallerySelectors.querySelectorAll("button").length, 0);
  assert.equal(app.el.spectrumGalleryImage.getAttribute("src"), jupiterMatchPayload().primary.image_url);
});

test("switching views updates image metadata and does not preload others", async () => {
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
  const beforeTarget = { ...CRAB };
  app.state.currentTarget = beforeTarget;
  await app.syncSpectrumGallery(CRAB);
  const xray = crabViews()[1];
  app.selectSpectrumGalleryView(xray);
  assert.equal(app.el.spectrumGalleryImage.getAttribute("src"), xray.image_url);
  assert.match(app.el.spectrumGalleryWavelength.textContent, /X-ray/);
  assert.match(app.el.spectrumGalleryObservatory.textContent, /Chandra/);
  assert.match(app.el.spectrumGalleryCredits.textContent, /NASA\/CXC\/SAO/);
  assert.equal(app.el.spectrumGallerySourceLink.getAttribute("href"), xray.source_page_url);
  assert.equal(app.state.currentTarget, beforeTarget);
  assert.equal(app.state.currentTarget.name, "Crab Nebula");
});

test("rapid view switch keeps the latest selected image", async () => {
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
  const [multi, xray, optical] = crabViews();
  app.selectSpectrumGalleryView(xray);
  app.selectSpectrumGalleryView(optical);
  assert.equal(app.el.spectrumGalleryImage.getAttribute("src"), optical.image_url);
  assert.match(app.el.spectrumGalleryWavelength.textContent, /Visible/);
  assert.notEqual(app.el.spectrumGalleryImage.getAttribute("src"), multi.image_url);
  assert.notEqual(app.el.spectrumGalleryImage.getAttribute("src"), xray.image_url);
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
      payload.primary = payload.options[payload.options.length - 1];
      payload.available_views = [];
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
  assert.equal(app.el.spectrumGalleryAvailable.hidden, true);
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
      payload.primary.short_explanation = "<script>alert(1)</script>";
      payload.available_views[0] = payload.primary;
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
  const url = SpectrumGallery.buildMatchUrl("Virgo Galaxy", "Virgo Galaxy", "M 87 - NGC 4486", true);
  assert.match(url, /catalogue_designations=M\+87/);
  assert.match(url, /allow_all_sky=1/);
});

test("view button labels disambiguate duplicate wavelengths", () => {
  const siblings = [
    { wavelength: "Infrared", observatory: "Spitzer Space Telescope" },
    { wavelength: "Infrared", observatory: "Hubble Space Telescope" },
  ];
  assert.equal(SpectrumGallery.viewButtonLabel(siblings[0], siblings), "Spitzer Infrared");
  assert.equal(SpectrumGallery.viewButtonLabel(siblings[1], siblings), "Hubble Infrared");
  assert.equal(
    SpectrumGallery.viewButtonLabel({ wavelength: "X-ray", observatory: "Chandra" }, siblings),
    "X-ray"
  );
});
