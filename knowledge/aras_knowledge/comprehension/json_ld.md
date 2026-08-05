---
category: comprehension
criterion: json_ld
severity: medium
related:
  - structured_data
  - schema_entities
---

# JSON-LD Semantic Understanding

## Definition

JSON-LD (JavaScript Object Notation for Linked Data) is a W3C-specified syntax for expressing structured, typed data as valid JSON, using `@context` and `@type` keywords to unambiguously map document terms to a vocabulary such as Schema.org.

## Technical Background

A JSON-LD block is embedded via `<script type="application/ld+json">`, decoupled entirely from the visible DOM. Multiple entities can be expressed via a top-level array or `@graph`. It is the format most consistently recommended by search engines and most broadly supported by current structured-data tooling among the three available syntaxes.

## Importance for AI Agent Readiness

JSON-LD is the highest-leverage single mechanism for making a page's meaning explicit to an AI agent: it directly answers "what type of entity is this, and what are its key properties" without requiring the agent to infer structure from visual layout or prose.

## ARAS Evaluation Context

ARAS checks: `evidence.structured_data["json-ld"]`.

Passed when: at least one JSON-LD object is present.

Failure condition: the `json-ld` list is empty.

Failure message: "No JSON-LD semantic information found"

## Common Issues

- No JSON-LD present even when Microdata or RDFa exist (a format the specification favors for its ease of maintenance is simply not adopted).
- JSON-LD present but containing syntactically invalid JSON, causing the entire block to fail parsing.
- JSON-LD referencing a non-standard or incorrect `@context`, preventing correct term resolution.

## Impact

- **Technical impact**: search engines and other structured-data consumers cannot reliably extract typed facts even if other formats are present, due to inconsistent tooling support across syntaxes.
- **AI agent impact**: the agent cannot access a self-contained, easily parseable semantic block and must instead cross-reference DOM-coupled Microdata/RDFa (if present) or fall back to unstructured parsing.
- **Security impact**: none directly.

## Recommendation Strategy

Add JSON-LD markup to describe website entities, using `@context: "https://schema.org"` and the most specific applicable `@type`, generated dynamically from the same data source that renders the visible page content.

## Implementation Guidance

- **FastAPI / Express**: render the JSON-LD block server-side within the page template from the same model/data object used for the visible content.
- **Next.js**: use `dangerouslySetInnerHTML` (React) or the framework's structured-data helper to inject a `<script type="application/ld+json">` tag safely.
- **Static site generators**: populate JSON-LD from frontmatter fields already driving the page's title/description.

## Validation Checklist

- `<script type="application/ld+json">` content parses as valid JSON.
- `@context` resolves to `https://schema.org` (or another recognized vocabulary).
- `@type` is present and specific to the page's actual content.
- Property values match what is visibly rendered on the page.

## Related ARAS Criteria

- `structured_data` — the broader criterion this format contributes to.
- `schema_entities` — evaluates the specific Schema.org types declared within this JSON-LD.

## References

Source: official_sources/comprehension/json_ld_reference.md
