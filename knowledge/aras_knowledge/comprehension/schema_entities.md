---
category: comprehension
criterion: schema_entities
severity: medium
related:
  - json_ld
  - structured_data
---

# Schema.org Entity Description

## Definition

Schema.org entity description refers to whether a page's structured data declares explicit, recognized Schema.org types (e.g., `Product`, `Article`, `Organization`) via `@type` (JSON-LD), `itemtype` (Microdata), or `typeof` (RDFa), rather than containing untyped or ambiguous data.

## Technical Background

Schema.org is a shared, versioned, hierarchical vocabulary of types (rooted at `Thing`) and properties, governed by a multi-stakeholder community group. Consumers are expected to select the most specific applicable type, since more specific types carry richer, more precisely defined properties.

## Importance for AI Agent Readiness

Explicit typing is what allows an agent's understanding of "what a Product is" to transfer directly to any site using the vocabulary correctly, without site-specific integration logic. Structured data without a recognized type is far less useful, since the agent still has to guess what the described object represents.

## ARAS Evaluation Context

ARAS checks: `@type` values extracted from `evidence.structured_data["json-ld"]` entries.

Passed when: at least one recognized Schema.org type is present.

Failure condition: no JSON-LD entries declare a resolvable `@type`.

Failure message: "No Schema.org entities detected"

## Common Issues

- JSON-LD present but omitting `@type` entirely.
- `@type` set to an overly generic value (`Thing`, `WebPage`) when a more specific type applies.
- Type value misspelled or referencing a non-existent Schema.org term.
- Type declared but populated with few or no type-appropriate properties, limiting practical usefulness.

## Impact

- **Technical impact**: search engines cannot match the content to any eligible rich-result feature.
- **AI agent impact**: the agent cannot reliably classify the entity, forcing generic content parsing instead of type-aware field extraction (price, author, rating, etc.).
- **Security impact**: none directly.

## Recommendation Strategy

Define semantic entities such as Product, Organization, Article, or FAQ using the most specific Schema.org type applicable to each page's primary content, and populate the type's defined properties accordingly.

## Implementation Guidance

- **E-commerce**: use `Product` with nested `Offer`, `AggregateRating`, and `Brand` entities.
- **Publishing**: use `Article`, `NewsArticle`, or `BlogPosting` with `author` and `publisher` as nested `Person`/`Organization` entities.
- **Organization identity**: use `Organization` or the most specific `LocalBusiness` subtype applicable (e.g., `Restaurant`, `Store`).
- **FastAPI / Express / Next.js**: derive `@type` and its properties from an existing content model field (e.g., a `content_type` column) rather than hardcoding per template.

## Validation Checklist

- `@type` present and resolves to a genuine Schema.org type.
- The most specific applicable type is used rather than a generic ancestor.
- Type-appropriate properties are populated (e.g., `Product.price`, `Article.datePublished`).
- Nested entities (e.g., `Organization` as `Product.brand`) are themselves properly typed.

## Related ARAS Criteria

- `json_ld` — the format most commonly carrying these type declarations.
- `structured_data` — the broader criterion of which explicit typing is a component.

## References

Source: official_sources/comprehension/schema_entities_reference.md
