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
  tabInstr: document.getElementById("tab-instructions"),
  tabKnow: document.getElementById("tab-knowledge"),
  logout: document.getElementById("logout-btn"),
  dashPane: document.getElementById("dashboard-pane"),
  convPane: document.getElementById("conversations-pane"),
  instrPane: document.getElementById("instructions-pane"),
  knowPane: document.getElementById("knowledge-pane"),
  detailPane: document.getElementById("detail-pane"),
  cards: document.getElementById("metrics-cards"),
  rows: document.getElementById("conv-rows"),
  convEmpty: document.getElementById("conv-empty"),
  detailBack: document.getElementById("detail-back"),
  detailContent: document.getElementById("detail-content"),
  promptEditor: document.getElementById("prompt-editor"),
  promptCount: document.getElementById("prompt-count"),
  promptOrigin: document.getElementById("prompt-origin"),
  knowledgeEnabled: document.getElementById("knowledge-enabled"),
  promptSave: document.getElementById("prompt-save"),
  promptReset: document.getElementById("prompt-reset"),
  promptStatus: document.getElementById("prompt-status"),
  kbForm: document.getElementById("kb-form"),
  kbTitle: document.getElementById("kb-title"),
  kbCategory: document.getElementById("kb-category"),
  kbFile: document.getElementById("kb-file"),
  kbText: document.getElementById("kb-text"),
  kbStatus: document.getElementById("kb-status"),
  kbRows: document.getElementById("kb-rows"),
  kbEmpty: document.getElementById("kb-empty"),
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

async function apiSend(path, method, body, isForm) {
  const headers = { Authorization: `Bearer ${token}` };
  let payload = body;
  if (body !== undefined && !isForm) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }
  const res = await fetch(path, { method, headers, body: payload });
  if (res.status === 401) {
    showLogin();
    throw new Error("unauthorized");
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.status === 204 ? null : res.json();
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
  const tabs = {
    dashboard: [els.tabDash, els.dashPane, loadDashboard],
    conversations: [els.tabConv, els.convPane, loadConversations],
    instructions: [els.tabInstr, els.instrPane, loadInstructions],
    knowledge: [els.tabKnow, els.knowPane, loadKnowledge],
  };
  els.detailPane.classList.add("hidden");
  for (const [key, [tab, pane]] of Object.entries(tabs)) {
    tab.classList.toggle("active", key === name);
    pane.classList.toggle("hidden", key !== name);
  }
  const loader = tabs[name] && tabs[name][2];
  if (loader) loader();
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

async function loadInstructions() {
  els.promptStatus.textContent = "";
  try {
    const s = await api("/admin/agent-settings");
    els.promptEditor.value = s.system_prompt;
    els.promptCount.textContent = String(s.system_prompt.length);
    els.promptOrigin.textContent = s.is_custom ? "instruções personalizadas" : "padrão";
    els.knowledgeEnabled.checked = s.knowledge_enabled;
  } catch (e) {
    if (e.message !== "unauthorized") els.promptStatus.textContent = `Erro: ${e.message}`;
  }
}

async function saveInstructions() {
  els.promptStatus.textContent = "Salvando…";
  try {
    await apiSend("/admin/agent-settings", "PUT", {
      system_prompt: els.promptEditor.value,
      knowledge_enabled: els.knowledgeEnabled.checked,
    });
    els.promptStatus.textContent = "Salvo.";
    loadInstructions();
  } catch (e) {
    if (e.message !== "unauthorized") els.promptStatus.textContent = `Erro: ${e.message}`;
  }
}

async function resetInstructions() {
  if (!confirm("Restaurar as instruções padrão? As personalizadas serão descartadas.")) return;
  els.promptStatus.textContent = "Restaurando…";
  try {
    await apiSend("/admin/agent-settings/reset", "POST");
    els.promptStatus.textContent = "Restaurado para o padrão.";
    loadInstructions();
  } catch (e) {
    if (e.message !== "unauthorized") els.promptStatus.textContent = `Erro: ${e.message}`;
  }
}

async function loadKnowledge() {
  els.kbStatus.textContent = "";
  try {
    const groups = await api("/admin/knowledge");
    els.kbEmpty.classList.toggle("hidden", groups.length > 0);
    els.kbRows.innerHTML = "";
    for (const g of groups) {
      const tr = document.createElement("tr");
      tr.innerHTML =
        `<td>${escapeHtml(g.source || g.title)}</td>` +
        `<td>${escapeHtml(g.category || "—")}</td>` +
        `<td>${g.chunk_count}</td>` +
        `<td>${g.is_active ? "sim" : "não"}</td>` +
        `<td><button class="btn-ghost" data-act="toggle">${g.is_active ? "Desativar" : "Ativar"}</button>` +
        ` <button class="btn-ghost" data-act="delete">Excluir</button></td>`;
      tr.querySelector('[data-act="toggle"]').addEventListener("click", () =>
        toggleKnowledge(g.document_group_id, !g.is_active)
      );
      tr.querySelector('[data-act="delete"]').addEventListener("click", () =>
        deleteKnowledge(g.document_group_id)
      );
      els.kbRows.appendChild(tr);
    }
  } catch (e) {
    if (e.message !== "unauthorized") els.kbStatus.textContent = `Erro: ${e.message}`;
  }
}

async function uploadKnowledge(e) {
  e.preventDefault();
  els.kbStatus.textContent = "Enviando…";
  const form = new FormData();
  form.append("title", els.kbTitle.value);
  if (els.kbCategory.value) form.append("category", els.kbCategory.value);
  if (els.kbFile.files[0]) form.append("file", els.kbFile.files[0]);
  else form.append("text", els.kbText.value);
  try {
    const r = await apiSend("/admin/knowledge", "POST", form, true);
    els.kbStatus.textContent = `Adicionado: ${r.chunk_count} trecho(s)${r.truncated ? " (truncado)" : ""}.`;
    els.kbForm.reset();
    loadKnowledge();
  } catch (err) {
    if (err.message !== "unauthorized") els.kbStatus.textContent = `Erro: ${err.message}`;
  }
}

async function toggleKnowledge(groupId, active) {
  try {
    await apiSend(`/admin/knowledge/${groupId}?is_active=${active}`, "PATCH");
    loadKnowledge();
  } catch (e) {
    if (e.message !== "unauthorized") els.kbStatus.textContent = `Erro: ${e.message}`;
  }
}

async function deleteKnowledge(groupId) {
  if (!confirm("Excluir este documento da base de conhecimento?")) return;
  try {
    await apiSend(`/admin/knowledge/${groupId}`, "DELETE");
    loadKnowledge();
  } catch (e) {
    if (e.message !== "unauthorized") els.kbStatus.textContent = `Erro: ${e.message}`;
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
els.tabInstr.addEventListener("click", () => selectTab("instructions"));
els.tabKnow.addEventListener("click", () => selectTab("knowledge"));
els.detailBack.addEventListener("click", () => selectTab("conversations"));

els.promptEditor.addEventListener("input", () => {
  els.promptCount.textContent = String(els.promptEditor.value.length);
});
els.promptSave.addEventListener("click", saveInstructions);
els.promptReset.addEventListener("click", resetInstructions);
els.kbForm.addEventListener("submit", uploadKnowledge);

(async function init() {
  const cfg = await loadBranding();
  els.brandName.textContent = cfg.brand_name;
  if (token) showPanel();
  else showLogin();
})();
