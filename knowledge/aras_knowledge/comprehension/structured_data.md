---
category: comprehension
criterion: structured_data
severity: medium
related:
  - json_ld
  - schema_entities
---

# Structured Data Availability

## Definition

Structured data is machine-readable markup — JSON-LD, Microdata, or RDFa — embedded in a page that explicitly labels its content according to a shared vocabulary (typically Schema.org), letting a parser extract typed facts instead of inferring meaning from unstructured HTML.

## Technical Background

The three syntaxes are independently specified (JSON-LD 1.1 and RDFa Core 1.1 as W3C Recommendations, Microdata as a W3C Working Group Note) but are all groundable in the RDF data model. JSON-LD lives in an isolated `<script type="application/ld+json">` block; Microdata and RDFa use attributes woven directly into visible markup.

## Importance for AI Agent Readiness

The presence of any structured data format is the single strongest signal that a page has been made explicitly machine-interpretable. Its complete absence means an agent must fall back to unstructured HTML parsing or heuristic text extraction to understand page content, which is materially less reliable.

## ARAS Evaluation Context

ARAS checks: `evidence.structured_data` for the presence of any of `json-ld`, `microdata`, or `rdfa` entries.

Passed when: at least one of the three formats is present.

Failure condition: all three are empty.

Failure message: "No structured data found"

## Common Issues

- No structured data of any kind present on key pages (product, article, organization pages).
- Structured data present only on the homepage, absent from deeper content pages that would benefit most.
- Malformed JSON-LD (invalid JSON syntax) causing the block to fail parsing entirely.

## Impact

- **Technical impact**: search engines cannot render rich results (ratings, prices, breadcrumbs) for the page.
- **AI agent impact**: an agent must rely on fragile HTML/text heuristics to extract facts (price, author, availability), significantly increasing extraction error rates.
- **Security impact**: none directly.

## Recommendation Strategy

Add JSON-LD structured data using Schema.org vocabulary, prioritizing the page types with the clearest applicable Schema.org type (products, articles, organization identity) and the highest traffic or business value.

## Implementation Guidance

- **Any stack**: generate a JSON-LD `<script>` block server-side from the same data source rendering the visible page content, to guarantee consistency.
- **Next.js / React**: inject via the framework's head-management API as a raw script tag with `type="application/ld+json"`.
- **CMS platforms**: many provide a structured-data plugin/module that auto-generates JSON-LD from existing content fields — verify it is enabled and correctly mapped.

## Validation Checklist

- At least one `<script type="application/ld+json">` block present and valid JSON.
- Declared `@type` matches the page's actual content.
- Properties populated reflect only information genuinely visible on the page.
- Markup validated with a structured-data testing tool before deployment.

## Related ARAS Criteria

- `json_ld` — the specific format most commonly recommended as the primary structured-data mechanism.
- `schema_entities` — evaluates whether the structured data present declares meaningful Schema.org types.

## References

Source: official_sources/comprehension/structured_data_reference.md
