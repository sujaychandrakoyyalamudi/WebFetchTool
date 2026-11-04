"""Playwright browser client for JavaScript rendering."""

from __future__ import annotations

import tempfile
from typing import Any, Dict, Optional

from playwright.sync_api import sync_playwright


class BrowserClient:
    """
    Playwright-based browser client for JavaScript rendering.
    
    Features:
    - Headless browser automation
    - Screenshot capture
    - Tracing for debugging
    - Isolated browser contexts
    - Storage state persistence
    """

    def __init__(
        self,
        headless: bool = True,
        proxy: Optional[str] = None,
    ):
        """
        Initialize browser client.
        
        Args:
            headless: Run browser in headless mode
            proxy: Proxy server URL
        """
        self.headless = headless
        self.proxy = proxy
        self._playwright = None
        self._browser = None

    def _ensure_browser(self):
        """Ensure browser is launched."""
        if self._playwright is None:
            self._playwright = sync_playwright().start()
        
        if self._browser is None:
            launch_args = {
                "headless": self.headless,
            }
            
            if self.proxy:
                launch_args["proxy"] = {"server": self.proxy}
            
            self._browser = self._playwright.chromium.launch(**launch_args)

    def fetch(
        self,
        url: str,
        timeout: float = 60.0,
        wait_until: str = "networkidle",
        storage_state: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Fetch page using browser rendering.
        
        Args:
            url: URL to fetch
            timeout: Navigation timeout in seconds (converted to milliseconds for Playwright)
            wait_until: Wait condition (load, domcontentloaded, networkidle, commit)
            storage_state: Path to storage state file for cookies/auth
            trace_id: Trace identifier for debugging
            
        Returns:
            Dictionary with html, status_code, final_url, screenshot, trace
        """
        self._ensure_browser()
        
        # Create browser context
        context_args = {}
        if storage_state:
            context_args["storage_state"] = storage_state
        
        context = self._browser.new_context(**context_args)
        
        # Start tracing if trace_id provided
        if trace_id:
            trace_path = f"/tmp/trace-{trace_id}.zip"
            context.tracing.start(screenshots=True, snapshots=True)
        else:
            trace_path = None
        
        try:
            page = context.new_page()
            
            # Navigate to page (Playwright timeouts are in milliseconds)
            response = page.goto(url, wait_until=wait_until, timeout=timeout * 1000)
            
            # Get page content
            html = page.content()
            final_url = page.url
            
            # Get status code
            status_code = response.status if response else None
            
            # Take screenshot
            screenshot = None
            try:
                screenshot = page.screenshot(full_page=True)
            except Exception:
                pass
            
            result = {
                "success": True,
                "html": html,
                "final_url": final_url,
                "status_code": status_code,
                "screenshot": screenshot,
            }
            
            # Stop tracing and get trace path
            if trace_path:
                context.tracing.stop(path=trace_path)
                with open(trace_path, "rb") as f:
                    result["trace"] = f.read()
            
            return result
            
        except Exception as e:
            # Stop tracing on error
            if trace_path:
                try:
                    context.tracing.stop(path=trace_path)
                except Exception:
                    pass
            
            return {
                "success": False,
                "error": str(e),
                "html": None,
                "final_url": url,
                "status_code": None,
                "screenshot": None,
            }
            
        finally:
            context.close()

    def close(self) -> None:
        """Close browser and playwright."""
        if self._browser:
            self._browser.close()
            self._browser = None
        
        if self._playwright:
            self._playwright.stop()
            self._playwright = None

    def __enter__(self) -> "BrowserClient":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()
