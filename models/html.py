"""Data contract for the HTML Parser.

This module defines the single output type produced by the HTML
Parser: a flat, JSON-serializable snapshot of structural information
extracted from a raw HTML document. No scoring, grading, or
interpretation logic belongs here — this is a data container only.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Optional


@dataclass
class HtmlParseResult:
    """Structured information extracted from a single HTML document.

    This dataclass is the sole output of :class:`HtmlParser`. It never
    contains derived scores, judgments, or recommendations — only facts
    observed during parsing. Any field that could not be extracted is
    left at its default (None or an empty collection) rather than
    causing the whole parse to fail.

    Attributes:
        title: The document's <title> text.
        language: Value of the <html lang="..."> attribute.
        meta_tags: Mapping of `<meta name="...">` to its content.
        canonical: The resolved canonical URL, if declared.
        open_graph: Mapping of `<meta property="og:*">` to its content.
        robots_meta: Parsed content of `<meta name="robots">`.
        favicon: Absolute URL of the resolved favicon, if declared.
        internal_links: Absolute URLs linking to the same domain.
        external_links: Absolute URLs linking to other domains.
        javascript_files: Absolute URLs of `<script src="...">` resources.
        css_files: Absolute URLs of `<link rel="stylesheet">` resources.
    """

    title: Optional[str] = None
    language: Optional[str] = None
    meta_tags: dict[str, str] = field(default_factory=dict)
    canonical: Optional[str] = None
    open_graph: dict[str, str] = field(default_factory=dict)
    robots_meta: dict[str, Any] = field(default_factory=dict)
    favicon: Optional[str] = None
    internal_links: list[str] = field(default_factory=list)
    external_links: list[str] = field(default_factory=list)
    javascript_files: list[str] = field(default_factory=list)
    css_files: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert this parse result into a plain JSON-serializable dict.

        Returns:
            A dict representation suitable for `json.dumps`.
        """
        return asdict(self)
