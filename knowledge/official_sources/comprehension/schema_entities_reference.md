# Schema.org Entity Types

## Overview

Schema.org is a shared, cross-industry vocabulary of entity types (e.g., `Product`, `Article`, `Organization`, `Person`) and their associated properties, designed to be embedded in web pages via structured data syntaxes (JSON-LD, Microdata, RDFa) so that any conforming consumer can interpret a page's content consistently, regardless of which website published it.

## Official Definition

Schema.org is maintained by a multi-stakeholder collaboration (originally founded by Google, Microsoft, Yahoo, and Yandex in 2011, now governed by the W3C Schema.org Community Group). It publishes a versioned, hierarchical type system at `schema.org`, with each type defined by a canonical URL, a set of applicable properties, and its position in a single-inheritance hierarchy rooted at `Thing`.

## Core Concepts

- **Type hierarchy**: every Schema.org type extends exactly one parent type, forming a tree rooted at the generic `Thing` (e.g., `Product` → `Thing`; `Restaurant` → `FoodEstablishment` → `LocalBusiness` → `Organization` → `Thing`).
- **Properties**: each type declares a set of applicable properties (e.g., `Product` has `price`, `brand`, `aggregateRating`); properties are also organized hierarchically and can apply to multiple types via a domain/range model borrowed from RDF Schema.
- **Specialization**: consumers are expected to select the most specific applicable type rather than a generic ancestor, since more specific types carry richer, more precisely defined properties.
- **Extensions and pending types**: Schema.org supports community-proposed extensions and a "pending" area for types under review before full inclusion in the core vocabulary.

## Technical Details

- Canonical identifiers: every type and property is addressable by a stable URL under `https://schema.org/` (e.g., `https://schema.org/Product`).
- Cross-type relationships are expressed via typed properties whose value is itself another typed entity (e.g., a `Product`'s `manufacturer` property takes an `Organization` value), enabling nested entity graphs.
- Multiple inheritance of behavior is not supported at the type level (single-parent hierarchy), though a single JSON-LD node may declare multiple `@type` values when representing an entity that legitimately belongs to more than one type.
- Versioning: Schema.org publishes dated releases; property and type definitions can be extended (rarely removed) between versions.

## Detection Characteristics

- A structured-data block (JSON-LD `@type`, Microdata `itemtype`, or RDFa `typeof`) whose value resolves to a `schema.org` URL or a bare recognized type name.
- Use of type-appropriate properties consistent with the declared type's defined property set (e.g., a `Product` entity populating `offers`, `aggregateRating`).
- Nested typed entities representing relationships (e.g., `Product.brand` containing a nested `Brand` or `Organization` entity).

## Common Implementations

- E-commerce: `Product`, `Offer`, `AggregateRating`, `Review`.
- Publishing: `Article`, `NewsArticle`, `BlogPosting`, with `author` and `publisher` as nested `Person`/`Organization` entities.
- Local/organizational identity: `Organization`, `LocalBusiness`, and its many specialized subtypes (`Restaurant`, `Store`, `MedicalBusiness`, etc.).
- Content organization: `BreadcrumbList`, `FAQPage`, `HowTo`, `Event`.

## Limitations

- The vocabulary, while broad, does not cover every domain-specific concept; publishers with highly specialized content may need external or custom extensions, which reduces interoperability.
- Type selection is a modeling judgment call; ambiguous content can reasonably map to more than one type, and no canonical resolution mechanism exists for such ambiguity.
- Property applicability is a strong convention, not a strictly enforced constraint — most consumers do not reject markup that uses a property outside its formally declared domain, which allows inconsistent usage to persist uncorrected.

## Related Technologies

- JSON-LD, Microdata, RDFa (the syntaxes used to encode Schema.org types)
- RDF Schema (RDFS), whose type/property hierarchy model Schema.org's design follows conceptually
- Open Graph protocol, a smaller, non-hierarchical, social-sharing-oriented alternative vocabulary

## Official References

- Schema.org, full type hierarchy and vocabulary documentation
- W3C Schema.org Community Group, governance and versioning process
