"""Katteb API v2 Client and CLI Integration Toolkit."""

__version__ = "1.0.0"

from katteb.client import KattebClient
from katteb.config import KattebConfig, get_config

__all__ = ["KattebClient", "KattebConfig", "get_config"]
