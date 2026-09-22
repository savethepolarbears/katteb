"""Pydantic schemas and data models for Katteb API v2."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class KattebErrorResponse(BaseModel):
    """Standard error response structure."""

    success: bool = False
    error: str = "Unknown error"
    retry_after: int | None = None
    active_job_id: int | None = None
    active_job_type: str | None = None


class ArticleGenerateRequest(BaseModel):
    """Payload for POST articles/generate."""

    topic: str = Field(..., max_length=500, description="Article topic (max 500 chars)")
    language: str = Field(default="English", description="Language name, e.g. 'English', 'Arabic', 'French'")
    country: str = Field(default="us", max_length=2, description="ISO 3166-1 alpha-2 code (gl parameter)")
    word_count: int = Field(default=1500, ge=500, le=5000, description="500-5000 words. Default: 1500")
    brand_id: int | None = Field(default=None, description="Optional brand ID from brands/list")
    writing_style_id: int | None = Field(default=None, description="Optional style ID from styles/list")
    guidelines: str | None = Field(default=None, max_length=2000, description="Custom instructions (max 2000 chars)")
    enhancements: list[str] | None = Field(
        default=None,
        description="Optional: 'tldr', 'featured_image', 'internal_links', 'faq', 'key_takeaways', 'video_embed', 'quotes', 'patent'",
    )


class ArticleGenerateResponse(BaseModel):
    """Response from POST articles/generate."""

    success: bool = True
    job_id: int | None = None
    topic: str | None = None
    credits_charged: int | None = None
    estimated_time: str | None = None
    status: str | None = "pending"
    poll_url: str | None = None
    error: str | None = None
    retry_after: int | None = None
    active_job_id: int | None = None


class ArticleGetResponse(BaseModel):
    """Response from GET articles/get."""

    success: bool = True
    job_id: int | None = None
    topic: str | None = None
    status: str | None = None  # pending, processing, completed, failed, cancelled
    progress: int | None = None
    content_html: str | None = None
    featured_image: str | None = None
    meta_title: str | None = None
    meta_description: str | None = None
    word_count: int | None = None
    error_detail: str | None = None
    error: str | None = None


class ArticleListItem(BaseModel):
    """Single article summary in articles/list."""

    job_id: int | None = None
    id: int | None = None
    topic: str | None = None
    status: str | None = None
    created_at: str | None = None
    word_count: int | None = None


class ArticleListResponse(BaseModel):
    """Response from GET articles/list."""

    success: bool = True
    articles: list[dict[str, Any]] = Field(default_factory=list)
    count: int | None = 0
    page: int | None = 1
    limit: int | None = 20


class SEOAnalyzeRequest(BaseModel):
    """Payload for POST seo/analyze."""

    type: Literal["url", "text"] = Field(..., description="'url' or 'text'")
    value: str = Field(..., description="The URL to analyze or raw HTML/text content")
    keyword: str | None = Field(default=None, description="Target keyword (auto-extracted if empty)")
    brand_id: int | None = Field(default=None, description="Optional brand ID")


class SEOAnalyzeResponse(BaseModel):
    """Response from POST seo/analyze."""

    success: bool = True
    job_id: int | None = None
    keyword: str | None = None
    credits_charged: int | None = None
    estimated_time: str | None = None
    status: str | None = "pending"
    poll_url: str | None = None
    error: str | None = None


class SEOGetResponse(BaseModel):
    """Response from GET seo/get."""

    success: bool = True
    job_id: int | None = None
    status: str | None = None
    keyword: str | None = None
    score: float | None = None
    data: dict[str, Any] | None = None
    recommendations: list[dict[str, Any]] | None = None
    error: str | None = None


class HumanizerDetectRequest(BaseModel):
    """Payload for POST humanizer/detect."""

    text: str = Field(..., min_length=50, max_length=50000, description="Text to analyze (50-50,000 chars)")
    language: str | None = Field(default="English", description="Language of the text")


class HumanizerDetectResponse(BaseModel):
    """Response from POST humanizer/detect."""

    success: bool = True
    ai_probability: int | None = None
    verdict: Literal["likely_human", "mixed", "likely_ai", "unknown"] | None = None
    credits_charged: int | None = None
    word_count: int | None = None
    error: str | None = None


class HumanizerRewriteRequest(BaseModel):
    """Payload for POST humanizer/rewrite."""

    text: str = Field(..., min_length=20, max_length=50000, description="Text to humanize (20-50,000 chars)")
    strength: Literal["Subtle", "Moderate", "Strong"] | None = Field(default="Moderate")
    language: str | None = Field(default="English")
    add_imperfections: bool | None = Field(default=False)
    brand_id: int | None = Field(default=None)


class HumanizerRewriteResponse(BaseModel):
    """Response from POST humanizer/rewrite."""

    success: bool = True
    rewritten_text: str | None = None
    strength: str | None = None
    language: str | None = None
    credits_charged: int | None = None
    original_length: int | None = None
    rewritten_length: int | None = None
    error: str | None = None


class FactReference(BaseModel):
    url: str | None = None
    title: str | None = None


class FactCheckRequest(BaseModel):
    """Payload for POST factcheck/verify."""

    text: str = Field(..., description="The claim to verify (3-300 words)")
    brand_id: int | None = Field(default=None)


class FactCheckResponse(BaseModel):
    """Response from POST factcheck/verify."""

    success: bool = True
    verdict: Literal["TRUE", "FALSE", "INCONCLUSIVE", "unknown"] | None = None
    is_fact: bool | None = None
    explanation: str | None = None
    search_query: str | None = None
    references: list[FactReference] | None = None
    credits_charged: int | None = None
    word_count: int | None = None
    error: str | None = None


class AccountCreditsResponse(BaseModel):
    """Response from GET account/credits."""

    model_config = ConfigDict(populate_by_name=True)

    success: bool = True
    credits: int | None = Field(default=None)
    credits_available: int | None = Field(default=None, alias="credits_available")
    credits_pool: int | None = Field(default=None, alias="credits_pool")
    credits_total: int | None = Field(default=None, alias="credits_total")
    brand_allocated: int | None = Field(default=None, alias="brand_allocated")
    brands: list[dict[str, Any]] = Field(default_factory=list)
    plan_type: str | None = None
    plan_tier: str | None = None
    api_usage_today: dict[str, int] | None = None
    error: str | None = None

    @model_validator(mode="after")
    def populate_credits(self) -> "AccountCreditsResponse":
        """Ensure credits reflects available or pool if not explicitly set."""
        if self.credits is None:
            if self.credits_available is not None:
                self.credits = self.credits_available
            elif self.credits_pool is not None:
                self.credits = self.credits_pool
            elif self.credits_total is not None:
                self.credits = self.credits_total
            else:
                self.credits = 0
        return self


class AccountLimitsResponse(BaseModel):
    """Response from GET account/limits."""

    success: bool = True
    limits: dict[str, Any] | None = None
    rate_limits: dict[str, Any] | None = None
    error: str | None = None


class WritingStyle(BaseModel):
    id: int
    name: str
    description: str | None = None
    is_active: bool | None = True
    created_at: str | None = None


class StylesListResponse(BaseModel):
    """Response from GET styles/list."""

    success: bool = True
    styles: list[WritingStyle] = Field(default_factory=list)
    count: int | None = 0
    hint: str | None = None
    error: str | None = None


class Brand(BaseModel):
    id: int
    name: str
    url: str | None = None
    created_at: str | None = None


class BrandsListResponse(BaseModel):
    """Response from GET brands/list."""

    success: bool = True
    brands: list[Brand] = Field(default_factory=list)
    count: int | None = 0
    hint: str | None = None
    error: str | None = None


class PreflightResult(BaseModel):
    """Typed result of WordPress site preflight connectivity check."""

    success: bool
    site: str
    category: str = "ok"  # "ok", "invalid_alias", "unauthorized_alias", "ssh_error", "wp_error", "timeout"
    message: str = ""
    version: str | None = None
    exit_code: int = 0

    def __bool__(self) -> bool:
        return self.success


