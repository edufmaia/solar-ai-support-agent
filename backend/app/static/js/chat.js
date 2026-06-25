"use strict";

import { postChat } from "./api.js";
import { loadBranding } from "./branding.js";

const STORAGE_KEY = "solar_ai_conversation_id";
const state = {
  conversationId: localStorage.getItem(STORAGE_KEY),
  sending: false,
};

const els = {
  messages: document.getElementById("messages"),
  form: document.getElementById("chat-form"),
  input: document.getElementById("message-input"),
  sendBtn: document.getElementById("send-btn"),
  newConv: document.getElementById("new-conversation"),
  brandLogo: document.getElementById("brand-logo"),
  brandName: document.getElementById("brand-name"),
  brandSubtitle: document.getElementById("brand-subtitle"),
  footer: document.getElementById("chat-footer"),
};

let branding = null;

function addBubble(text, role) {
  const div = document.createElement("div");
  div.className = `bubble ${role}`;
  div.textContent = text;
  els.messages.appendChild(div);
  els.messages.scrollTop = els.messages.scrollHeight;
  return div;
}

function applyBranding(cfg) {
  document.title = cfg.brand_name;
  els.brandName.textContent = cfg.brand_name;
  els.brandSubtitle.textContent = cfg.subtitle || "";
  els.input.placeholder = cfg.input_placeholder;
  if (cfg.logo_url) {
    const img = document.createElement("img");
    img.src = cfg.logo_url;
    img.alt = cfg.brand_name;
    img.className = "brand-logo-img";
    els.brandLogo.replaceWith(img);
  }
  if (cfg.show_powered_by) {
    els.footer.textContent = `Powered by ${cfg.brand_name}`;
    els.footer.classList.remove("hidden");
  }
}

function showWelcome() {
  els.messages.innerHTML = "";
  addBubble(branding.welcome_message, "agent");
}

async function send(message) {
  if (state.sending) return;
  state.sending = true;
  els.sendBtn.disabled = true;
  addBubble(message, "user");
  const typing = addBubble("digitando…", "agent");
  typing.classList.add("typing");
  try {
    const data = await postChat({ message, conversationId: state.conversationId });
    state.conversationId = data.conversation_id;
    localStorage.setItem(STORAGE_KEY, data.conversation_id);
    typing.classList.remove("typing");
    typing.textContent = data.response;
  } catch (e) {
    typing.classList.remove("typing");
    typing.classList.add("error");
    typing.textContent = `⚠️ Não consegui responder agora. Tente novamente. (${e.message})`;
  } finally {
    state.sending = false;
    els.sendBtn.disabled = false;
    els.input.focus();
  }
}

function resetConversation() {
  state.conversationId = null;
  localStorage.removeItem(STORAGE_KEY);
  showWelcome();
  els.input.focus();
}

els.form.addEventListener("submit", (e) => {
  e.preventDefault();
  const msg = els.input.value.trim();
  if (!msg) return;
  els.input.value = "";
  send(msg);
});
els.newConv.addEventListener("click", resetConversation);

(async () => {
  branding = await loadBranding();
  applyBranding(branding);
  showWelcome();
  els.input.focus();
})();
