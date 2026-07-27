# Schema.org

## Purpose

Schema.org is a collaborative, cross-industry vocabulary of types and properties for describing entities on the web — products, organizations, articles, events, people, places, recipes, and hundreds of other categories. It provides the shared "dictionary" that structured data formats such as JSON-LD, Microdata, and RDFa use to label content in a way that any compliant parser can understand, regardless of which site published it. Rather than each website inventing its own ad hoc labels for "price" or "author", Schema.org defines a common, hierarchical set of types (e.g. `Product` extends `Thing`) and properties, so structured data becomes interoperable across the entire web.

## Why it matters

For AI agent readiness, Schema.org is what makes structured data actually useful at scale: it is the shared semantic layer that lets an agent trained or configured to understand `schema:Product.price` apply that same understanding to any website that uses the vocabulary correctly, without site-specific integration work. Without a shared vocabulary, structured data would just be arbitrary JSON with no guaranteed meaning across sites. Schema.org's breadth — covering commerce, media, local business, health, and more — means most content types a website publishes already have a well-defined corresponding type, so adoption is rarely blocked by vocabulary gaps.

## When ARAS recommends it

The Recommendation Agent should retrieve this document when the Comprehension Agent reports:

- Structured data present (JSON-LD, Microdata, or RDFa) but no recognizable Schema.org `@type` or `itemtype`.
- Structured data using a non-standard or custom vocabulary instead of Schema.org.
- Content that clearly represents a well-known entity type (product, article, organization) but lacks any explicit typing.

## Implementation Guidelines

Start by identifying the primary entity or entities each page represents, then find the closest matching Schema.org type from schema.org's type hierarchy — for a product listing this is typically `Product`, for a blog post `Article` or `BlogPosting`, for a company's about page `Organization`. Populate the type-specific properties Schema.org defines for that type (for example, `Product` has `offers`, `aggregateRating`, `brand`; `Article` has `author`, `datePublished`, `headline`). When a page represents more than one related entity — such as a product listed by a specific organization — use nested typed objects to express the relationship (e.g. an `Offer` referencing an `Organization` as its `seller`) rather than flattening everything into one type. Where Schema.org offers more specific subtypes (`Restaurant` instead of the generic `LocalBusiness`, `NewsArticle` instead of generic `Article`), prefer the more specific type since it carries more precise semantics for downstream consumers.

## Best Practices

- Browse the Schema.org type hierarchy to find the most specific applicable type before defaulting to a generic one.
- Reuse Schema.org's defined property names exactly rather than inventing custom equivalents.
- Express relationships between entities using nested typed objects, not flat unstructured fields.
- Keep the chosen types consistent across similar pages sitewide (all product pages should consistently use `Product`, for example).
- Periodically review Schema.org updates, since new types and properties are added over time as the vocabulary evolves.

## Common Mistakes

- Defaulting to overly generic types (`Thing`, `WebPage`) when a specific type exists and would carry far more useful meaning.
- Inventing custom property names instead of using the standard ones defined by Schema.org, breaking interoperability.
- Mixing inconsistent types for conceptually identical content across a site.
- Applying a type that does not match the actual content, purely to attempt to trigger a search engine feature.
- Ignoring nested entity relationships and flattening related entities into a single disconnected type.

## Expected Benefits

For AI agents, Schema.org adoption means an agent's understanding of "what a product is" or "what an article is" transfers directly to any site using the vocabulary, without custom per-site logic. For search engines, correct Schema.org typing is a prerequisite for most rich result features. For machine readability broadly, it is the connective tissue that makes structured data portable and interoperable across the open web, rather than a collection of isolated, site-specific data islands.

## References

- Schema.org: the full type hierarchy and property definitions.
- Google Search Central: structured data type support and validation guidance.
- W3C: background on linked data principles that inform Schema.org's design.
