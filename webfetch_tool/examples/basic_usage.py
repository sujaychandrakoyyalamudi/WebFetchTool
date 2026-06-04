"""Example usage of WebFetchTool with LangChain."""

from webfetch_tool import FetchConfig, PolicyConfig, WebFetcher
from webfetch_tool.langchain import WebFetchLoader, WebFetchTool, create_webfetch_tool


def example_basic_fetch():
    """Basic HTTP fetch example."""
    print("=== Basic Fetch Example ===\n")
    
    fetcher = WebFetcher()
    result = fetcher.fetch("https://example.com")
    
    if result.success:
        print(f"Title: {result.metadata_extracted.get('title', 'N/A')}")
        print(f"Status: {result.metadata.status_code}")
        print(f"Text (first 500 chars): {result.text[:500] if result.text else 'N/A'}")
    else:
        print(f"Error: {result.metadata.error_message}")


def example_browser_fetch():
    """Browser-based fetch for JavaScript-heavy sites."""
    print("\n=== Browser Fetch Example ===\n")
    
    config = FetchConfig(use_browser=True, browser_headless=True)
    fetcher = WebFetcher(config=config)
    
    # Note: This requires playwright to be installed
    # result = fetcher.fetch("https://example.com/dynamic-content")
    print("Browser mode configured (requires playwright)")


def example_with_policy():
    """Fetch with security policy."""
    print("\n=== Policy Example ===\n")
    
    policy = PolicyConfig(
        allowed_domains=["example.com", "iana.org"],
        block_private_ips=True,
        require_https=False,
    )
    
    fetcher = WebFetcher(policy=policy)
    result = fetcher.fetch("https://www.iana.org/")
    
    if result.success:
        print(f"Fetched: {result.metadata.final_url}")
    else:
        print(f"Blocked/Error: {result.metadata.error_message}")


def example_langchain_loader():
    """LangChain document loader example."""
    print("\n=== LangChain Loader Example ===\n")
    
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    
    loader = WebFetchLoader(
        urls=["https://example.com"],
        use_browser=False,
        extract_metadata=True,
    )
    
    documents = loader.load()
    
    if documents:
        doc = documents[0]
        print(f"Document metadata: {doc.metadata}")
        print(f"Content length: {len(doc.page_content)}")
        
        # Split for RAG
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
        )
        chunks = text_splitter.split_documents(documents)
        print(f"Created {len(chunks)} chunks")


def example_langchain_tool():
    """LangChain agent tool example."""
    print("\n=== LangChain Tool Example ===\n")
    
    # Create the tool
    tool = create_webfetch_tool(
        name="web_fetch",
        description="Fetch content from a URL",
    )
    
    print(f"Tool name: {tool.name}")
    print(f"Tool description: {tool.description}")
    
    # Test the tool directly
    result = tool.run({"url": "https://example.com"})
    print(f"Tool result (first 200 chars): {result[:200]}")


def example_authenticated_fetch():
    """Authenticated fetch example."""
    print("\n=== Authenticated Fetch Example ===\n")
    
    from webfetch_tool import AuthConfig
    
    auth = AuthConfig(
        api_key="your-api-key-here",
        api_key_header="X-API-Key",
    )
    
    fetcher = WebFetcher(auth=auth)
    print("Auth configured for API key authentication")
    # result = fetcher.fetch("https://api.example.com/protected")


def main():
    """Run all examples."""
    print("WebFetchTool Examples\n")
    print("=" * 50)
    
    try:
        example_basic_fetch()
    except Exception as e:
        print(f"Basic fetch error: {e}")
    
    try:
        example_with_policy()
    except Exception as e:
        print(f"Policy fetch error: {e}")
    
    try:
        example_langchain_tool()
    except Exception as e:
        print(f"LangChain tool error: {e}")
    
    try:
        example_langchain_loader()
    except Exception as e:
        print(f"LangChain loader error: {e}")
    
    print("\n" + "=" * 50)
    print("Examples complete!")


if __name__ == "__main__":
    main()
