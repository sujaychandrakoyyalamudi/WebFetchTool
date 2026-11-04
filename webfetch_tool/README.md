# WebFetchTool

WebFetchTool is a Python library that fetches web pages for LLM applications. Before each fetch it checks the URL against configurable safety rules and robots.txt. It then fetches the page over HTTP or renders it in headless Chromium, extracts the main text, links, and page metadata, and returns them together with fetch metadata in one result object. LangChain wrappers are included.

Status: alpha, version 0.1.0. The package is not published on PyPI. A pytest suite covers the domain rules and the browser timeout (see [Development and tests](#development-and-tests)).

This file is the detailed reference. The [repository README](../README.md) is a shorter overview.

## How a fetch works

```text
WebFetcher.fetch(url)
  1. SSRFValidator.validate(url)    URL format, scheme, IPv4 private-range check
  2. PolicyEngine.check_url(url)    scheme, HTTPS-only, domain lists, ports
  3. robots.txt check               when FetchConfig.respect_robots_txt is true
  4. HTTP fetch with requests       default
     or browser fetch (Playwright)  when use_browser is true
  5. HTMLParser.parse(...)          text, links, images, page metadata
  6. FetchResult                    content plus FetchMetadata
```

`fetch()` reports validation, policy, robots.txt, and network failures in the result instead of raising. Check `result.success` and `result.metadata.error_message`. For HTTP status codes of 400 and above, `success` is `False`, `metadata.status_code` holds the code, and `error_message` is empty. The body is still available in `html` and `content`, but no text is extracted.

## Implemented

### HTTP fetching (`core/fetcher.py`, `WebFetcher`)

- One `requests.Session` per `WebFetcher`, with an `HTTPAdapter` connection pool (`pool_connections=20`, `pool_maxsize=100`, not configurable). Cookies set by responses persist for the life of the instance.
- `GET` requests only, with a connect timeout (`connect_timeout`) and a read timeout (`http_timeout`). There is no overall deadline.
- Redirects are followed when `follow_redirects` is true. `metadata.final_url` records where the fetch ended.
- Retries through urllib3 `Retry`, restricted to `GET` and `HEAD`. They use exponential backoff (`backoff_factor`), retry on `retry_statuses` (429, 500, 502, 503, and 504 by default), and honor `Retry-After` when `respect_retry_after` is true.
- Conditional requests: pass `etag` and/or `last_modified` to `fetch()` to send `If-None-Match` and `If-Modified-Since`. A 304 response comes back with `success=True`, `status_code=304`, and no body. The response's `ETag` and `Last-Modified` values are stored in `metadata`. There is no built-in cache, so the caller keeps the previous values.
- Request headers: `User-Agent`, `Accept`, and `Accept-Language`, plus `FetchConfig.extra_headers`.
- The body is read in full, then cut to `max_content_size` bytes (10 MB by default).
- `fetch_batch(urls)` fetches the URLs one after another.
- `close()` and context-manager support (`with WebFetcher() as fetcher:`) close the session and the browser.

### Browser mode (`browser/playwright_client.py`, `BrowserClient`)

- Chromium launched through Playwright's sync API, headless by default (`browser_headless`).
- Turned on with `FetchConfig(use_browser=True)`, or per call with `fetch(url, use_browser=True)`.
- The browser is launched once per `WebFetcher` and reused. Each fetch runs in a new browser context that is closed afterward, so cookies and storage do not carry over between fetches.
- An optional Playwright storage-state file (`AuthConfig.storage_state_path`) is loaded into each context, for example to reuse a logged-in session.
- Navigation waits for the `wait_until` state (`"networkidle"` by default) for up to `browser_timeout` seconds (60 by default).
- Each fetch returns the rendered HTML, the final URL, the status code, a full-page PNG screenshot (`result.screenshot`), and a Playwright trace archive (`result.trace`).
- Optional proxy: `PolicyConfig(proxy_enabled=True, proxy_url=...)` is passed to Chromium. HTTP mode ignores these fields.

### URL checks (`security/ssrf.py`, `core/policy.py`)

- `SSRFValidator`: URL format check with `validators.url()`, scheme allowlist, and blocking of private and reserved IPv4 addresses.
- `PolicyEngine`: scheme allowlist, HTTPS-only option, domain blocklist and allowlist matched on the URL's hostname (subdomains included), and port allow and block lists.
- The exact coverage and the gaps are listed under [Safety and limits](#safety-and-limits).

### robots.txt

- Checked before every fetch in both modes when `respect_robots_txt` is true (the default).
- A disallowed URL returns `success=False`, `error_message="Blocked by robots.txt"`, and `metadata.robots_verdict="disallow"`.
- The parser is simplified. See [Safety and limits](#safety-and-limits) and [Known issues](#known-issues).

### HTML extraction (`parsers/html.py`, `HTMLParser`)

- Main text with readability-lxml. If readability raises an error, the parser falls back to the full page text with `script`, `style`, and `noscript` removed.
- Links: absolute `<a href>` URLs, with exact duplicates removed and order preserved.
- Images: absolute `src`, `alt`, and `width` and `height` when present.
- Page metadata: `<title>`, every `<meta name>` and `<meta property>` value, Open Graph tags (`open_graph`), Twitter card tags (`twitter_card`), and JSON-LD blocks (`schema`).
- Every successful response body goes through this HTML parser, whatever its content type. JSON, XML, PDF, and image responses are not parsed by type. In HTTP mode the raw bytes are in `result.content`.

### Authentication (HTTP mode)

- `AuthConfig` supports an API key header, HTTP Basic, a Bearer token, cookies, and custom headers.
- They are set on the shared session, so they are sent with every request that the `WebFetcher` makes.
- Browser mode uses only `storage_state_path`.

### Results and provenance (`core/models.py`)

- `FetchResult` and `FetchMetadata` dataclasses. See [Result objects](#result-objects).
- Each fetch gets a random `trace_id` (UUID4) and a UTC `timestamp`. `duration_ms` is set for every fetch that gets past the URL and robots.txt checks.
- `FetchResult.content_hash` is the SHA-256 of the extracted text, or of the raw bytes when there is no text.

### LangChain integration (`langchain/`)

- `WebFetchLoader` fetches a list of URLs and returns `langchain_core.documents.Document` objects. Their metadata holds the source and final URL, title, content type, status code, timestamp, fetch mode, and Open Graph and Twitter card tags. Failed URLs are skipped. With `extract_links=True`, it also returns up to 50 link documents per page.
- `WebFetchTool` (a LangChain `BaseTool`) and `create_webfetch_tool()` take a `url` and return the extracted text, truncated to 4,000 characters. When no text was extracted, they return the HTML instead. Failures come back as an error message string.
- `MultiURLFetcher.fetch_all()` fetches URLs sequentially. `fetch_all_async()` runs fetches in a thread pool, at most `max_concurrent` at a time. That is one global limit, not a per-host limit.
- The wrappers pass their own `use_browser` value (default `False`) to every `fetch()` call, which overrides `FetchConfig.use_browser`.

## Installation

The package is not published on PyPI, so `pip install webfetch-tool` does not work. Install it from GitHub:

```bash
pip install "git+https://github.com/sujaychandrakoyyalamudi/WebFetchTool.git#subdirectory=webfetch_tool"
```

- The distribution name is `webfetch-tool` and the import name is `webfetch_tool`. It needs Python 3.9 or later.
- Every dependency in `pyproject.toml` is required. There are no optional extras for browser, LangChain, or OCR support.
- Some declared dependencies are not imported by the code yet: `httpx`, `pypdf`, `pdfplumber`, `pytesseract`, `Pillow`, `tldextract`, `redis`, `sqlalchemy`, the `opentelemetry-*` packages, `structlog`, `langchain-community`, `tenacity`, and `aiohttp`.

Browser mode also needs a browser binary. The code launches only Chromium:

```bash
playwright install chromium
```

For development, install from a clone. The `dev` extra adds pytest, pytest-asyncio, pytest-cov, black, ruff, and mypy. A `docs` extra adds Sphinx.

```bash
git clone https://github.com/sujaychandrakoyyalamudi/WebFetchTool.git
cd WebFetchTool/webfetch_tool
pip install -e ".[dev]"
```

## Quick start

### Basic fetch

```python
from webfetch_tool import WebFetcher

with WebFetcher() as fetcher:
    result = fetcher.fetch("https://example.com")

if result.success:
    print(result.metadata_extracted.get("title"))
    print(result.text)
else:
    print(result.metadata.status_code, result.metadata.error_message)
```

### Browser mode

```python
from webfetch_tool import FetchConfig, WebFetcher

# browser_timeout is the navigation timeout in seconds (default 60).
config = FetchConfig(use_browser=True, browser_timeout=30)

with WebFetcher(config=config) as fetcher:
    result = fetcher.fetch("https://example.com")

print(result.success, result.metadata.status_code)
if result.screenshot:
    with open("page.png", "wb") as f:
        f.write(result.screenshot)  # full-page PNG
```

### Fetch and policy settings

```python
from webfetch_tool import FetchConfig, PolicyConfig, WebFetcher

config = FetchConfig(
    connect_timeout=5,
    http_timeout=30,  # read timeout, not a total deadline
    retry_count=2,
    user_agent="MyBot/1.0 (+https://example.com/bot)",
)
policy = PolicyConfig(
    allowed_domains=["example.com"],      # subdomains are allowed too
    blocked_domains=["ads.example.com"],  # checked before the allowlist
    require_https=True,
)

with WebFetcher(config=config, policy=policy) as fetcher:
    result = fetcher.fetch("https://example.com")
```

### Conditional requests

```python
from webfetch_tool import WebFetcher

with WebFetcher() as fetcher:
    first = fetcher.fetch("https://example.com")
    again = fetcher.fetch(
        "https://example.com",
        etag=first.metadata.etag,
        last_modified=first.metadata.last_modified,
    )

print(again.metadata.status_code)  # 304 when the server reports no change
```

### Authenticated fetch

```python
import json
import os

from webfetch_tool import AuthConfig, WebFetcher

# Other options: bearer_token="...", or username="..." with password="..."
auth = AuthConfig(api_key=os.environ["EXAMPLE_API_KEY"], api_key_header="X-API-Key")

with WebFetcher(auth=auth) as fetcher:
    result = fetcher.fetch("https://api.example.com/items")

data = json.loads(result.content) if result.success else None
```

Credentials go to every host this `WebFetcher` requests, so use a separate instance for each API.

### Provenance fields

```python
# result is any FetchResult, for example from the basic fetch above
m = result.metadata
print(m.source_url, m.final_url, m.status_code, m.content_type)
print(m.timestamp.isoformat(), m.duration_ms, m.trace_id)
print(result.content_hash)
```

### LangChain document loader

```python
from webfetch_tool.langchain import WebFetchLoader

loader = WebFetchLoader(
    urls=["https://example.com/page1", "https://example.com/page2"],
    use_browser=False,
    extract_links=True,
)
for doc in loader.load():
    print(doc.metadata["source"], doc.page_content[:80])
```

To chunk the documents for retrieval, pass them to a LangChain text splitter, such as `RecursiveCharacterTextSplitter` from the `langchain-text-splitters` package.

### LangChain tool

```python
from webfetch_tool.langchain import create_webfetch_tool

tool = create_webfetch_tool(
    name="web_fetch",
    description="Fetch the text content of a web page.",
    use_browser=False,
)
print(tool.invoke({"url": "https://example.com"}))
```

### Several URLs

```python
import asyncio

from webfetch_tool.langchain import MultiURLFetcher

urls = ["https://example.com/page1", "https://example.com/page2"]
fetcher = MultiURLFetcher(max_concurrent=5, use_browser=False)

results = fetcher.fetch_all(urls)                     # one at a time
results = asyncio.run(fetcher.fetch_all_async(urls))  # thread pool, up to 5 at once
```

Use `fetch_all_async()` in HTTP mode only, because Playwright's sync API cannot be shared across threads.

## Configuration reference

All three classes are dataclasses in `core/config.py`, exported from `webfetch_tool`.

### FetchConfig

| Field | Default | Effect |
|-------|---------|--------|
| `connect_timeout` | `5.0` | Connect timeout in seconds (HTTP mode and robots.txt) |
| `http_timeout` | `30.0` | Read timeout in seconds, not a total deadline |
| `browser_timeout` | `60.0` | Navigation timeout in seconds for browser mode. Converted to milliseconds for Playwright's `page.goto()` |
| `retry_count` | `2` | Limit for urllib3 `Retry` (total, connect, read, and status) |
| `retry_statuses` | `[429, 500, 502, 503, 504]` | Status codes that are retried |
| `backoff_factor` | `0.5` | urllib3 exponential backoff factor |
| `respect_retry_after` | `True` | Wait for `Retry-After` on retried responses |
| `max_redirects` | `5` | Not used. `requests` allows up to 30 redirects |
| `follow_redirects` | `True` | Follow redirects in HTTP mode |
| `user_agent` | `"WebFetchTool/1.0 (+contact@example.invalid)"` | `User-Agent` for HTTP requests. The text before the first `/` is the robots.txt agent name. Browser mode keeps Chromium's default |
| `use_browser` | `False` | Default fetch mode. `fetch(use_browser=...)` overrides it per call |
| `browser_headless` | `True` | Launch Chromium headless |
| `wait_until` | `"networkidle"` | Playwright wait state: `load`, `domcontentloaded`, `networkidle`, or `commit` |
| `max_content_size` | `10485760` (10 MB) | HTTP mode: the body is cut to this many bytes after download |
| `respect_robots_txt` | `True` | Check robots.txt before fetching |
| `robots_cache_ttl` | `3600` | Not used. The robots.txt cache never expires |
| `track_provenance` | `True` | Not used. Metadata is always recorded |
| `use_conditional_requests` | `True` | Send `If-None-Match` and `If-Modified-Since` when `fetch()` receives `etag` or `last_modified` |
| `accept_language` | `"en-US,en;q=0.8"` | `Accept-Language` header in HTTP mode |
| `extra_headers` | `{}` | Headers added to page requests in HTTP mode (not to robots.txt requests) |

### PolicyConfig

| Field | Default | Effect |
|-------|---------|--------|
| `allowed_domains` | `[]` | If not empty, only these domains and their subdomains are allowed |
| `blocked_domains` | `[]` | These domains and their subdomains are refused. Checked first |
| `allowed_schemes` | `["http", "https"]` | Allowed URL schemes |
| `require_https` | `False` | Refuse URLs that are not `https` |
| `block_private_ips` | `True` | Resolve the host (IPv4 only) and refuse private and reserved addresses |
| `block_link_local` | `True` | Extra link-local check. Runs only when `block_private_ips` is true, and the IPv4 list already covers 169.254.0.0/16 |
| `block_loopback` | `True` | Extra loopback check. Runs only when `block_private_ips` is true, and the IPv4 list already covers 127.0.0.0/8 |
| `allowed_ports` | `[80, 443]` | An explicit port must be in this list. An empty list allows any port |
| `blocked_ports` | `[]` | Explicit ports that are refused |
| `allowed_content_types` | `[]` | Not used |
| `blocked_content_types` | `["application/x-executable", "application/x-msdownload"]` | Not used |
| `per_host_concurrency` | `2` | Not used |
| `rate_limit_requests` | `None` | Not used |
| `rate_limit_period` | `60` | Not used |
| `geo_routing_enabled` | `False` | Not used |
| `preferred_country` | `None` | Not used |
| `proxy_enabled` | `False` | With `proxy_url`, sets the Chromium proxy in browser mode. HTTP mode ignores it |
| `proxy_url` | `None` | Proxy server for browser mode |
| `proxy_bypass` | `[]` | Not used |

### AuthConfig

| Field | Default | Effect |
|-------|---------|--------|
| `api_key` | `None` | Sent in the `api_key_header` header (HTTP mode) |
| `api_key_header` | `"X-API-Key"` | Header name for `api_key` |
| `username`, `password` | `None` | HTTP Basic auth, used when both are set (HTTP mode) |
| `bearer_token` | `None` | Sends `Authorization: Bearer <token>` (HTTP mode) |
| `cookies` | `{}` | Added to the session cookie jar without a domain, so they are sent to every host (HTTP mode) |
| `custom_headers` | `{}` | Added to every HTTP request, including robots.txt requests |
| `storage_state_path` | `None` | Playwright storage-state file loaded into each browser context |
| `oauth_client_id`, `oauth_client_secret`, `oauth_token_url`, `oauth_scopes`, `oauth_access_token`, `oauth_refresh_token` | `None` or `[]` | Not used by the fetcher |

`AuthConfig.to_dict()` reports which credentials are set without including their values.

## Result objects

### FetchResult

| Attribute | Contents |
|-----------|----------|
| `success` | HTTP mode: `True` for status codes below 400, including 304. Browser mode: `True` when navigation completed, whatever the status code |
| `metadata` | `FetchMetadata` (below) |
| `text` | Extracted main text |
| `html` | Decoded response body (HTTP mode) or rendered DOM (browser mode) |
| `content` | Raw response bytes after the `max_content_size` cut (HTTP mode only) |
| `links` | Absolute link URLs |
| `images` | Dicts with `src`, `alt`, and optional `width` and `height` |
| `metadata_extracted` | Page metadata from `HTMLParser` |
| `screenshot` | Full-page PNG bytes (browser mode only) |
| `trace` | Playwright trace archive as zip bytes (browser mode only) |
| `chunks` | Always empty. Reserved for future use |
| `content_hash` | Property: SHA-256 hex digest of `text`, or of `content` when there is no text |
| `to_dict()` | Dict of the fields above, without `content`, `screenshot`, and `trace` |

### FetchMetadata

- Set in HTTP mode: `source_url`, `final_url`, `status_code`, `content_type`, `content_encoding`, `content_length`, `encoding`, `etag`, `last_modified`, `headers`, `fetch_mode`, `trace_id`, `timestamp` (UTC), and `duration_ms`.
- Set in browser mode: `source_url`, `final_url`, `status_code`, `content_type` (always `"text/html"`), `fetch_mode`, `trace_id`, `timestamp`, and `duration_ms`.
- Set on failure: `error_message`, and `robots_verdict="disallow"` when robots.txt blocks the URL.
- Defined but never set: `canonical_url`, `locale`, `redirect_count`, `retry_count`, `policy_verdict`, `span_id`, `warnings`, and `cookies`.
- `to_dict()` returns every field, with `timestamp` as an ISO 8601 string.

## Safety and limits

This section describes what the current code does, including its gaps.

### URL and SSRF checks

`fetch()` checks only the URL it is given, in this order:

1. `SSRFValidator.validate()`:
   - The URL must pass `validators.url()`.
   - The scheme must be in `PolicyConfig.allowed_schemes` (`http` and `https` by default).
   - When `block_private_ips` is true (the default), the hostname is resolved with `socket.getaddrinfo(..., AF_INET)`. The fetch is refused if the name has no IPv4 address, or if any address is in 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 127.0.0.0/8, 0.0.0.0/8, 169.254.0.0/16, 224.0.0.0/4, or 240.0.0.0/4.
2. `PolicyEngine.check_url()` applies `allowed_schemes`, `require_https`, `blocked_domains`, and `allowed_domains`. For URLs with an explicit port, it also applies `blocked_ports` and `allowed_ports` (80 and 443 by default).
   - Domain rules match the URL's hostname: lowercased, without userinfo or port, and without a trailing dot. List entries are normalized the same way, and each entry also matches its subdomains. So `blocked_domains=["blocked.example"]` refuses `https://blocked.example:443/`, `https://user@blocked.example/`, and `https://Sub.Blocked.Example./`, and `allowed_domains=["example.com"]` allows `https://example.com:443/`.
   - A URL whose authority (the `user@host:port` part) contains a backslash is refused. Python's `urlparse` reads `https://evil.example\@allowed.example/` as host `allowed.example`, but `requests` connects to `evil.example`.

Not covered:

- Redirects. `requests` follows them without repeating these checks, so a public URL that redirects to an internal address is still fetched.
- IPv6. Only IPv4 (A) records are checked. A host's IPv6 addresses are never checked.
- DNS rebinding. The hostname is resolved again when the connection is made, and the checked address is not pinned.
- Browser mode after the first URL. Chromium follows redirects and loads scripts, images, frames, and other requests without these checks.
- Other non-public ranges, such as 100.64.0.0/10.

### robots.txt

- On by default. robots.txt is fetched with the same session, so it carries the session's headers and credentials (but not `extra_headers`).
- A 404 response, or any network error, means the fetch is allowed (fail-open). Other status codes are parsed as if the body were robots.txt, which usually also means allowed.
- `Disallow` and `Allow` paths are matched as prefixes. There is no support for wildcards (`*`, `$`) and no longest-match precedence. The first matching `Disallow` blocks the URL.
- The verdict is cached per scheme and host for the life of the `WebFetcher` (`robots_cache_ttl` is not used).

### Privacy and data handling

- There is no PII detection, no redaction, and no logging of any kind.
- `FetchResult` keeps all response headers (`metadata.headers`), the decoded body (`html`), and the raw bytes (`content`).
- Browser mode records a Playwright trace, including screenshots and DOM snapshots, for every fetch. The trace is written to `/tmp/trace-<trace_id>.zip` and is never deleted. Each fetch also captures a full-page screenshot.
- `AuthConfig` credentials are set on the shared session. They are sent with every request the `WebFetcher` makes, including robots.txt requests and requests to other hosts. `AuthConfig.cookies` are added without a domain, so they also go to every host.
- The library does not read secrets from environment variables or secret managers. Pass them in yourself.

### TLS

- Certificate verification is left at the `requests` and Playwright defaults, which verify certificates. There is no setting to change this.

### Other limits

- The fetch path is synchronous. `fetch_batch()` and `MultiURLFetcher.fetch_all()` fetch one URL at a time, and the `max_concurrent` argument of `fetch_batch()` is ignored. `MultiURLFetcher.fetch_all_async()` runs the synchronous fetch in a thread pool.
- There is no response streaming. Bodies are read fully into memory before `max_content_size` is applied, and no warning is recorded when a body is cut.
- `max_redirects` is not applied. `requests` allows up to 30 redirects.
- In HTTP mode, bodies are decoded with the encoding that `requests` reports for the response, or UTF-8 when it reports none. There is no charset detection.
- Browser mode uses Playwright's sync API. It cannot run inside an active asyncio event loop (for example, a Jupyter notebook cell) and must not be shared across threads.

## Known issues

1. When browser navigation fails (including on timeout), the result has `success=False`, but `metadata.error_message` is empty. The error text from `BrowserClient.fetch()` is dropped.
2. The robots.txt cache is keyed by host but stores the verdict for the first path checked on that host. Later URLs on the same host reuse that verdict, whatever their path.
3. The robots.txt parser never resets user-agent groups, so once a `User-agent: *` line has been read, the rules of later groups also apply. Agent names are compared case-sensitively against lowercased lines, so an agent-specific group matches only if the part of `user_agent` before the first `/` is lowercase.
4. `WebFetchLoader` reads `language` from `metadata_extracted`, which `HTMLParser` does not fill, so the document's `language` is usually `None`. Its `extract_metadata` argument is accepted but ignored.

## Roadmap (not implemented yet)

### Fetching, parsing, and URL safety

- `HEAD` requests and response streaming
- Enforcing `max_redirects`
- SSRF checks on every redirect, IPv6 address checks, and DNS-rebinding protection by pinning the checked address
- Per-host concurrency limits, rate limiting, and backpressure. `per_host_concurrency`, `rate_limit_requests`, and `rate_limit_period` exist in `PolicyConfig` but are not used
- Circuit breakers
- OAuth 2.0. The `oauth_*` fields in `AuthConfig` are not used
- HTTP and SOCKS proxy support in HTTP mode. Browser mode already accepts `PolicyConfig.proxy_url`
- Content-type allow and block lists. `allowed_content_types` and `blocked_content_types` are not used
- JSON and XML response parsing
- PDF extraction with OCR fallback, and image OCR. `pypdf`, `pdfplumber`, `pytesseract`, and `Pillow` are declared but not used
- Character-encoding detection
- Structured metadata beyond Open Graph, Twitter cards, and JSON-LD, such as microdata and RDFa
- Locale negotiation and hreflang awareness. Today a fixed `Accept-Language` header is sent
- URL canonicalization and deduplication across fetches. `metadata.canonical_url` is never set

### Privacy, security, and operations

- Data minimization and privacy by default
- PII detection and log redaction
- Encryption at rest and secret-manager integration
- GDPR and CCPA support (data access, deletion, and portability)
- Consent records and policy evidence
- Legal takedown workflows and configurable retention controls
- Structured logs, metrics, audit trails, and end-to-end OpenTelemetry tracing
- Health checks and graceful shutdown beyond `close()`
- Container isolation and resource limits
- CI/CD, threat modeling, fuzzing, and security testing
- Cost estimation and quota accounting

### Crawling, integrations, and interfaces

- Sitemap discovery and parsing
- Frontier prioritization for crawling. Link extraction itself is implemented
- Concurrent batching and crawl job orchestration. A `CrawlJob` model exists in `core/models.py` but is not used
- Pagination helpers
- Custom wait strategies and event-stream support. Today only Playwright's `wait_until` states are available
- HAR capture and replay or debug assets. Browser mode already captures Playwright traces and screenshots
- Challenge detection with authorized human-in-the-loop escalation
- Accessibility-preserving extraction
- Chunking and summarization hooks for LLMs. `FetchResult.chunks` is always empty
- Keyword and vector index integration
- Pluggable artifact, metadata, and cache backends. `redis` and `sqlalchemy` are declared but not used
- Scheduling, webhooks, and event-driven triggers
- A REST API and a gRPC interface for internal high-throughput workflows

## Project layout

```text
webfetch_tool/
  pyproject.toml                    package metadata and dependencies
  README.md                         this file
  examples/basic_usage.py           example script (basic fetch, policy, LangChain tool and loader)
  tests/                            pytest suite (domain rules, browser timeout)
  src/webfetch_tool/
    __init__.py                     exports WebFetcher, FetchConfig, PolicyConfig, AuthConfig,
                                    FetchResult, FetchMetadata
    core/fetcher.py                 WebFetcher
    core/config.py                  FetchConfig, PolicyConfig, AuthConfig
    core/policy.py                  PolicyEngine, PolicyVerdict
    core/auth.py                    AuthManager (helper; WebFetcher does not use it)
    core/models.py                  FetchResult, FetchMetadata, FetchMode, CrawlJob
    browser/playwright_client.py    BrowserClient
    parsers/html.py                 HTMLParser, ParsedContent
    security/ssrf.py                SSRFValidator, ValidationResult
    langchain/loader.py             WebFetchLoader
    langchain/tool.py               WebFetchTool, create_webfetch_tool
    langchain/multi_fetcher.py      MultiURLFetcher
```

The loader example in `examples/basic_usage.py` imports `langchain_text_splitters`, which is not a declared dependency.

## Development and tests

The `dev` extra installs pytest, pytest-asyncio, pytest-cov, black, ruff, and mypy. Their settings are in `pyproject.toml`. Run the tests from this directory:

```bash
pip install -e ".[dev]"
pytest
```

The tests need no network access and no browser. They cover:

- `tests/test_policy.py`: `PolicyEngine` domain rules with explicit ports, userinfo (including `https://allowed.example@evil.example/`), subdomains and lookalike hosts, letter case and trailing dots in URLs and in list entries, and a backslash in the authority. One test runs `WebFetcher.fetch()` to check that a blocked URL with `:443` is refused before any request is sent.
- `tests/test_browser_timeout.py`: with Playwright replaced by mocks, `browser_timeout` in seconds reaches `page.goto()` in milliseconds, including the 60-second default.

`pytest` also prints a coverage report (`--cov` in `addopts`). There is no CI configuration yet.

## License

MIT. See [LICENSE](../LICENSE) at the repository root.
