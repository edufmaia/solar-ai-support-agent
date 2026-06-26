"use strict";

const HIGHLIGHT_EVENTS = new Set([
  "human_handoff_requested",
  "solar_potential_completed",
  "lead_score_updated",
  "geospatial_analysis_completed",
]);

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

function satelliteImage(lat, lon) {
  const d = 0.0016;
  const la = Number(lat);
  const lo = Number(lon);
  if (isNaN(la) || isNaN(lo)) return "";
  const bbox = `${lo - d},${la - d},${lo + d},${la + d}`;
  const url =
    "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/export" +
    `?bbox=${bbox}&bboxSR=4326&imageSR=4326&size=336,200&format=jpg&f=image`;
  return (
    '<div class="map-wrap">' +
    `<img class="map-thumb" src="${url}" alt="Vista de satélite do endereço" loading="lazy" ` +
    "onerror=\"this.closest('.map-wrap').style.display='none'\"/>" +
    '<span class="map-tag">vista de satélite</span>' +
    "</div>"
  );
}

function leadBlock(lead) {
  if (!lead) return '<div class="detail-section"><h3>Lead</h3><span class="muted">Nenhum lead.</span></div>';
  const scoreLine =
    lead.lead_score !== null && lead.lead_score !== undefined
      ? `<div class="row"><span class="label">Score / Temperatura</span><span class="value">${lead.lead_score} ${tempBadge(lead.lead_temperature)}</span></div>`
      : "";
  return (
    '<div class="detail-section"><h3>Lead</h3>' +
    row("Nome", lead.name) +
    row("Cidade", lead.city) +
    row("Endereço", lead.address) +
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
    row("Endereço", geo.formatted_address) +
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

function eventsBlock(events) {
  const items =
    events && events.length
      ? events
          .map((e) => `<li class="${HIGHLIGHT_EVENTS.has(e.event_type) ? "hl" : ""}">${e.event_type}</li>`)
          .join("")
      : '<li class="muted">—</li>';
  return `<div class="detail-section"><h3>Eventos</h3><ul class="events-list">${items}</ul></div>`;
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

export function renderDetail(container, detail) {
  container.innerHTML =
    convBlock(detail.conversation) +
    leadBlock(detail.lead) +
    solarBlock(detail.geospatial) +
    eventsBlock(detail.events);
}
