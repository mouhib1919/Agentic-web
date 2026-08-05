---
category: comprehension
criterion: semantic_formats
severity: low
related:
  - json_ld
  - structured_data
---

# Content Representation Formats

## Definition

This criterion evaluates the diversity of machine-readable content representation a page offers — how many of the three structured-data syntaxes (JSON-LD, Microdata, RDFa) are present — as a signal of representation breadth rather than any single format's correctness.

## Technical Background

All three formats are independently specified but map to the same underlying RDF data model, meaning the same entity data can, in principle, be losslessly expressed in any of them. A page may legally include more than one format simultaneously, either redundantly describing the same entities or describing different entities in different formats.

## Importance for AI Agent Readiness

Not every structured-data consumer parses all three formats with equal fidelity. A page offering multiple representations increases the likelihood of successful extraction across a heterogeneous population of agents and tools, even though a single well-formed format (typically JSON-LD) is generally sufficient for most modern consumers.

## ARAS Evaluation Context

ARAS checks: presence of any of `evidence.structured_data["json-ld"]`, `["microdata"]`, `["rdfa"]`.

Passed when: at least one format is present (identical underlying signal to `structured_data`, evaluated here as a representation-breadth criterion).

Failure condition: all three formats are empty.

Failure message: "Poor semantic representation"

## Common Issues

- No structured data in any format, the most severe case, already flagged more directly by the `structured_data` criterion.
- Reliance on a single, older format (Microdata or RDFa) inherited from earlier tooling, without a JSON-LD equivalent.
- Redundant, unsynchronized duplication across formats that drifts apart over time as the page is edited.

## Impact

- **Technical impact**: consumers unable to parse the site's chosen format receive no structured signal at all.
- **AI agent impact**: agents relying on a specific parser (most commonly JSON-LD-only tooling) receive nothing if the site only implements Microdata or RDFa.
- **Security impact**: none directly.

## Recommendation Strategy

Provide machine-readable content representations for AI agents, prioritizing JSON-LD as the primary, most broadly supported format, and avoiding reliance on Microdata/RDFa alone.

## Implementation Guidance

- **New implementations**: default to JSON-LD exclusively; it requires no coupling to visible markup and is the most broadly supported by current tooling.
- **Legacy Microdata/RDFa migrations**: migrate to JSON-LD incrementally per page type, verifying equivalence before removing the legacy markup.
- **Multi-format sites**: if maintaining more than one format, generate all from the same underlying data source to prevent drift.

## Validation Checklist

- At least one structured-data format is present and valid.
- If multiple formats are present, their described entities are consistent with each other.
- JSON-LD, where present, is prioritized as the canonical representation.

## Related ARAS Criteria

- `structured_data` — the underlying presence signal this criterion evaluates for representation breadth.
- `json_ld` — the specific, most broadly supported format this criterion's recommendation prioritizes.

## References

Source: official_sources/comprehension/semantic_formats_reference.md
