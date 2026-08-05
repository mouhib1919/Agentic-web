---
category: interaction
criterion: api_availability
severity: high
related:
  - api_documentation
  - graphql
---

# Backend API Availability

## Definition

API availability evaluates whether a website exposes at least one executable, callable interaction surface — a raw REST endpoint or a GraphQL endpoint — as distinct from merely publishing documentation about an API that may or may not have a working, reachable implementation behind it.

## Technical Background

An available API responds to real requests with a valid, non-error status, following either REST architectural conventions (resource-based addressing, standard HTTP methods) or the GraphQL specification (a single endpoint accepting query documents). Reachability is confirmed at the transport/HTTP level, independent of any documentation describing it.

## Importance for AI Agent Readiness

This is the most fundamental interaction signal: without at least one executable API surface, an AI agent has no direct programmatic way to interact with the site at all, and is limited to passive content retrieval (reading rendered pages) rather than taking action or querying structured data on demand.

## ARAS Evaluation Context

ARAS checks: `evidence.api_analysis["api_endpoints"]` and `evidence.api_analysis["graphql_endpoints"]`. Documentation-only evidence (OpenAPI/Swagger/ReDoc URLs) is deliberately excluded from this criterion to avoid double-crediting the same evidence across `api_availability` and `api_documentation`.

Passed when: `api_endpoints` OR `graphql_endpoints` is non-empty.

Failure condition: both are empty.

Failure message: "No executable API interaction surface detected."

## Common Issues

- Only documentation/specification files published, with no confirmed live endpoint behind them.
- API endpoints exist but are only reachable under authenticated sessions, making them appear unavailable to unauthenticated discovery.
- API surface exists on a separate subdomain not covered by the evaluated origin.

## Impact

- **Technical impact**: no direct integration path exists for any external consumer, human or automated.
- **AI agent impact**: the agent is confined to content scraping/parsing rather than structured, reliable data access or action-taking — the highest-severity interaction gap ARAS evaluates.
- **Security impact**: minimal directly, though the complete absence of any API can indicate an application architecture not designed for external integration at all.

## Recommendation Strategy

Expose structured API endpoints (REST or GraphQL) that agents can consume, prioritizing read access to the site's core data entities (products, content, availability) as the minimum viable interaction surface.

## Implementation Guidance

- **FastAPI / Express / NestJS**: expose existing internal service logic through a public-facing REST API layer, even a minimal read-only subset.
- **GraphQL**: consider a single `/graphql` endpoint as an alternative, particularly for sites with complex, relationship-heavy data models.
- **API gateway / Cloudflare**: front the API with rate limiting and authentication as needed, without blocking discovery of its existence.

## Validation Checklist

- At least one endpoint responds with a non-404, structured (JSON) response to a well-formed request.
- The endpoint is reachable from outside any authenticated session, or its authentication requirement is clearly documented.
- Response status codes follow standard HTTP semantics (2xx success, 4xx/5xx errors).

## Related ARAS Criteria

- `api_documentation` — describes how to use the API once its availability is confirmed.
- `graphql` — a specific executable-surface type this criterion also credits.

## References

Source: official_sources/interaction/api_availability_reference.md
