"""LangChain tool for web fetching."""

from __future__ import annotations

from typing import Any, Dict, Optional, Type

from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from webfetch_tool.core.config import AuthConfig, FetchConfig, PolicyConfig
from webfetch_tool.core.fetcher import WebFetcher


class WebFetchInput(BaseModel):
    """Input schema for web fetch tool."""

    url: str = Field(..., description="URL to fetch content from")


class WebFetchTool(BaseTool):
    """
    LangChain tool for fetching web content.
    
    Can be used in LangChain agents to fetch live web content.
    
    Example:
        ```python
        from webfetch_tool.langchain import WebFetchTool
        
        tool = WebFetchTool(
            name="web_fetch",
            description="Fetch content from a URL",
        )
        
        # Use in agent
        from langchain.agents import initialize_agent
        from langchain.llms import OpenAI
        
        agent = initialize_agent(
            tools=[tool],
            llm=OpenAI(),
            agent="zero-shot-react-description",
        )
        
        response = agent.run("What is on https://example.com?")
        ```
    """

    name: str = "web_fetch"
    description: str = (
        "Fetches content from a specified URL. "
        "Use this tool when you need to retrieve current web page content. "
        "Input should be a valid URL."
    )
    args_schema: Type[BaseModel] = WebFetchInput
    
    config: Optional[FetchConfig] = None
    policy: Optional[PolicyConfig] = None
    auth: Optional[AuthConfig] = None
    use_browser: bool = False
    
    _fetcher: Optional[WebFetcher] = None

    def __init__(
        self,
        name: str = "web_fetch",
        description: Optional[str] = None,
        config: Optional[FetchConfig] = None,
        policy: Optional[PolicyConfig] = None,
        auth: Optional[AuthConfig] = None,
        use_browser: bool = False,
    ):
        super().__init__()
        
        if name:
            self.name = name
        if description:
            self.description = description
        if config:
            self.config = config
        if policy:
            self.policy = policy
        if auth:
            self.auth = auth
        self.use_browser = use_browser
        
        self._fetcher = None

    @property
    def fetcher(self) -> WebFetcher:
        """Lazy initialization of fetcher."""
        if self._fetcher is None:
            self._fetcher = WebFetcher(
                config=self.config,
                policy=self.policy,
                auth=self.auth,
            )
        return self._fetcher

    def _run(self, url: str) -> str:
        """
        Execute the fetch tool.
        
        Args:
            url: URL to fetch
            
        Returns:
            Fetched text content or error message
        """
        result = self.fetcher.fetch(url, use_browser=self.use_browser)
        
        if not result.success:
            return f"Error fetching {url}: {result.metadata.error_message}"
        
        # Return main text content
        if result.text:
            # Truncate if too long (limit context)
            max_length = 4000
            if len(result.text) > max_length:
                return result.text[:max_length] + "\n\n[Content truncated...]"
            return result.text
        
        # Fallback to HTML if no text extracted
        if result.html:
            max_length = 4000
            if len(result.html) > max_length:
                return result.html[:max_length] + "\n\n[Content truncated...]"
            return result.html
        
        return "No content could be extracted from the page."

    async def _arun(self, url: str) -> str:
        """Async execution (currently synchronous)."""
        return self._run(url)


def create_webfetch_tool(
    name: str = "web_fetch",
    description: Optional[str] = None,
    config: Optional[FetchConfig] = None,
    policy: Optional[PolicyConfig] = None,
    auth: Optional[AuthConfig] = None,
    use_browser: bool = False,
) -> WebFetchTool:
    """
    Create a web fetch tool for LangChain agents.
    
    Args:
        name: Tool name
        description: Tool description
        config: Fetch configuration
        policy: Policy configuration
        auth: Authentication configuration
        use_browser: Use browser rendering mode
        
    Returns:
        Configured WebFetchTool instance
    """
    return WebFetchTool(
        name=name,
        description=description,
        config=config,
        policy=policy,
        auth=auth,
        use_browser=use_browser,
    )
