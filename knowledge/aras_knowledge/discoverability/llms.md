---
category: discoverability
criterion: llms_txt
severity: low
related:
  - robots_txt
  - sitemap
---

# llms.txt

## Definition

`llms.txt` is a community-proposed convention (llmstxt.org) for publishing a curated, Markdown-formatted index of a site's most important content, intended specifically to be consumed by large language models and AI agents operating under limited context.

## Technical Background

The file is served at `/llms.txt` as plain Markdown: an H1 title, a blockquote summary, and one or more H2-delimited sections each listing links in `[name](url): description` format. Unlike a sitemap, it is deliberately curated and non-exhaustive, prioritizing the highest-value pages rather than enumerating every URL.

## Importance for AI Agent Readiness

`llms.txt` is the clearest available signal that a site has been explicitly optimized for AI agent consumption rather than only for human browsers or classic search crawlers. It gives an agent a fast, pre-summarized starting point instead of forcing it to infer site purpose and structure from raw HTML or a full crawl.

## ARAS Evaluation Context

ARAS checks: `evidence.llms_txt` (populated by the Evidence Collector only when `/llms.txt` returns HTTP 200).

Passed when: `llms_txt` is non-empty.

Failure condition: `llms_txt` is empty or `None`.

Failure message: "No llms.txt found"

## Common Issues

- File not published at all — still the most common state, since the convention is recent and not universally adopted.
- File present but written as marketing copy rather than a navigational index.
- File not updated after significant site restructuring, leaving stale links.
- Content duplicating the entire sitemap instead of a genuinely curated subset.

## Impact

- **Technical impact**: minimal on classic crawling; this file has no effect on traditional search indexing.
- **AI agent impact**: without it, an agent must derive site understanding from a full crawl or raw HTML parsing, which is slower and less reliable than a curated summary.
- **Security impact**: none.

## Recommendation Strategy

Add an llms.txt file to guide AI agents to key site content: a short site summary followed by grouped links to documentation, core product pages, and other high-value resources, kept concise rather than exhaustive.

## Implementation Guidance

- **Static hosting / Nginx**: serve as a plain static Markdown file at the site root, `Content-Type: text/markdown` or `text/plain`.
- **Documentation platforms**: many docs-as-code pipelines can export existing navigation structure directly into the required Markdown format.
- **FastAPI / Express**: serve via a static file route; regenerate the file as part of the deployment pipeline if content changes frequently.

## Validation Checklist

- `GET /llms.txt` returns HTTP 200.
- Content begins with an H1 title followed by a blockquote summary.
- At least one H2 section with a Markdown link list is present.
- Links resolve successfully and reflect current site structure.

## Related ARAS Criteria

- `robots_txt` — structurally analogous root-file convention, different purpose (permissions vs. curation).
- `sitemap` — the exhaustive machine-oriented counterpart to this curated, human/AI-readable index.

## References

Source: official_sources/discoverability/llms_reference.md
