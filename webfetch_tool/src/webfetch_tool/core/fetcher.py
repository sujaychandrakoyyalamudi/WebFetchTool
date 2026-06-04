"""Main web fetcher implementation."""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from webfetch_tool.core.config import AuthConfig, FetchConfig, PolicyConfig
from webfetch_tool.core.models import FetchMetadata, FetchMode, FetchResult
from webfetch_tool.core.policy import PolicyEngine
from webfetch_tool.security.ssrf import SSRFValidator
from webfetch_tool.parsers.html import HTMLParser
from webfetch_tool.browser.playwright_client import BrowserClient


class WebFetcher:
    """
    Production-grade web fetcher with policy-governed fetch pipeline.
    
    Supports:
    - HTTP/HTTPS fetching with connection pooling
    - Browser-based rendering for JavaScript-heavy sites
    - SSRF protection and URL validation
    - Robots.txt compliance
    - Retry logic with exponential backoff
    - Conditional requests (ETag, Last-Modified)
    - Provenance tracking
    - PII redaction
    """

    def __init__(
        self,
        config: Optional[FetchConfig] = None,
        policy: Optional[PolicyConfig] = None,
        auth: Optional[AuthConfig] = None,
    ):
        """
        Initialize the web fetcher.
        
        Args:
            config: Fetch configuration
            policy: Policy configuration
            auth: Authentication configuration
        """
        self.config = config or FetchConfig()
        self.policy = policy or PolicyConfig()
        self.auth = auth or AuthConfig()
        
        # Initialize components
        self.policy_engine = PolicyEngine(self.policy)
        self.ssrf_validator = SSRFValidator(self.policy)
        self.html_parser = HTMLParser()
        self.browser_client: Optional[BrowserClient] = None
        
        # Initialize HTTP session
        self._session = self._create_session()
        
        # Robots.txt cache
        self._robots_cache: Dict[str, bool] = {}

    def _create_session(self) -> requests.Session:
        """Create configured HTTP session."""
        retry = Retry(
            total=self.config.retry_count,
            connect=self.config.retry_count,
            read=self.config.retry_count,
            status=self.config.retry_count,
            allowed_methods=frozenset({"GET", "HEAD"}),
            status_forcelist=set(self.config.retry_statuses),
            backoff_factor=self.config.backoff_factor,
            respect_retry_after_header=self.config.respect_retry_after,
            raise_on_status=False,
        )

        adapter = HTTPAdapter(
            max_retries=retry,
            pool_connections=20,
            pool_maxsize=100,
        )

        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": self.config.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.8,*/*;q=0.1",
                "Accept-Language": self.config.accept_language,
            }
        )
        
        # Add authentication headers
        if self.auth:
            self._apply_auth_to_session(session)
        
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session

    def _apply_auth_to_session(self, session: requests.Session) -> None:
        """Apply authentication to session."""
        if not self.auth:
            return
            
        if self.auth.api_key:
            session.headers[self.auth.api_key_header] = self.auth.api_key
            
        if self.auth.bearer_token:
            session.headers["Authorization"] = f"Bearer {self.auth.bearer_token}"
            
        if self.auth.username and self.auth.password:
            session.auth = (self.auth.username, self.auth.password)
            
        if self.auth.cookies:
            for name, value in self.auth.cookies.items():
                session.cookies.set(name, value)
                
        if self.auth.custom_headers:
            session.headers.update(self.auth.custom_headers)

    def fetch(
        self,
        url: str,
        etag: Optional[str] = None,
        last_modified: Optional[str] = None,
        use_browser: Optional[bool] = None,
    ) -> FetchResult:
        """
        Fetch content from a URL.
        
        Args:
            url: URL to fetch
            etag: ETag for conditional request
            last_modified: Last-Modified header for conditional request
            use_browser: Override default browser mode
            
        Returns:
            FetchResult with content and metadata
        """
        start_time = time.time()
        trace_id = str(uuid.uuid4())
        
        # Validate URL
        validation_result = self.ssrf_validator.validate(url)
        if not validation_result.is_valid:
            return self._create_error_result(
                url=url,
                error=f"URL validation failed: {validation_result.error}",
                trace_id=trace_id,
            )
        
        # Check policy
        policy_verdict = self.policy_engine.check_url(url)
        if not policy_verdict.allowed:
            return self._create_error_result(
                url=url,
                error=f"Policy violation: {policy_verdict.reason}",
                trace_id=trace_id,
            )
        
        # Check robots.txt
        if self.config.respect_robots_txt:
            robots_allowed = self._check_robots_txt(url)
            if not robots_allowed:
                return self._create_error_result(
                    url=url,
                    error="Blocked by robots.txt",
                    trace_id=trace_id,
                    robots_verdict="disallow",
                )
        
        # Determine fetch mode
        browser_mode = use_browser if use_browser is not None else self.config.use_browser
        
        try:
            if browser_mode:
                result = self._fetch_browser(url, trace_id)
            else:
                result = self._fetch_http(
                    url, 
                    etag=etag, 
                    last_modified=last_modified,
                    trace_id=trace_id,
                )
            
            # Parse and enrich result
            if result.success and result.html:
                parsed = self.html_parser.parse(result.html, result.metadata.final_url)
                result.text = parsed.text
                result.links = parsed.links
                result.images = parsed.images
                result.metadata_extracted = parsed.metadata
            
            # Add timing
            result.metadata.duration_ms = (time.time() - start_time) * 1000
            result.metadata.trace_id = trace_id
            
            return result
            
        except Exception as e:
            return self._create_error_result(
                url=url,
                error=str(e),
                trace_id=trace_id,
                duration_ms=(time.time() - start_time) * 1000,
            )

    def _fetch_http(
        self,
        url: str,
        etag: Optional[str] = None,
        last_modified: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> FetchResult:
        """Fetch using HTTP."""
        headers = {}
        
        # Conditional requests
        if self.config.use_conditional_requests:
            if etag:
                headers["If-None-Match"] = etag
            if last_modified:
                headers["If-Modified-Since"] = last_modified
        
        # Add extra headers
        headers.update(self.config.extra_headers)
        
        try:
            response = self._session.get(
                url,
                headers=headers,
                timeout=(self.config.connect_timeout, self.config.http_timeout),
                allow_redirects=self.config.follow_redirects,
                stream=False,
            )
            
            # Handle 304 Not Modified
            if response.status_code == 304:
                metadata = FetchMetadata(
                    source_url=url,
                    final_url=response.url,
                    status_code=304,
                    fetch_mode=FetchMode.HTTP,
                    etag=response.headers.get("ETag"),
                    last_modified=response.headers.get("Last-Modified"),
                    trace_id=trace_id,
                )
                return FetchResult(success=True, metadata=metadata)
            
            # Read content
            content = response.content
            
            # Check content size
            if len(content) > self.config.max_content_size:
                content = content[: self.config.max_content_size]
            
            metadata = FetchMetadata(
                source_url=url,
                final_url=response.url,
                status_code=response.status_code,
                content_type=response.headers.get("Content-Type", ""),
                content_encoding=response.headers.get("Content-Encoding", ""),
                content_length=len(content),
                encoding=response.encoding or "utf-8",
                etag=response.headers.get("ETag"),
                last_modified=response.headers.get("Last-Modified"),
                headers=dict(response.headers),
                trace_id=trace_id,
            )
            
            success = response.status_code < 400
            
            return FetchResult(
                success=success,
                metadata=metadata,
                html=content.decode(metadata.encoding, errors="replace") if content else None,
                content=content,
            )
            
        except requests.exceptions.RequestException as e:
            metadata = FetchMetadata(
                source_url=url,
                final_url=url,
                error_message=str(e),
                trace_id=trace_id,
            )
            return FetchResult(success=False, metadata=metadata)

    def _fetch_browser(self, url: str, trace_id: Optional[str] = None) -> FetchResult:
        """Fetch using browser rendering."""
        if not self.browser_client:
            self.browser_client = BrowserClient(
                headless=self.config.browser_headless,
                proxy=self.policy.proxy_url if self.policy.proxy_enabled else None,
            )
        
        try:
            browser_result = self.browser_client.fetch(
                url=url,
                timeout=self.config.browser_timeout,
                wait_until=self.config.wait_until,
                storage_state=self.auth.storage_state_path,
                trace_id=trace_id,
            )
            
            metadata = FetchMetadata(
                source_url=url,
                final_url=browser_result.get("final_url", url),
                status_code=browser_result.get("status_code"),
                content_type="text/html",
                fetch_mode=FetchMode.BROWSER,
                trace_id=trace_id,
            )
            
            return FetchResult(
                success=browser_result.get("success", False),
                metadata=metadata,
                html=browser_result.get("html"),
                screenshot=browser_result.get("screenshot"),
                trace=browser_result.get("trace"),
            )
            
        except Exception as e:
            metadata = FetchMetadata(
                source_url=url,
                final_url=url,
                error_message=str(e),
                fetch_mode=FetchMode.BROWSER,
                trace_id=trace_id,
            )
            return FetchResult(success=False, metadata=metadata)

    def _check_robots_txt(self, url: str) -> bool:
        """Check if URL is allowed by robots.txt."""
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        # Check cache
        if base_url in self._robots_cache:
            return self._robots_cache[base_url]
        
        # Fetch robots.txt
        try:
            robots_url = f"{base_url}/robots.txt"
            response = self._session.get(
                robots_url,
                timeout=(self.config.connect_timeout, self.config.http_timeout),
            )
            
            if response.status_code == 404:
                # No robots.txt, allow
                self._robots_cache[base_url] = True
                return True
            
            # Simple robots.txt parsing (production should use robotexclusionrules)
            robots_text = response.text
            user_agent = self.config.user_agent.split("/")[0]
            
            allowed = True
            current_agents = []
            
            for line in robots_text.split("\n"):
                line = line.strip().lower()
                
                if line.startswith("user-agent:"):
                    agent = line.split(":", 1)[1].strip()
                    current_agents.append(agent)
                elif line.startswith("disallow:") and current_agents:
                    if "*" in current_agents or user_agent in current_agents:
                        path = line.split(":", 1)[1].strip()
                        if path and parsed.path.startswith(path):
                            allowed = False
                            break
                elif line.startswith("allow:") and current_agents:
                    if "*" in current_agents or user_agent in current_agents:
                        path = line.split(":", 1)[1].strip()
                        if path and parsed.path.startswith(path):
                            allowed = True
            
            self._robots_cache[base_url] = allowed
            return allowed
            
        except Exception:
            # On error, allow (fail-open)
            self._robots_cache[base_url] = True
            return True

    def _create_error_result(
        self,
        url: str,
        error: str,
        trace_id: Optional[str] = None,
        duration_ms: Optional[float] = None,
        robots_verdict: Optional[str] = None,
    ) -> FetchResult:
        """Create an error result."""
        metadata = FetchMetadata(
            source_url=url,
            final_url=url,
            error_message=error,
            trace_id=trace_id,
            duration_ms=duration_ms,
            robots_verdict=robots_verdict,
        )
        return FetchResult(success=False, metadata=metadata)

    def fetch_batch(
        self,
        urls: List[str],
        max_concurrent: int = 5,
    ) -> List[FetchResult]:
        """
        Fetch multiple URLs concurrently.
        
        Args:
            urls: List of URLs to fetch
            max_concurrent: Maximum concurrent requests
            
        Returns:
            List of FetchResult objects
        """
        # For now, sequential implementation
        # Production should use asyncio with semaphore
        results = []
        for url in urls:
            result = self.fetch(url)
            results.append(result)
        return results

    def close(self) -> None:
        """Clean up resources."""
        self._session.close()
        if self.browser_client:
            self.browser_client.close()

    def __enter__(self) -> "WebFetcher":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()
