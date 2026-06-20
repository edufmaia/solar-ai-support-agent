from typing import Any

import httpx

from ...config.settings import Settings, get_settings


class ChatwootError(Exception):
    """Base error for Chatwoot integration."""


class ChatwootConfigurationError(ChatwootError):
    """Raised when the Chatwoot client is missing base URL or token."""


class ChatwootClient:
    def __init__(self, settings: Settings | None = None, client: Any | None = None) -> None:
        self.settings = settings or get_settings()
        self.client = client

    def send_message(self, account_id: int, conversation_id: int, content: str) -> None:
        base_url = self.settings.chatwoot_base_url
        token = self.settings.chatwoot_api_access_token
        if not base_url or not token:
            raise ChatwootConfigurationError(
                "CHATWOOT_BASE_URL and CHATWOOT_API_ACCESS_TOKEN must be set"
            )

        url = (
            f"{base_url.rstrip('/')}/api/v1/accounts/{account_id}"
            f"/conversations/{conversation_id}/messages"
        )
        headers = {"api_access_token": token}
        body = {"content": content, "message_type": "outgoing"}

        try:
            if self.client is not None:
                response = self.client.post(url, json=body, headers=headers)
            else:
                response = httpx.post(
                    url,
                    json=body,
                    headers=headers,
                    timeout=self.settings.chatwoot_timeout_seconds,
                )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ChatwootError(f"Chatwoot send_message failed: {exc}") from exc


def build_chatwoot_client() -> ChatwootClient:
    return ChatwootClient()
