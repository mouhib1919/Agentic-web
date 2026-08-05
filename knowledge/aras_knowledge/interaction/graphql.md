---
category: interaction
criterion: graphql
severity: medium
related:
  - api_availability
  - api_documentation
---

# GraphQL Availability

## Definition

GraphQL availability evaluates whether a website exposes a GraphQL endpoint — a single, query-language-driven interface (GraphQL Foundation specification) letting a client request exactly the fields it needs across related entities in one round trip, as opposed to REST's multiple fixed endpoints.

## Technical Background

A GraphQL API is described by a strongly typed schema, introspectable at runtime via the standard `__schema`/`__type` meta-fields. The endpoint conventionally lives at `/graphql`, accepting POST requests with a JSON body containing a query document and optional variables.

## Importance for AI Agent Readiness

GraphQL's introspection capability lets an agent discover the entire available schema programmatically, without external documentation, and construct precisely scoped queries that reduce the number of round trips needed to assemble related data — a meaningful efficiency advantage for multi-entity agent tasks.

## ARAS Evaluation Context

ARAS checks: `evidence.api_analysis["graphql_endpoints"]`.

Passed when: `graphql_endpoints` is non-empty.

Failure condition: `graphql_endpoints` is empty.

Failure message: "No GraphQL endpoint detected."

## Common Issues

- No GraphQL endpoint at all, common on sites built purely around REST.
- GraphQL endpoint present but introspection disabled without a published alternative schema (SDL) document, making it effectively undiscoverable.
- Endpoint present but returning inconsistent error shapes, unlike the standard `{"data": ..., "errors": ...}` response format.

## Impact

- **Technical impact**: consumers needing relationship-heavy data must issue multiple sequential REST calls instead of one query.
- **AI agent impact**: without GraphQL, an agent loses the ability to efficiently traverse related entities in a single request, increasing latency and request count for complex data-gathering tasks.
- **Security impact**: minimal directly, though publicly introspectable GraphQL APIs in production without complexity limiting can expose a broader attack surface for resource-exhaustion queries.

## Recommendation Strategy

Expose GraphQL APIs when flexible agent interaction is required, particularly for sites with relationship-heavy data models where REST would otherwise require many chained calls.

## Implementation Guidance

- **Apollo Server / Node.js**: a common, well-documented path to standing up a GraphQL endpoint alongside or instead of REST.
- **GraphQL Yoga / Express**: lightweight alternative for adding a `/graphql` endpoint to an existing Express application.
- **Schema design**: model the schema around domain entities and relationships, not a direct mirror of internal database tables.
- **Production hardening**: pair introspection availability with query depth/complexity limiting to prevent abuse.

## Validation Checklist

- `/graphql` (or equivalent) accepts POST requests and returns a GraphQL-shaped JSON response.
- An introspection query (`{ __schema { types { name } } }`) succeeds, or an equivalent SDL document is published if introspection is disabled.
- Query complexity/depth limits are in place for production deployments.

## Related ARAS Criteria

- `api_availability` — GraphQL endpoints also satisfy this broader executable-surface criterion.
- `api_documentation` — for GraphQL, introspection substitutes for a separate specification file.

## References

Source: official_sources/interaction/graphql_reference.md
