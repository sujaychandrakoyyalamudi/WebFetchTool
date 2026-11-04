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


def _normalize_domain(name: str) -> str:
    """Lowercase a domain name and drop trailing dots ("Example.COM." -> "example.com")."""
    return name.lower().rstrip(".")


def _matches_domain(host: str, domain: str) -> bool:
    """Return True if the normalized host is domain or one of its subdomains."""
    domain = _normalize_domain(domain)
    return host == domain or host.endswith(f".{domain}")


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
        
        # urlparse and requests/browsers disagree on hosts such as
        # "https://evil.example\@allowed.example/" (allowed.example vs evil.example)
        if "\\" in parsed.netloc:
            return PolicyVerdict(
                allowed=False,
                reason="Backslash in URL authority",
            )

        # Match domains on the hostname, which excludes userinfo and port
        domain = _normalize_domain(parsed.hostname or "")

        # Check domain blocklist first (higher priority)
        for blocked in self.config.blocked_domains:
            if _matches_domain(domain, blocked):
                return PolicyVerdict(
                    allowed=False,
                    reason=f"Domain '{domain}' is blocked",
                )
        
        # Check domain allowlist (if configured)
        if self.config.allowed_domains:
            allowed = False
            for allowed_domain in self.config.allowed_domains:
                if _matches_domain(domain, allowed_domain):
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
