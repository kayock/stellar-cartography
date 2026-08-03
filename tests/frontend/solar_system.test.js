"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");

const TargetModel = require(path.join(__dirname, "..", "..", "app", "static", "lib", "target_model.js"));
const SolarSystem = require(path.join(__dirname, "..", "..", "app", "static", "lib", "solar_system.js"));
const { loadApp, fireAndFlush } = require("./app_loader");

function buildFromFixture(apiBody, fovDeg) {
  const target = TargetModel.buildTargetFromSelection({
    ok: true,
    connected: true,
    ...apiBody,
    fov_deg: fovDeg,
  });
  return target;
}

const MOON = {
  name: "Moon",
  object_category: "Planet",
  object_type: "moon",
  angular_size_deg: 0.518,
  ra_deg: 120.5,
  dec_deg: 18.2,
};

const SATURN = {
  name: "Saturn",
  object_category: "Planet",
  object_type: "planet",
  angular_size_deg: 0.037,
  ra_deg: 45.2,
  dec_deg: 15.8,
};

const STAR = {
  name: "Sirius",
  object_category: "Star",
  object_type: "star",
  angular_size_deg: null,
  ra_deg: 101.287,
  dec_deg: -16.716,
};

const DEEP_SKY = {
  name: "M 31",
  object_category: "Nebula",
  object_type: "galaxy",
  angular_size_deg: 3.167,
  ra_deg: 10.6847,
  dec_deg: 41.26875,
};

test("Saturn is detected as a Solar System target", () => {
  assert.equal(SolarSystem.isSolarSystemTarget(SATURN), true);
});

test("Moon is detected as a Solar System target", () => {
  assert.equal(SolarSystem.isSolarSystemTarget(MOON), true);
});

test("a normal star is not a Solar System target", () => {
  assert.equal(SolarSystem.isSolarSystemTarget(STAR), false);
});

test("a deep-sky galaxy is not a Solar System target", () => {
  assert.equal(SolarSystem.isSolarSystemTarget(DEEP_SKY), false);
});

test("planetary nebula is not misclassified as Solar System", () => {
  assert.equal(
    SolarSystem.isSolarSystemTarget({
      object_category: "Nebula",
      object_type: "planetary nebula",
    }),
    false
  );
});

test("wide Stellarium FoV is clamped for Saturn", () => {
  const target = { ...SATURN, fov_deg: 60 };
  const viewerFov = SolarSystem.deriveEsaskyFovDeg(target);
  assert.ok(viewerFov <= SolarSystem.FOV_MAX_DEG);
  assert.ok(viewerFov >= SolarSystem.FOV_MIN_DEG);
  assert.notEqual(viewerFov, 60);
});

test("wide Stellarium FoV is clamped for the Moon", () => {
  const target = { ...MOON, fov_deg: 60 };
  const viewerFov = SolarSystem.deriveEsaskyFovDeg(target);
  assert.ok(viewerFov <= SolarSystem.FOV_MAX_DEG);
  assert.equal(viewerFov, Math.min(SolarSystem.FOV_MAX_DEG, MOON.angular_size_deg * SolarSystem.FOV_ANGULAR_SIZE_MARGIN));
});

test("deep-sky FoV passes through Stellarium value unchanged", () => {
  const target = { ...DEEP_SKY, fov_deg: 5.2 };
  assert.equal(SolarSystem.deriveEsaskyFovDeg(target), 5.2);
});

test("star FoV passes through Stellarium value unchanged", () => {
  const target = { ...STAR, fov_deg: 1.8 };
  assert.equal(SolarSystem.deriveEsaskyFovDeg(target), 1.8);
});

test("Solar System notice text is honest about ESASky survey limitations", () => {
  const paragraphs = SolarSystem.buildSolarSystemNoticeParagraphs();
  assert.ok(paragraphs.length >= 3);
  const joined = paragraphs.join(" ");
  assert.match(joined, /sky-survey/i);
  assert.match(joined, /HiPS/i);
  assert.match(joined, /not necessarily.*current visual appearance/i);
  assert.match(joined, /correct.*coordinates|correct RA\/Dec/i);
});

test("fixture-derived Moon target detects and clamps FoV", () => {
  const target = buildFromFixture(
    {
      name: "Moon",
      object_category: "Planet",
      object_type: "moon",
      angular_size_deg: 0.518,
      ra_deg: 120.5,
      dec_deg: 18.2,
    },
    60
  );
  assert.equal(SolarSystem.isSolarSystemTarget(target), true);
  assert.ok(SolarSystem.deriveEsaskyFovDeg(target) <= SolarSystem.FOV_MAX_DEG);
});

test("ESASky navigation uses clamped FoV for Solar System targets (real app.js)", async () => {
  const SATURN_API = {
    ok: true,
    connected: true,
    name: "Saturn",
    object_category: "Planet",
    object_type: "planet",
    angular_size_deg: 0.037,
    ra_deg: 45.2,
    dec_deg: 15.8,
    fov_deg: 60,
    ra_sexagesimal: null,
    dec_sexagesimal: null,
  };

  const fetchImpl = async (url) => {
    if (String(url).startsWith("/api/selection")) {
      return { ok: true, json: async () => SATURN_API };
    }
    return { ok: true, json: async () => ({ connected: true }) };
  };

  const { exports: app } = loadApp(fetchImpl);
  const dispatched = [];
  app.el.esaskyFrame.contentWindow.postMessage = (msg) => dispatched.push(msg);

  await fireAndFlush(app.el.btnRefreshSelection, "click");
  assert.equal(app.state.currentTarget.name, "Saturn");
  assert.equal(app.el.solarSystemNoticeCard.hidden, false);
  assert.match(app.el.solarSystemNoticeBody.innerHTML, /sky-survey/i);

  app.el.onlineModeToggle.checked = true;
  await fireAndFlush(app.el.onlineModeToggle, "change");
  await fireAndFlush(app.el.btnOpenEsasky, "click");

  const expectedFov = app.getViewerFovDeg(app.state.currentTarget);
  assert.ok(expectedFov <= SolarSystem.FOV_MAX_DEG);
  assert.notEqual(expectedFov, 60);
  assert.match(app.el.esaskyFrame.src, new RegExp(`fov=${expectedFov}`));

  app.el.esaskyFrame.dispatchEvent({ type: "load" });

  // First open encodes FoV in the iframe URL; postMessage setFov comes on
  // subsequent navigation once the queue is ready.
  await fireAndFlush(app.el.btnOpenEsasky, "click");
  const setFovCalls = dispatched.filter((m) => m.event === "setFov");
  assert.equal(setFovCalls.length, 1);
  assert.equal(setFovCalls[0].content.fov, expectedFov);
});

test("deep-sky target does not show Solar System notice (real app.js)", async () => {
  const GALAXY_API = {
    ok: true,
    connected: true,
    name: "M 31",
    object_category: "Nebula",
    object_type: "galaxy",
    angular_size_deg: 3.167,
    ra_deg: 10.6847,
    dec_deg: 41.26875,
    fov_deg: 5.2,
    ra_sexagesimal: null,
    dec_sexagesimal: null,
  };

  const fetchImpl = async (url) => {
    if (String(url).startsWith("/api/selection")) {
      return { ok: true, json: async () => GALAXY_API };
    }
    return { ok: true, json: async () => ({ connected: true }) };
  };

  const { exports: app } = loadApp(fetchImpl);
  await fireAndFlush(app.el.btnRefreshSelection, "click");
  assert.equal(app.el.solarSystemNoticeCard.hidden, true);
  assert.equal(app.getViewerFovDeg(app.state.currentTarget), 5.2);
});
