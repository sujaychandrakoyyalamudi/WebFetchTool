"""browser_timeout is in seconds; Playwright receives milliseconds."""

from unittest.mock import MagicMock

import pytest

from webfetch_tool import FetchConfig, WebFetcher
from webfetch_tool.browser import playwright_client
from webfetch_tool.browser.playwright_client import BrowserClient


@pytest.fixture
def fake_page(monkeypatch):
    """Replace Playwright with mocks so no browser is launched; return the fake page."""
    page = MagicMock(name="page")
    page.url = "https://example.com/"
    page.content.return_value = "<html><body><p>Hello</p></body></html>"
    page.goto.return_value.status = 200

    playwright = MagicMock(name="playwright")
    browser = playwright.chromium.launch.return_value
    browser.new_context.return_value.new_page.return_value = page

    sync_playwright = MagicMock(name="sync_playwright")
    sync_playwright.return_value.start.return_value = playwright
    monkeypatch.setattr(playwright_client, "sync_playwright", sync_playwright)
    return page


@pytest.mark.parametrize("seconds, milliseconds", [(60, 60_000), (2.5, 2_500)])
def test_browser_client_converts_timeout_to_milliseconds(fake_page, seconds, milliseconds):
    with BrowserClient() as client:
        result = client.fetch("https://example.com/", timeout=seconds)

    assert result["success"]
    fake_page.goto.assert_called_once_with(
        "https://example.com/", wait_until="networkidle", timeout=milliseconds
    )


def test_default_fetch_config_gives_playwright_60_seconds(fake_page):
    # _fetch_browser is where WebFetcher hands config.browser_timeout to BrowserClient.
    # Calling it directly skips the DNS lookup, robots.txt request, and trace file of fetch().
    with WebFetcher(config=FetchConfig()) as fetcher:
        result = fetcher._fetch_browser("https://example.com/")

    assert result.success
    assert fake_page.goto.call_args.kwargs["timeout"] == 60_000
