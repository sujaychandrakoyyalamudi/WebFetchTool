# WebFetchTool

WebFetchTool is a Python library for LLM applications that checks a URL against configurable safety rules and robots.txt, fetches it over HTTP or with headless Chromium, and returns the extracted text with fetch metadata.

## What it does

`WebFetcher.fetch(url)` runs these steps and returns a `FetchResult`:

1. `SSRFValidator` checks the URL format and scheme. By default it also resolves the hostname to IPv4 addresses and refuses private, loopback, link-local, multicast, and reserved ranges.
2. `PolicyEngine` applies the scheme, HTTPS-only, domain allow and block list, and port rules from `PolicyConfig`.
3. robots.txt is checked (on by default).
4. The page is fetched with `requests`, or rendered in headless Chromium through Playwright when `use_browser` is set.
5. `HTMLParser` extracts the main text, links, images, and page metadata.

Validation, policy, robots.txt, and network failures come back in the result instead of being raised. Check `result.success` and `result.metadata.error_message`. The `webfetch_tool.langchain` package wraps the fetcher as a LangChain document loader and a LangChain tool.

## Features

- HTTP fetching through one pooled `requests.Session` per `WebFetcher`, with connect and read timeouts, redirect following, and custom headers.
- Retries through urllib3 `Retry`, restricted to `GET` and `HEAD`, with exponential backoff. Responses with status 429, 500, 502, 503, or 504 are retried by default, and `Retry-After` is honored.
- Conditional requests: pass `etag` or `last_modified` to `fetch()`. A 304 response comes back as a successful result with no body.
- Browser mode: headless Chromium through Playwright, a new browser context per fetch, an optional Playwright storage-state file, a full-page screenshot, and a Playwright trace.
- URL rules: scheme allowlist, HTTPS-only option, domain allow and block lists matched on the hostname (subdomains included), port allow and block lists, and blocking of private IPv4 ranges.
- robots.txt checking, on by default, with a simplified parser. See [Safety and limits](#safety-and-limits).
- HTML extraction: main text with readability-lxml, absolute links with exact duplicates removed, images, `<meta>` tags, Open Graph, Twitter card tags, and JSON-LD.
- Authentication in HTTP mode: API key header, HTTP Basic, Bearer token, cookies, and custom headers.
- Fetch metadata: source and final URL, status code, content type, `ETag`, `Last-Modified`, response headers, UTC timestamp, duration, a per-fetch `trace_id`, and a SHA-256 `content_hash`.
- LangChain: `WebFetchLoader` (returns `Document` objects), `WebFetchTool` and `create_webfetch_tool()`, and `MultiURLFetcher`.

## Install

Version 0.1.0 (alpha) is not on PyPI. Install it from GitHub (Python 3.9 or later):

```bash
pip install "git+https://github.com/sujaychandrakoyyalamudi/WebFetchTool.git#subdirectory=webfetch_tool"
```

The distribution name is `webfetch-tool` and the import name is `webfetch_tool`. Every dependency in `pyproject.toml` is required, including Playwright and LangChain.

Browser mode also needs the Chromium build that Playwright drives:

```bash
playwright install chromium
```

To work on the code, install from a clone with the `dev` extra:

```bash
git clone https://github.com/sujaychandrakoyyalamudi/WebFetchTool.git
cd WebFetchTool/webfetch_tool
pip install -e ".[dev]"
```

## Quick start

```python
from webfetch_tool import WebFetcher

with WebFetcher() as fetcher:
    result = fetcher.fetch("https://example.com")

if result.success:
    print(result.metadata.final_url, result.metadata_extracted.get("title"))
    print(result.text)
else:
    print(result.metadata.status_code, result.metadata.error_message)
```

Browser mode, saving the screenshot:

```python
from webfetch_tool import FetchConfig, WebFetcher

# browser_timeout is the navigation timeout in seconds (default 60).
config = FetchConfig(use_browser=True, browser_timeout=30)

with WebFetcher(config=config) as fetcher:
    result = fetcher.fetch("https://example.com")

if result.screenshot:
    with open("page.png", "wb") as f:
        f.write(result.screenshot)
```

LangChain document loader and tool:

```python
from webfetch_tool.langchain import WebFetchLoader, create_webfetch_tool

loader = WebFetchLoader(urls=["https://example.com"], extract_links=True)
for doc in loader.load():
    print(doc.metadata["source"], doc.page_content[:80])

tool = create_webfetch_tool(name="web_fetch", description="Fetch the text of a web page.")
print(tool.invoke({"url": "https://example.com"}))
```

The [detailed reference](webfetch_tool/README.md#quick-start) has examples for policy settings, authentication, conditional requests, and batch fetching.

## Safety and limits

- SSRF checks apply only to the URL passed to `fetch()`. Its hostname is resolved to IPv4 addresses, and the fetch is refused if any address is in 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 127.0.0.0/8, 0.0.0.0/8, 169.254.0.0/16, 224.0.0.0/4, or 240.0.0.0/4. An explicit port must be 80 or 443 by default.
- Not covered by those checks: redirect targets (`requests` follows them unchecked), IPv6 addresses, DNS rebinding (the name is resolved again at connect time), and anything Chromium loads after the first URL in browser mode.
- Domain rules match the URL's hostname: lowercased, without userinfo or port, and without a trailing dot. List entries are normalized the same way and also match their subdomains, so `blocked_domains=["blocked.example"]` refuses `https://user@Sub.Blocked.Example:443/`. A URL whose authority (the `user@host:port` part) contains a backslash is refused, because Python's `urlparse` and `requests` disagree on which host it names.
- robots.txt is respected by default, with a simplified parser: prefix matching only and no wildcards. The fetch is allowed when robots.txt returns 404 or cannot be fetched. The verdict is cached per host for the life of the fetcher, and a known bug caches the verdict for the first path checked on that host.
- Privacy: there is no PII detection, redaction, or logging. Results keep the full response headers and the raw body. Browser mode writes a Playwright trace, with screenshots and DOM snapshots, to `/tmp/trace-<trace_id>.zip` on every fetch and never deletes it.
- Credentials in `AuthConfig` are set on the shared session. They are sent with every request that fetcher makes, including robots.txt requests and requests to other hosts.
- TLS certificate verification is left at the `requests` and Playwright defaults, which verify certificates.
- Bodies are read fully into memory and then cut to `max_content_size` (10 MB). `max_redirects` is not applied, so `requests` allows up to 30 redirects. `fetch_batch()` and `MultiURLFetcher.fetch_all()` fetch one URL at a time.

## Project layout

```text
LICENSE
README.md                          this overview
webfetch_tool/
  README.md                        detailed reference
  pyproject.toml                   package metadata and dependencies
  examples/basic_usage.py          example script
  tests/                           pytest suite (domain rules, browser timeout)
  src/webfetch_tool/
    core/fetcher.py                WebFetcher: URL checks, HTTP and browser fetch, parsing
    core/config.py                 FetchConfig, PolicyConfig, AuthConfig
    core/policy.py                 PolicyEngine: scheme, domain, and port rules
    core/auth.py                   AuthManager helper (not used by WebFetcher)
    core/models.py                 FetchResult, FetchMetadata
    browser/playwright_client.py   BrowserClient (Playwright, Chromium)
    parsers/html.py                HTMLParser (readability-lxml, BeautifulSoup)
    security/ssrf.py               SSRFValidator
    langchain/                     WebFetchLoader, WebFetchTool, MultiURLFetcher
```

## Tests

The tests in `webfetch_tool/tests/` cover the domain rules in `PolicyEngine` (explicit ports, userinfo, subdomains, letter case, and trailing dots) and check that `browser_timeout` reaches Playwright in milliseconds. They need no network access and no browser (Playwright is replaced with mocks). With the `dev` extra installed (see [Install](#install)), run them from `webfetch_tool/`:

```bash
pytest
```

The run also prints a coverage report. There is no CI configuration yet.

## Roadmap (not implemented yet)

- Parsing: JSON and XML responses (today every body goes through the HTML parser), PDF extraction with OCR fallback, and image OCR. `pypdf`, `pdfplumber`, `pytesseract`, and `Pillow` are declared dependencies but are not used.
- Fetching: `HEAD` requests, response streaming, an enforced `max_redirects`, OAuth 2.0 (the `oauth_*` fields in `AuthConfig` are not used), per-host concurrency limits, rate limiting, and backpressure.
- Security and privacy: SSRF checks on redirects and IPv6, DNS-rebinding protection, PII detection and log redaction, data minimization, encryption at rest, and secret-manager integration.
- Operations: structured logs, metrics, OpenTelemetry tracing, audit trails, health checks, graceful shutdown beyond `close()`, and a REST API.
- Crawling and integrations: URL canonicalization and deduplication across fetches, sitemaps, crawl frontier and job orchestration, circuit breakers, proxy support in HTTP mode, HAR capture, chunking hooks for LLMs, vector index integration, and pluggable cache and storage backends.

The [detailed reference](webfetch_tool/README.md#roadmap-not-implemented-yet) has the full list.

## License

MIT. See [LICENSE](LICENSE).

## Detailed reference

[webfetch_tool/README.md](webfetch_tool/README.md) covers every configuration field, the result objects, the full safety notes, known issues, and the complete roadmap.
