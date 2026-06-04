"""LangChain integration module for WebFetchTool."""

from webfetch_tool.langchain.loader import WebFetchLoader
from webfetch_tool.langchain.tool import create_webfetch_tool, WebFetchTool
from webfetch_tool.langchain.multi_fetcher import MultiURLFetcher

__all__ = [
    "WebFetchLoader",
    "create_webfetch_tool",
    "WebFetchTool",
    "MultiURLFetcher",
]
