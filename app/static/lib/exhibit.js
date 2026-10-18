/* exhibit.js
 *
 * Curated Exhibit player. Reuses Stories, Archaeoastronomy Visual Mode,
 * Official Media, Cosmic Signal, Spectrum, Time Machine, and Cartography
 * Narration. Audio never autoplays. Historical time is never silent.
 */
(function (root) {
  "use strict";

  var model = root.ExhibitModel || {};
  var els = {};
  var state = {
    list: [],
    exhibit: null,
    player: null,
    started: false,
    resume: null,
    historicalPending: false,
    lastText: "",
  };

  function $(id) {
    return typeof document !== "undefined" && document && document.getElementById
      ? document.getElementById(id)
      : null;
  }

  function init() {
    els.card = $("exhibit-card");
    els.list = $("exhibit-list");
    els.overview = $("exhibit-overview");
    els.player = $("exhibit-player");
    els.status = $("exhibit-status");
    els.autoAdvance = $("exhibit-auto-advance");
    if (els.autoAdvance) els.autoAdvance.checked = false;
    bind();
    if (els.card || els.list) refreshList();
  }

  function bind() {
    on("btn-exhibit-start", "click", startExhibit);
    on("btn-exhibit-resume", "click", resumeExhibit);
    on("btn-exhibit-restart", "click", function () {
      clearResume();
      renderOverview(state.exhibit);
    });
    on("btn-exhibit-prev", "click", function () { stepExhibit("prev"); });
    on("btn-exhibit-next", "click", function () { stepExhibit("next"); });
    on("btn-exhibit-pause", "click", function () {
      if (root.CartographyNarration && root.CartographyNarration.pauseNarration) {
        root.CartographyNarration.pauseNarration();
      }
    });
    on("btn-exhibit-stop-narration", "click", function () {
      if (root.CartographyNarration && root.CartographyNarration.stopNarration) {
        root.CartographyNarration.stopNarration(false);
      }
    });
    on("btn-exhibit-stop", "click", function () { stopExhibit(false); });
    on("btn-exhibit-exit-restore", "click", function () { stopExhibit(true); });
    on("btn-exhibit-apply-historical", "click", applyHistorical);
    on("btn-exhibit-sources", "click", toggleSources);
    if (els.autoAdvance) {
      els.autoAdvance.addEventListener("change", persistResume);
    }
  }

  function on(id, type, fn) {
    var node = $(id);
    if (node) node.addEventListener(type, fn);
  }

  async function refreshList() {
    if (!els.list) return;
    try {
      var resp = await fetch("/api/exhibits", { cache: "no-store" });
      var data = await resp.json();
      state.list = (data && data.exhibits) || [];
      renderList();
    } catch (_err) {
      els.list.innerHTML = "<p class=\"hint\">Could not load exhibits.</p>";
    }
  }

  function renderList() {
    if (!els.list) return;
    if (!state.list.length) {
      els.list.innerHTML = "<p class=\"hint\">No curated exhibits are enabled.</p>";
      return;
    }
    els.list.innerHTML = state.list.map(function (item) {
      return "<button type=\"button\" class=\"event-chip\" data-exhibit-id=\"" +
        escapeHtml(item.id) + "\">" + escapeHtml(item.title) + "</button>";
    }).join("");
    els.list.querySelectorAll("[data-exhibit-id]").forEach(function (btn) {
      btn.addEventListener("click", function () { openExhibit(btn.getAttribute("data-exhibit-id")); });
    });
  }

  async function openExhibit(exhibitId) {
    if (els.card) els.card.open = true;
    try {
      var resp = await fetch("/api/exhibit/" + encodeURIComponent(exhibitId), { cache: "no-store" });
      var data = await resp.json();
      if (!data || !data.ok) {
        setStatus((data && data.error) || "Unknown exhibit.");
        return;
      }
      state.exhibit = data.exhibit;
      state.started = false;
      state.player = null;
      state.resume = readResume(exhibitId);
      renderOverview(data.exhibit);
    } catch (_err) {
      setStatus("Could not open the exhibit.");
    }
  }

  function renderOverview(exhibit) {
    if (!els.overview) return;
    hide(els.player, true);
    hide(els.overview, false);
    var cultures = (exhibit.culture_scope || []).join(" · ");
    var evidence = (exhibit.evidence_types || []).map(function (key) {
      return model.evidenceBadgeLabel ? model.evidenceBadgeLabel(key) : key;
    }).filter(Boolean).join(" · ");
    var resume = state.resume;
    var html = "";
    html += "<div class=\"exhibit-cover\">" + ((exhibit.cover && exhibit.cover.svg) || "") + "</div>";
    html += "<div class=\"target-name\">" + escapeHtml(exhibit.title) + "</div>";
    html += "<p class=\"hint\">" + escapeHtml(exhibit.subtitle || "") + "</p>";
    html += "<p class=\"hint\">" + escapeHtml(exhibit.description || "") + "</p>";
    html += "<p class=\"hint\">Estimated duration: " + escapeHtml(String(exhibit.estimated_minutes || "")) + " minutes</p>";
    html += "<p class=\"hint\">Cultures / evidence: " + escapeHtml(cultures) +
      (evidence ? " · " + escapeHtml(evidence) : "") + "</p>";
    html += "<p class=\"hint\">" + escapeHtml(exhibit.source_note || "") + "</p>";
    if (resume) {
      html += "<p class=\"hint\" id=\"exhibit-resume-prompt\">" +
        escapeHtml((model.resumePrompt || function (t, n) { return "Resume at Step " + (n + 1) + "?"; })(exhibit.title, resume.last_completed_step)) +
        "</p>";
    }
    els.overview.innerHTML = html;
    setButtons({ overview: true, resume: !!resume });
    setStatus("Narration does not start until you press Start Exhibit.");
  }

  async function startExhibit() {
    if (!state.exhibit) return;
    await postAction("start", {});
  }

  async function resumeExhibit() {
    if (!state.exhibit) return;
    await postAction("start", {});
    var target = state.resume ? state.resume.last_completed_step : 0;
    var guard = 0;
    while (state.player && state.player.step_index < target && state.player.has_next && guard < 20) {
      await postAction("step", { direction: "next" }, { speak: false });
      guard += 1;
    }
    speakCurrent();
  }

  async function stepExhibit(direction) {
    await postAction("step", { direction: direction || "next" });
  }

  async function applyHistorical() {
    if (!state.player) return;
    await postAction("step", { action: "apply_historical" });
  }

  async function stopExhibit(restore) {
    try {
      await postJson("/api/exhibit/" + encodeURIComponent((state.exhibit && state.exhibit.id) || "") + "/stop", {
        restore: !!restore,
      });
    } catch (_err) { /* stop should still reset the UI */ }
    if (root.CartographyNarration && root.CartographyNarration.stopNarration) {
      root.CartographyNarration.stopNarration(true);
    }
    persistResume();
    state.started = false;
    state.player = null;
    state.historicalPending = false;
    if (state.exhibit) renderOverview(state.exhibit);
    setStatus(restore ? "Exhibit exited. Original Stellarium state restored where captured." : "Exhibit stopped.");
  }

  async function postAction(action, payload, options) {
    options = options || {};
    if (!state.exhibit) return;
    var url = "/api/exhibit/" + encodeURIComponent(state.exhibit.id) + "/" + action;
    try {
      var data = await postJson(url, payload || {});
      if (!data || data.ok === false) {
        setStatus((data && data.error) || "Exhibit action failed.");
        return;
      }
      renderPlayer(data);
      if (options.speak !== false && action !== "stop") speakCurrent();
    } catch (_err) {
      setStatus("Could not reach the exhibit API.");
    }
  }

  function renderPlayer(data) {
    state.started = true;
    state.player = data;
    hide(els.overview, true);
    hide(els.player, false);
    if (!els.player) return;
    var step = data.step || {};
    var confirm = step.historical_confirmation;
    state.historicalPending = !!(confirm && confirm.required && !data.historical_applied);
    var percent = model.progressPercent ? model.progressPercent(data.step_index, data.total_steps) : 0;
    var html = "";
    html += "<div class=\"target-name\">" + escapeHtml(step.title || data.title) + "</div>";
    html += "<div class=\"constellation-progress\">" + escapeHtml(data.progress_label || "") + "</div>";
    html += "<div class=\"exhibit-progress-track\" role=\"progressbar\" aria-valuemin=\"0\" aria-valuemax=\"100\" aria-valuenow=\"" +
      percent + "\"><div class=\"exhibit-progress-bar\" style=\"width:" + percent + "%\"></div></div>";
    html += renderBadges(step.evidence_badges || []);
    html += "<p class=\"hint\">Current story / object / site: " +
      escapeHtml(step.current_story || step.current_object || step.current_site || "Exhibit step") + "</p>";
    if (step.evidence_label) {
      html += "<p class=\"hint\">Evidence: " + escapeHtml(step.evidence_label) + "</p>";
    }
    html += renderSoundExplainer(step.sound_explainer);
    html += renderPlaceContext(step.place_context);
    html += renderHowTheyKnew(step.how_they_knew);
    html += "<div class=\"narration-script\">" + escapeHtml(((data.narration || {}).text) || "") + "</div>";
    html += renderComparison(step.comparison || [], step);
    html += renderMethodComparison(step.method_comparison || []);
    html += renderToolsOfTheSky(step.tools_of_the_sky || []);
    html += renderMedia(step.media || {});
    if (confirm && confirm.required && !data.historical_applied) {
      html += "<div class=\"exhibit-confirm\" id=\"exhibit-historical-confirm\">";
      html += "<div class=\"narration-label\">" + escapeHtml(confirm.prompt || "") + "</div>";
      html += "<p class=\"hint\">" + escapeHtml(confirm.explanation || "") + "</p>";
      html += "<p class=\"hint\">" + escapeHtml(confirm.reconstruction_label || "astronomical reconstruction") +
        ". " + escapeHtml(confirm.restore_note || "") + "</p>";
      html += "</div>";
    }
    if (data.historical_applied) {
      html += "<p class=\"hint\">Astronomical reconstruction applied. Modern planetarium simulation only. Original time restores on Exit and Restore.</p>";
    }
    html += "<details class=\"constellation-section\" id=\"exhibit-source-panel\"><summary>Sources for this Exhibit</summary>";
    html += renderSources(data.sources || (state.exhibit && state.exhibit.sources) || []);
    html += "</details>";
    els.player.innerHTML = html;
    bindPlayerActions(step);
    setButtons({ player: true, historical: state.historicalPending });
    persistResume();
    if (step.archaeo_visual_id && root.ArchaeoastronomyView && root.ArchaeoastronomyView.openVisual) {
      root.ArchaeoastronomyView.openVisual(step.archaeo_visual_id);
    }
    if (root.OfficialMedia && root.OfficialMedia.refreshStory && step.object_name) {
      root.OfficialMedia.refreshStory();
    }
    if (root.ExperienceLayer && root.ExperienceLayer.refreshSkyState) {
      root.ExperienceLayer.refreshSkyState();
    }
    if (root.LightEchoes && root.LightEchoes.showFromExhibitStep && step) {
      root.LightEchoes.showFromExhibitStep(step);
    }
    if (root.CosmicWeb && root.CosmicWeb.showFromExhibitStep && step) {
      root.CosmicWeb.showFromExhibitStep(step);
    }
    if (root.GravitationalWaves && root.GravitationalWaves.showFromExhibitStep && step) {
      root.GravitationalWaves.showFromExhibitStep(step);
    }
    if (root.BlackHoles && root.BlackHoles.showFromExhibitStep && step) {
      root.BlackHoles.showFromExhibitStep(step);
    }
    if (root.GalacticEncounters && root.GalacticEncounters.showFromExhibitStep && step) {
      root.GalacticEncounters.showFromExhibitStep(step);
    }
    if (root.CosmicDawn && root.CosmicDawn.showFromExhibitStep && step) {
      root.CosmicDawn.showFromExhibitStep(step);
    }
  }

  function renderBadges(badges) {
    if (!badges.length) return "";
    return "<div class=\"official-media-badges\">" + badges.map(function (badge) {
      return "<span class=\"archaeo-badge\">" + escapeHtml(badge.label || badge.id) + "</span>";
    }).join("") + "</div>";
  }

  function renderComparison(items, step) {
    if (!items || items.length < 2) return "";
    step = step || {};
    var title = step.comparison_title || "Same sky — different stories";
    var note = step.comparison_note || "These names remain distinct. They are not merged into one mythology.";
    return "<div class=\"story-compare\"><div class=\"narration-label\">" + escapeHtml(title) + "</div>" +
      "<p class=\"hint\">" + escapeHtml(note) + "</p>" +
      items.map(function (item) {
        return "<span class=\"event-chip\">" + escapeHtml(item.culture_name) + ": " +
          escapeHtml(item.translated_name || item.native_name || item.canonical_name) + "</span>";
      }).join("") + "</div>";
  }

  function renderHowTheyKnew(card) {
    if (!card || !(card.fields || []).length) return "";
    var html = "<details class=\"exhibit-hearing cosmic-signal-hearing exhibit-know\" open>";
    html += "<summary>" + escapeHtml(card.title || "How Did They Know?") + "</summary>";
    html += "<div class=\"cosmic-signal-hearing-content\">";
    (card.fields || []).forEach(function (row) {
      html += "<p><strong>" + escapeHtml(row.label || row.id) + ":</strong> " +
        escapeHtml(row.text || "") + "</p>";
    });
    html += "</div></details>";
    return html;
  }

  function renderPlaceContext(ctx) {
    if (!ctx) return "";
    var parts = [];
    if (ctx.tradition) parts.push("Tradition: " + ctx.tradition);
    if (ctx.period) parts.push("Period: " + ctx.period);
    if (ctx.region) parts.push("Region: " + ctx.region);
    if (ctx.observing_environment) parts.push("Observing environment: " + ctx.observing_environment);
    if (!parts.length) return "";
    return "<p class=\"hint exhibit-place-context\">" + escapeHtml(parts.join(" · ")) + "</p>";
  }

  function renderMethodComparison(rows) {
    if (!rows || !rows.length) return "";
    var html = "<div class=\"story-compare\"><div class=\"narration-label\">What was watched, measured, and determined</div>";
    html += "<p class=\"hint\">Similar observational function is not a shared origin.</p>";
    rows.forEach(function (row) {
      html += "<p class=\"story-provenance\"><strong>" + escapeHtml(row.tradition || "") + "</strong><br>" +
        escapeHtml(["Watched: " + (row.watched || ""), "Measured: " + (row.measured || ""),
          "Purpose: " + (row.purpose || ""), "Evidence: " + (row.evidence || "")].join(" · ")) +
        "</p>";
    });
    html += "</div>";
    return html;
  }

  function renderToolsOfTheSky(items) {
    if (!items || !items.length) return "";
    var html = "<div class=\"story-compare\"><div class=\"narration-label\">Tools of the Sky</div>";
    html += "<p class=\"hint\">Only methods actually sourced in this exhibit.</p>";
    html += items.map(function (item) {
      return "<span class=\"event-chip\">" + escapeHtml(item.label || item.id) + "</span>";
    }).join("");
    html += "</div>";
    return html;
  }

  function renderSoundExplainer(explainer) {
    if (!explainer) return "";
    var html = "<div class=\"exhibit-hearing cosmic-signal-hearing\">";
    html += "<div class=\"narration-label\">" + escapeHtml(explainer.title || "Can space make sound?") + "</div>";
    if (explainer.lead) html += "<p class=\"hint\">" + escapeHtml(explainer.lead) + "</p>";
    (explainer.points || []).forEach(function (point) {
      html += "<p class=\"hint\"><strong>" + escapeHtml(point.label || "") + ":</strong> " +
        escapeHtml(point.text || "") + "</p>";
    });
    html += "</div>";
    return html;
  }

  function renderHearingCard(card) {
    if (!card) return "";
    var html = "<details class=\"exhibit-hearing cosmic-signal-hearing\" open>";
    html += "<summary>" + escapeHtml(card.title || "What Am I Hearing?") + "</summary>";
    html += "<div class=\"cosmic-signal-hearing-content\">";
    [
      ["Source instrument / mission", card.source_instrument_mission],
      ["Original data type", card.original_data_type],
      ["Transformation type", card.transformation_type],
      ["Time scaling", card.time_scaling],
      ["Frequency mapping", card.frequency_mapping],
      ["Literal vs mapped", card.literal_vs_mapped],
      ["Provider / source", card.provider],
    ].forEach(function (row) {
      if (!row[1]) return;
      html += "<p><strong>" + escapeHtml(row[0]) + ":</strong> " + escapeHtml(row[1]) + "</p>";
    });
    html += "</div></details>";
    return html;
  }

  function renderSignalControls(entry, index, kind) {
    if (!entry) return "";
    var prefix = kind || "cs";
    return "<div class=\"button-row\">" +
      "<button type=\"button\" class=\"btn btn-primary btn-small\" data-exhibit-" + prefix + "-play=\"" + index + "\">Play</button>" +
      "<button type=\"button\" class=\"btn btn-secondary btn-small\" data-exhibit-" + prefix + "-stop=\"" + index + "\">Stop</button>" +
      "<button type=\"button\" class=\"btn btn-secondary btn-small\" data-exhibit-" + prefix + "=\"" + index + "\">Open in Cosmic Signal Deck</button>" +
      "</div>";
  }

  function renderMedia(media) {
    var html = "<div class=\"exhibit-media-note\">";
    html += "<p class=\"hint\">Listen to the Universe and official media remain manual. Nothing here autoplays.</p>";
    var classes = [];
    ((media.hearing_card && media.hearing_card.classification_labels) || []).forEach(function (label) {
      classes.push(label);
    });
    ((media.generated_hearing_card && media.generated_hearing_card.classification_labels) || []).forEach(function (label) {
      classes.push(label);
    });
    if (classes.length) {
      html += "<div class=\"official-media-badges\">" + classes.map(function (label) {
        return "<span class=\"archaeo-badge\">" + escapeHtml(label) + "</span>";
      }).join("") + "</div>";
    }
    if (media.official_media_title) {
      html += "<p class=\"hint\">" + (media.scientific_view ? "<span class=\"archaeo-badge\">SCIENTIFIC VIEW</span> " : "") +
        "Official media: " + escapeHtml(media.official_media_title) +
        ". Official Media remains manual in its existing panel. NASA or Chandra media are not the cultural source.</p>";
    } else if (media.scientific_view) {
      html += "<p class=\"hint\"><span class=\"archaeo-badge\">SCIENTIFIC VIEW</span> A scientific image may accompany this object. It is not the cultural source. Official Media remains manual.</p>";
    }
    var signals = (media.signals && media.signals.ranked) || [];
    if (signals.length) {
      html += "<div class=\"narration-label\">Listen to the Universe</div>";
      html += signals.slice(0, 1).map(function (entry, i) {
        var labels = (entry.classification_labels || []).join(" · ");
        return "<p class=\"hint\">" + escapeHtml(entry.title || entry.id) +
          (labels ? " — " + escapeHtml(labels) : "") +
          (entry.provider ? " · " + escapeHtml(entry.provider) : "") + "</p>" +
          renderSignalControls(entry, i, "cs") +
          renderHearingCard(entry.hearing_card || media.hearing_card);
      }).join("");
    }
    if (media.generated_hearing_card) {
      html += "<div class=\"narration-label\">Generated Cartography Data Sonification</div>";
      html += "<p class=\"hint\">Cartography is generating this Data Sonification from local altitude numbers. It is not a NASA or Chandra recording.</p>";
      html += renderHearingCard(media.generated_hearing_card);
      html += "<div class=\"button-row\">" +
        "<button type=\"button\" class=\"btn btn-primary btn-small\" data-exhibit-sonify-play=\"1\">Play Data Sonification</button>" +
        "<button type=\"button\" class=\"btn btn-secondary btn-small\" data-exhibit-sonify-stop=\"1\">Stop Data Sonification</button>" +
        "</div>";
    }
    (media.related_signals || []).forEach(function (entry, i) {
      html += "<p class=\"hint\">Related (open in Cosmic Signal Deck): " +
        escapeHtml(entry.title || entry.id) +
        ((entry.classification_labels || []).length ? " — " + escapeHtml(entry.classification_labels.join(" · ")) : "") +
        "</p>";
      html += "<button type=\"button\" class=\"event-chip\" data-exhibit-related=\"" + i + "\">Open in Cosmic Signal Deck</button>";
    });
    (media.free_listen || []).forEach(function (entry, i) {
      html += "<button type=\"button\" class=\"event-chip\" data-exhibit-free=\"" + i + "\">" +
        escapeHtml(entry.title || entry.id) + "</button>";
    });
    var spectra = (media.spectra && media.spectra.ranked) || [];
    if (spectra.length) {
      html += spectra.slice(0, 1).map(function (entry, i) {
        return "<button type=\"button\" class=\"event-chip\" data-exhibit-spec=\"" + i + "\">Spectrum: " +
          escapeHtml(entry.title || entry.id) + "</button>";
      }).join("");
    }
    html += "</div>";
    return html;
  }

  function renderSources(groups) {
    if (!groups.length) return "<p class=\"hint\">No grouped sources for this exhibit.</p>";
    return groups.map(function (group) {
      var rows = (group.sources || []).map(function (src) {
        return "<p class=\"story-provenance\"><strong>" + escapeHtml(src.title) + "</strong> — " +
          escapeHtml(src.institution || "") + "<br>" +
          escapeHtml((src.evidence_type || "") + (src.supports ? " · " + src.supports : "")) + "</p>";
      }).join("");
      return "<div class=\"exhibit-source-group\"><div class=\"hint\"><strong>" +
        escapeHtml(group.title || ("Step " + (group.step_index + 1))) +
        "</strong></div>" + (rows || "<p class=\"hint\">No source cards on this step.</p>") + "</div>";
    }).join("");
  }

  function bindPlayerActions(step) {
    if (!els.player) return;
    var media = (step && step.media) || {};
    var signals = (media.signals && media.signals.ranked) || [];
    var related = media.related_signals || [];
    var free = media.free_listen || [];
    var spectra = (media.spectra && media.spectra.ranked) || [];
    function openThen(entry, play) {
      if (!entry || !root.CartographyDeck) return;
      var opened = root.CartographyDeck.openSignal
        ? root.CartographyDeck.openSignal(entry, signals.concat(related, free))
        : null;
      function afterOpen() {
        if (play && root.CartographyDeck.play) root.CartographyDeck.play();
        if (root.CartographyDeck.scrollToDeck) root.CartographyDeck.scrollToDeck();
      }
      if (opened && typeof opened.then === "function") opened.then(afterOpen);
      else afterOpen();
    }
    els.player.querySelectorAll("[data-exhibit-cs]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        openThen(signals[Number(btn.getAttribute("data-exhibit-cs"))], false);
      });
    });
    els.player.querySelectorAll("[data-exhibit-cs-play]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        openThen(signals[Number(btn.getAttribute("data-exhibit-cs-play"))], true);
      });
    });
    els.player.querySelectorAll("[data-exhibit-cs-stop]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        if (root.CartographyDeck && root.CartographyDeck.stop) root.CartographyDeck.stop();
      });
    });
    els.player.querySelectorAll("[data-exhibit-related]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        openThen(related[Number(btn.getAttribute("data-exhibit-related"))], false);
      });
    });
    els.player.querySelectorAll("[data-exhibit-free]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        openThen(free[Number(btn.getAttribute("data-exhibit-free"))], false);
      });
    });
    els.player.querySelectorAll("[data-exhibit-spec]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var entry = spectra[Number(btn.getAttribute("data-exhibit-spec"))];
        if (entry && root.CartographyDeck && root.CartographyDeck.openSpectrum) {
          root.CartographyDeck.openSpectrum(entry);
        }
      });
    });
    els.player.querySelectorAll("[data-exhibit-sonify-play]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        if (root.ExperienceLayer && root.ExperienceLayer.openSonifyCard) root.ExperienceLayer.openSonifyCard();
        if (root.ExperienceLayer && root.ExperienceLayer.playSonify) root.ExperienceLayer.playSonify();
      });
    });
    els.player.querySelectorAll("[data-exhibit-sonify-stop]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        if (root.ExperienceLayer && root.ExperienceLayer.stopSonify) root.ExperienceLayer.stopSonify();
      });
    });
  }

  function speakCurrent() {
    var text = state.player && state.player.narration ? state.player.narration.text : "";
    state.lastText = text || "";
    if (!root.CartographyNarration) return;
    if (root.CartographyNarration.speakExhibit) {
      root.CartographyNarration.speakExhibit(text, {
        exhibitId: state.exhibit && state.exhibit.id,
        stepIndex: state.player && state.player.step_index,
      });
      return;
    }
    if (root.CartographyNarration.speakKind) {
      root.CartographyNarration.speakKind("exhibit_step");
    }
  }

  function toggleSources() {
    var panel = $("exhibit-source-panel");
    if (panel) panel.open = !panel.open;
  }

  function setButtons(flags) {
    flags = flags || {};
    var start = $("btn-exhibit-start");
    var resume = $("btn-exhibit-resume");
    var restart = $("btn-exhibit-restart");
    var prev = $("btn-exhibit-prev");
    var next = $("btn-exhibit-next");
    var pause = $("btn-exhibit-pause");
    var stopNarr = $("btn-exhibit-stop-narration");
    var stop = $("btn-exhibit-stop");
    var exit = $("btn-exhibit-exit-restore");
    var apply = $("btn-exhibit-apply-historical");
    var sources = $("btn-exhibit-sources");
    if (start) start.hidden = !flags.overview;
    if (resume) resume.hidden = !flags.resume;
    if (restart) restart.hidden = !flags.resume;
    if (prev) prev.disabled = !flags.player || !(state.player && state.player.has_previous);
    if (next) next.disabled = !flags.player || !(state.player && state.player.has_next);
    if (pause) pause.disabled = !flags.player;
    if (stopNarr) stopNarr.disabled = !flags.player;
    if (stop) stop.disabled = !flags.player;
    if (exit) exit.disabled = !flags.player;
    if (apply) {
      apply.hidden = !flags.historical;
      apply.disabled = !flags.historical;
    }
    if (sources) sources.disabled = !(state.exhibit);
    if (els.autoAdvance) els.autoAdvance.disabled = !flags.player && !flags.overview;
  }

  function persistResume() {
    if (!state.exhibit || !model.STORAGE_KEY) return;
    try {
      var provider = $("tts-provider");
      var voice = $("tts-voice");
      localStorage.setItem(model.STORAGE_KEY, (model.serializeResume || JSON.stringify)({
        exhibit_id: state.exhibit.id,
        last_completed_step: state.player ? state.player.step_index : 0,
        provider: provider ? provider.value : "",
        voice: voice ? voice.value : "",
        auto_advance: !!(els.autoAdvance && els.autoAdvance.checked),
      }));
    } catch (_err) { /* localStorage may be blocked */ }
  }

  function readResume(exhibitId) {
    try {
      var parsed = model.parseResume ? model.parseResume(localStorage.getItem(model.STORAGE_KEY)) : null;
      if (parsed && parsed.exhibit_id === exhibitId && parsed.last_completed_step > 0) return parsed;
    } catch (_err) { /* ignore */ }
    return null;
  }

  function clearResume() {
    try { localStorage.removeItem(model.STORAGE_KEY); } catch (_err) { /* ignore */ }
    state.resume = null;
  }

  function onNarrationEnded() {
    var flags = {
      autoAdvance: !!(els.autoAdvance && els.autoAdvance.checked),
      ended: true,
      hasNext: !!(state.player && state.player.has_next),
      stepType: state.player && state.player.step ? state.player.step.step_type : "",
      historicalPending: state.historicalPending,
    };
    if (model.shouldAutoAdvance && model.shouldAutoAdvance(flags)) {
      setTimeout(function () { stepExhibit("next"); }, 800);
    }
  }

  async function postJson(url, payload) {
    var resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload || {}),
    });
    return resp.json();
  }

  function hide(node, hidden) {
    if (node) node.hidden = !!hidden;
  }

  function setStatus(text) {
    if (els.status) els.status.textContent = text || "";
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  root.CartographyExhibit = {
    init: init,
    refreshList: refreshList,
    openExhibit: openExhibit,
    startExhibit: startExhibit,
    stopExhibit: stopExhibit,
    onNarrationEnded: onNarrationEnded,
    current: function () { return state.player; },
    started: function () { return state.started; },
    autoAdvanceEnabled: function () { return !!(els.autoAdvance && els.autoAdvance.checked); },
    noAutoplay: true,
  };

  if (typeof module === "object" && module.exports) {
    module.exports = root.CartographyExhibit;
  }

  if (typeof document !== "undefined" && document) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", init);
    } else if ($("exhibit-card") || $("exhibit-list")) {
      init();
    }
  }
})(typeof self !== "undefined" ? self : this);
