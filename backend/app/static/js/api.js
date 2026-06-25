"use strict";

export async function postChat({ message, conversationId }) {
  const res = await fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, conversation_id: conversationId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function getConversation(id) {
  try {
    const res = await fetch(`/conversations/${id}`);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}
