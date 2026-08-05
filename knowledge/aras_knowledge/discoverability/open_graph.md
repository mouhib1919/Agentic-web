---
category: discoverability
criterion: open_graph
severity: medium
related:
  - metadata
---

# Open Graph Metadata (Discoverability)

## Definition

The Open Graph protocol (ogp.me) defines `<meta property="og:...">` tags that let a page describe itself as a structured object (title, type, image, URL) so external platforms and agents can render or reference it consistently without parsing full content.

## Technical Background

The base specification requires four properties for any object: `og:title`, `og:type`, `og:image`, `og:url`. Additional optional properties (`og:description`, `og:site_name`) extend the description. Tags are flat `<meta>` elements placed in `<head>`, requiring no complex parsing.

## Importance for AI Agent Readiness

Open Graph tags are among the most consistently deployed metadata on the modern web (driven by social-sharing requirements), making them a reliable fallback identity source for an agent even when richer structured data (JSON-LD/Schema.org) is absent from a page.

## ARAS Evaluation Context

ARAS checks: `evidence.open_graph` (a mapping of Open Graph property to value, populated by the Evidence Collector).

Passed when: `open_graph` is non-empty (at least one `og:` tag present).

Failure condition: `open_graph` is empty.

Failure message: "No Open Graph metadata found"

## Common Issues

- No Open Graph tags at all, common on utility/internal pages not designed for sharing.
- Only `og:title` present, missing `og:image` and `og:url`, producing an incomplete object description.
- `og:url` pointing to a different URL than the page's own canonical, creating conflicting identity signals.
- Relative rather than absolute URLs used for `og:image`/`og:url`, which some consumers fail to resolve correctly.

## Impact

- **Technical impact**: link previews on third-party platforms render incompletely or generically.
- **AI agent impact**: an agent loses a fast, reliable identity signal it could otherwise use without deeper page parsing.
- **Security impact**: none directly.

## Recommendation Strategy

Add Open Graph metadata (og:title, og:description, og:image, ...) to every page intended for discovery, populated from the same content fields already driving the page's title and description to avoid divergence.

## Implementation Guidance

- **Templating (any stack)**: generate Open Graph tags from the same source fields as `<title>`/meta description to keep them synchronized.
- **CMS platforms**: most modern CMS/e-commerce platforms auto-populate Open Graph tags from existing content fields; verify the feature is enabled.
- **Next.js**: the Metadata API supports `openGraph` fields directly in page metadata exports.

## Validation Checklist

- `og:title`, `og:type`, `og:image`, `og:url` all present with non-empty, absolute values.
- `og:url` matches (or intentionally aligns with) the page's canonical URL.
- `og:image` resolves to a valid, reasonably sized image.

## Related ARAS Criteria

- `metadata` — the base title/description/canonical signals Open Graph properties commonly mirror.

## References

Source: official_sources/discoverability/open_graph_reference.md
