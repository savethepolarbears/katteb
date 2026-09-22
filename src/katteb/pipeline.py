"""Pipeline event adapter and webhook dispatcher for Katteb and WordPress Fleet."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from katteb.wordpress import WordPressFleetManager, generate_expansion_receipt, validate_site_alias


def _redact_sensitive_tokens(msg: str) -> str:
    """Redact API keys, bearer tokens, and credentials from error strings."""
    if not msg:
        return msg
    msg = re.sub(r"(Bearer\s+)[A-Za-z0-9_\-\.]{8,}", r"\1[REDACTED]", msg, flags=re.IGNORECASE)
    msg = re.sub(r"((?:api[-_]?key|token)[\"'\s:=]+)[A-Za-z0-9_\-\.]{8,}", r"\1[REDACTED]", msg, flags=re.IGNORECASE)
    return msg


class PipelineEventPayload(BaseModel):
    """Schema for inbound webhook / automation requests (e.g. from Activepieces)."""

    model_config = ConfigDict(extra="forbid")

    event: str = Field(default="post_expansion_requested", description="Event identifier")
    site: str = Field(..., description="Target WordPress fleet site alias")
    post_id: int = Field(..., gt=0, description="WordPress post ID to enrich")
    target_words: int = Field(default=1500, ge=500, le=5000, description="Target word count")
    enhancements: list[str] = Field(
        default_factory=lambda: ["tldr", "key_takeaways", "faq"],
        description="Enhancements to request from Katteb",
    )
    guidelines: str | None = Field(default=None, description="Custom editorial guidelines")
    brand_id: int | None = Field(default=None, description="Optional Katteb brand ID")
    writing_style_id: int | None = Field(default=None, description="Optional Katteb writing style ID")
    dry_run: bool = Field(default=False, description="Dry run simulation mode")
    receipt_dir: str | None = Field(default=None, description="Optional directory to write markdown audit receipt")


def process_pipeline_event(
    payload: dict[str, Any] | str,
    wp_manager: WordPressFleetManager | None = None,
) -> dict[str, Any]:
    """Process an inbound pipeline event payload and return a structured result dict.

    Accepts raw JSON string or pre-parsed dict.
    Returns a dictionary guaranteed to be JSON-serializable for stdout.
    """
    if isinstance(payload, str):
        try:
            raw_data = json.loads(payload)
        except json.JSONDecodeError as exc:
            return {
                "success": False,
                "error": f"Invalid JSON payload: {exc}",
                "event": None,
                "site": None,
                "post_id": None,
            }
    elif isinstance(payload, dict):
        raw_data = payload
    else:
        return {
            "success": False,
            "error": f"Payload must be JSON string or dict, got {type(payload).__name__}",
            "event": None,
            "site": None,
            "post_id": None,
        }

    try:
        validated = PipelineEventPayload.model_validate(raw_data)
    except ValidationError as exc:
        return {
            "success": False,
            "error": f"Validation error: {exc}",
            "event": raw_data.get("event"),
            "site": raw_data.get("site"),
            "post_id": raw_data.get("post_id"),
        }

    # Validate event type
    if validated.event != "post_expansion_requested":
        return {
            "success": False,
            "error": f"Unsupported event type: '{validated.event}'. Supported: 'post_expansion_requested'",
            "event": validated.event,
            "site": validated.site,
            "post_id": validated.post_id,
        }

    # Validate site alias
    try:
        sanitized_site = validate_site_alias(validated.site)
    except ValueError as exc:
        return {
            "success": False,
            "error": f"Invalid site alias: {exc}",
            "event": validated.event,
            "site": validated.site,
            "post_id": validated.post_id,
        }

    manager = wp_manager or WordPressFleetManager()

    try:
        if validated.receipt_dir:
            resolved_rcpt = Path(validated.receipt_dir).resolve()
            forbidden_roots = [
                f.resolve() for f in [Path("/etc"), Path("/var"), Path("/usr"), Path("/bin"), Path("/sbin"), Path("/System"), Path("/private")]
            ]
            for f_root in forbidden_roots:
                if resolved_rcpt == f_root or f_root in resolved_rcpt.parents:
                    return {
                        "success": False,
                        "error": f"Insecure receipt_dir '{validated.receipt_dir}' inside system root '{f_root}'",
                        "event": validated.event,
                        "site": sanitized_site,
                        "post_id": validated.post_id,
                        "dry_run": validated.dry_run,
                    }

        res = manager.expand_and_update_post(
            site=sanitized_site,
            post_id=validated.post_id,
            word_count=validated.target_words,
            enhancements=validated.enhancements,
            brand_id=validated.brand_id,
            writing_style_id=validated.writing_style_id,
            guidelines=validated.guidelines,
            dry_run=validated.dry_run,
        )

        if not res.get("success", False) and not res.get("dry_run", False):
            return {
                "success": False,
                "error": _redact_sensitive_tokens(str(res.get("error", "WordPress post expansion failed"))),
                "event": validated.event,
                "site": sanitized_site,
                "post_id": validated.post_id,
                "dry_run": validated.dry_run,
            }

        receipt_path = None
        if validated.receipt_dir and not validated.dry_run:
            receipt_path = generate_expansion_receipt(
                site=sanitized_site,
                results=[res],
                output_dir=validated.receipt_dir,
            )

        return {
            "success": True,
            "event": validated.event,
            "site": sanitized_site,
            "post_id": validated.post_id,
            "dry_run": validated.dry_run,
            "title": res.get("title"),
            "old_word_count": res.get("old_word_count") or res.get("current_word_count"),
            "new_word_count": res.get("new_word_count"),
            "meta_description": res.get("meta_description"),
            "receipt_path": receipt_path,
        }
    except Exception as exc:
        return {
            "success": False,
            "error": _redact_sensitive_tokens(str(exc)),
            "event": validated.event,
            "site": sanitized_site,
            "post_id": validated.post_id,
            "dry_run": validated.dry_run,
        }
