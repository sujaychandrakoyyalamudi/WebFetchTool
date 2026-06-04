"""Core module for WebFetchTool."""

from webfetch_tool.core.models import FetchResult, FetchMetadata, FetchMode
from webfetch_tool.core.config import FetchConfig, PolicyConfig, AuthConfig
from webfetch_tool.core.fetcher import WebFetcher
from webfetch_tool.core.policy import PolicyEngine
from webfetch_tool.core.auth import AuthManager

__all__ = [
    "FetchResult",
    "FetchMetadata",
    "FetchMode",
    "FetchConfig",
    "PolicyConfig",
    "AuthConfig",
    "WebFetcher",
    "PolicyEngine",
    "AuthManager",
]
