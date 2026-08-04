"use strict";

/* ---------------------------------------------------------------------
 * FOXAI Stellar Cartography - frontend
 *
 * This file:
 *   1. Polls this app's own local server for Stellarium connectivity
 *      and the current selection (server talks to localhost:8090).
 *   2. Handles the manual coordinate fallback form.
 *   3. Once the user opts into "Online Archive Mode", embeds ESASky
 *      (sky.esa.int) directly in an iframe and drives it via its
 *      documented postMessage JavaScript API. This app's local server
 *      is never in that path.
 *
 * The pure matching/queueing/shutdown logic used below lives in
 * app/static/lib/*.js (loaded via <script> tags before this file) so it
 * can be exercised directly by build-time Node tests -- see
 * tests/frontend/. This file is DOM glue only.
 * ------------------------------------------------------------------- */

const ESASKY_ORIGIN = "https://sky.esa.int";
const IMAGERY_BUTTONS = ImageryMatching.IMAGERY_BUTTONS;
const IMAGERY_ARCHIVE_MISSION = {
  hubble: "hst",
  jwst_nircam: "jwst_nircam",
  jwst_miri: "jwst_miri",
};

const state = {
  currentTarget: null, // {name, ra_deg, dec_deg, fov_deg, source, ...}
  onlineMode: false,
  esaskyQueue: EsaskyQueue.createState(),
  pendingHipsRequest: null, // {buttonId, timeoutId, generation}
  pendingChangeRequest: null, // {buttonId, requestedName, timeoutId, generation, kind}
  // Legacy field: kept in sync with hipsLayer.acknowledgedImageryButtonId for
  // shutdown/failed-selection helpers. Confirmed card styling uses hipsLayer.
  activeImageryButtonId: null,
  hipsLayer: HipsLayerControl.createState(),
  hipsNavTargetKey: null,
  planetaryImageRequest: PlanetaryImage.createRequestState(),
  archiveAvailability: ArchiveAvailability.createState(),
  archiveLights: {},
  discoveryBundle: null,
  discoveryInFlightKey: null,
  watchlistDocument: { schema_version: 1, entries: [] },
  watchlistLoadStatus: { status: "loading", entryCount: 0, storagePathRelative: "runtime_data/tracked_objects.json", error: null },
  watchlistNoteDrafts: {},
  selectedWatchlistId: null,
  apophisRequest: ApophisTracker.createRequestState(),
  apophisShowingCached: false,
};

// -- DOM refs ---------------------------------------------------------

const el = {
  stellariumIndicator: document.getElementById("stellarium-indicator"),
  archiveModeIndicator: document.getElementById("archive-mode-indicator"),
  btnRefreshSelection: document.getElementById("btn-refresh-selection"),
  targetCard: document.getElementById("target-card"),
  aboutObjectCard: document.getElementById("about-object-card"),
  aboutObjectBody: document.getElementById("about-object-body"),
  solarSystemNoticeCard: document.getElementById("solar-system-notice-card"),
  solarSystemNoticeBody: document.getElementById("solar-system-notice-body"),
  planetaryImageCard: document.getElementById("planetary-image-card"),
  planetaryImageBody: document.getElementById("planetary-image-body"),
  manualForm: document.getElementById("manual-form"),
  manualName: document.getElementById("manual-name"),
  manualRa: document.getElementById("manual-ra"),
  manualDec: document.getElementById("manual-dec"),
  manualFormError: document.getElementById("manual-form-error"),
  onlineModeToggle: document.getElementById("online-mode-toggle"),
  btnOpenEsasky: document.getElementById("btn-open-esasky"),
  viewerStatus: document.getElementById("viewer-status"),
  esaskyFrameWrap: document.getElementById("esasky-frame-wrap"),
  esaskyFrame: document.getElementById("esasky-frame"),
  imageryGrid: document.getElementById("imagery-grid"),
  imageryStatus: document.getElementById("imagery-status"),
  archiveObservationPanel: document.getElementById("archive-observation-panel"),
  discoveryPanel: document.getElementById("discovery-panel"),
  discoveryPanelBody: document.getElementById("discovery-panel-body"),
  hipsSurveyControlsLabel: document.getElementById("hips-survey-controls-label"),
  hipsRestoreWrap: document.getElementById("hips-restore-wrap"),
  btnHipsRestore: document.getElementById("btn-hips-restore"),
  hipsDiagnostics: document.getElementById("hips-diagnostics"),
  wavelengthExplainer: document.getElementById("wavelength-explainer"),
  watchlistExplainer: document.getElementById("watchlist-explainer"),
  watchlistStatus: document.getElementById("watchlist-status"),
  btnWatchlistAdd: document.getElementById("btn-watchlist-add"),
  btnApophisAdd: document.getElementById("btn-apophis-add"),
  btnWatchlistRefresh: document.getElementById("btn-watchlist-refresh"),
  watchlistList: document.getElementById("watchlist-list"),
  trackedObjectDetailsCard: document.getElementById("tracked-object-details-card"),
  trackedObjectDetailsHeading: document.getElementById("tracked-object-details-heading"),
  trackedObjectDetailsBody: document.getElementById("tracked-object-details-body"),
  apophisTrackerBody: document.getElementById("apophis-tracker-body"),
};

// -- Stellarium connection status -------------------------------------

async function pollStellariumStatus() {
  try {
    const resp = await fetch("/api/status", { cache: "no-store" });
    const data = await resp.json();
    setStellariumIndicator(!!data.connected);
  } catch (err) {
    setStellariumIndicator(false);
  }
}

function setStellariumIndicator(connected) {
  el.stellariumIndicator.classList.remove("status-connected", "status-disconnected", "status-unknown");
  const textEl = el.stellariumIndicator.querySelector(".status-text");
  if (connected) {
    el.stellariumIndicator.classList.add("status-connected");
    textEl.textContent = "Stellarium: Connected";
  } else {
    el.stellariumIndicator.classList.add("status-disconnected");
    textEl.textContent = "Stellarium: Not connected (manual mode available)";
  }
}

// -- Selected-target card ----------------------------------------------

function renderTargetCard() {
  const t = state.currentTarget;
  if (!t) {
    el.targetCard.className = "target-card target-card-empty";
    el.targetCard.innerHTML =
      '<div class="target-empty-msg">No target loaded yet. Select an object in Stellarium, then press ' +
      '"Use Stellarium Selection" — or enter a target manually below.</div>';
    el.btnOpenEsasky.disabled = true;
    el.aboutObjectCard.hidden = true;
    el.solarSystemNoticeCard.hidden = true;
    resetPlanetaryImagePanel();
    resetArchiveAvailabilityLights();
    return;
  }

  el.targetCard.className = "target-card";
  const nextHipsKey = `${t.ra_deg}:${t.dec_deg}:${t.name || ""}`;
  if (state.hipsNavTargetKey !== null && state.hipsNavTargetKey !== nextHipsKey) {
    invalidateHipsPendingWork();
  }
  state.hipsNavTargetKey = nextHipsKey;
  const viewerFovDeg = SolarSystem.deriveEsaskyFovDeg(t);
  const isSolarSystem = SolarSystem.isSolarSystemTarget(t);
  const fovRow = t.fov_deg != null
    ? `<div class="target-field"><label>Stellarium FoV</label><div class="value">${t.fov_deg.toFixed(3)}°</div></div>`
    : "";
  const viewerFovRow = isSolarSystem && viewerFovDeg != null
    ? `<div class="target-field"><label>ESASky viewer FoV</label><div class="value">${viewerFovDeg.toFixed(3)}°</div></div>`
    : "";
  const altRow = t.alt_name ? `<div class="target-alt">${escapeHtml(t.alt_name)}</div>` : "";
  const typeRow = t.object_type
    ? `<div class="target-field"><label>Type</label><div class="value">${escapeHtml(t.object_type)}</div></div>`
    : "";

  el.targetCard.innerHTML = `
    <div class="target-name">${escapeHtml(t.name || "Unnamed target")}</div>
    ${altRow}
    <div class="target-grid">
      <div class="target-field"><label>RA (J2000)</label><div class="value">${t.ra_sexagesimal || t.ra_deg.toFixed(5) + "°"}</div></div>
      <div class="target-field"><label>Dec (J2000)</label><div class="value">${t.dec_sexagesimal || t.dec_deg.toFixed(5) + "°"}</div></div>
      <div class="target-field"><label>RA (decimal)</label><div class="value">${t.ra_deg.toFixed(5)}°</div></div>
      <div class="target-field"><label>Dec (decimal)</label><div class="value">${t.dec_deg.toFixed(5)}°</div></div>
      ${typeRow}
      ${fovRow}
      ${viewerFovRow}
    </div>
    <div class="target-note">Source: ${escapeHtml(t.source || "unknown")}</div>
  `;
  el.btnOpenEsasky.disabled = false;

  syncEsaskyToCurrentTarget();

  renderAboutObjectCard(t);
  renderSolarSystemNoticeCard(t);
  syncPlanetaryImagePanel(t);
  syncArchiveAvailabilityChecks(t);
}

function getViewerFovDeg(target) {
  return SolarSystem.deriveEsaskyFovDeg(target);
}

// Requirement: whenever state.currentTarget changes while an ESASky
// session has already begun (the user has opened the viewer at least
// once this Online Archive Mode session), the viewer must be kept in
// sync with the *latest* target -- whether the iframe has already
// finished loading (send immediately) or is still mid-load (queue via
// sendEsaskyCommand/EsaskyQueue.enqueueOrSend, which uses replaceKey so
// only the newest queued goToRaDec/setFov survive). This is the single
// shared path for that: renderTargetCard() calls it on every successful
// Stellarium selection and every successful manual target entry (both
// funnel through renderTargetCard()), so neither call site can drift out
// of sync with the other the way renderTargetCard()'s old
// `state.esaskyQueue.ready`-only check did.
//
// Deliberately does NOT open or navigate a fresh ESASky iframe by itself:
// it only acts once state.esaskyQueue.loadListenerAttached is true, which
// only becomes true inside openOrUpdateEsasky() once a real navigation
// has actually been kicked off. Toggling Online Archive Mode on, by
// itself, never sets that flag, so this stays a no-op until the user has
// explicitly opened/requested imagery -- exactly like before this fix.
function syncEsaskyToCurrentTarget() {
  if (!state.onlineMode) return;
  if (!state.esaskyQueue.loadListenerAttached) return;
  const t = state.currentTarget;
  if (!t) return;
  sendEsaskyCommand("goToRaDec", { ra: t.ra_deg, dec: t.dec_deg }, "goToRaDec");
  const viewerFov = getViewerFovDeg(t);
  if (viewerFov) sendEsaskyCommand("setFov", { fov: viewerFov }, "setFov");
}

function renderAboutObjectCard(t) {
  // Fields shown here reflect what Stellarium actually returned. If a
  // field wasn't present or wasn't parseable, it's simply omitted --
  // never shown as an invented value or an empty placeholder row.
  const fields = [
    ["Common name", t.name && t.name !== "Manual target" && t.name !== "Unnamed object" ? t.name : null],
    ["Catalogue / alt. designations", t.catalogue_designations || null],
    ["Localized / alternate name", t.alt_name || null],
    ["Object category", t.object_category || null],
    ["Detailed type", t.object_type || null],
    ["Subtype", t.object_subtype || null],
    ["Constellation", t.constellation || null],
    ["J2000 RA", t.ra_sexagesimal ? `${t.ra_sexagesimal} (${t.ra_deg.toFixed(5)}°)` : null],
    ["J2000 Dec", t.dec_sexagesimal ? `${t.dec_sexagesimal} (${t.dec_deg.toFixed(5)}°)` : null],
    ["Apparent magnitude", typeof t.apparent_magnitude === "number" ? t.apparent_magnitude.toFixed(2) : null],
    ["Angular size", typeof t.angular_size_deg === "number" ? `${t.angular_size_deg.toFixed(3)}°` : null],
    ["Current altitude", typeof t.altitude_deg === "number" ? `${t.altitude_deg.toFixed(2)}°` : null],
    ["Current azimuth", typeof t.azimuth_deg === "number" ? `${t.azimuth_deg.toFixed(2)}°` : null],
    ["Above the horizon", typeof t.above_horizon === "boolean" ? (t.above_horizon ? "Yes" : "No") : null],
  ].filter(([, value]) => value !== null && value !== undefined && value !== "");

  if (fields.length === 0) {
    el.aboutObjectCard.hidden = true;
    return;
  }

  el.aboutObjectCard.hidden = false;
  el.aboutObjectBody.innerHTML = fields
    .map(
      ([label, value]) =>
        `<div class="about-field"><span class="about-label">${escapeHtml(label)}</span><span class="about-value">${escapeHtml(
          String(value)
        )}</span></div>`
    )
    .join("");
}

function renderSolarSystemNoticeCard(t) {
  if (!SolarSystem.isSolarSystemTarget(t)) {
    el.solarSystemNoticeCard.hidden = true;
    el.solarSystemNoticeBody.innerHTML = "";
    return;
  }

  el.solarSystemNoticeCard.hidden = false;
  el.solarSystemNoticeBody.innerHTML = SolarSystem.buildSolarSystemNoticeParagraphs()
    .map((p) => `<p>${escapeHtml(p)}</p>`)
    .join("");
}

function resetPlanetaryImagePanel() {
  PlanetaryImage.resetRequestState(state.planetaryImageRequest);
  el.planetaryImageCard.hidden = true;
  el.planetaryImageBody.innerHTML = "";
}

function renderPlanetaryImagePanel(view) {
  if (!view) {
    resetPlanetaryImagePanel();
    return;
  }

  el.planetaryImageCard.hidden = false;
  el.planetaryImageBody.innerHTML = "";

  if (view.mode === "loading" || view.mode === "unsupported" || view.mode === "unavailable" || view.mode === "error") {
    const status = document.createElement("p");
    status.className = "planetary-status";
    status.textContent = view.message || view.headline || "No archive image available.";
    el.planetaryImageBody.appendChild(status);
    appendPlanetaryArchiveNotice(el.planetaryImageBody, view.archiveNotice);
    return;
  }

  if (view.mode === "found" && PlanetaryImage.isAllowedImageUrl(view.imageUrl)) {
    const wrap = document.createElement("div");
    wrap.className = "planetary-image-wrap";
    const img = document.createElement("img");
    img.className = "planetary-image";
    img.src = view.imageUrl;
    img.alt = view.title || view.targetName || "NASA public archive media";
    wrap.appendChild(img);
    el.planetaryImageBody.appendChild(wrap);

    const mediaLabel = document.createElement("p");
    mediaLabel.className = "planetary-media-label";
    mediaLabel.textContent = view.mediaLabel || PlanetaryImage.MEDIA_LABEL;
    el.planetaryImageBody.appendChild(mediaLabel);

    const meta = document.createElement("div");
    meta.className = "planetary-meta";
    const metaRows = [
      ["Exact target searched", view.searchedTarget || view.targetName],
      ["Title", view.title],
      ["Description", view.description],
      ["Image date", view.imageDate],
      ["NASA center", view.nasaCenter],
      ["Mission / spacecraft", view.mission],
      ["NASA keywords", view.keywords],
      ["Instrument", view.instrument],
      ["Source agency", view.sourceAgency],
      ["Credit", view.credit],
    ];
    metaRows.forEach(([label, value]) => {
      if (!value) return;
      const row = document.createElement("div");
      row.className = "planetary-meta-row";
      const labelEl = document.createElement("span");
      labelEl.className = "planetary-meta-label";
      labelEl.textContent = label;
      const valueEl = document.createElement("span");
      valueEl.className = "planetary-meta-value";
      valueEl.textContent = String(value);
      row.appendChild(labelEl);
      row.appendChild(valueEl);
      meta.appendChild(row);
    });
    el.planetaryImageBody.appendChild(meta);

    if (PlanetaryImage.isAllowedSourceLink(view.sourceLink)) {
      const linkWrap = document.createElement("p");
      linkWrap.className = "planetary-source-link";
      const link = document.createElement("a");
      link.href = view.sourceLink;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = "Open official NASA source";
      linkWrap.appendChild(link);
      el.planetaryImageBody.appendChild(linkWrap);
    }

    appendPlanetaryArchiveNotice(el.planetaryImageBody, view.archiveNotice);
    return;
  }

  const fallback = document.createElement("p");
  fallback.className = "planetary-status";
  fallback.textContent = PlanetaryImage.EMPTY_MEDIA_MESSAGE;
  el.planetaryImageBody.appendChild(fallback);
  appendPlanetaryArchiveNotice(el.planetaryImageBody, view.archiveNotice);
}

function appendPlanetaryArchiveNotice(container, noticeText) {
  const notice = document.createElement("p");
  notice.className = "planetary-archive-notice";
  notice.textContent = noticeText || PlanetaryImage.ARCHIVE_NOTICE;
  container.appendChild(notice);
}

async function syncPlanetaryImagePanel(target) {
  if (!PlanetaryImage.shouldShowPlanetaryPanel(target, state.onlineMode)) {
    resetPlanetaryImagePanel();
    return;
  }

  const pilotId = PlanetaryImage.resolvePilotTargetId(target);
  if (!pilotId) {
    PlanetaryImage.prepareUnsupportedTargetSwitch(state.planetaryImageRequest);
    renderPlanetaryImagePanel(PlanetaryImage.buildUnsupportedView(target));
    return;
  }

  if (PlanetaryImage.shouldSkipDuplicateFetch(state.planetaryImageRequest, pilotId)) {
    return;
  }

  if (PlanetaryImage.shouldSkipInFlightDuplicate(state.planetaryImageRequest, pilotId)) {
    return;
  }

  const generation = PlanetaryImage.beginRequest(state.planetaryImageRequest, pilotId);
  renderPlanetaryImagePanel(PlanetaryImage.buildLoadingView(pilotId));

  try {
    const resp = await fetch(PlanetaryImage.buildApiUrl(pilotId), { cache: "no-store" });
    const data = await resp.json();
    if (PlanetaryImage.isStaleResponse(state.planetaryImageRequest, generation)) {
      return;
    }
    PlanetaryImage.markFetchComplete(state.planetaryImageRequest, pilotId);
    renderPlanetaryImagePanel(PlanetaryImage.buildResultView(data));
  } catch (_err) {
    if (PlanetaryImage.isStaleResponse(state.planetaryImageRequest, generation)) {
      return;
    }
    state.planetaryImageRequest.inFlightPilotId = null;
    renderPlanetaryImagePanel({
      mode: "error",
      message: "Could not reach the local server for a planetary archive image lookup.",
      archiveNotice: PlanetaryImage.ARCHIVE_NOTICE,
    });
  }
}

function escapeHtml(s) {
  const div = document.createElement("div");
  div.textContent = String(s);
  return div.innerHTML;
}

// -- "Use Stellarium Selection" ----------------------------------------

el.btnRefreshSelection.addEventListener("click", async () => {
  el.btnRefreshSelection.disabled = true;
  el.btnRefreshSelection.textContent = "Reading selection…";
  try {
    const resp = await fetch("/api/selection", { cache: "no-store" });
    const data = await resp.json();
    setStellariumIndicator(!!data.connected);
    if (!data.ok) {
      clearStaleTargetAfterFailedSelection(data.error || "Could not read a selection from Stellarium.");
      return;
    }
    state.currentTarget = TargetModel.buildTargetFromSelection(data);
    renderTargetCard();
  } catch (err) {
    setStellariumIndicator(false);
    // Requirement: a network/JSON failure here must clear the stale
    // target exactly like an ok:false response does (currentTarget,
    // About This Object, "Open in ESASky", pending imagery
    // requests/styling) -- not just swap the visible message while
    // leaving the prior target fully actionable underneath it.
    clearStaleTargetAfterFailedSelection("Could not reach the local bridge server. Is it still running?");
  } finally {
    el.btnRefreshSelection.disabled = false;
    el.btnRefreshSelection.textContent = "Use Stellarium Selection";
  }
});

// Requirement: a failed/empty /api/selection must not leave the *prior*
// target's card, "About This Object" info, "Open in ESASky" button, or
// active imagery-button styling looking usable -- and any imagery request
// still in flight for that prior target must be cancelled rather than
// resolved against the new (missing) target. Does NOT touch onlineMode or
// an already-open ESASky iframe -- see target_model.js buildFailedSelectionState.
function clearStaleTargetAfterFailedSelection(message) {
  const cleared = TargetModel.buildFailedSelectionState(state);

  cleared.timeoutIdsToClear.forEach((id) => clearTimeout(id));

  state.currentTarget = cleared.currentTarget;
  state.pendingHipsRequest = cleared.pendingHipsRequest;
  state.pendingChangeRequest = cleared.pendingChangeRequest;
  state.activeImageryButtonId = cleared.activeImageryButtonId;
  state.hipsNavTargetKey = null;
  HipsLayerControl.resetAll(state.hipsLayer);
  updateImageryButtonPresentations();
  updateRestoreLayerControl();
  renderHipsDiagnostics();

  el.targetCard.className = "target-card target-card-empty";
  el.targetCard.innerHTML = `<div class="target-empty-msg">${escapeHtml(message)}</div>`;
  el.btnOpenEsasky.disabled = cleared.openEsaskyDisabled;
  el.aboutObjectCard.hidden = cleared.aboutObjectCardHidden;
  el.aboutObjectBody.innerHTML = "";
  el.solarSystemNoticeCard.hidden = true;
  el.solarSystemNoticeBody.innerHTML = "";
  resetPlanetaryImagePanel();

  disableImageryButtons(false);
  setImageryStatus("", null);
}

// -- Manual entry form ----------------------------------------------------

el.manualForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  el.manualFormError.hidden = true;
  const ra = el.manualRa.value.trim();
  const dec = el.manualDec.value.trim();
  const name = el.manualName.value.trim();

  try {
    const url = `/api/manual/validate?ra=${encodeURIComponent(ra)}&dec=${encodeURIComponent(dec)}`;
    const resp = await fetch(url, { cache: "no-store" });
    const data = await resp.json();
    if (!data.ok) {
      el.manualFormError.textContent = data.error || "Could not parse those coordinates.";
      el.manualFormError.hidden = false;
      return;
    }
    state.currentTarget = TargetModel.buildTargetFromManual(data, name);
    renderTargetCard();
  } catch (err) {
    el.manualFormError.textContent = "Could not reach the local bridge server.";
    el.manualFormError.hidden = false;
  }
});

// -- Online Archive Mode toggle -----------------------------------------

el.onlineModeToggle.addEventListener("change", () => {
  if (el.onlineModeToggle.checked) {
    turnOnlineModeOn();
  } else {
    turnOnlineModeOff();
  }
});

function turnOnlineModeOn() {
  state.onlineMode = true;
  el.archiveModeIndicator.classList.remove("status-on", "status-off");
  el.archiveModeIndicator.classList.add("status-on");
  el.archiveModeIndicator.querySelector(".status-text").textContent = "Online Archive Mode: On";
  if (state.currentTarget) {
    syncPlanetaryImagePanel(state.currentTarget);
    syncArchiveAvailabilityChecks(state.currentTarget);
  }
}

// Requirement: "Online Mode Off" must really turn everything off -- cancel
// pending timers/requests, blank and hide the iframe, reset ready state,
// clear active button styling, and prevent further commands until the
// user explicitly re-enables it.
function turnOnlineModeOff() {
  const shutdown = OnlineMode.buildShutdownState(state);

  shutdown.timeoutIdsToClear.forEach((id) => clearTimeout(id));

  state.onlineMode = shutdown.onlineMode;
  state.pendingHipsRequest = shutdown.pendingHipsRequest;
  state.pendingChangeRequest = shutdown.pendingChangeRequest;
  state.activeImageryButtonId = shutdown.activeImageryButtonId;
  // Invalidates the active generation (EsaskyQueue.reset sets
  // state.esaskyQueue.cancelled = true) *before* the iframe src is set to
  // about:blank below. Any load handler still attached at this point --
  // stale or not -- is also detached outright, so the about:blank
  // navigation this triggers cannot reach it at all; and even if it
  // somehow did, markReadyIfActive() would still refuse to act because
  // the session is now cancelled.
  EsaskyQueue.reset(state.esaskyQueue, shutdown.esaskyQueueResetListenerFlag);
  if (esaskyLoadHandler) {
    el.esaskyFrame.removeEventListener("load", esaskyLoadHandler);
    esaskyLoadHandler = null;
  }

  el.esaskyFrame.src = shutdown.iframeSrc;
  el.esaskyFrameWrap.hidden = shutdown.iframeHidden;
  el.viewerStatus.textContent = shutdown.viewerStatusText;
  setImageryStatus(shutdown.imageryStatusText, null);
  disableImageryButtons(false);
  document.querySelectorAll(".imagery-btn").forEach((b) => {
    b.classList.remove("active");
    b.classList.remove("switching");
  });
  // Prefer the tracked imagery grid children in the test DOM stub.
  if (el.imageryGrid && Array.isArray(el.imageryGrid._children)) {
    el.imageryGrid._children.forEach((b) => {
      if (b && b.classList) {
        b.classList.remove("active");
        b.classList.remove("switching");
      }
    });
  }

  el.archiveModeIndicator.classList.remove("status-on", "status-off");
  el.archiveModeIndicator.classList.add("status-off");
  el.archiveModeIndicator.querySelector(".status-text").textContent = "Online Archive Mode: Off";
  el.onlineModeToggle.checked = false;
  resetPlanetaryImagePanel();
  ArchiveAvailability.resetForOffline(state.archiveAvailability);
  resetArchiveAvailabilityLights();
  clearHipsPendingTimers();
  HipsLayerControl.resetAll(state.hipsLayer);
  state.hipsNavTargetKey = null;
  state.activeImageryButtonId = null;
  updateImageryButtonPresentations();
  updateRestoreLayerControl();
  renderHipsDiagnostics();
}

// -- ESASky embed + control ----------------------------------------------

el.btnOpenEsasky.addEventListener("click", () => {
  if (!state.currentTarget) return;
  if (!state.onlineMode) {
    el.onlineModeToggle.checked = true;
    el.onlineModeToggle.dispatchEvent(new Event("change"));
  }
  openOrUpdateEsasky(state.currentTarget);
});

function openOrUpdateEsasky(target) {
  if (!state.onlineMode) return; // commands are never issued while offline
  el.esaskyFrameWrap.hidden = false;
  const params = new URLSearchParams({
    hide_welcome: "true",
    hide_banner_info: "true",
    sci: "true",
    cooframe: "J2000",
    target: `${target.ra_deg} ${target.dec_deg}`,
  });
  const viewerFov = getViewerFovDeg(target);
  if (viewerFov) params.set("fov", String(Math.min(180, Math.max(0.0001, viewerFov))));

  if (!state.esaskyQueue.loadListenerAttached) {
    el.viewerStatus.textContent = "Loading ESASky…";
    state.esaskyQueue.loadListenerAttached = true;
    // A fresh session: bump the generation token and reset queue.ready to
    // false *before* the navigation begins, per the browser-state
    // contract in esasky_queue.js. The load handler below captures this
    // generation and will refuse to mark the queue ready for any load
    // event that isn't this exact, still-current session -- including a
    // stale about:blank load triggered by turning Online Archive Mode
    // off while this navigation is still in flight (see
    // turnOnlineModeOff()).
    const generation = EsaskyQueue.beginSession(state.esaskyQueue);
    attachEsaskyLoadHandler(generation);
    el.esaskyFrame.src = `${ESASKY_ORIGIN}/esasky?${params.toString()}`;
  } else if (state.esaskyQueue.ready) {
    sendEsaskyCommand("goToRaDec", { ra: target.ra_deg, dec: target.dec_deg }, "goToRaDec");
    if (viewerFov) sendEsaskyCommand("setFov", { fov: viewerFov }, "setFov");
    el.viewerStatus.textContent = "View updated.";
  } else {
    // The iframe load has been kicked off but hasn't fired yet; queue the
    // update rather than sending (or dropping) it now. If the user picks
    // a different target again before the load completes, the replaceKey
    // ensures the newest goToRaDec/setFov replace the previous ones
    // rather than piling up -- the viewer will land on the latest target,
    // never an old one it "caught up" to after the fact.
    sendEsaskyCommand("goToRaDec", { ra: target.ra_deg, dec: target.dec_deg }, "goToRaDec");
    if (viewerFov) sendEsaskyCommand("setFov", { fov: viewerFov }, "setFov");
    el.viewerStatus.textContent = "Loading ESASky…";
  }
}

// The iframe's `load` handler, kept as a single named/removable function
// reference (rather than an anonymous closure) so a stale one can always
// be detached deterministically instead of relying solely on it noticing
// it's stale when it fires. Re-entrant: attaching a new handler always
// detaches whatever was previously attached first, so at most one `load`
// listener is ever registered on the iframe at a time.
let esaskyLoadHandler = null;

function attachEsaskyLoadHandler(generation) {
  if (esaskyLoadHandler) {
    el.esaskyFrame.removeEventListener("load", esaskyLoadHandler);
  }
  esaskyLoadHandler = function onEsaskyIframeLoad() {
    el.esaskyFrame.removeEventListener("load", esaskyLoadHandler);
    esaskyLoadHandler = null;
    // Belt-and-suspenders even after the removeEventListener() above:
    // markReadyIfActive() independently refuses to act unless Online
    // Archive Mode is still on and `generation` is still the queue's
    // current, non-cancelled session -- so even an about:blank load that
    // slips in before removal (or a handler this function doesn't own)
    // can never mark the queue ready.
    if (!state.onlineMode) return;
    const activated = EsaskyQueue.markReadyIfActive(state.esaskyQueue, generation, dispatchEsaskyCommand);
    if (activated) {
      el.viewerStatus.textContent = "ESASky loaded.";
    }
  };
  el.esaskyFrame.addEventListener("load", esaskyLoadHandler);
}

function dispatchEsaskyCommand(cmd) {
  if (!el.esaskyFrame.contentWindow) return;
  el.esaskyFrame.contentWindow.postMessage({ event: cmd.event, content: cmd.content }, ESASKY_ORIGIN);
}

// If an ESASky session has started (loadListenerAttached) but the one-shot
// load handler already ran without marking the queue ready — e.g. the
// session generation was cancelled while the iframe was still loading —
// later goToRaDec/setFov commands would queue forever with no handler left
// to flush them. Detect that zombie state (no pending load handler, iframe
// already on sky.esa.int) and mark ready before the next command is sent.
// Deliberately does nothing while esaskyLoadHandler is still attached:
// that means a navigation is genuinely in flight and the normal load path
// must still own readiness.
function recoverZombieEsaskyQueueIfNeeded() {
  const q = state.esaskyQueue;
  if (!state.onlineMode || !q.loadListenerAttached || q.ready) return;
  if (esaskyLoadHandler) return;
  const src = String(el.esaskyFrame.src || "");
  if (!src.startsWith(ESASKY_ORIGIN)) return;
  q.cancelled = false;
  EsaskyQueue.markReady(q, dispatchEsaskyCommand);
}

// getAvailableHips, changeHips, goToRaDec, and setFov must never be sent
// until the ESASky iframe has finished loading -- route everything
// through the command queue rather than postMessage directly. `replaceKey`
// (only used for goToRaDec/setFov) lets a newer target's navigation
// commands replace an older, still-queued target's rather than
// accumulating both -- see EsaskyQueue.enqueueOrSend.
function sendEsaskyCommand(event, content, replaceKey) {
  if (!state.onlineMode) return;
  recoverZombieEsaskyQueueIfNeeded();
  EsaskyQueue.enqueueOrSend(state.esaskyQueue, dispatchEsaskyCommand, { event, content, replaceKey });
}

window.addEventListener("message", (e) => {
  if (e.origin !== ESASKY_ORIGIN) return;
  handleEsaskyMessage(e.data);
});

function handleEsaskyMessage(data) {
  if (!data || typeof data !== "object") return;

  if (state.pendingChangeRequest) {
    if (HipsLayerControl.isStale(state.hipsLayer, state.pendingChangeRequest.generation)) {
      clearHipsPendingTimers();
      return;
    }
    const result = ChangeHips.interpretChangeHipsMessage(state.pendingChangeRequest, data);
    if (result.status !== "unrelated") {
      resolveChangeHipsRequest(result);
      return;
    }
  }

  if (state.pendingHipsRequest && ImageryMatching.looksLikeHipsListing(data)) {
    if (HipsLayerControl.isStale(state.hipsLayer, state.pendingHipsRequest.generation)) {
      clearTimeout(state.pendingHipsRequest.timeoutId);
      state.pendingHipsRequest = null;
      return;
    }
    clearTimeout(state.pendingHipsRequest.timeoutId);
    const req = state.pendingHipsRequest;
    state.pendingHipsRequest = null;
    resolveImageryListing(req.buttonId, data, req.generation);
  }
}

// -- Archive availability (MAST) ----------------------------------------

function imageryIdForMission(mission) {
  return Object.keys(IMAGERY_ARCHIVE_MISSION).find((id) => IMAGERY_ARCHIVE_MISSION[id] === mission) || null;
}

function resetArchiveAvailabilityLights() {
  state.archiveLights = {};
  state.discoveryBundle = null;
  state.discoveryInFlightKey = null;
  el.archiveObservationPanel.hidden = true;
  el.archiveObservationPanel.textContent = "";
  if (el.discoveryPanel) el.discoveryPanel.hidden = true;
  if (el.discoveryPanelBody) el.discoveryPanelBody.textContent = "";
  ArchiveAvailability.ARCHIVE_MISSIONS.forEach((mission) => {
    updateArchiveBadge(mission, {
      state: ArchiveAvailability.STATE.NOT_CHECKED,
      accessibleText: ArchiveAvailability.accessibleText(ArchiveAvailability.STATE.NOT_CHECKED, mission),
      observations: [],
    });
  });
}

function renderDiscoveryPanel(bundle) {
  if (!el.discoveryPanel || !el.discoveryPanelBody) return;
  el.discoveryPanelBody.textContent = "";
  if (!bundle) {
    el.discoveryPanel.hidden = true;
    return;
  }
  el.discoveryPanel.hidden = false;
  const view = DiscoveryPanel.buildPanelViewModel(bundle);

  const intro = document.createElement("p");
  intro.className = "discovery-intro";
  intro.textContent =
    "Scientific items and provider query outcomes are listed separately. " +
    "A zero result from one provider is not a claim that no scientific information exists.";
  el.discoveryPanelBody.appendChild(intro);

  (view.capabilityNotes || []).forEach((note) => {
    const p = document.createElement("p");
    p.className = "discovery-capability-note";
    p.textContent = note;
    el.discoveryPanelBody.appendChild(p);
  });

  (view.warnings || []).forEach((w) => {
    const p = document.createElement("p");
    p.className = "discovery-warning";
    p.textContent = w;
    el.discoveryPanelBody.appendChild(p);
  });

  if (view.emptyMessage) {
    const empty = document.createElement("p");
    empty.className = "discovery-empty";
    empty.textContent = view.emptyMessage;
    el.discoveryPanelBody.appendChild(empty);
  }

  view.domains.forEach((domain) => {
    const section = document.createElement("details");
    section.className = "discovery-domain";
    section.open = true;
    const summary = document.createElement("summary");
    summary.textContent = domain.label + " (" + domain.items.length + ")";
    section.appendChild(summary);
    domain.items.forEach((item) => {
      const row = document.createElement("div");
      row.className = "discovery-item";
      const text = document.createElement("div");
      text.className = "discovery-item-summary";
      text.textContent = DiscoveryPanel.summarizeItem(item);
      row.appendChild(text);
      const meta = document.createElement("div");
      meta.className = "discovery-item-meta";
      meta.textContent =
        "Type: " +
        (item.result_type || "") +
        " · Provider: " +
        (item.provider || "") +
        (item.match_basis ? " · " + DiscoveryPanel.matchBasisLabel(item.match_basis) : "");
      row.appendChild(meta);
      if (item.provenance_url && String(item.provenance_url).indexOf("https://") === 0) {
        const link = document.createElement("a");
        link.href = item.provenance_url;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.textContent = "Source";
        row.appendChild(link);
      }
      section.appendChild(row);
    });
    el.discoveryPanelBody.appendChild(section);
  });

  if (view.statusOutcomes && view.statusOutcomes.length) {
    const outcomesWrap = document.createElement("details");
    outcomesWrap.className = "discovery-outcomes";
    const osum = document.createElement("summary");
    osum.textContent = "Provider query outcomes (" + view.statusOutcomes.length + ")";
    outcomesWrap.appendChild(osum);
    view.statusOutcomes.forEach((outcome) => {
      const row = document.createElement("div");
      row.className = "discovery-outcome discovery-outcome-" + (outcome.query_status || "unknown");
      const head = document.createElement("div");
      head.className = "discovery-outcome-title";
      head.textContent =
        DiscoveryPanel.outcomeSectionTitle(outcome.query_status) +
        " — " +
        (outcome.provider || "provider") +
        (outcome.mission ? " / " + outcome.mission : "");
      row.appendChild(head);
      if (outcome.message && DiscoveryPanel.assertHonestText(outcome.message)) {
        const msg = document.createElement("div");
        msg.className = "discovery-outcome-message";
        msg.textContent = outcome.message;
        row.appendChild(msg);
      } else if (outcome.message) {
        const msg = document.createElement("div");
        msg.className = "discovery-outcome-message";
        msg.textContent =
          "No matching observations were returned by this provider for this position and search radius.";
        row.appendChild(msg);
      }
      outcomesWrap.appendChild(row);
    });
    el.discoveryPanelBody.appendChild(outcomesWrap);
  }
}

// -- ESASky HiPS survey-layer control (separate from MAST discovery) -----

function clearHipsPendingTimers() {
  if (state.pendingHipsRequest && state.pendingHipsRequest.timeoutId) {
    clearTimeout(state.pendingHipsRequest.timeoutId);
  }
  if (state.pendingChangeRequest && state.pendingChangeRequest.timeoutId) {
    clearTimeout(state.pendingChangeRequest.timeoutId);
  }
  state.pendingHipsRequest = null;
  state.pendingChangeRequest = null;
}

function invalidateHipsPendingWork() {
  clearHipsPendingTimers();
  HipsLayerControl.invalidatePending(state.hipsLayer);
  state.activeImageryButtonId = state.hipsLayer.acknowledgedImageryButtonId;
  updateImageryButtonPresentations();
  updateRestoreLayerControl();
  renderHipsDiagnostics();
  applyHipsStatusFromState();
}

function updateImageryButtonPresentations() {
  forEachImageryButton((b) => {
    b.classList.remove("active", "switching");
    const id = b.dataset.id;
    const pres = HipsLayerControl.buttonPresentation(state.hipsLayer, id);
    if (pres.activeClass) b.classList.add("active");
    if (pres.switchingClass) b.classList.add("switching");
  });
}

function applyHipsStatusFromState() {
  const msg = HipsLayerControl.buildStatusMessage(state.hipsLayer);
  setImageryStatus(msg.text, msg.kind);
}

function renderHipsDiagnostics() {
  if (!el.hipsDiagnostics) return;
  const snap = HipsLayerControl.diagnosticSnapshot(state.hipsLayer);
  const lines = [];
  if (snap.requestedSurveyName) {
    lines.push("Requested survey: " + snap.requestedSurveyName);
  }
  if (snap.acknowledgementSurveyName) {
    lines.push("Acknowledged survey: " + snap.acknowledgementSurveyName);
  }
  if (snap.uiState && snap.uiState !== HipsLayerControl.UI.AVAILABLE) {
    lines.push("Request state: " + snap.uiState);
  }
  if (snap.failureReason) {
    lines.push("Detail: " + snap.failureReason);
  }
  el.hipsDiagnostics.textContent = "";
  if (!lines.length) {
    el.hipsDiagnostics.hidden = true;
    return;
  }
  el.hipsDiagnostics.hidden = false;
  lines.forEach((line) => {
    const row = document.createElement("div");
    row.className = "hips-diag-line";
    row.textContent = line;
    el.hipsDiagnostics.appendChild(row);
  });
}

function updateRestoreLayerControl() {
  if (!el.hipsRestoreWrap || !el.btnHipsRestore) return;
  const show = HipsLayerControl.shouldShowRestoreAction(state.hipsLayer);
  const action = show ? HipsLayerControl.getRestoreAction(state.hipsLayer) : null;
  if (!action) {
    el.hipsRestoreWrap.hidden = true;
    el.btnHipsRestore.textContent = "";
    el.btnHipsRestore.onclick = null;
    return;
  }
  el.hipsRestoreWrap.hidden = false;
  el.btnHipsRestore.textContent = action.label;
  el.btnHipsRestore.onclick = () => {
    if (!state.currentTarget) return;
    if (!state.onlineMode) {
      el.onlineModeToggle.checked = true;
      el.onlineModeToggle.dispatchEvent(new Event("change"));
    }
    clearHipsPendingTimers();
    const cfg =
      IMAGERY_BUTTONS.find((c) => c.id === action.buttonId) || {
        id: action.buttonId,
        label: action.buttonId,
      };
    openOrUpdateEsasky(state.currentTarget);
    requestChangeHips(cfg, action.hipsName, action.kind);
  };
}

function applyDiscoveryBadges(badges) {
  const ackId = state.hipsLayer.acknowledgedImageryButtonId;
  ArchiveAvailability.ARCHIVE_MISSIONS.forEach((mission) => {
    const payload = badges && badges[mission];
    const imageryId = imageryIdForMission(mission);
    const activeMission = imageryId && imageryId === ackId ? mission : null;
    const light = ArchiveAvailability.mapBadgePayloadToLight(payload, mission, activeMission);
    updateArchiveBadge(mission, light);
  });
}

async function syncArchiveAvailabilityChecks(target) {
  if (!state.onlineMode || !target) {
    resetArchiveAvailabilityLights();
    return;
  }
  ArchiveAvailability.resetForTargetChange(state.archiveAvailability, target.ra_deg, target.dec_deg);
  const generation = state.archiveAvailability.generation;
  const nowMs = Date.now();

  // Mark Solar System / moving targets so the server skips historical archive claims.
  const moving = typeof SolarSystem !== "undefined" && SolarSystem.isSolarSystemTarget(target);
  const requestTarget = Object.assign({}, target, { moving_target: !!moving });

  const discoveryKey =
    ArchiveAvailability.normalizeCoordKey(target.ra_deg, target.dec_deg) +
    "|discovery|" +
    (target.name || "");

  if (ArchiveAvailability.shouldUseCache(state.archiveAvailability, discoveryKey, nowMs)) {
    const cached = state.archiveAvailability.cache[discoveryKey].payload;
    state.discoveryBundle = cached.bundle || null;
    renderDiscoveryPanel(state.discoveryBundle);
    applyDiscoveryBadges(cached.badges || {});
    return;
  }

  if (ArchiveAvailability.shouldRateLimit(state.archiveAvailability, discoveryKey, nowMs)) {
    return;
  }
  if (ArchiveAvailability.shouldSkipInFlight(state.archiveAvailability, discoveryKey)) {
    return;
  }

  ArchiveAvailability.markInFlight(state.archiveAvailability, discoveryKey);
  state.archiveAvailability.lastRequestAt[discoveryKey] = nowMs;
  state.discoveryInFlightKey = discoveryKey;

  ArchiveAvailability.ARCHIVE_MISSIONS.forEach((mission) => {
    updateArchiveBadge(mission, {
      state: ArchiveAvailability.STATE.CHECKING,
      accessibleText: ArchiveAvailability.accessibleText(ArchiveAvailability.STATE.CHECKING, mission),
      observations: [],
    });
  });

  try {
    // Single request feeds both the discovery panel and badge compatibility adapter.
    // Do not also call /api/archive-availability for the same target selection.
    const resp = await fetch(ArchiveAvailability.buildDiscoveryApiUrl(requestTarget), {
      cache: "no-store",
    });
    const data = await resp.json();
    if (ArchiveAvailability.isStale(state.archiveAvailability, generation)) {
      return;
    }
    ArchiveAvailability.clearInFlight(state.archiveAvailability, discoveryKey);
    ArchiveAvailability.storeCache(state.archiveAvailability, discoveryKey, data, Date.now());
    state.discoveryBundle = (data && data.bundle) || null;
    renderDiscoveryPanel(state.discoveryBundle);
    applyDiscoveryBadges((data && data.badges) || {});
  } catch (_err) {
    if (ArchiveAvailability.isStale(state.archiveAvailability, generation)) return;
    ArchiveAvailability.clearInFlight(state.archiveAvailability, discoveryKey);
    state.discoveryBundle = null;
    renderDiscoveryPanel(null);
    ArchiveAvailability.ARCHIVE_MISSIONS.forEach((mission) => {
      updateArchiveBadge(mission, {
        state: ArchiveAvailability.STATE.UNAVAILABLE,
        accessibleText: ArchiveAvailability.accessibleText(ArchiveAvailability.STATE.UNAVAILABLE, mission),
        observations: [],
      });
    });
  }
}

async function fetchArchiveMission(target, mission, key, generation, includeObservations) {
  // Legacy per-mission path retained for tests/exports but unused by sync when
  // /api/discovery is available. Prefer syncArchiveAvailabilityChecks.
  try {
    const resp = await fetch(
      ArchiveAvailability.buildApiUrl(target.ra_deg, target.dec_deg, mission, includeObservations),
      { cache: "no-store" }
    );
    const data = await resp.json();
    if (ArchiveAvailability.isStale(state.archiveAvailability, generation)) {
      return;
    }
    ArchiveAvailability.clearInFlight(state.archiveAvailability, key);
    ArchiveAvailability.storeCache(state.archiveAvailability, key, data, Date.now());
    const imageryId = imageryIdForMission(mission);
    const activeMission = imageryId && imageryId === state.activeImageryButtonId ? mission : null;
    updateArchiveBadge(mission, ArchiveAvailability.mapApiToLight(data, mission, activeMission));
  } catch (_err) {
    if (ArchiveAvailability.isStale(state.archiveAvailability, generation)) return;
    ArchiveAvailability.clearInFlight(state.archiveAvailability, key);
    updateArchiveBadge(mission, {
      state: ArchiveAvailability.STATE.UNAVAILABLE,
      accessibleText: ArchiveAvailability.accessibleText(ArchiveAvailability.STATE.UNAVAILABLE, mission),
      observations: [],
    });
  }
}

function updateArchiveBadge(mission, light) {
  state.archiveLights[mission] = light;
  const imageryId = imageryIdForMission(mission);
  if (!imageryId) return;
  const btn = el.imageryGrid.querySelector(`[data-id="${imageryId}"]`);
  if (!btn) return;
  let badge = btn.querySelector(".archive-badge");
  if (!badge) {
    badge = document.createElement("span");
    badge.className = "archive-badge";
    btn.appendChild(badge);
  }
  badge.className = "archive-badge archive-badge-" + light.state;
  badge.textContent = light.accessibleText;
  badge.setAttribute("aria-label", light.accessibleText);
  badge.title = light.accessibleText;
  if (light.state === ArchiveAvailability.STATE.CONFIRMED && light.observations && light.observations.length) {
    badge.style.cursor = "pointer";
    badge.onclick = (ev) => {
      ev.stopPropagation();
      renderArchiveObservationPanel(mission, light);
    };
  } else {
    badge.onclick = null;
    badge.style.cursor = "default";
  }
}

function renderArchiveObservationPanel(mission, light) {
  el.archiveObservationPanel.hidden = false;
  el.archiveObservationPanel.textContent = "";
  const heading = document.createElement("h3");
  heading.textContent = ArchiveAvailability.missionLabel(mission) + " archive observations (metadata summary)";
  el.archiveObservationPanel.appendChild(heading);
  const note = document.createElement("p");
  note.className = "archive-panel-note";
  note.textContent =
    "These are MAST CAOM metadata records near the current coordinates. Counts are not unique photographs " +
    "and do not prove ESASky is displaying a specific observation.";
  el.archiveObservationPanel.appendChild(note);
  (light.observations || []).forEach((obs) => {
    const row = document.createElement("div");
    row.className = "archive-obs-row";
    const fields = [
      ["Mission", obs.mission],
      ["Instrument", obs.instrument],
      ["Observation ID", obs.observation_id],
      ["Date", obs.observation_date],
      ["Preview listed", obs.preview_available ? "Yes (metadata indicates a preview may exist)" : "Not indicated"],
    ];
    fields.forEach(([label, value]) => {
      if (!value) return;
      const line = document.createElement("div");
      const l = document.createElement("span");
      l.className = "archive-obs-label";
      l.textContent = label + ": ";
      const v = document.createElement("span");
      v.className = "archive-obs-value";
      v.textContent = String(value);
      line.appendChild(l);
      line.appendChild(v);
      row.appendChild(line);
    });
    if (obs.source_link && obs.source_link.indexOf("https://mast.stsci.edu") === 0) {
      const link = document.createElement("a");
      link.href = obs.source_link;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = "Official MAST source";
      row.appendChild(link);
    }
    el.archiveObservationPanel.appendChild(row);
  });
}

function refreshSelectedArchiveLayerBadge() {
  // Prefer badges from the last discovery response when cached.
  const discoveryKey =
    state.archiveAvailability.coordKey &&
    state.archiveAvailability.coordKey +
      "|discovery|" +
      ((state.currentTarget && state.currentTarget.name) || "");
  const discoveryCached =
    discoveryKey && state.archiveAvailability.cache[discoveryKey]
      ? state.archiveAvailability.cache[discoveryKey].payload
      : null;
  if (discoveryCached && discoveryCached.badges) {
    applyDiscoveryBadges(discoveryCached.badges);
    return;
  }
  ArchiveAvailability.ARCHIVE_MISSIONS.forEach((mission) => {
    const imageryId = imageryIdForMission(mission);
    const existing = state.archiveLights[mission];
    if (!existing) return;
    if (imageryId === state.activeImageryButtonId) {
      updateArchiveBadge(mission, ArchiveAvailability.mapApiToLight({ status: existing.state, count: existing.count, observations: existing.observations }, mission, mission));
    } else if (existing.state === ArchiveAvailability.STATE.SELECTED_LAYER) {
      const key = state.archiveAvailability.coordKey;
      const cached = key && state.archiveAvailability.cache[key + "|" + mission];
      updateArchiveBadge(mission, ArchiveAvailability.mapApiToLight(cached ? cached.payload : null, mission, null));
    }
  });
}

// -- Watchlist -----------------------------------------------------------

function setWatchlistStatus(kind, message) {
  el.watchlistStatus.textContent = message;
  el.watchlistStatus.className = "watchlist-status" + (kind ? " watchlist-status-" + kind : "");
}

function watchlistWritesAllowed() {
  const status = state.watchlistLoadStatus.status;
  return status !== "loading" && status !== "load_failed";
}

function updateWatchlistControlsDisabled() {
  const blocked = !watchlistWritesAllowed();
  el.btnWatchlistAdd.disabled = blocked;
  el.btnApophisAdd.disabled = blocked;
  el.btnWatchlistRefresh.disabled = blocked;
}

function markWatchlistLoadFailed(message) {
  state.watchlistLoadStatus = {
    status: "load_failed",
    entryCount: state.watchlistLoadStatus.entryCount || 0,
    storagePathRelative: state.watchlistLoadStatus.storagePathRelative || "runtime_data/tracked_objects.json",
    recoveredFromBackup: false,
    error: message,
  };
  setWatchlistStatus("error", "Watchlist load failed: " + message + " Existing saved entries have not been replaced.");
  renderWatchlistPanel();
}

function getNoteDraft(entry) {
  const draft = state.watchlistNoteDrafts[entry.watchlist_id];
  if (draft && draft.text !== undefined) return draft.text;
  return entry.personal_note || "";
}

function getNoteDraftStatus(entry) {
  return (state.watchlistNoteDrafts[entry.watchlist_id] && state.watchlistNoteDrafts[entry.watchlist_id].status) || "saved";
}

function setNoteDraft(entry, text, status, error) {
  state.watchlistNoteDrafts[entry.watchlist_id] = {
    text: text,
    status: status || "saved",
    error: error || null,
  };
}

function hydrateApophisFromEntry(entry) {
  state.apophisShowingCached = false;
  state.apophisRequest.lastPayload = null;
  if (entry && entry.tracker_cache && entry.tracker_cache.summary) {
    state.apophisRequest.lastPayload = entry.tracker_cache.summary;
    state.apophisShowingCached = true;
  }
}

function updateApophisActionButton() {
  if (Watchlist.hasApophisEntry(state.watchlistDocument)) {
    el.btnApophisAdd.textContent = "Open Apophis Tracker";
  } else {
    el.btnApophisAdd.textContent = "Add Apophis Tracker";
  }
}

function clearTrackedObjectDetails() {
  el.trackedObjectDetailsCard.hidden = true;
  el.trackedObjectDetailsCard.classList.remove("tracked-object-details-open");
  el.trackedObjectDetailsHeading.textContent = "Tracked Object Details";
  el.trackedObjectDetailsBody.textContent = "";
}

function appendTrackedDetailRow(container, label, value, extraClass) {
  if (value === null || value === undefined) return;
  const row = document.createElement("div");
  row.className = "tracked-detail-row";
  const labelEl = document.createElement("span");
  labelEl.className = "tracked-detail-label";
  labelEl.textContent = label + ": ";
  const valueEl = document.createElement("span");
  valueEl.className = "tracked-detail-value" + (extraClass ? " " + extraClass : "");
  valueEl.textContent = String(value);
  row.appendChild(labelEl);
  row.appendChild(valueEl);
  container.appendChild(row);
}

function renderTrackedObjectDetails(entry, options) {
  options = options || {};
  if (!entry) {
    clearTrackedObjectDetails();
    return;
  }
  el.trackedObjectDetailsCard.hidden = false;
  el.trackedObjectDetailsCard.classList.add("tracked-object-details-open");
  el.trackedObjectDetailsHeading.textContent = "Tracked Object Details — " + entry.display_name;
  el.trackedObjectDetailsBody.textContent = "";

  const isApophis = ApophisTracker.isApophisEntry(entry);
  const ephem = isApophis ? Watchlist.extractValidatedEphemeris(entry, state.apophisRequest.lastPayload) : null;

  const snapshotNote = document.createElement("p");
  snapshotNote.className = "tracked-detail-snapshot-note";
  if (isApophis) {
    snapshotNote.textContent = ephem
      ? "Ephemeris coordinates below are valid only for the displayed epoch and observer context — not a live position."
      : "This featured tracker does not replace the Selected Target until you explicitly use a validated ephemeris position.";
  } else {
    snapshotNote.textContent =
      "Coordinates below are a saved snapshot from when this entry was added or last refreshed — not a live position.";
  }
  el.trackedObjectDetailsBody.appendChild(snapshotNote);

  const savedNote = typeof entry.personal_note === "string" ? entry.personal_note : "";
  const draft = state.watchlistNoteDrafts[entry.watchlist_id];
  const draftText = draft && typeof draft.text === "string" ? draft.text : null;
  const draftStatus = draft ? draft.status : "saved";
  const hasUnsavedDraft = draftStatus === "unsaved" && draftText !== null && draftText !== savedNote;

  appendTrackedDetailRow(el.trackedObjectDetailsBody, "Display name", entry.display_name);
  appendTrackedDetailRow(el.trackedObjectDetailsBody, "Favorite", entry.favorite ? "Yes" : "No");
  appendTrackedDetailRow(el.trackedObjectDetailsBody, "Saved personal note", savedNote.length ? savedNote : "(none)");
  if (hasUnsavedDraft) {
    appendTrackedDetailRow(el.trackedObjectDetailsBody, "Unsaved draft", draftText, "tracked-detail-value-unsaved");
  }
  if (draftStatus === "saving") {
    appendTrackedDetailRow(el.trackedObjectDetailsBody, "Note save status", "Saving…");
  } else if (draftStatus === "failed") {
    appendTrackedDetailRow(el.trackedObjectDetailsBody, "Note save status", "Save failed — showing last saved note above");
  }
  if (isApophis) {
    if (ephem) {
      appendTrackedDetailRow(el.trackedObjectDetailsBody, "Ephemeris RA", Number(ephem.ra_deg).toFixed(4) + "°");
      appendTrackedDetailRow(el.trackedObjectDetailsBody, "Ephemeris Dec", Number(ephem.dec_deg).toFixed(4) + "°");
      if (ephem.epoch) appendTrackedDetailRow(el.trackedObjectDetailsBody, "Ephemeris epoch", ephem.epoch);
      if (ephem.retrieved_at) appendTrackedDetailRow(el.trackedObjectDetailsBody, "Ephemeris retrieved", ephem.retrieved_at);
      if (ephem.observer_context) {
        appendTrackedDetailRow(
          el.trackedObjectDetailsBody,
          "Observer context",
          JSON.stringify(ephem.observer_context)
        );
      }
      if (ephem.distance_au != null) {
        appendTrackedDetailRow(el.trackedObjectDetailsBody, "Ephemeris distance", ephem.distance_au + " au");
      }
      const useBtn = document.createElement("button");
      useBtn.className = "btn btn-secondary btn-small";
      useBtn.type = "button";
      useBtn.textContent = "Use Ephemeris Position";
      useBtn.addEventListener("click", () => applyApophisEphemerisToTarget(entry));
      el.trackedObjectDetailsBody.appendChild(useBtn);
      const ephemNote = document.createElement("p");
      ephemNote.className = "tracked-detail-snapshot-note";
      ephemNote.textContent =
        "Click Use Ephemeris Position to copy this epoch-limited position to the Selected Target card. It is not kept current automatically.";
      el.trackedObjectDetailsBody.appendChild(ephemNote);
    } else {
      appendTrackedDetailRow(
        el.trackedObjectDetailsBody,
        "Sky position",
        "No validated sky position has been saved for this tracker yet."
      );
    }
  } else {
    appendTrackedDetailRow(
      el.trackedObjectDetailsBody,
      "Saved RA",
      Number(entry.saved_ra_deg).toFixed(4) + "°"
    );
    appendTrackedDetailRow(
      el.trackedObjectDetailsBody,
      "Saved Dec",
      Number(entry.saved_dec_deg).toFixed(4) + "°"
    );
  }
  appendTrackedDetailRow(el.trackedObjectDetailsBody, "Object type", entry.normalized_object_type || "unknown");
  appendTrackedDetailRow(el.trackedObjectDetailsBody, "Coordinate source", entry.coordinate_source || "unknown");
  if (entry.source_identifier) {
    appendTrackedDetailRow(el.trackedObjectDetailsBody, "Source identifier", entry.source_identifier);
  }
  appendTrackedDetailRow(el.trackedObjectDetailsBody, "Date added", entry.date_added || "unknown");
  if (entry.last_refreshed) {
    appendTrackedDetailRow(el.trackedObjectDetailsBody, "Last refreshed", entry.last_refreshed);
  }
  if (ApophisTracker.isApophisEntry(entry)) {
    if (entry.tracker_cache && entry.tracker_cache.retrieved_at) {
      appendTrackedDetailRow(
        el.trackedObjectDetailsBody,
        "Tracker cache",
        "Cached summary from " + entry.tracker_cache.retrieved_at
      );
    } else {
      appendTrackedDetailRow(el.trackedObjectDetailsBody, "Tracker cache", "No cached tracker data yet");
    }
  }

  if (options.focusHeading) {
    try {
      el.trackedObjectDetailsHeading.focus({ preventScroll: true });
    } catch (_err) {
      el.trackedObjectDetailsHeading.focus();
    }
  }
}

function renderSelectedWatchlistPanels(options) {
  options = options || {};
  const entries = state.watchlistDocument.entries || [];
  const selected = entries.find((e) => e.watchlist_id === state.selectedWatchlistId);
  if (!selected) {
    clearTrackedObjectDetails();
    el.apophisTrackerBody.hidden = true;
    el.apophisTrackerBody.textContent = "";
    state.apophisShowingCached = false;
    return;
  }
  renderTrackedObjectDetails(selected, { focusHeading: !!options.focusHeading });
  if (ApophisTracker.isApophisEntry(selected)) {
    renderApophisTrackerPanel(selected);
  } else {
    el.apophisTrackerBody.hidden = true;
    el.apophisTrackerBody.textContent = "";
    state.apophisShowingCached = false;
  }
}

async function loadWatchlistFromServer() {
  setWatchlistStatus(null, "Loading watchlist from server…");
  state.watchlistLoadStatus.status = "loading";
  updateWatchlistControlsDisabled();
  try {
    const resp = await fetch("/api/watchlist", { cache: "no-store" });
    let data;
    try {
      data = await resp.json();
    } catch (_parseErr) {
      markWatchlistLoadFailed("Server returned unreadable watchlist data.");
      return;
    }
    if (!data.ok || !data.document) {
      markWatchlistLoadFailed(data.error || "Server did not return watchlist data.");
      return;
    }
    state.watchlistLoadStatus = {
      status: data.status || "loaded",
      entryCount: data.entry_count || 0,
      storagePathRelative: data.storage_path_relative || "runtime_data/tracked_objects.json",
      recoveredFromBackup: !!data.recovered_from_backup,
      error: null,
    };
    state.watchlistDocument = data.document;
    Watchlist.writeLocalCache(data.document);
    const savedSelected = localStorage.getItem("foxai_watchlist_selected_id");
    if (savedSelected && (data.document.entries || []).some((e) => e.watchlist_id === savedSelected)) {
      state.selectedWatchlistId = savedSelected;
      const selected = data.document.entries.find((e) => e.watchlist_id === savedSelected);
      if (selected && ApophisTracker.isApophisEntry(selected)) {
        hydrateApophisFromEntry(selected);
      }
    }
    let msg =
      "Watchlist loaded: " +
      state.watchlistLoadStatus.entryCount +
      " entr" +
      (state.watchlistLoadStatus.entryCount === 1 ? "y" : "ies") +
      " from " +
      state.watchlistLoadStatus.storagePathRelative;
    if (state.watchlistLoadStatus.recoveredFromBackup) {
      msg += " (recovered from backup)";
    }
    setWatchlistStatus("ok", msg);
    renderWatchlistPanel();
  } catch (_err) {
    markWatchlistLoadFailed("Could not reach the local server. Persisted entries were not loaded.");
  }
}

async function saveWatchlistDocument(document) {
  if (!watchlistWritesAllowed()) {
    setWatchlistStatus("error", "Watchlist unavailable — load must succeed before saving changes.");
    return { ok: false, error: "load_failed" };
  }
  setWatchlistStatus(null, "Saving watchlist…");
  let resp;
  try {
    resp = await fetch("/api/watchlist", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ document }),
    });
  } catch (_err) {
    setWatchlistStatus("error", "Watchlist save failed: could not reach the local server.");
    return { ok: false, error: "network" };
  }
  let data;
  try {
    data = await resp.json();
  } catch (_err) {
    setWatchlistStatus("error", "Watchlist save failed: server returned an unreadable response.");
    return { ok: false, error: "malformed" };
  }
  if (!data.ok || !data.document) {
    setWatchlistStatus("error", "Watchlist save failed: " + (data.error || "Server rejected the save."));
    return data;
  }
  state.watchlistDocument = data.document;
  state.watchlistLoadStatus.entryCount = data.entry_count || (data.document.entries || []).length;
  Watchlist.writeLocalCache(data.document);
  setWatchlistStatus(
    "ok",
    "Watchlist saved (" +
      state.watchlistLoadStatus.entryCount +
      " entr" +
      (state.watchlistLoadStatus.entryCount === 1 ? "y" : "ies") +
      ") to " +
      (data.storage_path_relative || state.watchlistLoadStatus.storagePathRelative)
  );
  renderWatchlistPanel();
  return data;
}

function renderWatchlistPanel() {
  el.watchlistExplainer.textContent = Watchlist.TRACKED_EXPLAINER;
  updateApophisActionButton();
  updateWatchlistControlsDisabled();
  el.watchlistList.textContent = "";
  if (state.watchlistLoadStatus.status === "load_failed") {
    const unavailable = document.createElement("p");
    unavailable.className = "watchlist-unavailable";
    unavailable.textContent =
      "Watchlist could not be loaded. Existing saved entries have not been replaced.";
    el.watchlistList.appendChild(unavailable);
    const retryBtn = document.createElement("button");
    retryBtn.className = "btn btn-secondary btn-small";
    retryBtn.type = "button";
    retryBtn.textContent = "Retry Load";
    retryBtn.addEventListener("click", () => loadWatchlistFromServer());
    el.watchlistList.appendChild(retryBtn);
    clearTrackedObjectDetails();
    el.apophisTrackerBody.hidden = true;
    el.apophisTrackerBody.textContent = "";
    return;
  }
  const entries = state.watchlistDocument.entries || [];
  if (!entries.length && state.watchlistLoadStatus.status !== "load_failed") {
    const empty = document.createElement("p");
    empty.className = "watchlist-empty";
    empty.textContent = "No tracked objects yet.";
    el.watchlistList.appendChild(empty);
    clearTrackedObjectDetails();
    el.apophisTrackerBody.hidden = true;
    el.apophisTrackerBody.textContent = "";
    return;
  }
  entries.forEach((entry) => {
    const row = document.createElement("div");
    row.className = "watchlist-row" + (entry.watchlist_id === state.selectedWatchlistId ? " selected" : "");
    const title = document.createElement("div");
    title.className = "watchlist-title";
    title.textContent = (entry.favorite ? "★ " : "") + entry.display_name;
    row.appendChild(title);
    const meta = document.createElement("div");
    meta.className = "watchlist-meta";
    if (ApophisTracker.isApophisEntry(entry) && Watchlist.isFeaturedTrackerPlaceholder(entry)) {
      meta.textContent = "Featured tracker — no validated sky snapshot yet";
    } else {
      meta.textContent =
        "Saved snapshot: RA " + Number(entry.saved_ra_deg).toFixed(4) + "°, Dec " + Number(entry.saved_dec_deg).toFixed(4) + "°";
    }
    row.appendChild(meta);
    if (entry.last_refreshed) {
      const refreshed = document.createElement("div");
      refreshed.className = "watchlist-refreshed";
      refreshed.textContent = "Last refreshed: " + entry.last_refreshed;
      row.appendChild(refreshed);
    }
    const noteStatus = document.createElement("div");
    noteStatus.className = "watchlist-note-status";
    const draftStatus = getNoteDraftStatus(entry);
    if (draftStatus === "saving") noteStatus.textContent = "Saving…";
    else if (draftStatus === "failed") noteStatus.textContent = "Save failed";
    else if (draftStatus === "unsaved") {
      noteStatus.textContent = "Unsaved changes";
      noteStatus.className = "watchlist-note-status watchlist-note-status-unsaved";
    } else noteStatus.textContent = "Saved";
    const noteInput = document.createElement("textarea");
    noteInput.className = "watchlist-note";
    noteInput.rows = 2;
    noteInput.value = getNoteDraft(entry);
    noteInput.placeholder = "Personal note (plain text)";
    noteInput.addEventListener("input", () => {
      setNoteDraft(entry, noteInput.value, "unsaved");
      noteStatus.textContent = "Unsaved changes";
      noteStatus.className = "watchlist-note-status watchlist-note-status-unsaved";
      if (state.selectedWatchlistId === entry.watchlist_id) {
        const current = (state.watchlistDocument.entries || []).find((e) => e.watchlist_id === entry.watchlist_id);
        if (current) renderTrackedObjectDetails(current);
      }
    });
    row.appendChild(noteInput);
    row.appendChild(noteStatus);
    const saveNoteBtn = document.createElement("button");
    saveNoteBtn.className = "btn btn-secondary btn-small";
    saveNoteBtn.type = "button";
    saveNoteBtn.textContent = "Save Note";
    saveNoteBtn.addEventListener("click", () => {
      if (!watchlistWritesAllowed()) return;
      saveWatchlistNote(entry.watchlist_id, noteInput, noteStatus);
    });
    row.appendChild(saveNoteBtn);
    const actions = document.createElement("div");
    actions.className = "watchlist-row-actions";
    const openBtn = document.createElement("button");
    openBtn.className = "btn btn-secondary btn-small";
    openBtn.type = "button";
    openBtn.textContent = "Open Details";
    openBtn.addEventListener("click", () => selectWatchlistEntry(entry.watchlist_id, { userInitiated: true }));
    actions.appendChild(openBtn);
    const favBtn = document.createElement("button");
    favBtn.className = "btn btn-secondary btn-small";
    favBtn.type = "button";
    favBtn.textContent = entry.favorite ? "Unfavorite" : "Favorite";
    favBtn.addEventListener("click", async () => {
      if (!watchlistWritesAllowed()) return;
      const updated = Watchlist.updateEntry(state.watchlistDocument, entry.watchlist_id, { favorite: !entry.favorite });
      await saveWatchlistDocument(updated);
    });
    actions.appendChild(favBtn);
    const removeBtn = document.createElement("button");
    removeBtn.className = "btn btn-secondary btn-small";
    removeBtn.type = "button";
    removeBtn.textContent = "Remove";
    removeBtn.addEventListener("click", async () => {
      if (!watchlistWritesAllowed()) return;
      const updated = Watchlist.removeEntry(state.watchlistDocument, entry.watchlist_id);
      if (state.selectedWatchlistId === entry.watchlist_id) {
        state.selectedWatchlistId = null;
        try {
          localStorage.removeItem("foxai_watchlist_selected_id");
        } catch (_err) {
          /* ignore */
        }
      }
      delete state.watchlistNoteDrafts[entry.watchlist_id];
      await saveWatchlistDocument(updated);
    });
    actions.appendChild(removeBtn);
    row.appendChild(actions);
    el.watchlistList.appendChild(row);
  });
  renderSelectedWatchlistPanels();
}

async function saveWatchlistNote(watchlistId, noteInput, noteStatusEl) {
  if (!watchlistWritesAllowed()) return;
  const entry = (state.watchlistDocument.entries || []).find((e) => e.watchlist_id === watchlistId);
  if (!entry) return;
  setNoteDraft(entry, noteInput.value, "saving");
  noteStatusEl.textContent = "Saving…";
  noteStatusEl.className = "watchlist-note-status";
  if (state.selectedWatchlistId === watchlistId) {
    renderTrackedObjectDetails(entry);
  }
  const updated = Watchlist.updateEntry(state.watchlistDocument, watchlistId, {
    personal_note: Watchlist.sanitizeNote(noteInput.value),
  });
  const result = await saveWatchlistDocument(updated);
  const freshEntry = (state.watchlistDocument.entries || []).find((e) => e.watchlist_id === watchlistId) || entry;
  if (result && result.ok) {
    setNoteDraft(freshEntry, freshEntry.personal_note, "saved");
    noteStatusEl.textContent = "Saved";
    noteStatusEl.className = "watchlist-note-status";
    if (state.selectedWatchlistId === watchlistId) {
      renderTrackedObjectDetails(freshEntry);
    }
  } else {
    setNoteDraft(freshEntry, noteInput.value, "failed", "save failed");
    noteStatusEl.textContent = "Save failed";
    noteStatusEl.className = "watchlist-note-status watchlist-note-status-error";
    if (state.selectedWatchlistId === watchlistId) {
      renderTrackedObjectDetails(freshEntry);
    }
  }
}

function selectWatchlistEntry(watchlistId, options) {
  options = options || {};
  state.selectedWatchlistId = watchlistId;
  try {
    localStorage.setItem("foxai_watchlist_selected_id", watchlistId);
  } catch (_err) {
    /* ignore */
  }
  const entry = (state.watchlistDocument.entries || []).find((e) => e.watchlist_id === watchlistId);
  if (!entry) {
    renderSelectedWatchlistPanels();
    return;
  }
  if (ApophisTracker.isApophisEntry(entry)) {
    hydrateApophisFromEntry(entry);
  } else {
    state.apophisShowingCached = false;
    state.apophisRequest.lastPayload = null;
    state.currentTarget = Watchlist.targetFromEntry(entry);
    renderTargetCard();
  }
  renderWatchlistPanel();
  if (options.userInitiated) {
    renderSelectedWatchlistPanels({ focusHeading: true });
  }
}

function applyApophisEphemerisToTarget(entry) {
  const ephem = Watchlist.extractValidatedEphemeris(entry, state.apophisRequest.lastPayload);
  if (!ephem) return;
  state.currentTarget = {
    name: entry.display_name,
    alt_name: entry.source_identifier,
    object_type: entry.normalized_object_type,
    ra_deg: ephem.ra_deg,
    dec_deg: ephem.dec_deg,
    source: "apophis_ephemeris:" + (ephem.epoch || "unknown"),
    fov_deg: null,
  };
  renderTargetCard();
}

async function addCurrentTargetToWatchlist() {
  if (!state.currentTarget || !watchlistWritesAllowed()) return;
  const updated = Watchlist.addEntry(state.watchlistDocument, Watchlist.entryFromTarget(state.currentTarget));
  await saveWatchlistDocument(updated);
}

async function openOrAddApophisTracker() {
  if (!watchlistWritesAllowed()) return;
  const existing = Watchlist.findApophisEntry(state.watchlistDocument);
  if (existing) {
    selectWatchlistEntry(existing.watchlist_id);
    return;
  }
  const updated = Watchlist.addEntry(state.watchlistDocument, Watchlist.buildApophisSeedEntry());
  const apophisEntry = Watchlist.findApophisEntry(updated);
  state.selectedWatchlistId = apophisEntry ? apophisEntry.watchlist_id : null;
  await saveWatchlistDocument(updated);
  if (apophisEntry) selectWatchlistEntry(apophisEntry.watchlist_id);
}

async function refreshSelectedWatchlistEntry() {
  const entry = (state.watchlistDocument.entries || []).find((e) => e.watchlist_id === state.selectedWatchlistId);
  if (!entry) return;
  if (ApophisTracker.isApophisEntry(entry)) {
    await refreshApophisTracker();
    return;
  }
  const now = new Date().toISOString();
  const updated = Watchlist.updateEntry(state.watchlistDocument, entry.watchlist_id, { last_refreshed: now });
  await saveWatchlistDocument(updated);
}

// -- Apophis tracker -----------------------------------------------------

function renderApophisTrackerPanel(entry) {
  el.apophisTrackerBody.hidden = false;
  el.apophisTrackerBody.textContent = "";
  const sectionHeading = document.createElement("h4");
  sectionHeading.className = "apophis-tracker-heading";
  sectionHeading.textContent = "JPL Apophis Tracker";
  el.apophisTrackerBody.appendChild(sectionHeading);
  const cached = state.apophisShowingCached && entry && entry.tracker_cache;
  const vm = ApophisTracker.buildViewModel(state.apophisRequest.lastPayload || {}, {
    fromCache: !!cached,
    cacheRetrievedAt: cached ? entry.tracker_cache.retrieved_at : null,
  });
  if (cached) {
    const cacheNote = document.createElement("p");
    cacheNote.className = "apophis-note";
    cacheNote.textContent =
      "Showing cached Apophis summary saved on " +
      (entry.tracker_cache.retrieved_at || "unknown time") +
      ". Use Refresh Selected to retrieve new official data when online.";
    el.apophisTrackerBody.appendChild(cacheNote);
  }
  const title = document.createElement("h3");
  title.textContent = vm.name + " (" + vm.designation + ")";
  el.apophisTrackerBody.appendChild(title);
  const lines = [
    ["Countdown to documented April 2029 encounter", vm.countdownDays != null ? vm.countdownDays + " days" : "Unavailable"],
    [
      "Encounter date (SBDB when supplied)",
      vm.encounterDateUnavailable ? "April 2029 encounter not found in SBDB close-approach list" : vm.encounterDate,
    ],
    ["Nominal close-approach distance", vm.nominalDistanceAu != null ? vm.nominalDistanceAu + " au" : null],
    ["Retrieved", vm.retrievedAt],
    ["Source agency", vm.sourceAgency],
    ["Risk status", vm.riskStatusAvailable ? vm.riskStatus : vm.riskNotice],
  ];
  lines.forEach(([label, value]) => {
    if (!value) return;
    const row = document.createElement("div");
    row.className = "apophis-row";
    const l = document.createElement("span");
    l.className = "apophis-label";
    l.textContent = label + ": ";
    const v = document.createElement("span");
    v.className = "apophis-value";
    v.textContent = String(value);
    row.appendChild(l);
    row.appendChild(v);
    el.apophisTrackerBody.appendChild(row);
  });
  if (vm.ephemeris && vm.ephemeris.ok) {
    const ephem = document.createElement("div");
    ephem.className = "apophis-row";
    ephem.textContent =
      "Ephemeris at retrieval epoch (" +
      (vm.ephemeris.epoch || vm.ephemerisEpoch || "unknown") +
      "): RA " +
      vm.ephemeris.ra_deg +
      "°, Dec " +
      vm.ephemeris.dec_deg +
      "°" +
      (vm.ephemeris.distance_au != null ? ", distance " + vm.ephemeris.distance_au + " au" : "") +
      ".";
    el.apophisTrackerBody.appendChild(ephem);
  } else if (vm.ephemeris && vm.ephemeris.error) {
    const ephemErr = document.createElement("div");
    ephemErr.className = "apophis-row";
    ephemErr.textContent = "Observer ephemeris: " + vm.ephemeris.error;
    el.apophisTrackerBody.appendChild(ephemErr);
  }
  if (vm.observerContext) {
    const obs = document.createElement("div");
    obs.className = "apophis-row";
    obs.textContent = "Observer context: " + JSON.stringify(vm.observerContext);
    el.apophisTrackerBody.appendChild(obs);
  }
  if (vm.observerPrivacyNotice) {
    const privacy = document.createElement("p");
    privacy.className = "apophis-privacy";
    privacy.textContent = vm.observerPrivacyNotice;
    el.apophisTrackerBody.appendChild(privacy);
  }
  if (vm.countdownNotice) {
    const countdownNote = document.createElement("p");
    countdownNote.className = "apophis-note";
    countdownNote.textContent = vm.countdownNotice;
    el.apophisTrackerBody.appendChild(countdownNote);
  }
  Object.keys(vm.sourceLinks || {}).forEach((key) => {
    const url = vm.sourceLinks[key];
    if (!url || url.indexOf("https://") !== 0) return;
    const link = document.createElement("a");
    link.href = url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = "Official source: " + key;
    el.apophisTrackerBody.appendChild(link);
  });
}

async function refreshApophisTracker() {
  const nowMs = Date.now();
  if (ApophisTracker.shouldSkipInFlight(state.apophisRequest)) {
    setWatchlistStatus(null, "Apophis refresh already in progress…");
    return;
  }
  if (ApophisTracker.shouldRateLimit(state.apophisRequest, nowMs)) {
    const msg = ApophisTracker.buildRateLimitMessage(state.apophisRequest, nowMs);
    if (msg) setWatchlistStatus(null, msg);
    return;
  }
  const generation = ApophisTracker.beginRequest(state.apophisRequest);
  state.apophisShowingCached = false;
  setWatchlistStatus(null, "Refreshing Apophis tracker from JPL…");
  try {
    const resp = await fetch(ApophisTracker.buildApiUrl(null), { cache: "no-store" });
    const data = await resp.json();
    if (ApophisTracker.isStale(state.apophisRequest, generation)) return;
    ApophisTracker.markComplete(state.apophisRequest, data, nowMs);
    const now = new Date().toISOString();
    if (state.selectedWatchlistId) {
      const cache = Watchlist.buildApophisTrackerCache(data, now);
      const updated = Watchlist.updateEntry(state.watchlistDocument, state.selectedWatchlistId, {
        last_refreshed: now,
        tracker_cache: cache,
      });
      await saveWatchlistDocument(updated);
      return;
    }
    renderWatchlistPanel();
  } catch (_err) {
    if (ApophisTracker.isStale(state.apophisRequest, generation)) return;
    state.apophisRequest.inFlight = false;
    setWatchlistStatus("error", "Apophis refresh failed: could not retrieve JPL data.");
  }
}

el.btnWatchlistAdd.addEventListener("click", () => addCurrentTargetToWatchlist());
el.btnApophisAdd.addEventListener("click", () => openOrAddApophisTracker());
el.btnWatchlistRefresh.addEventListener("click", () => refreshSelectedWatchlistEntry());

// -- Imagery buttons ----------------------------------------------------

function buildImageryButtons() {
  el.imageryGrid.innerHTML = "";
  for (const cfg of IMAGERY_BUTTONS) {
    const btn = document.createElement("button");
    btn.className = "imagery-btn";
    btn.dataset.id = cfg.id;
    btn.innerHTML =
      `${escapeHtml(cfg.label)}<span class="wave-tag">${escapeHtml(cfg.waveTag)}</span>` +
      (IMAGERY_ARCHIVE_MISSION[cfg.id] ? `<span class="archive-badge archive-badge-not_checked" aria-label="${escapeHtml(ArchiveAvailability.accessibleText(ArchiveAvailability.STATE.NOT_CHECKED, IMAGERY_ARCHIVE_MISSION[cfg.id]))}">${escapeHtml(ArchiveAvailability.accessibleText(ArchiveAvailability.STATE.NOT_CHECKED, IMAGERY_ARCHIVE_MISSION[cfg.id]))}</span>` : "");
    btn.title = cfg.explain;
    btn.addEventListener("click", () => onImageryButtonClick(cfg));
    el.imageryGrid.appendChild(btn);
  }

  el.wavelengthExplainer.innerHTML = IMAGERY_BUTTONS.map(
    (cfg) => `<li><strong>${escapeHtml(cfg.label)}:</strong> ${escapeHtml(cfg.explain)}</li>`
  ).join("");
}

function setImageryStatus(text, kind) {
  el.imageryStatus.textContent = text;
  el.imageryStatus.className = "imagery-status" + (kind ? ` status-${kind}` : "");
}

function onImageryButtonClick(cfg) {
  if (!state.currentTarget) {
    setImageryStatus("Load a target first (Stellarium selection or manual entry).", "error");
    return;
  }
  if (!state.onlineMode) {
    el.onlineModeToggle.checked = true;
    el.onlineModeToggle.dispatchEvent(new Event("change"));
  }

  // Newer card request supersedes any older pending HiPS listing/change.
  clearHipsPendingTimers();
  HipsLayerControl.invalidatePending(state.hipsLayer);

  openOrUpdateEsasky(state.currentTarget);

  // Pending/switching styling only — confirmed .active waits for acknowledgement.
  state.hipsLayer.requestedImageryButtonId = cfg.id;
  state.hipsLayer.uiState = HipsLayerControl.UI.SWITCHING;
  state.hipsLayer.requestedSurveyName = cfg.preferredExact || null;
  state.hipsLayer.layerCommandSent = false;
  updateImageryButtonPresentations();
  updateRestoreLayerControl();
  renderHipsDiagnostics();

  if (cfg.preferredExact) {
    requestChangeHips(cfg, cfg.preferredExact, HipsLayerControl.KIND.SWITCH);
    return;
  }

  requestHipsListingThenApply(cfg);
}

function requestHipsListingThenApply(cfg) {
  setImageryStatus(`Asking ESASky what's available for ${cfg.label}…`, "switching");
  disableImageryButtons(true);

  const generation = state.hipsLayer.generation;
  const timeoutId = setTimeout(() => {
    if (HipsLayerControl.isStale(state.hipsLayer, generation)) return;
    if (!state.pendingHipsRequest || state.pendingHipsRequest.generation !== generation) return;
    state.pendingHipsRequest = null;
    disableImageryButtons(false);
    state.hipsLayer.uiState = HipsLayerControl.UI.TIMED_OUT;
    state.hipsLayer.failureReason =
      "ESASky did not return a HiPS listing within the time limit.";
    state.hipsLayer.layerCommandSent = false;
    applyHipsStatusFromState();
    updateImageryButtonPresentations();
    updateRestoreLayerControl();
    renderHipsDiagnostics();
  }, 5000);

  state.pendingHipsRequest = { buttonId: cfg.id, timeoutId, generation };
  sendEsaskyCommand("getAvailableHips", {});
}

function resolveImageryListing(buttonId, hipsData, generation) {
  if (generation !== undefined && HipsLayerControl.isStale(state.hipsLayer, generation)) {
    return;
  }
  disableImageryButtons(false);
  const cfg = IMAGERY_BUTTONS.find((c) => c.id === buttonId);
  if (!cfg) return;
  // Ignore listing if a newer card request already replaced this button.
  if (state.hipsLayer.requestedImageryButtonId && state.hipsLayer.requestedImageryButtonId !== buttonId) {
    return;
  }

  const names = ImageryMatching.extractHipsNames(hipsData);
  const match = ImageryMatching.matchImageryLayer(cfg, names);

  if (!match) {
    setImageryStatus("No matching ESASky visualization layer was found.", "missing");
    state.hipsLayer.uiState = HipsLayerControl.UI.FAILED;
    state.hipsLayer.failureReason = "No matching ESASky visualization layer was found.";
    state.hipsLayer.layerCommandSent = false;
    updateImageryButtonPresentations();
    updateRestoreLayerControl();
    renderHipsDiagnostics();
    return;
  }

  requestChangeHips(cfg, match, HipsLayerControl.KIND.SWITCH);
}

function requestChangeHips(cfg, layerName, kind) {
  const switchKind = kind || HipsLayerControl.KIND.SWITCH;
  const started = HipsLayerControl.beginSwitch(state.hipsLayer, cfg.id, layerName, switchKind);
  const generation = started.generation;
  const pending = started.pending;

  disableImageryButtons(true);

  const timeoutId = setTimeout(() => {
    if (HipsLayerControl.isStale(state.hipsLayer, generation)) return;
    if (!state.pendingChangeRequest || state.pendingChangeRequest.generation !== generation) return;
    state.pendingChangeRequest = null;
    disableImageryButtons(false);
    HipsLayerControl.applyTimeout(state.hipsLayer, pending);
    // Do not auto-restore after timeout.
    applyHipsStatusFromState();
    updateImageryButtonPresentations();
    updateRestoreLayerControl();
    renderHipsDiagnostics();
  }, 5000);

  state.pendingChangeRequest = Object.assign({}, pending, { timeoutId });
  updateImageryButtonPresentations();
  applyHipsStatusFromState();
  updateRestoreLayerControl();
  renderHipsDiagnostics();
  sendEsaskyCommand("changeHips", { hipsName: layerName });
}

function resolveChangeHipsRequest(result) {
  const pending = state.pendingChangeRequest;
  if (!pending) return;
  if (HipsLayerControl.isStale(state.hipsLayer, pending.generation)) {
    return;
  }

  clearTimeout(pending.timeoutId);
  state.pendingChangeRequest = null;
  disableImageryButtons(false);

  if (result.status === "acknowledged") {
    HipsLayerControl.applyAcknowledgement(state.hipsLayer, result.layerName, pending);
    state.activeImageryButtonId = state.hipsLayer.acknowledgedImageryButtonId;
  } else if (result.status === "mismatch") {
    HipsLayerControl.applyFailure(state.hipsLayer, result.message, pending);
  } else if (result.status === "error") {
    HipsLayerControl.applyFailure(state.hipsLayer, result.message, pending);
  }

  applyHipsStatusFromState();
  updateImageryButtonPresentations();
  updateRestoreLayerControl();
  renderHipsDiagnostics();
  // ESASky acknowledgement must not change MAST discovery badges or counts.
}

function disableImageryButtons(disabled) {
  forEachImageryButton((b) => {
    b.disabled = disabled;
  });
}

function forEachImageryButton(fn) {
  if (el.imageryGrid && Array.isArray(el.imageryGrid._children) && el.imageryGrid._children.length) {
    el.imageryGrid._children.forEach((child) => {
      if (child && child.dataset && child.dataset.id) fn(child);
    });
    return;
  }
  document.querySelectorAll(".imagery-btn").forEach(fn);
}

// -- init -----------------------------------------------------------------

buildImageryButtons();
renderTargetCard();
loadWatchlistFromServer();
pollStellariumStatus();
setInterval(pollStellariumStatus, 6000);

// Test-only hook: exposes real app.js internals to the Node browser-DOM
// integration harness (tests/frontend/app_dom_integration.test.js) so that
// harness exercises this actual file's code paths (the real click
// handlers, renderTargetCard(), syncEsaskyToCurrentTarget(), the ESASky
// load handler, etc.) instead of a re-implementation of them. Has no
// effect in the browser, where `module` is undefined and this block never
// runs.
if (typeof module === "object" && module.exports) {
  module.exports = {
    state,
    el,
    syncEsaskyToCurrentTarget,
    getViewerFovDeg,
    openOrUpdateEsasky,
    renderTargetCard,
    clearStaleTargetAfterFailedSelection,
    turnOnlineModeOn,
    turnOnlineModeOff,
    syncPlanetaryImagePanel,
    renderPlanetaryImagePanel,
    resetPlanetaryImagePanel,
    syncArchiveAvailabilityChecks,
    fetchArchiveMission,
    loadWatchlistFromServer,
    saveWatchlistDocument,
    refreshApophisTracker,
    selectWatchlistEntry,
    renderTrackedObjectDetails,
    renderSelectedWatchlistPanels,
    clearTrackedObjectDetails,
    saveWatchlistNote,
    openOrAddApophisTracker,
    applyApophisEphemerisToTarget,
    watchlistWritesAllowed,
    markWatchlistLoadFailed,
  };
}
