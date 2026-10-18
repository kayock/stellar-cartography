/* black_holes.js — interactive BH labs + object cards */
(function (root) {
  "use strict";

  var state = {
    payload: null,
    objectId: null,
    object: null,
    scaleId: null,
    approachId: null,
    lensStrength: 0.55,
    tidalId: "stellar",
  };

  function $(id) {
    return document.getElementById(id);
  }

  function setStatus(msg) {
    var el = $("bh-status");
    if (el) el.textContent = msg || "";
  }

  function badge(cls) {
    return '<span class="bh-class-badge bh-class-' + cls + '">' + String(cls || "").replace(/_/g, " ").toUpperCase() + "</span>";
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
    var el = $("bh-legend");
    if (!el || !legend) return;
    el.innerHTML = Object.keys(legend)
      .map(function (k) {
        return "<div>" + badge(k) + " " + legend[k] + "</div>";
      })
      .join("");
  }

  function renderScience(science) {
    var el = $("bh-science");
    if (!el || !science) return;
    var keys = ["what_is", "event_horizon", "shadow_vs_horizon", "accretion", "tidal_forces", "detection"];
    el.innerHTML = keys
      .filter(function (k) {
        return science[k];
      })
      .map(function (k) {
        return "<p><strong>" + k.replace(/_/g, " ") + ":</strong> " + science[k] + "</p>";
      })
      .join("");
  }

  function renderScale(data) {
    var svg = $("bh-scale-svg");
    var cap = $("bh-scale-caption");
    if (!svg || !data || !data.ok) return;
    var rs = data.schwarzschild_radius_km || 1;
    var logR = Math.log10(Math.max(rs, 0.001));
    var bar = Math.min(90, Math.max(8, (logR + 1) * 12));
    svg.innerHTML =
      '<rect class="bh-sky" width="100" height="100"/>' +
      '<circle cx="50" cy="50" r="' +
      (6 + Math.min(28, bar / 3)) +
      '" class="bh-horizon"/>' +
      '<text x="50" y="14" class="bh-label">' +
      (data.label || "") +
      "</text>" +
      '<text x="50" y="88" class="bh-label">Rs ≈ ' +
      (rs >= 1e6 ? (rs / 1.496e8).toFixed(3) + " AU" : rs.toPrecision(4) + " km") +
      "</text>";
    if (cap) {
      var comps = (data.comparisons || []).slice(0, 3).map(function (c) {
        return c.phrase;
      });
      cap.textContent =
        (data.example && data.example.label ? data.example.label + ". " : "") +
        (data.disclaimer || "") +
        " " +
        comps.join(" · ");
    }
    var sel = $("bh-scale-select");
    if (sel && data.examples && !sel.dataset.ready) {
      sel.innerHTML = data.examples
        .map(function (e) {
          return '<option value="' + e.id + '">' + e.label + "</option>";
        })
        .join("");
      sel.dataset.ready = "1";
      if (state.scaleId) sel.value = state.scaleId;
    }
  }

  function renderApproach(data) {
    var svg = $("bh-approach-svg");
    var cap = $("bh-approach-caption");
    if (!svg || !data || !data.ok) return;
    var p = (data.region && data.region.progress) || 0;
    var zones = [
      { r: 42, cls: "bh-zone-distant", id: "distant" },
      { r: 30, cls: "bh-zone-disk", id: "disk" },
      { r: 18, cls: "bh-zone-photon", id: "photon" },
      { r: 10, cls: "bh-zone-horizon", id: "horizon" },
    ];
    var html = '<rect class="bh-sky" width="100" height="100"/>';
    zones.forEach(function (z) {
      html += '<circle cx="50" cy="50" r="' + z.r + '" class="' + z.cls + (data.region && data.region.id === z.id ? " is-active" : "") + '"/>';
    });
    html +=
      '<circle cx="50" cy="50" r="6" class="bh-horizon-fill"/>' +
      '<text x="50" y="12" class="bh-label">' +
      (data.label || "") +
      "</text>" +
      '<circle cx="' +
      (50 + 38 * (1 - p)) +
      '" cy="50" r="2.2" class="bh-probe"/>';
    svg.innerHTML = html;
    if (cap) {
      cap.textContent =
        (data.region ? data.region.label + ": " + data.region.caption + " " : "") +
        (data.disclaimer || "");
    }
  }

  function renderLensing(data) {
    var svg = $("bh-lensing-svg");
    var cap = $("bh-lensing-caption");
    if (!svg || !data || !data.ok) return;
    var html =
      '<rect class="bh-sky" width="100" height="100"/>' +
      '<circle cx="50" cy="50" r="' +
      data.shadow_radius +
      '" class="bh-shadow"/>' +
      '<circle cx="50" cy="50" r="' +
      data.photon_ring_radius +
      '" class="bh-photon-ring"/>';
    (data.stars || []).forEach(function (s) {
      html += '<circle cx="' + s.x + '" cy="' + s.y + '" r="' + s.r + '" class="bh-star"/>';
    });
    if (data.einstein_ring_hint) {
      html += '<circle cx="50" cy="50" r="' + (data.photon_ring_radius + 4) + '" class="bh-einstein-hint"/>';
    }
    html += '<text x="50" y="10" class="bh-label">' + (data.label || "") + "</text>";
    svg.innerHTML = html;
    if (cap) cap.textContent = (data.disclaimer || "") + " " + (data.note || "");
  }

  function renderTidal(data) {
    var el = $("bh-tidal");
    if (!el || !data || !data.ok) return;
    var rel = data.relative_horizon_tide_vs_stellar;
    var bar = Math.min(100, Math.max(2, Math.log10(rel + 1e-12) + 12) * 8);
    el.innerHTML =
      "<div>" +
      badge(data.classification) +
      " " +
      (data.label || "") +
      "</div>" +
      "<p>" +
      (data.interpretation || "") +
      "</p>" +
      '<div class="bh-tide-bar" style="width:' +
      bar +
      '%"></div>' +
      "<p class=\"hint\">Relative horizon-tide index vs stellar reference ≈ " +
      (rel > 1e-4 ? rel.toPrecision(3) : rel.toExponential(2)) +
      ". " +
      (data.teaching_point || "") +
      " " +
      (data.disclaimer || "") +
      "</p>";
  }

  function renderDetection(methods) {
    var el = $("bh-detection");
    if (!el || !methods) return;
    el.innerHTML = methods
      .map(function (m) {
        var link =
          m.related_special === "gravitational_waves"
            ? ' <a href="#gravitational-waves-card">Open Gravitational Waves Special</a>'
            : "";
        return "<div class=\"bh-detect-item\"><strong>" + m.title + "</strong><p>" + m.summary + link + "</p></div>";
      })
      .join("");
  }

  function renderObjects(objects) {
    var el = $("bh-objects");
    if (!el) return;
    el.innerHTML = (objects || [])
      .map(function (o) {
        var active = o.id === state.objectId ? " is-active" : "";
        return (
          '<button type="button" class="event-chip' +
          active +
          '" data-bh-id="' +
          o.id +
          '">' +
          (o.short_name || o.name) +
          "</button>"
        );
      })
      .join("");
    el.querySelectorAll("[data-bh-id]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        selectObject(btn.getAttribute("data-bh-id"));
      });
    });
  }

  function renderDetail(obj) {
    var detail = $("bh-detail");
    var media = $("bh-media");
    if (!detail || !obj) return;
    detail.innerHTML =
      "<h3>" +
      obj.name +
      "</h3>" +
      "<p>" +
      (obj.significance || "") +
      "</p>" +
      "<p class=\"hint\">Mass: " +
      (obj.mass_note || "") +
      " · Distance: " +
      (obj.distance_note || "") +
      "</p>" +
      "<p class=\"hint\">Stellarium: " +
      (obj.stellarium_note || "") +
      "</p>" +
      "<ul class=\"bh-points\">" +
      (obj.observational_methods || [])
        .map(function (m) {
          return "<li>" + m + "</li>";
        })
        .join("") +
      "</ul>";
    if (media && obj.media) {
      var m = obj.media;
      media.innerHTML =
        "<div class=\"bh-figure\">" +
        badge(m.classification) +
        "<div class=\"narration-label\">" +
        m.title +
        "</div>" +
        '<img src="' +
        m.image_url +
        '" alt="' +
        m.title +
        '" loading="lazy"/>' +
        "<p class=\"hint\">" +
        (m.credit || "") +
        ". " +
        (m.license_note || "") +
        "</p></div>";
    }
  }

  function selectObject(id) {
    state.objectId = id;
    fetchJson("/api/black-holes/object/" + encodeURIComponent(id)).then(function (body) {
      if (!body.ok) {
        setStatus(body.error || "Object load failed");
        return;
      }
      state.object = body.object;
      renderObjects((state.payload && state.payload.objects) || []);
      renderDetail(body.object);
      setStatus("Selected " + body.object.name);
    });
  }

  function refreshScale() {
    var id = ($("bh-scale-select") && $("bh-scale-select").value) || state.scaleId || "";
    state.scaleId = id;
    var q = id ? "?example_id=" + encodeURIComponent(id) : "";
    return fetchJson("/api/black-holes/scale" + q).then(renderScale);
  }

  function refreshApproach() {
    var slider = $("bh-approach-time");
    var progress = slider ? Number(slider.value) / 100 : 0;
    return fetchJson("/api/black-holes/approach?progress=" + progress).then(function (data) {
      state.approachId = data.region && data.region.id;
      renderApproach(data);
    });
  }

  function refreshLensing() {
    var slider = $("bh-lensing-strength");
    state.lensStrength = slider ? Number(slider.value) / 100 : 0.55;
    return fetchJson("/api/black-holes/lensing?strength=" + state.lensStrength).then(renderLensing);
  }

  function refreshTidal() {
    var id = ($("bh-tidal-select") && $("bh-tidal-select").value) || state.tidalId;
    state.tidalId = id;
    return fetchJson("/api/black-holes/tidal?example_id=" + encodeURIComponent(id)).then(renderTidal);
  }

  function speak(segment) {
    if (root.CartographyNarration && typeof root.CartographyNarration.speakExhibit === "function") {
      fetchJson("/api/black-holes/narration?segment=" + encodeURIComponent(segment)).then(function (body) {
        if (!body.ok) {
          setStatus(body.error || "Narration unavailable");
          return;
        }
        root.CartographyNarration.speakExhibit({
          text: body.text,
          feature: "black_holes",
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
      setStatus("Select an object first");
      return;
    }
    postJson("/api/black-holes/focus", { object_id: state.objectId }).then(function (body) {
      setStatus(body.message || (body.focused ? "Focused" : "Focus attempted"));
    });
  }

  function bind() {
    var scaleSel = $("bh-scale-select");
    if (scaleSel) scaleSel.addEventListener("change", refreshScale);
    var approach = $("bh-approach-time");
    if (approach) approach.addEventListener("input", refreshApproach);
    var lens = $("bh-lensing-strength");
    if (lens) lens.addEventListener("input", refreshLensing);
    var tidal = $("bh-tidal-select");
    if (tidal) {
      tidal.innerHTML =
        '<option value="stellar">Stellar-mass horizon tides</option><option value="smbh">Supermassive horizon tides</option>';
      tidal.addEventListener("change", refreshTidal);
    }
    var focusBtn = $("btn-bh-focus");
    if (focusBtn) focusBtn.addEventListener("click", focusSky);
    var map = {
      "btn-bh-what": "what_is",
      "btn-bh-horizon": "horizon",
      "btn-bh-scale": "scale",
      "btn-bh-accretion": "accretion",
      "btn-bh-lensing": "lensing",
      "btn-bh-tidal": "tidal",
      "btn-bh-sgr": "sgr_a",
      "btn-bh-m87": "m87",
      "btn-bh-detection": "detection",
      "btn-bh-closing": "closing",
    };
    Object.keys(map).forEach(function (btnId) {
      var btn = $(btnId);
      if (btn) {
        btn.addEventListener("click", function () {
          speak(map[btnId]);
        });
      }
    });
    var stop = $("btn-bh-stop-narration");
    if (stop && root.CartographyNarration && root.CartographyNarration.stop) {
      stop.addEventListener("click", function () {
        root.CartographyNarration.stop();
        setStatus("Narration stopped");
      });
    }
  }

  function init() {
    if (!$("black-holes-card")) return;
    bind();
    fetchJson("/api/black-holes")
      .then(function (payload) {
        state.payload = payload;
        renderLegend(payload.classification_legend);
        renderScience(payload.science);
        renderObjects(payload.objects);
        renderDetection(payload.detection_methods);
        if (payload.accretion_lab && $("bh-accretion")) {
          $("bh-accretion").innerHTML =
            badge(payload.accretion_lab.classification) +
            " " +
            (payload.accretion_lab.label || "") +
            "<ul class=\"bh-points\">" +
            (payload.accretion_lab.points || [])
              .map(function (p) {
                return "<li>" + p + "</li>";
              })
              .join("") +
            "</ul>";
        }
        var first = payload.objects && payload.objects[0];
        if (first) selectObject(first.id);
        return Promise.all([refreshScale(), refreshApproach(), refreshLensing(), refreshTidal()]);
      })
      .then(function () {
        setStatus("Black Holes ready. Narration stays silent until Listen.");
      })
      .catch(function (err) {
        setStatus("Black Holes failed to load: " + err);
      });
  }

  function showFromExhibitStep(step) {
    if (!step || step.step_type !== "black_holes") return;
    if (step.black_holes_object_id) selectObject(step.black_holes_object_id);
    if (step.scientific_view === "scale") refreshScale();
    if (step.scientific_view === "approach") refreshApproach();
    if (step.scientific_view === "lensing") refreshLensing();
    if (step.scientific_view === "tidal") refreshTidal();
  }

  root.BlackHoles = { init: init, showFromExhibitStep: showFromExhibitStep, selectObject: selectObject };
  if (typeof module !== "undefined" && module.exports) module.exports = root.BlackHoles;
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})(window);
