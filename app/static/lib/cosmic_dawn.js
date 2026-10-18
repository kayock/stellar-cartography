/* cosmic_dawn.js — timeline, reionization, redshift, deep-field cards */
(function (root) {
  "use strict";

  var state = { payload: null, objectId: null };

  function $(id) {
    return document.getElementById(id);
  }

  function setStatus(msg) {
    var el = $("cd-status");
    if (el) el.textContent = msg || "";
  }

  function badge(cls) {
    return (
      '<span class="cd-class-badge cd-class-' +
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
    var el = $("cd-legend");
    if (!el || !legend) return;
    el.innerHTML = Object.keys(legend)
      .map(function (k) {
        return "<div>" + badge(k) + " " + legend[k] + "</div>";
      })
      .join("");
  }

  function renderScience(science) {
    var el = $("cd-science");
    if (!el || !science) return;
    var keys = ["recombination", "cmb", "dark_ages", "first_stars", "reionization", "jwst", "twenty_one_cm"];
    el.innerHTML = keys
      .filter(function (k) {
        return science[k];
      })
      .map(function (k) {
        return "<p><strong>" + k.replace(/_/g, " ") + ":</strong> " + science[k] + "</p>";
      })
      .join("");
  }

  function renderTimeline(data) {
    var svg = $("cd-timeline-svg");
    var cap = $("cd-timeline-caption");
    if (!svg || !data || !data.ok) return;
    var epochs = data.epochs || [];
    var html = '<rect class="cd-sky" width="100" height="100"/>';
    html += '<line x1="8" y1="70" x2="92" y2="70" class="cd-axis"/>';
    epochs.forEach(function (e, i) {
      var x = 8 + e.progress * 84;
      var active = data.epoch && data.epoch.id === e.id;
      html +=
        '<circle cx="' +
        x +
        '" cy="70" r="' +
        (active ? 3.2 : 2) +
        '" class="cd-epoch' +
        (active ? " is-active" : "") +
        '"/>';
      if (active) {
        html += '<text x="' + x + '" y="58" class="cd-label">' + e.label + "</text>";
      }
    });
    html += '<text x="50" y="14" class="cd-label">' + (data.label || "") + "</text>";
    // Simple plasma→clear motif
    var p = (data.epoch && data.epoch.progress) || 0;
    html +=
      '<rect x="10" y="22" width="' +
      (80 * (1 - p * 0.7)) +
      '" height="18" class="cd-fog" opacity="' +
      (0.55 - p * 0.35) +
      '"/>';
    svg.innerHTML = html;
    if (cap) {
      var ep = data.epoch || {};
      cap.textContent =
        (ep.label || "") +
        ": " +
        (ep.caption || "") +
        " z≈" +
        (ep.z_approx || "?") +
        "; age " +
        (ep.age_note || "?") +
        ". " +
        (data.disclaimer || "");
    }
  }

  function renderRedshift(data) {
    var el = $("cd-redshift");
    if (!el || !data || !data.ok) return;
    el.innerHTML =
      badge(data.classification) +
      " " +
      (data.label || "") +
      "<p>Teaching z = <strong>" +
      data.z +
      "</strong> → scale factor a≈" +
      data.scale_factor_teaching +
      " · lookback hint: <em>" +
      data.lookback_hint +
      "</em></p>" +
      '<p class="hint">' +
      (data.disclaimer || "") +
      " Not ordinary Doppler through static space alone.</p>" +
      "<ul class=\"cd-points\">" +
      (data.points || [])
        .map(function (p) {
          return "<li>" + p + "</li>";
        })
        .join("") +
      "</ul>";
  }

  function renderReion(data) {
    var svg = $("cd-reion-svg");
    var cap = $("cd-reion-caption");
    if (!svg || !data || !data.ok) return;
    var html =
      '<rect class="cd-sky" width="100" height="100"/>' +
      '<rect class="cd-neutral" x="5" y="5" width="90" height="90" rx="2"/>' +
      '<text x="50" y="12" class="cd-label">' +
      (data.label || "") +
      "</text>";
    (data.bubbles || []).forEach(function (b) {
      html += '<circle cx="' + b.x + '" cy="' + b.y + '" r="' + b.r + '" class="cd-bubble"/>';
    });
    svg.innerHTML = html;
    if (cap) {
      cap.textContent =
        (data.stage ? data.stage.label + ": " + data.stage.caption + " " : "") +
        "Teaching ionized fraction≈" +
        data.ionized_fraction_teaching +
        ". " +
        (data.disclaimer || "");
    }
  }

  function renderStructure(data) {
    var svg = $("cd-structure-svg");
    var cap = $("cd-structure-caption");
    if (!svg || !data || !data.ok) return;
    var html =
      '<rect class="cd-sky" width="100" height="100"/>' +
      '<text x="50" y="12" class="cd-label">' +
      (data.label || "") +
      "</text>";
    (data.peaks || []).forEach(function (p) {
      html +=
        '<circle cx="' +
        p.x +
        '" cy="' +
        p.y +
        '" r="' +
        p.r +
        '" class="' +
        (p.halo ? "cd-halo" : "cd-seed") +
        '"/>';
    });
    svg.innerHTML = html;
    if (cap) {
      cap.innerHTML =
        (data.disclaimer || "") +
        " " +
        (data.note || "") +
        (data.related_special === "cosmic_web"
          ? ' <a href="#cosmic-web-card">Open Cosmic Web Special</a>'
          : "");
    }
  }

  function render21(block) {
    var el = $("cd-21cm");
    if (!el || !block) return;
    el.innerHTML =
      badge(block.classification) +
      " " +
      (block.label || "") +
      '<p class="hint">' +
      (block.disclaimer || "") +
      "</p><ul class=\"cd-points\">" +
      (block.points || [])
        .map(function (p) {
          return "<li>" + p + "</li>";
        })
        .join("") +
      "</ul>";
  }

  function renderObjects(objects) {
    var el = $("cd-objects");
    if (!el) return;
    el.innerHTML = (objects || [])
      .map(function (o) {
        var active = o.id === state.objectId ? " is-active" : "";
        return (
          '<button type="button" class="event-chip' +
          active +
          '" data-cd-id="' +
          o.id +
          '">' +
          (o.short_name || o.name) +
          "</button>"
        );
      })
      .join("");
    el.querySelectorAll("[data-cd-id]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        selectObject(btn.getAttribute("data-cd-id"));
      });
    });
  }

  function renderDetail(obj) {
    var detail = $("cd-detail");
    var media = $("cd-media");
    if (!detail || !obj) return;
    detail.innerHTML =
      "<h3>" +
      obj.name +
      "</h3>" +
      "<p>" +
      (obj.significance || "") +
      "</p>" +
      "<p class=\"hint\">" +
      (obj.epoch_note || "") +
      "</p>" +
      "<p class=\"hint\">Stellarium: " +
      (obj.stellarium_note || "") +
      "</p>";
    if (media && obj.media) {
      var m = obj.media;
      media.innerHTML =
        '<div class="cd-figure">' +
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
    fetchJson("/api/cosmic-dawn/object/" + encodeURIComponent(id)).then(function (body) {
      if (!body.ok) {
        setStatus(body.error || "Object load failed");
        return;
      }
      renderObjects((state.payload && state.payload.objects) || []);
      renderDetail(body.object);
      setStatus("Selected " + body.object.name);
    });
  }

  function refreshTimeline() {
    var slider = $("cd-timeline-time");
    var progress = slider ? Number(slider.value) / 100 : 0;
    return fetchJson("/api/cosmic-dawn/timeline?progress=" + progress).then(renderTimeline);
  }

  function refreshRedshift() {
    var slider = $("cd-redshift-z");
    var z = slider ? Number(slider.value) / 10 : 6;
    return fetchJson("/api/cosmic-dawn/redshift?z=" + z).then(renderRedshift);
  }

  function refreshReion() {
    var slider = $("cd-reion-time");
    var progress = slider ? Number(slider.value) / 100 : 0;
    return fetchJson("/api/cosmic-dawn/reionization?progress=" + progress).then(renderReion);
  }

  function refreshStructure() {
    var slider = $("cd-structure-time");
    var progress = slider ? Number(slider.value) / 100 : 0.4;
    return fetchJson("/api/cosmic-dawn/structure?progress=" + progress).then(renderStructure);
  }

  function speak(segment) {
    if (root.CartographyNarration && typeof root.CartographyNarration.speakExhibit === "function") {
      fetchJson("/api/cosmic-dawn/narration?segment=" + encodeURIComponent(segment)).then(function (body) {
        if (!body.ok) {
          setStatus(body.error || "Narration unavailable");
          return;
        }
        root.CartographyNarration.speakExhibit({
          text: body.text,
          feature: "cosmic_dawn",
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
      setStatus("Select a topic card first");
      return;
    }
    postJson("/api/cosmic-dawn/focus", { object_id: state.objectId }).then(function (body) {
      setStatus(body.message || (body.focused ? "Focused" : "Focus attempted"));
    });
  }

  function bind() {
    ["cd-timeline-time", "cd-redshift-z", "cd-reion-time", "cd-structure-time"].forEach(function (id) {
      var el = $(id);
      if (!el) return;
      el.addEventListener("input", function () {
        if (id === "cd-timeline-time") refreshTimeline();
        if (id === "cd-redshift-z") refreshRedshift();
        if (id === "cd-reion-time") refreshReion();
        if (id === "cd-structure-time") refreshStructure();
      });
    });
    var focusBtn = $("btn-cd-focus");
    if (focusBtn) focusBtn.addEventListener("click", focusSky);
    var map = {
      "btn-cd-lookback": "lookback",
      "btn-cd-recombination": "recombination",
      "btn-cd-cmb": "cmb",
      "btn-cd-dark": "dark_ages",
      "btn-cd-stars": "first_stars",
      "btn-cd-galaxies": "first_galaxies",
      "btn-cd-reion": "reionization",
      "btn-cd-jwst": "jwst",
      "btn-cd-21": "twenty_one_cm",
      "btn-cd-closing": "closing",
    };
    Object.keys(map).forEach(function (btnId) {
      var btn = $(btnId);
      if (btn) {
        btn.addEventListener("click", function () {
          speak(map[btnId]);
        });
      }
    });
    var stop = $("btn-cd-stop-narration");
    if (stop && root.CartographyNarration && root.CartographyNarration.stop) {
      stop.addEventListener("click", function () {
        root.CartographyNarration.stop();
        setStatus("Narration stopped");
      });
    }
  }

  function init() {
    if (!$("cosmic-dawn-card")) return;
    bind();
    fetchJson("/api/cosmic-dawn")
      .then(function (payload) {
        state.payload = payload;
        renderLegend(payload.classification_legend);
        renderScience(payload.science);
        renderObjects(payload.objects);
        render21(payload.twenty_one_cm);
        var first = payload.objects && payload.objects[0];
        if (first) selectObject(first.id);
        return Promise.all([refreshTimeline(), refreshRedshift(), refreshReion(), refreshStructure()]);
      })
      .then(function () {
        setStatus("Cosmic Dawn ready. Stellarium is present-day sky only. Narration silent until Listen.");
      })
      .catch(function (err) {
        setStatus("Cosmic Dawn failed to load: " + err);
      });
  }

  function showFromExhibitStep(step) {
    if (!step || step.step_type !== "cosmic_dawn") return;
    if (step.cosmic_dawn_object_id) selectObject(step.cosmic_dawn_object_id);
    if (step.scientific_view === "timeline") refreshTimeline();
    if (step.scientific_view === "reionization") refreshReion();
    if (step.scientific_view === "redshift") refreshRedshift();
    if (step.scientific_view === "structure") refreshStructure();
  }

  root.CosmicDawn = { init: init, showFromExhibitStep: showFromExhibitStep, selectObject: selectObject };
  if (typeof module !== "undefined" && module.exports) module.exports = root.CosmicDawn;
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})(window);
