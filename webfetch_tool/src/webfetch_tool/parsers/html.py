"""HTML parsing and content extraction."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from readability import Document as ReadabilityDocument


@dataclass
class ParsedContent:
    """Parsed HTML content."""

    text: str = ""
    html: str = ""
    title: str = ""
    links: List[str] = field(default_factory=list)
    images: List[Dict[str, str]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    language: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "text": self.text,
            "html": self.html,
            "title": self.title,
            "links": self.links,
            "images": self.images,
            "metadata": self.metadata,
            "language": self.language,
        }


class HTMLParser:
    """
    HTML parser for content extraction.
    
    Features:
    - Main content extraction using Readability
    - Link extraction
    - Image extraction
    - Metadata extraction (Open Graph, schema.org, etc.)
    - Language detection
    """

    def __init__(self):
        """Initialize HTML parser."""
        pass

    def parse(self, html: str, base_url: str = "") -> ParsedContent:
        """
        Parse HTML content.
        
        Args:
            html: Raw HTML content
            base_url: Base URL for resolving relative links
            
        Returns:
            ParsedContent with extracted content
        """
        soup = BeautifulSoup(html, "lxml")
        
        # Extract main content using Readability if available
        try:
            doc = ReadabilityDocument(html)
            title = doc.title()
            content_html = doc.summary()
            content_soup = BeautifulSoup(content_html, "lxml")
            text = content_soup.get_text(separator="\n", strip=True)
        except Exception:
            # Fallback to basic extraction
            title = soup.title.string if soup.title else ""
            # Remove script and style elements
            for element in soup(["script", "style", "noscript"]):
                element.decompose()
            text = soup.get_text(separator="\n", strip=True)
            content_html = str(soup.body) if soup.body else html
        
        # Extract links
        links = self._extract_links(soup, base_url)
        
        # Extract images
        images = self._extract_images(soup, base_url)
        
        # Extract metadata
        metadata = self._extract_metadata(soup)
        
        # Detect language
        language = self._detect_language(soup)
        
        return ParsedContent(
            text=text,
            html=content_html,
            title=title or "",
            links=links,
            images=images,
            metadata=metadata,
            language=language,
        )

    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract all links from page."""
        links = []
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"].strip()
            if href:
                # Resolve relative URLs
                absolute_url = urljoin(base_url, href)
                links.append(absolute_url)
        
        # Deduplicate while preserving order
        seen = set()
        unique_links = []
        for link in links:
            if link not in seen:
                seen.add(link)
                unique_links.append(link)
        
        return unique_links

    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """Extract all images from page."""
        images = []
        for img_tag in soup.find_all("img"):
            src = img_tag.get("src", "").strip()
            if not src:
                continue
            
            # Resolve relative URLs
            absolute_src = urljoin(base_url, src)
            
            image_data = {
                "src": absolute_src,
                "alt": img_tag.get("alt", ""),
            }
            
            # Add dimensions if present
            if img_tag.get("width"):
                image_data["width"] = img_tag["width"]
            if img_tag.get("height"):
                image_data["height"] = img_tag["height"]
            
            images.append(image_data)
        
        return images

    def _extract_metadata(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract metadata from page."""
        metadata = {}
        
        # Basic metadata
        if soup.title:
            metadata["title"] = soup.title.string
        
        # Meta tags
        for meta in soup.find_all("meta"):
            name = meta.get("name", "").lower()
            property_ = meta.get("property", "").lower()
            content = meta.get("content", "")
            
            if name:
                metadata[name] = content
            if property_:
                metadata[property_] = content
        
        # Open Graph
        og_metadata = {}
        for meta in soup.find_all("meta"):
            property_ = meta.get("property", "")
            if property_ and property_.startswith("og:"):
                key = property_[3:]  # Remove 'og:' prefix
                og_metadata[key] = meta.get("content", "")
        
        if og_metadata:
            metadata["open_graph"] = og_metadata
        
        # Twitter Cards
        twitter_metadata = {}
        for meta in soup.find_all("meta"):
            name = meta.get("name", "")
            if name and name.startswith("twitter:"):
                key = name[8:]  # Remove 'twitter:' prefix
                twitter_metadata[key] = meta.get("content", "")
        
        if twitter_metadata:
            metadata["twitter_card"] = twitter_metadata
        
        # Schema.org JSON-LD
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                import json
                schema_data = json.loads(script.string)
                if "schema" not in metadata:
                    metadata["schema"] = []
                metadata["schema"].append(schema_data)
            except (json.JSONDecodeError, TypeError):
                pass
        
        return metadata

    def _detect_language(self, soup: BeautifulSoup) -> Optional[str]:
        """Detect page language."""
        # Check html lang attribute
        html_tag = soup.find("html")
        if html_tag and html_tag.get("lang"):
            return html_tag["lang"]
        
        # Check meta tags
        for meta in soup.find_all("meta"):
            if meta.get("http-equiv", "").lower() == "content-language":
                return meta.get("content", "")
        
        return None
