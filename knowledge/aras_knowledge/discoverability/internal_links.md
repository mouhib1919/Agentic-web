---
category: discoverability
criterion: internal_links
severity: medium
related:
  - sitemap
  - internal_structure
---

# Internal Navigation Links

## Definition

Internal links are same-origin `<a href="...">` hyperlinks connecting pages within a website, forming the graph structure crawlers and agents traverse to discover content beyond the entry point they started from.

## Technical Background

Discovery via internal links depends on the hyperlinks being present in crawlable (typically server-rendered) HTML; links injected only via client-side JavaScript after initial render may be invisible to crawlers that do not execute JavaScript. Global navigation, breadcrumbs, and in-content links are all structurally equivalent `<a>` elements.

## Importance for AI Agent Readiness

Internal links are the fallback discovery mechanism when no sitemap is available, and remain relevant even with a sitemap since they provide contextual relationships (via anchor text and position) that a flat URL list does not. A homepage with no outbound internal links effectively traps an agent at the entry point.

## ARAS Evaluation Context

ARAS checks: `evidence.internal_links` (a list of same-origin URLs discovered on the homepage by the Evidence Collector).

Passed when: `internal_links` is non-empty.

Failure condition: `internal_links` is empty.

Failure message: "No internal navigation links found"

## Common Issues

- Homepage built as a single-page application shell with all navigation rendered client-side after JavaScript execution, leaving no server-rendered `<a href>` elements.
- Navigation implemented via non-anchor elements (e.g., `<div onclick>`) that are not valid hyperlinks and are invisible to crawlers.
- Homepage genuinely isolated, linking only to external domains or assets.

## Impact

- **Technical impact**: crawl depth beyond the homepage is severely limited or entirely blocked.
- **AI agent impact**: an agent cannot navigate beyond the entry point without a sitemap, effectively confining any content discovery to a single page.
- **Security impact**: none directly.

## Recommendation Strategy

Add internal links so agents can navigate beyond the homepage: ensure primary navigation, footer links, and key in-content references are rendered as genuine, server-visible `<a href>` elements rather than client-side-only interactive handlers.

## Implementation Guidance

- **Server-side rendering / Next.js**: use the framework's `<Link>` component, which renders a real `<a href>` in the initial HTML.
- **Single-page applications**: ensure critical navigation routes are also rendered server-side (SSR/SSG) rather than relying solely on client-side routing.
- **CMS themes**: verify navigation menus and footers are rendered as standard anchor tags, not JavaScript-only click handlers.

## Validation Checklist

- The homepage's raw HTML (before JavaScript execution) contains one or more same-origin `<a href>` elements.
- Primary navigation and footer links are present in server-rendered markup.
- No orphan pages exist that are unreachable from the homepage within a reasonable number of hops.

## Related ARAS Criteria

- `sitemap` — a declarative alternative/complement to link-graph discovery.
- `internal_structure` — the Comprehension-dimension counterpart evaluating semantic organization rather than raw link presence.

## References

Source: official_sources/discoverability/internal_links_reference.md
