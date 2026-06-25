"use strict";

export const DEFAULT_BRANDING = {
  brand_name: "Solar AI",
  logo_url: "",
  primary_color: "#f59e0b",
  text_on_primary: "#ffffff",
  subtitle: "Atendimento inteligente",
  welcome_message: "Olá! 👋 Como posso ajudar com energia solar hoje?",
  input_placeholder: "Escreva uma mensagem...",
  show_powered_by: true,
};

export async function loadBranding() {
  let cfg = { ...DEFAULT_BRANDING };
  try {
    const res = await fetch("/ui/branding.json", { cache: "no-store" });
    if (res.ok) {
      const data = await res.json();
      if (data && typeof data === "object") cfg = { ...cfg, ...data };
    }
  } catch {
    /* keep defaults */
  }
  const root = document.documentElement;
  root.style.setProperty("--brand-primary", cfg.primary_color);
  root.style.setProperty("--brand-on-primary", cfg.text_on_primary);
  return cfg;
}
