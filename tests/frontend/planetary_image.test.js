"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");
const fs = require("node:fs");

const PlanetaryImage = require(path.join(__dirname, "..", "..", "app", "static", "lib", "planetary_image.js"));
const SolarSystem = require(path.join(__dirname, "..", "..", "app", "static", "lib", "solar_system.js"));
const { loadApp, fireAndFlush } = require("./app_loader");

const FIXTURES = path.join(__dirname, "..", "fixtures", "sample_responses");

function loadFixture(name) {
  return JSON.parse(fs.readFileSync(path.join(FIXTURES, name), "utf8"));
}

const MOON = {
  name: "Moon",
  object_category: "Planet",
  object_type: "moon",
};

const JUPITER = {
  name: "Jupiter",
  object_category: "Planet",
  object_type: "planet",
};

const SATURN = {
  name: "Saturn",
  object_category: "Planet",
  object_type: "planet",
};

const MARS = {
  name: "Mars",
  object_category: "Planet",
  object_type: "planet",
};

const COMET = {
  name: "1P/Halley",
  object_category: "Planet",
  object_type: "comet",
};

const STAR = {
  name: "Sirius",
  object_category: "Star",
  object_type: "star",
};

const DEEP_SKY = {
  name: "M 31",
  object_category: "Nebula",
  object_type: "galaxy",
};

function apiResultFromFixture(fixtureName, targetId) {
  const payload = loadFixture(fixtureName);
  const item = payload.collection.items[0];
  const data = item.data[0];
  const link = item.links.find((l) => l.rel === "preview");
  const keywords = Array.isArray(data.keywords) ? data.keywords.join(", ") : null;
  return {
    ok: true,
    status: "found",
    target_id: targetId,
    target_name: targetId.charAt(0).toUpperCase() + targetId.slice(1),
    searched_target: targetId.charAt(0).toUpperCase() + targetId.slice(1),
    image_url: link.href,
    title: data.title,
    description: data.description,
    mission: null,
    nasa_center: data.center || null,
    keywords: keywords,
    instrument: null,
    image_date: data.date_created,
    source_agency: "NASA",
    credit: data.secondary_creator,
    source_link: `https://images.nasa.gov/details/${data.nasa_id}`,
    archive_notice: PlanetaryImage.ARCHIVE_NOTICE,
    media_label: PlanetaryImage.MEDIA_LABEL,
    result_type: PlanetaryImage.RESULT_TYPE,
  };
}

test("Moon resolves to pilot id", () => {
  assert.equal(PlanetaryImage.resolvePilotTargetId(MOON), "moon");
});

test("Jupiter resolves to pilot id", () => {
  assert.equal(PlanetaryImage.resolvePilotTargetId(JUPITER), "jupiter");
});

test("Saturn resolves to pilot id", () => {
  assert.equal(PlanetaryImage.resolvePilotTargetId(SATURN), "saturn");
});

test("Mars resolves through the media registry", () => {
  assert.equal(PlanetaryImage.resolvePilotTargetId(MARS), "mars");
  assert.equal(SolarSystem.isSolarSystemTarget(MARS), true);
});

test("unsupported Solar System target has no media registry id", () => {
  assert.equal(PlanetaryImage.resolvePilotTargetId(COMET), null);
  assert.equal(SolarSystem.isSolarSystemTarget(COMET), true);
});

test("normal star hides planetary-image panel", async () => {
  const fetchImpl = async (url) => {
    if (String(url).startsWith("/api/planetary-image")) {
      throw new Error("planetary fetch must not run for stars");
    }
    if (String(url).startsWith("/api/selection")) {
      return {
        ok: true,
        json: async () => ({
          ok: true,
          connected: true,
          name: "Sirius",
          object_category: "Star",
          object_type: "star",
          ra_deg: 101.287,
          dec_deg: -16.716,
        }),
      };
    }
    return { ok: true, json: async () => ({ connected: true }) };
  };

  const { exports: app } = loadApp(fetchImpl);
  await fireAndFlush(app.el.btnRefreshSelection, "click");
  app.el.onlineModeToggle.checked = true;
  await fireAndFlush(app.el.onlineModeToggle, "change");
  assert.equal(app.el.planetaryImageCard.hidden, true);
});

test("deep-sky object hides planetary-image panel", async () => {
  const fetchImpl = async (url) => {
    if (String(url).startsWith("/api/planetary-image")) {
      throw new Error("planetary fetch must not run for deep-sky");
    }
    if (String(url).startsWith("/api/selection")) {
      return {
        ok: true,
        json: async () => ({
          ok: true,
          connected: true,
          name: "M 31",
          object_category: "Nebula",
          object_type: "galaxy",
          ra_deg: 10.6847,
          dec_deg: 41.26875,
        }),
      };
    }
    return { ok: true, json: async () => ({ connected: true }) };
  };

  const { exports: app } = loadApp(fetchImpl);
  await fireAndFlush(app.el.btnRefreshSelection, "click");
  app.el.onlineModeToggle.checked = true;
  await fireAndFlush(app.el.onlineModeToggle, "change");
  assert.equal(app.el.planetaryImageCard.hidden, true);
});

test("Online Archive Mode off causes zero planetary-image network calls", async () => {
  let planetaryCalls = 0;
  const fetchImpl = async (url) => {
    if (String(url).startsWith("/api/planetary-image")) {
      planetaryCalls += 1;
    }
    if (String(url).startsWith("/api/selection")) {
      return {
        ok: true,
        json: async () => ({
          ok: true,
          connected: true,
          name: "Moon",
          object_category: "Planet",
          object_type: "moon",
          ra_deg: 1,
          dec_deg: 2,
        }),
      };
    }
    return { ok: true, json: async () => ({ connected: true }) };
  };

  const { exports: app } = loadApp(fetchImpl);
  await fireAndFlush(app.el.btnRefreshSelection, "click");
  assert.equal(planetaryCalls, 0);
  assert.equal(app.el.planetaryImageCard.hidden, true);
});

test("successful official-source response renders safely", async () => {
  const fetchImpl = async (url) => {
    if (String(url).includes("target=moon")) {
      return { ok: true, json: async () => apiResultFromFixture("nasa_images_moon.json", "moon") };
    }
    if (String(url).startsWith("/api/selection")) {
      return {
        ok: true,
        json: async () => ({
          ok: true,
          connected: true,
          name: "Moon",
          object_category: "Planet",
          object_type: "moon",
          ra_deg: 1,
          dec_deg: 2,
        }),
      };
    }
    return { ok: true, json: async () => ({ connected: true }) };
  };

  const { exports: app } = loadApp(fetchImpl);
  await fireAndFlush(app.el.btnRefreshSelection, "click");
  app.el.onlineModeToggle.checked = true;
  await fireAndFlush(app.el.onlineModeToggle, "change");
  assert.equal(app.el.planetaryImageCard.hidden, false);
  const img = app.el.planetaryImageBody.querySelector("img");
  assert.ok(img);
  assert.match(img.src, /images-assets\.nasa\.gov/);
  assert.equal(img.getAttribute("onerror"), null);
  assert.match(app.el.planetaryImageBody.textContent, /Nearside of the Moon/);
  assert.doesNotMatch(app.el.planetaryImageBody.innerHTML, /<script/i);
});

test("service timeout and HTTP error views are honest", () => {
  const timeoutView = PlanetaryImage.buildResultView({
    status: "timeout",
    error: "NASA archive service did not respond in time.",
  });
  assert.equal(timeoutView.mode, "error");

  const httpView = PlanetaryImage.buildResultView({
    status: "http_error",
    error: "NASA archive service returned HTTP 503.",
  });
  assert.equal(httpView.mode, "error");
});

test("malformed and missing-image responses fall back cleanly", () => {
  const malformed = PlanetaryImage.buildResultView({ status: "malformed", error: "unexpected" });
  assert.equal(malformed.mode, "unavailable");

  const missing = PlanetaryImage.buildResultView({ status: "found", image_url: null });
  assert.equal(missing.mode, "unavailable");
});

test("missing optional metadata still renders found image", () => {
  const view = PlanetaryImage.buildResultView({
    status: "found",
    image_url: "https://images-assets.nasa.gov/image/PIA99999/PIA99999~thumb.jpg",
    target_name: "Jupiter",
    title: "Minimal",
    source_agency: "NASA",
  });
  assert.equal(view.mode, "found");
  assert.equal(view.mission, null);
  assert.equal(view.nasaCenter, null);
});

test("rejects unexpected or non-HTTPS image URLs", () => {
  assert.equal(PlanetaryImage.isAllowedImageUrl("http://images-assets.nasa.gov/x.jpg"), false);
  assert.equal(PlanetaryImage.isAllowedImageUrl("https://evil.example/x.jpg"), false);
  const view = PlanetaryImage.buildResultView({
    status: "found",
    image_url: "https://evil.example/x.jpg",
    title: "Bad",
  });
  assert.notEqual(view.mode, "found");
});

test("duplicate-target request suppression skips second fetch after completion", async () => {
  let planetaryCalls = 0;
  const fetchImpl = async (url) => {
    if (String(url).includes("target=jupiter")) {
      planetaryCalls += 1;
      return { ok: true, json: async () => apiResultFromFixture("nasa_images_jupiter.json", "jupiter") };
    }
    return { ok: true, json: async () => ({ connected: true }) };
  };

  const { exports: app } = loadApp(fetchImpl);
  app.state.onlineMode = true;
  const target = JUPITER;
  await app.syncPlanetaryImagePanel(target);
  await app.syncPlanetaryImagePanel(target);
  assert.equal(planetaryCalls, 1);
});

test("in-flight duplicate request for same pilot target is suppressed", async () => {
  let planetaryCalls = 0;
  let releaseFetch;
  const fetchStarted = new Promise((resolve) => {
    releaseFetch = resolve;
  });

  const fetchImpl = async (url) => {
    if (String(url).includes("target=moon")) {
      planetaryCalls += 1;
      await fetchStarted;
      return { ok: true, json: async () => apiResultFromFixture("nasa_images_moon.json", "moon") };
    }
    return { ok: true, json: async () => ({ connected: true }) };
  };

  const { exports: app } = loadApp(fetchImpl);
  app.state.onlineMode = true;

  const first = app.syncPlanetaryImagePanel(MOON);
  await new Promise((resolve) => setTimeout(resolve, 0));
  await app.syncPlanetaryImagePanel(MOON);
  assert.equal(planetaryCalls, 1);

  releaseFetch();
  await first;
});

test("rapid target switching does not show stale imagery", async () => {
  const fetchImpl = async (url) => {
    if (String(url).includes("target=moon")) {
      await new Promise((resolve) => setTimeout(resolve, 30));
      return { ok: true, json: async () => apiResultFromFixture("nasa_images_moon.json", "moon") };
    }
    if (String(url).includes("target=saturn")) {
      return { ok: true, json: async () => apiResultFromFixture("nasa_images_saturn.json", "saturn") };
    }
    return { ok: true, json: async () => ({ connected: true }) };
  };

  const { exports: app } = loadApp(fetchImpl);
  app.state.onlineMode = true;

  const moonPromise = app.syncPlanetaryImagePanel(MOON);
  const saturnPromise = app.syncPlanetaryImagePanel(SATURN);
  await Promise.all([moonPromise, saturnPromise]);

  assert.match(app.el.planetaryImageBody.textContent, /Saturn Atmosphere/);
  assert.doesNotMatch(app.el.planetaryImageBody.textContent, /Nearside of the Moon/);
});

test("late supported response cannot overwrite unsupported target message", async () => {
  let releaseMoon;
  const moonGate = new Promise((resolve) => {
    releaseMoon = resolve;
  });

  const fetchImpl = async (url) => {
    if (String(url).includes("target=moon")) {
      await moonGate;
      return { ok: true, json: async () => apiResultFromFixture("nasa_images_moon.json", "moon") };
    }
    return { ok: true, json: async () => ({ connected: true }) };
  };

  const { exports: app } = loadApp(fetchImpl);
  app.state.onlineMode = true;

  const moonPromise = app.syncPlanetaryImagePanel(MOON);
  await new Promise((resolve) => setTimeout(resolve, 0));
  await app.syncPlanetaryImagePanel(COMET);

  assert.match(app.el.planetaryImageBody.textContent, /not in the NASA public-media registry/i);
  assert.doesNotMatch(app.el.planetaryImageBody.textContent, /Nearside of the Moon/);

  releaseMoon();
  await moonPromise;
  await new Promise((resolve) => setTimeout(resolve, 0));

  assert.match(app.el.planetaryImageBody.textContent, /not in the NASA public-media registry/i);
  assert.doesNotMatch(app.el.planetaryImageBody.textContent, /Nearside of the Moon/);
  assert.equal(app.el.planetaryImageBody.querySelector("img"), null);
});

test("returning to Moon after unsupported target fetches Moon again", async () => {
  let moonCalls = 0;
  const fetchImpl = async (url) => {
    if (String(url).includes("target=moon")) {
      moonCalls += 1;
      return { ok: true, json: async () => apiResultFromFixture("nasa_images_moon.json", "moon") };
    }
    return { ok: true, json: async () => ({ connected: true }) };
  };

  const { exports: app } = loadApp(fetchImpl);
  app.state.onlineMode = true;

  await app.syncPlanetaryImagePanel(MOON);
  assert.equal(moonCalls, 1);
  assert.match(app.el.planetaryImageBody.textContent, /Nearside of the Moon/);

  await app.syncPlanetaryImagePanel(COMET);
  assert.match(app.el.planetaryImageBody.textContent, /not in the NASA public-media registry/i);
  assert.equal(app.el.planetaryImageBody.querySelector("img"), null);

  await app.syncPlanetaryImagePanel(MOON);
  assert.equal(moonCalls, 2);
  assert.match(app.el.planetaryImageBody.textContent, /Nearside of the Moon/);
  assert.doesNotMatch(app.el.planetaryImageBody.textContent, /not in the NASA public-media registry/i);
  assert.ok(app.el.planetaryImageBody.querySelector("img"));
});

test("unsupported target switch clears completed fetch cache", () => {
  const reqState = PlanetaryImage.createRequestState();
  reqState.lastFetchedPilotId = "moon";
  PlanetaryImage.prepareUnsupportedTargetSwitch(reqState);
  assert.equal(reqState.lastFetchedPilotId, null);
  assert.equal(reqState.inFlightPilotId, null);
});

test("unsupported Solar System target shows honest fallback without fetch", async () => {
  let planetaryCalls = 0;
  const fetchImpl = async (url) => {
    if (String(url).startsWith("/api/planetary-image")) planetaryCalls += 1;
    return { ok: true, json: async () => ({ connected: true }) };
  };

  const { exports: app } = loadApp(fetchImpl);
  app.state.onlineMode = true;
  await app.syncPlanetaryImagePanel(COMET);
  assert.equal(planetaryCalls, 0);
  assert.equal(app.el.planetaryImageCard.hidden, false);
  assert.match(app.el.planetaryImageBody.textContent, /not in the NASA public-media registry/i);
});

test("Mars no longer shows three-target-pilot unsupported message", async () => {
  let planetaryCalls = 0;
  const fetchImpl = async (url) => {
    if (String(url).includes("target=mars")) {
      planetaryCalls += 1;
      return {
        ok: true,
        json: async () => ({
          ok: true,
          status: "unavailable",
          target_id: "mars",
          target_name: "Mars",
          searched_target: "Mars",
          error: PlanetaryImage.EMPTY_MEDIA_MESSAGE,
          media_label: PlanetaryImage.MEDIA_LABEL,
          archive_notice: PlanetaryImage.ARCHIVE_NOTICE,
        }),
      };
    }
    return { ok: true, json: async () => ({ connected: true }) };
  };

  const { exports: app } = loadApp(fetchImpl);
  app.state.onlineMode = true;
  await app.syncPlanetaryImagePanel(MARS);
  assert.equal(planetaryCalls, 1);
  assert.doesNotMatch(app.el.planetaryImageBody.textContent, /Moon, Jupiter, and Saturn only/i);
  assert.match(app.el.planetaryImageBody.textContent, /No relevant NASA public-media result/i);
});

test("target switch clears previous media immediately", async () => {
  let releaseMars;
  const marsGate = new Promise((resolve) => {
    releaseMars = resolve;
  });

  const fetchImpl = async (url) => {
    if (String(url).includes("target=moon")) {
      return { ok: true, json: async () => apiResultFromFixture("nasa_images_moon.json", "moon") };
    }
    if (String(url).includes("target=mars")) {
      await marsGate;
      return {
        ok: true,
        json: async () => ({
          ok: true,
          status: "found",
          target_id: "mars",
          target_name: "Mars",
          searched_target: "Mars",
          image_url: "https://images-assets.nasa.gov/image/PIAMARS/PIAMARS~thumb.jpg",
          title: "Mars planet",
          media_label: PlanetaryImage.MEDIA_LABEL,
          result_type: PlanetaryImage.RESULT_TYPE,
          archive_notice: PlanetaryImage.ARCHIVE_NOTICE,
          source_agency: "NASA",
        }),
      };
    }
    return { ok: true, json: async () => ({ connected: true }) };
  };

  const { exports: app } = loadApp(fetchImpl);
  app.state.onlineMode = true;
  await app.syncPlanetaryImagePanel(MOON);
  assert.ok(app.el.planetaryImageBody.querySelector("img"));

  const marsPromise = app.syncPlanetaryImagePanel(MARS);
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(app.el.planetaryImageBody.querySelector("img"), null);
  assert.match(app.el.planetaryImageBody.textContent, /Searching NASA/i);

  releaseMars();
  await marsPromise;
  assert.match(app.el.planetaryImageBody.textContent, /Mars planet/);
});

test("empty media result clears old imagery", async () => {
  const fetchImpl = async (url) => {
    if (String(url).includes("target=moon")) {
      return { ok: true, json: async () => apiResultFromFixture("nasa_images_moon.json", "moon") };
    }
    if (String(url).includes("target=mars")) {
      return {
        ok: true,
        json: async () => ({
          ok: true,
          status: "unavailable",
          target_id: "mars",
          target_name: "Mars",
          error: PlanetaryImage.EMPTY_MEDIA_MESSAGE,
          media_label: PlanetaryImage.MEDIA_LABEL,
          archive_notice: PlanetaryImage.ARCHIVE_NOTICE,
        }),
      };
    }
    return { ok: true, json: async () => ({ connected: true }) };
  };

  const { exports: app } = loadApp(fetchImpl);
  app.state.onlineMode = true;
  await app.syncPlanetaryImagePanel(MOON);
  assert.ok(app.el.planetaryImageBody.querySelector("img"));
  await app.syncPlanetaryImagePanel(MARS);
  assert.equal(app.el.planetaryImageBody.querySelector("img"), null);
  assert.match(app.el.planetaryImageBody.textContent, /No relevant NASA public-media result/i);
});

test("found results expose public_media_asset classification", () => {
  const view = PlanetaryImage.buildResultView(apiResultFromFixture("nasa_images_moon.json", "moon"));
  assert.equal(view.mode, "found");
  assert.equal(view.resultType, "public_media_asset");
  assert.equal(view.mediaLabel, "NASA public archive media");
});

test("registry aliases resolve deterministically in the browser module", () => {
  const Registry = require("../../app/static/lib/solar_system_media_registry.js");
  assert.equal(Registry.normalizeMediaTargetId("Luna"), "moon");
  assert.equal(Registry.normalizeMediaTargetId("terra"), "earth");
  assert.equal(Registry.getEntry("europa").parent_body, "jupiter");
  assert.equal(Registry.getEntry("titan").parent_body, "saturn");
  assert.equal(Registry.getEntry("charon").parent_body, "pluto");
});

test("DOM rendering uses safe property assignment for remote image and link values", () => {
  const maliciousTitle = '"><img src=x onerror="alert(1)">';
  const validImageUrl = "https://images-assets.nasa.gov/image/PIA00001/PIA00001~thumb.jpg";
  const validSourceLink = "https://images.nasa.gov/details/PIA00001";

  const view = PlanetaryImage.buildResultView({
    status: "found",
    image_url: validImageUrl,
    title: maliciousTitle,
    description: "<b>not html</b>",
    target_name: "Moon",
    source_agency: "NASA",
    source_link: validSourceLink,
  });

  const { exports: app } = loadApp(async () => ({ ok: true, json: async () => ({}) }));
  app.renderPlanetaryImagePanel(view);

  const img = app.el.planetaryImageBody.querySelector("img");
  assert.ok(img);
  assert.equal(img.getAttribute("onerror"), null);
  assert.equal(img.alt, maliciousTitle);
  assert.equal(img.src, validImageUrl);

  const link = app.el.planetaryImageBody.querySelector("a");
  assert.ok(link);
  assert.equal(link.getAttribute("onclick"), null);
  assert.equal(link.href, validSourceLink);
  assert.equal(link.target, "_blank");
  assert.equal(link.rel, "noopener noreferrer");

  assert.doesNotMatch(app.el.planetaryImageBody.innerHTML, /onerror=/i);
  assert.doesNotMatch(app.el.planetaryImageBody.innerHTML, /onclick=/i);
});

test("literal quote characters in image URL are rejected before rendering", () => {
  const quotedUrl =
    "https://images-assets.nasa.gov/image/PIA00001/PIA00001~thumb.jpg?x=\" onerror=\"alert(1)";

  assert.equal(PlanetaryImage.isAllowedImageUrl(quotedUrl), false);

  const view = PlanetaryImage.buildResultView({
    status: "found",
    image_url: quotedUrl,
    title: "Moon",
    target_name: "Moon",
    source_agency: "NASA",
  });

  assert.notEqual(view.mode, "found");
});

test("rejects source links outside the official NASA details host", () => {
  assert.equal(
    PlanetaryImage.isAllowedSourceLink('https://images.nasa.gov/details/PIA00001" onclick="alert(1)'),
    false
  );
  const view = PlanetaryImage.buildResultView({
    status: "found",
    image_url: "https://images-assets.nasa.gov/image/PIA00001/PIA00001~thumb.jpg",
    source_link: 'https://evil.example.com/details/PIA00001',
    title: "Moon",
    target_name: "Moon",
    source_agency: "NASA",
  });
  assert.equal(view.sourceLink, null);
});

test("reset request state allows a fresh fetch after Online Archive Mode cycle", async () => {
  let planetaryCalls = 0;
  const fetchImpl = async (url) => {
    if (String(url).includes("target=moon")) {
      planetaryCalls += 1;
      return { ok: true, json: async () => apiResultFromFixture("nasa_images_moon.json", "moon") };
    }
    return { ok: true, json: async () => ({ connected: true }) };
  };

  const { exports: app } = loadApp(fetchImpl);
  app.state.onlineMode = true;
  await app.syncPlanetaryImagePanel(MOON);
  app.resetPlanetaryImagePanel();
  app.state.onlineMode = true;
  await app.syncPlanetaryImagePanel(MOON);
  assert.equal(planetaryCalls, 2);
});

test("Jupiter and Saturn normalized result views", () => {
  const jupiter = PlanetaryImage.buildResultView(apiResultFromFixture("nasa_images_jupiter.json", "jupiter"));
  assert.equal(jupiter.mode, "found");
  assert.equal(jupiter.targetName, "Jupiter");

  const saturn = PlanetaryImage.buildResultView(apiResultFromFixture("nasa_images_saturn.json", "saturn"));
  assert.equal(saturn.mode, "found");
  assert.equal(saturn.targetName, "Saturn");
});
