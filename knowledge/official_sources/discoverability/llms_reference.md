# llms.txt Convention

## Overview

`llms.txt` is a proposed convention for publishing a concise, curated, Markdown-formatted index of a website's most important content, intended to be consumed by large language models and AI agents operating under limited context budgets. It is modeled structurally on `robots.txt` (a well-known file at a fixed root path) but serves an entirely different purpose: content curation for AI consumption rather than crawl permission.

## Official Definition

The convention was proposed by Jeremy Howard (Answer.AI) in September 2024 and is maintained as a community specification at `llmstxt.org`. It is not an IETF, W3C, or WHATWG standard; it has no formal governance body and is not universally adopted by AI providers, but it has gained voluntary adoption among developer tools, documentation platforms, and AI-focused companies.

## Core Concepts

- **Curated, not exhaustive**: unlike a sitemap, `llms.txt` intentionally lists only the highest-value pages, prioritized by the publisher rather than enumerated completely.
- **Markdown format**: the file is a plain Markdown document, human-readable and directly usable as LLM context without additional parsing.
- **Structured sections**: convention specifies an H1 title, a blockquote summary, and H2-delimited link sections.
- **Companion `llms-full.txt`**: an optional, more exhaustive variant that concatenates full page content rather than only links, for models with larger context windows.

## Technical Details

- Location: served at `/llms.txt` at the site root, `Content-Type` typically `text/markdown` or `text/plain`.
- Required structure per the specification: an H1 with the project/site name; an immediately following blockquote (`>`) with a short summary; optional free-text paragraphs; zero or more H2 sections, each containing a Markdown list of links in the form `[name](url): optional description`; an optional final H2 section (conventionally named "Optional") for lower-priority links that may be omitted under tighter context constraints.
- No enforced size limit; the convention explicitly favors conciseness over completeness.

## Detection Characteristics

- File reachable at `/llms.txt` returning HTTP 200 with Markdown content.
- Presence of an H1 heading followed by a blockquote summary line.
- One or more `## ` (H2) sections containing Markdown-formatted link lists.
- Optionally accompanied by a sibling `/llms-full.txt` file.

## Common Implementations

- Adopted primarily by API/SDK documentation sites, developer tool vendors, and technical product sites.
- Often auto-generated from existing documentation navigation structures (e.g., exported from a docs-as-code pipeline).
- Frequently grouped into sections such as "Docs", "API Reference", "Guides", and "Examples".

## Limitations

- Not yet supported natively by major LLM providers as an automatic retrieval mechanism at the time of writing; adoption is voluntary on both the publishing and consuming sides.
- No validation schema or conformance checker is formally standardized.
- Risk of staleness: because it is manually curated, it can drift out of sync with actual site structure faster than an auto-generated sitemap.
- No authentication or integrity mechanism; content cannot be cryptographically verified as authoritative.

## Related Technologies

- Robots Exclusion Protocol (`robots.txt`), structurally analogous but functionally unrelated (permissions vs. curation)
- Sitemaps protocol, an exhaustive machine-oriented alternative
- Markdown (CommonMark), the underlying document format

## Official References

- llmstxt.org, "The /llms.txt file" specification
- Answer.AI, original proposal by Jeremy Howard (September 2024)
