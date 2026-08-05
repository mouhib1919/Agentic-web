# Semantic Content Representation Formats

## Overview

Semantic content representation refers to the range of distinct, co-existing formats — JSON-LD, Microdata, and RDFa — through which a single web page can expose machine-interpretable descriptions of its content. Evaluating "semantic formats" as a criterion concerns not any one format in isolation, but the diversity and completeness of representation a page offers, since different consumers and toolchains have varying support for each syntax.

## Official Definition

Each format is independently specified: JSON-LD 1.1 and RDFa Core 1.1 are W3C Recommendations; Microdata is a W3C Working Group Note (having originated in an earlier draft of the WHATWG HTML specification before being spun out). There is no single "semantic formats" specification; the concept is an evaluative category spanning the three.

## Core Concepts

- **Format independence, semantic equivalence**: the same entity and property data can, in principle, be losslessly expressed in any of the three formats, since all three ultimately map to the RDF data model (JSON-LD and RDFa explicitly; Microdata via a documented conversion algorithm to RDF).
- **Coexistence**: a single page may legally include more than one format simultaneously, either describing the same entities redundantly or different entities in different formats.
- **Separation of concerns**: JSON-LD is fully decoupled from visible markup (a standalone script block), while Microdata and RDFa are coupled to the visible DOM (attributes on rendered elements) — a structural distinction with implications for maintainability and drift risk.
- **Consumer support variance**: not all structured-data consumers parse all three formats with equal fidelity; breadth of format support in a page increases the likelihood of successful extraction across heterogeneous consumers.

## Technical Details

- JSON-LD: isolated `<script type="application/ld+json">` blocks, unaffected by visible DOM changes.
- Microdata: `itemscope`/`itemtype`/`itemprop` attributes woven into the elements that already render the described content.
- RDFa: `vocab`/`typeof`/`property`/`resource` attributes, similarly woven into visible markup, but based on a more general RDF-attribute model than Microdata's narrower, HTML-specific one.
- The W3C has published a normative "Microdata to RDF" transformation algorithm, formally grounding Microdata within the same RDF data model as the other two.

## Detection Characteristics

- Independently detectable per format: JSON-LD via script-tag scanning and JSON parsing; Microdata via `itemscope`/`itemtype`/`itemprop` attribute scanning; RDFa via `typeof`/`property`/`vocab` attribute scanning.
- A page may score positively on zero, one, two, or all three formats; the count and combination is itself a meaningful signal distinct from any single format's presence.
- Entities described in multiple formats simultaneously on the same page are a detectable (and generally redundant) pattern.

## Common Implementations

- JSON-LD as the sole format, the most common pattern in modern implementations due to its independence from template/markup changes.
- Legacy or CMS-theme-embedded Microdata, often introduced by older SEO plugins predating JSON-LD's dominance.
- RDFa usage concentrated in publishing/media platforms with RDF-native content-management heritage.

## Limitations

- Maintaining multiple formats in parallel introduces a synchronization burden and risk of the formats diverging from each other or from the visible page content over time.
- No format is universally supported by every consumer; relying on a single format risks incompatibility with consumers that only implement another.
- Format diversity is not, by itself, evidence of information quality — it measures representation breadth, not content accuracy or completeness.

## Related Technologies

- Structured Data (the umbrella concept these formats implement)
- Schema.org (the vocabulary most commonly expressed across all three formats)
- RDF 1.1 abstract data model (the common semantic foundation)

## Official References

- W3C Recommendation, "JSON-LD 1.1"
- W3C Working Group Note, "HTML Microdata" and "Microdata to RDF"
- W3C Recommendation, "RDFa Core 1.1"
