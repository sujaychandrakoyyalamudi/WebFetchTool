"""Configuration classes for WebFetchTool."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class FetchConfig:
    """Configuration for fetch operations."""

    # Timeouts
    connect_timeout: float = 5.0
    http_timeout: float = 30.0
    browser_timeout: float = 60.0

    # Retry settings
    retry_count: int = 2
    retry_statuses: List[int] = field(default_factory=lambda: [429, 500, 502, 503, 504])
    backoff_factor: float = 0.5
    respect_retry_after: bool = True

    # Redirects
    max_redirects: int = 5
    follow_redirects: bool = True

    # User agent
    user_agent: str = "WebFetchTool/1.0 (+contact@example.invalid)"

    # Fetch mode
    use_browser: bool = False
    browser_headless: bool = True
    wait_until: str = "networkidle"

    # Content limits
    max_content_size: int = 10 * 1024 * 1024  # 10MB

    # Robots.txt
    respect_robots_txt: bool = True
    robots_cache_ttl: int = 3600  # seconds

    # Provenance tracking
    track_provenance: bool = True

    # Conditional requests
    use_conditional_requests: bool = True

    # Locale
    accept_language: str = "en-US,en;q=0.8"

    # Additional headers
    extra_headers: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "connect_timeout": self.connect_timeout,
            "http_timeout": self.http_timeout,
            "browser_timeout": self.browser_timeout,
            "retry_count": self.retry_count,
            "retry_statuses": self.retry_statuses,
            "backoff_factor": self.backoff_factor,
            "respect_retry_after": self.respect_retry_after,
            "max_redirects": self.max_redirects,
            "follow_redirects": self.follow_redirects,
            "user_agent": self.user_agent,
            "use_browser": self.use_browser,
            "browser_headless": self.browser_headless,
            "wait_until": self.wait_until,
            "max_content_size": self.max_content_size,
            "respect_robots_txt": self.respect_robots_txt,
            "robots_cache_ttl": self.robots_cache_ttl,
            "track_provenance": self.track_provenance,
            "use_conditional_requests": self.use_conditional_requests,
            "accept_language": self.accept_language,
            "extra_headers": self.extra_headers,
        }


@dataclass
class PolicyConfig:
    """Policy configuration for fetch operations."""

    # Domain allowlist (empty = all allowed)
    allowed_domains: List[str] = field(default_factory=list)

    # Domain blocklist
    blocked_domains: List[str] = field(default_factory=list)

    # URL scheme allowlist
    allowed_schemes: List[str] = field(default_factory=lambda: ["http", "https"])

    # Security
    require_https: bool = False
    block_private_ips: bool = True
    block_link_local: bool = True
    block_loopback: bool = True

    # Port restrictions
    allowed_ports: List[int] = field(default_factory=lambda: [80, 443])
    blocked_ports: List[int] = field(default_factory=list)

    # Content type restrictions
    allowed_content_types: List[str] = field(default_factory=list)  # empty = all
    blocked_content_types: List[str] = field(
        default_factory=lambda: ["application/x-executable", "application/x-msdownload"]
    )

    # Rate limiting
    per_host_concurrency: int = 2
    rate_limit_requests: Optional[int] = None
    rate_limit_period: int = 60  # seconds

    # Geo-routing (advanced)
    geo_routing_enabled: bool = False
    preferred_country: Optional[str] = None

    # Proxy settings
    proxy_enabled: bool = False
    proxy_url: Optional[str] = None
    proxy_bypass: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "allowed_domains": self.allowed_domains,
            "blocked_domains": self.blocked_domains,
            "allowed_schemes": self.allowed_schemes,
            "require_https": self.require_https,
            "block_private_ips": self.block_private_ips,
            "block_link_local": self.block_link_local,
            "block_loopback": self.block_loopback,
            "allowed_ports": self.allowed_ports,
            "blocked_ports": self.blocked_ports,
            "allowed_content_types": self.allowed_content_types,
            "blocked_content_types": self.blocked_content_types,
            "per_host_concurrency": self.per_host_concurrency,
            "rate_limit_requests": self.rate_limit_requests,
            "rate_limit_period": self.rate_limit_period,
            "geo_routing_enabled": self.geo_routing_enabled,
            "preferred_country": self.preferred_country,
            "proxy_enabled": self.proxy_enabled,
            "proxy_url": self.proxy_url,
            "proxy_bypass": self.proxy_bypass,
        }


@dataclass
class AuthConfig:
    """Authentication configuration for fetch operations."""

    # API Key authentication
    api_key: Optional[str] = None
    api_key_header: str = "X-API-Key"

    # Basic authentication
    username: Optional[str] = None
    password: Optional[str] = None

    # Bearer token authentication
    bearer_token: Optional[str] = None

    # Cookie-based authentication
    cookies: Dict[str, str] = field(default_factory=dict)

    # OAuth2
    oauth_client_id: Optional[str] = None
    oauth_client_secret: Optional[str] = None
    oauth_token_url: Optional[str] = None
    oauth_scopes: List[str] = field(default_factory=list)
    oauth_access_token: Optional[str] = None
    oauth_refresh_token: Optional[str] = None

    # Custom headers
    custom_headers: Dict[str, str] = field(default_factory=dict)

    # Session storage state (for browser mode)
    storage_state_path: Optional[str] = None

    def has_auth(self) -> bool:
        """Check if any authentication is configured."""
        return bool(
            self.api_key
            or self.username
            or self.bearer_token
            or self.cookies
            or self.oauth_access_token
            or self.custom_headers
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (excluding secrets)."""
        return {
            "api_key_header": self.api_key_header,
            "has_api_key": bool(self.api_key),
            "has_username": bool(self.username),
            "has_bearer_token": bool(self.bearer_token),
            "cookie_count": len(self.cookies),
            "has_oauth": bool(self.oauth_access_token),
            "has_custom_headers": bool(self.custom_headers),
            "storage_state_path": self.storage_state_path,
        }
