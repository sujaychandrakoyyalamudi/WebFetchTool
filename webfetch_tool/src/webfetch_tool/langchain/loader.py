"""LangChain document loader for web content."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from langchain_core.documents import Document

from webfetch_tool.core.config import AuthConfig, FetchConfig, PolicyConfig
from webfetch_tool.core.fetcher import WebFetcher


class WebFetchLoader:
    """
    LangChain document loader for web content.
    
    Loads web pages as LangChain documents with rich metadata.
    
    Example:
        ```python
        from webfetch_tool.langchain import WebFetchLoader
        
        loader = WebFetchLoader(
            urls=["https://example.com/page1", "https://example.com/page2"],
            use_browser=False,
        )
        documents = loader.load()
        ```
    """

    def __init__(
        self,
        urls: List[str],
        config: Optional[FetchConfig] = None,
        policy: Optional[PolicyConfig] = None,
        auth: Optional[AuthConfig] = None,
        use_browser: bool = False,
        extract_links: bool = False,
        extract_metadata: bool = True,
    ):
        """
        Initialize web fetch loader.
        
        Args:
            urls: List of URLs to load
            config: Fetch configuration
            policy: Policy configuration
            auth: Authentication configuration
            use_browser: Use browser rendering mode
            extract_links: Extract links as separate documents
            extract_metadata: Include metadata in documents
        """
        self.urls = urls
        self.use_browser = use_browser
        self.extract_links = extract_links
        self.extract_metadata = extract_metadata
        
        # Create fetcher
        self.fetcher = WebFetcher(
            config=config,
            policy=policy,
            auth=auth,
        )

    def load(self) -> List[Document]:
        """
        Load all URLs as documents.
        
        Returns:
            List of LangChain Document objects
        """
        documents = []
        
        for url in self.urls:
            result = self.fetcher.fetch(url, use_browser=self.use_browser)
            
            if not result.success:
                # Skip failed fetches or add error document
                continue
            
            # Main content document
            if result.text:
                metadata = {
                    "source": result.metadata.source_url,
                    "final_url": result.metadata.final_url,
                    "title": result.metadata_extracted.get("title", ""),
                    "content_type": result.metadata.content_type,
                    "status_code": result.metadata.status_code,
                    "timestamp": result.metadata.timestamp.isoformat(),
                    "fetch_mode": result.metadata.fetch_mode.value,
                    "language": result.metadata_extracted.get("language"),
                }
                
                # Add Open Graph metadata if available
                if "open_graph" in result.metadata_extracted:
                    for key, value in result.metadata_extracted["open_graph"].items():
                        metadata[f"og:{key}"] = value
                
                # Add Twitter Card metadata if available
                if "twitter_card" in result.metadata_extracted:
                    for key, value in result.metadata_extracted["twitter_card"].items():
                        metadata[f"twitter:{key}"] = value
                
                doc = Document(
                    page_content=result.text,
                    metadata=metadata,
                )
                documents.append(doc)
            
            # Extract links as separate documents if requested
            if self.extract_links and result.links:
                for link in result.links[:50]:  # Limit to first 50 links
                    link_doc = Document(
                        page_content=f"Link: {link}",
                        metadata={
                            "source": result.metadata.source_url,
                            "link_url": link,
                            "link_type": "outbound",
                        },
                    )
                    documents.append(link_doc)
        
        return documents

    async def aload(self) -> List[Document]:
        """
        Async load (currently synchronous implementation).
        
        Returns:
            List of LangChain Document objects
        """
        return self.load()
