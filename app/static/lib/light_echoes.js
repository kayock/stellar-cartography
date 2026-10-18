/* light_echoes.js
 * Interactive Light Echoes lab: illustrative geometry + real-object examples.
 * Reuses Cartography narration/TTS hooks. Stellarium focus is explicit and optional.
 */
(function (root) {
  "use strict";

  var state = {
    payload: null,
    objectId: null,
    object: null,
    geometry: null,
    narrationSegment: "intro",
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

  async function init() {
    els.card = $("light-echoes-card");
    els.body = $("light-echoes-body");
    els.status = $("light-echoes-status");
    els.science = $("light-echoes-science");
    els.svg = $("light-echoes-svg");
    els.caption = $("light-echoes-caption");
    els.slider = $("light-echoes-time");
    els.objects = $("light-echoes-objects");
    els.detail = $("light-echoes-detail");
    els.media = $("light-echoes-media");
    if (!els.card) return;

    on("btn-light-echoes-intro", "click", function () { speakSegment("intro"); });
    on("btn-light-echoes-geometry-narration", "click", function () { speakSegment("geometry"); });
    on("btn-light-echoes-expansion", "click", function () { speakSegment("apparent_expansion"); });
    on("btn-light-echoes-examples", "click", function () { speakSegment("examples"); });
    on("btn-light-echoes-closing", "click", function () { speakSegment("closing"); });
    on("btn-light-echoes-focus", "click", focusSelected);
    on("btn-light-echoes-stop-narration", "click", function () {
      if (root.CartographyNarration && root.CartographyNarration.stopNarration) {
        root.CartographyNarration.stopNarration(false);
      }
      setStatus("Narration stopped.");
    });
    if (els.slider) {
      els.slider.addEventListener("input", function () {
        updateGeometry(null, Number(els.slider.value) / 100);
      });
    }

    try {
      var res = await fetchJson("/api/light-echoes");
      if (!res.ok || !res.data || !res.data.ok) {
        setStatus("Light Echoes data is unavailable.");
        return;
      }
      state.payload = res.data;
      renderShell(res.data);
      await updateGeometry(res.data.geometry_demo && res.data.geometry_demo.step_count ? null : "t0", 0);
      if ((res.data.objects || []).length) {
        await selectObject(res.data.objects[0].id);
      }
      setStatus("Light Echoes ready. Narration stays silent until you press Listen.");
    } catch (_err) {
      setStatus("Could not load Light Echoes.");
    }
  }

  function renderShell(data) {
    if (els.science) {
      var sci = data.science || {};
      els.science.innerHTML =
        "<p class=\"hint\"><strong>What is a light echo?</strong> " + escapeHtml(sci.what_is || "") + "</p>" +
        "<p class=\"hint\"><strong>Not matter racing out:</strong> " + escapeHtml(sci.not_matter_expansion || "") + "</p>" +
        "<p class=\"hint\"><strong>Geometry:</strong> " + escapeHtml(sci.geometry || "") + "</p>" +
        "<p class=\"hint\"><strong>Apparent superluminal motion:</strong> " + escapeHtml(sci.apparent_superluminal || "") + "</p>" +
        "<p class=\"hint light-echoes-disclaimer\"><span class=\"archaeo-badge\">ILLUSTRATIVE</span> " +
        escapeHtml(data.illustrative_disclaimer || "") + "</p>";
    }
    if (els.objects) {
      var buttons = (data.objects || []).map(function (obj) {
        return "<button type=\"button\" class=\"event-chip\" data-le-object=\"" +
          escapeHtml(obj.id) + "\">" + escapeHtml(obj.short_name || obj.name) + "</button>";
      }).join("");
      els.objects.innerHTML = buttons || "<p class=\"hint\">No objects enabled.</p>";
      els.objects.querySelectorAll("[data-le-object]").forEach(function (btn) {
        btn.addEventListener("click", function () {
          selectObject(btn.getAttribute("data-le-object"));
        });
      });
    }
  }

  async function updateGeometry(stepId, progress) {
    var url = "/api/light-echoes/geometry";
    if (stepId) url += "?step=" + encodeURIComponent(stepId);
    else if (progress != null && !isNaN(progress)) url += "?progress=" + encodeURIComponent(String(progress));
    var res = await fetchJson(url);
    if (!res.ok || !res.data || !res.data.ok) {
      setStatus((res.data && res.data.error) || "Geometry state unavailable.");
      return;
    }
    state.geometry = res.data;
    drawGeometry(res.data);
    if (els.caption) {
      els.caption.textContent = (res.data.step && res.data.step.caption) || "";
    }
    if (els.slider && res.data.step && typeof res.data.step.progress === "number") {
      els.slider.value = String(Math.round(res.data.step.progress * 100));
    }
  }

  function drawGeometry(geo) {
    if (!els.svg) return;
    var nodes = geo.nodes || {};
    var illuminated = ((geo.step && geo.step.illuminated) || []);
    var lit = {};
    illuminated.forEach(function (id) { lit[id] = true; });

    function pt(id) {
      var n = nodes[id] || { x: 0, y: 0 };
      return { x: Number(n.x), y: Number(n.y), label: n.label || id };
    }

    function line(a, b, cls) {
      return "<line class=\"" + cls + "\" x1=\"" + a.x + "\" y1=\"" + a.y +
        "\" x2=\"" + b.x + "\" y2=\"" + b.y + "\" />";
    }

    function node(id, extra) {
      var p = pt(id);
      var on = lit[id] ? " light-echoes-node-on" : "";
      return "<g class=\"light-echoes-node" + on + " " + (extra || "") + "\">" +
        "<circle cx=\"" + p.x + "\" cy=\"" + p.y + "\" r=\"3.2\" />" +
        "<text x=\"" + p.x + "\" y=\"" + (p.y - 5) + "\">" + escapeHtml(p.label) + "</text></g>";
    }

    var source = pt("source");
    var observer = pt("observer");
    var near = pt("near");
    var far = pt("far");
    var sheet = pt("sheet");

    var html = "";
    html += "<rect class=\"light-echoes-sky\" x=\"0\" y=\"0\" width=\"100\" height=\"100\" />";
    html += line(source, observer, "light-echoes-path light-echoes-path-direct");
    html += line(source, near, "light-echoes-path light-echoes-path-echo" + (lit.near ? " is-on" : ""));
    html += line(near, observer, "light-echoes-path light-echoes-path-echo" + (lit.near ? " is-on" : ""));
    html += line(source, far, "light-echoes-path light-echoes-path-echo" + (lit.far ? " is-on" : ""));
    html += line(far, observer, "light-echoes-path light-echoes-path-echo" + (lit.far ? " is-on" : ""));
    html += line(source, sheet, "light-echoes-path light-echoes-path-echo" + (lit.sheet ? " is-on" : ""));
    html += line(sheet, observer, "light-echoes-path light-echoes-path-echo" + (lit.sheet ? " is-on" : ""));
    html += node("source", "is-source");
    html += node("observer", "is-observer");
    html += node("near");
    html += node("far");
    html += node("sheet");
    html += "<text class=\"light-echoes-badge\" x=\"4\" y=\"8\">" +
      escapeHtml(geo.label || "ILLUSTRATIVE") + "</text>";
    els.svg.innerHTML = html;
  }

  async function selectObject(objectId) {
    var res = await fetchJson("/api/light-echoes/object/" + encodeURIComponent(objectId));
    if (!res.ok || !res.data || !res.data.ok) {
      setStatus((res.data && res.data.error) || "Object unavailable.");
      return;
    }
    state.objectId = objectId;
    state.object = res.data.object;
    renderObject(res.data.object);
    if (els.objects) {
      els.objects.querySelectorAll("[data-le-object]").forEach(function (btn) {
        btn.classList.toggle("is-active", btn.getAttribute("data-le-object") === objectId);
      });
    }
  }

  function renderObject(obj) {
    if (!els.detail) return;
    var years = (obj.key_years || []).join(", ");
    var points = (obj.teaching_points || []).map(function (p) {
      return "<li>" + escapeHtml(p) + "</li>";
    }).join("");
    var sources = (obj.sources || []).map(function (s) {
      return "<li><a href=\"" + escapeHtml(s.url) + "\" target=\"_blank\" rel=\"noopener noreferrer\">" +
        escapeHtml(s.title) + "</a> <span class=\"hint\">(" + escapeHtml(s.organization || "") + ")</span></li>";
    }).join("");
    els.detail.innerHTML =
      "<div class=\"target-name\">" + escapeHtml(obj.name) + "</div>" +
      "<p class=\"hint\">" + escapeHtml(obj.summary || "") + "</p>" +
      (years ? "<p class=\"hint\">Key years: " + escapeHtml(years) + "</p>" : "") +
      (points ? "<ul class=\"light-echoes-points\">" + points + "</ul>" : "") +
      "<p class=\"hint\">Stellarium search: <code>" + escapeHtml(obj.stellarium_search || "") + "</code>" +
      (obj.stellarium_match_mode === "host_sky" ? " (host-sky context)" : "") + "</p>" +
      (obj.stellarium_note ? "<p class=\"hint\">" + escapeHtml(obj.stellarium_note) + "</p>" : "") +
      "<details class=\"constellation-section\" open><summary>Sources</summary><ul>" + sources + "</ul></details>";

    var media = obj.media || {};
    if (els.media) {
      if (media.image_url) {
        els.media.innerHTML =
          "<figure class=\"light-echoes-figure\">" +
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
        els.media.innerHTML = "<p class=\"hint\">No curated image for this object.</p>";
      }
    }
  }

  async function focusSelected() {
    if (!state.objectId) {
      setStatus("Select an object first.");
      return;
    }
    setStatus("Focusing in Stellarium…");
    var res = await fetchJson("/api/light-echoes/focus", {
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
    if (data.focused) {
      setStatus("Stellarium focused on " + (data.name || state.objectId) + ".");
      if (root.ExperienceLayer && root.ExperienceLayer.refreshSkyState) {
        root.ExperienceLayer.refreshSkyState();
      }
    } else {
      setStatus(data.message || "Stellarium unavailable; exhibit content still works.");
    }
  }

  async function speakSegment(segment) {
    state.narrationSegment = segment;
    var res = await fetchJson("/api/light-echoes/narration?segment=" + encodeURIComponent(segment));
    if (!res.ok || !res.data || !res.data.ok) {
      setStatus((res.data && res.data.error) || "Narration unavailable.");
      return;
    }
    var text = res.data.text || "";
    setStatus("Narration ready: " + (res.data.title || segment) + ". Autoplay is off.");
    if (root.CartographyNarration && typeof root.CartographyNarration.speakExhibit === "function") {
      root.CartographyNarration.speakExhibit(text, {
        title: res.data.title,
        kind: "light_echoes",
        segment: segment,
      });
    } else {
      setStatus("TTS hook unavailable; narration text loaded (autoplay remains off).");
    }
  }

  function showFromExhibitStep(step) {
    if (!step) return;
    if (step.light_echo_object_id) {
      selectObject(step.light_echo_object_id);
    }
    if (step.light_echo_geometry_step) {
      updateGeometry(step.light_echo_geometry_step, null);
    }
    if (step.light_echo_narration_segment) {
      state.narrationSegment = step.light_echo_narration_segment;
    }
    var card = $("light-echoes-card");
    if (card && typeof card.open === "boolean") card.open = true;
    if (card && card.scrollIntoView) {
      card.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }

  var LightEchoes = {
    init: init,
    showFromExhibitStep: showFromExhibitStep,
    selectObject: selectObject,
  };

  root.LightEchoes = LightEchoes;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = LightEchoes;
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})(typeof window !== "undefined" ? window : globalThis);
