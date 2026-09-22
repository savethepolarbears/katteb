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


def test_request_retry_on_502_success(client):
    err_resp = MagicMock()
    err_resp.status_code = 502
    err_resp.json.return_value = {"error": "Bad Gateway"}

    ok_resp = MagicMock()
    ok_resp.status_code = 200
    ok_resp.json.return_value = {"success": True, "credits": 1000}

    with patch.object(client.session, "request", side_effect=[err_resp, ok_resp]), \
         patch("time.sleep") as mock_sleep:
        res = client._request("GET", "account/credits", max_retries=2, initial_delay=0.1)
        assert res["credits"] == 1000
        mock_sleep.assert_called_once()


def test_request_retry_exhausted_raises_api_error(client):
    from katteb.client import KattebAPIError

    err_resp = MagicMock()
    err_resp.status_code = 503
    err_resp.json.return_value = {"error": "Service Unavailable"}

    with patch.object(client.session, "request", return_value=err_resp), \
         patch("time.sleep"):
        with pytest.raises(KattebAPIError) as exc:
            client._request("GET", "account/credits", max_retries=2, initial_delay=0.01)
        assert exc.value.status_code == 503


def test_request_retry_on_network_connection_error(client):
    import requests
    from katteb.client import KattebAPIError

    ok_resp = MagicMock()
    ok_resp.status_code = 200
    ok_resp.json.return_value = {"success": True}

    with patch.object(client.session, "request", side_effect=[requests.exceptions.ConnectionError("Connection reset"), ok_resp]), \
         patch("time.sleep"):
        res = client._request("GET", "styles/list", max_retries=2, initial_delay=0.01)
        assert res["success"] is True


def test_auth_error_ip_auth_required(client):
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.json.return_value = {
        "success": False,
        "error": "ip_auth_required",
        "code": "ip_auth_required",
        "portal_url": "https://app.katteb.com/api_access",
    }

    with patch.object(client.session, "request", return_value=mock_resp):
        with pytest.raises(KattebAuthError) as exc:
            client.get_credits()
        assert exc.value.is_ip_auth_error is True
        assert exc.value.portal_url == "https://app.katteb.com/api_access"
        assert "https://app.katteb.com/api_access" in str(exc.value)


def test_post_request_does_not_retry_by_default(client):
    from katteb.client import KattebAPIError

    err_resp = MagicMock()
    err_resp.status_code = 500
    err_resp.json.return_value = {"error": "Internal Server Error"}

    with patch.object(client.session, "request", return_value=err_resp) as mock_req, \
         patch("time.sleep") as mock_sleep:
        with pytest.raises(KattebAPIError):
            client._request("POST", "articles/generate", json_data={"topic": "Test"}, max_retries=3)
        # Should not retry POST requests by default to avoid duplicate paid generation
        assert mock_req.call_count == 1
        mock_sleep.assert_not_called()


def test_retry_after_header_respected(client):
    err_resp = MagicMock()
    err_resp.status_code = 503
    err_resp.headers = {"Retry-After": "5"}
    err_resp.json.return_value = {"error": "Service Unavailable"}

    ok_resp = MagicMock()
    ok_resp.status_code = 200
    ok_resp.headers = {}
    ok_resp.json.return_value = {"success": True}

    delays = []

    def fake_sleep(d):
        delays.append(d)

    client_with_sleeper = KattebClient(api_key="mock_key", sleeper=fake_sleep)

    with patch.object(client_with_sleeper.session, "request", side_effect=[err_resp, ok_resp]):
        res = client_with_sleeper._request("GET", "account/limits", max_retries=2)
        assert res["success"] is True
        assert delays == [5.0]


def test_request_total_timeout_enforced(client):
    from katteb.client import KattebAPIError

    err_resp = MagicMock()
    err_resp.status_code = 502
    err_resp.json.return_value = {"error": "Bad Gateway"}

    with patch.object(client.session, "request", return_value=err_resp), \
         patch("time.sleep"):
        with pytest.raises(KattebAPIError, match="total timeout budget"):
            # Set total_timeout to -1 to trigger immediate timeout
            client._request("GET", "account/limits", total_timeout=-1)


