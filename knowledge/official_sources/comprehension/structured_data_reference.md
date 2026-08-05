# Structured Data on the Web

## Overview

Structured data is machine-readable markup embedded in a web page that explicitly labels its content according to a shared vocabulary, so that a parser can extract typed facts (an entity's name, price, author, rating) rather than inferring them from unstructured prose or visual layout. It is the general umbrella term covering multiple concrete syntaxes — JSON-LD, Microdata, and RDFa — that all typically express the Schema.org vocabulary.

## Official Definition

Structured data, as commonly used in web contexts, is not itself a single specification but a category comprising three W3C-defined (or W3C-adjacent) encoding syntaxes — JSON-LD (W3C Recommendation), Microdata (originally part of the WHATWG HTML specification, now a separate W3C Working Group Note), and RDFa (W3C Recommendation) — combined with an external vocabulary, most commonly Schema.org, that defines the actual types and properties available for use.

## Core Concepts

- **Syntax vs. vocabulary**: the encoding format (JSON-LD, Microdata, RDFa) is independent of the vocabulary (typically Schema.org) used within it; the same Schema.org `Product` type can be expressed in any of the three syntaxes.
- **Entities and properties**: structured data describes one or more typed entities, each with a set of named properties whose values may be literals, other nested entities, or references.
- **Linked data model**: JSON-LD and RDFa are both grounded in the RDF (Resource Description Framework) data model, representing information as subject-predicate-object triples, even though JSON-LD's surface syntax resembles plain JSON.
- **Embedding location**: structured data lives alongside, not instead of, the human-visible content — it is additive markup, not a replacement rendering.

## Technical Details

- JSON-LD: a `<script type="application/ld+json">` block containing a JSON object with `@context` and `@type` keys.
- Microdata: HTML attributes (`itemscope`, `itemtype`, `itemprop`) applied directly to visible elements, tying the markup to the DOM structure that renders it.
- RDFa: HTML attributes (`vocab`, `typeof`, `property`) similarly applied to existing elements, using a more general RDF-attribute vocabulary than Microdata's.
- All three can co-exist on the same page describing the same or different entities, though most implementations standardize on a single syntax (JSON-LD is the most commonly recommended by search engines as of current guidance).

## Detection Characteristics

- One or more `<script type="application/ld+json">` blocks parseable as JSON.
- HTML elements carrying `itemscope`/`itemtype`/`itemprop` attributes (Microdata).
- HTML elements carrying `typeof`/`property`/`vocab` attributes (RDFa).
- Presence of a recognized `@type` (JSON-LD) or `itemtype`/`typeof` value (Microdata/RDFa) resolving to a known vocabulary, most commonly a `schema.org` URL.

## Common Implementations

- CMS plugins and e-commerce platforms auto-generating JSON-LD from product, article, or organization data already stored in the system.
- Server-side templating injecting Microdata attributes directly into existing visible markup (avoiding duplication of content).
- Static site generators embedding JSON-LD at build time from frontmatter or a content database.

## Limitations

- Presence of structured data does not guarantee correctness; a parser can extract syntactically valid but factually inaccurate or inconsistent markup (e.g., describing content not actually visible on the page).
- No syntax is intrinsically "better" for machine consumption, but tooling and parser support is uneven — JSON-LD has the broadest current tooling support.
- Structured data adds no visual/functional behavior; a page can pass validation yet remain unreadable to non-technical consumers because the markup is invisible in the rendered page.

## Related Technologies

- JSON-LD (specific syntax reference)
- Schema.org (the dominant vocabulary used within all three syntaxes)
- RDF and the RDF triple data model underlying JSON-LD and RDFa

## Official References

- W3C Recommendation, "JSON-LD 1.1"
- W3C Working Group Note, "HTML Microdata"
- W3C Recommendation, "RDFa Core 1.1"
