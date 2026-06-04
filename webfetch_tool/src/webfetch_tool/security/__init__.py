"""Security module for WebFetchTool."""

from webfetch_tool.security.ssrf import SSRFValidator, ValidationResult

__all__ = [
    "SSRFValidator",
    "ValidationResult",
]
