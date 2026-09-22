import logging
import time
from typing import Any

import requests

from katteb.config import get_config
from katteb.models import (
    AccountCreditsResponse,
    AccountLimitsResponse,
    ArticleGenerateRequest,
    ArticleGenerateResponse,
    ArticleGetResponse,
    ArticleListResponse,
    BrandsListResponse,
    FactCheckRequest,
    FactCheckResponse,
    HumanizerDetectRequest,
    HumanizerDetectResponse,
    HumanizerRewriteRequest,
    HumanizerRewriteResponse,
    SEOAnalyzeRequest,
    SEOAnalyzeResponse,
    SEOGetResponse,
    StylesListResponse,
)

logger = logging.getLogger("katteb")


class KattebAPIError(Exception):
    """Base exception for Katteb API errors."""

    def __init__(self, message: str, status_code: int = 0, response_data: dict[str, Any] | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data or {}


class KattebAuthError(KattebAPIError):
    """Raised on 401 Unauthorized or IP authorization errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 401,
        response_data: dict[str, Any] | None = None,
        is_ip_auth_error: bool = False,
        portal_url: str | None = None,
    ):
        super().__init__(message, status_code=status_code, response_data=response_data)
        self.is_ip_auth_error = is_ip_auth_error
        self.portal_url = portal_url



class KattebCreditError(KattebAPIError):
    """Raised on 402 Insufficient Credits."""

    pass


class KattebRateLimitError(KattebAPIError):
    """Raised on 429 Rate Limited or Concurrency Gated."""

    def __init__(
        self,
        message: str,
        retry_after: int = 60,
        active_job_id: int | None = None,
        active_job_type: str | None = None,
    ):
        super().__init__(message, status_code=429)
        self.retry_after = retry_after
        self.active_job_id = active_job_id
        self.active_job_type = active_job_type


class KattebClient:
    """Synchronous Client for interacting with Katteb API v2."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: int = 60,
        session: requests.Session | None = None,
        sleeper: Any = None,
    ):
        self.config = get_config(api_key=api_key, base_url=base_url)
        self.timeout = timeout
        self.session = session or requests.Session()
        self.sleeper = sleeper

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Katteb-CLI-SDK/1.0",
        }

    def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
        initial_delay: float = 1.0,
        retry_unsafe: bool = False,
        total_timeout: float | None = None,
    ) -> dict[str, Any]:
        """Execute HTTP request against Katteb endpoint with backoff retries for idempotent/safe requests."""
        import random
        import time

        request_params = {"endpoint": endpoint}
        if params:
            request_params.update(params)

        url = self.config.base_url
        headers = self._headers()
        last_error: Exception | None = None
        is_idempotent = method.upper() in ("GET", "HEAD", "OPTIONS")
        can_retry = is_idempotent or retry_unsafe
        start_monotonic = time.monotonic()

        for attempt in range(max_retries + 1):
            if total_timeout and (time.monotonic() - start_monotonic) >= total_timeout:
                raise KattebAPIError(f"Request exceeded total timeout budget of {total_timeout}s")

            try:
                resp = self.session.request(
                    method=method.upper(),
                    url=url,
                    params=request_params,
                    json=json_data,
                    headers=headers,
                    timeout=self.timeout,
                )
            except requests.exceptions.RequestException as e:
                last_error = e
                if can_retry and attempt < max_retries:
                    delay = initial_delay * (backoff_factor ** attempt) + random.uniform(0, 0.5)
                    (self.sleeper or time.sleep)(delay)
                    continue
                raise KattebAPIError(f"Network error connecting to Katteb API ({method.upper()} {endpoint}): {e}") from e

            # Parse JSON response
            try:
                data = resp.json()
            except Exception:
                data = {"success": resp.status_code in (200, 201), "error": resp.text}

            # Retry on 5xx server errors for safe/idempotent operations
            if 500 <= resp.status_code < 600:
                last_error = KattebAPIError(
                    data.get("error", f"API server error with HTTP {resp.status_code}"),
                    status_code=resp.status_code,
                    response_data=data,
                )
                if can_retry and attempt < max_retries:
                    # Check Retry-After header
                    retry_header = resp.headers.get("Retry-After")
                    if retry_header:
                        try:
                            delay = min(float(retry_header), 60.0)
                        except ValueError:
                            delay = initial_delay * (backoff_factor ** attempt) + random.uniform(0, 0.5)
                    else:
                        delay = initial_delay * (backoff_factor ** attempt) + random.uniform(0, 0.5)
                    (self.sleeper or time.sleep)(delay)
                    continue
                raise last_error

            # Embedded error status on 200 OK
            if resp.status_code == 200 and data.get("status") == "error":
                raise KattebAPIError(
                    data.get("message") or data.get("error") or "API returned error payload with status: error",
                    status_code=200,
                    response_data=data,
                )

            # Non-retryable specific error codes
            if resp.status_code == 401:
                err_msg = data.get("error", "Unauthorized: Invalid or missing API key")
                err_code = data.get("code") or data.get("error_code")
                is_ip_auth = (
                    err_code == "ip_auth_required"
                    or err_msg == "ip_auth_required"
                    or "ip is not authorized" in str(err_msg).lower()
                    or "ip_auth_required" in str(data).lower()
                )
                portal_url = data.get("portal_url") or "https://app.katteb.com/api_access"
                if is_ip_auth:
                    msg = (
                        f"Katteb API IP authorization required: your public egress IP is not whitelisted.\n"
                        f"Please add your IP to the allowed list in your Katteb dashboard: {portal_url}"
                    )
                else:
                    msg = err_msg

                raise KattebAuthError(
                    msg,
                    status_code=401,
                    response_data=data,
                    is_ip_auth_error=is_ip_auth,
                    portal_url=portal_url if is_ip_auth else None,
                )
            if resp.status_code == 402:
                raise KattebCreditError(
                    data.get("error", "Insufficient credits to complete operation"),
                    status_code=402,
                    response_data=data,
                )
            if resp.status_code == 429:
                retry_after = data.get("retry_after") or resp.headers.get("Retry-After", 60)
                try:
                    retry_after = int(retry_after)
                except ValueError:
                    retry_after = 60
                job_id = data.get("active_job_id")
                job_type = data.get("active_job_type")
                raise KattebRateLimitError(
                    data.get("error", "Rate limit exceeded or heavy operation concurrency blocked"),
                    retry_after=retry_after,
                    active_job_id=job_id,
                    active_job_type=job_type,
                )
            if resp.status_code >= 400:
                raise KattebAPIError(
                    data.get("error", f"API request failed with HTTP {resp.status_code}"),
                    status_code=resp.status_code,
                    response_data=data,
                )

            from typing import cast

            return cast(dict[str, Any], data)

        if last_error:
            raise last_error
        raise KattebAPIError("Request failed after retries.")

    # -------------------------------------------------------------------------
    # Account & Metadata Endpoints
    # -------------------------------------------------------------------------

    def get_credits(self) -> AccountCreditsResponse:
        """Get credit balance and plan details (GET account/credits)."""
        data = self._request("GET", "account/credits")
        return AccountCreditsResponse.model_validate(data)

    def get_limits(self) -> AccountLimitsResponse:
        """Get rate limit status (GET account/limits)."""
        data = self._request("GET", "account/limits")
        return AccountLimitsResponse.model_validate(data)

    def list_styles(self) -> StylesListResponse:
        """List user writing styles (GET styles/list)."""
        data = self._request("GET", "styles/list")
        return StylesListResponse.model_validate(data)

    def list_brands(self) -> BrandsListResponse:
        """List user brands/workspaces (GET brands/list)."""
        data = self._request("GET", "brands/list")
        return BrandsListResponse.model_validate(data)

    # -------------------------------------------------------------------------
    # Article Operations
    # -------------------------------------------------------------------------

    def generate_article(
        self,
        topic: str,
        language: str = "English",
        country: str = "us",
        word_count: int = 1500,
        brand_id: int | None = None,
        writing_style_id: int | None = None,
        guidelines: str | None = None,
        enhancements: list[str] | None = None,
    ) -> ArticleGenerateResponse:
        """Queue an article generation job (POST articles/generate)."""
        req = ArticleGenerateRequest(
            topic=topic,
            language=language,
            country=country,
            word_count=word_count,
            brand_id=brand_id,
            writing_style_id=writing_style_id,
            guidelines=guidelines,
            enhancements=enhancements,
        )
        data = self._request("POST", "articles/generate", json_data=req.model_dump(exclude_none=True))
        return ArticleGenerateResponse.model_validate(data)

    def get_article(self, job_id: int) -> ArticleGetResponse:
        """Get article status and content (GET articles/get&id=<job_id>)."""
        data = self._request("GET", "articles/get", params={"id": job_id})
        return ArticleGetResponse.model_validate(data)

    def list_articles(
        self,
        page: int = 1,
        limit: int = 20,
        status: str | None = None,
    ) -> ArticleListResponse:
        """List past generated articles (GET articles/list)."""
        params: dict[str, Any] = {"page": page, "limit": limit}
        if status:
            params["status"] = status
        data = self._request("GET", "articles/list", params=params)
        return ArticleListResponse.model_validate(data)

    def cancel_article(self, job_id: int) -> dict[str, Any]:
        """Cancel a pending article and refund credits (DELETE articles/cancel&id=<job_id>)."""
        from typing import cast

        return cast(dict[str, Any], self._request("DELETE", "articles/cancel", params={"id": job_id}))

    def poll_article_until_complete(
        self,
        job_id: int,
        interval_seconds: int = 10,
        timeout_seconds: int = 600,
        on_progress: Any | None = None,
    ) -> ArticleGetResponse:
        """Poll articles/get until status is 'completed' or 'failed'."""
        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            res = self.get_article(job_id)
            if on_progress:
                on_progress(res)
            if res.status == "completed":
                return res
            if res.status in ("failed", "cancelled"):
                raise KattebAPIError(f"Article generation {res.status}: {res.error_detail or res.error}")
            time.sleep(interval_seconds)

        raise KattebAPIError(f"Article generation timed out after {timeout_seconds}s (Job #{job_id})")

    # -------------------------------------------------------------------------
    # SEO Analysis
    # -------------------------------------------------------------------------

    def analyze_seo(
        self,
        type: str,
        value: str,
        keyword: str | None = None,
        brand_id: int | None = None,
    ) -> SEOAnalyzeResponse:
        """Submit URL or text for SEO analysis (POST seo/analyze)."""
        req = SEOAnalyzeRequest(type=type, value=value, keyword=keyword, brand_id=brand_id)  # type: ignore
        data = self._request("POST", "seo/analyze", json_data=req.model_dump(exclude_none=True))
        return SEOAnalyzeResponse.model_validate(data)

    def get_seo(self, job_id: int) -> SEOGetResponse:
        """Get SEO analysis results (GET seo/get&id=<job_id>)."""
        data = self._request("GET", "seo/get", params={"id": job_id})
        return SEOGetResponse.model_validate(data)

    # -------------------------------------------------------------------------
    # Humanizer & Fact-Checking Tools
    # -------------------------------------------------------------------------

    def detect_ai(self, text: str, language: str = "English") -> HumanizerDetectResponse:
        """Detect AI-written probability (POST humanizer/detect)."""
        req = HumanizerDetectRequest(text=text, language=language)
        data = self._request("POST", "humanizer/detect", json_data=req.model_dump(exclude_none=True))
        return HumanizerDetectResponse.model_validate(data)

    def rewrite_humanizer(
        self,
        text: str,
        strength: str = "Moderate",
        language: str = "English",
        add_imperfections: bool = False,
        brand_id: int | None = None,
    ) -> HumanizerRewriteResponse:
        """Humanize AI text (POST humanizer/rewrite)."""
        req = HumanizerRewriteRequest(
            text=text,
            strength=strength,  # type: ignore
            language=language,
            add_imperfections=add_imperfections,
            brand_id=brand_id,
        )
        data = self._request("POST", "humanizer/rewrite", json_data=req.model_dump(exclude_none=True))
        return HumanizerRewriteResponse.model_validate(data)

    def verify_fact(self, text: str, brand_id: int | None = None) -> FactCheckResponse:
        """Verify claim with web search (POST factcheck/verify)."""
        req = FactCheckRequest(text=text, brand_id=brand_id)
        data = self._request("POST", "factcheck/verify", json_data=req.model_dump(exclude_none=True))
        return FactCheckResponse.model_validate(data)
