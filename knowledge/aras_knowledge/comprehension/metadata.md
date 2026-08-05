---
category: comprehension
criterion: metadata
severity: medium
related:
  - open_graph
  - internal_structure
---

# Comprehension Metadata (Title, Description, Language)

## Definition

Comprehension metadata is the minimal document-level signal set — `<title>`, `<meta name="description">`, and the `lang` attribute — that lets a machine consumer establish basic subject-matter and linguistic context before any deeper semantic analysis.

## Technical Background

`<title>` and `lang` are defined by the WHATWG HTML Living Standard; `lang` values must conform to BCP 47 (IETF RFC 5646). `lang` is inherited: content without its own explicit `lang` is assumed to be in the nearest ancestor's declared language, and a document lacking `lang` entirely is formally "of unknown language."

## Importance for AI Agent Readiness

Language declaration in particular is critical for correct downstream processing: translation, spell-checking, and NLP pipelines all depend on it to select the right language model or ruleset. Combined with title and description, these three fields form the baseline an agent needs before attempting any content interpretation.

## ARAS Evaluation Context

ARAS checks: `evidence.title`, `evidence.meta_tags["description"]`, `evidence.language`.

Passed when: title is non-empty AND meta description is non-empty AND language is non-empty.

Failure condition: any of the three is missing.

Failure message: `"Missing metadata information: {comma-separated list of missing fields}"` (fields: `title`, `meta description`, `language`).

## Common Issues

- `lang` attribute entirely absent from the root `<html>` element.
- `lang` present but malformed (not a valid BCP 47 tag).
- Multi-locale sites failing to set `lang` per rendered locale variant.
- Meta description absent, present but empty, or generic/templated with no real per-page content.

## Impact

- **Technical impact**: assistive technology and language-dependent tooling cannot reliably determine how to process the page.
- **AI agent impact**: without an explicit language signal, an agent's NLP pipeline must fall back to language detection, which is slower and less accurate than an explicit declaration, especially on short or mixed-language pages.
- **Security impact**: none directly.

## Recommendation Strategy

Add title, meta description, and language attributes: set `lang` on the root `<html>` element from the application's locale configuration, and ensure title/description are populated per page rather than defaulted globally.

## Implementation Guidance

- **Server-side rendering (any stack)**: set `<html lang="...">` from the request's resolved locale at render time.
- **Next.js**: set `lang` in the root layout's `<html>` tag, driven by the active locale/i18n configuration.
- **Multi-locale sites**: pair `lang` with `hreflang` alternate-language link annotations for each locale variant.

## Validation Checklist

- Root `<html>` element has a `lang` attribute with a valid BCP 47 value.
- `<title>` is present, non-empty, and page-specific.
- `<meta name="description">` is present with meaningful, page-specific content.
- Mixed-language sections within the page override `lang` locally where appropriate.

## Related ARAS Criteria

- `open_graph` — overlapping identity metadata for social/preview rendering.
- `internal_structure` — semantic organization signals that complement basic metadata for deeper comprehension.

## References

Source: official_sources/comprehension/metadata_reference.md
