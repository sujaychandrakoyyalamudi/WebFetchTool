# WebFetchTool

Production-grade LLM WebFetchTool with policy-governed fetch pipeline, browser automation, and LangChain integration.

## Features

### Must-Have (Production Ready)
- ✅ Strict URL parsing and SSRF defense
- ✅ HTTP core semantics (GET, HEAD, redirects, headers, streaming)
- ✅ Connection pooling and persistent sessions
- ✅ Timeouts on every network phase
- ✅ Retry policy with idempotency awareness
- ✅ Honor `Retry-After` and provider throttling
- ✅ Per-host concurrency limits and backpressure
- ✅ Headless browser mode with JavaScript execution (Playwright)
- ✅ Isolated sessions, cookies, and storage
- ✅ Authentication support (API keys, Basic, Bearer, OAuth)
- ✅ Cookie handling consistent with web standards
- ✅ HTML, JSON, and XML parsing
- ✅ PDF extraction with OCR fallback
- ✅ Image handling and OCR fallback
- ✅ Canonicalization and deduplication
- ✅ Conditional requests and change detection (ETag, Last-Modified)
- ✅ Robots.txt handling with default respect mode
- ✅ Data minimization and privacy-by-default
- ✅ PII detection and log redaction
- ✅ TLS verification, encryption at rest, secret management
- ✅ Structured logs, metrics, traces, audit trails
- ✅ Health checks and graceful shutdown
- ✅ Stable REST API with provenance-rich outputs
- ✅ Official SDKs and documentation

### Should-Have (First Major Release)
- 🔄 Sitemap discovery and parsing
- 🔄 Link extraction with frontier prioritization
- 🔄 Structured metadata extraction (schema.org, Open Graph)
- 🔄 Locale negotiation and hreflang awareness
- 🔄 Robust character-encoding handling
- 🔄 Wait strategies and event-stream support
- 🔄 Tracing, HAR, screenshots, replay/debug assets
- 🔄 Circuit breakers
- 🔄 Batching and crawl job orchestration
- 🔄 Pagination helpers
- 🔄 Chunking and summarization hooks for LLMs
- 🔄 Keyword and vector index integration
- 🔄 Pluggable artifact, metadata, and cache backends
- 🔄 Scheduling, webhooks, event-driven triggers
- 🔄 Consent records and policy evidence
- 🔄 Legal takedown workflows and retention controls
- 🔄 Accessibility-preserving extraction
- 🔄 HTTP/SOCKS proxy support
- 🔄 Challenge detection and authorized human-in-the-loop escalation
- 🔄 Container isolation and resource limits
- 🔄 CI/CD, threat modeling, fuzzing, security testing
- 🔄 gRPC surface for internal high-throughput workflows
- 🔄 OpenTelemetry end to end
- 🔄 Cost estimation and quota accounting

## Installation

```bash
pip install webfetch-tool
```

For development:

```bash
pip install -e ".[dev]"
playwright install  # Install browser binaries
```

## Quick Start

### Basic HTTP Fetch

```python
from webfetch_tool import WebFetcher

fetcher = WebFetcher()
result = fetcher.fetch("https://example.com")

print(result.text)
print(result.metadata)
```

### Browser Mode (JavaScript Rendering)

```python
from webfetch_tool import WebFetcher

fetcher = WebFetcher(use_browser=True)
result = fetcher.fetch("https://example.com/dynamic-content")

print(result.text)
print(result.screenshot)  # Optional screenshot
```

### LangChain Integration

```python
from langchain.text_splitter import RecursiveCharacterTextSplitter
from webfetch_tool.langchain import WebFetchLoader

# Load web content
loader = WebFetchLoader(
    urls=["https://example.com/page1", "https://example.com/page2"],
    use_browser=False,
    extract_links=True,
)

documents = loader.load()

# Split for RAG
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
)
chunks = text_splitter.split_documents(documents)

# Use with your favorite LLM
from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings

vectorstore = Chroma.from_documents(chunks, OpenAIEmbeddings())
retriever = vectorstore.as_retriever()
```

### Advanced Configuration

```python
from webfetch_tool import WebFetcher, FetchConfig, PolicyConfig

config = FetchConfig(
    http_timeout=30,
    connect_timeout=5,
    browser_timeout=60,
    max_redirects=5,
    retry_count=2,
    respect_robots_txt=True,
    user_agent="MyBot/1.0 (+contact@example.com)",
)

policy = PolicyConfig(
    allowed_domains=["example.com", "trusted.org"],
    blocked_domains=["malicious.com"],
    require_https=True,
    block_private_ips=True,
)

fetcher = WebFetcher(config=config, policy=policy)
result = fetcher.fetch("https://example.com")
```

### Authenticated Fetch

```python
from webfetch_tool import WebFetcher, AuthConfig

auth = AuthConfig(
    api_key="your-api-key",
    api_key_header="X-API-Key",
)

fetcher = WebFetcher(auth=auth)
result = fetcher.fetch("https://api.example.com/protected")
```

### With Provenance Tracking

```python
from webfetch_tool import WebFetcher

fetcher = WebFetcher(track_provenance=True)
result = fetcher.fetch("https://example.com")

print(f"Source URL: {result.source_url}")
print(f"Final URL: {result.final_url}")
print(f"Canonical URL: {result.canonical_url}")
print(f"Fetch timestamp: {result.timestamp}")
print(f"HTTP status: {result.status_code}")
print(f"Content type: {result.content_type}")
print(f"Trace ID: {result.trace_id}")
```

## Architecture

```
┌─────────────────┐
│  LLM / Client   │
└────────┬────────┘
         │
┌────────▼────────┐
│  Fetch API      │
│  / Orchestrator │
└────────┬────────┘
         │
┌────────▼────────┐
│  Policy Engine  │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼──┐  ┌───▼──┐
│ HTTP │  │Browser│
│Fetch │  │ Fetch │
└───┬──┘  └───┬──┘
    │         │
    └────┬────┘
         │
┌────────▼────────┐
│  Parsers &      │
│  Normalizers    │
└────────┬────────┘
         │
┌────────▼────────┐
│  Canonicalize   │
│  & Deduplicate  │
└────────┬────────┘
         │
┌────────▼────────┐
│  PII Redaction  │
│  & Compliance   │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼──┐  ┌───▼──┐
│Store │  │Search│
│& Meta│  │Index │
└──────┘  └──────┘
```

## Configuration Reference

### FetchConfig

| Parameter | Default | Description |
|-----------|---------|-------------|
| `http_timeout` | 30 | Total HTTP request timeout (seconds) |
| `connect_timeout` | 5 | Connection timeout (seconds) |
| `browser_timeout` | 60 | Browser navigation timeout (seconds) |
| `max_redirects` | 5 | Maximum redirect follow count |
| `retry_count` | 2 | Number of retries for idempotent requests |
| `respect_robots_txt` | True | Whether to respect robots.txt |
| `user_agent` | "WebFetchTool/1.0" | User-Agent header |
| `use_browser` | False | Enable browser rendering mode |
| `track_provenance` | True | Track detailed provenance metadata |

### PolicyConfig

| Parameter | Default | Description |
|-----------|---------|-------------|
| `allowed_domains` | [] | Whitelist of allowed domains (empty = all) |
| `blocked_domains` | [] | Blacklist of blocked domains |
| `require_https` | False | Require HTTPS URLs only |
| `block_private_ips` | True | Block private/reserved IP ranges |
| `max_content_size` | 10MB | Maximum content size to fetch |

### AuthConfig

| Parameter | Default | Description |
|-----------|---------|-------------|
| `api_key` | None | API key for authentication |
| `api_key_header` | "Authorization" | Header name for API key |
| `username` | None | Username for Basic auth |
| `password` | None | Password for Basic auth |
| `bearer_token` | None | Bearer token for Authorization header |
| `cookies` | {} | Cookies to include in requests |

## Security Considerations

### SSRF Protection

The tool includes built-in SSRF protection:
- URL scheme allowlisting (http, https only by default)
- DNS rebinding protection
- Private IP address blocking
- Port restrictions

### Privacy and Compliance

- PII detection and automatic redaction in logs
- Data minimization by default
- Configurable retention policies
- GDPR/CCPA compliance support (access, deletion, portability)

### TLS and Secrets

- Certificate validation enabled by default
- Secrets managed via environment variables or secret managers
- Encryption at rest for sensitive artifacts

## Observability

The tool integrates with OpenTelemetry for distributed tracing:

```python
from opentelemetry import trace
from webfetch_tool import WebFetcher

# Configure OTLP exporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor

tracer_provider = trace.get_tracer_provider()
span_processor = BatchSpanProcessor(OTLPSpanExporter())
tracer_provider.add_span_processor(span_processor)

fetcher = WebFetcher()
result = fetcher.fetch("https://example.com")
```

## LangChain Tools

### WebFetchTool

```python
from langchain.agents import Tool
from webfetch_tool.langchain import create_webfetch_tool

tool = create_webfetch_tool(
    name="web_fetch",
    description="Fetch content from a URL",
    use_browser=False,
)

# Use in agent
from langchain.agents import initialize_agent
from langchain.llms import OpenAI

agent = initialize_agent(
    tools=[tool],
    llm=OpenAI(),
    agent="zero-shot-react-description",
)

response = agent.run("What is the main content of https://example.com?")
```

### MultiURLFetcher

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

## Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Type checking
mypy src

# Code formatting
black src tests

# Linting
ruff check src tests
```

## License

MIT License

## Contributing

Contributions welcome! Please read our contributing guidelines before submitting PRs.

## Support

- Documentation: https://webfetch-tool.readthedocs.io
- Issues: https://github.com/yourusername/webfetch-tool/issues
- Discussions: https://github.com/yourusername/webfetch-tool/discussions
