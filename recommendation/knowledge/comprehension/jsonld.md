# JSON-LD

## Purpose

JSON-LD (JavaScript Object Notation for Linked Data) is a lightweight, widely adopted format for embedding structured data directly into a web page as a `<script type="application/ld+json">` block. It allows a page to declare, in machine-readable JSON, what the page represents — a product, an organization, an article, an event, a person, or any other typed entity — using vocabularies such as Schema.org. Because JSON-LD is embedded as a self-contained script block rather than woven into HTML attributes, it can describe content without altering the visual markup at all, making it easy to add to existing pages without redesigning them.

## Why it matters

For AI agent readiness, JSON-LD is the single highest-leverage mechanism for making a page's meaning explicit rather than inferred. An agent parsing plain HTML has to guess whether a block of text is a price, a review score, or an address; JSON-LD removes that ambiguity by explicitly typing and labeling each piece of data. This matters enormously for comprehension: a page selling a product with JSON-LD `Product` markup lets an agent reliably extract the price, availability, and rating without fragile HTML scraping heuristics. Search engines have relied on this same mechanism for years to power rich results, and AI agents increasingly use the same structured signals to ground their understanding of a page's content.

## When ARAS recommends it

The Recommendation Agent should retrieve this document when the Comprehension Agent reports:

- No JSON-LD found on the page (`json_ld` check failed).
- Structured data present in other formats (Microdata, RDFa) but not JSON-LD, since JSON-LD is generally easier to maintain and less error-prone.
- JSON-LD present but without a recognizable `@type` (schema entities check failed).

## Implementation Guidelines

Add a `<script type="application/ld+json">` block containing a single JSON object (or an array of objects, or a `@graph`) describing the primary entities on the page. Always include `@context` set to `https://schema.org` and an appropriate `@type` matching the page's content — `Product`, `Organization`, `Article`, `FAQPage`, `Event`, `Person`, and so on. Populate as many relevant properties as accurately reflect the page's actual content; do not include data that is not visibly present on the page, since this violates structured data guidelines and can be penalized. Generate the JSON-LD dynamically from the same data source that renders the visible page content, so the two never drift out of sync. For pages representing multiple related entities (for example, a product page that also names its manufacturer), use nested objects or a `@graph` array rather than multiple disconnected script blocks.

## Best Practices

- Keep JSON-LD synchronized with visible page content; never mark up information the user cannot see.
- Use the most specific applicable `@type` rather than a generic one.
- Validate markup with structured data testing tools before deployment.
- Prefer one well-formed JSON-LD block per page over scattered, redundant fragments.
- Include identifying properties (`name`, `url`, `image`, `description`) at minimum, and type-specific properties (`price`, `author`, `datePublished`) where applicable.
- Automate generation from the underlying content model rather than hand-writing static JSON.

## Common Mistakes

- Marking up content that does not exist on the visible page, which can be flagged as manipulative structured data.
- Using outdated or invalid `@type` values that do not exist in the Schema.org vocabulary.
- Letting JSON-LD go stale after content updates because it is hand-maintained separately from the page template.
- Producing invalid JSON due to manual editing errors, which causes the entire block to be ignored by parsers.
- Overloading a single page with unrelated entity types that do not reflect its actual primary content.

## Expected Benefits

For AI agents, JSON-LD provides direct, reliable access to typed facts about a page's content, dramatically improving extraction accuracy over HTML scraping. For search engines, it enables rich results (star ratings, prices, event dates) that improve visibility. For machine readability broadly, it establishes a common vocabulary (via Schema.org) that lets independently built agents and crawlers interpret the same page consistently, without needing site-specific parsing logic.

## References

- Schema.org: the vocabulary most commonly used within JSON-LD.
- W3C: JSON-LD 1.1 specification.
- Google Search Central: structured data guidelines and supported rich result types.
