from unittest.mock import MagicMock, patch

import pytest

from katteb.client import KattebAuthError, KattebClient, KattebRateLimitError


@pytest.fixture
def client():
    return KattebClient(api_key="mock_key_abc123")


def test_client_headers(client):
    headers = client._headers()
    assert headers["Authorization"] == "Bearer mock_key_abc123"
    assert headers["Content-Type"] == "application/json"


def test_get_credits_mock(client):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "success": True,
        "credits": 25000,
        "credits_total": 50000,
        "plan_type": "pro",
    }

    with patch.object(client.session, "request", return_value=mock_resp) as mock_req:
        res = client.get_credits()
        mock_req.assert_called_once()
        args, kwargs = mock_req.call_args
        assert kwargs["params"] == {"endpoint": "account/credits"}
        assert res.credits == 25000


def test_generate_article_mock(client):
    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.json.return_value = {
        "success": True,
        "job_id": 9999,
        "topic": "Tokyo Travel",
        "credits_charged": 1605,
        "status": "pending",
    }

    with patch.object(client.session, "request", return_value=mock_resp):
        res = client.generate_article(
            topic="Tokyo Travel",
            language="English",
            country="jp",
            word_count=1500,
        )
        assert res.job_id == 9999
        assert res.status == "pending"


def test_auth_error_401(client):
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.json.return_value = {"success": False, "error": "Invalid API key"}

    with (
        patch.object(client.session, "request", return_value=mock_resp),
        pytest.raises(KattebAuthError, match="Invalid API key"),
    ):
        client.get_credits()


def test_rate_limit_429_with_active_job(client):
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.json.return_value = {
        "success": False,
        "error": "You have an article being generated",
        "retry_after": 120,
        "active_job_id": 4444,
        "active_job_type": "article",
    }

    with patch.object(client.session, "request", return_value=mock_resp):
        with pytest.raises(KattebRateLimitError) as exc:
            client.generate_article(topic="Busy Topic")
        assert exc.value.active_job_id == 4444
        assert exc.value.retry_after == 120
