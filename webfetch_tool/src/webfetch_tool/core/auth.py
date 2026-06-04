"""Authentication management for web fetcher."""

from __future__ import annotations

from typing import Dict, Optional

from webfetch_tool.core.config import AuthConfig


class AuthManager:
    """
    Authentication manager for web fetcher.
    
    Supports:
    - API Key authentication
    - Basic authentication
    - Bearer token authentication
    - Cookie-based authentication
    - OAuth2 tokens
    """

    def __init__(self, config: Optional[AuthConfig] = None):
        """
        Initialize auth manager.
        
        Args:
            config: Authentication configuration
        """
        self.config = config or AuthConfig()

    def get_headers(self) -> Dict[str, str]:
        """Get authentication headers."""
        headers = {}
        
        if self.config.api_key:
            headers[self.config.api_key_header] = self.config.api_key
        
        if self.config.bearer_token:
            headers["Authorization"] = f"Bearer {self.config.bearer_token}"
        
        if self.config.custom_headers:
            headers.update(self.config.custom_headers)
        
        return headers

    def get_basic_auth(self) -> Optional[tuple]:
        """Get basic auth tuple."""
        if self.config.username and self.config.password:
            return (self.config.username, self.config.password)
        return None

    def get_cookies(self) -> Dict[str, str]:
        """Get authentication cookies."""
        return self.config.cookies.copy()

    def has_auth(self) -> bool:
        """Check if any authentication is configured."""
        return self.config.has_auth()
