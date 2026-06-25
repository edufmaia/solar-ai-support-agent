"use strict";

(function () {
  if (window.__solarAiWidgetLoaded) return;
  window.__solarAiWidgetLoaded = true;

  var script = document.currentScript;
  var ORIGIN = new URL(script.src).origin;
  var teaserAttr = script.getAttribute("data-teaser");
  var teaserText = teaserAttr === null ? "Posso ajudar?" : teaserAttr;
  var teaserEnabled = teaserAttr !== "off";

  var PRIMARY = "#f59e0b";
  var ON_PRIMARY = "#ffffff";

  // ---- root container -------------------------------------------------
  var root = document.createElement("div");
  root.id = "solar-ai-widget";
  document.body.appendChild(root);

  var style = document.createElement("style");
  style.textContent = [
    "#solar-ai-widget{position:fixed;right:20px;bottom:20px;z-index:2147483000;font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;}",
    "#solar-ai-launcher{width:56px;height:56px;border-radius:50%;border:none;cursor:pointer;box-shadow:0 6px 20px rgba(0,0,0,.25);font-size:24px;line-height:1;display:flex;align-items:center;justify-content:center;}",
    "#solar-ai-teaser{position:absolute;right:0;bottom:70px;max-width:220px;background:#fff;color:#1f2430;border-radius:12px;box-shadow:0 6px 20px rgba(0,0,0,.18);padding:10px 28px 10px 12px;font-size:14px;line-height:1.35;cursor:pointer;}",
    "#solar-ai-teaser .x{position:absolute;top:4px;right:6px;cursor:pointer;color:#9aa0aa;font-size:14px;}",
    "#solar-ai-panel{position:absolute;right:0;bottom:70px;width:384px;height:600px;max-height:80vh;border-radius:16px;overflow:hidden;box-shadow:0 12px 40px rgba(0,0,0,.28);display:none;background:#fff;}",
    "#solar-ai-panel.open{display:block;}",
    "#solar-ai-panel iframe{width:100%;height:100%;border:0;}",
    "@media (max-width:480px){#solar-ai-panel{position:fixed;right:0;bottom:0;width:100vw;height:100vh;max-height:100vh;border-radius:0;}}",
  ].join("");
  document.head.appendChild(style);

  // ---- launcher -------------------------------------------------------
  var launcher = document.createElement("button");
  launcher.id = "solar-ai-launcher";
  launcher.setAttribute("aria-label", "Abrir chat");
  launcher.textContent = "💬";
  launcher.style.background = PRIMARY;
  launcher.style.color = ON_PRIMARY;
  root.appendChild(launcher);

  // ---- panel (lazy iframe) -------------------------------------------
  var panel = document.createElement("div");
  panel.id = "solar-ai-panel";
  root.appendChild(panel);
  var iframeLoaded = false;

  function ensureIframe() {
    if (iframeLoaded) return;
    var iframe = document.createElement("iframe");
    iframe.src = ORIGIN + "/ui/?embed=1";
    iframe.title = "Chat";
    panel.appendChild(iframe);
    iframeLoaded = true;
  }

  function openPanel() {
    ensureIframe();
    panel.classList.add("open");
    launcher.textContent = "✕";
    hideTeaser();
  }
  function closePanel() {
    panel.classList.remove("open");
    launcher.textContent = "💬";
  }
  function togglePanel() {
    panel.classList.contains("open") ? closePanel() : openPanel();
  }
  launcher.addEventListener("click", togglePanel);

  // ---- teaser ---------------------------------------------------------
  var teaser = null;
  function hideTeaser() {
    if (teaser) {
      teaser.remove();
      teaser = null;
    }
  }
  function showTeaser() {
    if (!teaserEnabled) return;
    if (localStorage.getItem("solar_ai_teaser_seen") === "1") return;
    teaser = document.createElement("div");
    teaser.id = "solar-ai-teaser";
    var span = document.createElement("span");
    span.textContent = teaserText;
    var x = document.createElement("span");
    x.className = "x";
    x.textContent = "✕";
    x.addEventListener("click", function (e) {
      e.stopPropagation();
      localStorage.setItem("solar_ai_teaser_seen", "1");
      hideTeaser();
    });
    teaser.appendChild(span);
    teaser.appendChild(x);
    teaser.addEventListener("click", function () {
      localStorage.setItem("solar_ai_teaser_seen", "1");
      openPanel();
    });
    root.appendChild(teaser);
  }
  setTimeout(showTeaser, 3000);

  // ---- messages from the iframe --------------------------------------
  window.addEventListener("message", function (event) {
    if (event.origin !== ORIGIN) return;
    var data = event.data || {};
    if (data.type === "solar-ai:branding") {
      if (data.primary_color) {
        PRIMARY = data.primary_color;
        launcher.style.background = PRIMARY;
      }
      if (data.text_on_primary) {
        ON_PRIMARY = data.text_on_primary;
        launcher.style.color = ON_PRIMARY;
      }
    } else if (data.type === "solar-ai:close") {
      closePanel();
    }
  });
})();
