"""Data models for WebFetchTool."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class FetchMode(str, Enum):
    """Fetch mode enumeration."""

    HTTP = "http"
    BROWSER = "browser"
    HYBRID = "hybrid"


@dataclass
class FetchMetadata:
    """Metadata about a fetch operation."""

    source_url: str
    final_url: str
    canonical_url: Optional[str] = None
    fetch_mode: FetchMode = FetchMode.HTTP
    status_code: Optional[int] = None
    content_type: Optional[str] = None
    content_encoding: Optional[str] = None
    content_length: Optional[int] = None
    encoding: Optional[str] = None
    locale: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    duration_ms: Optional[float] = None
    redirect_count: int = 0
    retry_count: int = 0
    etag: Optional[str] = None
    last_modified: Optional[str] = None
    robots_verdict: Optional[str] = None
    policy_verdict: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    headers: Dict[str, str] = field(default_factory=dict)
    cookies: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source_url": self.source_url,
            "final_url": self.final_url,
            "canonical_url": self.canonical_url,
            "fetch_mode": self.fetch_mode.value,
            "status_code": self.status_code,
            "content_type": self.content_type,
            "content_encoding": self.content_encoding,
            "content_length": self.content_length,
            "encoding": self.encoding,
            "locale": self.locale,
            "timestamp": self.timestamp.isoformat(),
            "duration_ms": self.duration_ms,
            "redirect_count": self.redirect_count,
            "retry_count": self.retry_count,
            "etag": self.etag,
            "last_modified": self.last_modified,
            "robots_verdict": self.robots_verdict,
            "policy_verdict": self.policy_verdict,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "error_message": self.error_message,
            "warnings": self.warnings,
            "headers": self.headers,
            "cookies": self.cookies,
        }


@dataclass
class FetchResult:
    """Result of a fetch operation."""

    success: bool
    metadata: FetchMetadata
    text: Optional[str] = None
    html: Optional[str] = None
    content: Optional[bytes] = None
    links: List[str] = field(default_factory=list)
    images: List[Dict[str, str]] = field(default_factory=list)
    metadata_extracted: Dict[str, Any] = field(default_factory=dict)
    chunks: List[Dict[str, Any]] = field(default_factory=list)
    screenshot: Optional[bytes] = None
    trace: Optional[bytes] = None

    @property
    def content_hash(self) -> Optional[str]:
        """Calculate content hash."""
        if self.text:
            return hashlib.sha256(self.text.encode("utf-8")).hexdigest()
        elif self.content:
            return hashlib.sha256(self.content).hexdigest()
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "metadata": self.metadata.to_dict(),
            "text": self.text,
            "html": self.html,
            "links": self.links,
            "images": self.images,
            "metadata_extracted": self.metadata_extracted,
            "chunks": self.chunks,
            "content_hash": self.content_hash,
        }


@dataclass
class CrawlJob:
    """Represents a crawl job with multiple URLs."""

    job_id: str
    urls: List[str]
    status: str = "pending"
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    total_urls: int = 0
    fetched_urls: int = 0
    failed_urls: int = 0
    results: List[FetchResult] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "job_id": self.job_id,
            "urls": self.urls,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_urls": self.total_urls,
            "fetched_urls": self.fetched_urls,
            "failed_urls": self.failed_urls,
            "results": [r.to_dict() for r in self.results],
            "errors": self.errors,
        }
