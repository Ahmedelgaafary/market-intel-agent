"""Slack incoming-webhook integration."""

from types import TracebackType
from typing import Self

import httpx


class SlackDeliveryError(Exception):
    """Raised when Slack message delivery fails."""


class SlackConfigurationError(SlackDeliveryError):
    """Raised when Slack is not configured correctly."""


class SlackWebhookClient:
    """Send messages through a Slack incoming webhook."""

    def __init__(
        self,
        webhook_url: str,
        timeout: float = 10.0,
        http_client: httpx.Client | None = None,
    ) -> None:
        if not webhook_url.strip():
            raise SlackConfigurationError("Slack webhook URL cannot be empty.")

        self.webhook_url = webhook_url
        self._owns_client = http_client is None
        self._client = http_client or httpx.Client(timeout=timeout)

    def send_message(self, message: str) -> None:
        """Send a message and raise an error if Slack rejects it."""

        if not message.strip():
            raise SlackDeliveryError("Cannot send an empty Slack message.")

        try:
            response = self._client.post(
                self.webhook_url,
                json={"text": message},
            )
            response.raise_for_status()

            if response.text.strip().lower() != "ok":
                raise SlackDeliveryError(
                    f"Slack returned an unexpected response: {response.text[:200]}"
                )

        except SlackDeliveryError:
            raise
        except httpx.HTTPError as exc:
            raise SlackDeliveryError(f"Slack HTTP request failed: {exc}") from exc

    def close(self) -> None:
        """Close the internally created HTTP client."""

        if self._owns_client:
            self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()
