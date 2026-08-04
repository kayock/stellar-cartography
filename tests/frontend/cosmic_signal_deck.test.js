"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");
const fs = require("node:fs");

const CosmicSignalDeck = require("../../app/static/lib/cosmic_signal_deck.js");
const { loadApp, fireAndFlush } = require("./app_loader");

const REGISTRY_JSON = path.join(__dirname, "..", "..", "app", "data", "cosmic_signal_registry.json");
const JS_MIRROR = path.join(__dirname, "..", "..", "app", "static", "lib", "cosmic_signal_registry.js");

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

const STAR = {
  name: "Sirius",
  object_category: "Star",
  object_type: "star",
  ra_deg: 101.28,
  dec_deg: -16.71,
};

function crabMatchPayload() {
  return {
    ok: true,
    relevance: "exact_target",
    empty_exact_message: "No exact curated signal is available for this target.",
    deck_title: "Cosmic Signal Deck",
    deck_subtitle: "Listen to the data. See how we know.",
    redirect_limitation_notice: "Slice 1 validates the initial HTTPS media URL host only.",
    primary: {
      id: "crab_nebula_chandra_sonification",
      title: "Crab Nebula Sonification",
      relevance: "exact_target",
      media_type: "data_sonification",
      conversion_method: "Left-to-right scan",
      mapping_explanation: "Brightness maps to loudness.",
      what_it_does_not_prove: "Not a microphone recording.",
      short_explanation: "A data sonification of the Crab Nebula.",
      observatories: ["Chandra X-ray Observatory"],
      spacecraft: ["Chandra"],
      instruments: ["Chandra X-ray"],
      media_kind: "video",
      media_url: "https://www.chandra.si.edu/sound/sounds/crab_all.mp4",
      source_page_url: "https://www.chandra.si.edu/sound/crab.html",
      poster_url: "https://www.chandra.si.edu/sound/images/crab_all.jpg",
      credits: "Chandra X-ray Center",
      attribution: "CXC / NASA",
    },
    featured: [],
  };
}

function featuredPayload() {
  const base = crabMatchPayload();
  base.relevance = "general_featured";
  base.primary = {
    ...base.primary,
    id: "voyager1_interstellar_plasma_pia17045",
    title: "Voyager 1 Interstellar Plasma Waves",
    relevance: "general_featured",
    media_type: "data_audification",
    media_url: "https://assets.science.nasa.gov/content/dam/science/psd/photojournal/pia/pia17/pia17045/PIA17045_20130906-640.mp4",
    source_page_url: "https://www.jpl.nasa.gov/images/pia17045-voyager-captures-sounds-of-interstellar-space/",
    poster_url: "https://assets.science.nasa.gov/content/dam/science/psd/photojournal/pia/pia17/pia17045/PIA17045.jpg",
    credits: "NASA / JPL-Caltech",
  };
  base.featured = [base.primary];
  return base;
}

function registryPayload() {
  return {
    ok: true,
    registry: JSON.parse(fs.readFileSync(REGISTRY_JSON, "utf8")),
  };
}

test("only one registry JSON source exists", () => {
  assert.equal(fs.existsSync(REGISTRY_JSON), true);
  assert.equal(fs.existsSync(JS_MIRROR), false);
});

test("expanded registry keeps Slice 1 entries and fifteen enabled composites", () => {
  const registry = JSON.parse(fs.readFileSync(REGISTRY_JSON, "utf8"));
  const enabled = registry.entries.filter((e) => e.enabled);
  assert.equal(enabled.length, 15);
  const ids = new Set(enabled.map((e) => e.id));
  for (const id of [
    "voyager1_interstellar_plasma_pia17045",
    "vela_pulsar_chandra_sonification",
    "crab_nebula_chandra_sonification",
    "cassiopeia_a_chandra_sonification",
    "galactic_center_chandra_sonification",
    "msh_15_52_chandra_ixpe_sonification",
    "m74_chandra_webb_hubble_sonification",
    "sn_1987a_chandra_hubble_sonification",
    "m87_chandra_vla_sonification",
    "m31_multiwavelength_sonification",
    "jupiter_chandra_hubble_sonification",
    "saturn_chandra_cassini_sonification",
    "uranus_chandra_keck_sonification",
    "southern_ring_nebula_jwst_sonification",
    "stephans_quintet_chandra_webb_sonification",
  ]) {
    assert.equal(ids.has(id), true, id);
  }
  const voyager = enabled.find((e) => e.id === "voyager1_interstellar_plasma_pia17045");
  assert.equal(voyager.media_type, "data_audification");
  const mediaUrls = enabled.map((e) => e.media_url);
  assert.equal(mediaUrls.length, new Set(mediaUrls).size);
});

test("media src absent before explicit playback and native controls remain", async () => {
  const calls = [];
  const fetchImpl = async (url) => {
    const href = String(url);
    calls.push(href);
    if (href.startsWith("/api/cosmic-signal-registry")) {
      return { ok: true, json: async () => registryPayload() };
    }
    if (href.startsWith("/api/cosmic-signal-match")) {
      return { ok: true, json: async () => crabMatchPayload() };
    }
    return { ok: true, json: async () => ({ connected: true }) };
  };

  const { exports: app } = loadApp(fetchImpl);
  app.state.onlineMode = true;
  await app.syncCosmicSignalDeck(CRAB);
  assert.equal(app.el.cosmicSignalVideo.getAttribute("src"), null);
  assert.equal(app.el.cosmicSignalAudio.getAttribute("src"), null);
  assert.equal(app.el.cosmicSignalVideo.controls, true);
  assert.equal(app.el.cosmicSignalAudio.controls, true);
  assert.equal(app.el.cosmicSignalVideo.preload, "none");
  assert.match(app.el.cosmicSignalRelevance.textContent, /Exact target/i);
  assert.doesNotMatch(app.el.cosmicSignalRelevance.className, /is-featured/);

  await fireAndFlush(app.el.cosmicSignalPlay, "click");
  assert.equal(app.el.cosmicSignalVideo.getAttribute("src"), crabMatchPayload().primary.media_url);
});

test("Online Mode off creates zero signal media or poster requests", async () => {
  let cosmicCalls = 0;
  const fetchImpl = async (url) => {
    if (String(url).includes("/api/cosmic-signal")) cosmicCalls += 1;
    return { ok: true, json: async () => ({ connected: true }) };
  };
  const { exports: app } = loadApp(fetchImpl);
  app.state.onlineMode = false;
  await app.syncCosmicSignalDeck(CRAB);
  assert.equal(cosmicCalls, 0);
  assert.equal(app.el.cosmicSignalPoster.getAttribute("src"), null);
  assert.equal(app.el.cosmicSignalVideo.getAttribute("src"), null);
});

test("target switch clears media src and stale responses cannot overwrite", async () => {
  let releaseCrab;
  const crabGate = new Promise((resolve) => {
    releaseCrab = resolve;
  });
  const fetchImpl = async (url) => {
    const href = String(url);
    if (href.startsWith("/api/cosmic-signal-registry")) {
      return { ok: true, json: async () => registryPayload() };
    }
    if (href.includes("name=Crab")) {
      await crabGate;
      return { ok: true, json: async () => crabMatchPayload() };
    }
    if (href.includes("name=Phobos")) {
      return { ok: true, json: async () => featuredPayload() };
    }
    return { ok: true, json: async () => ({ connected: true }) };
  };

  const { exports: app } = loadApp(fetchImpl);
  app.state.onlineMode = true;
  const crabPromise = app.syncCosmicSignalDeck(CRAB);
  await new Promise((r) => setTimeout(r, 0));
  await app.syncCosmicSignalDeck(PHOBOS);
  assert.equal(app.el.cosmicSignalVideo.getAttribute("src"), null);
  assert.match(app.el.cosmicSignalRelevance.textContent, /Featured/i);
  assert.match(app.el.cosmicSignalBody.className, /is-featured/);

  releaseCrab();
  await crabPromise;
  await new Promise((r) => setTimeout(r, 0));
  assert.match(app.el.cosmicSignalRelevance.textContent, /Featured/i);
  assert.doesNotMatch(app.el.cosmicSignalStatus.textContent, /Crab Nebula Sonification/);
});

test("featured fallback never receives exact-target styling", async () => {
  const fetchImpl = async (url) => {
    const href = String(url);
    if (href.startsWith("/api/cosmic-signal-registry")) {
      return { ok: true, json: async () => registryPayload() };
    }
    if (href.startsWith("/api/cosmic-signal-match")) {
      return { ok: true, json: async () => featuredPayload() };
    }
    return { ok: true, json: async () => ({ connected: true }) };
  };
  const { exports: app } = loadApp(fetchImpl);
  app.state.onlineMode = true;
  await app.syncCosmicSignalDeck(PHOBOS);
  assert.match(app.el.cosmicSignalRelevance.className, /is-featured/);
  assert.doesNotMatch(app.el.cosmicSignalRelevance.textContent, /Exact target/i);
  assert.match(app.el.cosmicSignalStatus.textContent, /Featured fallback/i);
});

test("poster failure does not block playback", async () => {
  const fetchImpl = async (url) => {
    const href = String(url);
    if (href.startsWith("/api/cosmic-signal-registry")) {
      return { ok: true, json: async () => registryPayload() };
    }
    if (href.startsWith("/api/cosmic-signal-match")) {
      const payload = crabMatchPayload();
      payload.primary.poster_url = "https://evil.example/bad.jpg";
      payload.primary.thumbnail_url = "https://evil.example/bad.jpg";
      return { ok: true, json: async () => payload };
    }
    return { ok: true, json: async () => ({ connected: true }) };
  };
  const { exports: app } = loadApp(fetchImpl);
  app.state.onlineMode = true;
  await app.syncCosmicSignalDeck(CRAB);
  assert.equal(app.el.cosmicSignalPoster.hidden, true);
  assert.equal(app.el.cosmicSignalPlayerWrap.hidden, false);
  await fireAndFlush(app.el.cosmicSignalPlay, "click");
  assert.equal(app.el.cosmicSignalVideo.getAttribute("src"), crabMatchPayload().primary.media_url);
});

test("safe text rendering for explanations and credits", async () => {
  const fetchImpl = async (url) => {
    const href = String(url);
    if (href.startsWith("/api/cosmic-signal-registry")) {
      return { ok: true, json: async () => registryPayload() };
    }
    if (href.startsWith("/api/cosmic-signal-match")) {
      const payload = crabMatchPayload();
      payload.primary.credits = '<img src=x onerror="alert(1)">';
      payload.primary.mapping_explanation = '<script>alert(1)</script>';
      return { ok: true, json: async () => payload };
    }
    return { ok: true, json: async () => ({ connected: true }) };
  };
  const { exports: app } = loadApp(fetchImpl);
  app.state.onlineMode = true;
  await app.syncCosmicSignalDeck(CRAB);
  assert.match(app.el.cosmicSignalCredits.textContent, /<img src=x/);
  assert.equal(app.el.cosmicSignalCredits.querySelectorAll("img").length, 0);
  assert.equal(app.el.cosmicSignalHearing.querySelectorAll("script").length, 0);
});

test("Stop clears media src", async () => {
  const fetchImpl = async (url) => {
    const href = String(url);
    if (href.startsWith("/api/cosmic-signal-registry")) {
      return { ok: true, json: async () => registryPayload() };
    }
    if (href.startsWith("/api/cosmic-signal-match")) {
      return { ok: true, json: async () => crabMatchPayload() };
    }
    return { ok: true, json: async () => ({ connected: true }) };
  };
  const { exports: app } = loadApp(fetchImpl);
  app.state.onlineMode = true;
  await app.syncCosmicSignalDeck(CRAB);
  await fireAndFlush(app.el.cosmicSignalPlay, "click");
  assert.ok(app.el.cosmicSignalVideo.getAttribute("src"));
  await fireAndFlush(app.el.cosmicSignalStop, "click");
  assert.equal(app.el.cosmicSignalVideo.getAttribute("src"), null);
});

test("MAST and planetary paths remain independent of signal errors", async () => {
  let planetaryCalls = 0;
  let discoveryCalls = 0;
  const fetchImpl = async (url) => {
    const href = String(url);
    if (href.startsWith("/api/planetary-image")) {
      planetaryCalls += 1;
      return { ok: true, json: async () => ({ status: "unsupported" }) };
    }
    if (href.startsWith("/api/discovery")) {
      discoveryCalls += 1;
      return { ok: true, json: async () => ({ ok: true, items: [], query_outcomes: [] }) };
    }
    if (href.startsWith("/api/cosmic-signal")) {
      throw new Error("signal failure");
    }
    return { ok: true, json: async () => ({ connected: true }) };
  };
  const { exports: app } = loadApp(fetchImpl);
  app.state.onlineMode = true;
  await app.syncCosmicSignalDeck(STAR);
  assert.match(app.el.cosmicSignalStatus.textContent, /Could not reach the local server/i);
  assert.equal(planetaryCalls, 0);
  assert.equal(discoveryCalls, 0);
});

test("URL helper rejects unsafe schemes and documents no redirect enforcement", () => {
  const hosts = new Set(["www.chandra.si.edu"]);
  assert.equal(CosmicSignalDeck.isAllowedUrl("javascript:alert(1)", hosts), false);
  assert.equal(CosmicSignalDeck.isAllowedUrl("data:text/plain,x", hosts), false);
  assert.equal(CosmicSignalDeck.isAllowedUrl("https://www.chandra.si.edu/a.mp4", hosts), true);
  const notice = crabMatchPayload().redirect_limitation_notice;
  assert.match(notice, /initial HTTPS/i);
});

test("match URL forwards catalogue designations for M87 handoff", () => {
  const url = CosmicSignalDeck.buildMatchUrl(
    "Virgo Galaxy",
    "Virgo Galaxy",
    true,
    "M 87 - NGC 4486 - PGC 41361 - UGC 7654 - Arp 152"
  );
  assert.match(url, /name=Virgo\+Galaxy/);
  assert.match(url, /catalogue_designations=M\+87/);
  assert.match(url, /NGC\+4486/);
  assert.match(url, /allow_featured=1/);
});

test("Play button is keyboard-activatable semantic control", () => {
  const { exports: app } = loadApp(async () => ({ ok: true, json: async () => ({}) }));
  assert.equal(app.el.cosmicSignalPlay.tagName, "BUTTON");
  assert.equal(app.el.cosmicSignalStop.tagName, "BUTTON");
  assert.equal(app.el.cosmicSignalPlay.type, "button");
});
