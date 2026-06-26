"use strict";

import { loadBranding } from "./branding.js";
import { renderDetail, money } from "./admin-detail.js";

const TOKEN_KEY = "solar-admin-token";
let token = localStorage.getItem(TOKEN_KEY) || null;

const els = {
  login: document.getElementById("login-view"),
  loginForm: document.getElementById("login-form"),
  password: document.getElementById("password"),
  loginError: document.getElementById("login-error"),
  panel: document.getElementById("panel-view"),
  brandName: document.getElementById("brand-name"),
  tabDash: document.getElementById("tab-dashboard"),
  tabConv: document.getElementById("tab-conversations"),
  logout: document.getElementById("logout-btn"),
  dashPane: document.getElementById("dashboard-pane"),
  convPane: document.getElementById("conversations-pane"),
  detailPane: document.getElementById("detail-pane"),
  cards: document.getElementById("metrics-cards"),
  rows: document.getElementById("conv-rows"),
  convEmpty: document.getElementById("conv-empty"),
  detailBack: document.getElementById("detail-back"),
  detailContent: document.getElementById("detail-content"),
};

async function api(path) {
  const res = await fetch(path, { headers: { Authorization: `Bearer ${token}` } });
  if (res.status === 401) {
    showLogin();
    throw new Error("unauthorized");
  }
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

function showLogin() {
  token = null;
  localStorage.removeItem(TOKEN_KEY);
  els.panel.classList.add("hidden");
  els.login.classList.remove("hidden");
}

function showPanel() {
  els.login.classList.add("hidden");
  els.panel.classList.remove("hidden");
  selectTab("dashboard");
}

function selectTab(name) {
  const dash = name === "dashboard";
  els.tabDash.classList.toggle("active", dash);
  els.tabConv.classList.toggle("active", !dash);
  els.dashPane.classList.toggle("hidden", !dash);
  els.convPane.classList.toggle("hidden", dash);
  els.detailPane.classList.add("hidden");
  if (dash) loadDashboard();
  else loadConversations();
}

function card(title, big, sub) {
  return `<div class="card"><h3>${title}</h3><div class="big">${big}</div>${
    sub ? `<div class="sub">${sub}</div>` : ""
  }</div>`;
}

async function loadDashboard() {
  try {
    const m = await api("/admin/metrics");
    const byTemp = m.leads.by_temperature || {};
    const tempSub = ["hot", "warm", "cold"]
      .map((t) => `${t}: ${byTemp[t] || 0}`)
      .join(" · ");
    const conv = m.conversations || {};
    const pctHuman = conv.total ? Math.round((100 * conv.assigned_to_human) / conv.total) : 0;
    const usage = m.usage || {};
    const topEvent = (m.events || [])[0];
    els.cards.innerHTML =
      card("Leads", m.leads.total, tempSub) +
      card("Conversas", conv.total, `${conv.assigned_to_human} com humano (${pctHuman}%)`) +
      card("Custo LLM (US$)", "US$ " + Number(usage.total_estimated_cost || 0).toFixed(4),
        `${usage.total_input_tokens || 0} in / ${usage.total_output_tokens || 0} out`) +
      card("Evento mais comum", topEvent ? topEvent.event_type : "—",
        topEvent ? `${topEvent.count}×` : "");
  } catch (e) {
    if (e.message !== "unauthorized") els.cards.innerHTML = `<p class="muted">Erro: ${e.message}</p>`;
  }
}

function tempBadge(t) {
  if (!t) return '<span class="badge neutral">—</span>';
  return `<span class="badge ${["hot", "warm", "cold"].includes(t) ? t : "neutral"}">${t}</span>`;
}

async function loadConversations() {
  try {
    const data = await api("/admin/conversations?limit=100&offset=0");
    els.convEmpty.classList.toggle("hidden", data.items.length > 0);
    els.rows.innerHTML = data.items
      .map((it) => `
        <tr data-id="${it.conversation_id}">
          <td>${escapeHtml(it.lead_name || "—")}</td>
          <td>${escapeHtml(it.lead_city || "—")}</td>
          <td>${money(it.average_energy_bill) || "—"}</td>
          <td>${it.lead_score ?? "—"} ${tempBadge(it.lead_temperature)}</td>
          <td>${escapeHtml(it.channel || "—")}</td>
          <td>${formatDate(it.started_at)}</td>
          <td>${it.assigned_to_human ? '<span class="badge review">sim</span>' : '<span class="badge ok">não</span>'}</td>
        </tr>`)
      .join("");
    els.rows.querySelectorAll("tr[data-id]").forEach((tr) =>
      tr.addEventListener("click", () => openDetail(tr.getAttribute("data-id")))
    );
  } catch (e) {
    if (e.message !== "unauthorized") els.rows.innerHTML = `<tr><td colspan="7">Erro: ${e.message}</td></tr>`;
  }
}

async function openDetail(id) {
  try {
    const detail = await api(`/admin/conversations/${id}`);
    renderDetail(els.detailContent, detail);
    els.convPane.classList.add("hidden");
    els.dashPane.classList.add("hidden");
    els.detailPane.classList.remove("hidden");
  } catch (e) {
    if (e.message !== "unauthorized") alert(`Erro: ${e.message}`);
  }
}

function escapeHtml(s) {
  const div = document.createElement("div");
  div.textContent = String(s);
  return div.innerHTML;
}

function formatDate(iso) {
  try {
    return new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
  } catch {
    return iso;
  }
}

els.loginForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  els.loginError.classList.add("hidden");
  try {
    const res = await fetch("/admin/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: els.password.value }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      els.loginError.textContent =
        res.status === 503 ? "Login não configurado no servidor." : (err.detail || "Senha inválida.");
      els.loginError.classList.remove("hidden");
      return;
    }
    token = (await res.json()).token;
    localStorage.setItem(TOKEN_KEY, token);
    els.password.value = "";
    showPanel();
  } catch {
    els.loginError.textContent = "Erro de conexão.";
    els.loginError.classList.remove("hidden");
  }
});

els.logout.addEventListener("click", async () => {
  try {
    await fetch("/admin/logout", { method: "POST", headers: { Authorization: `Bearer ${token}` } });
  } catch {
    /* best-effort */
  }
  showLogin();
});

els.tabDash.addEventListener("click", () => selectTab("dashboard"));
els.tabConv.addEventListener("click", () => selectTab("conversations"));
els.detailBack.addEventListener("click", () => selectTab("conversations"));

(async function init() {
  const cfg = await loadBranding();
  els.brandName.textContent = cfg.brand_name;
  if (token) showPanel();
  else showLogin();
})();
