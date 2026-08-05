# Comprehension Metadata (Title, Description, Language)

## Overview

Comprehension metadata is the minimal set of document-level signals — the title, a descriptive summary, and the declared natural language — that let a machine consumer establish basic understanding of what a page is about and how its text content should be linguistically processed, prior to any deeper semantic or structured-data analysis.

## Official Definition

- `<title>` is defined by the WHATWG HTML Living Standard as required document metadata.
- `<meta name="description">` is a widely adopted convention (not part of the core HTML specification's normative element list, but documented as a recognized metadata pattern).
- The document language is declared through the `lang` global attribute, formally defined in the WHATWG HTML Living Standard, whose values are constrained to valid BCP 47 language tags (IETF RFC 5646).

## Core Concepts

- **Title**: the primary human- and machine-facing identity string for a document.
- **Description**: a free-text summary intended to convey the page's subject matter without requiring full-content parsing.
- **Language declaration**: `lang` on the root `<html>` element (or on any sub-element to override locally) declares the primary natural language of the enclosed text, which downstream systems (screen readers, translation tools, NLP pipelines, spell-checkers) rely on to select correct language-specific processing.

## Technical Details

- `lang` attribute syntax: `<html lang="en">`, `<html lang="fr-CA">` — values must conform to BCP 47 (a primary subtag, optionally extended by region, script, or variant subtags).
- The `lang` attribute is inherited: content within an element without an explicit `lang` attribute is assumed to be in the nearest ancestor's declared language.
- `<meta name="description">` has no required length; no formal schema constrains its content beyond being plain text.
- A document with no `lang` attribute is formally "of unknown language" per the HTML specification, which downstream tools may handle via heuristic language detection rather than an explicit signal.

## Detection Characteristics

- Presence and value of the `lang` attribute on the root `<html>` element.
- Presence and content of `<title>`.
- Presence and `content` attribute value of `<meta name="description">`.
- A `lang` value that fails BCP 47 syntax validation is a detectable malformed state distinct from simple absence.

## Common Implementations

- Server-side rendering setting `lang` from the application's locale/internationalization configuration.
- CMS-driven title/description fields populated per page, often with template-level fallbacks for pages lacking explicit values.
- Multi-locale sites setting `lang` per rendered locale variant, frequently paired with `hreflang` alternate-language link annotations.

## Limitations

- `lang` declares intent, not a guarantee; a page can declare one language while actually containing substantial text in another (e.g., untranslated fallback content).
- Meta description is not rendered on the page itself and cannot be visually verified by a human editor without external tooling, making silent staleness or omission common.
- None of these signals are individually sufficient for deep content understanding; they establish minimal identification and linguistic context, not semantic meaning.

## Related Technologies

- `hreflang` link annotations (declaring language/region alternates of the same content)
- Structured data (`@language` in JSON-LD, an alternative per-entity language declaration mechanism)
- `<meta charset>` (character encoding, a related but distinct concern from natural language)

## Official References

- WHATWG HTML Living Standard, "The lang and xml:lang attributes"
- IETF RFC 5646, "Tags for Identifying Languages" (BCP 47)
- WHATWG HTML Living Standard, "The title element"
