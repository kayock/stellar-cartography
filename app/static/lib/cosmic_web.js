/* cosmic_web.js
 * Interactive Cosmic Web lab: illustrative structure growth + survey/simulation anchors.
 */
(function (root) {
  "use strict";

  var state = {
    payload: null,
    objectId: null,
    object: null,
    structure: null,
    layers: { galaxies: true, filaments: true, nodes: true, voids: true },
  };

  var els = {};

  function $(id) {
    return document.getElementById(id);
  }

  function escapeHtml(text) {
    return String(text == null ? "" : text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function setStatus(msg) {
    if (els.status) els.status.textContent = msg || "";
  }

  function on(id, evt, fn) {
    var node = $(id);
    if (node) node.addEventListener(evt, fn);
  }

  async function fetchJson(url, options) {
    var resp = await fetch(url, options || { cache: "no-store" });
    var data = await resp.json().catch(function () { return null; });
    return { ok: resp.ok, status: resp.status, data: data };
  }

  function classBadge(cls) {
    var label = String(cls || "illustration").toUpperCase();
    return "<span class=\"archaeo-badge cosmic-web-class cosmic-web-class-" +
      escapeHtml(String(cls || "illustration")) + "\">" + escapeHtml(label) + "</span>";
  }

  async function init() {
    els.card = $("cosmic-web-card");
    els.status = $("cosmic-web-status");
    els.science = $("cosmic-web-science");
    els.svg = $("cosmic-web-svg");
    els.caption = $("cosmic-web-caption");
    els.slider = $("cosmic-web-time");
    els.objects = $("cosmic-web-objects");
    els.detail = $("cosmic-web-detail");
    els.media = $("cosmic-web-media");
    els.legend = $("cosmic-web-legend");
    if (!els.card) return;

    ["galaxies", "filaments", "nodes", "voids"].forEach(function (layer) {
      on("cw-layer-" + layer, "change", function (ev) {
        state.layers[layer] = !!(ev.target && ev.target.checked);
        updateStructure(null, els.slider ? Number(els.slider.value) / 100 : null);
      });
    });

    on("btn-cosmic-web-focus", "click", focusSelected);
    on("btn-cosmic-web-intro", "click", function () { speakSegment("intro"); });
    on("btn-cosmic-web-fluctuations", "click", function () { speakSegment("fluctuations"); });
    on("btn-cosmic-web-gravity", "click", function () { speakSegment("gravity"); });
    on("btn-cosmic-web-filaments", "click", function () { speakSegment("filaments"); });
    on("btn-cosmic-web-voids", "click", function () { speakSegment("voids"); });
    on("btn-cosmic-web-surveys", "click", function () { speakSegment("surveys"); });
    on("btn-cosmic-web-night-sky", "click", function () { speakSegment("night_sky"); });
    on("btn-cosmic-web-closing", "click", function () { speakSegment("closing"); });
    on("btn-cosmic-web-stop-narration", "click", function () {
      if (root.CartographyNarration && root.CartographyNarration.stopNarration) {
        root.CartographyNarration.stopNarration(false);
      }
      setStatus("Narration stopped.");
    });
    if (els.slider) {
      els.slider.addEventListener("input", function () {
        updateStructure(null, Number(els.slider.value) / 100);
      });
    }

    try {
      var res = await fetchJson("/api/cosmic-web");
      if (!res.ok || !res.data || !res.data.ok) {
        setStatus("Cosmic Web data is unavailable.");
        return;
      }
      state.payload = res.data;
      renderShell(res.data);
      await updateStructure("t0", 0);
      if ((res.data.objects || []).length) {
        await selectObject(res.data.objects[0].id);
      }
      setStatus("Cosmic Web ready. Narration stays silent until you press Listen.");
    } catch (_err) {
      setStatus("Could not load Cosmic Web.");
    }
  }

  function renderShell(data) {
    if (els.legend) {
      var legend = data.classification_legend || {};
      els.legend.innerHTML = Object.keys(legend).map(function (key) {
        return "<p class=\"hint\">" + classBadge(key) + " " + escapeHtml(legend[key]) + "</p>";
      }).join("");
    }
    if (els.science) {
      var sci = data.science || {};
      els.science.innerHTML =
        "<p class=\"hint\"><strong>What is the cosmic web?</strong> " + escapeHtml(sci.what_is || "") + "</p>" +
        "<p class=\"hint\"><strong>Not random:</strong> " + escapeHtml(sci.not_uniform || "") + "</p>" +
        "<p class=\"hint\"><strong>Gravity & dark matter:</strong> " + escapeHtml(sci.gravity_dark_matter || "") + "</p>" +
        "<p class=\"hint\"><strong>Filaments, nodes, voids:</strong> " + escapeHtml(sci.filaments_nodes_voids || "") + "</p>" +
        "<p class=\"hint\"><strong>Observation vs simulation:</strong> " + escapeHtml(sci.observation_vs_simulation || "") + "</p>" +
        "<p class=\"hint cosmic-web-disclaimer\">" + classBadge("illustration") + " " +
        escapeHtml(data.illustrative_disclaimer || "") + "</p>";
    }
    if (els.objects) {
      els.objects.innerHTML = (data.objects || []).map(function (obj) {
        return "<button type=\"button\" class=\"event-chip\" data-cw-object=\"" +
          escapeHtml(obj.id) + "\">" + escapeHtml(obj.short_name || obj.name) +
          " " + classBadge(obj.media_classification || "illustration") + "</button>";
      }).join("") || "<p class=\"hint\">No objects enabled.</p>";
      els.objects.querySelectorAll("[data-cw-object]").forEach(function (btn) {
        btn.addEventListener("click", function () {
          selectObject(btn.getAttribute("data-cw-object"));
        });
      });
    }
  }

  async function updateStructure(stepId, progress) {
    var params = [];
    if (stepId) params.push("step=" + encodeURIComponent(stepId));
    else if (progress != null && !isNaN(progress)) params.push("progress=" + encodeURIComponent(String(progress)));
    Object.keys(state.layers).forEach(function (key) {
      params.push("layer_" + key + "=" + (state.layers[key] ? "1" : "0"));
    });
    var url = "/api/cosmic-web/structure" + (params.length ? "?" + params.join("&") : "");
    var res = await fetchJson(url);
    if (!res.ok || !res.data || !res.data.ok) {
      setStatus((res.data && res.data.error) || "Structure state unavailable.");
      return;
    }
    state.structure = res.data;
    drawStructure(res.data);
    if (els.caption) els.caption.textContent = (res.data.step && res.data.step.caption) || "";
    if (els.slider && res.data.step && typeof res.data.step.progress === "number") {
      els.slider.value = String(Math.round(res.data.step.progress * 100));
    }
    var layers = res.data.layers || {};
    Object.keys(layers).forEach(function (key) {
      state.layers[key] = !!layers[key];
      var box = $("cw-layer-" + key);
      if (box) box.checked = !!layers[key];
    });
  }

  function drawStructure(geo) {
    if (!els.svg) return;
    var layers = geo.layers || {};
    var clustering = (geo.step && typeof geo.step.clustering === "number") ? geo.step.clustering : 0.5;
    var html = "";
    html += "<rect class=\"cosmic-web-sky\" x=\"0\" y=\"0\" width=\"100\" height=\"100\" />";
    html += "<text class=\"cosmic-web-badge\" x=\"3\" y=\"7\">" + escapeHtml(geo.label || "ILLUSTRATIVE") + "</text>";

    if (layers.voids) {
      (geo.void_regions || []).forEach(function (v) {
        html += "<ellipse class=\"cosmic-web-void\" cx=\"" + v.cx + "\" cy=\"" + v.cy +
          "\" rx=\"" + v.rx + "\" ry=\"" + v.ry + "\" />";
      });
    }
    if (layers.filaments) {
      (geo.filament_paths || []).forEach(function (path) {
        if (!path || path.length < 2) return;
        var d = path.map(function (pt, i) {
          return (i === 0 ? "M" : "L") + pt[0] + " " + pt[1];
        }).join(" ");
        html += "<path class=\"cosmic-web-filament\" d=\"" + d + "\" />";
      });
    }
    if (layers.galaxies) {
      (geo.seed_points || []).forEach(function (pt, idx) {
        var jitter = (idx % 3) * 0.4 * (1 - clustering);
        var x = pt[0] + jitter;
        var y = pt[1] - jitter * 0.5;
        // Pull toward nearest node as clustering grows (illustrative only)
        var nodes = geo.node_points || [];
        if (nodes.length && clustering > 0.2) {
          var target = nodes[idx % nodes.length];
          x = x + (target[0] - x) * clustering * 0.35;
          y = y + (target[1] - y) * clustering * 0.35;
        }
        html += "<circle class=\"cosmic-web-galaxy\" cx=\"" + x + "\" cy=\"" + y + "\" r=\"0.9\" />";
      });
    }
    if (layers.nodes) {
      (geo.node_points || []).forEach(function (pt) {
        html += "<circle class=\"cosmic-web-node\" cx=\"" + pt[0] + "\" cy=\"" + pt[1] + "\" r=\"2.4\" />";
      });
    }
    els.svg.innerHTML = html;
  }

  async function selectObject(objectId) {
    var res = await fetchJson("/api/cosmic-web/object/" + encodeURIComponent(objectId));
    if (!res.ok || !res.data || !res.data.ok) {
      setStatus((res.data && res.data.error) || "Object unavailable.");
      return;
    }
    state.objectId = objectId;
    state.object = res.data.object;
    renderObject(res.data.object);
    if (els.objects) {
      els.objects.querySelectorAll("[data-cw-object]").forEach(function (btn) {
        btn.classList.toggle("is-active", btn.getAttribute("data-cw-object") === objectId);
      });
    }
  }

  function renderObject(obj) {
    if (!els.detail) return;
    var points = (obj.teaching_points || []).map(function (p) {
      return "<li>" + escapeHtml(p) + "</li>";
    }).join("");
    var sources = (obj.sources || []).map(function (s) {
      return "<li>" + classBadge(s.classification || "observation") +
        " <a href=\"" + escapeHtml(s.url) + "\" target=\"_blank\" rel=\"noopener noreferrer\">" +
        escapeHtml(s.title) + "</a> <span class=\"hint\">(" + escapeHtml(s.organization || "") + ")</span></li>";
    }).join("");
    els.detail.innerHTML =
      "<div class=\"target-name\">" + escapeHtml(obj.name) + "</div>" +
      "<p class=\"hint\">" + escapeHtml(obj.summary || "") + "</p>" +
      (points ? "<ul class=\"cosmic-web-points\">" + points + "</ul>" : "") +
      "<p class=\"hint\">Stellarium sky anchor: <code>" + escapeHtml(obj.stellarium_search || "") + "</code>" +
      (obj.stellarium_match_mode === "host_sky" ? " (host-sky)" : "") + "</p>" +
      (obj.stellarium_note ? "<p class=\"hint\">" + escapeHtml(obj.stellarium_note) + "</p>" : "") +
      "<details class=\"constellation-section\" open><summary>Sources</summary><ul>" + sources + "</ul></details>";

    var media = obj.media || {};
    if (els.media) {
      if (media.image_url) {
        els.media.innerHTML =
          "<figure class=\"cosmic-web-figure\">" +
          classBadge(media.classification || "illustration") +
          "<img src=\"" + escapeHtml(media.image_url) + "\" alt=\"" + escapeHtml(media.title || obj.name) +
          "\" loading=\"lazy\" referrerpolicy=\"no-referrer\">" +
          "<figcaption class=\"hint\">" + escapeHtml(media.title || "") + " — " +
          escapeHtml(media.credit || "") + ". " +
          "<a href=\"" + escapeHtml(media.source_page_url || "#") +
          "\" target=\"_blank\" rel=\"noopener noreferrer\">Source page</a>. " +
          escapeHtml(media.license_note || "") +
          (media.note ? " " + escapeHtml(media.note) : "") +
          "</figcaption></figure>";
      } else {
        els.media.innerHTML = "<p class=\"hint\">No curated image for this item.</p>";
      }
    }
  }

  async function focusSelected() {
    if (!state.objectId) {
      setStatus("Select an anchor first.");
      return;
    }
    setStatus("Focusing Stellarium sky anchor…");
    var res = await fetchJson("/api/cosmic-web/focus", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ object_id: state.objectId }),
      cache: "no-store",
    });
    var data = res.data || {};
    if (!res.ok || !data.ok) {
      setStatus((data && data.error) || "Focus request failed.");
      return;
    }
    setStatus(data.message || (data.focused ? "Focused." : "Stellarium unavailable."));
    if (data.focused && root.ExperienceLayer && root.ExperienceLayer.refreshSkyState) {
      root.ExperienceLayer.refreshSkyState();
    }
  }

  async function speakSegment(segment) {
    var res = await fetchJson("/api/cosmic-web/narration?segment=" + encodeURIComponent(segment));
    if (!res.ok || !res.data || !res.data.ok) {
      setStatus((res.data && res.data.error) || "Narration unavailable.");
      return;
    }
    setStatus("Narration ready: " + (res.data.title || segment) + ". Autoplay is off.");
    if (root.CartographyNarration && root.CartographyNarration.speakExhibit) {
      root.CartographyNarration.speakExhibit(res.data.text || "", {
        title: res.data.title,
        kind: "cosmic_web",
        segment: segment,
      });
    }
  }

  function showFromExhibitStep(step) {
    if (!step) return;
    if (step.cosmic_web_object_id) selectObject(step.cosmic_web_object_id);
    if (step.cosmic_web_structure_step) updateStructure(step.cosmic_web_structure_step, null);
    var card = $("cosmic-web-card");
    if (card && typeof card.open === "boolean") card.open = true;
    if (card && card.scrollIntoView) card.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  root.CosmicWeb = {
    init: init,
    showFromExhibitStep: showFromExhibitStep,
    selectObject: selectObject,
  };

  if (typeof module !== "undefined" && module.exports) module.exports = root.CosmicWeb;
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})(typeof window !== "undefined" ? window : globalThis);
