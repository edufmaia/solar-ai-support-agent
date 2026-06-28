"use strict";

function row(label, value) {
  if (value === null || value === undefined || value === "") return "";
  return `<div class="row"><span class="label">${label}</span><span class="value">${value}</span></div>`;
}

function tempBadge(temp) {
  if (!temp) return '<span class="badge neutral">—</span>';
  const cls = ["hot", "warm", "cold"].includes(temp) ? temp : "neutral";
  return `<span class="badge ${cls}">${temp}</span>`;
}

export function money(v) {
  if (v === null || v === undefined) return null;
  const n = Number(v);
  return isNaN(n) ? v : `R$ ${n.toFixed(2)}`;
}

function escapeHtml(s) {
  const div = document.createElement("div");
  div.textContent = String(s);
  return div.innerHTML;
}

function hhmm(iso) {
  try {
    return new Date(iso).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "";
  }
}

function satelliteUrl(lat, lon) {
  const d = 0.0016;
  const la = Number(lat);
  const lo = Number(lon);
  if (isNaN(la) || isNaN(lo)) return null;
  const bbox = `${lo - d},${la - d},${lo + d},${la + d}`;
  return (
    "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/export" +
    `?bbox=${bbox}&bboxSR=4326&imageSR=4326&size=672,400&format=jpg&f=image`
  );
}

function satelliteImage(lat, lon) {
  const url = satelliteUrl(lat, lon);
  if (!url) return "";
  return (
    '<div class="map-wrap">' +
    `<img class="map-thumb" src="${url}" alt="Vista de satélite do endereço" loading="lazy" ` +
    `data-full="${url}" ` +
    "onerror=\"this.closest('.map-wrap').style.display='none'\"/>" +
    '<span class="map-tag">vista de satélite (clique para ampliar)</span>' +
    "</div>"
  );
}

function convBlock(c) {
  return (
    '<div class="detail-section"><h3>Conversa</h3>' +
    row("Estado", c.current_state) +
    row("Canal", c.channel) +
    row("Status", c.status) +
    row("Atendimento humano", c.assigned_to_human
      ? '<span class="badge review">sim</span>'
      : '<span class="badge ok">não</span>') +
    "</div>"
  );
}

function leadBlock(lead) {
  if (!lead) return '<div class="detail-section"><h3>Dados do lead</h3><span class="muted">Nenhum lead.</span></div>';
  const scoreLine =
    lead.lead_score !== null && lead.lead_score !== undefined
      ? `<div class="row"><span class="label">Score / Temperatura</span><span class="value">${lead.lead_score} ${tempBadge(lead.lead_temperature)}</span></div>`
      : "";
  return (
    '<div class="detail-section"><h3>Dados do lead</h3>' +
    row("Nome", lead.name ? escapeHtml(lead.name) : null) +
    row("Cidade", lead.city ? escapeHtml(lead.city) : null) +
    row("Endereço", lead.address ? escapeHtml(lead.address) : null) +
    row("Tipo de imóvel", lead.property_type) +
    row("Conta média", money(lead.average_energy_bill)) +
    row("Intenção", lead.intent) +
    scoreLine +
    row("Status do lead", lead.status) +
    "</div>"
  );
}

function solarBlock(geo) {
  if (!geo) return '<div class="detail-section"><h3>Análise solar</h3><span class="muted">Não realizada.</span></div>';
  let html = '<div class="detail-section"><h3>Análise solar</h3>';
  if (geo.latitude && geo.longitude) html += satelliteImage(geo.latitude, geo.longitude);
  html +=
    row("Endereço", geo.formatted_address ? escapeHtml(geo.formatted_address) : null) +
    row("Confiança do endereço", geo.address_confidence) +
    row("Coordenadas", geo.latitude && geo.longitude ? `${geo.latitude}, ${geo.longitude}` : null);
  if (geo.solar_data_available) {
    const panels =
      geo.estimated_panel_min !== null && geo.estimated_panel_max !== null
        ? `${geo.estimated_panel_min}–${geo.estimated_panel_max} placas`
        : null;
    html +=
      row("Placas estimadas", panels) +
      row("Sistema (kWp)", geo.estimated_system_kwp) +
      row("Confiança", geo.confidence_level) +
      row("Revisão técnica", geo.requires_technical_review
        ? '<span class="badge review">necessária</span>'
        : '<span class="badge ok">não</span>');
  } else {
    html += '<div class="muted">Geocodificado, mas sem dados solares.</div>';
  }
  return html + "</div>";
}

function transcriptBlock(messages) {
  const visible = (messages || []).filter((m) => m.role === "user" || m.role === "assistant");
  if (!visible.length) {
    return '<div class="detail-section"><h3>Conversa (transcrição)</h3><span class="muted">Sem mensagens.</span></div>';
  }
  const bubbles = visible
    .map(
      (m) =>
        `<div class="msg ${m.role === "user" ? "user" : "assistant"}">` +
        `<span class="msg-text">${escapeHtml(m.content)}</span>` +
        `<span class="msg-time">${m.role === "user" ? "Cliente" : "IA"} · ${hhmm(m.created_at)}</span>` +
        "</div>"
    )
    .join("");
  return `<div class="detail-section"><h3>Conversa (transcrição)</h3><div class="transcript">${bubbles}</div></div>`;
}

export function renderDetail(container, detail) {
  container.innerHTML =
    convBlock(detail.conversation) +
    leadBlock(detail.lead) +
    solarBlock(detail.geospatial) +
    transcriptBlock(detail.messages);

  container.querySelectorAll(".map-thumb").forEach((img) =>
    img.addEventListener("click", () => openLightbox(img.getAttribute("data-full")))
  );
}

function openLightbox(url) {
  const box = document.getElementById("lightbox");
  const img = document.getElementById("lightbox-img");
  if (!box || !img || !url) return;
  img.src = url;
  box.classList.remove("hidden");
}

function closeLightbox() {
  const box = document.getElementById("lightbox");
  if (box) box.classList.add("hidden");
}

(function initLightbox() {
  const box = document.getElementById("lightbox");
  const close = document.getElementById("lightbox-close");
  if (close) close.addEventListener("click", closeLightbox);
  if (box) box.addEventListener("click", (e) => { if (e.target === box) closeLightbox(); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeLightbox(); });
})();
