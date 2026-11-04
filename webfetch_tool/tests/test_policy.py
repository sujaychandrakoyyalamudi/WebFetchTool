"""Domain rules in PolicyEngine match the URL's hostname, not its netloc."""

import pytest
import requests

from webfetch_tool import PolicyConfig, WebFetcher
from webfetch_tool.core.policy import PolicyEngine

BLOCK = {"blocked_domains": ["blocked.example"]}
ALLOW = {"allowed_domains": ["allowed.example"]}


def check(url, **policy):
    """Return the PolicyEngine verdict for url under PolicyConfig(**policy)."""
    return PolicyEngine(PolicyConfig(**policy)).check_url(url)


# Explicit ports


@pytest.mark.parametrize(
    "url, host",
    [
        ("https://blocked.example:443/", "blocked.example"),
        ("http://blocked.example:80/page", "blocked.example"),
        ("https://sub.blocked.example:443/", "sub.blocked.example"),
    ],
)
def test_explicit_port_does_not_bypass_blocked_domains(url, host):
    verdict = check(url, **BLOCK)
    assert not verdict.allowed
    assert verdict.reason == f"Domain '{host}' is blocked"


@pytest.mark.parametrize(
    "url",
    [
        "https://allowed.example:443/",
        "http://allowed.example:80/",
        "https://api.allowed.example:443/path",
    ],
)
def test_allowed_domain_with_explicit_port_is_allowed(url):
    assert check(url, **ALLOW).allowed


def test_port_rules_still_apply_to_allowed_domains():
    verdict = check("https://allowed.example:8443/", **ALLOW)
    assert not verdict.allowed
    assert verdict.reason == "Port 8443 not allowed"


# Userinfo


@pytest.mark.parametrize(
    "url",
    [
        "https://user@blocked.example/",
        "https://user:secret@blocked.example:443/",
    ],
)
def test_userinfo_does_not_hide_blocked_domain(url):
    verdict = check(url, **BLOCK)
    assert not verdict.allowed
    assert verdict.reason == "Domain 'blocked.example' is blocked"  # no credentials


def test_userinfo_cannot_pose_as_allowed_domain():
    verdict = check("https://allowed.example@evil.example/", **ALLOW)
    assert not verdict.allowed
    assert verdict.reason == "Domain 'evil.example' not in allowlist"


def test_userinfo_on_allowed_domain_is_allowed():
    assert check("https://user:secret@allowed.example/", **ALLOW).allowed


def test_backslash_in_authority_is_refused():
    # urlparse reports allowed.example as the hostname; requests connects to evil.example
    verdict = check("https://evil.example\\@allowed.example/", **ALLOW)
    assert not verdict.allowed
    assert verdict.reason == "Backslash in URL authority"


# Subdomains


@pytest.mark.parametrize("url", ["https://sub.blocked.example/", "https://a.b.blocked.example/"])
def test_subdomains_of_blocked_domain_are_refused(url):
    assert not check(url, **BLOCK).allowed


def test_subdomain_of_allowed_domain_is_allowed():
    assert check("https://api.allowed.example/", **ALLOW).allowed


@pytest.mark.parametrize(
    "url", ["https://notblocked.example/", "https://blocked.example.evil.example/"]
)
def test_lookalike_hosts_are_not_blocked(url):
    assert check(url, **BLOCK).allowed


@pytest.mark.parametrize(
    "url", ["https://notallowed.example/", "https://allowed.example.evil.example/"]
)
def test_lookalike_hosts_are_not_allowed(url):
    assert not check(url, **ALLOW).allowed


# Case and trailing dot


@pytest.mark.parametrize(
    "url",
    [
        "https://BLOCKED.Example/",
        "https://blocked.example./",
        "https://Sub.Blocked.Example.:443/",
    ],
)
def test_case_and_trailing_dot_do_not_bypass_blocked_domains(url):
    assert not check(url, **BLOCK).allowed


def test_case_and_trailing_dot_still_match_allowed_domains():
    assert check("https://ALLOWED.example./", **ALLOW).allowed


def test_domain_entries_are_normalized_the_same_way():
    assert not check("https://blocked.example/", blocked_domains=["Blocked.Example."]).allowed
    assert check("https://allowed.example/", allowed_domains=["Allowed.Example."]).allowed


# Through WebFetcher.fetch


def test_fetch_refuses_blocked_domain_with_port_without_sending_requests(monkeypatch):
    def no_network(*args, **kwargs):
        raise AssertionError("no request should be sent for a blocked URL")

    monkeypatch.setattr(requests.Session, "get", no_network)
    # block_private_ips=False skips the DNS lookup in SSRFValidator
    policy = PolicyConfig(blocked_domains=["blocked.example"], block_private_ips=False)
    with WebFetcher(policy=policy) as fetcher:
        result = fetcher.fetch("https://blocked.example:443/")

    assert not result.success
    assert result.metadata.error_message == "Policy violation: Domain 'blocked.example' is blocked"
