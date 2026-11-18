import httpx
import pytest

from market_intel.tools.slack import (
    SlackConfigurationError,
    SlackDeliveryError,
    SlackWebhookClient,
)


def test_slack_sends_message():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, text="ok")

    http_client = httpx.Client(transport=httpx.MockTransport(handler))

    client = SlackWebhookClient(
        "https://hooks.slack.com/services/test",
        http_client=http_client,
    )

    client.send_message("Test report")

    assert len(requests) == 1
    assert requests[0].method == "POST"
    assert requests[0].read() == b'{"text":"Test report"}'

    http_client.close()


def test_slack_rejects_empty_message():
    http_client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, text="ok"))
    )

    client = SlackWebhookClient(
        "https://hooks.slack.com/services/test",
        http_client=http_client,
    )

    with pytest.raises(SlackDeliveryError, match="empty"):
        client.send_message("")

    http_client.close()


def test_slack_rejects_invalid_webhook_url():
    with pytest.raises(SlackConfigurationError, match="cannot be empty"):
        SlackWebhookClient("")


def test_slack_handles_http_failure():
    http_client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(500, text="Internal Server Error")
        )
    )

    client = SlackWebhookClient(
        "https://hooks.slack.com/services/test",
        http_client=http_client,
    )

    with pytest.raises(SlackDeliveryError, match="HTTP request failed"):
        client.send_message("Test report")

    http_client.close()


def test_slack_rejects_unexpected_response():
    http_client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, text="not-ok"))
    )

    client = SlackWebhookClient(
        "https://hooks.slack.com/services/test",
        http_client=http_client,
    )

    with pytest.raises(SlackDeliveryError, match="unexpected response"):
        client.send_message("Test report")

    http_client.close()


def test_slack_closes_owned_http_client():
    client = SlackWebhookClient("https://hooks.slack.com/services/test")

    http_client = client._client
    client.close()

    assert http_client.is_closed


def test_slack_does_not_close_injected_http_client():
    http_client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, text="ok"))
    )

    client = SlackWebhookClient(
        "https://hooks.slack.com/services/test",
        http_client=http_client,
    )

    client.close()

    assert not http_client.is_closed

    http_client.close()
