"""Multi-URL fetcher for batch operations."""

from __future__ import annotations

import asyncio
from typing import List, Optional

from webfetch_tool.core.config import AuthConfig, FetchConfig, PolicyConfig
from webfetch_tool.core.fetcher import WebFetcher
from webfetch_tool.core.models import FetchResult


class MultiURLFetcher:
    """
    Fetch multiple URLs concurrently.
    
    Example:
        ```python
        from webfetch_tool.langchain import MultiURLFetcher
        
        fetcher = MultiURLFetcher(
            max_concurrent=5,
            use_browser=False,
        )
        
        results = fetcher.fetch_all([
            "https://example.com/page1",
            "https://example.com/page2",
        ])
        ```
    """

    def __init__(
        self,
        config: Optional[FetchConfig] = None,
        policy: Optional[PolicyConfig] = None,
        auth: Optional[AuthConfig] = None,
        use_browser: bool = False,
        max_concurrent: int = 5,
    ):
        """
        Initialize multi-URL fetcher.
        
        Args:
            config: Fetch configuration
            policy: Policy configuration
            auth: Authentication configuration
            use_browser: Use browser rendering mode
            max_concurrent: Maximum concurrent requests
        """
        self.config = config or FetchConfig()
        self.policy = policy or PolicyConfig()
        self.auth = auth or AuthConfig()
        self.use_browser = use_browser
        self.max_concurrent = max_concurrent
        
        # Create base fetcher
        self._base_fetcher = WebFetcher(
            config=self.config,
            policy=self.policy,
            auth=self.auth,
        )

    def fetch_all(self, urls: List[str]) -> List[FetchResult]:
        """
        Fetch all URLs concurrently.
        
        Args:
            urls: List of URLs to fetch
            
        Returns:
            List of FetchResult objects
        """
        # For now, sequential implementation
        # Production should use asyncio with semaphore
        results = []
        
        for url in urls:
            result = self._base_fetcher.fetch(url, use_browser=self.use_browser)
            results.append(result)
        
        return results

    async def fetch_all_async(self, urls: List[str]) -> List[FetchResult]:
        """
        Fetch all URLs asynchronously.
        
        Args:
            urls: List of URLs to fetch
            
        Returns:
            List of FetchResult objects
        """
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def fetch_with_semaphore(url: str) -> FetchResult:
            async with semaphore:
                # Run synchronous fetch in executor
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: self._base_fetcher.fetch(url, use_browser=self.use_browser),
                )
                return result
        
        tasks = [fetch_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to error results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                from webfetch_tool.core.models import FetchMetadata
                metadata = FetchMetadata(
                    source_url=urls[i],
                    final_url=urls[i],
                    error_message=str(result),
                )
                final_results.append(FetchResult(success=False, metadata=metadata))
            else:
                final_results.append(result)
        
        return final_results
