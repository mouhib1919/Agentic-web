# JSON-LD (JavaScript Object Notation for Linked Data)

## Overview

JSON-LD is a lightweight syntax for expressing Linked Data (RDF) using ordinary JSON. It allows a JSON document to unambiguously identify the meaning of its keys and values by mapping them to terms defined in an external vocabulary, while remaining valid, parseable JSON that requires no specialized parser to read structurally.

## Official Definition

JSON-LD 1.1 is a W3C Recommendation, published by the JSON-LD Working Group, that defines the syntax, processing algorithms (expansion, compaction, flattening, framing), and API for producing and consuming JSON-LD documents. It is designed to be layered on top of the RDF 1.1 abstract data model.

## Core Concepts

- **`@context`**: maps short property/type names used in the document to full IRIs (typically vocabulary URLs such as `https://schema.org`), making the document's terms globally unambiguous.
- **`@type`**: declares the RDF type(s) of the described entity, typically a term resolvable through the active `@context`.
- **`@id`**: assigns a globally unique identifier (IRI) to an entity, enabling cross-references and entity reuse across documents.
- **`@graph`**: a keyword used to express multiple top-level entities, or entities alongside a shared context, within a single JSON-LD document.
- **Processing algorithms**: JSON-LD defines formal transformations — expansion (removing context, producing explicit IRIs), compaction (the reverse, using a context to shorten terms), and flattening (removing nested structure) — that allow JSON-LD documents to be normalized and compared programmatically.

## Technical Details

- Media type: `application/ld+json`.
- Web embedding syntax: `<script type="application/ld+json">{ ... }</script>` placed anywhere in the HTML document (commonly `<head>` or end of `<body>`).
- A JSON-LD document is, at the syntactic level, always valid JSON; the semantic layer is added entirely through reserved `@`-prefixed keywords.
- Multiple entities can be expressed as a top-level JSON array or via `@graph`.
- Nested objects represent related entities (e.g., an `Organization` referenced as the `publisher` of an `Article`) and are themselves typed via their own `@type`.

## Detection Characteristics

- One or more `<script type="application/ld+json">` elements with valid JSON content.
- Presence of an `@context` key (commonly, though not exclusively, resolving to `https://schema.org`).
- Presence of one or more `@type` values identifying the entity type(s) described.
- Well-formed documents parse without error under standard JSON parsing prior to any semantic interpretation.

## Common Implementations

- Search-engine-oriented structured data for articles, products, organizations, FAQs, breadcrumbs, and events, typically using Schema.org as the vocabulary.
- API-adjacent metadata describing an organization's identity (`Organization`, `WebSite` types) placed sitewide.
- Knowledge-graph and linked-data publishing outside the search context, using domain-specific vocabularies beyond Schema.org.

## Limitations

- A syntactically valid JSON-LD block can still be semantically inconsistent with the visible page content; JSON-LD itself provides no built-in mechanism to verify that claims match rendered content.
- Processing algorithms (expansion, framing) are non-trivial to implement fully; many lightweight consumers only perform a shallow read of `@type` and top-level properties rather than full RDF-level processing.
- No native versioning mechanism for the vocabulary referenced by `@context`; consumers must separately track vocabulary evolution (e.g., Schema.org version changes).

## Related Technologies

- RDF 1.1 (the abstract data model JSON-LD serializes)
- Schema.org (the most common vocabulary referenced via `@context`)
- Microdata and RDFa (alternative syntaxes for the same underlying structured-data goal)

## Official References

- W3C Recommendation, "JSON-LD 1.1: A JSON-based Serialization for Linked Data"
- W3C Recommendation, "JSON-LD 1.1 Processing Algorithms and API"
