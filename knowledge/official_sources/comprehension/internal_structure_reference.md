# Internal Content Structure (Semantic HTML and Document Outline)

## Overview

Internal content structure concerns how a page's own HTML organizes its content into a machine-parseable hierarchy — through sectioning elements, heading levels, and landmark roles — independent of any external metadata or structured-data markup. It determines whether a document's organization (what is a heading, what is a navigation region, what is the main content) can be inferred reliably from markup rather than visual layout alone.

## Official Definition

The relevant elements are defined by the WHATWG HTML Living Standard's sections on "Sections" and "Grouping content": sectioning elements (`<article>`, `<section>`, `<nav>`, `<aside>`), heading elements (`<h1>`–`<h6>`), and the broader semantics of landmark-conveying elements are further reinforced by the WAI-ARIA specification's landmark roles, which formalize the accessibility-facing equivalent of the same structural concepts.

## Core Concepts

- **Sectioning content**: `<article>`, `<section>`, `<nav>`, `<aside>` define nested regions of a document, each of which can have its own heading hierarchy and outline.
- **Heading hierarchy**: `<h1>`–`<h6>` establish a nested outline of topics and subtopics; the HTML Living Standard's algorithm for generating a document outline derives structure from heading levels combined with sectioning boundaries.
- **Landmark roles**: implicit ARIA roles (e.g., `<nav>` implies `role="navigation"`, `<main>` implies `role="main"`) allow assistive technology and other structural parsers to jump directly to a named region without relying on visual position.
- **Semantic vs. presentational elements**: the distinction between elements chosen for their structural meaning (`<article>`) versus purely presentational grouping (`<div>`, `<span>`) is the central quality signal for this criterion.

## Technical Details

- `<main>` identifies the dominant content of the document, and per the specification should appear at most once per page, excluding content repeated across pages (navigation, headers, footers, sitewide banners).
- Each `<article>` or `<section>` may define its own local heading hierarchy; the HTML outline algorithm effectively "restarts" heading context within nested sectioning content.
- ARIA landmark roles complementing native HTML semantics include `banner`, `navigation`, `main`, `complementary`, `contentinfo`, and `search`.
- Skipped heading levels (e.g., an `<h1>` followed directly by an `<h3>`) are syntactically valid but violate the structural intent of a strictly nested outline.

## Detection Characteristics

- Presence and count of sectioning elements (`<main>`, `<article>`, `<section>`, `<nav>`, `<aside>`) relative to generic `<div>` usage.
- Heading hierarchy well-formedness: presence of exactly one `<h1>`, and absence of skipped levels within a given sectioning context.
- Presence of explicit or implicit ARIA landmark roles.
- Ratio of semantic elements to non-semantic wrapper elements ("div soup") as a coarse structural-quality signal.

## Common Implementations

- Modern component-based frontend frameworks generating semantic wrapper elements (`<main>`, `<article>`) around templated content blocks.
- CMS themes with a fixed page skeleton (`<header>`, `<nav>`, `<main>`, `<aside>`, `<footer>`) populated per page.
- Documentation and publishing platforms enforcing strict heading-level discipline via linting or style guides.

## Limitations

- Structural markup does not itself convey topical meaning; two identically well-structured pages can differ arbitrarily in content quality.
- Legacy or heavily componentized codebases frequently degrade into non-semantic `<div>`-based structure despite functioning correctly, since browsers apply no rendering penalty for semantically empty markup.
- No formal validator enforces heading-level continuity or landmark uniqueness as hard errors; violations are conventionally treated as warnings by accessibility and structural linters, not blocking errors.

## Related Technologies

- WAI-ARIA landmark roles (the accessibility-facing parallel structure model)
- Schema.org `BreadcrumbList` and `WebPage` (structured-data representations of page organization, distinct from raw HTML structure)
- HTML outline algorithm (formal specification for deriving a document's heading-based outline)

## Official References

- WHATWG HTML Living Standard, "Sections" (article, section, nav, aside, main)
- WHATWG HTML Living Standard, "Headings and outlines"
- W3C Recommendation, "Accessible Rich Internet Applications (WAI-ARIA) 1.2" — Landmark Roles
