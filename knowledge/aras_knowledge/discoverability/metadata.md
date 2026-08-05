---
category: discoverability
criterion: metadata
severity: medium
related:
  - open_graph
  - api_discoverability
---

# Discovery Metadata (Title, Meta Description, Canonical)

## Definition

Discovery metadata is the set of `<head>` elements — `<title>`, `<meta name="description">`, and `<link rel="canonical">` — that let a crawler or agent identify a page's title, summary, and preferred URL before any deeper content analysis.

## Technical Background

`<title>` is a required HTML element. `<meta name="description">` is a widely adopted convention providing a free-text summary. `<link rel="canonical" href="...">` (RFC 6596) declares which URL should be treated as authoritative among duplicate or near-duplicate variants (tracking parameters, protocol/host differences).

## Importance for AI Agent Readiness

These three fields are the minimum viable identity signal for a page. Without them, an agent has no reliable, low-cost way to know what a page is about or which URL to treat as the canonical reference when the same content is reachable through multiple paths — increasing the risk of duplicate processing or citing an unstable URL.

## ARAS Evaluation Context

ARAS checks: `evidence.title`, `evidence.meta_tags["description"]`, `evidence.canonical`.

Passed when: title is non-empty AND meta description is non-empty AND canonical is non-empty.

Failure condition: any of the three is missing.

Failure message: `"Missing metadata: {comma-separated list of missing fields}"` (fields: `title`, `meta description`, `canonical URL`).

## Common Issues

- `<title>` present but generic/duplicated across many pages (e.g., the site name only).
- Meta description entirely absent, or duplicated verbatim across unrelated pages.
- No canonical tag on pages reachable via multiple URL variants (query parameters, trailing slash, HTTP/HTTPS).
- Canonical tag present but pointing to a non-200 or redirected target.

## Impact

- **Technical impact**: search engines and agents may select an unintended canonical version, splitting ranking/attention signals across duplicate URLs.
- **AI agent impact**: without a title/description, an agent must parse full page content just to determine relevance, increasing processing cost per page.
- **Security impact**: none directly.

## Recommendation Strategy

Add the missing metadata fields identified by the evaluation: ensure every page declares a unique, descriptive `<title>`, a concise `<meta name="description">`, and a `<link rel="canonical">` pointing to its preferred URL.

## Implementation Guidance

- **Templating (any stack)**: derive `<title>` and description from the same content fields already used for the page (CMS title/excerpt), avoiding hardcoded duplicates.
- **Next.js / React**: use the framework's head-management utilities (e.g., `next/head` or the Metadata API) to set per-page values.
- **Express / FastAPI**: set these fields from server-side templating context per route.
- **Canonical at scale**: default every page to a self-referential canonical unless it is a known duplicate, in which case point explicitly to the preferred variant.

## Validation Checklist

- Each page has exactly one `<title>`, non-empty and distinct from other pages' titles.
- `<meta name="description">` present with meaningful, page-specific content.
- `<link rel="canonical">` present and resolves to a 200 response.
- No conflicting canonical declarations between HTML and any `Link` HTTP header.

## Related ARAS Criteria

- `open_graph` — overlapping identity metadata used for social/preview rendering.
- `api_discoverability` — a separate discovery signal for machine-readable API surfaces rather than page identity.

## References

Source: official_sources/discoverability/metadata_reference.md
