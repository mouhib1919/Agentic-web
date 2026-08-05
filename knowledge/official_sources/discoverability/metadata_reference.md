# Discovery Metadata (Title, Meta Description, Canonical Link)

## Overview

Discovery metadata refers to the small set of HTML `<head>` elements that a crawler or agent reads before deciding whether, and how, to represent a page in an index or a candidate list: the document title, the meta description, and the canonical link. These elements do not affect rendering; they exist specifically to communicate identity and preferred-URL information to automated consumers.

## Official Definition

- `<title>` is defined in the WHATWG HTML Living Standard as a required metadata element giving the document's title, used by user agents in window/tab titles, history, and bookmarks.
- `<meta name="description">` is a non-standardized but universally supported convention (documented by major search engines, not formally part of the HTML specification's required elements) providing a short summary of page content.
- `<link rel="canonical">` is defined in RFC 6596, "The Canonical Link Relation," specifying the preferred URL among a set of duplicate or near-duplicate pages.

## Core Concepts

- **Title**: a single, required, plain-text element; the HTML specification requires exactly one `<title>` per document with a head element.
- **Meta description**: a free-text `content` attribute value, not length-constrained by any specification, though search engines truncate displayed snippets in practice.
- **Canonical**: establishes a one-directional preference relationship — a page declares which URL should be treated as authoritative when multiple URLs serve equivalent or near-equivalent content (e.g., with tracking parameters, session IDs, or protocol/host variants).

## Technical Details

- `<title>` syntax: `<title>Text content</title>`, must appear within `<head>`, text content only (no nested elements).
- Meta description syntax: `<meta name="description" content="...">`, a single `<meta>` element with `name` and `content` attributes.
- Canonical syntax: `<link rel="canonical" href="https://example.com/preferred-url">`, `href` must be an absolute or resolvable URL; RFC 6596 permits cross-domain canonicalization.
- Canonical signals can also be communicated via the `Link` HTTP response header (`Link: <url>; rel="canonical"`) for non-HTML resources such as PDFs.

## Detection Characteristics

- Presence and content of `<title>` in the parsed `<head>`.
- Presence and `content` attribute value of `<meta name="description">`.
- Presence and `href` value of `<link rel="canonical">`, and whether it resolves to a distinct or self-referential URL.
- Multiple conflicting canonical declarations (e.g., one in HTML, a different one in the HTTP header) are a detectable inconsistency.

## Common Implementations

- Server-side or static-site-generator templating that injects per-page title/description from CMS fields or frontmatter.
- Self-referential canonical tags applied uniformly across a site as a default duplicate-content safeguard.
- Dynamic canonical resolution for paginated, filtered, or parameterized URL variants pointing back to a single base URL.

## Limitations

- None of these elements are enforced; a crawler may disregard a canonical declaration if it contradicts other signals (redirects, sitemap entries, internal linking patterns).
- Meta description length has no hard limit but is unofficially bounded by rendering/truncation behavior in consuming interfaces.
- Canonical declarations pointing to non-indexable (blocked, non-200, or noindex) targets create ambiguous signals.

## Related Technologies

- Open Graph and Twitter Card meta tags (social-sharing metadata, distinct purpose)
- `<meta name="robots">` and `X-Robots-Tag` (indexing control, separate from identity metadata)
- HTTP `Link` header (canonical signaling for non-HTML resources)

## Official References

- WHATWG HTML Living Standard, "The title element"
- IETF RFC 6596, "The Canonical Link Relation"
- Google Search Central, "Meta tags that Google understands"
