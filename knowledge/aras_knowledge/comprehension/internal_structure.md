---
category: comprehension
criterion: internal_structure
severity: medium
related:
  - internal_links
---

# Internal Content Structure

## Definition

Internal content structure concerns whether a page's organization can be inferred reliably from its own HTML — via sectioning elements, heading hierarchy, and landmark roles — rather than only from visual layout, and, at the ARAS evaluation level, whether the page exposes navigable internal content at all.

## Technical Background

Sectioning elements (`<article>`, `<section>`, `<nav>`, `<aside>`, `<main>`) and heading levels (`<h1>`–`<h6>`) are defined by the WHATWG HTML Living Standard; WAI-ARIA landmark roles reinforce the same structural concepts for assistive technology. A well-formed document maintains one `<h1>` and a non-skipping heading hierarchy within each sectioning context.

## Importance for AI Agent Readiness

Semantic structure lets an agent navigate directly to the relevant region of a page (main content vs. navigation vs. sidebar) without relying on visual heuristics, and lets it build an accurate outline of topics and subtopics from heading hierarchy alone.

## ARAS Evaluation Context

ARAS checks: `evidence.internal_links` (used as the concrete, evidence-backed proxy for navigable internal content organization).

Passed when: `internal_links` is non-empty.

Failure condition: `internal_links` is empty.

Failure message: "No internal content structure found"

## Common Issues

- Content structured almost entirely with generic `<div>` elements ("div soup") rather than semantic sectioning elements.
- Skipped heading levels (e.g., `<h1>` followed directly by `<h3>`) breaking outline continuity.
- More than one `<main>` element per page, or none at all.
- No navigable internal links at all, isolating the page from the rest of the site's content graph.

## Impact

- **Technical impact**: assistive technology and structural parsers cannot reliably jump to relevant regions.
- **AI agent impact**: an agent must infer structure heuristically rather than reading it directly from markup, and — per the concrete ARAS check — cannot navigate to related content at all if no internal links exist.
- **Security impact**: none directly.

## Recommendation Strategy

Add internal links so agents can navigate content organization: ensure the page links to related content within the site, and adopt semantic sectioning elements (`<main>`, `<article>`, `<nav>`) with a consistent, non-skipping heading hierarchy.

## Implementation Guidance

- **Any stack**: replace generic wrapper `<div>` elements with appropriate sectioning elements (`<main>`, `<article>`, `<section>`, `<nav>`, `<aside>`) where they convey real structural meaning.
- **Component frameworks (React, Vue)**: define shared layout components that consistently emit `<main>`/`<nav>`/`<footer>` rather than ad hoc divs per page.
- **Content editors**: enforce heading-level discipline (no skipped levels) via linting or editorial style guides.

## Validation Checklist

- Exactly one `<main>` element per page (excluding sitewide repeated content).
- Heading hierarchy has no skipped levels within any sectioning context.
- Internal links to related content are present and functional.
- Landmark roles (native or ARIA) correctly identify navigation, main content, and complementary regions.

## Related ARAS Criteria

- `internal_links` — the Discoverability-dimension counterpart evaluating the same underlying evidence for crawl-graph traversal rather than semantic organization.

## References

Source: official_sources/comprehension/internal_structure_reference.md
