"use strict";

const state = { conversationId: null, sending: false };

const els = {
  messages: document.getElementById("messages"),
  form: document.getElementById("chat-form"),
  input: document.getElementById("message-input"),
  sendBtn: document.getElementById("send-btn"),
  modeBadge: document.getElementById("mode-badge"),
  newConv: document.getElementById("new-conversation"),
  handoffBanner: document.getElementById("handoff-banner"),
  convInfo: document.getElementById("conv-info"),
  leadInfo: document.getElementById("lead-info"),
  solarInfo: document.getElementById("solar-info"),
  eventsList: document.getElementById("events-list"),
};

const HIGHLIGHT_EVENTS = new Set([
  "human_handoff_requested",
  "solar_potential_completed",
  "lead_score_updated",
  "geospatial_analysis_completed",
]);

function addBubble(text, role) {
  const hint = els.messages.querySelector(".empty-hint");
  if (hint) hint.remove();
  const div = document.createElement("div");
  div.className = `bubble ${role}`;
  div.textContent = text;
  els.messages.appendChild(div);
  els.messages.scrollTop = els.messages.scrollHeight;
  return div;
}

function row(label, value) {
  if (value === null || value === undefined || value === "") return "";
  return `<div class="row"><span class="label">${label}</span><span class="value">${value}</span></div>`;
}

function tempBadge(temp) {
  if (!temp) return '<span class="badge neutral">—</span>';
  const cls = ["hot", "warm", "cold"].includes(temp) ? temp : "neutral";
  return `<span class="badge ${cls}">${temp}</span>`;
}

function money(v) {
  if (v === null || v === undefined) return null;
  const n = Number(v);
  return isNaN(n) ? v : `R$ ${n.toFixed(2)}`;
}

async function sendMessage(message) {
  if (state.sending) return;
  state.sending = true;
  els.sendBtn.disabled = true;
  addBubble(message, "user");
  const typing = addBubble("digitando…", "agent");
  typing.classList.add("typing");

  try {
    const res = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, conversation_id: state.conversationId }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    const data = await res.json();
    state.conversationId = data.conversation_id;
    els.modeBadge.textContent = `modo: ${data.mode}`;
    typing.classList.remove("typing");
    typing.textContent = data.response;
    await refreshInspector();
  } catch (e) {
    typing.classList.remove("typing");
    typing.textContent = `⚠️ Erro: ${e.message}`;
  } finally {
    state.sending = false;
    els.sendBtn.disabled = false;
    els.input.focus();
  }
}

async function refreshInspector() {
  if (!state.conversationId) return;
  let detail;
  try {
    const res = await fetch(`/conversations/${state.conversationId}`);
    if (!res.ok) return;
    detail = await res.json();
  } catch {
    return;
  }
  renderConversation(detail.conversation);
  renderLead(detail.lead);
  renderSolar(detail.geospatial);
  renderEvents(detail.events);
}

function renderConversation(c) {
  els.handoffBanner.classList.toggle("hidden", !c.assigned_to_human);
  els.convInfo.innerHTML =
    row("Estado", c.current_state) +
    row("Canal", c.channel) +
    row("Status", c.status) +
    row("Atendimento humano", c.assigned_to_human
      ? '<span class="badge review">sim</span>'
      : '<span class="badge ok">não</span>');
}

function renderLead(lead) {
  if (!lead) {
    els.leadInfo.innerHTML = '<span class="muted">Nenhum lead identificado ainda.</span>';
    return;
  }
  const scoreLine =
    (lead.lead_score !== null && lead.lead_score !== undefined)
      ? `<div class="row"><span class="label">Score / Temperatura</span><span class="value">${lead.lead_score} ${tempBadge(lead.lead_temperature)}</span></div>`
      : "";
  els.leadInfo.innerHTML =
    row("Nome", lead.name) +
    row("Cidade", lead.city) +
    row("Endereço", lead.address) +
    row("Tipo de imóvel", lead.property_type) +
    row("Conta média", money(lead.average_energy_bill)) +
    row("Intenção", lead.intent) +
    scoreLine +
    row("Status do lead", lead.status) ||
    '<span class="muted">—</span>';
}

function renderSolar(geo) {
  if (!geo) {
    els.solarInfo.innerHTML = '<span class="muted">Ainda não realizada. Autorize a análise e informe o endereço.</span>';
    return;
  }
  let html =
    row("Endereço", geo.formatted_address) +
    row("Confiança do endereço", geo.address_confidence) +
    row("Coordenadas",
      (geo.latitude && geo.longitude) ? `${geo.latitude}, ${geo.longitude}` : null);

  if (geo.solar_data_available) {
    const panels =
      (geo.estimated_panel_min !== null && geo.estimated_panel_max !== null)
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
    html += '<div class="muted">Geocodificado, mas sem dados solares disponíveis.</div>';
  }
  els.solarInfo.innerHTML = html || '<span class="muted">—</span>';
}

function renderEvents(events) {
  if (!events || !events.length) {
    els.eventsList.innerHTML = '<li class="muted">—</li>';
    return;
  }
  els.eventsList.innerHTML = events
    .map((e) => {
      const hl = HIGHLIGHT_EVENTS.has(e.event_type) ? " hl" : "";
      return `<li class="${hl.trim()}">${e.event_type}</li>`;
    })
    .join("");
}

function resetConversation() {
  state.conversationId = null;
  els.messages.innerHTML =
    '<div class="empty-hint">Nova conversa iniciada. Escreva uma mensagem para começar.</div>';
  els.modeBadge.textContent = "modo: —";
  els.handoffBanner.classList.add("hidden");
  els.convInfo.innerHTML = '<span class="muted">Sem conversa ainda.</span>';
  els.leadInfo.innerHTML = '<span class="muted">—</span>';
  els.solarInfo.innerHTML = '<span class="muted">Ainda não realizada.</span>';
  els.eventsList.innerHTML = '<li class="muted">—</li>';
  els.input.focus();
}

els.form.addEventListener("submit", (e) => {
  e.preventDefault();
  const msg = els.input.value.trim();
  if (!msg) return;
  els.input.value = "";
  sendMessage(msg);
});

els.newConv.addEventListener("click", resetConversation);
els.input.focus();
