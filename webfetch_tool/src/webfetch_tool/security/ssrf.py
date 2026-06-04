"""SSRF (Server-Side Request Forgery) protection."""

from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from typing import List, Optional, Set
from urllib.parse import urlparse

import validators

from webfetch_tool.core.config import PolicyConfig


@dataclass
class ValidationResult:
    """Result of URL validation."""

    is_valid: bool
    error: Optional[str] = None
    resolved_ips: List[str] = None

    def __post_init__(self):
        if self.resolved_ips is None:
            self.resolved_ips = []


# Private and reserved IP ranges
PRIVATE_IP_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("224.0.0.0/4"),
    ipaddress.ip_network("240.0.0.0/4"),
]

LINK_LOCAL_RANGES = [
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("fe80::/10"),
]

LOOPBACK_RANGES = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
]


class SSRFValidator:
    """
    SSRF (Server-Side Request Forgery) validator.
    
    Protects against:
    - Private IP address access
    - Link-local address access
    - Loopback address access
    - DNS rebinding attacks
    - Invalid URL schemes
    """

    def __init__(self, policy: Optional[PolicyConfig] = None):
        """
        Initialize SSRF validator.
        
        Args:
            policy: Policy configuration
        """
        self.policy = policy or PolicyConfig()

    def validate(self, url: str) -> ValidationResult:
        """
        Validate URL for SSRF vulnerabilities.
        
        Args:
            url: URL to validate
            
        Returns:
            ValidationResult with validation status
        """
        # Basic URL validation
        if not self._is_valid_url(url):
            return ValidationResult(
                is_valid=False,
                error="Invalid URL format",
            )
        
        parsed = urlparse(url)
        
        # Check scheme
        if parsed.scheme not in self.policy.allowed_schemes:
            return ValidationResult(
                is_valid=False,
                error=f"Scheme '{parsed.scheme}' not allowed",
            )
        
        # Check hostname
        hostname = parsed.hostname
        if not hostname:
            return ValidationResult(
                is_valid=False,
                error="No hostname in URL",
            )
        
        # Check for private IPs in hostname
        if self.policy.block_private_ips:
            try:
                # Resolve hostname
                ips = self._resolve_hostname(hostname)
                
                if not ips:
                    return ValidationResult(
                        is_valid=False,
                        error=f"Could not resolve hostname: {hostname}",
                    )
                
                # Check each resolved IP
                for ip_str in ips:
                    try:
                        ip = ipaddress.ip_address(ip_str)
                        
                        # Check private ranges
                        if self._is_private_ip(ip):
                            return ValidationResult(
                                is_valid=False,
                                error=f"Private IP address blocked: {ip_str}",
                                resolved_ips=ips,
                            )
                        
                        # Check link-local
                        if self.policy.block_link_local and self._is_link_local(ip):
                            return ValidationResult(
                                is_valid=False,
                                error=f"Link-local IP address blocked: {ip_str}",
                                resolved_ips=ips,
                            )
                        
                        # Check loopback
                        if self.policy.block_loopback and self._is_loopback(ip):
                            return ValidationResult(
                                is_valid=False,
                                error=f"Loopback IP address blocked: {ip_str}",
                                resolved_ips=ips,
                            )
                            
                    except ValueError:
                        # Not a valid IP, continue
                        pass
                
                return ValidationResult(
                    is_valid=True,
                    resolved_ips=ips,
                )
                
            except socket.gaierror as e:
                return ValidationResult(
                    is_valid=False,
                    error=f"DNS resolution failed: {str(e)}",
                )
        
        return ValidationResult(is_valid=True)

    def _is_valid_url(self, url: str) -> bool:
        """Check if URL has valid format."""
        try:
            result = validators.url(url)
            return result is True
        except Exception:
            return False

    def _resolve_hostname(self, hostname: str) -> List[str]:
        """
        Resolve hostname to IP addresses.
        
        Uses safe DNS resolution that prevents DNS rebinding.
        """
        try:
            # Get all address records
            results = socket.getaddrinfo(hostname, None, socket.AF_INET)
            ips = list(set([r[4][0] for r in results]))
            return ips
        except socket.gaierror:
            return []

    def _is_private_ip(self, ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
        """Check if IP is in private range."""
        for network in PRIVATE_IP_RANGES:
            try:
                if ip in network:
                    return True
            except TypeError:
                # IPv4/IPv6 mismatch
                pass
        return False

    def _is_link_local(self, ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
        """Check if IP is link-local."""
        for network in LINK_LOCAL_RANGES:
            try:
                if ip in network:
                    return True
            except TypeError:
                pass
        return False

    def _is_loopback(self, ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
        """Check if IP is loopback."""
        for network in LOOPBACK_RANGES:
            try:
                if ip in network:
                    return True
            except TypeError:
                pass
        return False
