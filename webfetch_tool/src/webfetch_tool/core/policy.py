"""Policy engine for URL validation and access control."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import urlparse

from webfetch_tool.core.config import PolicyConfig


@dataclass
class PolicyVerdict:
    """Result of policy check."""

    allowed: bool
    reason: Optional[str] = None


class PolicyEngine:
    """
    Policy engine for URL access control.
    
    Checks:
    - Domain allowlist/blocklist
    - URL scheme restrictions
    - Content type restrictions
    """

    def __init__(self, config: PolicyConfig):
        """
        Initialize policy engine.
        
        Args:
            config: Policy configuration
        """
        self.config = config

    def check_url(self, url: str) -> PolicyVerdict:
        """
        Check if URL is allowed by policy.
        
        Args:
            url: URL to check
            
        Returns:
            PolicyVerdict with decision
        """
        parsed = urlparse(url)
        
        # Check scheme
        if parsed.scheme not in self.config.allowed_schemes:
            return PolicyVerdict(
                allowed=False,
                reason=f"Scheme '{parsed.scheme}' not allowed",
            )
        
        # Check HTTPS requirement
        if self.config.require_https and parsed.scheme != "https":
            return PolicyVerdict(
                allowed=False,
                reason="HTTPS required",
            )
        
        # Check domain blocklist first (higher priority)
        domain = parsed.netloc.lower()
        for blocked in self.config.blocked_domains:
            if domain == blocked or domain.endswith(f".{blocked}"):
                return PolicyVerdict(
                    allowed=False,
                    reason=f"Domain '{domain}' is blocked",
                )
        
        # Check domain allowlist (if configured)
        if self.config.allowed_domains:
            allowed = False
            for allowed_domain in self.config.allowed_domains:
                if domain == allowed_domain or domain.endswith(f".{allowed_domain}"):
                    allowed = True
                    break
            
            if not allowed:
                return PolicyVerdict(
                    allowed=False,
                    reason=f"Domain '{domain}' not in allowlist",
                )
        
        # Check port restrictions
        port = parsed.port
        if port:
            if port in self.config.blocked_ports:
                return PolicyVerdict(
                    allowed=False,
                    reason=f"Port {port} is blocked",
                )
            
            if self.config.allowed_ports and port not in self.config.allowed_ports:
                return PolicyVerdict(
                    allowed=False,
                    reason=f"Port {port} not allowed",
                )
        
        return PolicyVerdict(allowed=True)
