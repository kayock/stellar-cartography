/* galactic_encounters.js — interactive encounter labs + system cards */
(function (root) {
  "use strict";

  var state = {
    payload: null,
    objectId: null,
    massRatio: "equal",
    orientation: "prograde",
    starsGas: "both",
    merger: "major",
  };

  function $(id) {
    return document.getElementById(id);
  }

  function setStatus(msg) {
    var el = $("ge-status");
    if (el) el.textContent = msg || "";
  }

  function badge(cls) {
    return (
      '<span class="ge-class-badge ge-class-' +
      cls +
      '">' +
      String(cls || "").replace(/_/g, " ").toUpperCase() +
      "</span>"
    );
  }

  function fetchJson(url) {
    return fetch(url, { credentials: "same-origin" }).then(function (r) {
      return r.json();
    });
  }

  function postJson(url, body) {
    return fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
    }).then(function (r) {
      return r.json();
    });
  }

  function renderLegend(legend) {
    var el = $("ge-legend");
    if (!el || !legend) return;
    el.innerHTML = Object.keys(legend)
      .map(function (k) {
        return "<div>" + badge(k) + " " + legend[k] + "</div>";
      })
      .join("");
  }

  function renderScience(science) {
    var el = $("ge-science");
    if (!el || !science) return;
    var keys = ["gravity", "stars_miss", "gas_collides", "tides", "timescales", "major_minor", "mw_m31"];
    el.innerHTML = keys
      .filter(function (k) {
        return science[k];
      })
      .map(function (k) {
        return "<p><strong>" + k.replace(/_/g, " ") + ":</strong> " + science[k] + "</p>";
      })
      .join("");
  }

  function renderEncounter(data) {
    var svg = $("ge-encounter-svg");
    var cap = $("ge-encounter-caption");
    if (!svg || !data || !data.ok) return;
    var L = data.layout || {};
    var cx = 50;
    var cy = 50;
    var sep = L.separation || 20;
    var xa = cx - sep / 2;
    var xb = cx + sep / 2;
    var rx = (L.size_a || 10) * (L.stretch || 1);
    var ry = L.size_a || 10;
    var rxb = (L.size_b || 7) * (L.stretch || 1);
    var ryb = L.size_b || 7;
    var tail = L.tail_length || 0;
    var html =
      '<rect class="ge-sky" width="100" height="100"/>' +
      '<text x="50" y="10" class="ge-label">' +
      (data.label || "") +
      "</text>" +
      '<ellipse cx="' +
      xa +
      '" cy="' +
      cy +
      '" rx="' +
      rx +
      '" ry="' +
      ry +
      '" class="ge-gal-a"/>' +
      '<ellipse cx="' +
      xb +
      '" cy="' +
      cy +
      '" rx="' +
      rxb +
      '" ry="' +
      ryb +
      '" class="ge-gal-b"/>';
    if (L.bridge) {
      html +=
        '<path d="M ' +
        (xa + rx * 0.6) +
        " " +
        cy +
        " Q 50 " +
        (cy - 6) +
        " " +
        (xb - rxb * 0.6) +
        " " +
        cy +
        '" class="ge-bridge"/>';
    }
    if (tail > 2) {
      html +=
        '<path d="M ' +
        (xa - rx) +
        " " +
        cy +
        " Q " +
        (xa - rx - tail / 2) +
        " " +
        (cy - 12) +
        " " +
        (xa - rx - tail) +
        " " +
        (cy - 4) +
        '" class="ge-tail"/>';
      html +=
        '<path d="M ' +
        (xb + rxb) +
        " " +
        cy +
        " Q " +
        (xb + rxb + tail / 2) +
        " " +
        (cy + 12) +
        " " +
        (xb + rxb + tail) +
        " " +
        (cy + 4) +
        '" class="ge-tail"/>';
    }
    svg.innerHTML = html;
    if (cap) {
      cap.textContent =
        (data.stage ? data.stage.label + ": " + data.stage.caption + " " : "") +
        (data.mass_ratio ? "[" + data.mass_ratio.label + "] " : "") +
        (data.orientation ? "[" + data.orientation.label + "] " : "") +
        (data.disclaimer || "");
    }
  }

  function renderTidal(data) {
    var svg = $("ge-tidal-svg");
    var cap = $("ge-tidal-caption");
    if (!svg || !data || !data.ok) return;
    var t = data.tail_extension || 0;
    var html =
      '<rect class="ge-sky" width="100" height="100"/>' +
      '<circle cx="18" cy="50" r="8" class="ge-perturber"/>' +
      '<ellipse cx="62" cy="50" rx="' +
      (14 + t * 0.35) +
      '" ry="9" class="ge-gal-a"/>' +
      '<line x1="40" y1="50" x2="' +
      (40 + data.near_side_pull * 10) +
      '" y2="50" class="ge-pull-near"/>' +
      '<line x1="78" y1="50" x2="' +
      (78 + data.far_side_pull * 6) +
      '" y2="50" class="ge-pull-far"/>' +
      '<text x="50" y="12" class="ge-label">' +
      (data.label || "") +
      "</text>";
    svg.innerHTML = html;
    if (cap) {
      cap.textContent =
        (data.caption || "") +
        " Differential≈" +
        data.differential +
        ". " +
        (data.scale_note || "") +
        " " +
        (data.disclaimer || "");
    }
  }

  function renderStarsGas(data) {
    var el = $("ge-stars-gas");
    if (!el || !data || !data.ok) return;
    el.innerHTML =
      badge(data.classification) +
      " " +
      (data.label || "") +
      "<p><strong>" +
      data.mode.label +
      ":</strong> " +
      data.mode.caption +
      "</p>" +
      '<p class="hint">Direct star–star collisions likely? <strong>' +
      (data.star_collision_likely ? "Yes" : "No — separations are huge") +
      "</strong>. Gas interactions strong? <strong>" +
      (data.gas_interaction_strong ? "Yes" : "Not in stars-only view") +
      "</strong>.</p>";
  }

  function renderMerger(data) {
    var el = $("ge-merger");
    if (!el || !data || !data.ok) return;
    el.innerHTML =
      badge(data.classification) +
      " <strong>" +
      data.mode.label +
      "</strong><p>" +
      data.mode.caption +
      "</p>";
  }

  function renderFuture(fut) {
    var el = $("ge-future");
    if (!el || !fut) return;
    el.innerHTML =
      badge(fut.classification) +
      " " +
      (fut.label || "") +
      "<p class=\"hint\">" +
      (fut.disclaimer || "") +
      "</p><ul class=\"ge-points\">" +
      (fut.points || [])
        .map(function (p) {
          return "<li>" + p + "</li>";
        })
        .join("") +
      "</ul>";
  }

  function renderObjects(objects) {
    var el = $("ge-objects");
    if (!el) return;
    el.innerHTML = (objects || [])
      .map(function (o) {
        var active = o.id === state.objectId ? " is-active" : "";
        return (
          '<button type="button" class="event-chip' +
          active +
          '" data-ge-id="' +
          o.id +
          '">' +
          (o.short_name || o.name) +
          "</button>"
        );
      })
      .join("");
    el.querySelectorAll("[data-ge-id]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        selectObject(btn.getAttribute("data-ge-id"));
      });
    });
  }

  function renderDetail(obj) {
    var detail = $("ge-detail");
    var media = $("ge-media");
    if (!detail || !obj) return;
    detail.innerHTML =
      "<h3>" +
      obj.name +
      "</h3>" +
      "<p>" +
      (obj.significance || "") +
      "</p>" +
      "<p class=\"hint\">" +
      (obj.interaction_type || "") +
      " · " +
      (obj.distance_note || "") +
      "</p>" +
      "<p class=\"hint\">Stellarium: " +
      (obj.stellarium_note || "") +
      "</p>" +
      "<ul class=\"ge-points\">" +
      (obj.observed_features || [])
        .map(function (f) {
          return "<li>" + f + "</li>";
        })
        .join("") +
      "</ul>";
    if (media && obj.media) {
      var m = obj.media;
      media.innerHTML =
        '<div class="ge-figure">' +
        badge(m.classification) +
        '<div class="narration-label">' +
        m.title +
        "</div>" +
        '<img src="' +
        m.image_url +
        '" alt="' +
        m.title +
        '" loading="lazy"/>' +
        '<p class="hint">' +
        (m.credit || "") +
        ". " +
        (m.license_note || "") +
        "</p></div>";
    }
  }

  function selectObject(id) {
    state.objectId = id;
    fetchJson("/api/galactic-encounters/object/" + encodeURIComponent(id)).then(function (body) {
      if (!body.ok) {
        setStatus(body.error || "Object load failed");
        return;
      }
      renderObjects((state.payload && state.payload.objects) || []);
      renderDetail(body.object);
      setStatus("Selected " + body.object.name);
    });
  }

  function refreshEncounter() {
    var slider = $("ge-encounter-time");
    var progress = slider ? Number(slider.value) / 100 : 0;
    var q =
      "?progress=" +
      progress +
      "&mass_ratio=" +
      encodeURIComponent(state.massRatio) +
      "&orientation=" +
      encodeURIComponent(state.orientation);
    return fetchJson("/api/galactic-encounters/encounter" + q).then(renderEncounter);
  }

  function refreshTidal() {
    var slider = $("ge-tidal-strength");
    var s = slider ? Number(slider.value) / 100 : 0.65;
    return fetchJson("/api/galactic-encounters/tidal?strength=" + s).then(renderTidal);
  }

  function refreshStarsGas() {
    return fetchJson("/api/galactic-encounters/stars-gas?mode=" + encodeURIComponent(state.starsGas)).then(
      renderStarsGas
    );
  }

  function refreshMerger() {
    return fetchJson("/api/galactic-encounters/merger?mode=" + encodeURIComponent(state.merger)).then(renderMerger);
  }

  function speak(segment) {
    if (root.CartographyNarration && typeof root.CartographyNarration.speakExhibit === "function") {
      fetchJson("/api/galactic-encounters/narration?segment=" + encodeURIComponent(segment)).then(function (body) {
        if (!body.ok) {
          setStatus(body.error || "Narration unavailable");
          return;
        }
        root.CartographyNarration.speakExhibit({
          text: body.text,
          feature: "galactic_encounters",
          segment: segment,
        });
        setStatus("Narrating: " + segment);
      });
      return;
    }
    setStatus("Narration hook unavailable");
  }

  function focusSky() {
    if (!state.objectId) {
      setStatus("Select a system first");
      return;
    }
    postJson("/api/galactic-encounters/focus", { object_id: state.objectId }).then(function (body) {
      setStatus(body.message || (body.focused ? "Focused" : "Focus attempted"));
    });
  }

  function bind() {
    var enc = $("ge-encounter-time");
    if (enc) enc.addEventListener("input", refreshEncounter);
    var mass = $("ge-mass-ratio");
    if (mass) {
      mass.addEventListener("change", function () {
        state.massRatio = mass.value;
        refreshEncounter();
      });
    }
    var ori = $("ge-orientation");
    if (ori) {
      ori.addEventListener("change", function () {
        state.orientation = ori.value;
        refreshEncounter();
      });
    }
    var tidal = $("ge-tidal-strength");
    if (tidal) tidal.addEventListener("input", refreshTidal);
    var sg = $("ge-stars-gas-mode");
    if (sg) {
      sg.addEventListener("change", function () {
        state.starsGas = sg.value;
        refreshStarsGas();
      });
    }
    var mg = $("ge-merger-mode");
    if (mg) {
      mg.addEventListener("change", function () {
        state.merger = mg.value;
        refreshMerger();
      });
    }
    var focusBtn = $("btn-ge-focus");
    if (focusBtn) focusBtn.addEventListener("click", focusSky);
    var map = {
      "btn-ge-motion": "motion",
      "btn-ge-tides": "tides",
      "btn-ge-tails": "tails",
      "btn-ge-stars-gas": "stars_gas",
      "btn-ge-antennae": "antennae",
      "btn-ge-whirlpool": "whirlpool",
      "btn-ge-major-minor": "major_minor",
      "btn-ge-remnants": "remnants",
      "btn-ge-mw-m31": "mw_m31",
      "btn-ge-closing": "closing",
    };
    Object.keys(map).forEach(function (btnId) {
      var btn = $(btnId);
      if (btn) {
        btn.addEventListener("click", function () {
          speak(map[btnId]);
        });
      }
    });
    var stop = $("btn-ge-stop-narration");
    if (stop && root.CartographyNarration && root.CartographyNarration.stop) {
      stop.addEventListener("click", function () {
        root.CartographyNarration.stop();
        setStatus("Narration stopped");
      });
    }
  }

  function fillSelects(payload) {
    var mass = $("ge-mass-ratio");
    if (mass && payload.encounter_lab && payload.encounter_lab.mass_ratios) {
      mass.innerHTML = payload.encounter_lab.mass_ratios
        .map(function (r) {
          return '<option value="' + r.id + '">' + r.label + "</option>";
        })
        .join("");
    }
    var ori = $("ge-orientation");
    if (ori && payload.encounter_lab && payload.encounter_lab.orientations) {
      ori.innerHTML = payload.encounter_lab.orientations
        .map(function (o) {
          return '<option value="' + o.id + '">' + o.label + "</option>";
        })
        .join("");
    }
    var sg = $("ge-stars-gas-mode");
    if (sg && payload.stars_gas_lab && payload.stars_gas_lab.modes) {
      sg.innerHTML = payload.stars_gas_lab.modes
        .map(function (m) {
          return '<option value="' + m.id + '">' + m.label + "</option>";
        })
        .join("");
      sg.value = "both";
    }
    var mg = $("ge-merger-mode");
    if (mg && payload.merger_lab && payload.merger_lab.modes) {
      mg.innerHTML = payload.merger_lab.modes
        .map(function (m) {
          return '<option value="' + m.id + '">' + m.label + "</option>";
        })
        .join("");
    }
  }

  function init() {
    if (!$("galactic-encounters-card")) return;
    bind();
    fetchJson("/api/galactic-encounters")
      .then(function (payload) {
        state.payload = payload;
        renderLegend(payload.classification_legend);
        renderScience(payload.science);
        renderObjects(payload.objects);
        renderFuture(payload.future_mw_m31);
        fillSelects(payload);
        var first = payload.objects && payload.objects[0];
        if (first) selectObject(first.id);
        return Promise.all([refreshEncounter(), refreshTidal(), refreshStarsGas(), refreshMerger()]);
      })
      .then(function () {
        setStatus("Galactic Encounters ready. Narration stays silent until Listen.");
      })
      .catch(function (err) {
        setStatus("Galactic Encounters failed to load: " + err);
      });
  }

  function showFromExhibitStep(step) {
    if (!step || step.step_type !== "galactic_encounters") return;
    if (step.galactic_encounters_object_id) selectObject(step.galactic_encounters_object_id);
    if (step.scientific_view === "encounter") refreshEncounter();
    if (step.scientific_view === "tidal") refreshTidal();
    if (step.scientific_view === "stars_gas") refreshStarsGas();
    if (step.scientific_view === "merger") refreshMerger();
  }

  root.GalacticEncounters = {
    init: init,
    showFromExhibitStep: showFromExhibitStep,
    selectObject: selectObject,
  };
  if (typeof module !== "undefined" && module.exports) module.exports = root.GalacticEncounters;
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})(window);
